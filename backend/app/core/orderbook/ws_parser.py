"""
Parser para mensajes WebSocket de orderbook.

⚠️ IMPORTANTE: El payload viene con strings, no floats.
"""
import logging
from typing import Dict, Any, Tuple, List, Optional
from .models import OrderbookLevel

logger = logging.getLogger(__name__)


def parse_ws_book_payload(
    book_msg: Dict[str, Any]
) -> Tuple[List[OrderbookLevel], List[OrderbookLevel], int, Optional[str]]:
    """
    Parsea payload WS book a OrderbookLevel lists, timestamp y hash.
    
    ⚠️ IMPORTANTE: El payload viene con strings:
    - "price": ".48" → float(".48") = 0.48
    - "size": "30" → float("30") = 30.0
    - "timestamp": "123456789000" → int("123456789000") = 123456789000
    - "hash": "0x0...." → string (opcional)
    
    Args:
        book_msg: Mensaje WS con estructura:
            {
                "event_type": "book",
                "asset_id": "...",
                "market": "...",
                "bids": [{"price": ".48", "size": "30"}, ...],  # o "buys"
                "asks": [{"price": ".52", "size": "25"}, ...],  # o "sells"
                "timestamp": "123456789000",
                "hash": "0x0...."  # opcional
            }
    
    Returns:
        (bids, asks, ts_ms, hash) donde:
        - bids: Lista de OrderbookLevel (ordenada desc price)
        - asks: Lista de OrderbookLevel (ordenada asc price)
        - ts_ms: Timestamp en ms (int)
        - hash: Hash del mensaje (str o None)
    """
    # Soporta tanto "bids"/"asks" como "buys"/"sells"
    bids_raw = book_msg.get("bids") or book_msg.get("buys", [])
    asks_raw = book_msg.get("asks") or book_msg.get("sells", [])
    timestamp_str = book_msg.get("timestamp", "0")
    hash_value = book_msg.get("hash")  # Campo opcional
    
    bids = []
    for level in bids_raw:
        try:
            price = float(level["price"])  # ".48" -> 0.48
            size = float(level["size"])    # "30" -> 30.0
            if price > 0 and size >= 0:
                bids.append(OrderbookLevel(price=price, size=size))
        except (ValueError, KeyError, TypeError) as e:
            logger.warning(f"Error parsing bid level: {level}, error: {e}")
            continue
    
    asks = []
    for level in asks_raw:
        try:
            price = float(level["price"])
            size = float(level["size"])
            if price > 0 and size >= 0:
                asks.append(OrderbookLevel(price=price, size=size))
        except (ValueError, KeyError, TypeError) as e:
            logger.warning(f"Error parsing ask level: {level}, error: {e}")
            continue
    
    try:
        ts_ms = int(timestamp_str)
    except (ValueError, TypeError):
        logger.warning(f"Error parsing timestamp: {timestamp_str}, using 0")
        ts_ms = 0
    
    # Sort: bids desc, asks asc
    bids.sort(key=lambda x: x.price, reverse=True)
    asks.sort(key=lambda x: x.price)
    
    # Truncate to top 20 (el OrderbookBook también lo hace, pero por si acaso)
    bids = bids[:20]
    asks = asks[:20]
    
    return bids, asks, ts_ms, hash_value



