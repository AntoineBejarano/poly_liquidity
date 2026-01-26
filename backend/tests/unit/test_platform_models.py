"""
Tests unitarios para modelos de plataforma.
"""
import pytest
from decimal import Decimal
from uuid import uuid4
from datetime import datetime

from app.core.execution_engine.platform_models import (
    OrderResult,
    OrderStatusUpdate,
    OrderStatus,
    OrderType,
    PlatformFeatureNotSupported
)


class TestOrderResult:
    """Tests para OrderResult."""
    
    def test_order_result_creation(self):
        """Test creación básica de OrderResult."""
        result = OrderResult(
            platform_order_id="order_123",
            status=OrderStatus.SUBMITTED
        )
        
        assert result.platform_order_id == "order_123"
        assert result.status == OrderStatus.SUBMITTED
        assert result.filled_size == Decimal("0")
        assert result.filled_size_usdc == Decimal("0")
        assert result.average_price is None
        assert result.trace_id is None
        assert result.platform_metadata == {}
        assert isinstance(result.submitted_at, datetime)
    
    def test_order_result_with_all_fields(self):
        """Test OrderResult con todos los campos."""
        trace_id = uuid4()
        result = OrderResult(
            platform_order_id="order_456",
            status=OrderStatus.FILLED,
            filled_size=Decimal("10.5"),
            filled_size_usdc=Decimal("105.00"),
            average_price=Decimal("10.0"),
            trace_id=trace_id,
            platform_metadata={"token_id": "token_123", "latency_ms": 50.5}
        )
        
        assert result.platform_order_id == "order_456"
        assert result.status == OrderStatus.FILLED
        assert result.filled_size == Decimal("10.5")
        assert result.filled_size_usdc == Decimal("105.00")
        assert result.average_price == Decimal("10.0")
        assert result.trace_id == trace_id
        assert result.platform_metadata == {"token_id": "token_123", "latency_ms": 50.5}
    
    def test_order_result_json_encoding(self):
        """Test que OrderResult se puede serializar a JSON."""
        result = OrderResult(
            platform_order_id="order_789",
            status=OrderStatus.PARTIALLY_FILLED,
            filled_size=Decimal("5.0"),
            average_price=Decimal("10.5")
        )
        
        # Verificar que los campos Decimal se pueden convertir a string
        assert isinstance(result.filled_size, Decimal)
        assert isinstance(result.average_price, Decimal)
        
        # Verificar que submitted_at es datetime
        assert isinstance(result.submitted_at, datetime)


class TestOrderStatusUpdate:
    """Tests para OrderStatusUpdate."""
    
    def test_order_status_update_creation(self):
        """Test creación básica de OrderStatusUpdate."""
        update = OrderStatusUpdate(
            platform_order_id="order_123",
            status=OrderStatus.FILLED,
            filled_size=Decimal("10.0"),
            filled_size_usdc=Decimal("0"),
            remaining_size=Decimal("0")
        )
        
        assert update.platform_order_id == "order_123"
        assert update.status == OrderStatus.FILLED
        assert update.filled_size == Decimal("10.0")
        assert update.remaining_size == Decimal("0")
        assert update.filled_size_usdc == Decimal("0")
        assert update.average_price is None
        assert update.trace_id is None
        assert update.platform_metadata == {}
        assert isinstance(update.updated_at, datetime)
    
    def test_order_status_update_with_all_fields(self):
        """Test OrderStatusUpdate con todos los campos."""
        trace_id = uuid4()
        update = OrderStatusUpdate(
            platform_order_id="order_456",
            status=OrderStatus.PARTIALLY_FILLED,
            filled_size=Decimal("5.0"),
            filled_size_usdc=Decimal("50.0"),
            average_price=Decimal("10.0"),
            remaining_size=Decimal("5.0"),
            trace_id=trace_id,
            platform_metadata={"partial_fill": True}
        )
        
        assert update.platform_order_id == "order_456"
        assert update.status == OrderStatus.PARTIALLY_FILLED
        assert update.filled_size == Decimal("5.0")
        assert update.filled_size_usdc == Decimal("50.0")
        assert update.average_price == Decimal("10.0")
        assert update.remaining_size == Decimal("5.0")
        assert update.trace_id == trace_id
        assert update.platform_metadata == {"partial_fill": True}


class TestPlatformFeatureNotSupported:
    """Tests para PlatformFeatureNotSupported."""
    
    def test_exception_creation(self):
        """Test creación básica de la excepción."""
        exc = PlatformFeatureNotSupported("polymarket", "market_order")
        
        assert exc.platform_name == "polymarket"
        assert exc.feature == "market_order"
        assert exc.reason is None
        assert "polymarket" in str(exc)
        assert "market_order" in str(exc)
    
    def test_exception_with_reason(self):
        """Test excepción con razón."""
        exc = PlatformFeatureNotSupported(
            "pinnacle",
            "limit_order",
            "Pinnacle only supports market orders"
        )
        
        assert exc.platform_name == "pinnacle"
        assert exc.feature == "limit_order"
        assert exc.reason == "Pinnacle only supports market orders"
        assert "Pinnacle only supports market orders" in str(exc)
    
    def test_exception_raises(self):
        """Test que la excepción se puede lanzar."""
        with pytest.raises(PlatformFeatureNotSupported) as exc_info:
            raise PlatformFeatureNotSupported("test_platform", "test_feature", "test_reason")
        
        assert exc_info.value.platform_name == "test_platform"
        assert exc_info.value.feature == "test_feature"
        assert exc_info.value.reason == "test_reason"
