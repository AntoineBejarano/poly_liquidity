"""
Tests unitarios para verificar que Strategy Engine usa ConfigService.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta
from app.core.strategy.strategy import Strategy
from app.core.strategy.models import MarketState, EventState
from app.core.config_service import config_service
from app.core.latency_monitor import LatencyStatus


@pytest.fixture
def strategy():
    """Fixture para Strategy Engine."""
    return Strategy()


@pytest.fixture
def mock_config_service():
    """Mock ConfigService."""
    with patch('app.core.strategy.strategy.config_service') as mock:
        # Mock get_strategy_config
        mock_strategy_config = Mock()
        mock_strategy_config.min_entry_price = 0.97
        mock_strategy_config.max_entry_spread = 0.02
        mock_strategy_config.safety_tick = 0.001
        mock_strategy_config.target_edge = 0.01
        mock_strategy_config.max_order_size = 5000.0
        mock_strategy_config.max_exposure_per_market = 10000.0
        mock_strategy_config.max_global_exposure = 200000.0
        mock_strategy_config.min_liquidity_required = 1000.0
        
        mock.get_strategy_config.return_value = mock_strategy_config
        
        # Mock get para parámetros adicionales
        mock.get.side_effect = lambda key, default=None: {
            "safety_tick_multiplier_yellow": 2.0,
            "safety_tick_multiplier_red": 3.0,
            "yellow_latency_size_factor": 0.5,
            "sports_old_event_minutes": 10,
            "sports_old_event_size_factor": 0.7,
            "sports_multi_source_threshold": 3,
            "sports_multi_source_size_factor": 1.1,
            "default_orderbook_liquidity": 10000.0,
        }.get(key, default)
        
        yield mock


def test_get_config_uses_config_service(strategy, mock_config_service):
    """Test que _get_config() usa ConfigService.get_strategy_config()."""
    config = strategy._get_config()
    
    # Verificar que se llamó a get_strategy_config
    mock_config_service.get_strategy_config.assert_called()
    
    # Verificar que retorna el config mockeado
    assert config.min_entry_price == 0.97
    assert config.max_entry_spread == 0.02


def test_calculate_target_price_uses_safety_tick_multipliers(strategy, mock_config_service):
    """Test que _calculate_target_price usa multiplicadores desde ConfigService."""
    best_ask = 0.99
    best_bid = 0.98
    
    # Test con YELLOW
    target_yellow = strategy._calculate_target_price(
        best_ask, best_bid, LatencyStatus.YELLOW
    )
    
    # Verificar que se obtuvo el multiplicador
    mock_config_service.get.assert_any_call("safety_tick_multiplier_yellow", 2.0)
    
    # Test con RED
    target_red = strategy._calculate_target_price(
        best_ask, best_bid, LatencyStatus.RED
    )
    
    # Verificar que se obtuvo el multiplicador
    mock_config_service.get.assert_any_call("safety_tick_multiplier_red", 3.0)
    
    # RED debería tener precio más bajo (más conservador)
    assert target_red <= target_yellow


def test_calculate_size_uses_yellow_latency_factor(strategy, mock_config_service):
    """Test que _calculate_size usa yellow_latency_size_factor desde ConfigService."""
    market_id = uuid4()
    target_price = 0.99
    orderbook_liquidity = 10000.0
    
    event_state = EventState(
        event_status="FINISHED_CONFIRMED",
        confidence_score=0.9,
        sources_state={},
        last_update=datetime.utcnow(),
        event_type="sports"
    )
    
    # Mock state para evitar dependencias
    with patch('app.core.strategy.strategy.state') as mock_state:
        mock_state.exposures = {}
        mock_state.markets = {}
        
        # Test con YELLOW
        size_yellow = strategy._calculate_size(
            market_id, target_price, orderbook_liquidity, event_state, LatencyStatus.YELLOW
        )
        
        # Verificar que se obtuvo el factor
        mock_config_service.get.assert_any_call("yellow_latency_size_factor", 0.5)
        
        # Test con GREEN
        size_green = strategy._calculate_size(
            market_id, target_price, orderbook_liquidity, event_state, LatencyStatus.GREEN
        )
        
        # YELLOW debería tener tamaño menor
        assert size_yellow <= size_green


def test_apply_sports_heuristics_uses_config_service(strategy, mock_config_service):
    """Test que _apply_sports_heuristics usa parámetros desde ConfigService."""
    base_size = 1000.0
    
    # Test con evento viejo
    old_event_state = EventState(
        event_status="FINISHED_CONFIRMED",
        confidence_score=0.9,
        sources_state={},
        event_finished_at=datetime.utcnow() - timedelta(minutes=15),
        last_update=datetime.utcnow(),
        event_type="sports"
    )
    
    config = strategy._get_config()
    size_old = strategy._apply_sports_heuristics(base_size, old_event_state, config)
    
    # Verificar que se obtuvieron los parámetros
    mock_config_service.get.assert_any_call("sports_old_event_minutes", 10)
    mock_config_service.get.assert_any_call("sports_old_event_size_factor", 0.7)
    
    # Tamaño debería ser menor
    assert size_old < base_size
    
    # Test con múltiples fuentes
    multi_source_state = EventState(
        event_status="FINISHED_CONFIRMED",
        confidence_score=0.9,
        sources_state={"source1": "FINISHED", "source2": "FINISHED", "source3": "FINISHED"},
        last_update=datetime.utcnow(),
        event_type="sports"
    )
    
    size_multi = strategy._apply_sports_heuristics(base_size, multi_source_state, config)
    
    # Verificar que se obtuvieron los parámetros
    mock_config_service.get.assert_any_call("sports_multi_source_threshold", 3)
    mock_config_service.get.assert_any_call("sports_multi_source_size_factor", 1.1)
    
    # Tamaño debería ser mayor
    assert size_multi > base_size


def test_get_orderbook_liquidity_uses_default(strategy, mock_config_service):
    """Test que _get_orderbook_liquidity usa default_orderbook_liquidity desde ConfigService."""
    market_id = uuid4()
    target_price = 0.99
    
    # Mock state sin orderbook
    with patch('app.core.strategy.strategy.state') as mock_state:
        mock_state.markets = {}
        
        liquidity = strategy._get_orderbook_liquidity(market_id, target_price)
        
        # Verificar que se obtuvo el default
        mock_config_service.get.assert_any_call("default_orderbook_liquidity", 10000.0)
        
        # Debería retornar el default
        assert liquidity == 10000.0

