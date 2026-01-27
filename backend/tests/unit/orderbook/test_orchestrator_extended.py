"""
Tests adicionales para orchestrator (cobertura 100%).
"""
import pytest
from app.core.orderbook.orchestrator import OrderbookOrchestrator
from app.core.orderbook.models import OrderbookLevel


def test_orchestrator_unsubscribe_edge_cases():
    """Test orchestrator unsubscribe edge cases."""
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
    
    # Unsubscribe sin subscribe previo (debe manejar gracefully)
    orchestrator.unsubscribe(asset_id, "strategy_1")
    assert asset_id not in orchestrator.owners
    assert len(unsubscribed_assets) == 0  # No se llama on_unsubscribe
    
    # Subscribe y luego unsubscribe con owner diferente
    orchestrator.subscribe(asset_id, "strategy_1")
    orchestrator.unsubscribe(asset_id, "strategy_2")  # Owner diferente
    assert asset_id in orchestrator.owners  # Todavía suscrito por strategy_1
    assert len(unsubscribed_assets) == 0  # No se desuscribe todavía


def test_orchestrator_get_subscribed_asset_ids():
    """Test get_subscribed_asset_ids() method."""
    orchestrator = OrderbookOrchestrator()
    
    # Sin suscripciones
    assert len(orchestrator.get_subscribed_asset_ids()) == 0
    
    # Con suscripciones
    orchestrator.subscribe("asset_1", "strategy_1")
    orchestrator.subscribe("asset_2", "strategy_1")
    
    subscribed = orchestrator.get_subscribed_asset_ids()
    assert len(subscribed) == 2
    assert "asset_1" in subscribed
    assert "asset_2" in subscribed



