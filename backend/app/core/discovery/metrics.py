"""
Discovery metrics: edge, spread, depth, slippage, fillability (valor añadido vs Polymarket).

Fórmulas:
- mid_price = (best_bid + best_ask) / 2
- fair_price = mid + k * imbalance, imbalance = (bidSize - askSize) / (bidSize + askSize)
- edge_cents = (fair_price - best_ask) * 100  [para compra; positivo = oportunidad]
- spread_bps = (best_ask - best_bid) / mid * 10_000
- depth_50bps_usd = USD disponible dentro de ±50 bps del mid
- slippage_1k_cents = coste estimado de ejecutar $1k vs mid (walking the book)
- fillability_score = heurístico 0-100 (penaliza spread, slippage, staleness)
- event_score = edge_cents * (fillability/100) * log(1 + liquidity_usd)
"""
import math
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Configuración por defecto (se puede sobreescribir desde config)
FAIR_PRICE_K = 0.02  # peso del imbalance en fair
DEPTH_BPS = 50
SLIPPAGE_NOTIONAL_USD = 1000.0
MAX_STALENESS_MS = 5000  # 5s para fillability penalty


def _parse_level(level: Any) -> tuple[float, float]:
    if not isinstance(level, dict):
        return 0.0, 0.0
    try:
        p = level.get("price") or level.get("price_float")
        s = level.get("size") or level.get("size_float")
        return float(p or 0), float(s or 0)
    except (TypeError, ValueError):
        return 0.0, 0.0


def mid_price(best_bid: Optional[float], best_ask: Optional[float]) -> Optional[float]:
    if best_bid is not None and best_ask is not None and best_bid > 0:
        return (best_bid + best_ask) / 2.0
    return None


def fair_price_indicative(
    best_bid: Optional[float],
    best_ask: Optional[float],
    bid_size: float,
    ask_size: float,
    k: float = FAIR_PRICE_K,
) -> Optional[float]:
    """Fair = mid + k * imbalance. Indicative only."""
    mid = mid_price(best_bid, best_ask)
    if mid is None:
        return None
    total = bid_size + ask_size
    if total <= 0:
        return mid
    imbalance = (bid_size - ask_size) / total
    return mid + k * imbalance


def edge_cents(fair: Optional[float], best_ask: Optional[float]) -> Optional[float]:
    """Edge en céntimos: (fair - best_ask) * 100. Positivo = oportunidad de compra."""
    if fair is not None and best_ask is not None:
        return (fair - best_ask) * 100.0
    return None


def spread_bps(best_bid: Optional[float], best_ask: Optional[float], mid: Optional[float]) -> Optional[float]:
    if best_bid is not None and best_ask is not None and mid and mid > 0:
        return (best_ask - best_bid) / mid * 10_000
    return None


def depth_50bps_usd(
    bids: List[Any],
    asks: List[Any],
    mid: float,
    bps: int = DEPTH_BPS,
) -> float:
    """USD disponible dentro de ±bps del mid (price * size en cada nivel)."""
    low = mid * (1 - bps / 10_000)
    high = mid * (1 + bps / 10_000)
    total = 0.0
    for lev in bids:
        p, s = _parse_level(lev)
        if low <= p <= high and s > 0:
            total += p * s
    for lev in asks:
        p, s = _parse_level(lev)
        if low <= p <= high and s > 0:
            total += p * s
    return total


def slippage_1k_cents(
    asks: List[Any],
    mid: Optional[float],
    notional_usd: float = SLIPPAGE_NOTIONAL_USD,
) -> Optional[float]:
    """
    Coste estimado en céntimos de ejecutar notional_usd ($1k) comprando (walking the ask book).
    Simulamos comprar hasta gastar notional_usd; avg_price = cost_usd / shares_bought.
    Slippage en céntimos para $1k = 100 * (avg_price - mid) / mid * 1000 = 100_000 * (avg_price - mid) / mid.
    """
    if not mid or mid <= 0 or not asks:
        return None
    levels = [_parse_level(x) for x in asks if x]
    levels = [(p, s) for p, s in levels if p > 0 and s > 0]
    levels.sort(key=lambda x: x[0])
    remaining_usd = notional_usd
    cost_usd = 0.0
    shares_bought = 0.0
    for p, s in levels:
        if remaining_usd <= 0:
            break
        value_here = p * s
        take_usd = min(remaining_usd, value_here)
        take_shares = take_usd / p if p else 0
        cost_usd += take_usd
        shares_bought += take_shares
        remaining_usd -= take_usd
    if shares_bought <= 0:
        return None
    avg_price = cost_usd / shares_bought
    return 100_000 * (avg_price - mid) / mid if mid else None


def compute_fillability_score(
    spread_bps_val: Optional[float],
    slippage_1k_val: Optional[float],
    stale_ms: Optional[int],
    max_staleness_ms: int = MAX_STALENESS_MS,
) -> int:
    """
    Score 0-100. Penaliza spread alto, slippage alto, datos viejos.
    - 80+ GREAT
    - 60-79 OK
    - <60 HARD
    """
    score = 100.0
    if spread_bps_val is not None:
        # spread 0 = no penalty; 100 bps = -20; 500 bps = -60
        score -= min(60, spread_bps_val * 0.12)
    if slippage_1k_val is not None and slippage_1k_val > 0:
        score -= min(30, slippage_1k_val * 0.3)  # 100 cents slippage → -30
    if stale_ms is not None and stale_ms > 0:
        # 2s = -5, 5s = -15, 10s = -25
        score -= min(25, (stale_ms / 1000) * 5)
    return max(0, min(100, int(round(score))))


def compute_event_score(
    edge_cents_val: float,
    fillability: int,
    liquidity_usd: float,
) -> float:
    """event_score = edge_cents * (fillability/100) * log(1 + liquidity_usd)."""
    if liquidity_usd < 0:
        liquidity_usd = 0
    return edge_cents_val * (fillability / 100.0) * math.log1p(liquidity_usd)


def compute_market_metrics(
    book_data: Dict[str, Any],
    liquidity_usd: float = 0.0,
    k_fair: float = FAIR_PRICE_K,
) -> Dict[str, Any]:
    """
    Dado un item de fetch_orderbooks_batch (por token), calcula todas las métricas.
    Returns dict con: mid_price, fair_price, edge_cents, spread_bps, depth_50bps_usd,
    slippage_1k_cents, fillability_score, best_bid, best_ask, stale_ms, etc.
    """
    best_bid = book_data.get("best_bid")
    best_ask = book_data.get("best_ask")
    bid_size_top = book_data.get("bid_size_top") or 0
    ask_size_top = book_data.get("ask_size_top") or 0
    total_bid = book_data.get("total_bid_size") or 0
    total_ask = book_data.get("total_ask_size") or 0
    bids = book_data.get("bids") or []
    asks = book_data.get("asks") or []
    stale_ms = book_data.get("stale_ms")

    mid = mid_price(best_bid, best_ask)
    fair = fair_price_indicative(best_bid, best_ask, total_bid, total_ask, k=k_fair)
    edge = edge_cents(fair, best_ask)
    spread = spread_bps(best_bid, best_ask, mid)
    depth = depth_50bps_usd(bids, asks, mid) if mid else 0.0
    slippage = slippage_1k_cents(asks, mid) if asks else None
    fillability = compute_fillability_score(spread, slippage, stale_ms)

    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid_price": mid,
        "fair_price": fair,
        "edge_cents": edge,
        "spread_bps": spread,
        "depth_50bps_usd": depth,
        "slippage_1k_cents": slippage,
        "fillability_score": fillability,
        "stale_ms": stale_ms,
        "liquidity_usd": liquidity_usd,
    }
