"""
Unit tests for Historical Replay.

Según especificación en docs/services/historical_replay.md
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from uuid import uuid4
from app.core.historical_replay import EventStore, ReplayEngine, StrategyComparator
from app.models.event_log import EventLog


class TestEventStore:
    """Test cases for Event Store."""
    
    @pytest.mark.asyncio
    async def test_event_store_initialization(self, db_session):
        """Test Event Store initializes correctly."""
        def get_db():
            return db_session
        store = EventStore(storage_type="sqlite", db_session_factory=get_db)
        assert store is not None
        assert store.storage_type == "sqlite"
        store.close()
    
    @pytest.mark.asyncio
    async def test_store_event(self, db_session):
        """Test storing an event."""
        def get_db():
            return db_session
        store = EventStore(storage_type="sqlite", db_session_factory=get_db)
        
        event = {
            "type": "strategy_intent_created",
            "timestamp": datetime.utcnow(),
            "trace_id": str(uuid4()),
            "market_id": "pm123",
            "target_price": 0.979,
            "size": 5000.0
        }
        
        result = await store.store_event(event)
        assert result is True
        
        # Verificar que se guardó en DB
        events = await store.get_events(event_type="strategy_intent_created")
        assert len(events) > 0
        assert events[0]["type"] == "strategy_intent_created"
        assert events[0]["market_id"] == "pm123"
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_get_events_filtered(self, db_session):
        """Test getting filtered events."""
        def get_db():
            return db_session
        store = EventStore(storage_type="sqlite", db_session_factory=get_db)
        
        # Crear varios eventos
        trace_id = str(uuid4())
        market_id = "pm123"
        
        event1 = {
            "type": "strategy_intent_created",
            "timestamp": datetime.utcnow(),
            "trace_id": trace_id,
            "market_id": market_id
        }
        
        event2 = {
            "type": "risk_decision",
            "timestamp": datetime.utcnow(),
            "trace_id": trace_id,
            "market_id": market_id
        }
        
        await store.store_event(event1)
        await store.store_event(event2)
        
        # Filtrar por tipo
        strategy_events = await store.get_events(event_type="strategy_intent_created")
        assert len(strategy_events) > 0
        assert all(e["type"] == "strategy_intent_created" for e in strategy_events)
        
        # Filtrar por trace_id
        trace_events = await store.get_events(trace_id=trace_id)
        assert len(trace_events) >= 2
        
        # Filtrar por market_id
        market_events = await store.get_events(market_id=market_id)
        assert len(market_events) >= 2
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_get_timeline(self, db_session):
        """Test getting timeline."""
        def get_db():
            return db_session
        store = EventStore(storage_type="sqlite", db_session_factory=get_db)
        
        market_id = "pm123"
        base_time = datetime.utcnow()
        
        # Crear eventos con diferentes timestamps
        for i in range(3):
            event = {
                "type": f"event_{i}",
                "timestamp": base_time + timedelta(seconds=i),
                "market_id": market_id
            }
            await store.store_event(event)
        
        timeline = await store.get_timeline(market_id=market_id)
        assert len(timeline) >= 3
        
        # Verificar orden
        timestamps = [datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) for e in timeline]
        assert timestamps == sorted(timestamps)
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_rewind_to_timestamp(self, db_session):
        """Test rewinding to a timestamp."""
        def get_db():
            return db_session
        store = EventStore(storage_type="sqlite", db_session_factory=get_db)
        
        base_time = datetime.utcnow()
        
        # Crear eventos
        event1 = {
            "type": "risk_decision",
            "timestamp": base_time,
            "market_id": "pm123",
            "approved": True,
            "final_size": 5000.0,
            "price": 0.979
        }
        
        event2 = {
            "type": "runtime_mode_changed",
            "timestamp": base_time + timedelta(seconds=1),
            "from": "GREEN",
            "to": "YELLOW"
        }
        
        await store.store_event(event1)
        await store.store_event(event2)
        
        # Rewindear a un timestamp intermedio
        rewind_time = base_time + timedelta(milliseconds=500)
        system_state = await store.rewind_to_timestamp(rewind_time)
        
        assert system_state is not None
        assert "timestamp" in system_state
        assert "exposure_total" in system_state
        assert "runtime_mode" in system_state
        
        store.close()


class TestReplayEngine:
    """Test cases for Replay Engine."""
    
    @pytest.mark.asyncio
    async def test_replay_engine_initialization(self, db_session):
        """Test Replay Engine initializes correctly."""
        def get_db():
            return db_session
        store = EventStore(storage_type="sqlite", db_session_factory=get_db)
        engine = ReplayEngine(store)
        assert engine is not None
        store.close()
    
    @pytest.mark.asyncio
    async def test_replay_market(self, db_session):
        """Test replaying market events."""
        def get_db():
            return db_session
        store = EventStore(storage_type="sqlite", db_session_factory=get_db)
        engine = ReplayEngine(store)
        
        market_id = "pm123"
        base_time = datetime.utcnow()
        
        # Crear eventos
        for i in range(3):
            event = {
                "type": f"event_{i}",
                "timestamp": base_time + timedelta(seconds=i),
                "market_id": market_id
            }
            await store.store_event(event)
        
        events = await engine.replay_market(market_id=market_id)
        assert len(events) >= 3
        
        # Verificar que tienen tiempos relativos
        if events:
            assert "relative_time_ms" in events[0]
            assert "t" in events[0]
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_replay_step_by_step(self, db_session):
        """Test replaying step by step."""
        def get_db():
            return db_session
        store = EventStore(storage_type="sqlite", db_session_factory=get_db)
        engine = ReplayEngine(store)
        
        market_id = "pm123"
        base_time = datetime.utcnow()
        
        # Crear eventos
        for i in range(3):
            event = {
                "type": f"event_{i}",
                "timestamp": base_time + timedelta(seconds=i),
                "market_id": market_id
            }
            await store.store_event(event)
        
        # Replay paso 0
        result = await engine.replay_step_by_step(market_id=market_id, step=0)
        assert result is not None
        assert result["step"] == 0
        assert "event" in result
        assert "system_state_at_step" in result
        
        # Replay paso inexistente
        result = await engine.replay_step_by_step(market_id=market_id, step=100)
        assert result is None
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_rewind_to_timestamp(self, db_session):
        """Test rewinding to timestamp."""
        def get_db():
            return db_session
        store = EventStore(storage_type="sqlite", db_session_factory=get_db)
        engine = ReplayEngine(store)
        
        base_time = datetime.utcnow()
        rewind_time = base_time + timedelta(seconds=5)
        
        system_state = await engine.rewind_to_timestamp(rewind_time)
        assert system_state is not None
        assert "timestamp" in system_state
        
        store.close()


class TestStrategyComparator:
    """Test cases for Strategy Comparator."""
    
    @pytest.mark.asyncio
    async def test_strategy_comparator_initialization(self, db_session):
        """Test Strategy Comparator initializes correctly."""
        def get_db():
            return db_session
        store = EventStore(storage_type="sqlite", db_session_factory=get_db)
        engine = ReplayEngine(store)
        comparator = StrategyComparator(store, engine)
        assert comparator is not None
        store.close()
    
    @pytest.mark.asyncio
    async def test_compare_strategies(self, db_session):
        """Test comparing strategies."""
        def get_db():
            return db_session
        store = EventStore(storage_type="sqlite", db_session_factory=get_db)
        engine = ReplayEngine(store)
        comparator = StrategyComparator(store, engine)
        
        market_id = "pm123"
        base_time = datetime.utcnow()
        
        # Crear eventos históricos
        event1 = {
            "type": "watcher_event_state",
            "timestamp": base_time,
            "market_id": market_id,
            "state": "FINISHED_CONFIRMED"
        }
        
        event2 = {
            "type": "strategy_intent_created",
            "timestamp": base_time + timedelta(seconds=1),
            "market_id": market_id,
            "target_price": 0.979,
            "size": 5000.0,
            "trace_id": str(uuid4())
        }
        
        await store.store_event(event1)
        await store.store_event(event2)
        
        # Comparar estrategias (usando None como placeholder)
        comparison = await comparator.compare_strategies(
            market_id=market_id,
            original_strategy=None,
            new_strategy=None
        )
        
        assert comparison is not None
        assert "original_intents_count" in comparison
        assert "new_intents_count" in comparison
        assert "simulated_pnl_original" in comparison
        assert "simulated_pnl_new" in comparison
        assert "differences" in comparison
        
        store.close()

