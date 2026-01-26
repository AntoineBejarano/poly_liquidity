"""
Tests unitarios para GraphRuntime.
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.core.strategy_engine.graph_runtime import GraphRuntime
from app.core.strategy_engine.models import GraphExecutionContext, GraphExecutionResult
from app.core.strategy_engine.nodes.base import (
    GraphNode,
    SuccessResult,
    ConditionalResult,
    ExecutionIntentResult,
    FailureResult
)
from app.core.strategy.models import OrderIntent
from app.core.strategy_engine.nodes.noop import NoOpNode


@pytest.fixture
def mock_state_cache():
    """Mock StateCacheService."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


@pytest.fixture
def graph_runtime(mock_state_cache):
    """Fixture para GraphRuntime."""
    runtime = GraphRuntime(mock_state_cache)
    return runtime


@pytest.fixture
def graph_context(mock_state_cache):
    """Fixture para GraphExecutionContext."""
    return GraphExecutionContext(
        strategy_id=uuid4(),
        event_id=uuid4(),
        market_id=uuid4(),
        trace_id=uuid4(),
        state_cache=mock_state_cache
    )


class TestNoOpNode:
    """Test para NoOpNode."""
    
    @pytest.mark.asyncio
    async def test_noop_execute(self, graph_context):
        """Test que NoOpNode ejecuta correctamente."""
        node = NoOpNode({}, graph_context)
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)


class TestGraphRuntime:
    """Tests para GraphRuntime."""
    
    @pytest.mark.asyncio
    async def test_execute_graph_simple(self, graph_runtime, graph_context):
        """Test ejecutar un grafo simple con NoOp."""
        graph_runtime.register_node("noop", NoOpNode)
        
        graph = {
            "entry_node": "start",
            "nodes": {
                "start": {
                    "type": "noop"
                }
            }
        }
        
        result = await graph_runtime.execute_graph(graph, graph_context)
        
        assert isinstance(result, GraphExecutionResult)
        assert result.success is True
        assert len(result.intents) == 0
        assert len(result.execution_trace) == 1
        assert result.execution_trace[0]["node_id"] == "start"
        assert result.execution_trace[0]["node_type"] == "noop"
        assert result.duration_ms >= 0
    
    @pytest.mark.asyncio
    async def test_execute_graph_sequential(self, graph_runtime, graph_context):
        """Test ejecutar un grafo secuencial con múltiples nodos."""
        graph_runtime.register_node("noop", NoOpNode)
        
        # Crear un nodo mock que retorna SuccessResult
        class MockNode(GraphNode):
            async def execute(self):
                return SuccessResult()
        
        graph_runtime.register_node("mock", MockNode)
        
        graph = {
            "entry_node": "start",
            "nodes": {
                "start": {
                    "type": "mock",
                    "next": "end"
                },
                "end": {
                    "type": "noop"
                }
            }
        }
        
        result = await graph_runtime.execute_graph(graph, graph_context)
        
        assert result.success is True
        assert len(result.execution_trace) == 2
        assert result.execution_trace[0]["node_id"] == "start"
        assert result.execution_trace[1]["node_id"] == "end"
    
    @pytest.mark.asyncio
    async def test_execute_graph_conditional(self, graph_runtime, graph_context):
        """Test ejecutar un grafo con condiciones."""
        # Crear nodo mock que retorna ConditionalResult
        class ConditionalNode(GraphNode):
            def __init__(self, config, context):
                super().__init__(config, context)
                self.condition_value = config.get("condition", True)
            
            async def execute(self):
                return ConditionalResult(self.condition_value)
        
        graph_runtime.register_node("conditional", ConditionalNode)
        graph_runtime.register_node("noop", NoOpNode)
        
        graph = {
            "entry_node": "check",
            "nodes": {
                "check": {
                    "type": "conditional",
                    "config": {"condition": True},
                    "on_true": "success",
                    "on_false": "failure"
                },
                "success": {
                    "type": "noop"
                },
                "failure": {
                    "type": "noop"
                }
            }
        }
        
        result = await graph_runtime.execute_graph(graph, graph_context)
        
        assert result.success is True
        assert len(result.execution_trace) == 2
        assert result.execution_trace[0]["node_id"] == "check"
        assert result.execution_trace[1]["node_id"] == "success"  # on_true
    
    @pytest.mark.asyncio
    async def test_execute_graph_conditional_false(self, graph_runtime, graph_context):
        """Test ejecutar un grafo con condición False."""
        class ConditionalNode(GraphNode):
            def __init__(self, config, context):
                super().__init__(config, context)
                self.condition_value = config.get("condition", False)
            
            async def execute(self):
                return ConditionalResult(self.condition_value)
        
        graph_runtime.register_node("conditional", ConditionalNode)
        graph_runtime.register_node("noop", NoOpNode)
        
        graph = {
            "entry_node": "check",
            "nodes": {
                "check": {
                    "type": "conditional",
                    "config": {"condition": False},
                    "on_true": "success",
                    "on_false": "failure"
                },
                "success": {
                    "type": "noop"
                },
                "failure": {
                    "type": "noop"
                }
            }
        }
        
        result = await graph_runtime.execute_graph(graph, graph_context)
        
        assert result.success is True
        assert len(result.execution_trace) == 2
        assert result.execution_trace[1]["node_id"] == "failure"  # on_false
    
    @pytest.mark.asyncio
    async def test_execute_graph_with_intent(self, graph_runtime, graph_context):
        """Test ejecutar un grafo que emite un ExecutionIntent."""
        class IntentNode(GraphNode):
            async def execute(self):
                intent = OrderIntent(
                    side="YES",
                    outcome="YES",
                    target_price=0.98,
                    price=0.98,  # Campo requerido
                    size=100.0,
                    size_usdc=98.0,
                    reason="test",
                    event_id=graph_context.event_id  # Campo requerido
                )
                return ExecutionIntentResult(intent)
        
        graph_runtime.register_node("emit_intent", IntentNode)
        graph_runtime.register_node("noop", NoOpNode)
        
        graph = {
            "entry_node": "emit",
            "nodes": {
                "emit": {
                    "type": "emit_intent",
                    "next": "end"
                },
                "end": {
                    "type": "noop"
                }
            }
        }
        
        result = await graph_runtime.execute_graph(graph, graph_context)
        
        assert result.success is True
        assert len(result.intents) == 1
        assert result.intents[0].side == "YES"
        assert result.intents[0].price == 0.98
    
    @pytest.mark.asyncio
    async def test_execute_graph_with_failure(self, graph_runtime, graph_context):
        """Test ejecutar un grafo que falla."""
        class FailingNode(GraphNode):
            async def execute(self):
                return FailureResult("Test error")
        
        graph_runtime.register_node("fail", FailingNode)
        
        graph = {
            "entry_node": "fail",
            "nodes": {
                "fail": {
                    "type": "fail"
                }
            }
        }
        
        result = await graph_runtime.execute_graph(graph, graph_context)
        
        assert result.success is False
        assert result.error_message == "Test error"
        assert len(result.execution_trace) == 1
    
    @pytest.mark.asyncio
    async def test_execute_graph_missing_entry_node(self, graph_runtime, graph_context):
        """Test ejecutar un grafo sin entry_node."""
        graph = {
            "nodes": {
                "start": {"type": "noop"}
            }
        }
        
        result = await graph_runtime.execute_graph(graph, graph_context)
        
        assert result.success is False
        assert "entry_node" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_graph_unknown_node_type(self, graph_runtime, graph_context):
        """Test ejecutar un grafo con tipo de nodo desconocido."""
        graph = {
            "entry_node": "start",
            "nodes": {
                "start": {
                    "type": "unknown_node_type"
                }
            }
        }
        
        result = await graph_runtime.execute_graph(graph, graph_context)
        
        assert result.success is False
        assert "unknown" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_graph_node_exception(self, graph_runtime, graph_context):
        """Test que las excepciones en nodos se capturan correctamente."""
        class ExceptionNode(GraphNode):
            async def execute(self):
                raise ValueError("Node exception")
        
        graph_runtime.register_node("exception", ExceptionNode)
        
        graph = {
            "entry_node": "start",
            "nodes": {
                "start": {
                    "type": "exception"
                }
            }
        }
        
        result = await graph_runtime.execute_graph(graph, graph_context)
        
        assert result.success is False
        assert result.error_message is not None
        assert "node exception" in result.error_message.lower() or "error" in result.error_message.lower()
        assert len(result.execution_trace) == 1
    
    @pytest.mark.asyncio
    async def test_register_node(self, graph_runtime):
        """Test registrar un nodo."""
        class TestNode(GraphNode):
            async def execute(self):
                return SuccessResult()
        
        graph_runtime.register_node("test", TestNode)
        
        assert "test" in graph_runtime.node_registry
        assert graph_runtime.node_registry["test"] == TestNode

