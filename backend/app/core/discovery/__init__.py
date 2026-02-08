"""
Discovery module: screener de oportunidades para traders (solo lectura, sin ejecución).

- Nivel EVENTO: contenedor (partido, elección, ventana temporal).
- Nivel MARKET/OUTCOME: lo tradeable (precio, book, edge, fillability).

Redis como cache; CLOB REST para orderbook snapshot.
"""

from app.core.discovery.clob_client import fetch_orderbooks_batch
from app.core.discovery.metrics import (
    compute_market_metrics,
    compute_fillability_score,
    compute_event_score,
)
from app.core.discovery.tradeable import is_tradeable_market, tradeable_reasons

__all__ = [
    "fetch_orderbooks_batch",
    "compute_market_metrics",
    "compute_fillability_score",
    "compute_event_score",
    "is_tradeable_market",
    "tradeable_reasons",
]
