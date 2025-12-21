"""
Tests unitarios para factory de proveedores de señales.
"""
import pytest
from unittest.mock import Mock
from uuid import uuid4

from app.core.strategy_engine.indicators.factory import (
    create_signal_provider,
    register_provider
)
from app.core.strategy_engine.indicators.liquidity_provider import LiquidityProvider
from app.core.strategy_engine.indicators.arbitrage_provider import ArbitrageProvider
from app.core.strategy_engine.models import GraphExecutionContext


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


class TestFactory:
    """Tests para factory de proveedores."""
    
    def test_create_liquidity_provider(self, mock_context):
        """Test crear LiquidityProvider."""
        provider = create_signal_provider("liquidity", mock_context)
        
        assert isinstance(provider, LiquidityProvider)
        assert provider.context == mock_context
    
    def test_create_liquidity_near_end_provider(self, mock_context):
        """Test crear LiquidityProvider con alias liquidity_near_end."""
        provider = create_signal_provider("liquidity_near_end", mock_context)
        
        assert isinstance(provider, LiquidityProvider)
    
    def test_create_arbitrage_provider(self, mock_context):
        """Test crear ArbitrageProvider."""
        provider = create_signal_provider("surebet_arbitrage", mock_context)
        
        assert isinstance(provider, ArbitrageProvider)
        assert provider.context == mock_context
    
    def test_create_arbitrage_provider_alias(self, mock_context):
        """Test crear ArbitrageProvider con alias arbitrage."""
        provider = create_signal_provider("arbitrage", mock_context)
        
        assert isinstance(provider, ArbitrageProvider)
    
    def test_create_provider_invalid_type(self, mock_context):
        """Test crear proveedor con tipo inválido."""
        with pytest.raises(ValueError) as exc_info:
            create_signal_provider("invalid_type", mock_context)
        
        assert "Unsupported strategy_type" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)
    
    def test_register_provider(self, mock_context):
        """Test registrar un nuevo proveedor."""
        from app.core.strategy_engine.indicators.base import SignalProvider
        
        class CustomProvider(SignalProvider):
            def validate_data(self):
                return True
            
            def calculate_all(self):
                return {}
        
        # Registrar nuevo proveedor
        register_provider("custom", CustomProvider)
        
        # Verificar que se puede crear
        provider = create_signal_provider("custom", mock_context)
        assert isinstance(provider, CustomProvider)
    
    def test_register_provider_invalid_class(self, mock_context):
        """Test registrar proveedor con clase inválida."""
        class NotASignalProvider:
            pass
        
        with pytest.raises(TypeError) as exc_info:
            register_provider("invalid", NotASignalProvider)
        
        assert "subclass of SignalProvider" in str(exc_info.value)

