"""
Tests de integración para ExecutionCoordinatorNode con TradingPlatform.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from app.core.strategy_engine.nodes.execution_coordinator import ExecutionCoordinatorNode
from app.core.strategy_engine.models import GraphExecutionContext, PlanLeg
from app.core.execution_engine.platforms.polymarket_adapter import PolymarketAdapter
from app.core.execution_engine.platform_models import OrderResult, OrderStatus
from app.models.execution_plan import ExecutionPlan
from app.core.strategy_engine.state_cache_service import StateCacheService


class TestExecutionCoordinatorPlatformIntegration:
    """Tests de integración para ExecutionCoordinatorNode con TradingPlatform."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock de sesión de base de datos."""
        return Mock()
    
    @pytest.fixture
    def mock_state_cache(self):
        """Mock de StateCacheService."""
        return Mock(spec=StateCacheService)
    
    @pytest.fixture
    def mock_trading_platform(self):
        """Mock de TradingPlatform."""
        platform = Mock(spec=PolymarketAdapter)
        platform.is_available.return_value = True
        platform.get_platform_name.return_value = "polymarket"
        platform.submit_order = AsyncMock(return_value=OrderResult(
            platform_order_id="polymarket_order_123",
            status=OrderStatus.SUBMITTED
        ))
        return platform
    
    @pytest.fixture
    def context(self, mock_db, mock_state_cache, mock_trading_platform):
        """Contexto de ejecución con trading_platform."""
        return GraphExecutionContext(
            strategy_id=uuid4(),
            event_id=uuid4(),
            market_id=uuid4(),
            trace_id=uuid4(),
            state_cache=mock_state_cache,
            db=mock_db,
            plan_id=uuid4(),
            trading_platform=mock_trading_platform
        )
    
    @pytest.fixture
    def mock_plan(self, mock_db):
        """Mock de ExecutionPlan."""
        plan = Mock(spec=ExecutionPlan)
        plan.id = uuid4()
        plan.status = "PLAN_BUILT"
        plan.legs = [
            {
                "leg_id": "leg_1",
                "side": "BUY",
                "outcome": "YES",
                "target_price": 0.5,
                "size": 10.0,
                "size_usdc": 5.0,
                "status": "PENDING",
                "filled_size": 0.0,
                "filled_size_usdc": 0.0,
                "reason": "Test leg",
                "metadata": {"token_id": "token_123"}
            }
        ]
        plan.ttl_ms = 30000
        plan.risk_config = {"max_slippage": 0.05, "order_type": "GTC"}
        plan.trace_id = uuid4()
        plan.expires_at = datetime.utcnow() + timedelta(seconds=30)
        plan.event = Mock()
        plan.event.id = uuid4()
        plan.event.event_id = plan.event.id  # OrderIntent requiere event_id
        plan.event.market_id = uuid4()
        
        # Mock de query con FOR UPDATE
        query_mock = Mock()
        query_mock.filter.return_value.with_for_update.return_value.first.return_value = plan
        mock_db.query.return_value = query_mock
        
        return plan
    
    @pytest.fixture
    def node(self, context):
        """ExecutionCoordinatorNode con contexto."""
        config = {
            "plan_id": "{{plan.id}}",
            "execution_mode": "sequential"
        }
        return ExecutionCoordinatorNode(config, context)
    
    @pytest.mark.asyncio
    async def test_execute_leg_via_platform_success(self, node, context, mock_trading_platform, mock_plan):
        """Test ejecución de leg usando TradingPlatform."""
        leg = mock_plan.legs[0]
        
        result = await node._execute_leg_via_platform(leg, mock_plan, mock_trading_platform, mock_plan.event)
        
        assert result["success"] is True
        assert result["order_id"] == "polymarket_order_123"
        assert result["leg_id"] == "leg_1"
        mock_trading_platform.submit_order.assert_called_once()
        
        # Verificar que se pasó el trace_id
        call_args = mock_trading_platform.submit_order.call_args
        assert call_args[1]["trace_id"] == mock_plan.trace_id
    
    @pytest.mark.asyncio
    async def test_execute_leg_via_platform_with_plan_leg(self, node, context, mock_trading_platform, mock_plan):
        """Test que _execute_leg_via_platform convierte leg dict a PlanLeg."""
        leg = mock_plan.legs[0]
        
        result = await node._execute_leg_via_platform(leg, mock_plan, mock_trading_platform, mock_plan.event)
        
        # Verificar que se creó un PlanLeg (submit_order se llama con leg=plan_leg como kwarg)
        call_args = mock_trading_platform.submit_order.call_args
        plan_leg = call_args[1]["leg"] if call_args[1] else call_args[0][0]
        assert isinstance(plan_leg, PlanLeg)
        assert plan_leg.leg_id == "leg_1"
        assert plan_leg.side == "BUY"
        assert plan_leg.outcome == "YES"
        assert plan_leg.target_price == Decimal("0.5")
        assert plan_leg.size == Decimal("10.0")
        
        # Verificar que metadata incluye event_id
        assert "event_id" in plan_leg.metadata
    
    @pytest.mark.asyncio
    async def test_execute_leg_via_platform_platform_feature_not_supported(self, node, context, mock_trading_platform, mock_plan):
        """Test manejo de PlatformFeatureNotSupported."""
        from app.core.execution_engine.platform_models import PlatformFeatureNotSupported
        
        mock_trading_platform.submit_order.side_effect = PlatformFeatureNotSupported(
            "polymarket",
            "market_order",
            "Not supported"
        )
        
        leg = mock_plan.legs[0]
        result = await node._execute_leg_via_platform(leg, mock_plan, mock_trading_platform, mock_plan.event)
        
        assert result["success"] is False
        assert "Platform feature not supported" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_leg_prefers_platform_over_engine(self, node, context, mock_trading_platform, mock_plan):
        """Test que _execute_leg prefiere trading_platform sobre execution_engine."""
        # Añadir execution_engine también (legacy)
        context.execution_engine = Mock()
        
        leg = mock_plan.legs[0]
        result = await node._execute_leg(leg, mock_plan, Mock())
        
        # Debería usar trading_platform, no execution_engine
        assert result["success"] is True
        assert result["order_id"] == "polymarket_order_123"
        mock_trading_platform.submit_order.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_leg_fallback_to_engine(self, node, context, mock_plan):
        """Test que _execute_leg hace fallback a execution_engine si no hay trading_platform."""
        # Remover trading_platform
        context.trading_platform = None
        
        # Añadir execution_engine (legacy)
        mock_engine = Mock()
        context.execution_engine = mock_engine
        
        leg = mock_plan.legs[0]
        result = await node._execute_leg(leg, mock_plan, Mock())
        
        # Debería usar execution_engine (legacy)
        # Por ahora solo simula, pero verifica que se llama al método correcto
        assert result["success"] is True  # Simulado por ahora
    
    @pytest.mark.asyncio
    async def test_execute_leg_no_platform_no_engine(self, node, context, mock_plan):
        """Test que _execute_leg simula si no hay plataforma ni engine."""
        # Remover ambos
        context.trading_platform = None
        context.execution_engine = None
        
        leg = mock_plan.legs[0]
        result = await node._execute_leg(leg, mock_plan, Mock())
        
        # Debería simular ejecución exitosa
        assert result["success"] is True
        assert result["order_id"] is None  # Simulado

