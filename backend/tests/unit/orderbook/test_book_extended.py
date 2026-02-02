"""
Tests adicionales para OrderbookBook (cobertura 100%).
"""
import pytest
from app.core.orderbook.book import OrderbookBook
from app.core.orderbook.models import OrderbookLevel


def test_orderbook_book_get_bids():
    """Test get_bids() method."""
    book = OrderbookBook(top_n=20)
    bids = [OrderbookLevel(price=0.50, size=10)]
    asks = [OrderbookLevel(price=0.52, size=20)]
    book.update_from_snapshot(bids, asks, ts_ms=1000)
    
    result = book.get_bids()
    assert len(result) == 1
    assert result[0].price == 0.50
    # Debe ser una copia, no la misma referencia
    assert result is not book.bids


def test_orderbook_book_get_asks():
    """Test get_asks() method."""
    book = OrderbookBook(top_n=20)
    bids = [OrderbookLevel(price=0.50, size=10)]
    asks = [OrderbookLevel(price=0.52, size=20)]
    book.update_from_snapshot(bids, asks, ts_ms=1000)
    
    result = book.get_asks()
    assert len(result) == 1
    assert result[0].price == 0.52
    # Debe ser una copia, no la misma referencia
    assert result is not book.asks


def test_orderbook_book_get_last_ts_ms():
    """Test get_last_ts_ms() method."""
    book = OrderbookBook(top_n=20)
    bids = [OrderbookLevel(price=0.50, size=10)]
    asks = [OrderbookLevel(price=0.52, size=20)]
    book.update_from_snapshot(bids, asks, ts_ms=123456789)
    
    assert book.get_last_ts_ms() == 123456789



