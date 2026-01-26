"""
Tests para OrderbookBook.
"""
import pytest
from app.core.orderbook.book import OrderbookBook
from app.core.orderbook.models import OrderbookLevel


def test_orderbook_book_sorting():
    """Test OrderbookBook sorts correctly."""
    book = OrderbookBook(top_n=20)
    bids = [
        OrderbookLevel(price=0.50, size=10),
        OrderbookLevel(price=0.48, size=20),
        OrderbookLevel(price=0.49, size=15)
    ]
    asks = [
        OrderbookLevel(price=0.52, size=25),
        OrderbookLevel(price=0.54, size=30),
        OrderbookLevel(price=0.53, size=20)
    ]
    book.update_from_snapshot(bids, asks, ts_ms=1000)
    
    best_bid, best_ask, mid, spread = book.compute_bbo()
    assert best_bid == 0.50  # best bid (highest)
    assert best_ask == 0.52  # best ask (lowest)
    assert mid == 0.51
    assert spread is not None


def test_orderbook_book_truncation():
    """Test OrderbookBook truncates to top_n."""
    book = OrderbookBook(top_n=3)
    bids = [OrderbookLevel(price=0.50 - i*0.01, size=10) for i in range(10)]
    asks = [OrderbookLevel(price=0.52 + i*0.01, size=10) for i in range(10)]
    book.update_from_snapshot(bids, asks, ts_ms=1000)
    
    assert len(book.bids) == 3
    assert len(book.asks) == 3
    # Deben estar ordenados
    assert book.bids[0].price == 0.50
    assert book.bids[1].price == 0.49
    assert book.bids[2].price == 0.48
    assert book.asks[0].price == 0.52
    assert book.asks[1].price == 0.53
    assert book.asks[2].price == 0.54


def test_orderbook_book_no_bids():
    """Test OrderbookBook with no bids."""
    book = OrderbookBook(top_n=20)
    bids = []
    asks = [OrderbookLevel(price=0.52, size=25)]
    book.update_from_snapshot(bids, asks, ts_ms=1000)
    
    # Verify asks are still there
    assert len(book.asks) == 1
    assert book.asks[0].price == 0.52
    
    # BBO requires both bids and asks
    best_bid, best_ask, mid, spread = book.compute_bbo()
    assert best_bid is None  # No bids
    assert best_ask is None  # compute_bbo returns None for both if one is missing
    assert mid is None
    assert spread is None


def test_orderbook_book_no_asks():
    """Test OrderbookBook with no asks."""
    book = OrderbookBook(top_n=20)
    bids = [OrderbookLevel(price=0.50, size=10)]
    asks = []
    book.update_from_snapshot(bids, asks, ts_ms=1000)
    
    # Verify bids are still there
    assert len(book.bids) == 1
    assert book.bids[0].price == 0.50
    
    # BBO requires both bids and asks
    best_bid, best_ask, mid, spread = book.compute_bbo()
    assert best_bid is None  # compute_bbo returns None for both if one is missing
    assert best_ask is None  # No asks
    assert mid is None
    assert spread is None

