"""
Tests unitarios para SignalProvider (clase base).
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from app.core.strategy_engine.indicators.base import SignalProvider
from app.core.strategy_engine.models import GraphExecutionContext


class ConcreteSignalProvider(SignalProvider):
    """Implementación concreta para testing."""
    
    def validate_data(self) -> bool:
        return True
    
    def calculate_all(self):
        return {"test_signal": 1.0}


@pytest.fixture
def mock_context():
    """Crea un contexto mock para testing."""
    context = Mock(spec=GraphExecutionContext)
    context.strategy_id = uuid4()
    context.event_id = uuid4()
    context.market_id = uuid4()
    context.trace_id = uuid4()
    context.collected_state = {}
    return context


class TestSignalProvider:
    """Tests para SignalProvider."""
    
    def test_init(self, mock_context):
        """Test inicialización básica."""
        provider = ConcreteSignalProvider(mock_context)
        
        assert provider.context == mock_context
        assert provider._collected_state == {}
        assert provider._memo_cache == {}
        assert provider._memo_timestamps == {}
    
    def test_market_state_property(self, mock_context):
        """Test propiedad market_state."""
        mock_context.collected_state = {"market_state": {"price": 0.98}}
        provider = ConcreteSignalProvider(mock_context)
        
        assert provider.market_state == {"price": 0.98}
    
    def test_market_state_property_none(self, mock_context):
        """Test propiedad market_state cuando no existe."""
        mock_context.collected_state = {}
        provider = ConcreteSignalProvider(mock_context)
        
        assert provider.market_state is None
    
    def test_event_state_property(self, mock_context):
        """Test propiedad event_state."""
        mock_context.collected_state = {"event_state": {"state": "ACTIVE"}}
        provider = ConcreteSignalProvider(mock_context)
        
        assert provider.event_state == {"state": "ACTIVE"}
    
    def test_external_data_property(self, mock_context):
        """Test propiedad external_data."""
        mock_context.collected_state = {"external_data": {"source": "pinnacle"}}
        provider = ConcreteSignalProvider(mock_context)
        
        assert provider.external_data == {"source": "pinnacle"}
    
    def test_risk_state_property(self, mock_context):
        """Test propiedad risk_state."""
        mock_context.collected_state = {"risk_state": {"exposure": 1000}}
        provider = ConcreteSignalProvider(mock_context)
        
        assert provider.risk_state == {"exposure": 1000}
    
    def test_check_data_freshness_with_fresh_data(self, mock_context):
        """Test check_data_freshness con datos frescos."""
        provider = ConcreteSignalProvider(mock_context)
        
        # Datos con timestamp reciente (hace 1 segundo)
        data = {
            "last_update": datetime.utcnow() - timedelta(seconds=1)
        }
        
        result = provider.check_data_freshness(data, max_age_ms=5000)
        assert result is True
    
    def test_check_data_freshness_with_stale_data(self, mock_context):
        """Test check_data_freshness con datos obsoletos."""
        provider = ConcreteSignalProvider(mock_context)
        
        # Datos con timestamp viejo (hace 10 segundos)
        data = {
            "last_update": datetime.utcnow() - timedelta(seconds=10)
        }
        
        result = provider.check_data_freshness(data, max_age_ms=5000)
        assert result is False
    
    def test_check_data_freshness_with_iso_string(self, mock_context):
        """Test check_data_freshness con timestamp ISO string."""
        provider = ConcreteSignalProvider(mock_context)
        
        # Timestamp ISO string
        data = {
            "last_update": datetime.utcnow().isoformat()
        }
        
        result = provider.check_data_freshness(data, max_age_ms=5000)
        assert result is True
    
    def test_check_data_freshness_with_unix_timestamp_seconds(self, mock_context):
        """Test check_data_freshness con Unix timestamp en segundos."""
        provider = ConcreteSignalProvider(mock_context)
        
        # Unix timestamp en segundos
        data = {
            "last_update": datetime.utcnow().timestamp()
        }
        
        result = provider.check_data_freshness(data, max_age_ms=5000)
        assert result is True
    
    def test_check_data_freshness_with_unix_timestamp_milliseconds(self, mock_context):
        """Test check_data_freshness con Unix timestamp en milisegundos."""
        provider = ConcreteSignalProvider(mock_context)
        
        # Unix timestamp en milisegundos
        data = {
            "last_update": int(datetime.utcnow().timestamp() * 1000)
        }
        
        result = provider.check_data_freshness(data, max_age_ms=5000)
        assert result is True
    
    def test_check_data_freshness_without_timestamp(self, mock_context):
        """Test check_data_freshness sin timestamp (asume fresco con warning)."""
        provider = ConcreteSignalProvider(mock_context)
        
        data = {"price": 0.98}  # Sin timestamp
        
        result = provider.check_data_freshness(data, max_age_ms=5000)
        # Debe retornar True pero loggear warning
        assert result is True
    
    def test_check_data_freshness_empty_data(self, mock_context):
        """Test check_data_freshness con datos vacíos."""
        provider = ConcreteSignalProvider(mock_context)
        
        result = provider.check_data_freshness({}, max_age_ms=5000)
        assert result is False
    
    def test_memoize_caches_result(self, mock_context):
        """Test que memoize cachea el resultado."""
        provider = ConcreteSignalProvider(mock_context)
        
        call_count = [0]  # Usar lista para poder modificar desde closure
        
        def expensive_function():
            call_count[0] += 1
            return "cached_result"
        
        # Primera llamada: debe ejecutar la función
        result1 = provider.memoize("test_key", expensive_function)
        assert result1 == "cached_result"
        assert call_count[0] == 1
        
        # Segunda llamada: debe usar cache
        result2 = provider.memoize("test_key", expensive_function)
        assert result2 == "cached_result"
        assert call_count[0] == 1  # No se ejecutó de nuevo
    
    def test_memoize_different_keys(self, mock_context):
        """Test que memoize usa diferentes caches para diferentes keys."""
        provider = ConcreteSignalProvider(mock_context)
        
        def func1():
            return "result1"
        
        def func2():
            return "result2"
        
        result1 = provider.memoize("key1", func1)
        result2 = provider.memoize("key2", func2)
        
        assert result1 == "result1"
        assert result2 == "result2"
        assert provider._memo_cache["key1"] == "result1"
        assert provider._memo_cache["key2"] == "result2"
    
    def test_clear_memo_cache(self, mock_context):
        """Test que clear_memo_cache limpia el cache."""
        provider = ConcreteSignalProvider(mock_context)
        
        provider.memoize("key1", lambda: "result1")
        provider.memoize("key2", lambda: "result2")
        
        assert len(provider._memo_cache) == 2
        
        provider.clear_memo_cache()
        
        assert len(provider._memo_cache) == 0
        assert len(provider._memo_timestamps) == 0
    
    def test_validate_data_abstract(self, mock_context):
        """Test que validate_data es abstracto."""
        # Intentar instanciar directamente debe fallar
        with pytest.raises(TypeError):
            SignalProvider(mock_context)
    
    def test_calculate_all_abstract(self, mock_context):
        """Test que calculate_all es abstracto."""
        # Intentar instanciar directamente debe fallar
        with pytest.raises(TypeError):
            SignalProvider(mock_context)

