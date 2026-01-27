"""
OrderbookOrchestrator - Orquesta suscripciones y gestión de orderbooks.

Gestiona ref-count mejorado con owners set para evitar leaks.
"""
import logging
from typing import Dict, Set, Optional, Callable
from .book import OrderbookBook
from .models import OrderbookLevel

logger = logging.getLogger(__name__)


class OrderbookOrchestrator:
    """
    Orquestador de orderbooks con ref-count mejorado.
    
    Estructura interna:
    - owners: Dict[str, Set[str]] - asset_id -> set of owner_keys
    - ref_count: Dict[str, int] - asset_id -> count (derivado de len(owners))
    
    Reglas:
    - ref_count[asset_id] = len(owners[asset_id]) (siempre derivado, nunca manual)
    - subscribe(asset_id, owner) → añadir a owners[asset_id] (idempotente)
    - unsubscribe(asset_id, owner) → remover de owners[asset_id] (validar existencia)
    - Si ref_count pasa 0→1: suscribir WS
    - Si ref_count pasa 1→0: desuscribir WS
    - Nunca dejar ref_count negativo (validar antes de decrementar)
    - Double-subscribe mismo owner: ignorar (idempotente)
    """
    
    def __init__(
        self,
        on_subscribe: Optional[Callable[[str], None]] = None,
        on_unsubscribe: Optional[Callable[[str], None]] = None
    ):
        """
        Args:
            on_subscribe: Callback cuando ref_count pasa 0→1 (suscribir WS)
            on_unsubscribe: Callback cuando ref_count pasa 1→0 (desuscribir WS)
        """
        self.owners: Dict[str, Set[str]] = {}  # asset_id -> set of owner_keys
        self.books: Dict[str, OrderbookBook] = {}  # asset_id -> OrderbookBook
        self.on_subscribe = on_subscribe
        self.on_unsubscribe = on_unsubscribe
    
    @property
    def ref_count(self) -> Dict[str, int]:
        """
        Ref-count derivado de owners (siempre derivado, nunca manual).
        
        Returns:
            Dict[asset_id, count] donde count = len(owners[asset_id])
        """
        return {asset_id: len(owners_set) for asset_id, owners_set in self.owners.items()}
    
    def subscribe(self, asset_id: str, owner_key: str) -> None:
        """
        Suscribe un owner a un asset_id.
        
        Si es el primer owner (ref_count pasa 0→1), llama on_subscribe.
        Idempotente: double-subscribe del mismo owner se ignora.
        
        Args:
            asset_id: Asset ID (token ID)
            owner_key: Identificador del owner (ej: "strategy_1")
        """
        if asset_id not in self.owners:
            self.owners[asset_id] = set()
            self.books[asset_id] = OrderbookBook()
        
        old_count = len(self.owners[asset_id])
        self.owners[asset_id].add(owner_key)
        new_count = len(self.owners[asset_id])
        
        # Si ref_count pasa 0→1, suscribir WS
        if old_count == 0 and new_count == 1:
            logger.info(f"First subscription to asset_id={asset_id}, subscribing WS")
            if self.on_subscribe:
                self.on_subscribe(asset_id)
        
        logger.debug(
            f"Subscribed owner={owner_key} to asset_id={asset_id}, ref_count={new_count}",
            extra={
                "component": "orderbook",
                "event": "subscribe",
                "asset_id": asset_id,
                "owner_key": owner_key,
                "ref_count": new_count
            }
        )
    
    def unsubscribe(self, asset_id: str, owner_key: str) -> None:
        """
        Desuscribe un owner de un asset_id.
        
        Si es el último owner (ref_count pasa 1→0), llama on_unsubscribe.
        Maneja gracefully: unsubscribe sin subscribe previo no crashea.
        
        Args:
            asset_id: Asset ID (token ID)
            owner_key: Identificador del owner (ej: "strategy_1")
        """
        if asset_id not in self.owners:
            logger.warning(
                f"Unsubscribe called for asset_id={asset_id} without prior subscription",
                extra={
                    "component": "orderbook",
                    "event": "unsubscribe_warning",
                    "asset_id": asset_id,
                    "owner_key": owner_key
                }
            )
            return
        
        if owner_key not in self.owners[asset_id]:
            logger.warning(
                f"Unsubscribe called for owner={owner_key} not in owners for asset_id={asset_id}",
                extra={
                    "component": "orderbook",
                    "event": "unsubscribe_warning",
                    "asset_id": asset_id,
                    "owner_key": owner_key
                }
            )
            return
        
        old_count = len(self.owners[asset_id])
        self.owners[asset_id].remove(owner_key)
        new_count = len(self.owners[asset_id])
        
        # Si ref_count pasa 1→0, desuscribir WS
        if old_count == 1 and new_count == 0:
            logger.info(f"Last subscription to asset_id={asset_id}, unsubscribing WS")
            if self.on_unsubscribe:
                self.on_unsubscribe(asset_id)
            
            # Limpiar recursos
            del self.owners[asset_id]
            del self.books[asset_id]
        
        logger.debug(
            f"Unsubscribed owner={owner_key} from asset_id={asset_id}, ref_count={new_count}",
            extra={
                "component": "orderbook",
                "event": "unsubscribe",
                "asset_id": asset_id,
                "owner_key": owner_key,
                "ref_count": new_count
            }
        )
    
    def ingest_book_msg(
        self,
        asset_id: str,
        bids: list[OrderbookLevel],
        asks: list[OrderbookLevel],
        ts_ms: int
    ) -> None:
        """
        Ingresa un mensaje de book update.
        
        Args:
            asset_id: Asset ID (token ID)
            bids: Lista de bids (se ordenará desc)
            asks: Lista de asks (se ordenará asc)
            ts_ms: Timestamp del update (ms)
        """
        if asset_id not in self.books:
            logger.warning(
                f"Received book update for unsubscribed asset_id={asset_id}, ignoring",
                extra={
                    "component": "orderbook",
                    "event": "ingest_unsubscribed",
                    "asset_id": asset_id
                }
            )
            return
        
        book = self.books[asset_id]
        book.update_from_snapshot(bids, asks, ts_ms)
        
        logger.debug(
            f"Ingested book update for asset_id={asset_id}, ts={ts_ms}",
            extra={
                "component": "orderbook",
                "event": "ingest_book",
                "asset_id": asset_id,
                "ts_ms": ts_ms
            }
        )
    
    def get_book(self, asset_id: str) -> Optional[OrderbookBook]:
        """
        Obtiene OrderbookBook para un asset_id.
        
        Args:
            asset_id: Asset ID (token ID)
        
        Returns:
            OrderbookBook o None si no está suscrito
        """
        return self.books.get(asset_id)
    
    def get_subscribed_asset_ids(self) -> Set[str]:
        """
        Retorna set de asset_ids con ref_count > 0.
        
        Returns:
            Set de asset_ids suscritos
        """
        return set(self.owners.keys())



