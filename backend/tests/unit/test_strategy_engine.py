"""
Tests unitarios para StrategyEngine.
"""
import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

from app.core.strategy_engine.strategy_engine import StrategyEngine
from app.core.strategy_engine.models import GraphExecutionContext, GraphExecutionResult
from app.core.strategy.models import OrderIntent
from app.models.strategy import Strategy
from app.models.event import Event
from app.models.graph_execution import GraphExecution
from app.models.execution_intent import ExecutionIntent


@pytest.fixture
def mock_db():
    """Mock DB session."""
    db = MagicMock(spec=Session)
    db.add = MagicMock()
    db.commit = MagicMock()
    db.flush = MagicMock()
    return db


@pytest.fixture
def strategy_engine(mock_db):
    """Fixture para StrategyEngine inicializado."""
    engine = StrategyEngine()
    engine.initialize(mock_db)
    return engine


@pytest.fixture
def sample_strategy():
    """Fixture para Strategy de prueba."""
    strategy = Strategy(
        id=uuid4(),
        name="Test Strategy",
        description="Test",
        is_active=True,
        decision_graph={
            "entry_node": "start",
            "nodes": {
                "start": {
                    "type": "noop"
                }
            }
        },
        support_graphs=[],
        control_loop_config={},
        risk_config={}
    )
    return strategy


@pytest.fixture
def sample_event():
    """Fixture para Event de prueba."""
    event = Event(
        id=uuid4(),
        polymarket_event_id="test-event-123",
        market_id=uuid4(),
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        state="ACTIVE"
    )
    return event


class TestStrategyEngine:
    """Tests para StrategyEngine."""
    
    def test_initialize(self, mock_db):
        """Test inicialización de StrategyEngine."""
        engine = StrategyEngine()
        assert engine.state_cache_service is None
        assert engine.graph_runtime is None
        assert engine.control_loop is None
        
        engine.initialize(mock_db)
        
        assert engine.state_cache_service is not None
        assert engine.graph_runtime is not None
        assert engine.control_loop is not None
    
    @pytest.mark.asyncio
    async def test_execute_decision_graph_success(
        self,
        strategy_engine,
        sample_strategy,
        sample_event,
        mock_db
    ):
        """Test ejecutar Decision Graph exitosamente."""
        # Mock GraphRuntime
        mock_intent = OrderIntent(
            event_id=sample_event.id,
            outcome="YES",
            side="BUY",
            price=0.98,
            size=100.0,
            reason="Test",
            strategy_id=sample_strategy.id
        )
        
        mock_result = GraphExecutionResult(
            intents=[mock_intent],
            execution_trace=[{"node": "start", "result": "success"}],
            duration_ms=10.5,
            success=True
        )
        
        strategy_engine.graph_runtime.execute_graph = AsyncMock(return_value=mock_result)
        
        # Ejecutar
        intents = await strategy_engine.execute_decision_graph(
            sample_strategy,
            sample_event,
            mock_db
        )
        
        # Verificar
        assert len(intents) == 1
        assert intents[0] == mock_intent
        
        # Verificar que se guardó GraphExecution
        assert mock_db.add.call_count >= 2  # GraphExecution + ExecutionIntent
        
        # Verificar que se llamó commit
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_decision_graph_failure(
        self,
        strategy_engine,
        sample_strategy,
        sample_event,
        mock_db
    ):
        """Test ejecutar Decision Graph con fallo."""
        # Mock GraphRuntime para que falle
        mock_result = GraphExecutionResult(
            intents=[],
            execution_trace=[],
            duration_ms=5.0,
            success=False,
            error_message="Test error"
        )
        
        strategy_engine.graph_runtime.execute_graph = AsyncMock(return_value=mock_result)
        
        # Ejecutar
        intents = await strategy_engine.execute_decision_graph(
            sample_strategy,
            sample_event,
            mock_db
        )
        
        # Verificar
        assert len(intents) == 0
        
        # Verificar que se guardó GraphExecution con status "failed"
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_decision_graph_exception(
        self,
        strategy_engine,
        sample_strategy,
        sample_event,
        mock_db
    ):
        """Test ejecutar Decision Graph con excepción."""
        # Mock GraphRuntime para que lance excepción
        strategy_engine.graph_runtime.execute_graph = AsyncMock(
            side_effect=ValueError("Test exception")
        )
        
        # Ejecutar y verificar que se lanza excepción
        with pytest.raises(ValueError, match="Test exception"):
            await strategy_engine.execute_decision_graph(
                sample_strategy,
                sample_event,
                mock_db
            )
        
        # Verificar que se guardó GraphExecution con status "failed"
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_support_graph_success(
        self,
        strategy_engine,
        sample_strategy,
        sample_event,
        mock_db
    ):
        """Test ejecutar Support Graph exitosamente."""
        support_graph = {
            "name": "test_support",
            "entry_node": "start",
            "nodes": {
                "start": {
                    "type": "noop"
                }
            }
        }
        
        mock_result = GraphExecutionResult(
            intents=[],
            execution_trace=[],
            duration_ms=50.0,
            success=True
        )
        
        strategy_engine.graph_runtime.execute_graph = AsyncMock(return_value=mock_result)
        
        # Ejecutar
        await strategy_engine.execute_support_graph(
            sample_strategy,
            support_graph,
            sample_event,
            mock_db
        )
        
        # Verificar que se guardó GraphExecution
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_support_graph_exception(
        self,
        strategy_engine,
        sample_strategy,
        sample_event,
        mock_db
    ):
        """Test ejecutar Support Graph con excepción (no debe bloquear)."""
        support_graph = {
            "name": "test_support",
            "entry_node": "start",
            "nodes": {
                "start": {
                    "type": "noop"
                }
            }
        }
        
        # Mock GraphRuntime para que lance excepción
        strategy_engine.graph_runtime.execute_graph = AsyncMock(
            side_effect=ValueError("Test exception")
        )
        
        # Ejecutar (no debe lanzar excepción)
        await strategy_engine.execute_support_graph(
            sample_strategy,
            support_graph,
            sample_event,
            mock_db
        )
        
        # Verificar que se guardó GraphExecution con status "failed"
        mock_db.commit.assert_called_once()
