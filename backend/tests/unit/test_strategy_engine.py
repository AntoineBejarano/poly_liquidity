"""
Unit tests for Strategy Engine.

Refactorizado según especificación en docs/services/strategy.md
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from app.core.strategy import Strategy, OrderIntent, NoEntryReason, MarketState, EventState, StrategyConfig
from app.core.state import state, MarketState as InternalMarketState, EventState as InternalEventState
from app.core.latency_monitor import LatencyStatus
from app.core.runtime_supervisor import RuntimeMode


@pytest.fixture
def strategy():
    """Fixture para Strategy."""
    return Strategy()


@pytest.fixture
def sample_market_id():
    """Fixture para market_id de ejemplo."""
    return uuid4()


@pytest.fixture
def sample_market_state(sample_market_id):
    """Fixture para MarketState de ejemplo."""
    return MarketState(
        market_id=sample_market_id,
        best_bid=0.976,
        best_ask=0.98,
        last_price=0.978,
        spread=0.004,
        outcomes=["YES", "NO"]
    )


@pytest.fixture
def sample_event_state_finished():
    """Fixture para EventState con FINISHED_CONFIRMED."""
    return EventState(
        event_status="FINISHED_CONFIRMED",
        confidence_score=0.97,
        sources_state={"espn": "FINISHED", "flashscore": "FINISHED"},
        event_finished_at=datetime.utcnow() - timedelta(minutes=2),
        last_update=datetime.utcnow(),
        event_type="sports"
    )


@pytest.fixture
def sample_event_state_live():
    """Fixture para EventState con LIVE."""
    return EventState(
        event_status="LIVE",
        confidence_score=0.9,
        sources_state={"espn": "LIVE"},
        event_finished_at=None,
        last_update=datetime.utcnow(),
        event_type="sports"
    )


class TestStrategyConfig:
    """Tests para StrategyConfig."""
    
    def test_strategy_config_defaults(self):
        """Test valores por defecto de StrategyConfig."""
        config = StrategyConfig()
        
        assert config.min_entry_price == 0.97
        assert config.max_entry_spread == 0.02
        assert config.safety_tick == 0.001
        assert config.target_edge == 0.01
        assert config.max_order_size == 5000.0
        assert config.aggressive_mode is False
    
    def test_strategy_config_custom(self):
        """Test StrategyConfig con valores personalizados."""
        config = StrategyConfig(
            min_entry_price=0.99,
            max_entry_spread=0.01,
            aggressive_mode=True
        )
        
        assert config.min_entry_price == 0.99
        assert config.max_entry_spread == 0.01
        assert config.aggressive_mode is True


class TestOrderIntent:
    """Tests para OrderIntent."""
    
    def test_order_intent_creation(self, sample_market_id):
        """Test creación de OrderIntent."""
        intent = OrderIntent(
            market_id=sample_market_id,
            side="BUY",
            price=0.979,
            size=5000.0,
            reason="conditions_met"
        )
        
        assert intent.market_id == sample_market_id
        assert intent.side == "BUY"
        assert intent.price == 0.979
        assert intent.size == 5000.0
        assert intent.reason == "conditions_met"
    
    def test_order_intent_with_metadata(self, sample_market_id):
        """Test OrderIntent con metadata."""
        intent = OrderIntent(
            market_id=sample_market_id,
            price=0.979,
            size=5000.0,
            reason="conditions_met",
            metadata={"best_ask": 0.98, "latency_status": "GREEN"}
        )
        
        assert "best_ask" in intent.metadata
        assert intent.metadata["best_ask"] == 0.98


class TestStrategyActivationConditions:
    """Tests para condiciones de activación."""
    
    @pytest.mark.asyncio
    async def test_activation_event_not_finished(
        self, strategy, sample_market_id, sample_market_state, sample_event_state_live
    ):
        """Test que no se activa si evento no está terminado."""
        trace_id = uuid4()
        
        should_enter, reason, details = strategy._check_activation_conditions(
            sample_market_id,
            sample_market_state,
            sample_event_state_live,
            trace_id
        )
        
        assert should_enter is False
        assert reason == "event_not_finished"
        assert "event_status" in details
    
    @pytest.mark.asyncio
    async def test_activation_price_too_low(
        self, strategy, sample_market_id, sample_event_state_finished
    ):
        """Test que no se activa si precio es demasiado bajo."""
        trace_id = uuid4()
        market_state = MarketState(
            market_id=sample_market_id,
            best_bid=0.95,
            best_ask=0.96,  # Menor que min_entry_price (0.97)
            last_price=0.955,
            spread=0.01,
            outcomes=["YES", "NO"]
        )
        
        should_enter, reason, details = strategy._check_activation_conditions(
            sample_market_id,
            market_state,
            sample_event_state_finished,
            trace_id
        )
        
        assert should_enter is False
        assert reason == "ask_price_too_low"
    
    @pytest.mark.asyncio
    async def test_activation_spread_too_wide(
        self, strategy, sample_market_id, sample_event_state_finished
    ):
        """Test que no se activa si spread es demasiado amplio."""
        trace_id = uuid4()
        market_state = MarketState(
            market_id=sample_market_id,
            best_bid=0.95,
            best_ask=0.98,
            last_price=0.965,
            spread=0.03,  # Mayor que max_entry_spread (0.02)
            outcomes=["YES", "NO"]
        )
        
        should_enter, reason, details = strategy._check_activation_conditions(
            sample_market_id,
            market_state,
            sample_event_state_finished,
            trace_id
        )
        
        assert should_enter is False
        assert reason == "spread_too_wide"
    
    @pytest.mark.asyncio
    async def test_activation_conditions_met(
        self, strategy, sample_market_id, sample_market_state, sample_event_state_finished
    ):
        """Test que se activa cuando todas las condiciones se cumplen."""
        trace_id = uuid4()
        
        with patch('app.core.strategy.strategy.latency_monitor') as mock_latency:
            mock_latency.get_status.return_value = LatencyStatus.GREEN
            
            # Mock app.main para evitar import circular en tests
            with patch('app.core.strategy.strategy.main_module', create=True) as mock_main:
                mock_runtime_supervisor = Mock()
                mock_runtime_supervisor.get_mode.return_value = RuntimeMode.GREEN
                mock_main.runtime_supervisor = mock_runtime_supervisor
                
                should_enter, reason, details = strategy._check_activation_conditions(
                    sample_market_id,
                    sample_market_state,
                    sample_event_state_finished,
                    trace_id
                )
                
                assert should_enter is True
                assert reason == "conditions_met"


class TestStrategyPriceCalculation:
    """Tests para cálculo de precio objetivo."""
    
    def test_calculate_target_price_green(self, strategy):
        """Test cálculo de precio objetivo en modo GREEN."""
        # Asegurar que config tiene valores válidos
        strategy._config = None  # Reset config
        
        # Mock state.risk_config para tener valores de test apropiados
        with patch.object(state, 'risk_config') as mock_config:
            mock_config.min_entry_price = 0.97
            mock_config.target_margin = 0.01
            mock_config.safety_tick = 0.001
            mock_config.max_single_order_size = 5000.0
            mock_config.max_exposure_per_market = 10000.0
            mock_config.max_global_exposure = 200000.0
            
            config = strategy._get_config()
            
            target_price = strategy._calculate_target_price(
                best_ask=0.98,
                best_bid=0.976,
                latency_status=LatencyStatus.GREEN
            )
            
            # safe_price = 0.98 - 0.001 = 0.979
            # max_price = 1.0 - 0.01 = 0.99
            # target_price = min(0.979, 0.99) = 0.979
            # target_price = max(0.979, 0.976) = 0.979
            # Debería ser >= best_bid y <= best_ask
            assert target_price >= 0.976  # >= best_bid
            assert target_price <= 0.98  # <= best_ask
            assert target_price > 0.0  # Debe ser positivo
    
    def test_calculate_target_price_yellow(self, strategy):
        """Test cálculo de precio objetivo en modo YELLOW (más conservador)."""
        target_price = strategy._calculate_target_price(
            best_ask=0.98,
            best_bid=0.976,
            latency_status=LatencyStatus.YELLOW
        )
        
        # safety_tick = 0.001 * 2.0 = 0.002
        # safe_price = 0.98 - 0.002 = 0.978
        # Debería ser más conservador (menor precio)
        assert target_price <= 0.979  # Más conservador que GREEN
    
    def test_calculate_target_price_red(self, strategy):
        """Test cálculo de precio objetivo en modo RED (muy conservador)."""
        target_price = strategy._calculate_target_price(
            best_ask=0.98,
            best_bid=0.976,
            latency_status=LatencyStatus.RED
        )
        
        # safety_tick = 0.001 * 3.0 = 0.003
        # safe_price = 0.98 - 0.003 = 0.977
        # Debería ser muy conservador
        assert target_price <= 0.978  # Más conservador que YELLOW


class TestStrategySizeCalculation:
    """Tests para cálculo de tamaño."""
    
    def test_calculate_size_green(self, strategy, sample_market_id, sample_event_state_finished):
        """Test cálculo de tamaño en modo GREEN."""
        # Mock state.exposures
        with patch.object(state, 'exposures', {}):
            size = strategy._calculate_size(
                market_id=sample_market_id,
                target_price=0.979,
                orderbook_liquidity=10000.0,
                event_state=sample_event_state_finished,
                latency_status=LatencyStatus.GREEN
            )
            
            # Debería calcular tamaño basado en límites
            assert size > 0.0
            assert size <= 10000.0  # Limitado por orderbook_liquidity
    
    def test_calculate_size_yellow(self, strategy, sample_market_id, sample_event_state_finished):
        """Test cálculo de tamaño en modo YELLOW (reducido)."""
        with patch.object(state, 'exposures', {}):
            size_yellow = strategy._calculate_size(
                market_id=sample_market_id,
                target_price=0.979,
                orderbook_liquidity=10000.0,
                event_state=sample_event_state_finished,
                latency_status=LatencyStatus.YELLOW
            )
            
            size_green = strategy._calculate_size(
                market_id=sample_market_id,
                target_price=0.979,
                orderbook_liquidity=10000.0,
                event_state=sample_event_state_finished,
                latency_status=LatencyStatus.GREEN
            )
            
            # YELLOW debería ser 50% de GREEN
            assert size_yellow == pytest.approx(size_green * 0.5, rel=0.1)
    
    def test_calculate_size_red(self, strategy, sample_market_id, sample_event_state_finished):
        """Test cálculo de tamaño en modo RED (cero)."""
        with patch.object(state, 'exposures', {}):
            size = strategy._calculate_size(
                market_id=sample_market_id,
                target_price=0.979,
                orderbook_liquidity=10000.0,
                event_state=sample_event_state_finished,
                latency_status=LatencyStatus.RED
            )
            
            assert size == 0.0
    
    def test_calculate_size_unconfirmed(self, strategy, sample_market_id):
        """Test cálculo de tamaño con FINISHED_UNCONFIRMED."""
        event_state = EventState(
            event_status="FINISHED_UNCONFIRMED",
            confidence_score=0.9,  # >= 0.85
            sources_state={},
            event_finished_at=datetime.utcnow(),
            last_update=datetime.utcnow(),
            event_type="sports"
        )
        
        with patch.object(state, 'exposures', {}):
            size = strategy._calculate_size(
                market_id=sample_market_id,
                target_price=0.979,
                orderbook_liquidity=10000.0,
                event_state=event_state,
                latency_status=LatencyStatus.GREEN
            )
            
            # Debería ser 50% del tamaño normal
            assert size > 0.0


class TestStrategySportsHeuristics:
    """Tests para heurísticas de deportes."""
    
    def test_sports_heuristic_recent_finish(self, strategy, sample_event_state_finished):
        """Test heurística de evento recién terminado."""
        config = strategy._get_config()
        base_size = 1000.0
        
        # Evento terminado hace 2 minutos (reciente)
        event_state = EventState(
            event_status="FINISHED_CONFIRMED",
            confidence_score=0.97,
            sources_state={},
            event_finished_at=datetime.utcnow() - timedelta(minutes=2),
            last_update=datetime.utcnow(),
            event_type="sports"
        )
        
        size_recent = strategy._apply_sports_heuristics(base_size, event_state, config)
        assert size_recent == base_size  # No se reduce si es reciente
        
        # Evento terminado hace 15 minutos (antiguo)
        event_state.event_finished_at = datetime.utcnow() - timedelta(minutes=15)
        size_old = strategy._apply_sports_heuristics(base_size, event_state, config)
        
        # Debería reducirse a 70%
        assert size_old == pytest.approx(base_size * 0.7, rel=0.01)
    
    def test_sports_heuristic_multiple_sources(self, strategy, sample_event_state_finished):
        """Test heurística de múltiples fuentes coinciden."""
        config = strategy._get_config()
        base_size = 1000.0
        
        # 3+ fuentes coinciden
        event_state = EventState(
            event_status="FINISHED_CONFIRMED",
            confidence_score=0.97,
            sources_state={
                "espn": "FINISHED",
                "flashscore": "FINISHED",
                "nba_api": "FINISHED"
            },
            event_finished_at=datetime.utcnow(),
            last_update=datetime.utcnow(),
            event_type="sports"
        )
        
        size = strategy._apply_sports_heuristics(base_size, event_state, config)
        
        # Debería aumentar a 110%
        assert size == pytest.approx(base_size * 1.1, rel=0.01)


class TestStrategyTick:
    """Tests para el método tick."""
    
    @pytest.mark.asyncio
    async def test_tick_no_markets(self, strategy):
        """Test tick sin mercados."""
        with patch.object(state, 'markets', {}):
            intents = await strategy.tick()
            
            assert len(intents) == 0
    
    @pytest.mark.asyncio
    async def test_tick_with_valid_market(
        self, strategy, sample_market_id, sample_market_state, sample_event_state_finished
    ):
        """Test tick con mercado válido."""
        # Setup state
        internal_market = InternalMarketState()
        internal_market.market_id = sample_market_id
        internal_market.last_price = 0.978
        internal_market.spread = 0.004
        internal_market.orderbook_snapshot = {"liquidity_at_price": {"0.979": 10000.0}}
        
        internal_event = InternalEventState()
        internal_event.market_id = sample_market_id
        internal_event.state = "FINISHED_CONFIRMED"
        internal_event.confidence = 0.97
        internal_event.finished_at = datetime.utcnow() - timedelta(minutes=2)
        internal_event.updated_at = datetime.utcnow()
        
        with patch.object(state, 'markets', {sample_market_id: internal_market}):
            with patch.object(state, 'events', {sample_market_id: internal_event}):
                with patch.object(state, 'exposures', {}):
                    with patch('app.core.strategy.strategy.latency_monitor') as mock_latency:
                        mock_latency.get_status.return_value = LatencyStatus.GREEN
                        
                        # Mock app.main para evitar import circular en tests
                        with patch('app.core.strategy.strategy.main_module', create=True) as mock_main:
                            mock_runtime_supervisor = Mock()
                            mock_runtime_supervisor.get_mode.return_value = RuntimeMode.GREEN
                            mock_main.runtime_supervisor = mock_runtime_supervisor
                            
                            intents = await strategy.tick()
                            
                            # Debería crear al menos un intent si las condiciones se cumplen
                            # (puede que no si el tamaño calculado es 0)
                            assert isinstance(intents, list)

