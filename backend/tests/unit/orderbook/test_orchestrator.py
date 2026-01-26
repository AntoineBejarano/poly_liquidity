"""
Tests para OrderbookOrchestrator.
"""
import pytest
from app.core.orderbook.orchestrator import OrderbookOrchestrator
from app.core.orderbook.models import OrderbookLevel


def test_orchestrator_ref_count():
    """Test orchestrator ref-count lifecycle con owners set."""
    subscribed_assets = []
    unsubscribed_assets = []
    
    def on_subscribe(asset_id: str):
        subscribed_assets.append(asset_id)
    
    def on_unsubscribe(asset_id: str):
        unsubscribed_assets.append(asset_id)
    
    orchestrator = OrderbookOrchestrator(
        on_subscribe=on_subscribe,
        on_unsubscribe=on_unsubscribe
    )
    asset_id = "123"
    
    # First subscribe
    orchestrator.subscribe(asset_id, "strategy_1")
    assert asset_id in orchestrator.owners
    assert "strategy_1" in orchestrator.owners[asset_id]
    assert orchestrator.ref_count[asset_id] == 1
    assert len(orchestrator.owners[asset_id]) == orchestrator.ref_count[asset_id]
    assert asset_id in subscribed_assets
    
    # Double-subscribe same owner (idempotente)
    orchestrator.subscribe(asset_id, "strategy_1")
    assert orchestrator.ref_count[asset_id] == 1  # No cambia
    assert len(subscribed_assets) == 1  # No se llama de nuevo
    
    # Second subscribe (different owner)
    orchestrator.subscribe(asset_id, "strategy_2")
    assert orchestrator.ref_count[asset_id] == 2
    assert len(orchestrator.owners[asset_id]) == 2
    assert len(subscribed_assets) == 1  # No se llama de nuevo (ya estaba suscrito)
    
    # First unsubscribe
    orchestrator.unsubscribe(asset_id, "strategy_1")
    assert orchestrator.ref_count[asset_id] == 1
    assert "strategy_1" not in orchestrator.owners[asset_id]
    assert "strategy_2" in orchestrator.owners[asset_id]
    assert len(unsubscribed_assets) == 0  # No se desuscribe todavía
    
    # Second unsubscribe
    orchestrator.unsubscribe(asset_id, "strategy_2")
    # Cuando ref_count llega a 0, se elimina de owners, así que ref_count no tiene la key
    assert asset_id not in orchestrator.owners
    assert asset_id not in orchestrator.ref_count  # Se elimina cuando llega a 0
    assert asset_id in unsubscribed_assets
    
    # Unsubscribe sin subscribe previo (debe manejar gracefully)
    orchestrator.unsubscribe(asset_id, "strategy_3")  # No debe crashear
    assert asset_id not in orchestrator.owners


def test_orchestrator_ingest_book():
    """Test orchestrator ingest book message."""
    orchestrator = OrderbookOrchestrator()
    asset_id = "123"
    
    # Subscribe first
    orchestrator.subscribe(asset_id, "strategy_1")
    
    # Ingest book message
    bids = [OrderbookLevel(price=0.50, size=10)]
    asks = [OrderbookLevel(price=0.52, size=20)]
    orchestrator.ingest_book_msg(asset_id, bids, asks, ts_ms=1000)
    
    # Verify book was updated
    book = orchestrator.get_book(asset_id)
    assert book is not None
    best_bid, best_ask, mid, spread = book.compute_bbo()
    assert best_bid == 0.50
    assert best_ask == 0.52


def test_orchestrator_ingest_unsubscribed():
    """Test orchestrator ignores book updates for unsubscribed assets."""
    orchestrator = OrderbookOrchestrator()
    asset_id = "123"
    
    # Try to ingest without subscribing
    bids = [OrderbookLevel(price=0.50, size=10)]
    asks = [OrderbookLevel(price=0.52, size=20)]
    orchestrator.ingest_book_msg(asset_id, bids, asks, ts_ms=1000)
    
    # Book should not exist
    book = orchestrator.get_book(asset_id)
    assert book is None

