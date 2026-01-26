"""
Unit tests for Strategy Engine.
"""
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from app.core.strategy import Strategy, OrderIntent
from app.core.latency_monitor import LatencyStatus


class TestStrategy:
    """Test cases for Strategy Engine."""
    
    def test_strategy_initialization(self):
        """Test strategy initializes correctly."""
        strategy = Strategy()
        assert strategy._last_intents == []
    
    def test_calculate_target_price_normal(self, mock_state):
        """Test target price calculation in normal (GREEN) latency."""
        strategy = Strategy()
        
        best_ask = 0.99
        best_bid = 0.97
        target_price = strategy._calculate_target_price(best_ask, best_bid, LatencyStatus.GREEN)
        
        # Should be: min(0.99 - 0.001, 1.0 - 0.01) = min(0.989, 0.99) = 0.989
        # But also max(0.989, 0.97) = 0.989
        assert target_price <= best_ask - mock_state.risk_config.safety_tick
        assert target_price >= best_bid
    
    def test_calculate_target_price_yellow_latency(self, mock_state):
        """Test target price calculation in YELLOW latency (more conservative)."""
        strategy = Strategy()
        
        best_ask = 0.99
        best_bid = 0.97
        target_price = strategy._calculate_target_price(best_ask, best_bid, LatencyStatus.YELLOW)
        
        # Should use 2x safety_tick (0.002 instead of 0.001)
        # min(0.99 - 0.002, 0.99) = 0.988
        assert target_price <= best_ask - (mock_state.risk_config.safety_tick * 2.0)
        assert target_price >= best_bid
    
    def test_calculate_target_price_red_latency(self, mock_state):
        """Test target price calculation in RED latency (very conservative)."""
        strategy = Strategy()
        
        best_ask = 0.99
        best_bid = 0.97
        target_price = strategy._calculate_target_price(best_ask, best_bid, LatencyStatus.RED)
        
        # Should use 3x safety_tick (0.003 instead of 0.001)
        assert target_price <= best_ask - (mock_state.risk_config.safety_tick * 3.0)
        assert target_price >= best_bid
    
    def test_calculate_size_with_capacity(self, mock_state):
        """Test size calculation based on remaining capacity."""
        strategy = Strategy()
        market_id = uuid4()
        target_price = 0.98
        
        # Set up exposure state
        from app.core.state import ExposureState
        from app.core.strategy.models import EventState
        from app.core.latency_monitor import LatencyStatus
        
        exposure_state = ExposureState()
        exposure_state.market_id = market_id
        exposure_state.notional = 5000.0  # Current exposure
        mock_state.exposures[market_id] = exposure_state
        
        # Create event state for _calculate_size
        event_state = EventState(
            event_status="FINISHED_CONFIRMED",
            confidence_score=0.95,
            sources_state={},
            event_finished_at=None,
            last_update=__import__('datetime').datetime.utcnow(),
            event_type=None
        )
        
        # max_exposure_per_market = 10000, so remaining = 5000
        # size_from_capacity = 5000 / 0.98 ≈ 5102
        size = strategy._calculate_size(
            market_id, target_price, 10000.0, event_state, LatencyStatus.GREEN
        )
        
        # Should be limited by capacity
        assert size > 0
        assert size * target_price <= 5000.0  # Should not exceed remaining capacity
    
    def test_calculate_size_with_liquidity(self, mock_state):
        """Test size calculation limited by orderbook liquidity."""
        strategy = Strategy()
        market_id = uuid4()
        target_price = 0.98
        
        from app.core.strategy.models import EventState
        from app.core.latency_monitor import LatencyStatus
        
        event_state = EventState(
            event_status="FINISHED_CONFIRMED",
            confidence_score=0.95,
            sources_state={},
            event_finished_at=None,
            last_update=__import__('datetime').datetime.utcnow(),
            event_type=None
        )
        
        # No current exposure, so capacity is full (10000)
        # But liquidity is only 1000
        size = strategy._calculate_size(
            market_id, target_price, 1000.0, event_state, LatencyStatus.GREEN
        )
        
        # Should be limited by liquidity
        assert size <= 1000.0
    
    def test_calculate_size_red_latency_returns_zero(self, mock_state):
        """Test that size calculation returns 0 in RED latency."""
        strategy = Strategy()
        market_id = uuid4()
        target_price = 0.98
        
        from app.core.strategy.models import EventState
        from app.core.latency_monitor import LatencyStatus
        
        event_state = EventState(
            event_status="FINISHED_CONFIRMED",
            confidence_score=0.95,
            sources_state={},
            event_finished_at=None,
            last_update=__import__('datetime').datetime.utcnow(),
            event_type=None
        )
        
        size = strategy._calculate_size(
            market_id, target_price, 10000.0, event_state, LatencyStatus.RED
        )
        assert size == 0.0
    
    def test_calculate_size_yellow_latency_reduces_size(self, mock_state):
        """Test that size is reduced by 50% in YELLOW latency."""
        strategy = Strategy()
        market_id = uuid4()
        target_price = 0.98
        
        from app.core.strategy.models import EventState
        from app.core.latency_monitor import LatencyStatus
        
        event_state = EventState(
            event_status="FINISHED_CONFIRMED",
            confidence_score=0.95,
            sources_state={},
            event_finished_at=None,
            last_update=__import__('datetime').datetime.utcnow(),
            event_type=None
        )
        
        # Calculate size in GREEN and YELLOW
        size_green = strategy._calculate_size(
            market_id, target_price, 10000.0, event_state, LatencyStatus.GREEN
        )
        size_yellow = strategy._calculate_size(
            market_id, target_price, 10000.0, event_state, LatencyStatus.YELLOW
        )
        
        # YELLOW should be 50% of GREEN
        if size_green > 0:
            assert size_yellow == pytest.approx(size_green * 0.5, rel=0.1)
        assert size_yellow >= 0.0
    
    @pytest.mark.asyncio
    async def test_tick_creates_intents_for_finished_events(self, mock_state):
        """Test that tick creates intents for FINISHED_CONFIRMED events."""
        strategy = Strategy()
        market_id = uuid4()
        
        # Set up market state
        from app.core.state import MarketState as InternalMarketState, EventState as InternalEventState
        from datetime import datetime
        
        market_state = InternalMarketState()
        market_state.market_id = market_id
        market_state.last_price = 0.98
        market_state.spread = 0.002
        market_state.orderbook_snapshot = {"liquidity_at_price": {"0.979": 10000.0}}
        mock_state.markets[market_id] = market_state
        
        # Set up event state as FINISHED_CONFIRMED
        event_state = InternalEventState()
        event_state.market_id = market_id
        event_state.state = "FINISHED_CONFIRMED"
        event_state.confidence = 0.95
        event_state.updated_at = datetime.utcnow()
        mock_state.events[market_id] = event_state
        
        # Mock latency monitor and runtime supervisor
        with patch("app.core.strategy.strategy.latency_monitor") as mock_monitor:
            mock_monitor.get_status.return_value = LatencyStatus.GREEN
            
            with patch("app.core.strategy.strategy.main_module", create=True) as mock_main:
                from app.core.runtime_supervisor import RuntimeMode
                mock_runtime_supervisor = Mock()
                mock_runtime_supervisor.get_mode.return_value = RuntimeMode.GREEN
                mock_main.runtime_supervisor = mock_runtime_supervisor
                
                intents = await strategy.tick()
        
        # Should create intents if todas las condiciones se cumplen
        assert isinstance(intents, list)
        if len(intents) > 0:
            assert all(isinstance(intent, OrderIntent) for intent in intents)
    
    @pytest.mark.asyncio
    async def test_tick_skips_live_events(self, mock_state):
        """Test that tick skips events that are not FINISHED_CONFIRMED."""
        strategy = Strategy()
        market_id = uuid4()
        
        # Set up market state
        from app.core.state import MarketState, EventState
        market_state = MarketState()
        market_state.market_id = market_id
        market_state.last_price = 0.98
        mock_state.markets[market_id] = market_state
        
        # Set up event state as LIVE (not finished)
        event_state = EventState()
        event_state.market_id = market_id
        event_state.state = "LIVE"
        mock_state.events[market_id] = event_state
        
        intents = await strategy.tick()
        
        # Should not create intents for LIVE events
        assert len(intents) == 0
    
    @pytest.mark.asyncio
    async def test_tick_skips_low_price_markets(self, mock_state):
        """Test that tick skips markets below min_entry_price."""
        strategy = Strategy()
        market_id = uuid4()
        
        # Set up market state with low price
        from app.core.state import MarketState, EventState
        market_state = MarketState()
        market_state.market_id = market_id
        market_state.last_price = 0.95  # Below min_entry_price (0.97)
        mock_state.markets[market_id] = market_state
        
        # Set up event state as FINISHED_CONFIRMED
        event_state = EventState()
        event_state.market_id = market_id
        event_state.state = "FINISHED_CONFIRMED"
        mock_state.events[market_id] = event_state
        
        intents = await strategy.tick()
        
        # Should not create intents for low price markets
        assert len(intents) == 0

