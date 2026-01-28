"""
Modelos de datos para Orderbook Engine.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class OrderbookLevel(BaseModel):
    """Un nivel del orderbook (precio y tamaño)."""
    model_config = ConfigDict(frozen=True)  # Inmutable
    
    price: float = Field(..., description="Precio (0.01 - 0.99)")
    size: float = Field(..., description="Tamaño en shares (CLOB size)")


class OrderbookState(BaseModel):
    """
    Estado completo del orderbook para un asset_id.
    
    Publicado en State Cache como: pm.orderbook.{asset_id}
    """
    asset_id: str
    ts_ms: int  # Timestamp del último update (ms)
    
    # BBO (Best Bid/Offer)
    best_bid_price: Optional[float] = None
    best_bid_size: Optional[float] = None
    best_ask_price: Optional[float] = None
    best_ask_size: Optional[float] = None
    
    # Spread/Mid
    spread_bps: Optional[float] = None  # Spread en basis points
    mid: Optional[float] = None  # Mid price
    
    # Top N levels (top 20)
    bids: List[OrderbookLevel] = Field(default_factory=list)  # Desc price
    asks: List[OrderbookLevel] = Field(default_factory=list)  # Asc price
    
    # Depth metrics (BUY side only - asks)
    # ⚠️ WARNING: Estos cálculos son BUY-side only (asks)
    # Si un día operas SELL/NO, necesitarás campos separados o funciones _sell()
    depth_usdc_at_25bps: float = 0.0
    depth_usdc_at_50bps: float = 0.0
    depth_usdc_at_100bps: float = 0.0
    
    # Impact metrics (BUY side only - asks)
    # ⚠️ WARNING: Estos cálculos son BUY-side only (asks)
    impact_bps_for_usdc_100: float = 0.0
    impact_bps_for_usdc_500: float = 0.0
    impact_bps_for_usdc_1000: float = 0.0
    impact_bps_for_usdc_5000: float = 0.0
    
    # Competition proxies
    concentration_top3_pct: float = 0.0  # ⚠️ BUY side only (asks)
    update_rate_hz: float = 0.0  # Updates por segundo (rolling window)
    replenishment_score: float = 0.0  # Heurística de reposición de liquidez
    
    # Health
    staleness_ms: int = 0  # Tiempo desde último update (ms)
    integrity: Dict[str, Any] = Field(
        default_factory=lambda: {
            "resync_count": 0,
            "last_snapshot_ts_ms": 0,
            "parse_errors": 0,
        }
    )
    
    model_config = ConfigDict(frozen=False)  # Permite actualizaciones



