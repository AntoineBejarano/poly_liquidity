"""
OrderbookBook - Mantiene orderbook in-memory por asset_id.

⚠️ IMPORTANTE: Usa snapshot-only (no delta) para simplicidad y estabilidad.
"""
import logging
from typing import List, Tuple, Optional
from .models import OrderbookLevel

logger = logging.getLogger(__name__)


class OrderbookBook:
    """
    Mantiene orderbook in-memory con top-N levels.
    
    ⚠️ IMPORTANTE: WS book event es snapshot del top-of-book, no delta.
    Lógica: reemplazar completamente y truncar a top-N.
    NO implementar apply_delta() por ahora (evita 80% de bugs de coherencia).
    """
    
    def __init__(self, top_n: int = 20):
        """
        Args:
            top_n: Número máximo de levels a mantener (default: 20)
        """
        self.top_n = top_n
        self.bids: List[OrderbookLevel] = []  # Desc price (highest first)
        self.asks: List[OrderbookLevel] = []  # Asc price (lowest first)
        self.last_ts_ms: int = 0
    
    def update_from_snapshot(
        self,
        bids: List[OrderbookLevel],
        asks: List[OrderbookLevel],
        ts_ms: int
    ) -> None:
        """
        Actualiza el orderbook desde un snapshot completo.
        
        ⚠️ IMPORTANTE: Reemplaza completamente el estado anterior.
        No aplica deltas, solo snapshot.
        
        Args:
            bids: Lista de bids (se ordenará desc)
            asks: Lista de asks (se ordenará asc)
            ts_ms: Timestamp del snapshot (ms)
        """
        # Ordenar: bids desc, asks asc
        self.bids = sorted(bids, key=lambda x: x.price, reverse=True)
        self.asks = sorted(asks, key=lambda x: x.price)
        
        # Truncar a top_n
        self.bids = self.bids[:self.top_n]
        self.asks = self.asks[:self.top_n]
        
        # Filtrar niveles inválidos (price <= 0 o size < 0)
        self.bids = [level for level in self.bids if level.price > 0 and level.size >= 0]
        self.asks = [level for level in self.asks if level.price > 0 and level.size >= 0]
        
        self.last_ts_ms = ts_ms
        
        logger.debug(
            f"OrderbookBook updated: {len(self.bids)} bids, {len(self.asks)} asks, ts={ts_ms}"
        )
    
    def compute_bbo(self) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        Calcula Best Bid/Offer, Mid y Spread.
        
        Returns:
            (best_bid_price, best_ask_price, mid, spread_bps)
            Si no hay bids/asks, retorna None para los valores correspondientes.
        """
        best_bid = self.bids[0] if self.bids else None
        best_ask = self.asks[0] if self.asks else None
        
        if best_bid is None or best_ask is None:
            return (None, None, None, None)
        
        best_bid_price = best_bid.price
        best_ask_price = best_ask.price
        
        # Mid price
        mid = (best_bid_price + best_ask_price) / 2.0
        
        # Spread en basis points
        spread_bps = ((best_ask_price - best_bid_price) / best_bid_price) * 10000
        
        return (best_bid_price, best_ask_price, mid, spread_bps)
    
    def get_bids(self) -> List[OrderbookLevel]:
        """Retorna lista de bids (desc price)."""
        return self.bids.copy()
    
    def get_asks(self) -> List[OrderbookLevel]:
        """Retorna lista de asks (asc price)."""
        return self.asks.copy()
    
    def get_last_ts_ms(self) -> int:
        """Retorna timestamp del último update."""
        return self.last_ts_ms


