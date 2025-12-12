"""
Execution Engine - Firma, envío, gestión y confirmación de órdenes.

Refactorizado según especificación en docs/services/execution.md y docs/services/signatures_trazability.md
"""
import logging
import hashlib
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import httpx
import time

from app.core.state import state
from app.core.wallet import wallet_service
from app.core.risk_engine.models import ApprovedOrderIntent
from app.core.rate_limiter import rate_limiter, EndpointType
from app.core.latency_monitor import latency_monitor, LatencyStatus
from app.core.execution.models import (
    SignedOrder, ExecutionRecord, OrderStateHistory, FillRecord, ExecutionConfig
)
from app.core.execution.eip712_signer import EIP712Signer
from app.core.execution.nonce_manager import NonceManager
from app.core.execution.order_lifecycle import OrderLifecycleManager
from app.database import SessionLocal
from app.models.order import Order
from app.models.trade import Trade
from app.models.position import Position
from app.settings import settings

logger = logging.getLogger(__name__)


class Execution:
    """
    Execution Engine service.
    
    Responsabilidades:
    - Firmar órdenes con EIP-712
    - Enviar órdenes a Polymarket
    - Monitorear estado de órdenes
    - Gestionar fills y actualizar posiciones
    - Cancelar órdenes cuando es necesario
    - Mantener trazabilidad completa
    """
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        """Inicializa el Execution Engine."""
        self._config = config or ExecutionConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._pending_orders: Dict[str, Order] = {}  # Track orders sent to Polymarket
        self._eip712_signer = EIP712Signer(self._config)
        self._nonce_manager = NonceManager(self._config)
        self._lifecycle_manager = OrderLifecycleManager()
        self._signed_orders: Dict[UUID, SignedOrder] = {}  # Cache de órdenes firmadas
        self._execution_records: Dict[UUID, ExecutionRecord] = {}  # Cache de registros de ejecución
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Obtiene o crea cliente HTTP."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._config.timeout)
        return self._client
    
    def _build_order_payload(
        self,
        intent: ApprovedOrderIntent,
        nonce: int,
        client_order_id: str
    ) -> Dict[str, Any]:
        """
        Construye payload de orden según especificación de Polymarket.
        
        Según especificación en docs/services/execution.md
        """
        expiration = int((datetime.utcnow() + timedelta(seconds=self._config.order_ttl_seconds)).timestamp())
        
        # TODO: Obtener outcome desde el mercado (YES/NO)
        # Por ahora, asumimos "YES" para compras
        outcome = "YES" if intent.side == "BUY" else "NO"
        
        # TODO: Obtener polymarket_market_id desde el mercado
        # Por ahora, usamos el market_id como string
        market_id = str(intent.market_id)
        
        return {
            "marketId": market_id,
            "outcome": outcome,
            "price": intent.price,
            "size": intent.size,
            "side": intent.side,
            "nonce": nonce,
            "expiration": expiration,
            "clientOrderId": client_order_id,
        }
    
    def _sign_order(
        self,
        intent: ApprovedOrderIntent,
        payload: Dict[str, Any],
        private_key: str,
        wallet_address: str
    ) -> SignedOrder:
        """
        Firma una orden usando EIP-712.
        
        Según especificación en docs/services/signatures_trazability.md
        """
        # Construir mensaje EIP-712
        message = self._eip712_signer.build_order_message(
            market_id=payload["marketId"],
            outcome=payload["outcome"],
            price=payload["price"],
            size=payload["size"],
            side=payload["side"],
            nonce=payload["nonce"],
            expiration=payload["expiration"],
            client_order_id=payload["clientOrderId"]
        )
        
        # Firmar
        signing_result = self._eip712_signer.sign(message, private_key)
        
        # Crear SignedOrder
        signed_order = SignedOrder(
            signed_order_id=uuid4(),
            intent_id=intent.trace_id,  # Usar trace_id como referencia
            trace_id=intent.trace_id,
            wallet_address=wallet_address,
            chain_id=self._config.eip712_chain_id,
            domain_separator=signing_result.get("domain_separator"),
            domain_json=signing_result.get("domain_json", {}),
            message_struct=message,
            message_hash=signing_result.get("message_hash"),
            signature=signing_result["signature"],
            created_at=datetime.utcnow(),
            expires_at=datetime.fromtimestamp(payload["expiration"]) if payload.get("expiration") else None,
            status="READY_TO_SEND"
        )
        
        # Cachear
        self._signed_orders[signed_order.signed_order_id] = signed_order
        
        logger.info(
            f"Order signed: {signed_order.signed_order_id}",
            extra={
                "component": "execution",
                "event": "order_signed",
                "signed_order_id": str(signed_order.signed_order_id),
                "trace_id": str(signed_order.trace_id),
                "wallet_address": wallet_address
            }
        )
        
        return signed_order
    
    def _create_execution_record(
        self,
        signed_order: SignedOrder,
        request_payload: Dict[str, Any]
    ) -> ExecutionRecord:
        """
        Crea un registro de ejecución antes de enviar.
        
        Según especificación en docs/services/signatures_trazability.md
        """
        # Calcular hash del payload
        payload_str = json.dumps(request_payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        
        execution_record = ExecutionRecord(
            execution_id=uuid4(),
            signed_order_id=signed_order.signed_order_id,
            trace_id=signed_order.trace_id,
            request_payload=request_payload,
            request_payload_hash=payload_hash,
            http_method="POST",
            endpoint_url=self._config.polymarket_trading_endpoint,
            status="PENDING",
            created_at=datetime.utcnow()
        )
        
        # Cachear
        self._execution_records[execution_record.execution_id] = execution_record
        
        return execution_record
    
    async def _send_order_to_polymarket(
        self,
        signed_order: SignedOrder,
        request_payload: Dict[str, Any],
        execution_record: ExecutionRecord
    ) -> Optional[str]:
        """
        Envía orden a Polymarket Trading API con rate limiting y retry logic.
        
        Según especificación en docs/services/execution.md
        """
        execution_start = time.monotonic_ns()
        client = await self._get_client()
        
        # Retry logic con exponential backoff
        last_error = None
        for attempt in range(self._config.max_retries):
            try:
                # Adquirir permiso de rate limit
                if not await rate_limiter.wait_for_capacity(EndpointType.TRADING_ORDER, timeout=2.0):
                    logger.warning(
                        "Rate limit timeout for trading order",
                        extra={
                            "component": "execution",
                            "signed_order_id": str(signed_order.signed_order_id),
                            "trace_id": str(signed_order.trace_id)
                        }
                    )
                    execution_record.status = "TIMEOUT"
                    execution_record.error_message = "Rate limit timeout"
                    return None
                
                # Construir payload HTTP
                http_payload = {
                    **request_payload,
                    "signature": signed_order.signature
                }
                
                # TODO: Reemplazar con endpoint real de Polymarket
                # Por ahora, simular envío
                await asyncio.sleep(0.1)  # Simular network + processing time
                
                # Simular respuesta exitosa
                # response = await client.post(
                #     self._config.polymarket_trading_endpoint,
                #     json=http_payload
                # )
                # 
                # if response.status_code == 429:
                #     await rate_limiter.record_violation(EndpointType.TRADING_ORDER)
                #     raise httpx.HTTPStatusError("Rate limit exceeded", request=response.request, response=response)
                # 
                # response.raise_for_status()
                # response_data = response.json()
                
                # Simular respuesta
                response_data = {
                    "order_id": f"pm_order_{uuid4().hex[:8]}",
                    "status": "accepted"
                }
                
                # Medir latencia
                execution_end = time.monotonic_ns()
                execution_latency_ms = (execution_end - execution_start) / 1_000_000
                latency_monitor.record_execution_latency(execution_latency_ms)
                
                # Actualizar execution record
                execution_record.status = "ACCEPTED"
                execution_record.polymarket_order_id = response_data.get("order_id")
                execution_record.response_payload = response_data
                execution_record.response_payload_hash = hashlib.sha256(
                    json.dumps(response_data, sort_keys=True).encode()
                ).hexdigest()
                execution_record.http_status_code = 200
                execution_record.latency_ms = execution_latency_ms
                execution_record.retry_count = attempt
                execution_record.is_retry = attempt > 0
                
                # Actualizar signed order
                signed_order.status = "SENT"
                
                logger.info(
                    f"Order submitted to Polymarket: {execution_record.polymarket_order_id}",
                    extra={
                        "component": "execution",
                        "event": "order_submitted",
                        "signed_order_id": str(signed_order.signed_order_id),
                        "polymarket_order_id": execution_record.polymarket_order_id,
                        "latency_ms": execution_latency_ms,
                        "trace_id": str(signed_order.trace_id)
                    }
                )
                
                return execution_record.polymarket_order_id
                
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    await rate_limiter.record_violation(EndpointType.TRADING_ORDER)
                    logger.warning("Rate limit exceeded for trading API")
                
                # Si no es el último intento, esperar y reintentar
                if attempt < self._config.max_retries - 1:
                    delay = self._config.retry_delays[min(attempt, len(self._config.retry_delays) - 1)]
                    await asyncio.sleep(delay)
                    execution_record.retry_count = attempt + 1
                    execution_record.is_retry = True
                    continue
                else:
                    # Último intento falló
                    execution_record.status = "ERROR"
                    execution_record.error_message = str(e)
                    execution_record.http_status_code = e.response.status_code if hasattr(e, 'response') else None
                    break
                    
            except Exception as e:
                last_error = e
                # Si no es el último intento, esperar y reintentar
                if attempt < self._config.max_retries - 1:
                    delay = self._config.retry_delays[min(attempt, len(self._config.retry_delays) - 1)]
                    await asyncio.sleep(delay)
                    execution_record.retry_count = attempt + 1
                    execution_record.is_retry = True
                    continue
                else:
                    # Último intento falló
                    execution_record.status = "ERROR"
                    execution_record.error_message = str(e)
                    break
        
        # Si todos los intentos fallaron
        execution_record.latency_ms = (time.monotonic_ns() - execution_start) / 1_000_000
        signed_order.status = "SEND_FAILED"
        
        logger.error(
            f"Failed to send order to Polymarket after {self._config.max_retries} attempts",
            extra={
                "component": "execution",
                "event": "order_send_failed",
                "signed_order_id": str(signed_order.signed_order_id),
                "trace_id": str(signed_order.trace_id),
                "error": str(last_error),
                "retry_count": execution_record.retry_count
            }
        )
        
        return None
    
    async def _create_order_in_db(
        self,
        intent: ApprovedOrderIntent,
        polymarket_order_id: Optional[str],
        signed_order: SignedOrder
    ) -> Order:
        """Crea registro de orden en base de datos."""
        db = SessionLocal()
        try:
            order = Order(
                id=uuid4(),
                polymarket_order_id=polymarket_order_id,
                market_id=intent.market_id,
                side=intent.side,
                price=intent.price,
                size=intent.size,
                status="CREATED",  # Estado inicial según lifecycle
                filled_size=0.0,
            )
            db.add(order)
            db.commit()
            db.refresh(order)
            
            # Actualizar estado a SIGNED
            self._lifecycle_manager.update_order_state(
                order.id,
                "SIGNED",
                reason="Order signed with EIP-712"
            )
            
            # Si fue enviado exitosamente, actualizar a SUBMITTED
            if polymarket_order_id:
                self._lifecycle_manager.update_order_state(
                    order.id,
                    "SUBMITTED",
                    reason="Order submitted to Polymarket"
                )
            
            return order
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating order in DB: {e}")
            raise
        finally:
            db.close()
    
    async def _update_order_state(
        self,
        order_id: UUID,
        new_status: str,
        reason: Optional[str] = None,
        filled_size: Optional[float] = None
    ):
        """Actualiza estado de orden usando Order Lifecycle Manager."""
        self._lifecycle_manager.update_order_state(
            order_id,
            new_status,
            reason=reason,
            filled_size=filled_size
        )
        
        # Actualizar estado en memoria
        if order_id in state.orders:
            state.orders[order_id].status = new_status
            if filled_size is not None:
                state.orders[order_id].filled_size = filled_size
            state.orders[order_id].updated_at = datetime.utcnow()
    
    async def _handle_fill(
        self,
        order_id: UUID,
        fill_price: float,
        fill_size: float
    ):
        """
        Maneja un fill de orden - actualiza posición y crea trade.
        
        Según especificación en docs/services/execution.md
        """
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                logger.warning(f"Order {order_id} not found for fill")
                return
            
            # Crear trade record
            trade = Trade(
                id=uuid4(),
                order_id=order_id,
                market_id=order.market_id,
                fill_price=fill_price,
                fill_size=fill_size,
                direction=order.side,
                timestamp=datetime.utcnow(),
            )
            db.add(trade)
            
            # Actualizar orden
            new_filled_size = order.filled_size + fill_size
            order.filled_size = new_filled_size
            
            # Determinar nuevo estado
            if new_filled_size >= order.size:
                new_status = "FILLED"
            else:
                new_status = "PARTIALLY_FILLED"
            
            # Actualizar estado usando lifecycle manager
            await self._update_order_state(order_id, new_status, filled_size=new_filled_size)
            
            # Actualizar o crear posición
            position = db.query(Position).filter(Position.market_id == order.market_id).first()
            if not position:
                position = Position(
                    id=uuid4(),
                    market_id=order.market_id,
                    size=fill_size,
                    avg_price=fill_price,
                    resolved=False,
                )
                db.add(position)
            else:
                # Recalcular precio promedio
                total_cost = (position.size * position.avg_price) + (fill_size * fill_price)
                total_size = position.size + fill_size
                position.avg_price = total_cost / total_size if total_size > 0 else fill_price
                position.size = total_size
            
            # Actualizar posición en estado
            if order.market_id not in state.positions:
                from app.core.state import PositionState
                state.positions[order.market_id] = PositionState()
                state.positions[order.market_id].market_id = order.market_id
            
            pos_state = state.positions[order.market_id]
            pos_state.size = position.size
            pos_state.avg_price = position.avg_price
            pos_state.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(
                f"Fill handled for order {order_id}",
                extra={
                    "component": "execution",
                    "event": "fill",
                    "order_id": str(order_id),
                    "fill_price": fill_price,
                    "fill_size": fill_size,
                    "new_status": new_status
                }
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Error handling fill: {e}")
        finally:
            db.close()
    
    async def _poll_order_status(self, order_id: UUID):
        """
        Consulta estado de orden en Polymarket con rate limiting.
        
        Usa Data API para estado de orden (200 req / 10s).
        Almacena OrderStateHistory para trazabilidad.
        """
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order or not order.polymarket_order_id:
                return
            
            # Adquirir permiso de rate limit
            if not await rate_limiter.wait_for_capacity(EndpointType.DATA_API, timeout=1.0):
                logger.debug(f"Rate limit timeout for polling order {order_id}")
                return
            
            # TODO: Implementar polling real desde Polymarket API
            # Por ahora, simular consulta
            # try:
            #     client = await self._get_client()
            #     response = await client.get(
            #         f"{self._config.polymarket_trading_endpoint}/orders/{order.polymarket_order_id}"
            #     )
            #     
            #     if response.status_code == 429:
            #         await rate_limiter.record_violation(EndpointType.DATA_API)
            #         return
            #     
            #     response.raise_for_status()
            #     order_status = response.json()
            #     
            #     # Crear OrderStateHistory
            #     state_history = OrderStateHistory(
            #         order_state_history_id=uuid4(),
            #         polymarket_order_id=order.polymarket_order_id,
            #         trace_id=order.id,  # Usar order.id como referencia
            #         timestamp=datetime.utcnow(),
            #         previous_status=order.status,
            #         new_status=order_status.get("status", "UNKNOWN"),
            #         filled_size=order_status.get("filled_size", order.filled_size),
            #         remaining_size=order_status.get("remaining_size", order.size - order.filled_size),
            #         metadata={"source": "SCHEDULED_POLL", "raw_state": order_status}
            #     )
            #     
            #     # Actualizar orden si hay cambios
            #     if order_status.get("status") != order.status:
            #         await self._update_order_state(
            #             order_id,
            #             order_status.get("status"),
            #             reason="poll_update"
            #         )
            #     
            #     # Si hay fills, procesarlos
            #     if order_status.get("fills"):
            #         for fill in order_status.get("fills", []):
            #             await self._handle_fill(
            #                 order_id,
            #                 fill.get("price"),
            #                 fill.get("size")
            #             )
            # except httpx.HTTPStatusError as e:
            #     if e.response.status_code == 429:
            #         await rate_limiter.record_violation(EndpointType.DATA_API)
            #     logger.warning(f"Error polling order status: {e}")
            # except Exception as e:
            #     logger.error(f"Error polling order status: {e}")
            
            # Placeholder: Por ahora no hacer nada
            pass
            
        except Exception as e:
            logger.error(f"Error in _poll_order_status: {e}")
        finally:
            db.close()
    
    async def _cancel_order(self, order_id: UUID, reason: str = "system_request"):
        """
        Cancela una orden en Polymarket con rate limiting.
        
        Según especificación en docs/services/execution.md
        """
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order or order.status in ("FILLED", "CANCELLED"):
                return
            
            # Adquirir permiso de rate limit
            if not await rate_limiter.wait_for_capacity(EndpointType.TRADING_ORDER, timeout=1.0):
                logger.warning(f"Rate limit timeout for cancel order {order_id}")
                return
            
            # TODO: Enviar cancelación a Polymarket API
            # try:
            #     client = await self._get_client()
            #     response = await client.delete(
            #         f"{self._config.polymarket_trading_endpoint}/{order.polymarket_order_id}"
            #     )
            #     
            #     if response.status_code == 429:
            #         await rate_limiter.record_violation(EndpointType.TRADING_ORDER)
            #         return
            #     
            #     response.raise_for_status()
            # except httpx.HTTPStatusError as e:
            #     if e.response.status_code == 429:
            #         await rate_limiter.record_violation(EndpointType.TRADING_ORDER)
            #     raise
            
            # Actualizar estado
            await self._update_order_state(order_id, "CANCELLED", reason=reason)
            
            logger.info(
                f"Order cancelled: {order_id}",
                extra={
                    "component": "execution",
                    "event": "cancelled",
                    "order_id": str(order_id),
                    "reason": reason
                }
            )
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
        finally:
            db.close()
    
    async def _cancel_all_open_orders(self, market_id: Optional[UUID] = None, reason: str = "system_pause"):
        """Cancela todas las órdenes abiertas, opcionalmente de un mercado."""
        db = SessionLocal()
        try:
            query = db.query(Order).filter(Order.status.in_(["NEW", "PARTIALLY_FILLED", "OPEN", "ACCEPTED", "SUBMITTED"]))
            if market_id:
                query = query.filter(Order.market_id == market_id)
            
            orders = query.all()
            for order in orders:
                await self._cancel_order(order.id, reason=reason)
        finally:
            db.close()
    
    async def tick(self, approved_intents: List[ApprovedOrderIntent]):
        """
        Envía/cancela órdenes basándose en approved intents.
        
        Según especificación en docs/services/execution.md
        """
        # Verificar trading circuit breaker
        try:
            import app.main as main_module
            runtime_supervisor = main_module.runtime_supervisor
            
            if runtime_supervisor.trading_circuit.is_open():
                logger.warning("Trading circuit breaker OPEN: Not sending new orders")
                return
        except (AttributeError, ImportError):
            # Si no está disponible, continuar
            pass
        
        # Verificar wallet disponible
        wallet = await wallet_service.get_active_wallet()
        if not wallet:
            logger.warning("No active wallet, cannot execute orders")
            return
        
        # Verificar sistema activo
        if not state.system_active:
            logger.warning("System not active, cancelling all open orders")
            await self._cancel_all_open_orders(reason="system_pause")
            return
        
        # Verificar latencia
        latency_status = latency_monitor.get_status()
        if latency_status == LatencyStatus.RED:
            logger.warning("Latency RED: Cancelling all open orders")
            await self._cancel_all_open_orders(reason="latency_red")
            return
        
        # Procesar nuevos intents
        for intent in approved_intents:
            try:
                # Generar client_order_id
                client_order_id = f"{intent.market_id}-{uuid4().hex[:8]}"
                
                # Obtener nonce
                nonce = self._nonce_manager.get_next_nonce()
                
                # Construir payload
                payload = self._build_order_payload(intent, nonce, client_order_id)
                
                # Firmar orden
                signed_order = self._sign_order(
                    intent,
                    payload,
                    wallet.private_key,
                    wallet.address
                )
                
                # Crear execution record
                execution_record = self._create_execution_record(signed_order, payload)
                
                # Enviar a Polymarket
                polymarket_order_id = await self._send_order_to_polymarket(
                    signed_order,
                    payload,
                    execution_record
                )
                
                # Crear orden en DB
                order = await self._create_order_in_db(intent, polymarket_order_id, signed_order)
                
                # Actualizar estado en memoria
                from app.core.state import OrderState
                order_state = OrderState()
                order_state.order_id = order.id
                order_state.market_id = order.market_id
                order_state.status = order.status
                order_state.filled_size = order.filled_size
                order_state.updated_at = order.created_at
                state.orders[order.id] = order_state
                
                # Track pending order
                self._pending_orders[str(order.id)] = order
                
                # Registrar éxito en circuit breaker
                try:
                    runtime_supervisor.record_trading_success()
                except (AttributeError, NameError):
                    pass
                
                logger.info(
                    f"Order created: {order.id}",
                    extra={
                        "component": "execution",
                        "event": "order_created",
                        "order_id": str(order.id),
                        "polymarket_order_id": polymarket_order_id,
                        "trace_id": str(intent.trace_id)
                    }
                )
                
            except Exception as e:
                logger.error(
                    f"Error executing order intent: {e}",
                    extra={
                        "component": "execution",
                        "event": "execution_error",
                        "market_id": str(intent.market_id),
                        "trace_id": str(intent.trace_id)
                    }
                )
                # Registrar fallo en circuit breaker
                try:
                    runtime_supervisor.record_trading_failure()
                except (AttributeError, NameError):
                    pass
        
        # Poll para actualizaciones de estado (simplificado - debería ser async/background)
        for order_id, order in list(self._pending_orders.items()):
            if order.status in ("FILLED", "CANCELLED", "EXPIRED", "REJECTED"):
                self._pending_orders.pop(order_id)
            else:
                await self._poll_order_status(order.id)
    
    async def close(self):
        """Cierra cliente HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None

