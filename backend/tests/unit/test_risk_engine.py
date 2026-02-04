"""
Unit tests for Risk Engine.
"""
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from app.core.risk_engine import RiskEngine, ApprovedOrderIntent
from app.core.risk_engine.models import RiskConfig as EngineRiskConfig
from app.core.strategy import OrderIntent
from app.core.latency_monitor import LatencyStatus
from app.core.runtime_supervisor import RuntimeMode


@pytest.fixture(autouse=True)
def mock_risk_engine_config():
    """Ensure risk engine gets a valid RiskConfig from config_service."""
    from app.core.risk_engine import risk_engine as risk_engine_module
    config = EngineRiskConfig(
        max_market_exposure=10000.0,
        max_global_exposure=50000.0,
        max_markets_active=5,
        min_order_size=100.0,
    )
    with patch.object(risk_engine_module.config_service, "get_risk_engine_config", return_value=config):
        yield


class TestRiskEngine:
    """Test cases for Risk Engine."""
    
    def test_risk_engine_initialization(self):
        """Test risk engine initializes correctly."""
        engine = RiskEngine()
        assert engine is not None
    
    def test_calculate_exposure(self):
        """Test exposure calculation."""
        engine = RiskEngine()
        
        exposure = engine._calculate_exposure(1000.0, 0.98)
        assert exposure == 980.0  # 1000 * 0.98
    
    def test_calculate_global_exposure(self, mock_state):
        """Test global exposure calculation."""
        engine = RiskEngine()
        market_id_1 = uuid4()
        market_id_2 = uuid4()
        
        # Set up exposures
        from app.core.state import ExposureState
        exp1 = ExposureState()
        exp1.market_id = market_id_1
        exp1.notional = 5000.0
        mock_state.exposures[market_id_1] = exp1
        
        exp2 = ExposureState()
        exp2.market_id = market_id_2
        exp2.notional = 3000.0
        mock_state.exposures[market_id_2] = exp2
        
        global_exposure = engine._calculate_global_exposure()
        assert global_exposure == 8000.0
    
    def test_check_risk_rules_market_exposure_limit(self, mock_state):
        """Test that market exposure limit is enforced."""
        engine = RiskEngine()
        market_id = uuid4()
        event_id = uuid4()
        
        # Set up existing exposure
        from app.core.state import ExposureState
        exp = ExposureState()
        exp.market_id = market_id
        exp.notional = 9000.0  # Already high exposure
        mock_state.exposures[market_id] = exp
        
        # Set up event state for rule 7 (keyed by event_id)
        from app.core.state import EventState as InternalEventState
        from datetime import datetime
        event_state = InternalEventState()
        event_state.market_id = market_id
        event_state.state = "FINISHED_CONFIRMED"
        event_state.confidence = 0.95
        event_state.updated_at = datetime.utcnow()
        mock_state.events[event_id] = event_state
        
        intent = OrderIntent(
            event_id=event_id,
            outcome="YES",
            side="BUY",
            price=0.98,
            size=2000.0,  # Would add 1960 exposure, total = 10960 > 10000
            reason="test",
            metadata={"market_id": str(market_id)},
        )
        
        is_valid, reason, adjustments = engine._check_risk_rules(intent)
        # El Risk Engine ajusta el tamaño en lugar de rechazar cuando es posible
        # Con exposición de 9000 y límite de 10000, remaining = 1000
        # Tamaño máximo = 1000 / 0.98 ≈ 1020
        # El intent original es 2000, pero se ajustará a 1020
        # Como 1020 > min_order_size (100), debería pasar con tamaño ajustado
        if not is_valid:
            # Si se rechaza, debe ser porque el tamaño ajustado es muy pequeño
            assert "size_too_small" in reason.lower()
        else:
            # Si pasa, debe tener ajustes de tamaño
            assert "market_exposure_limit" in adjustments or "final_size" in adjustments
            if "final_size" in adjustments:
                assert adjustments["final_size"] < intent.size  # Debe ser menor que el original
    
    def test_check_risk_rules_global_exposure_limit(self, mock_state):
        """Test that global exposure limit is enforced."""
        engine = RiskEngine()
        market_id = uuid4()
        event_id = uuid4()
        
        # Set up high global exposure
        from app.core.state import ExposureState
        for i in range(5):
            exp = ExposureState()
            exp.market_id = uuid4()
            exp.notional = 10000.0  # Each market at max
            mock_state.exposures[exp.market_id] = exp
        
        mock_state.events[event_id] = type("Ev", (), {"market_id": market_id})()
        intent = OrderIntent(
            event_id=event_id,
            outcome="YES",
            side="BUY",
            price=0.98,
            size=1000.0,  # Would add 980 exposure
            reason="test",
            metadata={"market_id": str(market_id)},
        )
        
        is_valid, reason, adjustments = engine._check_risk_rules(intent)
        # Should fail because global exposure would exceed limit
        assert not is_valid
        assert "exceeds_global_exposure_limit" in reason or "global" in reason.lower() or "exceeds" in reason.lower()
    
    def test_check_risk_rules_max_markets_active(self, mock_state):
        """Test that max active markets limit is enforced."""
        engine = RiskEngine()
        market_id = uuid4()
        event_id = uuid4()
        
        # Set up max active markets
        from app.core.state import OrderState
        for i in range(5):  # Already at max (5)
            order_state = OrderState()
            order_state.order_id = uuid4()
            order_state.market_id = uuid4()
            order_state.status = "NEW"
            mock_state.orders[order_state.order_id] = order_state
        
        mock_state.events[event_id] = type("Ev", (), {"market_id": market_id})()
        intent = OrderIntent(
            event_id=event_id,
            outcome="YES",
            side="BUY",
            price=0.98,
            size=100.0,
            reason="test",
            metadata={"market_id": str(market_id)},
        )
        
        is_valid, reason, adjustments = engine._check_risk_rules(intent)
        assert not is_valid
        assert "exceeds_max_markets_active" in reason or "active markets" in reason.lower() or "exceeds" in reason.lower()
    
    def test_check_risk_rules_valid_intent(self, mock_state):
        """Test that valid intents pass all risk rules."""
        engine = RiskEngine()
        market_id = uuid4()
        event_id = uuid4()
        
        # Set up event state for rule 7 (keyed by event_id)
        from app.core.state import EventState as InternalEventState
        from datetime import datetime
        event_state = InternalEventState()
        event_state.market_id = market_id
        event_state.state = "FINISHED_CONFIRMED"
        event_state.confidence = 0.95
        event_state.updated_at = datetime.utcnow()
        mock_state.events[event_id] = event_state
        
        intent = OrderIntent(
            event_id=event_id,
            outcome="YES",
            side="BUY",
            price=0.98,
            size=100.0,  # Small size, well within limits
            reason="test",
            metadata={"market_id": str(market_id)},
        )
        
        is_valid, reason, adjustments = engine._check_risk_rules(intent)
        assert is_valid
        assert reason == ""
    
    @pytest.mark.asyncio
    async def test_tick_rejects_all_in_red_latency(self, mock_state):
        """Test that tick rejects all intents in RED latency."""
        engine = RiskEngine()
        market_id = uuid4()
        event_id = uuid4()
        mock_state.events[event_id] = type("Ev", (), {"market_id": market_id})()
        intent = OrderIntent(
            event_id=event_id,
            outcome="YES",
            side="BUY",
            price=0.98,
            size=100.0,
            reason="test",
            metadata={"market_id": str(market_id)},
        )
        
        # Mock runtime supervisor to return RED
        mock_runtime_supervisor = Mock()
        mock_runtime_supervisor.get_mode.return_value = RuntimeMode.RED
        
        # Mock latency monitor to return RED
        with patch("app.core.risk_engine.risk_engine.latency_monitor") as mock_monitor, \
             patch("app.core.risk_engine.risk_engine.main_module", create=True) as mock_main:
            mock_monitor.get_status.return_value = LatencyStatus.RED
            mock_main.runtime_supervisor = mock_runtime_supervisor
            
            approved = await engine.tick([intent])
        
        # Should reject all intents
        assert len(approved) == 0
    
    @pytest.mark.asyncio
    async def test_tick_approves_valid_intents(self, mock_state):
        """Test that tick approves valid intents."""
        engine = RiskEngine()
        market_id = uuid4()
        event_id = uuid4()
        
        from app.core.state import EventState as InternalEventState
        from datetime import datetime
        event_state = InternalEventState()
        event_state.market_id = market_id
        event_state.state = "FINISHED_CONFIRMED"
        event_state.confidence = 0.95
        event_state.updated_at = datetime.utcnow()
        mock_state.events[event_id] = event_state
        
        intent = OrderIntent(
            event_id=event_id,
            outcome="YES",
            side="BUY",
            price=0.98,
            size=100.0,
            reason="test",
            metadata={"market_id": str(market_id)},
        )
        
        # Mock runtime supervisor to return GREEN
        mock_runtime_supervisor = Mock()
        mock_runtime_supervisor.get_mode.return_value = RuntimeMode.GREEN
        
        # Mock latency monitor to return GREEN
        with patch("app.core.risk_engine.risk_engine.latency_monitor") as mock_monitor, \
             patch("app.core.risk_engine.risk_engine.main_module", create=True) as mock_main:
            mock_monitor.get_status.return_value = LatencyStatus.GREEN
            mock_main.runtime_supervisor = mock_runtime_supervisor
            
            # Mock database operations
            with patch("app.core.risk_engine.risk_engine.SessionLocal") as mock_db:
                mock_session = Mock()
                mock_db.return_value.__enter__ = Mock(return_value=mock_session)
                mock_db.return_value.__exit__ = Mock(return_value=None)
                mock_session.query.return_value.filter.return_value.first.return_value = None
                mock_session.add = Mock()
                mock_session.commit = Mock()
                
                approved = await engine.tick([intent])
        
        # Should approve valid intent
        assert len(approved) == 1
        assert isinstance(approved[0], ApprovedOrderIntent)
        assert approved[0].event_id == event_id
    
    @pytest.mark.asyncio
    async def test_tick_rejects_invalid_intents(self, mock_state):
        """Test that tick rejects invalid intents."""
        engine = RiskEngine()
        market_id = uuid4()
        event_id = uuid4()
        
        from app.core.state import ExposureState
        exp = ExposureState()
        exp.market_id = market_id
        exp.notional = 10000.0  # At max_market_exposure; remaining = 0 so intent rejected
        mock_state.exposures[market_id] = exp
        from app.core.state import EventState as InternalEventState
        from datetime import datetime
        ev_state = InternalEventState()
        ev_state.market_id = market_id
        ev_state.state = "FINISHED_CONFIRMED"
        mock_state.events[event_id] = ev_state
        
        intent = OrderIntent(
            event_id=event_id,
            outcome="YES",
            side="BUY",
            price=0.98,
            size=1000.0,  # Would exceed limit
            reason="test",
            metadata={"market_id": str(market_id)},
        )
        
        # Mock runtime supervisor to return GREEN
        mock_runtime_supervisor = Mock()
        mock_runtime_supervisor.get_mode.return_value = RuntimeMode.GREEN
        
        # Mock latency monitor to return GREEN
        with patch("app.core.risk_engine.risk_engine.latency_monitor") as mock_monitor, \
             patch("app.core.risk_engine.risk_engine.main_module", create=True) as mock_main:
            mock_monitor.get_status.return_value = LatencyStatus.GREEN
            mock_main.runtime_supervisor = mock_runtime_supervisor
            
            approved = await engine.tick([intent])
        
        # With exposure at limit, remaining = 0 so size adjustment yields 0 → intent rejected
        assert len(approved) == 0

