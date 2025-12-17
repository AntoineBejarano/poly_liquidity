"""
Tests unitarios para ControlLoop.
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

from app.core.strategy_engine.control_loop import ControlLoop
from app.core.strategy_engine.strategy_engine import StrategyEngine
from app.models.strategy import Strategy
from app.models.event import Event
from app.models.strategy_event import StrategyEvent


@pytest.fixture
def mock_db():
    """Mock DB session."""
    db = MagicMock(spec=Session)
    db.query = MagicMock()
    return db


@pytest.fixture
def strategy_engine(mock_db):
    """Fixture para StrategyEngine."""
    engine = StrategyEngine()
    engine.initialize(mock_db)
    return engine


@pytest.fixture
def control_loop(strategy_engine):
    """Fixture para ControlLoop."""
    return ControlLoop(strategy_engine)


@pytest.fixture
def sample_strategy():
    """Fixture para Strategy de prueba."""
    return Strategy(
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


@pytest.fixture
def sample_event():
    """Fixture para Event de prueba."""
    return Event(
        id=uuid4(),
        polymarket_event_id="test-event-123",
        market_id=uuid4(),
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        state="ACTIVE"
    )


@pytest.fixture
def sample_strategy_event(sample_strategy, sample_event):
    """Fixture para StrategyEvent de prueba."""
    return StrategyEvent(
        id=uuid4(),
        strategy_id=sample_strategy.id,
        event_id=sample_event.id,
        observation_started_at=None,
        observation_ended_at=None,
        event_config=None
    )


class TestControlLoop:
    """Tests para ControlLoop."""
    
    def test_init(self, strategy_engine):
        """Test inicialización de ControlLoop."""
        loop = ControlLoop(strategy_engine)
        
        assert loop.strategy_engine == strategy_engine
        assert len(loop.active_strategies) == 0
        assert loop.running is False
    
    @pytest.mark.asyncio
    async def test_load_active_strategies(
        self,
        control_loop,
        sample_strategy,
        mock_db
    ):
        """Test cargar estrategias activas."""
        # Mock query
        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_query.all = MagicMock(return_value=[sample_strategy])
        mock_db.query = MagicMock(return_value=mock_query)
        
        await control_loop.load_active_strategies(mock_db)
        
        assert len(control_loop.active_strategies) == 1
        assert sample_strategy.id in control_loop.active_strategies
    
    @pytest.mark.asyncio
    async def test_should_observe_active_event(
        self,
        control_loop,
        sample_strategy,
        sample_event,
        sample_strategy_event
    ):
        """Test _should_observe con evento activo."""
        result = control_loop._should_observe(
            sample_strategy,
            sample_event,
            sample_strategy_event
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_should_observe_finished_event(
        self,
        control_loop,
        sample_strategy,
        sample_strategy_event
    ):
        """Test _should_observe con evento finalizado."""
        finished_event = Event(
            id=uuid4(),
            polymarket_event_id="test-event-456",
            market_id=uuid4(),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            state="FINISHED"
        )
        
        result = control_loop._should_observe(
            sample_strategy,
            finished_event,
            sample_strategy_event
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_should_observe_before_start_time(
        self,
        control_loop,
        sample_strategy,
        sample_event
    ):
        """Test _should_observe antes de observation_started_at."""
        strategy_event = StrategyEvent(
            id=uuid4(),
            strategy_id=sample_strategy.id,
            event_id=sample_event.id,
            observation_started_at=datetime.utcnow() + timedelta(hours=1),
            observation_ended_at=None,
            event_config=None
        )
        
        result = control_loop._should_observe(
            sample_strategy,
            sample_event,
            strategy_event
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_should_observe_after_end_time(
        self,
        control_loop,
        sample_strategy,
        sample_event
    ):
        """Test _should_observe después de observation_ended_at."""
        strategy_event = StrategyEvent(
            id=uuid4(),
            strategy_id=sample_strategy.id,
            event_id=sample_event.id,
            observation_started_at=None,
            observation_ended_at=datetime.utcnow() - timedelta(hours=1),
            event_config=None
        )
        
        result = control_loop._should_observe(
            sample_strategy,
            sample_event,
            strategy_event
        )
        
        assert result is False
    
    def test_check_triggers(self, control_loop, sample_strategy, sample_event):
        """Test _check_triggers."""
        result = control_loop._check_triggers(sample_strategy, sample_event)
        
        # Por ahora, siempre retorna True
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_support_graph_trigger_always(
        self,
        control_loop,
        sample_event
    ):
        """Test _check_support_graph_trigger con tipo 'always'."""
        support_graph = {
            "name": "test",
            "trigger": {
                "type": "always"
            }
        }
        
        result = control_loop._check_support_graph_trigger(support_graph, sample_event)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_support_graph_trigger_timer(
        self,
        control_loop,
        sample_event
    ):
        """Test _check_support_graph_trigger con tipo 'timer'."""
        support_graph = {
            "name": "test",
            "trigger": {
                "type": "timer"
            }
        }
        
        result = control_loop._check_support_graph_trigger(support_graph, sample_event)
        
        # Por ahora, siempre retorna True
        assert result is True
    
    @pytest.mark.asyncio
    async def test_tick_executes_decision_graph(
        self,
        control_loop,
        sample_strategy,
        sample_event,
        sample_strategy_event,
        mock_db
    ):
        """Test que tick ejecuta Decision Graph cuando corresponde."""
        # Configurar active_strategies
        control_loop.active_strategies = {sample_strategy.id: sample_strategy}
        
        # Asociar evento al strategy_event
        sample_strategy_event.event = sample_event
        
        # Mock query para StrategyEvent
        mock_strategy_event_query = MagicMock()
        mock_strategy_event_query.filter = MagicMock(return_value=mock_strategy_event_query)
        mock_strategy_event_query.all = MagicMock(return_value=[sample_strategy_event])
        
        # Mock query general
        def query_side_effect(model):
            if model == StrategyEvent:
                return mock_strategy_event_query
            return MagicMock()
        
        mock_db.query = MagicMock(side_effect=query_side_effect)
        
        # Mock execute_decision_graph
        control_loop.strategy_engine.execute_decision_graph = AsyncMock()
        
        # Ejecutar tick
        await control_loop.tick(mock_db)
        
        # Verificar que se llamó execute_decision_graph
        control_loop.strategy_engine.execute_decision_graph.assert_called_once_with(
            sample_strategy,
            sample_event,
            mock_db
        )
    
    @pytest.mark.asyncio
    async def test_tick_skips_finished_event(
        self,
        control_loop,
        sample_strategy,
        sample_strategy_event,
        mock_db
    ):
        """Test que tick omite eventos finalizados."""
        finished_event = Event(
            id=uuid4(),
            polymarket_event_id="test-event-456",
            market_id=uuid4(),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            state="FINISHED"
        )
        
        strategy_event = StrategyEvent(
            id=uuid4(),
            strategy_id=sample_strategy.id,
            event_id=finished_event.id,
            observation_started_at=None,
            observation_ended_at=None,
            event_config=None
        )
        strategy_event.event = finished_event
        
        # Configurar active_strategies
        control_loop.active_strategies = {sample_strategy.id: sample_strategy}
        
        # Mock query
        mock_strategy_event_query = MagicMock()
        mock_strategy_event_query.filter = MagicMock(return_value=mock_strategy_event_query)
        mock_strategy_event_query.all = MagicMock(return_value=[strategy_event])
        
        def query_side_effect(model):
            if model == StrategyEvent:
                return mock_strategy_event_query
            return MagicMock()
        
        mock_db.query = MagicMock(side_effect=query_side_effect)
        
        # Mock execute_decision_graph
        control_loop.strategy_engine.execute_decision_graph = AsyncMock()
        
        # Ejecutar tick
        await control_loop.tick(mock_db)
        
        # Verificar que NO se llamó execute_decision_graph
        control_loop.strategy_engine.execute_decision_graph.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_stop(self, control_loop):
        """Test detener ControlLoop."""
        control_loop.running = True
        
        await control_loop.stop()
        
        assert control_loop.running is False

