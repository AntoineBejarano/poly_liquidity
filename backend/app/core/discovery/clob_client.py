"""
CLOB REST client for Discovery: orderbook snapshots only (no trading).

Uses Polymarket CLOB API:
- POST /books with body [{"token_id": "..."}, ...] → list of orderbooks
- Each book: bids/asks arrays of {price, size}, timestamp
"""
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

CLOB_BASE = getattr(settings, "polymarket_trading_api_url", "https://clob.polymarket.com")
BOOKS_URL = f"{CLOB_BASE.rstrip('/')}/books"
REQUEST_TIMEOUT = 15.0
MAX_TOKENS_PER_REQUEST = 100


def _parse_price_size(level: Any) -> tuple[float, float]:
    """Parse a bid/ask level to (price, size). Price/size can be string or number."""
    if not isinstance(level, dict):
        return 0.0, 0.0
    try:
        p = level.get("price") or level.get("price_float")
        s = level.get("size") or level.get("size_float")
        price = float(p) if p is not None else 0.0
        size = float(s) if s is not None else 0.0
        return price, size
    except (TypeError, ValueError):
        return 0.0, 0.0


def _best_bid_ask(bids: List[Any], asks: List[Any]) -> tuple[Optional[float], Optional[float], float, float, float, float]:
    """
    From orderbook bids/asks return best_bid, best_ask, bid_size_top, ask_size_top, total_bid_size, total_ask_size.
    Bids: highest price first (desc); Asks: lowest price first (asc).
    """
    best_bid, best_ask = None, None
    bid_size_top, ask_size_top = 0.0, 0.0
    total_bid_size, total_ask_size = 0.0, 0.0

    if bids:
        # Polymarket: bids often sorted desc by price
        prices_sizes = [_parse_price_size(x) for x in bids if x]
        prices_sizes = [(p, s) for p, s in prices_sizes if p > 0 and s > 0]
        if prices_sizes:
            prices_sizes.sort(key=lambda x: -x[0])
            best_bid = prices_sizes[0][0]
            bid_size_top = prices_sizes[0][1]
            total_bid_size = sum(s for _, s in prices_sizes)

    if asks:
        prices_sizes = [_parse_price_size(x) for x in asks if x]
        prices_sizes = [(p, s) for p, s in prices_sizes if p > 0 and s > 0]
        if prices_sizes:
            prices_sizes.sort(key=lambda x: x[0])
            best_ask = prices_sizes[0][0]
            ask_size_top = prices_sizes[0][1]
            total_ask_size = sum(s for _, s in prices_sizes)

    return best_bid, best_ask, bid_size_top, ask_size_top, total_bid_size, total_ask_size


async def fetch_orderbooks_batch(token_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch orderbooks for multiple tokens via POST /books.

    Args:
        token_ids: list of CLOB token IDs (from Gamma market clobTokenIds).

    Returns:
        List of dicts, one per token_id, with keys:
        - token_id
        - best_bid, best_ask (float or None)
        - bid_size_top, ask_size_top
        - total_bid_size, total_ask_size
        - bids, asks (raw for depth calc)
        - timestamp_iso (from API)
        - stale_ms (ms since timestamp if parseable)
    """
    if not token_ids:
        return []

    # CLOB accepts up to 500; we chunk to avoid timeouts
    chunk_size = min(MAX_TOKENS_PER_REQUEST, 80)
    results: List[Dict[str, Any]] = []

    for i in range(0, len(token_ids), chunk_size):
        chunk = token_ids[i : i + chunk_size]
        body = [{"token_id": tid} for tid in chunk]
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                r = await client.post(BOOKS_URL, json=body)
                r.raise_for_status()
                books = r.json()
        except Exception as e:
            logger.debug("Discovery CLOB books error for chunk: %s", e)
            for tid in chunk:
                results.append({
                    "token_id": tid,
                    "best_bid": None,
                    "best_ask": None,
                    "bid_size_top": 0.0,
                    "ask_size_top": 0.0,
                    "total_bid_size": 0.0,
                    "total_ask_size": 0.0,
                    "bids": [],
                    "asks": [],
                    "timestamp_iso": None,
                    "stale_ms": None,
                    "error": str(e),
                })
            continue

        if not isinstance(books, list):
            for tid in chunk:
                results.append({
                    "token_id": tid,
                    "best_bid": None,
                    "best_ask": None,
                    "bid_size_top": 0.0,
                    "ask_size_top": 0.0,
                    "total_bid_size": 0.0,
                    "total_ask_size": 0.0,
                    "bids": [],
                    "asks": [],
                    "timestamp_iso": None,
                    "stale_ms": None,
                })
            continue

        import time as _t
        now_ts = _t.time()

        for j, book in enumerate(books):
            token_id = chunk[j] if j < len(chunk) else ""
            if not isinstance(book, dict):
                results.append({
                    "token_id": token_id,
                    "best_bid": None,
                    "best_ask": None,
                    "bid_size_top": 0.0,
                    "ask_size_top": 0.0,
                    "total_bid_size": 0.0,
                    "total_ask_size": 0.0,
                    "bids": [],
                    "asks": [],
                    "timestamp_iso": None,
                    "stale_ms": None,
                })
                continue

            bids = book.get("bids") or []
            asks = book.get("asks") or []
            ts_iso = book.get("timestamp")
            stale_ms = None
            if ts_iso:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
                    stale_ms = int((now_ts - dt.timestamp()) * 1000)
                except Exception:
                    pass

            best_bid, best_ask, bid_size_top, ask_size_top, total_bid_size, total_ask_size = _best_bid_ask(bids, asks)

            results.append({
                "token_id": token_id,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "bid_size_top": bid_size_top,
                "ask_size_top": ask_size_top,
                "total_bid_size": total_bid_size,
                "total_ask_size": total_ask_size,
                "bids": bids,
                "asks": asks,
                "timestamp_iso": ts_iso,
                "stale_ms": stale_ms,
            })

    return results
