"""
Tests adicionales para parser (cobertura 100%).
"""
import pytest
from app.core.orderbook.ws_parser import parse_ws_book_payload


def test_parse_ws_book_payload_invalid_price_type():
    """Test parsing with invalid price type."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [{"price": None, "size": "30"}],  # None en lugar de string
        "asks": [{"price": ".52", "size": "25"}],
        "timestamp": "123456789000"
    }
    bids, asks, ts_ms = parse_ws_book_payload(payload)
    
    # Debe filtrar el bid inválido
    assert len(bids) == 0
    assert len(asks) == 1


def test_parse_ws_book_payload_invalid_size_type():
    """Test parsing with invalid size type."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [{"price": ".48", "size": None}],  # None en lugar de string
        "asks": [{"price": ".52", "size": "25"}],
        "timestamp": "123456789000"
    }
    bids, asks, ts_ms = parse_ws_book_payload(payload)
    
    # Debe filtrar el bid inválido
    assert len(bids) == 0
    assert len(asks) == 1


def test_parse_ws_book_payload_missing_price_key():
    """Test parsing with missing price key."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [{"size": "30"}],  # Falta "price"
        "asks": [{"price": ".52", "size": "25"}],
        "timestamp": "123456789000"
    }
    bids, asks, ts_ms = parse_ws_book_payload(payload)
    
    # Debe filtrar el bid inválido
    assert len(bids) == 0
    assert len(asks) == 1


def test_parse_ws_book_payload_missing_size_key():
    """Test parsing with missing size key."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [{"price": ".48"}],  # Falta "size"
        "asks": [{"price": ".52", "size": "25"}],
        "timestamp": "123456789000"
    }
    bids, asks, ts_ms = parse_ws_book_payload(payload)
    
    # Debe filtrar el bid inválido
    assert len(bids) == 0
    assert len(asks) == 1


def test_parse_ws_book_payload_invalid_timestamp():
    """Test parsing with invalid timestamp."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [{"price": ".48", "size": "30"}],
        "asks": [{"price": ".52", "size": "25"}],
        "timestamp": "invalid"  # Timestamp inválido
    }
    bids, asks, ts_ms = parse_ws_book_payload(payload)
    
    # Debe usar 0 como fallback
    assert ts_ms == 0
    assert len(bids) == 1
    assert len(asks) == 1


def test_parse_ws_book_payload_timestamp_none():
    """Test parsing with None timestamp."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [{"price": ".48", "size": "30"}],
        "asks": [{"price": ".52", "size": "25"}],
        "timestamp": None  # None timestamp
    }
    bids, asks, ts_ms = parse_ws_book_payload(payload)
    
    # Debe usar 0 como fallback
    assert ts_ms == 0


def test_parse_ws_book_payload_invalid_ask_price_type():
    """Test parsing with invalid ask price type."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [{"price": ".48", "size": "30"}],
        "asks": [{"price": None, "size": "25"}],  # None en lugar de string
        "timestamp": "123456789000"
    }
    bids, asks, ts_ms = parse_ws_book_payload(payload)
    
    # Debe filtrar el ask inválido
    assert len(bids) == 1
    assert len(asks) == 0


def test_parse_ws_book_payload_invalid_ask_size_type():
    """Test parsing with invalid ask size type."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [{"price": ".48", "size": "30"}],
        "asks": [{"price": ".52", "size": None}],  # None en lugar de string
        "timestamp": "123456789000"
    }
    bids, asks, ts_ms = parse_ws_book_payload(payload)
    
    # Debe filtrar el ask inválido
    assert len(bids) == 1
    assert len(asks) == 0


def test_parse_ws_book_payload_missing_ask_price_key():
    """Test parsing with missing ask price key."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [{"price": ".48", "size": "30"}],
        "asks": [{"size": "25"}],  # Falta "price"
        "timestamp": "123456789000"
    }
    bids, asks, ts_ms = parse_ws_book_payload(payload)
    
    # Debe filtrar el ask inválido
    assert len(bids) == 1
    assert len(asks) == 0


def test_parse_ws_book_payload_missing_ask_size_key():
    """Test parsing with missing ask size key."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [{"price": ".48", "size": "30"}],
        "asks": [{"price": ".52"}],  # Falta "size"
        "timestamp": "123456789000"
    }
    bids, asks, ts_ms = parse_ws_book_payload(payload)
    
    # Debe filtrar el ask inválido
    assert len(bids) == 1
    assert len(asks) == 0

