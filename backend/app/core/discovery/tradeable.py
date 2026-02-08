"""
Definición de "tradeable" para Discovery: cuándo un market/outcome es operativo.

Un market es tradeable si:
- Está activo (no cerrado)
- Tiene tokenId / assetId válido
- Tiene precios válidos (bestBid/bestAsk u outcomePrices)
- liquidity_usd >= min_liquidity (configurable)
- stale_ms < max_staleness (ej. 2s)

Si NO cumple: mostrarlo igual, marcar tradeable=False y listar razones en tradeable_reasons.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MIN_LIQUIDITY_USD = 100.0
DEFAULT_MAX_STALENESS_MS = 2000


def is_tradeable_market(
    market_or_outcome: Dict[str, Any],
    book_data: Optional[Dict[str, Any]] = None,
    *,
    min_liquidity_usd: float = DEFAULT_MIN_LIQUIDITY_USD,
    max_staleness_ms: int = DEFAULT_MAX_STALENESS_MS,
) -> bool:
    """
    Determina si un market (o outcome con token) es tradeable.

    market_or_outcome: dict con closed, acceptingOrders, liquidity, clob_token_ids, outcome_prices, etc.
    book_data: opcional, resultado de orderbook con best_bid, best_ask, stale_ms.
    """
    reasons = tradeable_reasons(
        market_or_outcome,
        book_data,
        min_liquidity_usd=min_liquidity_usd,
        max_staleness_ms=max_staleness_ms,
    )
    return len(reasons) == 0


def tradeable_reasons(
    market_or_outcome: Dict[str, Any],
    book_data: Optional[Dict[str, Any]] = None,
    *,
    min_liquidity_usd: float = DEFAULT_MIN_LIQUIDITY_USD,
    max_staleness_ms: int = DEFAULT_MAX_STALENESS_MS,
) -> List[str]:
    """
    Lista de razones por las que NO es tradeable (vacía si sí es tradeable).
    """
    reasons: List[str] = []

    if market_or_outcome.get("closed") is True:
        reasons.append("Mercado cerrado")
    if market_or_outcome.get("acceptingOrders") is not True:
        reasons.append("No acepta órdenes")
    if market_or_outcome.get("archived") is True:
        reasons.append("Archivado")

    # Token válido (primary_yes o primary para binarios)
    clob = market_or_outcome.get("clob_token_ids") or {}
    token_id = clob.get("primary_yes") or clob.get("primary")
    if not token_id or not str(token_id).strip():
        reasons.append("Sin token CLOB")

    # Precios: o bien tenemos book (best_bid, best_ask) o outcome_prices
    has_book_prices = False
    if book_data:
        if book_data.get("best_bid") is not None or book_data.get("best_ask") is not None:
            has_book_prices = True
    has_outcome_prices = bool(market_or_outcome.get("outcome_prices"))
    if not has_book_prices and not has_outcome_prices:
        reasons.append("Sin precios (book ni outcome)")

    # Liquidez
    liq = market_or_outcome.get("liquidity") or market_or_outcome.get("liquidity_usd") or 0
    try:
        liq_f = float(liq)
    except (TypeError, ValueError):
        liq_f = 0
    if liq_f < min_liquidity_usd:
        reasons.append(f"Liquidez < ${min_liquidity_usd:.0f}")

    # Staleness (solo si tenemos book)
    if book_data and max_staleness_ms > 0:
        stale = book_data.get("stale_ms")
        if stale is not None and stale > max_staleness_ms:
            reasons.append(f"Datos de book antiguos ({stale}ms > {max_staleness_ms}ms)")

    return reasons
