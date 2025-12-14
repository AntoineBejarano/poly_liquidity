"""
WebSocket client para Polymarket CLOB API.

Proporciona conexiones WebSocket para recibir updates en tiempo real sobre:
- User Channel: Órdenes y trades del usuario
- Market Channel: Orderbooks y cambios de precio de mercados
"""
import logging
import json
import asyncio
import threading
import time
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    """Tipos de canales WebSocket disponibles."""
    USER = "user"
    MARKET = "market"


@dataclass
class WebSocketAuth:
    """Credenciales de autenticación para WebSocket."""
    api_key: str
    secret: str
    passphrase: str


class PolymarketWebSocketClient:
    """
    Cliente WebSocket para Polymarket CLOB API.
    
    Soporta dos canales:
    - USER: Updates sobre órdenes y trades del usuario autenticado
    - MARKET: Updates sobre orderbooks y precios de mercados públicos
    """
    
    WSS_URL = "wss://ws-subscriptions-clob.polymarket.com"
    PING_INTERVAL = 10  # segundos
    
    def __init__(
        self,
        channel_type: ChannelType,
        auth: Optional[WebSocketAuth] = None,
        asset_ids: Optional[List[str]] = None,
        market_ids: Optional[List[str]] = None,
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_close: Optional[Callable[[], None]] = None
    ):
        """
        Inicializa el cliente WebSocket.
        
        Args:
            channel_type: Tipo de canal (USER o MARKET)
            auth: Credenciales de autenticación (requerido para USER channel)
            asset_ids: Lista de asset IDs (token IDs) para MARKET channel
            market_ids: Lista de market IDs (condition IDs) para USER channel
            on_message: Callback para mensajes recibidos
            on_error: Callback para errores
            on_close: Callback para cierre de conexión
        """
        self.channel_type = channel_type
        self.auth = auth
        self.asset_ids = asset_ids or []
        self.market_ids = market_ids or []
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        
        self.ws = None
        self.is_connected = False
        self.ping_thread = None
        self._stop_ping = threading.Event()
    
    def _build_url(self) -> str:
        """Construye la URL del WebSocket."""
        return f"{self.WSS_URL}/ws/{self.channel_type.value}"
    
    def _on_open(self, ws):
        """Callback cuando se abre la conexión."""
        logger.info(f"WebSocket connection opened for {self.channel_type.value} channel")
        self.is_connected = True
        
        # Enviar mensaje de suscripción
        subscription_msg = self._build_subscription_message()
        ws.send(json.dumps(subscription_msg))
        logger.debug(f"Sent subscription: {subscription_msg}")
        
        # Iniciar thread de ping
        self._stop_ping.clear()
        self.ping_thread = threading.Thread(target=self._ping_loop, args=(ws,), daemon=True)
        self.ping_thread.start()
    
    def _on_message(self, ws, message):
        """Callback cuando se recibe un mensaje."""
        try:
            # Ignorar mensajes de ping/pong
            if message == "PING" or message == "PONG":
                return
            
            data = json.loads(message)
            logger.debug(f"Received WebSocket message: {data.get('event_type', 'unknown')}")
            
            if self.on_message:
                self.on_message(data)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
            if self.on_error:
                self.on_error(e)
    
    def _on_error(self, ws, error):
        """Callback cuando ocurre un error."""
        logger.error(f"WebSocket error: {error}")
        if self.on_error:
            self.on_error(error)
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Callback cuando se cierra la conexión."""
        logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        self.is_connected = False
        self._stop_ping.set()
        
        if self.on_close:
            self.on_close()
    
    def _build_subscription_message(self) -> Dict[str, Any]:
        """Construye el mensaje de suscripción según el tipo de canal."""
        if self.channel_type == ChannelType.USER:
            if not self.auth:
                raise ValueError("Auth required for USER channel")
            
            return {
                "type": ChannelType.USER.value,
                "markets": self.market_ids,
                "auth": {
                    "apiKey": self.auth.api_key,
                    "secret": self.auth.secret,
                    "passphrase": self.auth.passphrase
                }
            }
        elif self.channel_type == ChannelType.MARKET:
            return {
                "type": ChannelType.MARKET.value,
                "assets_ids": self.asset_ids
            }
        else:
            raise ValueError(f"Unknown channel type: {self.channel_type}")
    
    def _ping_loop(self, ws):
        """Loop para enviar PING periódicamente."""
        while not self._stop_ping.is_set():
            try:
                ws.send("PING")
                self._stop_ping.wait(self.PING_INTERVAL)
            except Exception as e:
                logger.error(f"Error in ping loop: {e}")
                break
    
    def connect(self, max_retries: int = 5, retry_delay: float = 5.0):
        # #region agent log
        import json
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:167","message":"PolymarketWebSocketClient.connect ENTRY","data":{"channel_type":self.channel_type.value},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        """
        Conecta al WebSocket con reconexión automática.
        
        Args:
            max_retries: Número máximo de intentos de reconexión (0 = infinito)
            retry_delay: Segundos a esperar entre intentos de reconexión
        """
        try:
            import websocket
            
            url = self._build_url()
            logger.info(f"Connecting to WebSocket: {url}")
            
            self.ws = websocket.WebSocketApp(
                url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Ejecutar en un thread separado para no bloquear
            logger.info("connect - Creando thread para WebSocket...")
            # #region agent log
            import json
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:195","message":"BEFORE Thread creation","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            ws_thread = threading.Thread(
                target=self._run_with_reconnect,
                args=(max_retries, retry_delay),
                daemon=True
            )
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:201","message":"BEFORE ws_thread.start()","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            ws_thread.start()
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:202","message":"AFTER ws_thread.start()","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            logger.info("connect - Thread iniciado, método completado")
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:204","message":"PolymarketWebSocketClient.connect EXIT","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            
        except ImportError:
            logger.error("websocket-client not installed. Install with: pip install websocket-client")
            raise
        except Exception as e:
            logger.error(f"Error connecting WebSocket: {e}")
            # #region agent log
            import json
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:210","message":"EXCEPTION en connect","data":{"error":str(e)},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            raise
    
    def _run_with_reconnect(self, max_retries: int, retry_delay: float):
        """Ejecuta WebSocket con reconexión automática."""
        # #region agent log
        import json
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:204","message":"_run_with_reconnect ENTRY","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        retries = 0
        while True:
            try:
                # #region agent log
                with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:209","message":"BEFORE ws.run_forever()","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
                # #endregion
                self.ws.run_forever()
                # #region agent log
                with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:211","message":"AFTER ws.run_forever()","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
                # #endregion
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
            
            # Si se cierra normalmente o está desconectado explícitamente, no reintentar
            if not self.is_connected or self._stop_ping.is_set():
                break
            
            # Verificar límite de reintentos
            if max_retries > 0:
                retries += 1
                if retries > max_retries:
                    logger.error(f"Max retries ({max_retries}) reached for WebSocket connection")
                    break
            
            # Esperar antes de reconectar
            logger.info(f"Attempting to reconnect WebSocket in {retry_delay}s... (retry {retries})")
            time.sleep(retry_delay)
            
            # Reconectar
            try:
                import websocket
                url = self._build_url()
                self.ws = websocket.WebSocketApp(
                    url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
            except Exception as e:
                logger.error(f"Error reconnecting WebSocket: {e}")
                time.sleep(retry_delay)
    
    def disconnect(self):
        """Desconecta del WebSocket."""
        if self.ws:
            self._stop_ping.set()
            self.ws.close()
            self.is_connected = False
            logger.info("WebSocket disconnected")
    
    def send_message(self, message: Dict[str, Any]):
        """Envía un mensaje al WebSocket."""
        if not self.is_connected or not self.ws:
            raise RuntimeError("WebSocket not connected")
        
        self.ws.send(json.dumps(message))


class PolymarketWebSocketManager:
    """
    Gestor para múltiples conexiones WebSocket de Polymarket.
    
    Facilita la gestión de conexiones USER y MARKET, con callbacks
    estructurados para integrar con el Execution Engine y otros módulos.
    """
    
    def __init__(self):
        # #region agent log
        import json
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:309","message":"PolymarketWebSocketManager.__init__ ENTRY","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        self.user_client: Optional[PolymarketWebSocketClient] = None
        self.market_clients: Dict[str, PolymarketWebSocketClient] = {}  # market_id -> client
        self.auth: Optional[WebSocketAuth] = None
        
        # Callbacks
        self.on_trade: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_order_update: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_book_update: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_price_change: Optional[Callable[[Dict[str, Any]], None]] = None
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:318","message":"PolymarketWebSocketManager.__init__ EXIT","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
    
    def set_auth(self, api_key: str, secret: str, passphrase: str):
        """Configura credenciales de autenticación."""
        self.auth = WebSocketAuth(
            api_key=api_key,
            secret=secret,
            passphrase=passphrase
        )
    
    def _handle_user_message(self, message: Dict[str, Any]):
        """Maneja mensajes del USER channel."""
        event_type = message.get("event_type")
        
        if event_type == "trade":
            logger.debug(f"Trade event: {message.get('id')}")
            if self.on_trade:
                self.on_trade(message)
        elif event_type == "order":
            order_type = message.get("type")  # PLACEMENT, UPDATE, CANCELLATION
            logger.debug(f"Order event: {order_type} - {message.get('id')}")
            if self.on_order_update:
                self.on_order_update(message)
        else:
            logger.debug(f"Unknown user event type: {event_type}")
    
    def _handle_market_message(self, message: Dict[str, Any]):
        """Maneja mensajes del MARKET channel."""
        event_type = message.get("event_type")
        
        if event_type == "book":
            logger.debug(f"Book update: {message.get('market')}")
            if self.on_book_update:
                self.on_book_update(message)
        elif event_type == "price_change":
            logger.debug(f"Price change: {message.get('market')}")
            if self.on_price_change:
                self.on_price_change(message)
        elif event_type == "tick_size_change":
            logger.debug(f"Tick size change: {message.get('market')}")
        elif event_type == "last_trade_price":
            logger.debug(f"Last trade price: {message.get('asset_id')}")
        else:
            logger.debug(f"Unknown market event type: {event_type}")
    
    def connect_user_channel(self, market_ids: Optional[List[str]] = None):
        """
        Conecta al USER channel para recibir updates de órdenes y trades.
        
        Args:
            market_ids: Lista de market IDs para filtrar (None = todos)
        """
        # #region agent log
        import json
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:321","message":"connect_user_channel ENTRY","data":{"has_auth":self.auth is not None},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        if not self.auth:
            raise ValueError("Auth required for USER channel. Call set_auth() first.")
        
        if self.user_client and self.user_client.is_connected:
            logger.warning("USER channel already connected")
            return
        
        logger.info("connect_user_channel - Creando PolymarketWebSocketClient...")
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:335","message":"BEFORE PolymarketWebSocketClient","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        self.user_client = PolymarketWebSocketClient(
            channel_type=ChannelType.USER,
            auth=self.auth,
            market_ids=market_ids or [],
            on_message=self._handle_user_message,
            on_error=lambda e: logger.error(f"USER channel error: {e}"),
            on_close=lambda: logger.info("USER channel closed")
        )
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:344","message":"AFTER PolymarketWebSocketClient","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        
        logger.info("connect_user_channel - Llamando a connect()...")
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:344","message":"BEFORE user_client.connect()","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        self.user_client.connect()
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:345","message":"AFTER user_client.connect()","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        logger.info("USER channel connected")
    
    def connect_market_channel(
        self,
        asset_ids: List[str],
        market_id: Optional[str] = None,
        max_retries: int = 0
    ):
        """
        Conecta al MARKET channel para recibir updates de orderbooks y precios.
        
        Args:
            asset_ids: Lista de asset IDs (token IDs) a suscribir
            market_id: ID del mercado (opcional, para identificación)
            max_retries: Número máximo de intentos de reconexión (0 = infinito)
        """
        key = market_id or asset_ids[0] if asset_ids else "default"
        
        if key in self.market_clients and self.market_clients[key].is_connected:
            logger.warning(f"MARKET channel for {key} already connected")
            return
        
        client = PolymarketWebSocketClient(
            channel_type=ChannelType.MARKET,
            asset_ids=asset_ids,
            on_message=self._handle_market_message,
            on_error=lambda e: logger.error(f"MARKET channel error for {key}: {e}"),
            on_close=lambda: logger.info(f"MARKET channel closed for {key}")
        )
        
        client.connect(max_retries=max_retries, retry_delay=5.0)
        self.market_clients[key] = client
        logger.info(f"MARKET channel connected for {key}")
    
    def disconnect_all(self):
        """Desconecta todos los canales."""
        if self.user_client:
            self.user_client.disconnect()
            self.user_client = None
        
        for client in self.market_clients.values():
            client.disconnect()
        self.market_clients.clear()
        
        logger.info("All WebSocket channels disconnected")
    
    def is_user_connected(self) -> bool:
        """Verifica si el USER channel está conectado."""
        return self.user_client is not None and self.user_client.is_connected
    
    def is_market_connected(self, market_id: Optional[str] = None) -> bool:
        """Verifica si el MARKET channel está conectado."""
        if market_id:
            return market_id in self.market_clients and self.market_clients[market_id].is_connected
        return any(client.is_connected for client in self.market_clients.values())


# Instancia global del manager
_websocket_manager: Optional[PolymarketWebSocketManager] = None


def get_websocket_manager() -> PolymarketWebSocketManager:
    """
    Obtiene la instancia global del WebSocket manager.
    
    Returns:
        Instancia de PolymarketWebSocketManager
    """
    global _websocket_manager
    # #region agent log
    import json
    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:406","message":"get_websocket_manager ENTRY","data":{"instance_exists":_websocket_manager is not None},"timestamp":int(__import__('time').time()*1000)})+"\n")
    # #endregion
    if _websocket_manager is None:
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:415","message":"BEFORE PolymarketWebSocketManager()","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        _websocket_manager = PolymarketWebSocketManager()
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:416","message":"AFTER PolymarketWebSocketManager()","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
    # #region agent log
    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_websocket.py:417","message":"get_websocket_manager EXIT","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
    # #endregion
    return _websocket_manager

