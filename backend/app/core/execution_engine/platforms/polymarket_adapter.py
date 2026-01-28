"""
Polymarket Platform Adapter - Implementación de TradingPlatform para Polymarket.

Este adaptador encapsula toda la lógica específica de Polymarket:
- Firma de mensajes EIP-712
- Manejo de token_id (extraído del leg.metadata o del evento)
- Conversión de tipos de órdenes (GTC, FOK, IOC)
- Integración con py-clob-client
"""
import logging
from typing import Dict, Optional, Any, List
from decimal import Decimal
from uuid import UUID

from app.core.execution_engine.platform_base import TradingPlatform
from app.core.execution_engine.platform_models import (
    OrderResult,
    OrderStatusUpdate,
    OrderStatus,
    OrderType,
    PlatformFeatureNotSupported
)
from app.core.rate_limiter import rate_limiter, EndpointType
from app.core.latency_monitor import latency_monitor
from app.core.strategy_engine.models import PlanLeg
from app.core.execution.polymarket_client_wrapper import get_polymarket_client
from app.core.rate_limiter import rate_limiter, EndpointType
from app.core.latency_monitor import latency_monitor
from app.database import SessionLocal
from app.models.event import Event
from app.models.market import Market

logger = logging.getLogger(__name__)


class PolymarketAdapter(TradingPlatform):
    """
    Adaptador de Polymarket que implementa TradingPlatform.
    
    Encapsula toda la lógica específica de Polymarket:
    - Extracción de token_id desde leg.metadata o evento
    - Conversión de tipos de orden
    - Integración con PolymarketCLOBWrapper
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el adaptador de Polymarket.
        
        Args:
            config: Configuración opcional (por ahora usa settings por defecto)
        """
        super().__init__("polymarket", config or {})
        self._client_wrapper = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa el cliente de Polymarket."""
        try:
            self._client_wrapper = get_polymarket_client()
        except Exception as e:
            logger.warning(f"Could not initialize Polymarket client: {e}")
            self._client_wrapper = None
    
    def is_available(self) -> bool:
        """Verifica si Polymarket está disponible."""
        return self._client_wrapper is not None and self._client_wrapper.is_available()
    
    async def _get_token_id_from_leg(self, leg: PlanLeg) -> Optional[str]:
        """
        Extrae el token_id de Polymarket desde el leg.metadata o del evento.
        
        Args:
            leg: PlanLeg con la información de la orden
        
        Returns:
            token_id de Polymarket o None si no se encuentra
        """
        # Primero intentar desde leg.metadata (más eficiente)
        if leg.metadata:
            token_id = leg.metadata.get("token_id") or leg.metadata.get("polymarket_token_id")
            if token_id:
                return str(token_id)
        
        # Si no está en metadata, intentar obtener desde el evento
        # Necesitamos el event_id desde el contexto (no está en PlanLeg directamente)
        # Por ahora, retornamos None y el caller debe proporcionar el event_id
        return None
    
    async def _get_token_id_from_event(
        self,
        event_id: UUID,
        outcome: str
    ) -> Optional[str]:
        """
        Obtiene el token_id de Polymarket para un Event y outcome.
        
        Args:
            event_id: ID interno del Event
            outcome: "YES", "NO", "UP", o "DOWN"
        
        Returns:
            token_id de Polymarket o None si no se encuentra
        """
        db = SessionLocal()
        try:
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                return None
            
            # Intentar obtener token_id desde polymarket_payload del Event
            if event.polymarket_payload and isinstance(event.polymarket_payload, dict):
                clob_token_ids = event.polymarket_payload.get("clobTokenIds") or event.polymarket_payload.get("clob_token_ids")
                if clob_token_ids:
                    if isinstance(clob_token_ids, dict):
                        token_id = clob_token_ids.get(outcome.upper())
                        if token_id:
                            return str(token_id)
                    elif isinstance(clob_token_ids, list) and len(clob_token_ids) >= 2:
                        # Si es una lista, asumir [YES, NO] o [UP, DOWN]
                        if outcome.upper() in ["YES", "UP"]:
                            return str(clob_token_ids[0])
                        elif outcome.upper() in ["NO", "DOWN"]:
                            return str(clob_token_ids[1])
            
            # Si no está en el Event, intentar desde el Market
            if event.market_id:
                market = db.query(Market).filter(Market.id == event.market_id).first()
                if market and market.polymarket_payload and isinstance(market.polymarket_payload, dict):
                    clob_token_ids = market.polymarket_payload.get("clobTokenIds") or market.polymarket_payload.get("clob_token_ids")
                    if clob_token_ids:
                        if isinstance(clob_token_ids, dict):
                            token_id = clob_token_ids.get(outcome.upper())
                            if token_id:
                                return str(token_id)
                        elif isinstance(clob_token_ids, list) and len(clob_token_ids) >= 2:
                            if outcome.upper() in ["YES", "UP"]:
                                return str(clob_token_ids[0])
                            elif outcome.upper() in ["NO", "DOWN"]:
                                return str(clob_token_ids[1])
            
            logger.warning(
                f"Could not get token_id for event {event_id}, outcome {outcome}",
                extra={
                    "component": "polymarket_adapter",
                    "event": "token_id_not_found",
                    "event_id": str(event_id),
                    "outcome": outcome
                }
            )
            return None
        except Exception as e:
            logger.error(f"Error getting token_id for event {event_id}: {e}", exc_info=True)
            return None
        finally:
            db.close()
    
    def _convert_order_type(self, risk_config: Dict[str, Any]) -> str:
        """
        Convierte la configuración de riesgo a tipo de orden de Polymarket.
        
        Args:
            risk_config: Configuración de riesgo del ExecutionPlan
        
        Returns:
            Tipo de orden: "GTC", "FOK", o "IOC"
        """
        # Por defecto, usar GTC (Good Till Cancel)
        order_type = risk_config.get("order_type", "GTC")
        
        # Validar que sea un tipo soportado
        if order_type.upper() not in ["GTC", "FOK", "IOC"]:
            logger.warning(f"Unknown order type {order_type}, defaulting to GTC")
            order_type = "GTC"
        
        return order_type.upper()
    
    async def submit_order(
        self,
        leg: PlanLeg,
        risk_config: Dict[str, Any],
        trace_id: Optional[UUID] = None
    ) -> OrderResult:
        """
        Envía una orden a Polymarket.
        
        Args:
            leg: PlanLeg con la información de la orden
            risk_config: Configuración de riesgo del ExecutionPlan
            trace_id: ID de trazabilidad (opcional)
        
        Returns:
            OrderResult con el resultado de la orden
        
        Raises:
            PlatformFeatureNotSupported: Si el tipo de orden no está soportado
            RuntimeError: Si hay un error al enviar la orden
        """
        if not self.is_available():
            raise RuntimeError("Polymarket client not initialized")
        
        # Extraer token_id
        token_id = await self._get_token_id_from_leg(leg)
        
        # Si no está en metadata, necesitamos el event_id
        # Por ahora, asumimos que está en metadata o lanzamos error
        if not token_id:
            # Intentar obtener desde el contexto si está disponible
            # Esto requiere que el caller pase el event_id en metadata
            event_id = leg.metadata.get("event_id")
            if event_id:
                token_id = await self._get_token_id_from_event(UUID(event_id), leg.outcome)
        
        if not token_id:
            raise RuntimeError(
                f"Could not get token_id for leg {leg.leg_id}. "
                f"Ensure token_id is in leg.metadata or event_id is available."
            )
        
        # Validar que el tipo de orden esté soportado
        # Polymarket soporta GTC, FOK, IOC para limit orders
        # Market orders solo soportan FOK e IOC
        if risk_config.get("order_type") == "MARKET":
            # Para market orders, usar market_order_type o FOK por defecto
            order_type = risk_config.get("market_order_type", "FOK").upper()
            if order_type not in ["FOK", "IOC"]:
                raise PlatformFeatureNotSupported(
                    self.platform_name,
                    f"Market order with type {order_type}",
                    "Polymarket only supports FOK and IOC for market orders"
                )
            # Usar market order
            return await self._submit_market_order(leg, token_id, order_type, trace_id)
        else:
            # Para limit orders, convertir tipo de orden
            order_type = self._convert_order_type(risk_config)
            # Usar limit order
            return await self._submit_limit_order(leg, token_id, order_type, trace_id)
    
    async def _submit_limit_order(
        self,
        leg: PlanLeg,
        token_id: str,
        order_type: str,
        trace_id: Optional[UUID]
    ) -> OrderResult:
        """Envía una limit order a Polymarket."""
        import time
        from datetime import datetime
        
        try:
            # Adquirir permiso de rate limit
            if not await rate_limiter.wait_for_capacity(EndpointType.CLOB_POST_ORDER, timeout=5.0):
                raise RuntimeError("Rate limit exceeded for CLOB POST /order endpoint")
            
            # Medir latencia
            execution_start = time.monotonic_ns()
            
            # Crear limit order usando el cliente oficial
            response = await self._client_wrapper.create_limit_order(
                token_id=token_id,
                price=float(leg.target_price),
                size=float(leg.size),
                side=leg.side,
                order_type=order_type
            )
            
            execution_end = time.monotonic_ns()
            execution_latency_ms = (execution_end - execution_start) / 1_000_000
            
            # Registrar latencia
            latency_monitor.record_execution_latency(execution_latency_ms)
            
            # Extraer order_id de la respuesta
            if isinstance(response, dict):
                platform_order_id = response.get("id") or response.get("order_id") or response.get("orderID")
            else:
                platform_order_id = str(response) if response else None
            
            if not platform_order_id:
                raise RuntimeError(f"Could not extract order_id from response: {response}")
            
            # Crear OrderResult estandarizado
            order_result = OrderResult(
                platform_order_id=str(platform_order_id),
                status=OrderStatus.SUBMITTED,
                filled_size=Decimal("0"),
                filled_size_usdc=Decimal("0"),
                average_price=None,
                trace_id=trace_id,
                platform_metadata={
                    "token_id": token_id,
                    "order_type": order_type,
                    "latency_ms": execution_latency_ms,
                    "polymarket_response": response
                },
                submitted_at=datetime.utcnow()
            )
            
            logger.info(
                f"Limit order submitted to Polymarket: {platform_order_id}",
                extra={
                    "component": "polymarket_adapter",
                    "event": "order_submitted",
                    "platform_order_id": platform_order_id,
                    "leg_id": leg.leg_id,
                    "trace_id": str(trace_id) if trace_id else None,
                    "latency_ms": execution_latency_ms
                }
            )
            
            return order_result
            
        except Exception as e:
            logger.error(
                f"Error submitting limit order to Polymarket: {e}",
                extra={
                    "component": "polymarket_adapter",
                    "event": "order_submit_error",
                    "leg_id": leg.leg_id,
                    "trace_id": str(trace_id) if trace_id else None
                },
                exc_info=True
            )
            raise RuntimeError(f"Failed to submit order to Polymarket: {e}") from e
    
    async def _submit_market_order(
        self,
        leg: PlanLeg,
        token_id: str,
        order_type: str,
        trace_id: Optional[UUID]
    ) -> OrderResult:
        """Envía una market order a Polymarket."""
        import time
        from datetime import datetime
        
        try:
            # Adquirir permiso de rate limit
            if not await rate_limiter.wait_for_capacity(EndpointType.CLOB_POST_ORDER, timeout=5.0):
                raise RuntimeError("Rate limit exceeded for CLOB POST /order endpoint")
            
            # Medir latencia
            execution_start = time.monotonic_ns()
            
            # Crear market order usando el cliente oficial
            # Market orders usan amount (en USDC), no size (en shares)
            response = await self._client_wrapper.create_market_order(
                token_id=token_id,
                amount=float(leg.size_usdc),
                side=leg.side,
                order_type=order_type
            )
            
            execution_end = time.monotonic_ns()
            execution_latency_ms = (execution_end - execution_start) / 1_000_000
            
            # Registrar latencia
            latency_monitor.record_execution_latency(execution_latency_ms)
            
            # Extraer order_id de la respuesta
            if isinstance(response, dict):
                platform_order_id = response.get("id") or response.get("order_id") or response.get("orderID")
            else:
                platform_order_id = str(response) if response else None
            
            if not platform_order_id:
                raise RuntimeError(f"Could not extract order_id from response: {response}")
            
            # Crear OrderResult estandarizado
            order_result = OrderResult(
                platform_order_id=str(platform_order_id),
                status=OrderStatus.SUBMITTED,
                filled_size=Decimal("0"),
                filled_size_usdc=Decimal("0"),
                average_price=None,
                trace_id=trace_id,
                platform_metadata={
                    "token_id": token_id,
                    "order_type": order_type,
                    "latency_ms": execution_latency_ms,
                    "polymarket_response": response
                },
                submitted_at=datetime.utcnow()
            )
            
            logger.info(
                f"Market order submitted to Polymarket: {platform_order_id}",
                extra={
                    "component": "polymarket_adapter",
                    "event": "market_order_submitted",
                    "platform_order_id": platform_order_id,
                    "leg_id": leg.leg_id,
                    "trace_id": str(trace_id) if trace_id else None,
                    "latency_ms": execution_latency_ms
                }
            )
            
            return order_result
            
        except Exception as e:
            logger.error(
                f"Error submitting market order to Polymarket: {e}",
                extra={
                    "component": "polymarket_adapter",
                    "event": "market_order_submit_error",
                    "leg_id": leg.leg_id,
                    "trace_id": str(trace_id) if trace_id else None
                },
                exc_info=True
            )
            raise RuntimeError(f"Failed to submit market order to Polymarket: {e}") from e
    
    async def cancel_order(
        self,
        order_id: str,
        trace_id: Optional[UUID] = None
    ) -> bool:
        """
        Cancela una orden en Polymarket.
        
        Args:
            order_id: ID de la orden en Polymarket
            trace_id: ID de trazabilidad (opcional)
        
        Returns:
            True si la orden fue cancelada exitosamente, False en caso contrario
        """
        if not self.is_available():
            raise RuntimeError("Polymarket client not initialized")
        
        try:
            # Adquirir permiso de rate limit
            if not await rate_limiter.wait_for_capacity(EndpointType.CLOB_DELETE_ORDER, timeout=5.0):
                raise RuntimeError("Rate limit exceeded for CLOB DELETE /order endpoint")
            
            # Cancelar orden
            response = await self._client_wrapper.cancel_order(order_id)
            
            # Verificar si fue cancelada
            if isinstance(response, dict):
                canceled = response.get("canceled", [])
                not_canceled = response.get("not_canceled", {})
                
                if order_id in canceled or (isinstance(canceled, list) and order_id in canceled):
                    logger.info(
                        f"Order cancelled successfully: {order_id}",
                        extra={
                            "component": "polymarket_adapter",
                            "event": "order_cancelled",
                            "platform_order_id": order_id,
                            "trace_id": str(trace_id) if trace_id else None
                        }
                    )
                    return True
                elif order_id in not_canceled:
                    reason = not_canceled[order_id]
                    logger.warning(
                        f"Order could not be cancelled: {order_id}, reason: {reason}",
                        extra={
                            "component": "polymarket_adapter",
                            "event": "order_cancel_failed",
                            "platform_order_id": order_id,
                            "reason": reason,
                            "trace_id": str(trace_id) if trace_id else None
                        }
                    )
                    return False
            else:
                # Si la respuesta no es dict, asumir éxito
                logger.info(
                    f"Order cancelled: {order_id}",
                    extra={
                        "component": "polymarket_adapter",
                        "event": "order_cancelled",
                        "platform_order_id": order_id,
                        "trace_id": str(trace_id) if trace_id else None
                    }
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(
                f"Error cancelling order {order_id}: {e}",
                extra={
                    "component": "polymarket_adapter",
                    "event": "order_cancel_error",
                    "platform_order_id": order_id,
                    "trace_id": str(trace_id) if trace_id else None
                },
                exc_info=True
            )
            raise RuntimeError(f"Failed to cancel order: {e}") from e
    
    async def get_order_status(
        self,
        order_id: str,
        trace_id: Optional[UUID] = None
    ) -> OrderStatusUpdate:
        """
        Obtiene el estado actual de una orden en Polymarket.
        
        Usa get_order() para obtener información básica y get_trades() para obtener fills.
        Proporciona control absoluto sobre el estado de las órdenes.
        
        Args:
            order_id: ID de la orden en Polymarket (order_hash)
            trace_id: ID de trazabilidad (opcional)
        
        Returns:
            OrderStatusUpdate con el estado actual de la orden
        
        Raises:
            RuntimeError: Si hay un error al obtener el estado
        """
        if not self.is_available():
            raise RuntimeError("Polymarket client not initialized")
        
        import time
        from datetime import datetime, timezone
        
        try:
            # Adquirir permiso de rate limit para get_order
            if not await rate_limiter.wait_for_capacity(EndpointType.CLOB_LEDGER_DATA_ORDERS, timeout=5.0):
                raise RuntimeError("Rate limit exceeded for CLOB GET /order endpoint")
            
            # Medir latencia
            execution_start = time.monotonic_ns()
            
            # 1. Obtener información básica de la orden usando get_order()
            order_info = self._client_wrapper.get_order(order_id)
            
            if order_info is None:
                # Orden no encontrada - puede estar cerrada o nunca existió
                # Intentar obtener desde get_open_orders para verificar si está abierta
                open_orders = self._client_wrapper.get_open_orders(order_id=order_id)
                
                if not open_orders:
                    # Orden no está abierta y no se encontró - puede estar cerrada/completada
                    # Intentar obtener fills desde trades para verificar si fue ejecutada
                    # Obtener trades recientes y filtrar por order_id
                    all_recent_trades = await self._client_wrapper.get_trades()
                    trades = self._filter_trades_by_order_id(all_recent_trades, order_id)
                    
                    if trades:
                        # La orden fue ejecutada, calcular estado desde trades
                        return await self._build_status_from_trades(order_id, trades, trace_id)
                    else:
                        # Orden no encontrada en ningún lado
                        raise RuntimeError(f"Order {order_id} not found in Polymarket")
                
                # Orden está abierta, usar información de get_open_orders
                order_info = open_orders[0]
            
            execution_end = time.monotonic_ns()
            execution_latency_ms = (execution_end - execution_start) / 1_000_000
            
            # Registrar latencia
            latency_monitor.record_execution_latency(execution_latency_ms)
            
            # 2. Obtener fills relacionados con esta orden usando get_trades()
            # Obtener trades recientes y filtrar por order_id (taker_order_id o maker_orders)
            all_recent_trades = await self._client_wrapper.get_trades()
            all_trades = self._filter_trades_by_order_id(all_recent_trades, order_id)
            
            # 3. Calcular estado y fills desde order_info y trades
            status_update = self._build_status_from_order_and_trades(
                order_id=order_id,
                order_info=order_info,
                trades=all_trades,
                trace_id=trace_id,
                latency_ms=execution_latency_ms
            )
            
            logger.info(
                f"Order status retrieved: {order_id} = {status_update.status}",
                extra={
                    "component": "polymarket_adapter",
                    "event": "order_status_retrieved",
                    "platform_order_id": order_id,
                    "status": status_update.status.value,
                    "filled_size": float(status_update.filled_size),
                    "trace_id": str(trace_id) if trace_id else None,
                    "latency_ms": execution_latency_ms
                }
            )
            
            return status_update
            
        except Exception as e:
            logger.error(
                f"Error getting order status for {order_id}: {e}",
                extra={
                    "component": "polymarket_adapter",
                    "event": "order_status_error",
                    "platform_order_id": order_id,
                    "trace_id": str(trace_id) if trace_id else None
                },
                exc_info=True
            )
            raise RuntimeError(f"Failed to get order status: {e}") from e
    
    def _build_status_from_order_and_trades(
        self,
        order_id: str,
        order_info: Dict[str, Any],
        trades: List[Dict[str, Any]],
        trace_id: Optional[UUID],
        latency_ms: float
    ) -> OrderStatusUpdate:
        """
        Construye OrderStatusUpdate desde order_info y trades.
        
        Args:
            order_id: ID de la orden
            order_info: Información de la orden desde get_order() o get_open_orders()
            trades: Lista de trades relacionados con la orden
            trace_id: ID de trazabilidad
            latency_ms: Latencia de la operación
        
        Returns:
            OrderStatusUpdate con el estado completo
        """
        from decimal import Decimal
        from datetime import datetime, timezone
        
        # Extraer información básica de la orden
        # get_order() y get_open_orders() pueden tener estructuras diferentes
        # Intentar múltiples campos comunes
        order_size = Decimal(str(
            order_info.get("size") or 
            order_info.get("totalSize") or 
            order_info.get("remainingSize") or 
            order_info.get("originalSize") or
            "0"
        ))
        order_price = Decimal(str(
            order_info.get("price") or 
            order_info.get("limitPrice") or 
            order_info.get("limit_price") or
            "0"
        ))
        order_side = (order_info.get("side") or order_info.get("orderSide") or "").upper()
        
        # Estado de la orden desde Polymarket
        pm_status = (order_info.get("status") or order_info.get("orderStatus") or "").upper()
        
        # Calcular fills desde trades
        filled_size = Decimal("0")
        filled_size_usdc = Decimal("0")
        total_price_paid = Decimal("0")
        
        for trade in trades:
            # Los trades ya están filtrados por order_id, así que todos son relevantes
            trade_size = Decimal(str(trade.get("size", "0")))
            trade_price = Decimal(str(trade.get("price", "0")))
            
            filled_size += trade_size
            filled_size_usdc += trade_size * trade_price
            total_price_paid += trade_size * trade_price
        
        # Calcular precio promedio
        average_price = None
        if filled_size > 0:
            average_price = total_price_paid / filled_size
        
        # Calcular tamaño restante
        remaining_size = order_size - filled_size
        
        # Mapear estado de Polymarket a OrderStatus estandarizado
        status = self._map_polymarket_status_to_order_status(pm_status, filled_size, order_size)
        
        # Crear OrderStatusUpdate
        return OrderStatusUpdate(
            platform_order_id=order_id,
            status=status,
            filled_size=filled_size,
            filled_size_usdc=filled_size_usdc,
            average_price=average_price,
            remaining_size=remaining_size,
            trace_id=trace_id,
            platform_metadata={
                "polymarket_status": pm_status,
                "order_info": order_info,
                "trades_count": len(trades),
                "latency_ms": latency_ms,
                "order_side": order_side,
                "order_price": float(order_price)
            },
            updated_at=datetime.now(timezone.utc)
        )
    
    async def _build_status_from_trades(
        self,
        order_id: str,
        trades: List[Dict[str, Any]],
        trace_id: Optional[UUID]
    ) -> OrderStatusUpdate:
        """
        Construye OrderStatusUpdate solo desde trades (cuando la orden ya no está abierta).
        
        Usado cuando get_order() retorna None pero hay trades relacionados.
        """
        from decimal import Decimal
        from datetime import datetime, timezone
        
        filled_size = Decimal("0")
        filled_size_usdc = Decimal("0")
        total_price_paid = Decimal("0")
        
        for trade in trades:
            trade_size = Decimal(str(trade.get("size", "0")))
            trade_price = Decimal(str(trade.get("price", "0")))
            
            filled_size += trade_size
            filled_size_usdc += trade_size * trade_price
            total_price_paid += trade_size * trade_price
        
        average_price = None
        if filled_size > 0:
            average_price = total_price_paid / filled_size
        
        # Si hay trades, la orden fue ejecutada (FILLED o PARTIALLY_FILLED)
        # No podemos saber el tamaño original, así que asumimos FILLED
        status = OrderStatus.FILLED if filled_size > 0 else OrderStatus.CANCELLED
        
        return OrderStatusUpdate(
            platform_order_id=order_id,
            status=status,
            filled_size=filled_size,
            filled_size_usdc=filled_size_usdc,
            average_price=average_price,
            remaining_size=Decimal("0"),  # No sabemos el tamaño original
            trace_id=trace_id,
            platform_metadata={
                "source": "trades_only",
                "trades_count": len(trades),
                "note": "Order not found in open orders, status inferred from trades"
            },
            updated_at=datetime.now(timezone.utc)
        )
    
    def _map_polymarket_status_to_order_status(
        self,
        pm_status: str,
        filled_size: Decimal,
        order_size: Decimal
    ) -> OrderStatus:
        """
        Mapea el estado de Polymarket a OrderStatus estandarizado.
        
        Args:
            pm_status: Estado de Polymarket (OPEN, FILLED, CANCELLED, etc.)
            filled_size: Tamaño ejecutado
            order_size: Tamaño total de la orden
        
        Returns:
            OrderStatus estandarizado
        """
        pm_status_upper = pm_status.upper()
        
        # Mapeo directo de estados conocidos
        status_map = {
            "OPEN": OrderStatus.ACCEPTED,
            "FILLED": OrderStatus.FILLED,
            "CANCELLED": OrderStatus.CANCELLED,
            "CANCELED": OrderStatus.CANCELLED,  # Variante
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.EXPIRED,
            "FAILED": OrderStatus.FAILED,
        }
        
        if pm_status_upper in status_map:
            mapped_status = status_map[pm_status_upper]
            
            # Si está OPEN pero tiene fills, es PARTIALLY_FILLED
            if mapped_status == OrderStatus.ACCEPTED and filled_size > 0:
                return OrderStatus.PARTIALLY_FILLED
            
            return mapped_status
        
        # Si no está en el mapa, inferir desde fills
        if filled_size >= order_size and order_size > 0:
            return OrderStatus.FILLED
        elif filled_size > 0:
            return OrderStatus.PARTIALLY_FILLED
        elif pm_status_upper == "" or pm_status_upper == "UNKNOWN":
            # Estado desconocido, asumir PENDING
            return OrderStatus.PENDING
        else:
            # Estado desconocido pero con texto, asumir ACCEPTED
            logger.warning(f"Unknown Polymarket status '{pm_status}', defaulting to ACCEPTED")
            return OrderStatus.ACCEPTED
    
    def _filter_trades_by_order_id(
        self,
        trades: List[Dict[str, Any]],
        order_id: str
    ) -> List[Dict[str, Any]]:
        """
        Filtra trades que están relacionados con una orden específica.
        
        Un trade está relacionado si:
        - trade.taker_order_id == order_id (la orden es taker)
        - Algún trade.maker_orders[].id == order_id (la orden es maker)
        
        Args:
            trades: Lista de trades a filtrar
            order_id: ID de la orden a buscar
        
        Returns:
            Lista de trades relacionados con la orden
        """
        filtered = []
        for trade in trades:
            # Verificar si la orden es taker
            trade_taker_id = trade.get("taker_order_id")
            if trade_taker_id == order_id:
                filtered.append(trade)
                continue
            
            # Verificar si la orden es maker
            maker_orders = trade.get("maker_orders", [])
            if isinstance(maker_orders, list):
                for maker_order in maker_orders:
                    maker_id = maker_order.get("id") if isinstance(maker_order, dict) else None
                    if maker_id == order_id:
                        filtered.append(trade)
                        break
        
        return filtered
    
    async def get_balances(self) -> Dict[str, Decimal]:
        """
        Obtiene los balances disponibles en Polymarket.
        
        Returns:
            Dict con los balances por moneda
        """
        if not self.is_available():
            raise RuntimeError("Polymarket client not initialized")
        
        try:
            # Obtener balances usando el cliente
            # TODO: Implementar cuando el cliente oficial tenga soporte para balances
            raise NotImplementedError(
                "get_balances not yet implemented for Polymarket. "
                "Use the client directly or implement via API."
            )
            
        except Exception as e:
            logger.error(
                f"Error getting balances from Polymarket: {e}",
                extra={
                    "component": "polymarket_adapter",
                    "event": "balances_error"
                },
                exc_info=True
            )
            raise RuntimeError(f"Failed to get balances: {e}") from e

