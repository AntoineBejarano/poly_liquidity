"""
Tests unitarios para CalculateOrderSizeNode con 100% de cobertura.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from decimal import Decimal

from app.core.strategy_engine.nodes.calculate_order_size import CalculateOrderSizeNode
from app.core.strategy_engine.nodes.base import CalculationResult, FailureResult
from app.core.strategy_engine.models import GraphExecutionContext


class TestCalculateOrderSizeNode:
    """Tests para CalculateOrderSizeNode."""
    
    @pytest.fixture
    def context(self):
        """Contexto de ejecución."""
        context = GraphExecutionContext(
            strategy_id=None,
            event_id=None,
            market_id=None,
            trace_id=None,
            state_cache=Mock(),
            db=Mock()
        )
        context.collected_state = {
            "market_state": {
                "last_price": 0.95,
                "price": 0.95
            },
            "risk_state": {
                "available_bank": 10000.0
            }
        }
        return context
    
    @pytest.mark.asyncio
    async def test_calculate_order_size_fixed_range(self, context):
        """Test que calcula tamaño usando fixed_range."""
        config = {
            "method": "fixed_range",
            "min": 100.0,
            "max": 1000.0
        }
        
        node = CalculateOrderSizeNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, CalculationResult)
        assert result.price == 0.95
        assert result.size_usdc == 1000.0  # max
        assert result.size == pytest.approx(1000.0 / 0.95, rel=1e-6)
        
        # Verificar que se guardó en contexto
        assert context.calculated_price == 0.95
        assert context.calculated_size == pytest.approx(1000.0 / 0.95, rel=1e-6)
        assert context.calculated_size_usdc == 1000.0
    
    @pytest.mark.asyncio
    async def test_calculate_order_size_percentage(self, context):
        """Test que calcula tamaño usando percentage."""
        config = {
            "method": "percentage",
            "percentage": 10.0  # 10% del bank
        }
        
        node = CalculateOrderSizeNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, CalculationResult)
        assert result.price == 0.95
        assert result.size_usdc == 1000.0  # 10% de 10000
        assert result.size == pytest.approx(1000.0 / 0.95, rel=1e-6)
    
    @pytest.mark.asyncio
    async def test_calculate_order_size_percentage_with_limits(self, context):
        """Test que percentage respeta límites min y max."""
        config = {
            "method": "percentage",
            "percentage": 50.0,  # 50% del bank = 5000
            "min": 100.0,
            "max": 2000.0  # Limita a 2000
        }
        
        node = CalculateOrderSizeNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, CalculationResult)
        assert result.size_usdc == 2000.0  # Limitado por max
    
    @pytest.mark.asyncio
    async def test_calculate_order_size_percentage_below_min(self, context):
        """Test que percentage aplica min si el resultado es menor."""
        config = {
            "method": "percentage",
            "percentage": 0.5,  # 0.5% del bank = 50
            "min": 100.0  # Min es mayor
        }
        
        node = CalculateOrderSizeNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, CalculationResult)
        assert result.size_usdc == 100.0  # Aplicado min
    
    @pytest.mark.asyncio
    async def test_calculate_order_size_default_method(self, context):
        """Test que usa fixed_range por defecto."""
        config = {
            "max": 500.0
        }
        
        node = CalculateOrderSizeNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, CalculationResult)
        assert result.size_usdc == 500.0
    
    @pytest.mark.asyncio
    async def test_calculate_order_size_no_market_price(self, context):
        """Test que falla si no hay precio de mercado."""
        context.collected_state = {}  # Sin market_state
        
        config = {
            "method": "fixed_range",
            "max": 1000.0
        }
        
        node = CalculateOrderSizeNode(config, context)
        
        with pytest.raises(ValueError, match="market price not available"):
            await node.execute()
    
    @pytest.mark.asyncio
    async def test_calculate_order_size_unknown_method(self, context):
        """Test que falla si el método es desconocido."""
        config = {
            "method": "unknown_method"
        }
        
        node = CalculateOrderSizeNode(config, context)
        
        with pytest.raises(ValueError, match="Unknown calculation method"):
            await node.execute()
    
    @pytest.mark.asyncio
    async def test_calculate_order_size_market_state_dict(self, context):
        """Test que obtiene precio de market_state dict."""
        context.collected_state = {
            "market_state": {
                "price": 0.85  # Sin last_price, usa price
            }
        }
        
        config = {
            "method": "fixed_range",
            "max": 1000.0
        }
        
        node = CalculateOrderSizeNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, CalculationResult)
        assert result.price == 0.85
    
    @pytest.mark.asyncio
    async def test_calculate_order_size_no_risk_state(self, context):
        """Test que usa bank por defecto si no hay risk_state."""
        context.collected_state = {
            "market_state": {
                "last_price": 0.95
            }
            # Sin risk_state
        }
        
        config = {
            "method": "percentage",
            "percentage": 5.0
        }
        
        node = CalculateOrderSizeNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, CalculationResult)
        # Debe usar bank por defecto (10000.0)
        assert result.size_usdc == pytest.approx(500.0, rel=1e-6)  # 5% de 10000
    
    @pytest.mark.asyncio
    async def test_calculate_order_size_no_collected_state(self, context):
        """Test que falla si no hay collected_state."""
        context.collected_state = None
        
        config = {
            "method": "fixed_range",
            "max": 1000.0
        }
        
        node = CalculateOrderSizeNode(config, context)
        
        with pytest.raises(ValueError, match="market price not available"):
            await node.execute()
    
    @pytest.mark.asyncio
    async def test_calculate_order_size_market_state_not_dict(self, context):
        """Test que maneja market_state que no es dict."""
        context.collected_state = {
            "market_state": "not_a_dict"
        }
        
        config = {
            "method": "fixed_range",
            "max": 1000.0
        }
        
        node = CalculateOrderSizeNode(config, context)
        
        with pytest.raises(ValueError, match="market price not available"):
            await node.execute()
    
    def test_get_market_price_from_last_price(self, context):
        """Test método _get_market_price obtiene last_price."""
        node = CalculateOrderSizeNode({}, context)
        price = node._get_market_price()
        
        assert price == 0.95
    
    def test_get_market_price_from_price(self, context):
        """Test método _get_market_price obtiene price si no hay last_price."""
        context.collected_state = {
            "market_state": {
                "price": 0.85  # Sin last_price
            }
        }
        
        node = CalculateOrderSizeNode({}, context)
        price = node._get_market_price()
        
        assert price == 0.85
    
    def test_get_market_price_no_market_state(self, context):
        """Test método _get_market_price retorna None si no hay market_state."""
        context.collected_state = {}
        
        node = CalculateOrderSizeNode({}, context)
        price = node._get_market_price()
        
        assert price is None
    
    def test_get_market_price_market_state_falsy(self, context):
        """Test método _get_market_price retorna None si market_state es falsy (línea 78)."""
        context.collected_state = {
            "market_state": None  # Falsy value
        }
        
        node = CalculateOrderSizeNode({}, context)
        price = node._get_market_price()
        
        assert price is None
    
    def test_get_market_price_no_collected_state(self, context):
        """Test método _get_market_price retorna None si no hay collected_state."""
        context.collected_state = None
        
        node = CalculateOrderSizeNode({}, context)
        price = node._get_market_price()
        
        assert price is None
    
    def test_get_market_price_market_state_no_price_fields(self, context):
        """Test método _get_market_price retorna None si market_state no tiene price ni last_price."""
        context.collected_state = {
            "market_state": {
                "other_field": "value"
            }
        }
        
        node = CalculateOrderSizeNode({}, context)
        price = node._get_market_price()
        
        assert price is None
    
    def test_calculate_fixed_range(self, context):
        """Test método _calculate_fixed_range."""
        config = {
            "min": 100.0,
            "max": 1000.0
        }
        
        node = CalculateOrderSizeNode(config, context)
        size_usdc = node._calculate_fixed_range()
        
        assert size_usdc == 1000.0  # max
    
    def test_calculate_fixed_range_defaults(self, context):
        """Test método _calculate_fixed_range con valores por defecto."""
        node = CalculateOrderSizeNode({}, context)
        size_usdc = node._calculate_fixed_range()
        
        assert size_usdc == 1000.0  # max por defecto
    
    def test_calculate_percentage(self, context):
        """Test método _calculate_percentage."""
        config = {
            "percentage": 10.0
        }
        
        node = CalculateOrderSizeNode(config, context)
        size_usdc = node._calculate_percentage()
        
        assert size_usdc == 1000.0  # 10% de 10000
    
    def test_calculate_percentage_with_limits(self, context):
        """Test método _calculate_percentage con límites."""
        config = {
            "percentage": 50.0,  # 5000
            "min": 100.0,
            "max": 2000.0
        }
        
        node = CalculateOrderSizeNode(config, context)
        size_usdc = node._calculate_percentage()
        
        assert size_usdc == 2000.0  # Limitado por max
    
    def test_calculate_percentage_no_risk_state(self, context):
        """Test método _calculate_percentage sin risk_state."""
        context.collected_state = {
            "market_state": {
                "last_price": 0.95
            }
        }
        
        config = {
            "percentage": 5.0
        }
        
        node = CalculateOrderSizeNode(config, context)
        size_usdc = node._calculate_percentage()
        
        assert size_usdc == pytest.approx(500.0, rel=1e-6)  # 5% de 10000 (default)
    
    def test_calculate_percentage_no_collected_state(self, context):
        """Test método _calculate_percentage sin collected_state."""
        context.collected_state = None
        
        config = {
            "percentage": 5.0
        }
        
        node = CalculateOrderSizeNode(config, context)
        size_usdc = node._calculate_percentage()
        
        assert size_usdc == pytest.approx(500.0, rel=1e-6)  # 5% de 10000 (default)

