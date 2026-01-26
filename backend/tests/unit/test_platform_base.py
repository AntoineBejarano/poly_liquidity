"""
Tests unitarios para TradingPlatform (interfaz base).
"""
import pytest
from unittest.mock import Mock, AsyncMock
from decimal import Decimal
from uuid import uuid4

from app.core.execution_engine.platform_base import TradingPlatform
from app.core.execution_engine.platform_models import (
    OrderResult,
    OrderStatusUpdate,
    OrderStatus,
    PlatformFeatureNotSupported
)
from app.core.strategy_engine.models import PlanLeg


class MockTradingPlatform(TradingPlatform):
    """Implementación mock de TradingPlatform para tests."""
    
    def __init__(self, platform_name="mock", config=None):
        super().__init__(platform_name, config or {})
        self._available = True
        self._submit_order_result = None
        self._cancel_order_result = True
        self._order_status_result = None
        self._balances_result = {}
    
    async def submit_order(self, leg, risk_config, trace_id=None):
        if self._submit_order_result is None:
            return OrderResult(
                platform_order_id="mock_order_123",
                status=OrderStatus.SUBMITTED
            )
        return self._submit_order_result
    
    async def cancel_order(self, order_id, trace_id=None):
        return self._cancel_order_result
    
    async def get_order_status(self, order_id, trace_id=None):
        if self._order_status_result is None:
            return OrderStatusUpdate(
                platform_order_id=order_id,
                status=OrderStatus.FILLED,
                filled_size=Decimal("10.0"),
                filled_size_usdc=Decimal("0"),
                remaining_size=Decimal("0")
            )
        return self._order_status_result
    
    async def get_balances(self):
        return self._balances_result
    
    def is_available(self):
        return self._available


class TestTradingPlatform:
    """Tests para TradingPlatform (interfaz base)."""
    
    def test_platform_initialization(self):
        """Test inicialización de plataforma."""
        platform = MockTradingPlatform("test_platform", {"key": "value"})
        
        assert platform.platform_name == "test_platform"
        assert platform.config == {"key": "value"}
        assert platform.get_platform_name() == "test_platform"
    
    def test_get_platform_name(self):
        """Test get_platform_name."""
        platform = MockTradingPlatform("my_platform")
        assert platform.get_platform_name() == "my_platform"
    
    @pytest.mark.asyncio
    async def test_submit_order_abstract(self):
        """Test que submit_order es abstracto y debe ser implementado."""
        # TradingPlatform es abstracto, no se puede instanciar directamente
        with pytest.raises(TypeError):
            TradingPlatform("test", {})
    
    @pytest.mark.asyncio
    async def test_submit_order_implementation(self):
        """Test implementación de submit_order."""
        platform = MockTradingPlatform()
        leg = PlanLeg(
            leg_id="leg_1",
            side="BUY",
            outcome="YES",
            target_price=Decimal("0.5"),
            size=Decimal("10.0"),
            size_usdc=Decimal("5.0"),
            reason="Test"
        )
        
        result = await platform.submit_order(leg, {})
        
        assert isinstance(result, OrderResult)
        assert result.platform_order_id == "mock_order_123"
    
    @pytest.mark.asyncio
    async def test_cancel_order_implementation(self):
        """Test implementación de cancel_order."""
        platform = MockTradingPlatform()
        
        result = await platform.cancel_order("order_123")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_order_status_implementation(self):
        """Test implementación de get_order_status."""
        platform = MockTradingPlatform()
        
        result = await platform.get_order_status("order_123")
        
        assert isinstance(result, OrderStatusUpdate)
        assert result.platform_order_id == "order_123"
        assert result.status == OrderStatus.FILLED
    
    @pytest.mark.asyncio
    async def test_get_balances_implementation(self):
        """Test implementación de get_balances."""
        platform = MockTradingPlatform()
        platform._balances_result = {"USDC": Decimal("1000.00")}
        
        result = await platform.get_balances()
        
        assert result == {"USDC": Decimal("1000.00")}
    
    def test_is_available_implementation(self):
        """Test implementación de is_available."""
        platform = MockTradingPlatform()
        assert platform.is_available() is True
        
        platform._available = False
        assert platform.is_available() is False
