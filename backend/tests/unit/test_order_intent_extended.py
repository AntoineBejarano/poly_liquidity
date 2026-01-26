"""
Tests unitarios para OrderIntent extendido con campos nuevos.
"""
import pytest
from uuid import uuid4
from app.core.strategy.models import OrderIntent


def test_order_intent_with_new_fields():
    """Test que OrderIntent puede crearse con los nuevos campos opcionales."""
    event_id = uuid4()
    strategy_id = uuid4()
    graph_execution_id = uuid4()
    trace_id = uuid4()
    
    intent = OrderIntent(
        event_id=event_id,
        outcome="YES",
        side="BUY",
        price=0.98,
        size=100.0,
        reason="Test reason",
        strategy_id=strategy_id,
        graph_execution_id=graph_execution_id,
        trace_id=trace_id
    )
    
    assert intent.event_id == event_id
    assert intent.outcome == "YES"
    assert intent.side == "BUY"
    assert intent.price == 0.98
    assert intent.size == 100.0
    assert intent.reason == "Test reason"
    assert intent.strategy_id == strategy_id
    assert intent.graph_execution_id == graph_execution_id
    assert intent.trace_id == trace_id


def test_order_intent_without_new_fields():
    """Test que OrderIntent sigue funcionando sin los nuevos campos (compatibilidad)."""
    event_id = uuid4()
    
    intent = OrderIntent(
        event_id=event_id,
        outcome="YES",
        side="BUY",
        price=0.98,
        size=100.0,
        reason="Test reason"
    )
    
    assert intent.event_id == event_id
    assert intent.outcome == "YES"
    assert intent.strategy_id is None
    assert intent.graph_execution_id is None


def test_order_intent_partial_new_fields():
    """Test que OrderIntent puede tener solo uno de los nuevos campos."""
    event_id = uuid4()
    strategy_id = uuid4()
    
    intent = OrderIntent(
        event_id=event_id,
        outcome="YES",
        side="BUY",
        price=0.98,
        size=100.0,
        reason="Test reason",
        strategy_id=strategy_id
    )
    
    assert intent.strategy_id == strategy_id
    assert intent.graph_execution_id is None


def test_order_intent_metadata_preserved():
    """Test que el metadata se preserva correctamente."""
    event_id = uuid4()
    market_id = uuid4()
    
    intent = OrderIntent(
        event_id=event_id,
        outcome="YES",
        side="BUY",
        price=0.98,
        size=100.0,
        reason="Test reason",
        metadata={"market_id": str(market_id), "test": "value"}
    )
    
    assert intent.metadata["market_id"] == str(market_id)
    assert intent.metadata["test"] == "value"

