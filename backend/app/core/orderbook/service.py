"""
OrderbookService - Servicio singleton que inicializa y gestiona todo el sistema de orderbook.

Conecta:
- OrderbookOrchestrator (ref-count)
- OrderbookWSRouter (manejo de mensajes WS)
- OrderbookPublisher (publicación a State Cache)
- PolymarketWebSocketManager (conexión WS MARKET)
"""
import logging
import asyncio
from typing import Optional, Dict, Any
from app.core.orderbook.orchestrator import OrderbookOrchestrator
from app.core.orderbook.ws_router import OrderbookWSRouter
from app.core.orderbook.publisher import OrderbookPublisher
from app.core.strategy_engine.state_cache_service import StateCacheService
from app.core.execution.polymarket_websocket import get_websocket_manager
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# Instancia global del servicio
_orderbook_service: Optional['OrderbookService'] = None


class OrderbookService:
    """
    Servicio singleton que gestiona todo el sistema de orderbook.
    
    Responsabilidades:
    - Inicializar orchestrator, router, publisher
    - Conectar WS callbacks con router
    - Gestionar suscripciones con ref-count
    - Exponer API para suscribir/desuscribir asset_ids
    """
    
    def __init__(self, state_cache_service: Optional[StateCacheService] = None):
        """
        Inicializa el servicio de orderbook.
        
        Args:
            state_cache_service: Servicio de State Cache (opcional, se crea si no se proporciona)
        """
        # Crear State Cache Service si no se proporciona
        if state_cache_service is None:
            db = SessionLocal()
            state_cache_service = StateCacheService(db)
        
        self.state_cache_service = state_cache_service
        
        # Inicializar componentes
        self.orchestrator = OrderbookOrchestrator(
            on_subscribe=self._on_subscribe_asset,
            on_unsubscribe=self._on_unsubscribe_asset
        )
        
        self.publisher = OrderbookPublisher(self.state_cache_service)
        
        self.router = OrderbookWSRouter(
            orchestrator=self.orchestrator,
            publisher=self.publisher
        )
        
        # WebSocket Manager
        self.ws_manager = get_websocket_manager()
        
        # Conectar callbacks WS con router
        self.ws_manager.on_book_update = self._handle_ws_book_update
        
        # Track de asset_ids suscritos en WS
        self._ws_subscribed_assets: set = set()
        
        logger.info("OrderbookService initialized")
    
    def _on_subscribe_asset(self, asset_id: str) -> None:
        """
        Callback cuando ref_count pasa 0→1 (primer suscriptor).
        
        Suscribe el asset_id al WebSocket MARKET channel.
        """
        logger.info(f"First subscription to asset_id={asset_id}, subscribing to WS MARKET")
        
        # Si ya está suscrito, no hacer nada
        if asset_id in self._ws_subscribed_assets:
            logger.debug(f"Asset {asset_id} already subscribed to WS")
            return
        
        # Obtener asset_ids actualmente suscritos
        current_assets = list(self._ws_subscribed_assets)
        current_assets.append(asset_id)
        
        # Si no hay conexión WS MARKET, crear una nueva
        # Si ya hay conexión, necesitamos agregar el nuevo asset_id
        # Por ahora, creamos una conexión por asset_id (puede optimizarse después)
        try:
            self.ws_manager.connect_market_channel(
                asset_ids=[asset_id],
                market_id=None,
                max_retries=0  # Reconexión infinita
            )
            self._ws_subscribed_assets.add(asset_id)
            logger.info(f"Subscribed asset_id={asset_id} to WS MARKET channel")
        except Exception as e:
            logger.error(f"Error subscribing asset_id={asset_id} to WS: {e}", exc_info=True)
    
    def _on_unsubscribe_asset(self, asset_id: str) -> None:
        """
        Callback cuando ref_count pasa 1→0 (último suscriptor).
        
        Desuscribe el asset_id del WebSocket MARKET channel.
        """
        logger.info(f"Last unsubscribe from asset_id={asset_id}, unsubscribing from WS MARKET")
        
        # Remover de tracking
        if asset_id in self._ws_subscribed_assets:
            self._ws_subscribed_assets.remove(asset_id)
        
        # Nota: Desconectar completamente el WS puede ser agresivo si hay otros asset_ids
        # Por ahora, solo removemos del tracking. La desconexión real se puede hacer
        # cuando no hay más asset_ids suscritos (optimización futura)
        logger.debug(f"Unsubscribed asset_id={asset_id} from WS MARKET channel")
    
    async def _handle_ws_book_update_async(self, book_msg: Dict[str, Any]) -> None:
        """
        Handler async para mensajes WS de book update.
        
        Conecta el mensaje WS con el router.
        """
        try:
            await self.router.handle_book_update(book_msg)
        except Exception as e:
            logger.error(
                f"Error handling WS book update: {e}",
                exc_info=True,
                extra={
                    "component": "orderbook",
                    "event": "ws_book_update_error",
                    "book_msg": book_msg
                }
            )
    
    def _handle_ws_book_update(self, book_msg: Dict[str, Any]) -> None:
        """
        Handler sync para mensajes WS de book update.
        
        Conecta el mensaje WS con el router (que es async).
        """
        # El router.handle_book_update es async, pero el callback WS es sync
        # Necesitamos ejecutarlo en un event loop
        try:
            # Obtener o crear event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Ejecutar async handler
            if loop.is_running():
                # Si el loop ya está corriendo, crear una task
                asyncio.create_task(self._handle_ws_book_update_async(book_msg))
            else:
                # Si no está corriendo, ejecutar directamente
                loop.run_until_complete(self._handle_ws_book_update_async(book_msg))
        except Exception as e:
            logger.error(
                f"Error handling WS book update: {e}",
                exc_info=True,
                extra={
                    "component": "orderbook",
                    "event": "ws_book_update_error",
                    "book_msg": book_msg
                }
            )
    
    def subscribe(self, asset_id: str, owner_key: str) -> None:
        """
        Suscribe un owner a un asset_id.
        
        Args:
            asset_id: Asset ID (token ID)
            owner_key: Identificador del owner (ej: "strategy_1")
        """
        self.orchestrator.subscribe(asset_id, owner_key)
    
    def unsubscribe(self, asset_id: str, owner_key: str) -> None:
        """
        Desuscribe un owner de un asset_id.
        
        Args:
            asset_id: Asset ID (token ID)
            owner_key: Identificador del owner
        """
        self.orchestrator.unsubscribe(asset_id, owner_key)
    
    def get_ref_count(self) -> Dict[str, int]:
        """
        Obtiene el ref-count actual de todos los asset_ids.
        
        Returns:
            Dict[asset_id, count]
        """
        return self.orchestrator.ref_count
    
    def get_book(self, asset_id: str):
        """
        Obtiene el OrderbookBook para un asset_id.
        
        Args:
            asset_id: Asset ID
        
        Returns:
            OrderbookBook o None si no existe
        """
        return self.orchestrator.get_book(asset_id)
    
    def get_orderbook_state(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el OrderbookState desde State Cache.
        
        Args:
            asset_id: Asset ID
        
        Returns:
            OrderbookState dict o None si no existe
        """
        cache_key = f"pm.orderbook.{asset_id}"
        # State Cache es async, pero este método es sync
        # Por ahora retornamos None, el endpoint async lo manejará
        return None


def get_orderbook_service(state_cache_service: Optional[StateCacheService] = None) -> OrderbookService:
    """
    Obtiene la instancia global del OrderbookService (singleton).
    
    Args:
        state_cache_service: Servicio de State Cache (opcional, solo en primera inicialización)
    
    Returns:
        Instancia de OrderbookService
    """
    global _orderbook_service
    
    if _orderbook_service is None:
        _orderbook_service = OrderbookService(state_cache_service)
        logger.info("OrderbookService singleton created")
    
    return _orderbook_service

