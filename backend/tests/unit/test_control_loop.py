"""
Tests unitarios para ControlLoop.
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime, timedelta, timezone
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
            observation_started_at=datetime.now(timezone.utc) + timedelta(hours=1),
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
            observation_ended_at=datetime.now(timezone.utc) - timedelta(hours=1),
            event_config=None
        )
        
        result = control_loop._should_observe(
            sample_strategy,
            sample_event,
            strategy_event
        )
        
        assert result is False
    
    def test_evaluate_triggers(self, control_loop, sample_strategy, sample_event):
        """Test _evaluate_triggers (anteriormente _check_triggers)."""
        result = control_loop._evaluate_triggers(sample_strategy, sample_event)
        
        # Sin triggers definidos, retorna True por defecto
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


class TestControlLoopRefreshStrategies:
    """Tests para refresh de estrategias activas (DoD 4.1)."""

    @pytest.fixture
    def strategy_engine(self, mock_db):
        """Fixture para StrategyEngine."""
        engine = StrategyEngine()
        engine.initialize(mock_db)
        return engine

    @pytest.fixture
    def control_loop(self, strategy_engine):
        """Fixture para ControlLoop."""
        return ControlLoop(strategy_engine)

    @pytest.fixture
    def mock_db(self):
        """Mock DB session."""
        db = MagicMock(spec=Session)
        db.query = MagicMock()
        return db

    @pytest.mark.asyncio
    async def test_refresh_adds_newly_activated_strategy(self, control_loop, mock_db):
        """DoD 4.1: Estrategia activada por API se añade a active_strategies."""
        # Loop arranca vacío
        control_loop.active_strategies = {}

        # Simular estrategia activada en DB
        new_strategy = Strategy(
            id=uuid4(),
            name="Newly Activated",
            is_active=True,
            decision_graph={},
            support_graphs=[],
            control_loop_config={},
            risk_config={},
        )
        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_query.all = MagicMock(return_value=[new_strategy])
        mock_db.query.return_value = mock_query

        await control_loop._refresh_active_strategies(mock_db)

        assert new_strategy.id in control_loop.active_strategies
        assert control_loop.active_strategies[new_strategy.id] == new_strategy

    @pytest.mark.asyncio
    async def test_refresh_removes_deactivated_strategy(self, control_loop, mock_db):
        """DoD 4.1: Estrategia desactivada por API se elimina de active_strategies."""
        old_strategy = Strategy(
            id=uuid4(),
            name="Was Active",
            is_active=False,  # Ya desactivada en DB
            decision_graph={},
            support_graphs=[],
            control_loop_config={},
            risk_config={},
        )
        # Loop tenía la estrategia activa
        control_loop.active_strategies = {old_strategy.id: old_strategy}

        # Simular que la DB ya no la reporta como activa
        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_query.all = MagicMock(return_value=[])  # vacío
        mock_db.query.return_value = mock_query

        await control_loop._refresh_active_strategies(mock_db)

        assert old_strategy.id not in control_loop.active_strategies

    @pytest.mark.asyncio
    async def test_rapid_activate_deactivate_no_ghost(self, control_loop, mock_db):
        """DoD 4.1 (4a): Activar y desactivar rápido no deja estrategia fantasma."""
        strategy = Strategy(
            id=uuid4(),
            name="Rapid Toggle",
            is_active=True,
            decision_graph={},
            support_graphs=[],
            control_loop_config={},
            risk_config={},
        )
        control_loop.active_strategies = {}

        # Primera refresh: estrategia activa
        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_query.all = MagicMock(return_value=[strategy])
        mock_db.query.return_value = mock_query
        await control_loop._refresh_active_strategies(mock_db)
        assert strategy.id in control_loop.active_strategies

        # Segunda refresh inmediata: estrategia desactivada en DB
        mock_query.all = MagicMock(return_value=[])
        await control_loop._refresh_active_strategies(mock_db)
        assert strategy.id not in control_loop.active_strategies

    @pytest.mark.asyncio
    async def test_batch_activation_all_considered(self, control_loop, mock_db):
        """DoD 4.1 (4c): Varias estrategias activadas en ráfaga se añaden todas."""
        strategies = [
            Strategy(
                id=uuid4(),
                name=f"Batch {i}",
                is_active=True,
                decision_graph={},
                support_graphs=[],
                control_loop_config={},
                risk_config={},
            )
            for i in range(3)
        ]
        control_loop.active_strategies = {}

        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_query.all = MagicMock(return_value=strategies)
        mock_db.query.return_value = mock_query

        await control_loop._refresh_active_strategies(mock_db)

        for s in strategies:
            assert s.id in control_loop.active_strategies

    @pytest.mark.asyncio
    async def test_tick_triggers_refresh_at_interval(self, control_loop, mock_db):
        """DoD 4.1: El tick invoca refresh cada _refresh_strategies_interval ticks."""
        control_loop._refresh_strategies_interval = 2  # Cada 2 ticks
        control_loop._refresh_strategies_counter = 0
        control_loop.active_strategies = {}

        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_query.all = MagicMock(return_value=[])
        mock_db.query.return_value = mock_query

        # Primer tick: counter=1, no refresh aún
        await control_loop.tick(mock_db)
        assert control_loop._refresh_strategies_counter == 1

        # Segundo tick: counter=2 >= interval, hace refresh y resetea
        await control_loop.tick(mock_db)
        assert control_loop._refresh_strategies_counter == 0
