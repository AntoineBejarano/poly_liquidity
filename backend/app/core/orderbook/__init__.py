"""
Orderbook Engine - Sistema de gestión de orderbooks para Polymarket.

Responsabilidades:
- Consumir updates de orderbook desde WebSocket MARKET channel
- Mantener estado normalizado por asset_id (top-N levels)
- Calcular métricas derivadas (depth, impact, concentration)
- Publicar a State Cache para uso en Decision Graphs
- Orquestar suscripciones con ref-count
"""

from .models import OrderbookLevel, OrderbookState
from .book import OrderbookBook
from .features import (
    compute_spread_bps,
    compute_mid,
    compute_depth_usdc_at_bps_buy,
    compute_impact_bps_for_usdc_buy,
    compute_concentration_top3_pct_buy,
    compute_update_rate_hz,
)
from .ws_parser import parse_ws_book_payload
from .publisher import OrderbookPublisher
from .orchestrator import OrderbookOrchestrator
from .ws_router import OrderbookWSRouter

__all__ = [
    "OrderbookLevel",
    "OrderbookState",
    "OrderbookBook",
    "compute_spread_bps",
    "compute_mid",
    "compute_depth_usdc_at_bps_buy",
    "compute_impact_bps_for_usdc_buy",
    "compute_concentration_top3_pct_buy",
    "compute_update_rate_hz",
    "parse_ws_book_payload",
    "OrderbookPublisher",
    "OrderbookOrchestrator",
    "OrderbookWSRouter",
]

