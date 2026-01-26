"""
Tests unitarios para verificar que Risk Engine usa ConfigService.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta
from app.core.risk_engine.risk_engine import RiskEngine
from app.core.strategy.models import OrderIntent
from app.core.config_service import config_service
from app.core.latency_monitor import LatencyStatus
from app.core.runtime_supervisor import RuntimeMode


@pytest.fixture
def risk_engine():
    """Fixture para Risk Engine."""
    return RiskEngine()


@pytest.fixture
def mock_config_service():
    """Mock ConfigService."""
    with patch('app.core.risk_engine.risk_engine.config_service') as mock:
        # Mock get_risk_engine_config
        mock_risk_config = Mock()
        mock_risk_config.max_market_exposure = 10000.0
        mock_risk_config.max_global_exposure = 200000.0
        mock_risk_config.max_markets_active = 10
        mock_risk_config.max_order_size = 5000.0
        mock_risk_config.min_order_size = 100.0
        mock_risk_config.latency_fail_mode = "strict"
        mock_risk_config.reduce_size_in_yellow = True
        mock_risk_config.yellow_size_factor = 0.5
        mock_risk_config.cancel_on_red = True
        mock_risk_config.exposure_method = "notional"
        mock_risk_config.max_price_swing_pct = 0.05
        mock_risk_config.max_swing_time_seconds = 10.0
        mock_risk_config.min_realistic_spread = 0.001
        
        mock.get_risk_engine_config.return_value = mock_risk_config
        
        # Mock get para parámetros adicionales
        mock.get.side_effect = lambda key, default=None: {
            "price_history_window_seconds": 60,
        }.get(key, default)
        
        yield mock


def test_get_config_uses_config_service(risk_engine, mock_config_service):
    """Test que _get_config() usa ConfigService.get_risk_engine_config()."""
    config = risk_engine._get_config()
    
    # Verificar que se llamó a get_risk_engine_config
    mock_config_service.get_risk_engine_config.assert_called()
    
    # Verificar que retorna el config mockeado
    assert config.max_market_exposure == 10000.0
    assert config.max_global_exposure == 200000.0
    assert config.min_order_size == 100.0


def test_check_rule_6_uses_price_history_window(risk_engine, mock_config_service):
    """Test que _check_rule_6_price_swings usa price_history_window_seconds desde ConfigService."""
    market_id = uuid4()
    
    intent = OrderIntent(
        market_id=market_id,
        side="BUY",
        price=0.99,
        size=1000.0,
        reason="test",
        metadata={"spread": 0.002}
    )
    
    # Agregar historial de precios
    risk_engine._price_history[market_id] = [
        (0.98, datetime.utcnow() - timedelta(seconds=30)),
        (0.99, datetime.utcnow())
    ]
    
    # Mock state para evitar dependencias
    with patch('app.core.risk_engine.risk_engine.state') as mock_state:
        mock_state.events = {}
        
        # Ejecutar check
        is_valid, reason = risk_engine._check_rule_6_price_swings(intent)
        
        # Verificar que se obtuvo el parámetro
        mock_config_service.get.assert_any_call("price_history_window_seconds", 60)
        
        # Debería ser válido (no hay swing sospechoso)
        assert is_valid is True


def test_check_rule_5_uses_config_values(risk_engine, mock_config_service):
    """Test que _check_rule_5_latency_control usa valores desde ConfigService."""
    market_id = uuid4()
    
    intent = OrderIntent(
        market_id=market_id,
        side="BUY",
        price=0.99,
        size=1000.0,
        reason="test"
    )
    
    # Mock state
    with patch('app.core.risk_engine.risk_engine.state') as mock_state:
        mock_state.events = {}
        mock_state.exposures = {}
        mock_state.positions = {}
        mock_state.orders = {}
        
        # Mock latency monitor
        with patch('app.core.risk_engine.risk_engine.latency_monitor') as mock_latency:
            mock_latency.get_status.return_value = LatencyStatus.YELLOW
            
            # Mock import de main_module para evitar AttributeError
            with patch('builtins.__import__') as mock_import:
                # Simular que el import falla (como en el código real cuando no está disponible)
                mock_import.side_effect = ImportError("Cannot import main_module")
                
                is_valid, reason, latency_factor = risk_engine._check_rule_5_latency_control(intent)
                
                # Verificar que se obtuvo el config
                mock_config_service.get_risk_engine_config.assert_called()
                
                # Debería retornar factor de latencia si reduce_size_in_yellow es True
                config = risk_engine._get_config()
                if config.reduce_size_in_yellow:
                    assert latency_factor == config.yellow_size_factor


def test_adjust_size_uses_config_values(risk_engine, mock_config_service):
    """Test que _adjust_size usa min_order_size desde ConfigService."""
    market_id = uuid4()
    
    intent = OrderIntent(
        market_id=market_id,
        side="BUY",
        price=0.99,
        size=50.0,  # Menor que min_order_size
        reason="test"
    )
    
    # Mock state
    with patch('app.core.risk_engine.risk_engine.state') as mock_state:
        mock_state.exposures = {}
        
        final_size = risk_engine._adjust_size(intent, [], None)
        
        # Verificar que se obtuvo el config
        mock_config_service.get_risk_engine_config.assert_called()
        
        # Si el tamaño es menor que min_order_size, debería retornar 0.0
        config = risk_engine._get_config()
        if intent.size < config.min_order_size:
            assert final_size == 0.0

