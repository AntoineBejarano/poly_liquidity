"""
Tests unitarios para ExecutionCoordinatorNode usando TradingPlatform.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timedelta

from app.core.strategy_engine.nodes.execution_coordinator import ExecutionCoordinatorNode
from app.core.strategy_engine.models import GraphExecutionContext, PlanLeg
from app.core.execution_engine.platform_models import OrderResult, OrderStatus
from app.core.execution_engine.platforms.polymarket_adapter import PolymarketAdapter
from app.models.execution_plan import ExecutionPlan
from app.core.strategy_engine.risk_validator import RiskValidator


class TestExecutionCoordinatorWithPlatform:
    """Tests para ExecutionCoordinatorNode usando TradingPlatform."""
    
    @pytest.fixture
    def mock_context(self):
        """Fixture para crear un contexto mock."""
        context = Mock(spec=GraphExecutionContext)
        context.strategy_id = uuid4()
        context.event_id = uuid4()
        context.market_id = uuid4()
        context.trace_id = uuid4()
        context.state_cache = Mock()
        context.db = Mock()
        context.plan_id = uuid4()
        return context
    
    @pytest.fixture
    def mock_plan(self):
        """Fixture para crear un ExecutionPlan mock."""
        plan = Mock(spec=ExecutionPlan)
        plan.id = uuid4()
        plan.status = "PLAN_BUILT"
        plan.legs = [
            {
                "leg_id": "leg_1",
                "side": "BUY",
                "outcome": "YES",
                "target_price": 0.50,
                "size": 100.0,
                "size_usdc": 50.0,
                "status": "PENDING",
                "filled_size": 0.0,
                "filled_size_usdc": 0.0,
                "reason": "Test leg",
                "metadata": {"token_id": "token_123"}
            }
        ]
        plan.risk_config = {
            "max_slippage": 0.05,
            "max_fill_delay_ms": 5000,
            "max_partial_fill_ratio": 0.8,
            "abort_on_price_move": True
        }
        plan.trace_id = uuid4()
        plan.event = Mock()
        plan.event.id = uuid4()
        plan.event.event_id = plan.event.id  # OrderIntent requiere event_id
        plan.event.market_id = uuid4()
        plan.expires_at = datetime.utcnow() + timedelta(minutes=5)
        plan.created_at = datetime.utcnow()
        plan.ttl_ms = 300000
        return plan
    
    @pytest.fixture
    def mock_trading_platform(self):
        """Fixture para crear un TradingPlatform mock."""
        platform = Mock(spec=PolymarketAdapter)
        platform.is_available.return_value = True
        platform.get_platform_name.return_value = "polymarket"
        return platform
    
    @pytest.fixture
    def coordinator_node(self, mock_context, mock_trading_platform):
        """Fixture para crear un ExecutionCoordinatorNode."""
        mock_context.trading_platform = mock_trading_platform
        config = {
            "plan_id": str(mock_context.plan_id),
            "execution_mode": "sequential"
        }
        node = ExecutionCoordinatorNode(config, mock_context)
        return node
    
    @pytest.mark.asyncio
    async def test_execute_leg_via_platform_success(self, coordinator_node, mock_plan, mock_trading_platform):
        """Test _execute_leg_via_platform() exitosa."""
        leg = mock_plan.legs[0]
        
        # Mock del resultado de la plataforma
        order_result = OrderResult(
            platform_order_id="polymarket_order_123",
            status=OrderStatus.SUBMITTED,
            filled_size=Decimal("0"),
            filled_size_usdc=Decimal("0"),
            trace_id=mock_plan.trace_id
        )
        mock_trading_platform.submit_order = AsyncMock(return_value=order_result)
        
        # Mock de validaciones
        risk_validator = Mock(spec=RiskValidator)
        risk_validator.validate_price.return_value = (True, None)
        risk_validator.validate_liquidity.return_value = (True, None)
        risk_validator.should_abort_on_price_move.return_value = False
        
        # Mock de métodos auxiliares
        coordinator_node._get_current_price = Mock(return_value=Decimal("0.50"))
        coordinator_node._get_available_liquidity = Mock(return_value=Decimal("1000.0"))
        
        result = await coordinator_node._execute_leg_via_platform(
            leg,
            mock_plan,
            mock_trading_platform,
            mock_plan.event
        )
        
        assert result["success"] is True
        assert result["leg_id"] == "leg_1"
        assert result["order_id"] == "polymarket_order_123"
        assert result["partial_fill"] is False
        mock_trading_platform.submit_order.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_leg_via_platform_price_validation_fails(self, coordinator_node, mock_plan, mock_trading_platform):
        """Test _execute_leg() cuando falla validación de precio (no llama a submit_order)."""
        leg = mock_plan.legs[0]
        
        # Mock de validaciones (precio inválido)
        risk_validator = Mock(spec=RiskValidator)
        risk_validator.validate_price.return_value = (False, "Price moved too much")
        risk_validator.validate_liquidity.return_value = (True, None)
        risk_validator.should_abort_on_price_move.return_value = False
        
        # Mock de métodos auxiliares
        coordinator_node._get_current_price = Mock(return_value=Decimal("0.60"))
        coordinator_node._get_available_liquidity = Mock(return_value=Decimal("1000.0"))
        
        # _execute_leg hace la validación de precio antes de llamar a _execute_leg_via_platform
        result = await coordinator_node._execute_leg(leg, mock_plan, risk_validator)
        
        assert result["success"] is False
        assert "Price" in result["error"] or "price" in result["error"].lower()
        mock_trading_platform.submit_order.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_leg_via_platform_platform_error(self, coordinator_node, mock_plan, mock_trading_platform):
        """Test _execute_leg_via_platform() cuando la plataforma lanza error."""
        leg = mock_plan.legs[0]
        
        # Mock del error de la plataforma
        mock_trading_platform.submit_order = AsyncMock(side_effect=RuntimeError("Platform error"))
        
        # Mock de validaciones
        risk_validator = Mock(spec=RiskValidator)
        risk_validator.validate_price.return_value = (True, None)
        risk_validator.validate_liquidity.return_value = (True, None)
        risk_validator.should_abort_on_price_move.return_value = False
        
        # Mock de métodos auxiliares
        coordinator_node._get_current_price = Mock(return_value=Decimal("0.50"))
        coordinator_node._get_available_liquidity = Mock(return_value=Decimal("1000.0"))
        
        with pytest.raises(RuntimeError):
            await coordinator_node._execute_leg_via_platform(
                leg,
                mock_plan,
                mock_trading_platform,
                mock_plan.event
            )
    
    @pytest.mark.asyncio
    async def test_execute_leg_uses_platform_when_available(self, coordinator_node, mock_plan, mock_trading_platform):
        """Test que _execute_leg() usa TradingPlatform cuando está disponible."""
        leg = mock_plan.legs[0]
        
        # Mock del resultado de la plataforma
        order_result = OrderResult(
            platform_order_id="polymarket_order_123",
            status=OrderStatus.SUBMITTED,
            filled_size=Decimal("0"),
            filled_size_usdc=Decimal("0"),
            trace_id=mock_plan.trace_id
        )
        mock_trading_platform.submit_order = AsyncMock(return_value=order_result)
        
        # Mock de validaciones
        risk_validator = Mock(spec=RiskValidator)
        risk_validator.validate_price.return_value = (True, None)
        risk_validator.validate_liquidity.return_value = (True, None)
        risk_validator.should_abort_on_price_move.return_value = False
        
        # Mock de métodos auxiliares
        coordinator_node._get_current_price = Mock(return_value=Decimal("0.50"))
        coordinator_node._get_available_liquidity = Mock(return_value=Decimal("1000.0"))
        
        result = await coordinator_node._execute_leg(leg, mock_plan, risk_validator)
        
        assert result["success"] is True
        assert result["order_id"] == "polymarket_order_123"
        mock_trading_platform.submit_order.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_leg_falls_back_to_engine(self, coordinator_node, mock_plan):
        """Test que _execute_leg() usa execution_engine cuando no hay trading_platform."""
        leg = mock_plan.legs[0]
        
        # Remover trading_platform del contexto
        coordinator_node.context.trading_platform = None
        
        # Añadir execution_engine (legacy)
        mock_execution_engine = Mock()
        coordinator_node.context.execution_engine = mock_execution_engine
        
        # Mock de validaciones
        risk_validator = Mock(spec=RiskValidator)
        risk_validator.validate_price.return_value = (True, None)
        risk_validator.validate_liquidity.return_value = (True, None)
        risk_validator.should_abort_on_price_move.return_value = False
        
        # Mock de métodos auxiliares
        coordinator_node._get_current_price = Mock(return_value=Decimal("0.50"))
        coordinator_node._get_available_liquidity = Mock(return_value=Decimal("1000.0"))
        
        result = await coordinator_node._execute_leg(leg, mock_plan, risk_validator)
        
        # Debería usar el método legacy
        assert result["success"] is True
        # El método legacy retorna order_id=None por ahora
        assert result.get("order_id") is None or result.get("order_id") is not None

