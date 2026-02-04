"""
Tests para parser WS book.
"""
import pytest
from app.core.orderbook.ws_parser import parse_ws_book_payload
from app.core.orderbook.models import OrderbookLevel


def test_parse_ws_book_payload_strings():
    """Test parsing WS payload with string prices/sizes."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [{"price": ".48", "size": "30"}],
        "asks": [{"price": ".52", "size": "25"}],
        "timestamp": "123456789000",
        "hash": "0xabc123"
    }
    bids, asks, ts_ms, hash_value = parse_ws_book_payload(payload)
    
    assert len(bids) == 1
    assert bids[0].price == 0.48
    assert bids[0].size == 30.0
    assert len(asks) == 1
    assert asks[0].price == 0.52
    assert asks[0].size == 25.0
    assert ts_ms == 123456789000
    assert hash_value == "0xabc123"


def test_parse_ws_book_payload_multiple_levels():
    """Test parsing WS payload with multiple levels."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [
            {"price": ".48", "size": "30"},
            {"price": ".47", "size": "20"},
            {"price": ".46", "size": "10"}
        ],
        "asks": [
            {"price": ".52", "size": "25"},
            {"price": ".53", "size": "35"},
            {"price": ".54", "size": "45"}
        ],
        "timestamp": "123456789000"
    }
    bids, asks, ts_ms, hash_value = parse_ws_book_payload(payload)
    
    assert len(bids) == 3
    assert len(asks) == 3
    # Bids deben estar ordenados desc
    assert bids[0].price == 0.48
    assert bids[1].price == 0.47
    assert bids[2].price == 0.46
    # Asks deben estar ordenados asc
    assert asks[0].price == 0.52
    assert asks[1].price == 0.53
    assert asks[2].price == 0.54
    assert hash_value is None  # No se proporcionó hash


def test_parse_ws_book_payload_invalid_levels():
    """Test parsing WS payload with invalid levels (filtered out)."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [
            {"price": ".48", "size": "30"},
            {"price": "-0.1", "size": "20"},  # Invalid: negative price
            {"price": ".46", "size": "-10"}   # Invalid: negative size
        ],
        "asks": [
            {"price": ".52", "size": "25"},
            {"price": "0", "size": "35"},     # Invalid: zero price
        ],
        "timestamp": "123456789000"
    }
    bids, asks, ts_ms, hash_value = parse_ws_book_payload(payload)
    
    # Solo niveles válidos deben pasar
    assert len(bids) == 1
    assert bids[0].price == 0.48
    assert len(asks) == 1
    assert asks[0].price == 0.52


def test_parse_ws_book_payload_missing_fields():
    """Test parsing WS payload with missing fields."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        # Missing bids/asks/timestamp
    }
    bids, asks, ts_ms, hash_value = parse_ws_book_payload(payload)
    
    assert len(bids) == 0
    assert len(asks) == 0
    assert ts_ms == 0
    assert hash_value is None



