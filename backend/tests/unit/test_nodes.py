"""
Tests unitarios para nodos del grafo.
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.core.strategy_engine.models import GraphExecutionContext
from app.core.strategy_engine.nodes.collect_state import CollectStateNode
from app.core.strategy_engine.nodes.edge_and_risk_check import EdgeAndRiskCheckNode
from app.core.strategy_engine.nodes.calculate_order_size import CalculateOrderSizeNode
from app.core.strategy_engine.nodes.emit_execution_intent import EmitExecutionIntentNode
from app.core.strategy_engine.nodes.base import (
    SuccessResult,
    ConditionalResult,
    ExecutionIntentResult,
    FailureResult
)
from app.core.strategy.models import MarketState, EventState


@pytest.fixture
def mock_state_cache():
    """Mock StateCacheService."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.get_many = AsyncMock(return_value={})
    return cache


@pytest.fixture
def graph_context(mock_state_cache):
    """Fixture para GraphExecutionContext."""
    context = GraphExecutionContext(
        strategy_id=uuid4(),
        event_id=uuid4(),
        market_id=uuid4(),
        trace_id=uuid4(),
        state_cache=mock_state_cache
    )
    return context


class TestCollectStateNode:
    """Tests para CollectStateNode."""
    
    @pytest.mark.asyncio
    async def test_collect_market_state(self, graph_context, mock_state_cache):
        """Test recopilar market_state."""
        market_state = {"last_price": 0.98, "spread": 0.01}
        mock_state_cache.get = AsyncMock(return_value=market_state)
        
        node = CollectStateNode(
            {"sources": ["market_state"]},
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
        assert hasattr(graph_context, 'collected_state')
        assert graph_context.collected_state["market_state"] == market_state
        mock_state_cache.get.assert_called_once_with(f"event.{graph_context.event_id}.market_state")
    
    @pytest.mark.asyncio
    async def test_collect_event_state(self, graph_context, mock_state_cache):
        """Test recopilar event_state."""
        event_state = {"state": "ACTIVE", "confidence": 0.95}
        mock_state_cache.get = AsyncMock(return_value=event_state)
        
        node = CollectStateNode(
            {"sources": ["event_state"]},
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
        assert graph_context.collected_state["event_state"] == event_state
    
    @pytest.mark.asyncio
    async def test_collect_multiple_sources(self, graph_context, mock_state_cache):
        """Test recopilar múltiples fuentes."""
        market_state = {"last_price": 0.98}
        event_state = {"state": "ACTIVE"}
        
        def get_side_effect(key):
            if "market_state" in key:
                return market_state
            elif "event_state" in key:
                return event_state
            return None
        
        mock_state_cache.get = AsyncMock(side_effect=get_side_effect)
        mock_state_cache.get_many = AsyncMock(return_value={})
        
        node = CollectStateNode(
            {"sources": ["market_state", "event_state", "external_data"]},
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
        assert graph_context.collected_state["market_state"] == market_state
        assert graph_context.collected_state["event_state"] == event_state
        assert "external_data" in graph_context.collected_state
    
    @pytest.mark.asyncio
    async def test_collect_external_data(self, graph_context, mock_state_cache):
        """Test recopilar external_data."""
        external_data = {
            "event.123.external_data.sportsbook": {"odds": 1.5},
            "event.123.external_data.exchange": {"price": 0.98}
        }
        mock_state_cache.get_many = AsyncMock(return_value=external_data)
        
        node = CollectStateNode(
            {"sources": ["external_data"]},
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
        assert graph_context.collected_state["external_data"] == external_data


class TestEdgeAndRiskCheckNode:
    """Tests para EdgeAndRiskCheckNode."""
    
    @pytest.mark.asyncio
    async def test_simple_condition_true(self, graph_context):
        """Test condición simple que es True."""
        graph_context.collected_state = {
            "event_state": {"state": "ACTIVE"}
        }
        
        node = EdgeAndRiskCheckNode(
            {
                "conditions": [
                    {"field": "event_state.state", "operator": "==", "value": "ACTIVE"}
                ]
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, ConditionalResult)
        assert result.condition is True
    
    @pytest.mark.asyncio
    async def test_simple_condition_false(self, graph_context):
        """Test condición simple que es False."""
        graph_context.collected_state = {
            "event_state": {"state": "UPCOMING"}
        }
        
        node = EdgeAndRiskCheckNode(
            {
                "conditions": [
                    {"field": "event_state.state", "operator": "==", "value": "ACTIVE"}
                ]
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, ConditionalResult)
        assert result.condition is False
    
    @pytest.mark.asyncio
    async def test_multiple_conditions_and(self, graph_context):
        """Test múltiples condiciones con lógica AND."""
        graph_context.collected_state = {
            "event_state": {"state": "ACTIVE"},
            "market_state": {"last_price": 0.98}
        }
        
        node = EdgeAndRiskCheckNode(
            {
                "conditions": [
                    {"field": "event_state.state", "operator": "==", "value": "ACTIVE"},
                    {"field": "market_state.last_price", "operator": ">=", "value": 0.97}
                ],
                "logic": "AND"
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, ConditionalResult)
        assert result.condition is True
    
    @pytest.mark.asyncio
    async def test_multiple_conditions_and_false(self, graph_context):
        """Test múltiples condiciones AND donde una falla."""
        graph_context.collected_state = {
            "event_state": {"state": "ACTIVE"},
            "market_state": {"last_price": 0.95}  # < 0.97
        }
        
        node = EdgeAndRiskCheckNode(
            {
                "conditions": [
                    {"field": "event_state.state", "operator": "==", "value": "ACTIVE"},
                    {"field": "market_state.last_price", "operator": ">=", "value": 0.97}
                ],
                "logic": "AND"
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, ConditionalResult)
        assert result.condition is False
    
    @pytest.mark.asyncio
    async def test_multiple_conditions_or(self, graph_context):
        """Test múltiples condiciones con lógica OR."""
        graph_context.collected_state = {
            "event_state": {"state": "UPCOMING"},
            "market_state": {"last_price": 0.98}
        }
        
        node = EdgeAndRiskCheckNode(
            {
                "conditions": [
                    {"field": "event_state.state", "operator": "==", "value": "ACTIVE"},
                    {"field": "market_state.last_price", "operator": ">=", "value": 0.97}
                ],
                "logic": "OR"
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, ConditionalResult)
        assert result.condition is True  # Una condición es True
    
    @pytest.mark.asyncio
    async def test_operators(self, graph_context):
        """Test diferentes operadores."""
        graph_context.collected_state = {
            "market_state": {"last_price": 0.98}
        }
        
        # Test >
        node = EdgeAndRiskCheckNode(
            {
                "conditions": [
                    {"field": "market_state.last_price", "operator": ">", "value": 0.97}
                ]
            },
            graph_context
        )
        result = await node.execute()
        assert result.condition is True
        
        # Test <
        node = EdgeAndRiskCheckNode(
            {
                "conditions": [
                    {"field": "market_state.last_price", "operator": "<", "value": 0.99}
                ]
            },
            graph_context
        )
        result = await node.execute()
        assert result.condition is True
        
        # Test !=
        node = EdgeAndRiskCheckNode(
            {
                "conditions": [
                    {"field": "market_state.last_price", "operator": "!=", "value": 0.99}
                ]
            },
            graph_context
        )
        result = await node.execute()
        assert result.condition is True
    
    @pytest.mark.asyncio
    async def test_operator_in(self, graph_context):
        """Test operador 'in'."""
        graph_context.collected_state = {
            "event_state": {"state": "ACTIVE"}
        }
        
        node = EdgeAndRiskCheckNode(
            {
                "conditions": [
                    {"field": "event_state.state", "operator": "in", "value": ["ACTIVE", "LIVE"]}
                ]
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, ConditionalResult)
        assert result.condition is True
    
    @pytest.mark.asyncio
    async def test_no_conditions(self, graph_context):
        """Test sin condiciones."""
        node = EdgeAndRiskCheckNode(
            {"conditions": []},
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, ConditionalResult)
        assert result.condition is True  # Sin condiciones = True
    
    @pytest.mark.asyncio
    async def test_missing_field(self, graph_context):
        """Test con campo faltante."""
        graph_context.collected_state = {}
        
        node = EdgeAndRiskCheckNode(
            {
                "conditions": [
                    {"field": "event_state.state", "operator": "==", "value": "ACTIVE"}
                ]
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, ConditionalResult)
        assert result.condition is False  # Campo faltante = False


class TestCalculateOrderSizeNode:
    """Tests para CalculateOrderSizeNode."""
    
    @pytest.mark.asyncio
    async def test_fixed_range(self, graph_context):
        """Test cálculo con rango fijo."""
        graph_context.collected_state = {
            "market_state": {"last_price": 0.98}
        }
        
        node = CalculateOrderSizeNode(
            {
                "method": "fixed_range",
                "min": 100.0,
                "max": 1000.0
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
        assert hasattr(graph_context, 'calculated_price')
        assert hasattr(graph_context, 'calculated_size')
        assert graph_context.calculated_price == 0.98
        assert graph_context.calculated_size == 1000.0 / 0.98  # max / price
    
    @pytest.mark.asyncio
    async def test_percentage(self, graph_context):
        """Test cálculo con porcentaje."""
        graph_context.collected_state = {
            "market_state": {"last_price": 0.98},
            "risk_state": {"available_bank": 10000.0}
        }
        
        node = CalculateOrderSizeNode(
            {
                "method": "percentage",
                "percentage": 5.0,  # 5%
                "min": 100.0,
                "max": 2000.0
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
        # 5% de 10000 = 500 USDC
        # 500 / 0.98 = ~510.2 shares
        assert graph_context.calculated_price == 0.98
        assert graph_context.calculated_size > 0
    
    @pytest.mark.asyncio
    async def test_missing_price(self, graph_context):
        """Test sin precio disponible."""
        graph_context.collected_state = {}
        
        node = CalculateOrderSizeNode(
            {
                "method": "fixed_range",
                "min": 100.0,
                "max": 1000.0
            },
            graph_context
        )
        
        with pytest.raises(ValueError, match="market price not available"):
            await node.execute()
    
    @pytest.mark.asyncio
    async def test_unknown_method(self, graph_context):
        """Test con método desconocido."""
        graph_context.collected_state = {
            "market_state": {"last_price": 0.98}
        }
        
        node = CalculateOrderSizeNode(
            {
                "method": "unknown_method"
            },
            graph_context
        )
        
        with pytest.raises(ValueError, match="Unknown calculation method"):
            await node.execute()


class TestEmitExecutionIntentNode:
    """Tests para EmitExecutionIntentNode."""
    
    @pytest.mark.asyncio
    async def test_emit_intent_success(self, graph_context):
        """Test emitir intent exitosamente."""
        graph_context.calculated_price = 0.98
        graph_context.calculated_size = 100.0
        graph_context.collected_state = {"test": "data"}
        
        node = EmitExecutionIntentNode(
            {
                "side": "BUY",
                "outcome": "YES",
                "reason": "Test reason"
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, ExecutionIntentResult)
        assert result.intent is not None
        assert result.intent.side == "BUY"
        assert result.intent.outcome == "YES"
        assert result.intent.price == 0.98
        assert result.intent.size == 100.0
        assert result.intent.event_id == graph_context.event_id
        assert result.intent.strategy_id == graph_context.strategy_id
    
    @pytest.mark.asyncio
    async def test_emit_intent_missing_price(self, graph_context):
        """Test emitir intent sin precio."""
        graph_context.calculated_size = 100.0
        
        node = EmitExecutionIntentNode(
            {
                "side": "BUY",
                "outcome": "YES"
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "price" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_emit_intent_missing_size(self, graph_context):
        """Test emitir intent sin tamaño."""
        graph_context.calculated_price = 0.98
        
        node = EmitExecutionIntentNode(
            {
                "side": "BUY",
                "outcome": "YES"
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "size" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_emit_intent_defaults(self, graph_context):
        """Test emitir intent con valores por defecto."""
        graph_context.calculated_price = 0.98
        graph_context.calculated_size = 100.0
        
        node = EmitExecutionIntentNode(
            {},  # Sin config, usa defaults
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, ExecutionIntentResult)
        assert result.intent.side == "BUY"  # Default
        assert result.intent.outcome == "YES"  # Default
        assert result.intent.reason == "Strategy decision"  # Default

