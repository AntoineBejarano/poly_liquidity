"""
Tests unitarios para ConfigService con hot reload y métodos por componente.
"""
import pytest
import time
import threading
from unittest.mock import Mock, patch
from app.core.config_service import SystemConfigService
from app.models.system_config import SystemConfig


@pytest.fixture
def config_service():
    """Fixture para ConfigService."""
    return SystemConfigService(hot_reload_interval_seconds=1)


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    with patch('app.core.config_service.SessionLocal') as mock_session:
        db = Mock()
        mock_session.return_value = db
        yield db


def test_load_from_db(config_service, mock_db_session):
    """Test que load_from_db carga configuración correctamente."""
    # Mock configs
    config1 = Mock(spec=SystemConfig)
    config1.key = "test_key"
    config1.value = "123"
    config1.value_type = "int"
    config1.is_readonly = False
    config1.requires_confirmation = False
    config1.category = "system"
    config1.execution_mode = None
    config1.min_value = None
    config1.max_value = None
    config1.validation_rule = None
    config1.updated_at = None
    
    config2 = Mock(spec=SystemConfig)
    config2.key = "test_bool"
    config2.value = "true"
    config2.value_type = "bool"
    config2.is_readonly = True
    config2.requires_confirmation = True
    config2.category = "risk"
    config2.execution_mode = None
    config2.min_value = None
    config2.max_value = None
    config2.validation_rule = None
    config2.updated_at = None
    
    mock_db_session.query.return_value.all.return_value = [config1, config2]
    
    config_service.load_from_db()
    
    assert config_service.get("test_key") == 123
    assert config_service.get("test_bool") is True
    assert config_service.is_readonly("test_bool") is True
    assert config_service.requires_confirmation("test_bool") is True


def test_get_strategy_config(config_service, mock_db_session):
    """Test que get_strategy_config retorna StrategyConfig."""
    # Mock empty configs
    mock_db_session.query.return_value.all.return_value = []
    
    config_service.load_from_db()
    
    strategy_config = config_service.get_strategy_config()
    
    assert strategy_config is not None
    assert hasattr(strategy_config, "min_entry_price")
    assert hasattr(strategy_config, "max_entry_spread")
    assert hasattr(strategy_config, "safety_tick")


def test_get_risk_engine_config(config_service, mock_db_session):
    """Test que get_risk_engine_config retorna RiskEngineConfig."""
    # Mock empty configs
    mock_db_session.query.return_value.all.return_value = []
    
    config_service.load_from_db()
    
    risk_config = config_service.get_risk_engine_config()
    
    assert risk_config is not None
    assert hasattr(risk_config, "max_market_exposure")
    assert hasattr(risk_config, "max_global_exposure")
    assert hasattr(risk_config, "latency_fail_mode")


def test_get_execution_mode(config_service, mock_db_session):
    """Test que get_execution_mode retorna el modo de ejecución."""
    # Mock config with execution_mode
    config = Mock(spec=SystemConfig)
    config.key = "execution_mode"
    config.value = "PAPER"
    config.value_type = "string"
    config.is_readonly = False
    config.requires_confirmation = True
    config.category = "execution"
    config.execution_mode = "PAPER"
    config.min_value = None
    config.max_value = None
    config.validation_rule = None
    config.updated_at = None
    
    mock_db_session.query.return_value.all.return_value = [config]
    
    config_service.load_from_db()
    
    assert config_service.get_execution_mode() == "PAPER"


def test_get_by_category(config_service, mock_db_session):
    """Test que get_by_category retorna configs de una categoría."""
    # Mock configs
    config1 = Mock(spec=SystemConfig)
    config1.key = "strategy_param1"
    config1.value = "100"
    config1.value_type = "int"
    config1.is_readonly = False
    config1.requires_confirmation = False
    config1.category = "strategy"
    config1.execution_mode = None
    config1.min_value = None
    config1.max_value = None
    config1.validation_rule = None
    config1.updated_at = None
    
    config2 = Mock(spec=SystemConfig)
    config2.key = "risk_param1"
    config2.value = "200"
    config2.value_type = "int"
    config2.is_readonly = False
    config2.requires_confirmation = False
    config2.category = "risk"
    config2.execution_mode = None
    config2.min_value = None
    config2.max_value = None
    config2.validation_rule = None
    config2.updated_at = None
    
    mock_db_session.query.return_value.all.return_value = [config1, config2]
    
    config_service.load_from_db()
    
    strategy_configs = config_service.get_by_category("strategy")
    assert "strategy_param1" in strategy_configs
    assert "risk_param1" not in strategy_configs
    
    risk_configs = config_service.get_by_category("risk")
    assert "risk_param1" in risk_configs
    assert "strategy_param1" not in risk_configs


def test_hot_reload_start_stop(config_service):
    """Test que hot reload se inicia y detiene correctamente."""
    assert not config_service._hot_reload_active
    
    config_service.start_hot_reload()
    
    # Wait a bit for thread to start
    time.sleep(0.1)
    
    assert config_service._hot_reload_active
    assert config_service._hot_reload_thread is not None
    assert config_service._hot_reload_thread.is_alive()
    
    config_service.stop_hot_reload()
    
    # Wait a bit for thread to stop
    time.sleep(0.2)
    
    assert not config_service._hot_reload_active


def test_parse_value_types(config_service):
    """Test que _parse_value maneja diferentes tipos correctamente."""
    # Test int
    config_int = Mock(spec=SystemConfig)
    config_int.value = "123"
    config_int.value_type = "int"
    assert config_service._parse_value(config_int) == 123
    
    # Test float
    config_float = Mock(spec=SystemConfig)
    config_float.value = "123.45"
    config_float.value_type = "float"
    assert config_service._parse_value(config_float) == 123.45
    
    # Test bool
    config_bool = Mock(spec=SystemConfig)
    config_bool.value = "true"
    config_bool.value_type = "bool"
    assert config_service._parse_value(config_bool) is True
    
    # Test string
    config_string = Mock(spec=SystemConfig)
    config_string.value = "test_string"
    config_string.value_type = "string"
    assert config_service._parse_value(config_string) == "test_string"
    
    # Test json
    config_json = Mock(spec=SystemConfig)
    config_json.value = '{"key": "value"}'
    config_json.value_type = "json"
    result = config_service._parse_value(config_json)
    assert isinstance(result, dict)
    assert result["key"] == "value"
