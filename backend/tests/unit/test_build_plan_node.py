"""
Tests unitarios para BuildPlanNode con 100% de cobertura.
"""
import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from app.core.strategy_engine.nodes.build_plan import BuildPlanNode
from app.core.strategy_engine.nodes.base import PlanResult, FailureResult
from app.core.strategy_engine.models import GraphExecutionContext
from app.models.execution_plan import ExecutionPlan
from app.models.strategy import Strategy
from app.models.event import Event


class TestBuildPlanNode:
    """Tests para BuildPlanNode."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock de SQLAlchemy Session."""
        db = Mock()
        db.add = Mock()
        db.flush = Mock()
        return db
    
    @pytest.fixture
    def context(self, mock_db):
        """Contexto de ejecución."""
        context = GraphExecutionContext(
            strategy_id=uuid4(),
            event_id=uuid4(),
            market_id=uuid4(),
            trace_id=uuid4(),
            state_cache=Mock(),
            db=mock_db
        )
        context.calculated_price = Decimal("0.95")
        context.calculated_size = Decimal("1000")
        context.calculated_size_usdc = Decimal("950")
        return context
    
    @pytest.mark.asyncio
    async def test_build_plan_success_single_leg(self, context):
        """Test que build_plan crea un plan con un leg exitosamente."""
        plan_id = uuid4()
        # Configurar mock para que el plan tenga ID después de flush
        def mock_flush():
            call_args = context.db.add.call_args[0][0]
            call_args.id = plan_id
        
        context.db.flush.side_effect = mock_flush
        
        config = {
            "legs": [
                {
                    "leg_id": "leg_1",
                    "side": "BUY",
                    "outcome": "YES",
                    "target_price": "0.95",
                    "size": "1000",
                    "size_usdc": "950",
                    "reason": "Test leg"
                }
            ],
            "ttl_ms": 30000
        }
        
        node = BuildPlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, PlanResult)
        assert result.plan_id == plan_id
        context.db.add.assert_called_once()
        context.db.flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_build_plan_success_multiple_legs(self, context):
        """Test que build_plan crea un plan con múltiples legs."""
        plan_id = uuid4()
        def mock_flush():
            call_args = context.db.add.call_args[0][0]
            call_args.id = plan_id
        
        context.db.flush.side_effect = mock_flush
        
        config = {
            "legs": [
                {
                    "leg_id": "leg_1",
                    "side": "BUY",
                    "outcome": "YES",
                    "target_price": "0.95",
                    "size": "1000",
                    "size_usdc": "950",
                    "reason": "Leg 1"
                },
                {
                    "leg_id": "leg_2",
                    "side": "BUY",
                    "outcome": "NO",
                    "target_price": "0.05",
                    "size": "1000",
                    "size_usdc": "50",
                    "reason": "Leg 2"
                }
            ],
            "ttl_ms": 60000,
            "risk_config": {
                "max_slippage": 0.01
            }
        }
        
        node = BuildPlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, PlanResult)
        assert result.plan_id == plan_id
    
    @pytest.mark.asyncio
    async def test_build_plan_with_templates(self, context):
        """Test que build_plan resuelve templates correctamente."""
        config = {
            "legs": [
                {
                    "leg_id": "leg_1",
                    "side": "BUY",
                    "outcome": "YES",
                    "target_price": "{{calculated_price}}",
                    "size": "{{calculated_size}}",
                    "size_usdc": "{{calculated_size_usdc}}",
                    "reason": "Test with templates"
                }
            ],
            "ttl_ms": 30000
        }
        
        node = BuildPlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, PlanResult)
        # Verificar que se llamó add con un ExecutionPlan
        call_args = context.db.add.call_args[0][0]
        assert isinstance(call_args, ExecutionPlan)
        assert len(call_args.legs) == 1
        leg = call_args.legs[0]
        assert Decimal(str(leg["target_price"])) == Decimal("0.95")
        assert Decimal(str(leg["size"])) == Decimal("1000")
        assert Decimal(str(leg["size_usdc"])) == Decimal("950")
    
    @pytest.mark.asyncio
    async def test_build_plan_no_db(self, context):
        """Test que falla si no hay DB session."""
        context.db = None
        config = {
            "legs": [{
                "leg_id": "leg_1",
                "side": "BUY",
                "outcome": "YES",
                "target_price": "0.95",
                "size": "1000",
                "size_usdc": "950",
                "reason": "Test"
            }],
            "ttl_ms": 30000
        }
        
        node = BuildPlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Database session required" in result.error
    
    @pytest.mark.asyncio
    async def test_build_plan_no_legs(self, context):
        """Test que falla si no hay legs."""
        config = {
            "legs": [],
            "ttl_ms": 30000
        }
        
        node = BuildPlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "At least one leg is required" in result.error
    
    @pytest.mark.asyncio
    async def test_build_plan_invalid_leg_missing_field(self, context):
        """Test que falla si un leg tiene campos faltantes."""
        config = {
            "legs": [
                {
                    "leg_id": "leg_1",
                    "side": "BUY",
                    # Falta outcome
                    "target_price": "0.95",
                    "size": "1000",
                    "size_usdc": "950",
                    "reason": "Test"
                }
            ],
            "ttl_ms": 30000
        }
        
        node = BuildPlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Error processing leg" in result.error
    
    @pytest.mark.asyncio
    async def test_build_plan_invalid_leg_invalid_side(self, context):
        """Test que falla si un leg tiene side inválido."""
        config = {
            "legs": [
                {
                    "leg_id": "leg_1",
                    "side": "INVALID",
                    "outcome": "YES",
                    "target_price": "0.95",
                    "size": "1000",
                    "size_usdc": "950",
                    "reason": "Test"
                }
            ],
            "ttl_ms": 30000
        }
        
        node = BuildPlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Error processing leg" in result.error
    
    @pytest.mark.asyncio
    async def test_build_plan_template_unresolved(self, context):
        """Test que falla si un template no se puede resolver."""
        config = {
            "legs": [
                {
                    "leg_id": "leg_1",
                    "side": "BUY",
                    "outcome": "YES",
                    "target_price": "{{unknown_template}}",
                    "size": "1000",
                    "size_usdc": "950",
                    "reason": "Test"
                }
            ],
            "ttl_ms": 30000
        }
        
        node = BuildPlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Unresolved template" in result.error
    
    @pytest.mark.asyncio
    async def test_build_plan_size_usdc_auto_calculated(self, context):
        """Test que size_usdc se calcula automáticamente si no se proporciona."""
        config = {
            "legs": [
                {
                    "leg_id": "leg_1",
                    "side": "BUY",
                    "outcome": "YES",
                    "target_price": "0.95",
                    "size": "1000",
                    # No size_usdc
                    "reason": "Test"
                }
            ],
            "ttl_ms": 30000
        }
        
        node = BuildPlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, PlanResult)
        call_args = context.db.add.call_args[0][0]
        leg = call_args.legs[0]
        # size_usdc debería ser 1000 * 0.95 = 950
        assert Decimal(leg["size_usdc"]) == Decimal("950")
    
    @pytest.mark.asyncio
    async def test_build_plan_with_metadata(self, context):
        """Test que build_plan acepta metadata en legs."""
        config = {
            "legs": [
                {
                    "leg_id": "leg_1",
                    "side": "BUY",
                    "outcome": "YES",
                    "target_price": "0.95",
                    "size": "1000",
                    "size_usdc": "950",
                    "reason": "Test",
                    "metadata": {
                        "source": "test",
                        "confidence": 0.9
                    }
                }
            ],
            "ttl_ms": 30000
        }
        
        node = BuildPlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, PlanResult)
        call_args = context.db.add.call_args[0][0]
        leg = call_args.legs[0]
        assert leg["metadata"]["source"] == "test"
        assert leg["metadata"]["confidence"] == 0.9
    
    @pytest.mark.asyncio
    async def test_build_plan_with_risk_config(self, context):
        """Test que build_plan acepta risk_config."""
        risk_config = {
            "max_slippage": 0.01,
            "max_fill_delay_ms": 5000,
            "abort_on_price_move": True
        }
        
        config = {
            "legs": [
                {
                    "leg_id": "leg_1",
                    "side": "BUY",
                    "outcome": "YES",
                    "target_price": "0.95",
                    "size": "1000",
                    "size_usdc": "950",
                    "reason": "Test"
                }
            ],
            "ttl_ms": 30000,
            "risk_config": risk_config
        }
        
        node = BuildPlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, PlanResult)
        call_args = context.db.add.call_args[0][0]
        assert call_args.risk_config == risk_config
    
    @pytest.mark.asyncio
    async def test_build_plan_default_ttl(self, context):
        """Test que build_plan usa TTL por defecto si no se proporciona."""
        config = {
            "legs": [
                {
                    "leg_id": "leg_1",
                    "side": "BUY",
                    "outcome": "YES",
                    "target_price": "0.95",
                    "size": "1000",
                    "size_usdc": "950",
                    "reason": "Test"
                }
            ]
            # No ttl_ms
        }
        
        node = BuildPlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, PlanResult)
        call_args = context.db.add.call_args[0][0]
        assert call_args.ttl_ms == 60000  # Default
    
    @pytest.mark.asyncio
    async def test_build_plan_db_error(self, context):
        """Test que maneja errores de DB correctamente."""
        context.db.flush.side_effect = Exception("DB Error")
        
        config = {
            "legs": [
                {
                    "leg_id": "leg_1",
                    "side": "BUY",
                    "outcome": "YES",
                    "target_price": "0.95",
                    "size": "1000",
                    "size_usdc": "950",
                    "reason": "Test"
                }
            ],
            "ttl_ms": 30000
        }
        
        node = BuildPlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Error creating ExecutionPlan" in result.error
    
    def test_resolve_template_simple(self, context):
        """Test método _resolve_template con template simple."""
        node = BuildPlanNode({}, context)
        
        # Template simple - cuando el template es el valor completo, retorna el valor directamente
        result = node._resolve_template("{{calculated_price}}", {"calculated_price": Decimal("0.95")})
        assert result == Decimal("0.95")
        
        # Sin template
        result = node._resolve_template("0.95", {})
        assert result == "0.95"
        
        # None
        result = node._resolve_template(None, {})
        assert result is None
        
        # Template que reemplaza completamente con string
        result = node._resolve_template("{{calculated_price}}", {"calculated_price": "0.95"})
        assert result == "0.95"
    
    def test_resolve_template_partial(self, context):
        """Test método _resolve_template con template parcial."""
        node = BuildPlanNode({}, context)
        
        # Template parcial en string
        result = node._resolve_template("Price: {{calculated_price}}", {"calculated_price": Decimal("0.95")})
        assert result == "Price: 0.95"
    
    def test_process_leg_complete(self, context):
        """Test método _process_leg completo."""
        node = BuildPlanNode({}, context)
        
        leg_data = {
            "leg_id": "leg_1",
            "side": "BUY",
            "outcome": "YES",
            "target_price": "{{calculated_price}}",
            "size": "{{calculated_size}}",
            "size_usdc": "{{calculated_size_usdc}}",
            "reason": "Test",
            "metadata": {"test": True}
        }
        
        leg = node._process_leg(leg_data)
        
        assert leg.leg_id == "leg_1"
        assert leg.side == "BUY"
        assert leg.outcome == "YES"
        assert leg.target_price == Decimal("0.95")
        assert leg.size == Decimal("1000")
        assert leg.size_usdc == Decimal("950")
        assert leg.reason == "Test"
        assert leg.metadata["test"] is True
    
    def test_process_leg_target_price_none(self, context):
        """Test que _process_leg lanza error si target_price es None."""
        node = BuildPlanNode({}, context)
        
        leg_data = {
            "leg_id": "leg_1",
            "side": "BUY",
            "outcome": "YES",
            "target_price": None,  # None
            "size": "1000",
            "size_usdc": "950",
            "reason": "Test"
        }
        
        with pytest.raises(ValueError, match="target_price is required"):
            node._process_leg(leg_data)
    
    def test_process_leg_size_none(self, context):
        """Test que _process_leg lanza error si size es None."""
        node = BuildPlanNode({}, context)
        
        leg_data = {
            "leg_id": "leg_1",
            "side": "BUY",
            "outcome": "YES",
            "target_price": "0.95",
            "size": None,  # None
            "size_usdc": "950",
            "reason": "Test"
        }
        
        with pytest.raises(ValueError, match="size is required"):
            node._process_leg(leg_data)
