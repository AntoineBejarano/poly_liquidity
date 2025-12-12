"""
Unit tests for Live Control.

Según especificación en docs/services/livecontrol.md
"""
import pytest
from datetime import datetime
from app.core.live_control import LiveControlStore, LiveControlEventBus, emit_event


class TestLiveControlStore:
    """Test cases for Live Control Store."""
    
    def test_store_initialization(self):
        """Test Store initializes correctly."""
        store = LiveControlStore()
        assert store is not None
        assert len(store.events) == 0
        assert len(store.markets) == 0
        assert len(store.watchers) == 0
        assert len(store.orders) == 0
    
    def test_update_event(self):
        """Test updating event state."""
        store = LiveControlStore()
        
        store.update_event(
            event_id="sports:nba:401585236",
            event_type="sports",
            status="FINISHED_CONFIRMED",
            confidence=0.97,
            watcher_status="active",
            markets=["pm123", "pm555"],
            sources={"espn": "FINISHED", "flashscore": "FINISHED"}
        )
        
        assert "sports:nba:401585236" in store.events
        event = store.events["sports:nba:401585236"]
        assert event.status == "FINISHED_CONFIRMED"
        assert event.confidence == 0.97
        assert event.markets == ["pm123", "pm555"]
        assert event.sources["espn"] == "FINISHED"
    
    def test_update_market(self):
        """Test updating market state."""
        store = LiveControlStore()
        
        store.update_market(
            market_id="pm555",
            event_id="sports:nba:401585236",
            state="FINISHED_CONFIRMED",
            best_ask=0.98,
            best_bid=0.97,
            exposure=5000.0
        )
        
        assert "pm555" in store.markets
        market = store.markets["pm555"]
        assert market.state == "FINISHED_CONFIRMED"
        assert market.best_ask == 0.98
        assert market.exposure == 5000.0
    
    def test_update_watcher(self):
        """Test updating watcher state."""
        store = LiveControlStore()
        
        store.update_watcher(
            event_id="sports:nba:401585236",
            event_name="Lakers vs Warriors",
            status="active",
            checks_per_minute=30,
            last_check=datetime.utcnow()
        )
        
        assert "sports:nba:401585236" in store.watchers
        watcher = store.watchers["sports:nba:401585236"]
        assert watcher.status == "active"
        assert watcher.checks_per_minute == 30
    
    def test_update_order(self):
        """Test updating order state."""
        store = LiveControlStore()
        
        fills = [
            {"size": 3000, "price": 0.979, "timestamp": datetime.utcnow().isoformat()}
        ]
        
        store.update_order(
            order_id="order_xyz",
            market_id="pm555",
            status="filled",
            fills=fills,
            avg_price=0.979
        )
        
        assert "order_xyz" in store.orders
        order = store.orders["order_xyz"]
        assert order.status == "filled"
        assert len(order.fills) == 1
        assert order.avg_price == 0.979
    
    def test_update_latency(self):
        """Test updating latency state."""
        store = LiveControlStore()
        
        store.update_latency(mode="GREEN", latency_ms=32.0)
        
        assert store.latency.mode == "GREEN"
        assert store.latency.latency_ms == 32.0
    
    def test_update_system_health(self):
        """Test updating system health."""
        store = LiveControlStore()
        
        store.update_system_health(
            runtime_mode="GREEN",
            exposure_total=25000.0,
            markets_active=5,
            watchers_active=10
        )
        
        assert store.system_health.runtime_mode == "GREEN"
        assert store.system_health.exposure_total == 25000.0
        assert store.system_health.markets_active == 5
    
    def test_get_state(self):
        """Test getting complete state."""
        store = LiveControlStore()
        
        # Agregar algunos datos
        store.update_event(
            event_id="sports:nba:401585236",
            event_type="sports",
            status="FINISHED_CONFIRMED",
            confidence=0.97,
            watcher_status="active"
        )
        
        store.update_market(
            market_id="pm555",
            state="FINISHED_CONFIRMED",
            exposure=5000.0
        )
        
        state = store.get_state()
        
        assert "events" in state
        assert "markets" in state
        assert "watchers" in state
        assert "orders" in state
        assert "latency" in state
        assert "system_health" in state
        assert "sports:nba:401585236" in state["events"]
        assert "pm555" in state["markets"]


class TestLiveControlEventBus:
    """Test cases for Live Control Event Bus."""
    
    def test_event_bus_initialization(self):
        """Test Event Bus initializes correctly."""
        store = LiveControlStore()
        bus = LiveControlEventBus(store)
        assert bus is not None
        assert bus.store == store
        assert len(bus.subscribers) == 0
    
    def test_emit_event_update(self):
        """Test emitting event_update event."""
        store = LiveControlStore()
        bus = LiveControlEventBus(store)
        
        bus.emit("event_update", {
            "event_id": "sports:nba:401585236",
            "event_type": "sports",
            "status": "FINISHED_CONFIRMED",
            "confidence": 0.97,
            "watcher_status": "active"
        })
        
        assert "sports:nba:401585236" in store.events
        event = store.events["sports:nba:401585236"]
        assert event.status == "FINISHED_CONFIRMED"
    
    def test_emit_market_update(self):
        """Test emitting market_update event."""
        store = LiveControlStore()
        bus = LiveControlEventBus(store)
        
        bus.emit("market_update", {
            "market_id": "pm555",
            "state": "FINISHED_CONFIRMED",
            "best_ask": 0.98,
            "best_bid": 0.97
        })
        
        assert "pm555" in store.markets
        market = store.markets["pm555"]
        assert market.state == "FINISHED_CONFIRMED"
    
    def test_emit_strategy_intent(self):
        """Test emitting strategy_intent event."""
        store = LiveControlStore()
        bus = LiveControlEventBus(store)
        
        bus.emit("strategy_intent", {
            "market_id": "pm555",
            "target_price": 0.979,
            "size": 5000.0,
            "reason": "event_finished_confirmed"
        })
        
        assert "pm555" in store.markets
        market = store.markets["pm555"]
        assert market.last_intent is not None
        assert market.last_intent["target_price"] == 0.979
    
    def test_emit_risk_decision(self):
        """Test emitting risk_decision event."""
        store = LiveControlStore()
        bus = LiveControlEventBus(store)
        
        bus.emit("risk_decision", {
            "market_id": "pm555",
            "approved": True,
            "final_size": 5000.0,
            "price": 0.979
        })
        
        assert "pm555" in store.markets
        market = store.markets["pm555"]
        assert market.exposure == 5000.0 * 0.979
    
    def test_emit_execution_update(self):
        """Test emitting execution_update event."""
        store = LiveControlStore()
        bus = LiveControlEventBus(store)
        
        fills = [
            {"size": 3000, "price": 0.979, "timestamp": datetime.utcnow().isoformat()}
        ]
        
        bus.emit("execution_update", {
            "order_id": "order_xyz",
            "market_id": "pm555",
            "status": "filled",
            "fills": fills,
            "avg_price": 0.979
        })
        
        assert "order_xyz" in store.orders
        order = store.orders["order_xyz"]
        assert order.status == "filled"
        assert store.system_health.last_fill is not None
    
    def test_subscribe_unsubscribe(self):
        """Test subscribing and unsubscribing."""
        store = LiveControlStore()
        bus = LiveControlEventBus(store)
        
        received_events = []
        
        def callback(event_type: str, data: dict):
            received_events.append((event_type, data))
        
        bus.subscribe(callback)
        assert len(bus.subscribers) == 1
        
        bus.emit("event_update", {"event_id": "test"})
        assert len(received_events) == 1
        
        bus.unsubscribe(callback)
        assert len(bus.subscribers) == 0
        
        bus.emit("event_update", {"event_id": "test2"})
        assert len(received_events) == 1  # No se recibió el segundo evento

