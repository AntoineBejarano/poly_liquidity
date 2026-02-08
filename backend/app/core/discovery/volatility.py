"""
Market-level rolling volatility (5m / 15m) from a stable price series.

- Price: mid = (best_bid + best_ask) / 2 when both exist; fallback last_trade_price.
- Ring buffer: (timestamp_sec, price) per market, at least 20 minutes of data.
- Volatility: std(log returns) over the window. returns_t = ln(p_t / p_{t-1}).
"""
import math
import time
import logging
from collections import deque
from typing import Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# Mantener 20+ min de datos para ventanas 5m y 15m con margen
BUFFER_MAX_AGE_SEC = 20 * 60 + 60  # 21 min
WINDOW_5M_SEC = 5 * 60
WINDOW_15M_SEC = 15 * 60

VOL_SOURCE_MID = "MID"
VOL_SOURCE_LAST_TRADE = "LAST_TRADE"


def _log_returns(prices: list) -> list:
    """returns[i] = ln(prices[i] / prices[i-1]). Requires len(prices) >= 2 and all > 0."""
    out = []
    for i in range(1, len(prices)):
        if prices[i - 1] and prices[i - 1] > 0 and prices[i] and prices[i] > 0:
            out.append(math.log(prices[i] / prices[i - 1]))
    return out


def _std(values: list) -> float:
    if len(values) < 2:
        return 0.0
    n = len(values)
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    return math.sqrt(var) if var >= 0 else 0.0


class PriceSeriesBuffer:
    """
    Ring buffer of (timestamp_sec, price). Drops points older than BUFFER_MAX_AGE_SEC.
    """
    __slots__ = ("_points",)

    def __init__(self) -> None:
        self._points: deque = deque()

    def add(self, ts_sec: float, price: float) -> None:
        if not (price is not None and price > 0):
            return
        cutoff = ts_sec - BUFFER_MAX_AGE_SEC
        while self._points and self._points[0][0] < cutoff:
            self._points.popleft()
        self._points.append((ts_sec, price))

    def get_prices_in_window(self, ts_end: float, window_sec: float) -> list:
        """Returns list of (ts, price) in [ts_end - window_sec, ts_end], sorted by ts."""
        ts_start = ts_end - window_sec
        out = [(t, p) for t, p in self._points if ts_start <= t <= ts_end]
        out.sort(key=lambda x: x[0])
        return out

    def volatility(self, ts_end: float, window_sec: float) -> Tuple[float, int]:
        """
        Volatility as std(log returns) in the window.
        Returns (vol, sample_count). sample_count = number of returns (len(prices)-1).
        """
        points = self.get_prices_in_window(ts_end, window_sec)
        prices = [p for _, p in points]
        if len(prices) < 2:
            return 0.0, 0
        returns = _log_returns(prices)
        if not returns:
            return 0.0, 0
        return _std(returns), len(returns)


class VolatilityStore:
    """
    In-memory store of price series per token_id. Thread-safe for single-threaded async;
    for multi-worker use a shared backend (e.g. Redis) later.
    """
    __slots__ = ("_buffers",)

    def __init__(self) -> None:
        self._buffers: Dict[str, PriceSeriesBuffer] = {}

    def _get_buffer(self, token_id: str) -> PriceSeriesBuffer:
        if token_id not in self._buffers:
            self._buffers[token_id] = PriceSeriesBuffer()
        return self._buffers[token_id]

    def update(
        self,
        token_id: str,
        ts_sec: float,
        price: Optional[float],
        source: str = VOL_SOURCE_MID,
    ) -> Dict[str, Any]:
        """
        Push one price observation and return current vol metrics for the market.
        If price is None, the buffer is not updated but last computed vol can still be returned
        from the existing buffer (we don't persist that; this call returns vol from current buffer).
        """
        buf = self._get_buffer(token_id)
        if price is not None and price > 0:
            buf.add(ts_sec, price)
        vol_5m, n_5m = buf.volatility(ts_sec, WINDOW_5M_SEC)
        vol_15m, n_15m = buf.volatility(ts_sec, WINDOW_15M_SEC)
        return {
            "vol_5m": round(vol_5m, 8),
            "vol_15m": round(vol_15m, 8),
            "vol_source": source,
            "vol_samples_5m": n_5m,
            "vol_samples_15m": n_15m,
            "vol_last_updated_at": ts_sec,
        }


# Singleton for use from orderbook and screener
_volatility_store: Optional[VolatilityStore] = None


def get_volatility_store() -> VolatilityStore:
    global _volatility_store
    if _volatility_store is None:
        _volatility_store = VolatilityStore()
    return _volatility_store
