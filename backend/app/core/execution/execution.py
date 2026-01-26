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
from app.core.config_service import config_service
from app.core.decision_trace import decision_trace_service
from app.core.risk_engine.models import ApprovedOrderIntent
from app.core.rate_limiter import rate_limiter, EndpointType
from app.core.latency_monitor import latency_monitor, LatencyStatus
from app.core.execution.models import (
    SignedOrder, ExecutionRecord, OrderStateHistory, FillRecord, ExecutionConfig
)
from app.core.execution.eip712_signer import EIP712Signer
from app.core.execution.nonce_manager import NonceManager
from app.core.execution.order_lifecycle import OrderLifecycleManager
from app.core.execution.polymarket_client_wrapper import get_polymarket_client
from app.core.execution.polymarket_websocket import get_websocket_manager
from app.database import SessionLocal
from app.models.order import Order
from app.models.trade import Trade
from app.models.position import Position
from app.models.market import Market
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
        """
        Inicializa el Execution Engine.
        
        Args:
            config: ExecutionConfig (opcional, para tests). Si es None, se carga desde ConfigService.
        """
        # #region agent log
        import json
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"execution.py:54","message":"Execution.__init__ ENTRY","data":{"has_config":config is not None},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        logger.info("Execution.__init__ - Iniciando inicialización...")
        if config is None:
            # Cargar configuración desde ConfigService
            logger.info("Execution.__init__ - [1/8] Obteniendo exec_config desde ConfigService...")
            # #region agent log
            import json
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"execution.py:63","message":"BEFORE config_service.get_execution_config","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            exec_config = config_service.get_execution_config()
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"execution.py:65","message":"AFTER config_service.get_execution_config","data":{"exec_config_keys":list(exec_config.keys()) if isinstance(exec_config,dict) else "not_dict"},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            logger.info("Execution.__init__ - [2/8] Creando ExecutionConfig...")
            config = ExecutionConfig()
            # Cargar desde settings si hay credenciales API (opcionales)
            # Si no se proporcionan, py-clob-client las genera automáticamente
            if settings.polymarket_api_key and settings.polymarket_api_secret:
                config.trading_api_keys = {
                    "api_key": settings.polymarket_api_key,
                    "api_secret": settings.polymarket_api_secret,
                    "api_passphrase": settings.polymarket_api_passphrase or ""
                }
            # Si no hay credenciales API, py-clob-client las generará automáticamente
            # usando PRIVATE_KEY y FUNDER_ADDRESS
            if settings.polymarket_trading_api_url:
                config.polymarket_trading_endpoint = settings.polymarket_trading_api_url
            if settings.chain_id:
                config.eip712_chain_id = settings.chain_id
            
            # Cargar parámetros desde ConfigService
            config.timeout = exec_config.get("http_timeout_seconds", 30.0)
            config.order_ttl_seconds = exec_config.get("order_ttl_seconds", 3600)
            config.max_retries = exec_config.get("max_retries", 3)
            config.retry_delays = [exec_config.get("retry_delay_seconds", 1.0)] * config.max_retries
            config.poll_interval_seconds = exec_config.get("fill_check_interval_seconds", 5.0)
            config.max_poll_attempts = int(exec_config.get("order_timeout_seconds", 3600.0) / config.poll_interval_seconds)
        
        logger.info("Execution.__init__ - [3/8] Asignando config y obteniendo execution_mode...")
        self._config = config
        # Obtener modo de ejecución desde ConfigService
        self._execution_mode = config_service.get_execution_mode()
        logger.info(f"Execution.__init__ - [4/8] Execution mode: {self._execution_mode}")
        self._client: Optional[httpx.AsyncClient] = None
        self._pending_orders: Dict[str, Order] = {}  # Track orders sent to Polymarket
        logger.info("Execution.__init__ - [5/8] Inicializando EIP712Signer...")
        self._eip712_signer = EIP712Signer(self._config)
        logger.info("Execution.__init__ - [6/8] Inicializando NonceManager...")
        self._nonce_manager = NonceManager(self._config)
        logger.info("Execution.__init__ - [7/8] Inicializando OrderLifecycleManager...")
        self._lifecycle_manager = OrderLifecycleManager()
        self._signed_orders: Dict[UUID, SignedOrder] = {}  # Cache de órdenes firmadas
        self._execution_records: Dict[UUID, ExecutionRecord] = {}  # Cache de registros de ejecución
        
        # WebSocket para updates en tiempo real
        logger.info("Execution.__init__ - [8/8] Configurando WebSocket...")
        # #region agent log
        import json
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"execution.py:103","message":"BEFORE _setup_websocket","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        self._websocket_manager = None
        self._use_websocket = True  # Usar WebSocket si está disponible
        self._setup_websocket()
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"execution.py:103","message":"AFTER _setup_websocket","data":{"use_websocket":self._use_websocket},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        logger.info("Execution.__init__ - Inicialización completada")
        # #region agent log
        import json
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"execution.py:135","message":"Execution.__init__ EXIT - Completado exitosamente","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
    
    def _setup_websocket(self):
        """Configura WebSocket para recibir updates en tiempo real."""
        # #region agent log
        import json
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"execution.py:105","message":"_setup_websocket ENTRY","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        logger.info("_setup_websocket - [1/5] Obteniendo websocket_manager...")
        try:
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"execution.py:108","message":"BEFORE get_websocket_manager","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            manager = get_websocket_manager()
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"execution.py:110","message":"AFTER get_websocket_manager","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            logger.info("_setup_websocket - [2/5] Obteniendo polymarket_client...")
            self._websocket_manager = manager
            
            # Obtener credenciales API desde el cliente CLOB si está disponible
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"execution.py:112","message":"BEFORE get_polymarket_client","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            polymarket_client = get_polymarket_client()
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"execution.py:114","message":"AFTER get_polymarket_client","data":{"is_available":polymarket_client.is_available()},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            logger.info(f"_setup_websocket - [3/5] polymarket_client.is_available() = {polymarket_client.is_available()}")
            if polymarket_client.is_available():
                logger.info("_setup_websocket - [4/5] Obteniendo cliente y credenciales API...")
                try:
                    # #region agent log
                    import json
                    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"execution.py:116","message":"BEFORE get_client","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
                    # #endregion
                    client = polymarket_client.get_client()
                    # #region agent log
                    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"execution.py:117","message":"BEFORE create_or_derive_api_creds","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
                    # #endregion
                    api_creds = client.create_or_derive_api_creds()
                    # #region agent log
                    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"execution.py:118","message":"AFTER create_or_derive_api_creds","data":{"has_creds":api_creds is not None},"timestamp":int(__import__('time').time()*1000)})+"\n")
                    # #endregion
                    if api_creds:
                        manager.set_auth(
                            api_key=api_creds.get("apiKey", ""),
                            secret=api_creds.get("secret", ""),
                            passphrase=api_creds.get("passphrase", "")
                        )
                        
                        # Configurar callbacks
                        manager.on_trade = self._handle_websocket_trade
                        manager.on_order_update = self._handle_websocket_order_update
                        
                        # Conectar a USER channel
                        logger.info("_setup_websocket - [5/5] Conectando a USER channel...")
                        # #region agent log
                        import json
                        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"execution.py:129","message":"BEFORE connect_user_channel","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
                        # #endregion
                        manager.connect_user_channel()
                        # #region agent log
                        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"execution.py:130","message":"AFTER connect_user_channel","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
                        # #endregion
                        logger.info("WebSocket USER channel connected for real-time order updates")
                except Exception as e:
                    logger.warning(f"Could not setup WebSocket (will use polling): {e}")
                    self._use_websocket = False
            else:
                logger.debug("WebSocket not available (no PRIVATE_KEY configured)")
                self._use_websocket = False
        except Exception as e:
            logger.warning(f"Error setting up WebSocket: {e}. Will use polling as fallback.")
            self._use_websocket = False
    
    def _find_order_by_polymarket_id(self, polymarket_order_id: str) -> Optional[Order]:
        """Busca una orden por su polymarket_order_id."""
        db = SessionLocal()
        try:
            return db.query(Order).filter(Order.polymarket_order_id == polymarket_order_id).first()
        finally:
            db.close()
    
    async def _handle_websocket_trade(self, trade_msg: Dict[str, Any]):
        """Maneja trade event desde WebSocket."""
        try:
            trade_id = trade_msg.get('id')
            taker_order_id = trade_msg.get('taker_order_id')
            status = trade_msg.get('status')
            price = float(trade_msg.get('price', '0'))
            size = float(trade_msg.get('size', '0'))
            asset_id = trade_msg.get('asset_id')
            market = trade_msg.get('market')
            
            logger.info(
                f"WebSocket trade event: {trade_id} - Status: {status}",
                extra={
                    "component": "execution",
                    "event": "websocket_trade",
                    "trade_id": trade_id,
                    "order_id": taker_order_id,
                    "status": status,
                    "price": price,
                    "size": size
                }
            )
            
            # Buscar orden por polymarket_order_id
            order = self._find_order_by_polymarket_id(taker_order_id)
            if order:
                if status == "CONFIRMED" or status == "MATCHED":
                    # Manejar fill
                    await self._handle_fill(order.id, price, size)
                elif status == "FAILED":
                    await self._update_order_state(
                        order.id,
                        "FAILED",
                        reason=f"Trade failed: {trade_id}"
                    )
            else:
                # También verificar en maker_orders
                maker_orders = trade_msg.get('maker_orders', [])
                for maker_order in maker_orders:
                    maker_order_id = maker_order.get('order_id')
                    matched_amount = float(maker_order.get('matched_amount', '0'))
                    maker_price = float(maker_order.get('price', '0'))
                    
                    order = self._find_order_by_polymarket_id(maker_order_id)
                    if order:
                        await self._handle_fill(order.id, maker_price, matched_amount)
        except Exception as e:
            logger.error(f"Error handling WebSocket trade: {e}", exc_info=True)
    
    async def _handle_websocket_order_update(self, order_msg: Dict[str, Any]):
        """Maneja order event desde WebSocket."""
        try:
            order_id = order_msg.get('id')
            event_type = order_msg.get('type')  # PLACEMENT, UPDATE, CANCELLATION
            size_matched = float(order_msg.get('size_matched', '0'))
            original_size = float(order_msg.get('original_size', '0'))
            
            logger.info(
                f"WebSocket order event: {order_id} - Type: {event_type}",
                extra={
                    "component": "execution",
                    "event": "websocket_order",
                    "order_id": order_id,
                    "event_type": event_type,
                    "size_matched": size_matched
                }
            )
            
            # Buscar orden por polymarket_order_id
            order = self._find_order_by_polymarket_id(order_id)
            if order:
                if event_type == "CANCELLATION":
                    await self._update_order_state(
                        order.id,
                        "CANCELLED",
                        reason="Cancelled via WebSocket"
                    )
                elif event_type == "UPDATE":
                    # Orden parcialmente llenada
                    await self._update_order_state(
                        order.id,
                        "PARTIALLY_FILLED",
                        filled_size=size_matched
                    )
                elif event_type == "PLACEMENT":
                    await self._update_order_state(
                        order.id,
                        "SUBMITTED",
                        reason="Order placed via WebSocket"
                    )
        except Exception as e:
            logger.error(f"Error handling WebSocket order update: {e}", exc_info=True)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Obtiene o crea cliente HTTP."""
        if self._client is None:
            # Obtener timeout desde ConfigService (hot reload)
            exec_config = config_service.get_execution_config()
            timeout = exec_config.get("http_timeout_seconds", self._config.timeout)
            self._client = httpx.AsyncClient(timeout=timeout)
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
        
        # ⚠️ IMPORTANTE: Obtener outcome desde el intent
        outcome = intent.outcome if hasattr(intent, 'outcome') else ("YES" if intent.side == "BUY" else "NO")
        
        # Obtener market_id desde el Event (para compatibilidad con payload legacy)
        market_id = self._get_market_id_from_intent(intent)
        market_id_str = str(market_id) if market_id else str(intent.event_id)
        
        return {
            "marketId": market_id_str,
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
        
        Respeta el modo de ejecución:
        - DRY_RUN: No envía, solo simula
        - PAPER: Envía pero no ejecuta realmente (simula respuesta)
        - LIVE: Envía órdenes reales
        """
        # Verificar modo de ejecución
        execution_mode = config_service.get_execution_mode()
        
        if execution_mode == "DRY_RUN":
            # DRY_RUN: No enviar, solo simular
            logger.info(
                f"DRY_RUN mode: Simulating order submission (not sending)",
                extra={
                    "component": "execution",
                    "event": "order_simulated",
                    "signed_order_id": str(signed_order.signed_order_id),
                    "trace_id": str(signed_order.trace_id),
                    "execution_mode": execution_mode
                }
            )
            execution_record.status = "SIMULATED"
            execution_record.polymarket_order_id = f"dry_run_{uuid4().hex[:8]}"
            execution_record.response_payload = {"status": "simulated", "mode": "DRY_RUN"}
            signed_order.status = "SIMULATED"
            return execution_record.polymarket_order_id
        
        execution_start = time.monotonic_ns()
        client = await self._get_client()
        
        # Obtener max_retries desde ConfigService (hot reload)
        exec_config = config_service.get_execution_config()
        max_retries = exec_config.get("max_retries", self._config.max_retries)
        
        # Retry logic con exponential backoff
        last_error = None
        for attempt in range(max_retries):
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
                
                # Enviar orden según modo de ejecución
                if execution_mode == "PAPER":
                    # PAPER: Simular envío pero no ejecutar realmente
                    await asyncio.sleep(0.1)  # Simular network + processing time
                    response_data = {
                        "order_id": f"paper_{uuid4().hex[:8]}",
                        "status": "accepted",
                        "mode": "PAPER"
                    }
                    logger.info(
                        f"PAPER mode: Simulated order submission",
                        extra={
                            "component": "execution",
                            "event": "order_paper_simulated",
                            "signed_order_id": str(signed_order.signed_order_id),
                            "trace_id": str(signed_order.trace_id),
                            "execution_mode": execution_mode
                        }
                    )
                else:
                    # LIVE: Enviar orden real
                    # TODO: Reemplazar con endpoint real de Polymarket
                    # Por ahora, simular envío
                    await asyncio.sleep(0.1)  # Simular network + processing time
                    
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
                    
                    # Simular respuesta (TODO: reemplazar con llamada real)
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
                if attempt < max_retries - 1:
                    retry_delay = exec_config.get("retry_delay_seconds", 1.0)
                    delay = retry_delay * (attempt + 1)  # Exponential backoff
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
                if attempt < max_retries - 1:
                    retry_delay = exec_config.get("retry_delay_seconds", 1.0)
                    delay = retry_delay * (attempt + 1)  # Exponential backoff
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
            f"Failed to send order to Polymarket after {max_retries} attempts",
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
            # Obtener market_id desde el Event
            market_id = self._get_market_id_from_intent(intent)
            if not market_id:
                raise ValueError(f"Cannot create order: market_id not available for event {intent.event_id}")
            
            order = Order(
                id=uuid4(),
                polymarket_order_id=polymarket_order_id,
                market_id=market_id,  # Usar market_id para compatibilidad con DB
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
    
    def _get_market_id_from_intent(self, intent: ApprovedOrderIntent) -> Optional[UUID]:
        """
        Obtiene market_id desde el OrderIntent.
        
        ⚠️ IMPORTANTE: OrderIntent ahora usa event_id, pero necesitamos market_id para cálculos de exposición y DB.
        El market_id se obtiene desde:
        1. intent.adjustments.get("market_id") (si está disponible en ApprovedOrderIntent)
        2. intent.metadata.get("market_id") (si está disponible en OrderIntent)
        3. state.events[intent.event_id].market_id (desde el Event)
        
        Returns:
            UUID del market_id o None si no se encuentra
        """
        from app.core.state import state
        
        # Intentar obtener desde adjustments (ApprovedOrderIntent)
        if hasattr(intent, 'adjustments') and isinstance(intent.adjustments, dict):
            if "market_id" in intent.adjustments:
                try:
                    market_id_str = intent.adjustments.get("market_id")
                    if isinstance(market_id_str, str):
                        return UUID(market_id_str)
                except (ValueError, TypeError):
                    pass
        
        # Intentar obtener desde metadata (OrderIntent)
        if hasattr(intent, 'metadata') and isinstance(intent.metadata, dict):
            if "market_id" in intent.metadata:
                try:
                    market_id_str = intent.metadata.get("market_id")
                    if isinstance(market_id_str, str):
                        return UUID(market_id_str)
                except (ValueError, TypeError):
                    pass
        
        # Obtener desde state.events
        if intent.event_id in state.events:
            event_state = state.events[intent.event_id]
            return event_state.market_id
        
        return None
    
    async def _get_token_id_from_event(self, event_id: UUID, outcome: str = "YES") -> Optional[str]:
        """
        Obtiene el token_id de Polymarket para un Event y outcome.
        
        ⚠️ IMPORTANTE: Ahora opera sobre Events, no Markets.
        
        Args:
            event_id: ID interno del Event
            outcome: "YES" o "NO" o "UP" o "DOWN"
        
        Returns:
            token_id de Polymarket o None si no se encuentra
        """
        from app.models.event import Event
        
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
            
            # Si no está almacenado, intentar obtener desde Polymarket API
            # Esto puede pasar si el mercado fue creado antes de implementar la extracción
            logger.warning(
                f"clob_token_ids not found for market {market_id}, fetching from API",
                extra={
                    "component": "execution",
                    "event": "token_id_fetch",
                    "market_id": str(market_id),
                    "outcome": outcome
                }
            )
            
            # Fetch desde Gamma API
            try:
                import httpx
                from app.settings import settings
                from app.core.rate_limiter import rate_limiter, EndpointType
                
                # Esperar capacidad de rate limiter
                if await rate_limiter.wait_for_capacity(EndpointType.DATA_API, timeout=2.0):
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(
                            f"{settings.polymarket_gamma_api_url}/markets/{market.polymarket_id}"
                        )
                        if response.status_code == 200:
                            market_data = response.json()
                            clob_token_ids_raw = market_data.get("clobTokenIds")
                            
                            if clob_token_ids_raw:
                                # Parsear clobTokenIds
                                if isinstance(clob_token_ids_raw, str):
                                    import json
                                    clob_token_ids = json.loads(clob_token_ids_raw)
                                elif isinstance(clob_token_ids_raw, list) and len(clob_token_ids_raw) >= 2:
                                    clob_token_ids = {
                                        "YES": str(clob_token_ids_raw[0]),
                                        "NO": str(clob_token_ids_raw[1])
                                    }
                                else:
                                    clob_token_ids = clob_token_ids_raw
                                
                                # Guardar en DB para futuras consultas
                                market.clob_token_ids = clob_token_ids
                                db.commit()
                                
                                # Retornar token_id
                                token_id = clob_token_ids.get(outcome.upper())
                                if token_id:
                                    return str(token_id)
            except Exception as api_error:
                logger.error(f"Error fetching token_id from API: {api_error}")
            
            # Fallback: retornar None (no podemos crear orden sin token_id)
            logger.error(
                f"Could not get token_id for market {market_id}, outcome {outcome}",
                extra={
                    "component": "execution",
                    "event": "token_id_not_found",
                    "market_id": str(market_id),
                    "outcome": outcome
                }
            )
            return None
        except Exception as e:
            logger.error(f"Error getting token_id for market {market_id}: {e}", exc_info=True)
            return None
        finally:
            db.close()
    
    async def _send_order_via_official_client(
        self,
        intent: ApprovedOrderIntent,
        polymarket_client
    ) -> tuple[Optional[str], Optional[SignedOrder]]:
        """
        Envía orden usando el cliente oficial de Polymarket.
        
        Args:
            intent: ApprovedOrderIntent con los detalles de la orden
            polymarket_client: Instancia de PolymarketCLOBWrapper
        
        Returns:
            Tuple de (polymarket_order_id, signed_order) o (None, None) si falla
        """
        try:
            # ⚠️ IMPORTANTE: Obtener token_id desde el Event, no desde market_id
            # OrderIntent ahora usa event_id, no market_id
            outcome = intent.outcome if hasattr(intent, 'outcome') else ("YES" if intent.side == "BUY" else "NO")
            token_id = await self._get_token_id_from_event(intent.event_id, outcome)
            if not token_id:
                logger.error(f"Could not get token_id for event {intent.event_id}, outcome {outcome}")
                return None, None
            
            # Adquirir permiso de rate limit
            if not await rate_limiter.wait_for_capacity(EndpointType.TRADING_ORDER, timeout=2.0):
                logger.warning("Rate limit timeout for trading order (official client)")
                return None, None
            
            # Crear limit order usando el cliente oficial
            execution_start = time.monotonic_ns()
            response = polymarket_client.create_limit_order(
                token_id=token_id,
                price=intent.price,
                size=intent.size,
                side=intent.side,
                order_type="GTC"
            )
            execution_end = time.monotonic_ns()
            execution_latency_ms = (execution_end - execution_start) / 1_000_000
            
            # Registrar latencia
            latency_monitor.record_execution_latency(execution_latency_ms)
            
            # Extraer order_id de la respuesta
            if isinstance(response, dict):
                polymarket_order_id = response.get("id") or response.get("order_id")
            else:
                polymarket_order_id = str(response) if response else None
            
            if not polymarket_order_id:
                logger.error(f"Could not extract order_id from response: {response}")
                return None, None
            
            # Crear SignedOrder simplificado para trazabilidad
            # El cliente oficial maneja la firma internamente, pero creamos un registro para trazabilidad
            wallet = await wallet_service.get_active_wallet()
            signed_order = SignedOrder(
                signed_order_id=uuid4(),
                intent_id=intent.trace_id,
                trace_id=intent.trace_id,
                wallet_address=wallet.address if wallet else "",
                chain_id=self._config.eip712_chain_id,
                signature="",  # El cliente oficial maneja esto internamente
                message_struct={
                    "token_id": token_id,
                    "price": intent.price,
                    "size": intent.size,
                    "side": intent.side
                },
                status="SENT"
            )
            
            self._signed_orders[signed_order.signed_order_id] = signed_order
            
            logger.info(
                f"Order submitted via official client: {polymarket_order_id}",
                extra={
                    "component": "execution",
                    "event": "order_submitted",
                    "signed_order_id": str(signed_order.signed_order_id),
                    "polymarket_order_id": polymarket_order_id,
                    "latency_ms": execution_latency_ms,
                    "trace_id": str(intent.trace_id)
                }
            )
            
            return polymarket_order_id, signed_order
            
        except Exception as e:
            logger.error(f"Error sending order via official client: {e}", exc_info=True)
            return None, None
    
    async def _handle_fill(
        self,
        order_id: UUID,
        fill_price: float,
        fill_size: float,
        onchain_event: Optional[Dict[str, Any]] = None
    ):
        """
        Maneja un fill de orden - actualiza posición y crea trade.
        
        Según especificación en docs/services/execution.md
        
        Args:
            order_id: ID interno de la orden
            fill_price: Precio del fill
            fill_size: Tamaño del fill en shares
            onchain_event: Opcional, datos del evento OrderFilled on-chain para validación
        """
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                logger.warning(f"Order {order_id} not found for fill")
                return
            
            # Si tenemos evento on-chain, validar y extraer información adicional
            if onchain_event:
                try:
                    from app.core.execution.onchain_events import parse_order_filled_event
                    parsed_event = parse_order_filled_event(onchain_event)
                    if parsed_event:
                        # Validar que el precio y tamaño coinciden
                        if abs(parsed_event.fill_price - fill_price) > 0.0001:
                            logger.warning(
                                f"Price mismatch: calculated={fill_price}, onchain={parsed_event.fill_price}"
                            )
                        if abs(parsed_event.fill_size - fill_size) > 0.0001:
                            logger.warning(
                                f"Size mismatch: calculated={fill_size}, onchain={parsed_event.fill_size}"
                            )
                        
                        # Usar valores del evento on-chain si hay discrepancia significativa
                        if abs(parsed_event.fill_price - fill_price) > 0.001:
                            fill_price = parsed_event.fill_price
                            logger.info(f"Using on-chain price: {fill_price}")
                        if abs(parsed_event.fill_size - fill_size) > 0.001:
                            fill_size = parsed_event.fill_size
                            logger.info(f"Using on-chain size: {fill_size}")
                except Exception as e:
                    logger.error(f"Error processing on-chain event: {e}")
            
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
        
        Este método se usa como fallback si WebSocket no está disponible.
        Si WebSocket está activo, este método se omite.
        
        Usa Data API para estado de orden (200 req / 10s).
        Almacena OrderStateHistory para trazabilidad.
        """
        # Si WebSocket está disponible y conectado, no hacer polling
        if self._use_websocket and self._websocket_manager:
            if self._websocket_manager.is_user_connected():
                logger.debug(f"Skipping polling for order {order_id} (WebSocket active)")
                return
        
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
        execution_latency_ms = None
        for intent in approved_intents:
            try:
                # Intentar usar cliente oficial de Polymarket si está disponible
                polymarket_client = get_polymarket_client()
                if polymarket_client.is_available():
                    # Usar cliente oficial (nuevo método)
                    polymarket_order_id, signed_order = await self._send_order_via_official_client(
                        intent,
                        polymarket_client
                    )
                    # La latencia se calcula dentro de _send_order_via_official_client
                    # Necesitamos obtenerla desde ahí o calcularla aquí
                    execution_latency_ms = None  # TODO: Obtener desde _send_order_via_official_client
                else:
                    # Usar método legacy (implementación manual)
                    logger.debug("Using legacy order execution (official client not available)")
                    market_id = self._get_market_id_from_intent(intent)
                    client_order_id = f"{market_id if market_id else intent.event_id}-{uuid4().hex[:8]}"
                    nonce = self._nonce_manager.get_next_nonce()
                    payload = self._build_order_payload(intent, nonce, client_order_id)
                    signed_order = self._sign_order(
                        intent,
                        payload,
                        wallet.private_key,
                        wallet.address
                    )
                    execution_record = self._create_execution_record(signed_order, payload)
                    polymarket_order_id = await self._send_order_to_polymarket(
                        signed_order,
                        payload,
                        execution_record
                    )
                    execution_latency_ms = execution_record.latency_ms if execution_record else None
                
                # Crear orden en DB
                if polymarket_order_id and signed_order:
                    order = await self._create_order_in_db(intent, polymarket_order_id, signed_order)
                    
                    # Log decision trace para orden enviada
                    execution_mode = config_service.get_execution_mode()
                    decision_trace_service.log_decision(
                        trace_id=intent.trace_id,
                        component="execution",
                        decision_stage="EXECUTION",
                        decision_type="entry",
                        decision="APPROVED" if execution_mode != "DRY_RUN" else "SIMULATED",
                        input_data={
                            "event_id": str(intent.event_id),
                            "market_id": str(market_id) if (market_id := self._get_market_id_from_intent(intent)) else None,
                            "outcome": intent.outcome if hasattr(intent, 'outcome') else None,
                            "price": intent.price,
                            "size": intent.size,
                            "side": intent.side,
                            "execution_mode": execution_mode,
                            "wallet_address": wallet.address if wallet else None,
                        },
                        output_data={
                            "order_id": str(order.id) if order else None,
                            "polymarket_order_id": polymarket_order_id,
                            "status": "SUBMITTED" if execution_mode != "DRY_RUN" else "SIMULATED",
                        },
                        reason="order_submitted",
                        market_id=market_id,  # Mantener para compatibilidad con decision_trace
                        latency_ms=execution_latency_ms,
                        metadata={
                            "execution_mode": execution_mode,
                            "polymarket_order_id": polymarket_order_id,
                        }
                    )
                else:
                    order = None
                    market_id = self._get_market_id_from_intent(intent)
                    logger.warning(f"Could not create order for intent event {intent.event_id} (market {market_id}): no polymarket_order_id or signed_order")
                
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
                # Obtener market_id desde el Event para logging
                market_id = self._get_market_id_from_intent(intent)
                logger.error(
                    f"Error executing order intent: {e}",
                    extra={
                        "component": "execution",
                        "event": "execution_error",
                        "event_id": str(intent.event_id),
                        "market_id": str(market_id) if market_id else None,
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
        """Cierra cliente HTTP y WebSocket."""
        if self._client:
            await self._client.aclose()
            self._client = None
        
        # Desconectar WebSocket si está conectado
        if self._websocket_manager:
            self._websocket_manager.disconnect_all()
            logger.info("WebSocket connections closed")

