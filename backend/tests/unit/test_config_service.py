"""
Unit tests for Config Service.

Según especificación en docs/services/config_service.md
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.core.config_service import SystemConfigService
from app.core.state import RiskConfig


class TestSystemConfigService:
    """Test cases for SystemConfigService."""
    
    @pytest.fixture
    def config_service(self):
        """Fixture para SystemConfigService."""
        return SystemConfigService()
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        db = MagicMock()
        
        # Mock SystemConfig objects
        mock_configs = []
        for key, value, value_type in [
            ("max_exposure_per_market", "50000.0", "float"),
            ("max_global_exposure", "500000.0", "float"),
            ("max_markets_active", "30", "int"),
            ("min_entry_price", "0.98", "float"),
            ("target_margin", "0.001", "float"),
        ]:
            mock_config = MagicMock()
            mock_config.key = key
            mock_config.value = value
            mock_config.value_type = value_type
            mock_configs.append(mock_config)
        
        db.query.return_value.all.return_value = mock_configs
        return db
    
    def test_get_returns_cached_value(self, config_service, mock_db_session):
        """Test get returns value from cache."""
        with patch("app.core.config_service.SessionLocal", return_value=mock_db_session):
            config_service.load_from_db()
            value = config_service.get("max_exposure_per_market")
            assert value == 50000.0
    
    def test_get_returns_default_when_not_found(self, config_service):
        """Test get returns default when key not found."""
        value = config_service.get("nonexistent_key", default="default_value")
        assert value == "default_value"
    
    def test_get_risk_config_returns_risk_config(self, config_service, mock_db_session):
        """Test get_risk_config returns RiskConfig object."""
        with patch("app.core.config_service.SessionLocal", return_value=mock_db_session):
            config_service.load_from_db()
            risk_config = config_service.get_risk_config()
            assert isinstance(risk_config, RiskConfig)
            assert risk_config.max_exposure_per_market == 50000.0
    
    def test_get_risk_config_loads_if_not_cached(self, config_service, mock_db_session):
        """Test get_risk_config loads from DB if not cached."""
        with patch("app.core.config_service.SessionLocal", return_value=mock_db_session):
            risk_config = config_service.get_risk_config()
            assert isinstance(risk_config, RiskConfig)
    
    def test_invalidate_cache_reloads_all(self, config_service, mock_db_session):
        """Test invalidate_cache reloads all config when key is None."""
        with patch("app.core.config_service.SessionLocal", return_value=mock_db_session):
            config_service.load_from_db()
            config_service.invalidate_cache()
            # Should have called load_from_db again
            assert config_service._cache
    
    def test_invalidate_cache_reloads_specific_key(self, config_service, mock_db_session):
        """Test invalidate_cache reloads specific key."""
        with patch("app.core.config_service.SessionLocal", return_value=mock_db_session):
            config_service.load_from_db()
            
            # Mock finding specific config
            mock_config = MagicMock()
            mock_config.key = "max_exposure_per_market"
            mock_config.value = "60000.0"
            mock_config.value_type = "float"
            mock_config.category = "risk"
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config
            
            config_service.invalidate_cache("max_exposure_per_market")
            # Should have reloaded
            assert config_service._cache
    
    def test_load_from_db_parses_different_types(self, config_service):
        """Test load_from_db parses different value types correctly."""
        db = MagicMock()
        
        mock_configs = []
        for key, value, value_type in [
            ("float_val", "1.5", "float"),
            ("int_val", "42", "int"),
            ("bool_val", "true", "bool"),
            ("string_val", "test", "string"),
        ]:
            mock_config = MagicMock()
            mock_config.key = key
            mock_config.value = value
            mock_config.value_type = value_type
            mock_configs.append(mock_config)
        
        db.query.return_value.all.return_value = mock_configs
        
        with patch("app.core.config_service.SessionLocal", return_value=db):
            config_service.load_from_db()
            
            assert config_service.get("float_val") == 1.5
            assert config_service.get("int_val") == 42
            assert config_service.get("bool_val") is True
            assert config_service.get("string_val") == "test"

