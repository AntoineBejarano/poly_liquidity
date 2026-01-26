"""
Tests unitarios para CompensatePlanNode con 100% de cobertura.
"""
import pytest
from uuid import uuid4
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from app.core.strategy_engine.nodes.compensate_plan import CompensatePlanNode
from app.core.strategy_engine.nodes.base import SuccessResult, FailureResult
from app.core.strategy_engine.models import GraphExecutionContext
from app.models.execution_plan import ExecutionPlan
from app.models.event import Event


class TestCompensatePlanNode:
    """Tests para CompensatePlanNode."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock de SQLAlchemy Session."""
        db = Mock()
        db.query = Mock()
        db.flush = Mock()
        return db
    
    @pytest.fixture
    def mock_plan(self):
        """Mock de ExecutionPlan."""
        plan = Mock(spec=ExecutionPlan)
        plan.id = uuid4()
        plan.status = "EXECUTING"
        plan.legs = [
            {
                "leg_id": "leg_1",
                "side": "BUY",
                "outcome": "YES",
                "status": "FILLED",
                "filled_size": Decimal("1000"),
                "filled_size_usdc": Decimal("950"),
                "order_id": uuid4()
            }
        ]
        return plan
    
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
        return context
    
    @pytest.mark.asyncio
    async def test_execute_missing_plan_id(self, context):
        """Test que falla si no se proporciona plan_id."""
        config = {}
        node = CompensatePlanNode(config, context)
        
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "plan_id is required" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_plan_not_found(self, context, mock_db):
        """Test que falla si el plan no existe."""
        plan_id = uuid4()
        config = {"plan_id": str(plan_id)}
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = None
        mock_db.query.return_value = query_mock
        
        node = CompensatePlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "not found" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_invalid_status(self, context, mock_db, mock_plan):
        """Test que falla si el plan está en estado inválido."""
        plan_id = mock_plan.id
        config = {"plan_id": str(plan_id)}
        mock_plan.status = "COMPLETED"  # Estado terminal
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = CompensatePlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Cannot compensate plan in status" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_reverse_all(self, context, mock_db, mock_plan):
        """Test compensación con estrategia reverse_all."""
        plan_id = mock_plan.id
        config = {
            "plan_id": str(plan_id),
            "compensation_strategy": "reverse_all"
        }
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = CompensatePlanNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.compensate_plan.validate_compensation_only_reduces_exposure'):
            result = await node.execute()
        
        assert isinstance(result, SuccessResult)
        assert mock_plan.status == "ABORTED"
    
    @pytest.mark.asyncio
    async def test_execute_cancel_all(self, context, mock_db, mock_plan):
        """Test compensación con estrategia cancel_all."""
        plan_id = mock_plan.id
        mock_plan.legs[0]["status"] = "PENDING"
        config = {
            "plan_id": str(plan_id),
            "compensation_strategy": "cancel_all"
        }
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = CompensatePlanNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.compensate_plan.validate_compensation_only_reduces_exposure'):
            result = await node.execute()
        
        assert isinstance(result, SuccessResult)
    
    @pytest.mark.asyncio
    async def test_execute_partial_missing_leg_ids(self, context, mock_db, mock_plan):
        """Test que falla si se usa partial sin leg_ids."""
        plan_id = mock_plan.id
        config = {
            "plan_id": str(plan_id),
            "compensation_strategy": "partial"
        }
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = CompensatePlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "leg_ids required" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_partial_with_leg_ids(self, context, mock_db, mock_plan):
        """Test compensación con estrategia partial."""
        plan_id = mock_plan.id
        config = {
            "plan_id": str(plan_id),
            "compensation_strategy": "partial",
            "leg_ids": ["leg_1"]
        }
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = CompensatePlanNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.compensate_plan.validate_compensation_only_reduces_exposure'):
            result = await node.execute()
        
        assert isinstance(result, SuccessResult)
    
    @pytest.mark.asyncio
    async def test_execute_unknown_strategy(self, context, mock_db, mock_plan):
        """Test que falla con estrategia desconocida."""
        plan_id = mock_plan.id
        config = {
            "plan_id": str(plan_id),
            "compensation_strategy": "unknown"
        }
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = CompensatePlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Unknown compensation_strategy" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_no_legs_to_compensate(self, context, mock_db, mock_plan):
        """Test que retorna success si no hay legs para compensar."""
        plan_id = mock_plan.id
        mock_plan.legs[0]["status"] = "CANCELLED"  # Ya cancelado
        config = {
            "plan_id": str(plan_id),
            "compensation_strategy": "reverse_all"
        }
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = CompensatePlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
    
    @pytest.mark.asyncio
    async def test_execute_validation_error(self, context, mock_db, mock_plan):
        """Test que falla si la validación de compensación falla."""
        plan_id = mock_plan.id
        config = {
            "plan_id": str(plan_id),
            "compensation_strategy": "reverse_all"
        }
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = CompensatePlanNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.compensate_plan.validate_compensation_only_reduces_exposure') as validate_mock:
            validate_mock.side_effect = ValueError("Compensation validation failed")
            result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Compensation validation failed" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_with_execution_engine(self, context, mock_db, mock_plan):
        """Test compensación con execution_engine disponible."""
        plan_id = mock_plan.id
        config = {
            "plan_id": str(plan_id),
            "compensation_strategy": "reverse_all"
        }
        context.execution_engine = Mock()
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = CompensatePlanNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.compensate_plan.validate_compensation_only_reduces_exposure'):
            result = await node.execute()
        
        assert isinstance(result, SuccessResult)
    
    @pytest.mark.asyncio
    async def test_resolve_template_plan_id(self, context):
        """Test resolución de template con plan_id."""
        plan_id = uuid4()
        context.plan_id = plan_id
        node = CompensatePlanNode({}, context)
        
        result = node._resolve_template("{{plan.id}}")
        assert result == plan_id or str(result) == str(plan_id)
    
    @pytest.mark.asyncio
    async def test_resolve_template_unresolved(self, context):
        """Test que falla con template no resuelto."""
        node = CompensatePlanNode({}, context)
        
        with pytest.raises(ValueError, match="could not be resolved"):
            node._resolve_template("{{plan.id}}")
    
    @pytest.mark.asyncio
    async def test_resolve_template_no_template(self, context):
        """Test que retorna valor sin template."""
        node = CompensatePlanNode({}, context)
        
        result = node._resolve_template("plain_string")
        assert result == "plain_string"
        
        result = node._resolve_template(None)
        assert result is None
