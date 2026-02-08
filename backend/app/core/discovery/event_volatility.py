"""
Event-level volatility metrics and 3-state label (NON_VOLATILE / VOLATILE / CHAOTIC).

Aggregates market-level vol_5m / vol_15m without heavy computation.
Guardrails: downgrade on high spread / low liquidity; UNKNOWN on too few samples.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 3-state label
LABEL_NON_VOLATILE = "NON_VOLATILE"
LABEL_VOLATILE = "VOLATILE"
LABEL_CHAOTIC = "CHAOTIC"
LABEL_UNKNOWN = "UNKNOWN"

# TODO: dynamic thresholds by category (sports vs crypto) using rolling percentiles (p70/p90)
# Static thresholds for now: vol_5m (log-return std)
THRESHOLD_VOLATILE = 0.02   # >= 2% std of log returns → VOLATILE
THRESHOLD_CHAOTIC = 0.05    # >= 5% → CHAOTIC
HOT_MARKET_VOL_5M_THRESHOLD = 0.02  # count markets with vol_5m >= this as "hot"

# Guardrails: illiquidity / wide spread → downgrade by 1 level
MAX_SPREAD_BPS_DOWNGRADE = 500.0   # if spread_bps > this, downgrade
MIN_LIQUIDITY_USD_DOWNGRADE = 500.0  # if liquidity_usd < this, downgrade
MIN_SAMPLES_FOR_LABEL = 3  # if vol_samples_5m < this, set UNKNOWN (or NON_VOLATILE)


def _downgrade_label(label: str) -> str:
    if label == LABEL_CHAOTIC:
        return LABEL_VOLATILE
    if label == LABEL_VOLATILE:
        return LABEL_NON_VOLATILE
    return label


def compute_event_volatility_metrics(markets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate market-level vol into event-level metrics.
    markets: list of market dicts with optional vol_5m, vol_15m (and spread_bps, liquidity_usd for guardrails).
    """
    vols_5m = []
    vols_15m = []
    hot_count_5m = 0
    for m in markets:
        v5 = m.get("vol_5m")
        v15 = m.get("vol_15m")
        if v5 is not None:
            vols_5m.append(v5)
            if v5 >= HOT_MARKET_VOL_5M_THRESHOLD:
                hot_count_5m += 1
        if v15 is not None:
            vols_15m.append(v15)
    max_vol_5m = max(vols_5m) if vols_5m else None
    max_vol_15m = max(vols_15m) if vols_15m else None
    return {
        "max_vol_5m": max_vol_5m,
        "max_vol_15m": max_vol_15m,
        "hot_markets_count_5m": hot_count_5m,
    }


def get_volatility_label(
    max_vol_5m: Optional[float],
    max_vol_15m: Optional[float],
    hot_markets_count_5m: int = 0,
    worst_spread_bps: Optional[float] = None,
    worst_liquidity_usd: Optional[float] = None,
    min_samples_5m: Optional[int] = None,
) -> tuple:
    """
    Returns (label, reason).
    - NON_VOLATILE / VOLATILE / CHAOTIC / UNKNOWN
    - reason: short string for logging and UI (e.g. "samples_5m=2" or "guardrail: spread")
    """
    if min_samples_5m is not None and min_samples_5m < MIN_SAMPLES_FOR_LABEL:
        return (
            LABEL_UNKNOWN,
            f"samples_5m={min_samples_5m or 0}",
        )
    if max_vol_5m is None:
        return (LABEL_UNKNOWN, "no_vol_data")
    label = LABEL_NON_VOLATILE
    if max_vol_5m >= THRESHOLD_CHAOTIC:
        label = LABEL_CHAOTIC
    elif max_vol_5m >= THRESHOLD_VOLATILE:
        label = LABEL_VOLATILE
    reason = ""
    # Guardrails: downgrade one level if illiquid or wide spread
    if worst_spread_bps is not None and worst_spread_bps > MAX_SPREAD_BPS_DOWNGRADE:
        label = _downgrade_label(label)
        reason = "guardrail: spread"
    if worst_liquidity_usd is not None and worst_liquidity_usd < MIN_LIQUIDITY_USD_DOWNGRADE:
        label = _downgrade_label(label)
        reason = reason or "guardrail: liquidity"
    if not reason:
        reason = f"max_vol_5m={max_vol_5m:.4f}"
    return (label, reason)


def compute_event_volatility_label_and_metrics(
    markets: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Full event-level result: metrics + volatility_label + volatility_label_reason.
    Uses worst spread and worst liquidity across markets for guardrails.
    """
    agg = compute_event_volatility_metrics(markets)
    max_vol_5m = agg.get("max_vol_5m")
    max_vol_15m = agg.get("max_vol_15m")
    hot_count = agg.get("hot_markets_count_5m", 0)
    worst_spread = None  # max spread = worst
    worst_liq = None     # min liquidity = worst
    min_samples = None
    for m in markets:
        sp = m.get("spread_bps")
        if sp is not None:
            worst_spread = max(worst_spread, sp) if worst_spread is not None else sp
        liq = m.get("liquidity_usd")
        if liq is not None:
            worst_liq = min(worst_liq, liq) if worst_liq is not None else liq
        n5 = m.get("vol_samples_5m")
        if n5 is not None:
            min_samples = min(min_samples, n5) if min_samples is not None else n5
    label, reason = get_volatility_label(
        max_vol_5m,
        max_vol_15m,
        hot_markets_count_5m=hot_count,
        worst_spread_bps=worst_spread,
        worst_liquidity_usd=worst_liq,
        min_samples_5m=min_samples,
    )
    out = dict(agg)
    out["volatility_label"] = label
    out["volatility_label_reason"] = reason
    return out
