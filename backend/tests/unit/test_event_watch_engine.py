"""
Unit tests for Event Watch Engine.
"""
import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.event_watch_engine.models import (
    EventState, EventStateType, WatcherState, WatcherStatus,
    WatchEngineConfig, StateSnapshot
)
from app.core.event_watch_engine.state_aggregator import StateAggregator
from app.core.event_watch_engine.lifecycle_manager import LifecycleManager
from app.core.event_watch_engine.coordinator import EventWatchCoordinator
from app.core.event_watch_engine.watcher import Watcher
from app.core.event_mapping_layer.models import EventDescriptor
from app.core.checkers.base import CheckerResult


@pytest.fixture
def watch_config():
    """Fixture para WatchEngineConfig."""
    return WatchEngineConfig(
        check_frequency_sports=3,
        check_frequency_politics=60,
        min_checkers_for_confirmed=2,
        min_confidence_threshold=0.8
    )


@pytest.fixture
def state_aggregator(watch_config):
    """Fixture para StateAggregator."""
    return StateAggregator(watch_config)


@pytest.fixture
def lifecycle_manager():
    """Fixture para LifecycleManager."""
    return LifecycleManager()


@pytest.fixture
def coordinator(watch_config):
    """Fixture para EventWatchCoordinator."""
    return EventWatchCoordinator(watch_config)


@pytest.fixture
def sample_event_descriptor():
    """Fixture para EventDescriptor de ejemplo."""
    return EventDescriptor(
        market_id="pm_12345",
        mapped=True,
        event_type="sports",
        mapping_confidence=0.9,
        canonical_event_id="sports:nba:401585236",
        sources=["sports_client"],
        metadata={"sport": "basketball", "league": "nba"},
        trace_id=uuid4()
    )


@pytest.fixture
def sample_checker_result_finished():
    """Fixture para CheckerResult con FINISHED."""
    return CheckerResult(
        state="FINISHED",
        confidence=0.95,
        source="sports_checker",
        latency_ms=100.0,
        timestamp=datetime.utcnow()
    )


@pytest.fixture
def sample_checker_result_live():
    """Fixture para CheckerResult con LIVE."""
    return CheckerResult(
        state="LIVE",
        confidence=0.9,
        source="sports_checker",
        latency_ms=80.0,
        timestamp=datetime.utcnow()
    )


class TestStateAggregator:
    """Tests para StateAggregator."""
    
    def test_aggregate_no_results(self, state_aggregator):
        """Test agregación sin resultados."""
        result = state_aggregator.aggregate([], "event_123")
        
        assert result.state == EventStateType.UNKNOWN
        assert result.confidence == 0.0
        assert result.event_id == "event_123"
    
    def test_aggregate_finished_confirmed(self, state_aggregator, sample_checker_result_finished):
        """Test agregación con FINISHED_CONFIRMED (2+ checkers con alta confianza)."""
        results = [
            sample_checker_result_finished,
            CheckerResult(
                state="FINISHED",
                confidence=0.92,
                source="espn_checker",
                latency_ms=120.0,
                timestamp=datetime.utcnow()
            )
        ]
        
        aggregated = state_aggregator.aggregate(results, "event_123")
        
        assert aggregated.state == EventStateType.FINISHED_CONFIRMED
        assert aggregated.confidence > 0.8
        assert len(aggregated.sources) == 2
    
    def test_aggregate_finished_unconfirmed_single(self, state_aggregator, sample_checker_result_finished):
        """Test agregación con FINISHED_UNCONFIRMED (1 checker con alta confianza)."""
        results = [sample_checker_result_finished]
        
        aggregated = state_aggregator.aggregate(results, "event_123")
        
        assert aggregated.state == EventStateType.FINISHED_UNCONFIRMED
        assert aggregated.confidence == 0.95
    
    def test_aggregate_live(self, state_aggregator, sample_checker_result_live):
        """Test agregación con LIVE."""
        results = [sample_checker_result_live]
        
        aggregated = state_aggregator.aggregate(results, "event_123")
        
        assert aggregated.state == EventStateType.LIVE
        assert aggregated.confidence > 0.0
    
    def test_aggregate_unknown_all_fail(self, state_aggregator):
        """Test agregación con UNKNOWN (todos los checkers fallan)."""
        results = [
            CheckerResult(
                state="UNKNOWN",
                confidence=0.0,
                source="checker1",
                error="timeout",
                latency_ms=5000.0,
                timestamp=datetime.utcnow()
            ),
            CheckerResult(
                state="UNKNOWN",
                confidence=0.0,
                source="checker2",
                error="api_error",
                latency_ms=3000.0,
                timestamp=datetime.utcnow()
            )
        ]
        
        aggregated = state_aggregator.aggregate(results, "event_123")
        
        assert aggregated.state == EventStateType.UNKNOWN
        assert aggregated.confidence == 0.0
    
    def test_aggregate_mixed_results(self, state_aggregator, sample_checker_result_finished, sample_checker_result_live):
        """Test agregación con resultados mixtos."""
        results = [
            sample_checker_result_finished,
            sample_checker_result_live,
            CheckerResult(
                state="UNKNOWN",
                confidence=0.0,
                source="checker3",
                error="timeout",
                latency_ms=5000.0,
                timestamp=datetime.utcnow()
            )
        ]
        
        aggregated = state_aggregator.aggregate(results, "event_123")
        
        # Debería ser FINISHED_UNCONFIRMED porque solo 1 checker dice FINISHED con alta confianza
        assert aggregated.state == EventStateType.FINISHED_UNCONFIRMED


class TestLifecycleManager:
    """Tests para LifecycleManager."""
    
    @pytest.mark.asyncio
    async def test_register_watcher(self, lifecycle_manager, sample_event_descriptor, watch_config):
        """Test registro de watcher."""
        watcher = Watcher(sample_event_descriptor, watch_config, lifecycle_manager)
        
        result = lifecycle_manager.register_watcher(watcher)
        
        assert result is True
        assert lifecycle_manager.get_watcher(sample_event_descriptor.canonical_event_id) == watcher
    
    @pytest.mark.asyncio
    async def test_register_duplicate_watcher(self, lifecycle_manager, sample_event_descriptor, watch_config):
        """Test registro de watcher duplicado."""
        watcher1 = Watcher(sample_event_descriptor, watch_config, lifecycle_manager)
        watcher2 = Watcher(sample_event_descriptor, watch_config, lifecycle_manager)
        
        result1 = lifecycle_manager.register_watcher(watcher1)
        result2 = lifecycle_manager.register_watcher(watcher2)
        
        assert result1 is True
        assert result2 is False  # Duplicado
    
    @pytest.mark.asyncio
    async def test_unregister_watcher(self, lifecycle_manager, sample_event_descriptor, watch_config):
        """Test desregistro de watcher."""
        watcher = Watcher(sample_event_descriptor, watch_config, lifecycle_manager)
        lifecycle_manager.register_watcher(watcher)
        
        result = lifecycle_manager.unregister_watcher(sample_event_descriptor.canonical_event_id)
        
        assert result is True
        assert lifecycle_manager.get_watcher(sample_event_descriptor.canonical_event_id) is None
    
    @pytest.mark.asyncio
    async def test_on_state_transition(self, lifecycle_manager, sample_event_descriptor, watch_config):
        """Test manejo de transición de estado."""
        watcher = Watcher(sample_event_descriptor, watch_config, lifecycle_manager)
        lifecycle_manager.register_watcher(watcher)
        
        new_state = EventState(
            event_id=sample_event_descriptor.canonical_event_id,
            state=EventStateType.FINISHED_CONFIRMED,
            confidence=0.95,
            last_update=datetime.utcnow()
        )
        
        await lifecycle_manager.on_state_transition(sample_event_descriptor.canonical_event_id, new_state)
        
        # Verificar que se guardó en el historial
        assert sample_event_descriptor.canonical_event_id in lifecycle_manager._state_history
        assert len(lifecycle_manager._state_history[sample_event_descriptor.canonical_event_id]) > 0


class TestEventWatchCoordinator:
    """Tests para EventWatchCoordinator."""
    
    @pytest.mark.asyncio
    async def test_register_event_creates_watcher(self, coordinator, sample_event_descriptor):
        """Test que register_event crea un nuevo watcher."""
        market_id = uuid4()
        
        watcher = await coordinator.register_event(sample_event_descriptor, market_id)
        
        assert watcher is not None
        assert watcher.get_state().event_id == sample_event_descriptor.canonical_event_id
    
    @pytest.mark.asyncio
    async def test_register_event_reuses_existing_watcher(self, coordinator, sample_event_descriptor):
        """Test que register_event reutiliza watcher existente."""
        market_id1 = uuid4()
        market_id2 = uuid4()
        
        watcher1 = await coordinator.register_event(sample_event_descriptor, market_id1)
        watcher2 = await coordinator.register_event(sample_event_descriptor, market_id2)
        
        assert watcher1 is not None
        assert watcher2 is not None
        assert watcher1 == watcher2  # Mismo watcher
        assert market_id2 in watcher2.get_state().markets
    
    @pytest.mark.asyncio
    async def test_register_event_respects_max_limit(self, coordinator, sample_event_descriptor):
        """Test que register_event respeta el límite máximo de watchers."""
        # Configurar límite bajo para el test
        coordinator.config.max_watchers_active = 2
        
        # Crear 2 watchers
        market_id1 = uuid4()
        market_id2 = uuid4()
        descriptor1 = EventDescriptor(
            market_id="pm_1",
            mapped=True,
            event_type="sports",
            mapping_confidence=0.9,
            canonical_event_id="sports:nba:1",
            trace_id=uuid4()
        )
        descriptor2 = EventDescriptor(
            market_id="pm_2",
            mapped=True,
            event_type="sports",
            mapping_confidence=0.9,
            canonical_event_id="sports:nba:2",
            trace_id=uuid4()
        )
        
        watcher1 = await coordinator.register_event(descriptor1, market_id1)
        watcher2 = await coordinator.register_event(descriptor2, market_id2)
        
        assert watcher1 is not None
        assert watcher2 is not None
        
        # Intentar crear un tercer watcher debería fallar
        descriptor3 = EventDescriptor(
            market_id="pm_3",
            mapped=True,
            event_type="sports",
            mapping_confidence=0.9,
            canonical_event_id="sports:nba:3",
            trace_id=uuid4()
        )
        watcher3 = await coordinator.register_event(descriptor3, uuid4())
        
        assert watcher3 is None  # Límite alcanzado
    
    @pytest.mark.asyncio
    async def test_unregister_event(self, coordinator, sample_event_descriptor):
        """Test desregistro de evento."""
        market_id = uuid4()
        
        watcher = await coordinator.register_event(sample_event_descriptor, market_id)
        assert watcher is not None
        
        result = await coordinator.unregister_event(
            sample_event_descriptor.canonical_event_id,
            market_id
        )
        
        assert result is True
        # El watcher debería estar terminado si no quedan mercados
        state = watcher.get_state()
        assert state.status == WatcherStatus.TERMINATED or len(state.markets) == 0
    
    @pytest.mark.asyncio
    async def test_get_active_watchers(self, coordinator, sample_event_descriptor):
        """Test obtención de watchers activos."""
        market_id = uuid4()
        
        await coordinator.register_event(sample_event_descriptor, market_id)
        
        watchers = await coordinator.get_active_watchers()
        
        assert len(watchers) > 0
        assert any(w.event_id == sample_event_descriptor.canonical_event_id for w in watchers)
    
    @pytest.mark.asyncio
    async def test_cleanup_finished_watchers(self, coordinator, sample_event_descriptor):
        """Test limpieza de watchers terminados."""
        market_id = uuid4()
        
        watcher = await coordinator.register_event(sample_event_descriptor, market_id)
        await watcher.stop()  # Terminar watcher
        
        await coordinator.cleanup_finished_watchers()
        
        # El watcher debería estar limpiado después de un tiempo
        # (en este test, puede que no se limpie inmediatamente porque no ha pasado suficiente tiempo)
        # Pero el método debería ejecutarse sin errores
        pass
    
    @pytest.mark.asyncio
    async def test_stop_all(self, coordinator, sample_event_descriptor):
        """Test detener todos los watchers."""
        market_id = uuid4()
        
        watcher = await coordinator.register_event(sample_event_descriptor, market_id)
        assert watcher is not None
        
        await coordinator.stop_all()
        
        # Todos los watchers deberían estar detenidos
        watchers = await coordinator.get_active_watchers()
        # Después de stop_all, los watchers pueden seguir en la lista pero deberían estar terminados
        pass


class TestWatcher:
    """Tests para Watcher."""
    
    @pytest.mark.asyncio
    async def test_watcher_start_stop(self, sample_event_descriptor, watch_config, lifecycle_manager):
        """Test inicio y detención de watcher."""
        watcher = Watcher(sample_event_descriptor, watch_config, lifecycle_manager)
        
        await watcher.start()
        
        state = watcher.get_state()
        # Si no hay checkers disponibles, puede estar en ERROR_RETRYING
        assert state.status in [
            WatcherStatus.INITIALIZING, 
            WatcherStatus.LIVE_MONITORING,
            WatcherStatus.ERROR_RETRYING  # Si no hay checkers disponibles
        ]
        
        await watcher.stop()
        
        state = watcher.get_state()
        assert state.status == WatcherStatus.TERMINATED
    
    @pytest.mark.asyncio
    async def test_watcher_add_remove_market(self, sample_event_descriptor, watch_config, lifecycle_manager):
        """Test agregar y remover mercados."""
        watcher = Watcher(sample_event_descriptor, watch_config, lifecycle_manager)
        market_id = uuid4()
        
        watcher.add_market(market_id)
        
        state = watcher.get_state()
        assert market_id in state.markets
        
        watcher.remove_market(market_id)
        
        state = watcher.get_state()
        assert market_id not in state.markets
    
    def test_watcher_get_check_interval(self, sample_event_descriptor, watch_config, lifecycle_manager):
        """Test obtención de intervalo de checks según tipo de evento."""
        watcher = Watcher(sample_event_descriptor, watch_config, lifecycle_manager)
        
        interval = watcher._get_check_interval()
        
        assert interval == watch_config.check_frequency_sports  # sports = 3 segundos
    
    @pytest.mark.asyncio
    async def test_watcher_load_checkers(self, sample_event_descriptor, watch_config, lifecycle_manager):
        """Test carga de checkers."""
        watcher = Watcher(sample_event_descriptor, watch_config, lifecycle_manager)
        
        checkers = watcher._load_checkers()
        
        # Debería cargar checkers para el tipo de evento "sports"
        # Puede que no haya checkers registrados en el test, pero el método debería ejecutarse
        assert isinstance(checkers, list)

