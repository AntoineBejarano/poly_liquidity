"""
Tests unitarios para DerivePlanNode con 100% de cobertura.
"""
import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from app.core.strategy_engine.nodes.derive_plan import DerivePlanNode
from app.core.strategy_engine.nodes.base import PlanResult, FailureResult
from app.core.strategy_engine.models import GraphExecutionContext
from app.models.execution_plan import ExecutionPlan
from app.models.event import Event


class TestDerivePlanNode:
    """Tests para DerivePlanNode."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock de SQLAlchemy Session."""
        db = Mock()
        db.query = Mock()
        db.add = Mock()
        db.flush = Mock()
        db.rollback = Mock()
        return db
    
    @pytest.fixture
    def mock_event(self):
        """Mock de Event."""
        event = Mock(spec=Event)
        event.id = uuid4()
        event.market_id = uuid4()
        return event
    
    @pytest.fixture
    def mock_plan(self, mock_event):
        """Mock de ExecutionPlan."""
        plan = Mock(spec=ExecutionPlan)
        plan.id = uuid4()
        plan.status = "EXECUTING"
        plan.event = mock_event
        plan.trace_id = uuid4()
        plan.decision_graph_execution_id = uuid4()
        plan.ttl_ms = 30000
        plan.risk_config = {}
        plan.legs = [
            {
                "leg_id": "leg_1",
                "side": "BUY",
                "outcome": "YES",
                "target_price": Decimal("0.95"),
                "size": Decimal("1000"),
                "size_usdc": Decimal("950"),
                "status": "PARTIAL",
                "filled_size": Decimal("500"),
                "filled_size_usdc": Decimal("475"),
                "reason": "Test leg"
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
    async def test_execute_missing_base_plan_id(self, context):
        """Test que falla si no se proporciona base_plan_id."""
        config = {}
        node = DerivePlanNode(config, context)
        
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "base_plan_id is required" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_base_plan_not_found(self, context, mock_db):
        """Test que falla si el plan base no existe."""
        base_plan_id = uuid4()
        config = {"base_plan_id": str(base_plan_id)}
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = None
        mock_db.query.return_value = query_mock
        
        node = DerivePlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "not found" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_invalid_status(self, context, mock_db, mock_plan):
        """Test que falla si el plan base está en estado inválido."""
        base_plan_id = mock_plan.id
        config = {"base_plan_id": str(base_plan_id)}
        mock_plan.status = "COMPLETED"  # Estado terminal
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = DerivePlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Cannot derive plan from base plan in status" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_fill_remaining(self, context, mock_db, mock_plan, mock_event):
        """Test crear plan con estrategia fill_remaining."""
        base_plan_id = mock_plan.id
        config = {
            "base_plan_id": str(base_plan_id),
            "strategy": "fill_remaining"
        }
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        # Mock para el nuevo plan
        new_plan = Mock(spec=ExecutionPlan)
        new_plan.id = uuid4()
        mock_db.add.return_value = None
        
        node = DerivePlanNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.derive_plan.ExecutionPlan', return_value=new_plan):
            result = await node.execute()
        
        assert isinstance(result, PlanResult)
        assert result.plan_id == new_plan.id
    
    @pytest.mark.asyncio
    async def test_execute_retry_failed(self, context, mock_db, mock_plan, mock_event):
        """Test crear plan con estrategia retry_failed."""
        base_plan_id = mock_plan.id
        mock_plan.legs[0]["status"] = "FAILED"
        config = {
            "base_plan_id": str(base_plan_id),
            "strategy": "retry_failed"
        }
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        new_plan = Mock(spec=ExecutionPlan)
        new_plan.id = uuid4()
        
        node = DerivePlanNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.derive_plan.ExecutionPlan', return_value=new_plan):
            result = await node.execute()
        
        assert isinstance(result, PlanResult)
    
    @pytest.mark.asyncio
    async def test_execute_all_remaining(self, context, mock_db, mock_plan, mock_event):
        """Test crear plan con estrategia all_remaining."""
        base_plan_id = mock_plan.id
        config = {
            "base_plan_id": str(base_plan_id),
            "strategy": "all_remaining"
        }
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        new_plan = Mock(spec=ExecutionPlan)
        new_plan.id = uuid4()
        
        node = DerivePlanNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.derive_plan.ExecutionPlan', return_value=new_plan):
            result = await node.execute()
        
        assert isinstance(result, PlanResult)
    
    @pytest.mark.asyncio
    async def test_execute_unknown_strategy(self, context, mock_db, mock_plan):
        """Test que falla con estrategia desconocida."""
        base_plan_id = mock_plan.id
        config = {
            "base_plan_id": str(base_plan_id),
            "strategy": "unknown"
        }
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = DerivePlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Unknown strategy" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_no_legs_to_create(self, context, mock_db, mock_plan):
        """Test que falla si no hay legs para crear el plan."""
        base_plan_id = mock_plan.id
        mock_plan.legs[0]["status"] = "FILLED"  # Ya completado
        config = {
            "base_plan_id": str(base_plan_id),
            "strategy": "fill_remaining"
        }
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = DerivePlanNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "No legs to create follow-up plan" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_custom_ttl_and_risk_config(self, context, mock_db, mock_plan, mock_event):
        """Test crear plan con TTL y risk_config personalizados."""
        base_plan_id = mock_plan.id
        config = {
            "base_plan_id": str(base_plan_id),
            "strategy": "fill_remaining",
            "ttl_ms": 60000,
            "risk_config": {"max_slippage": 0.01}
        }
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        new_plan = Mock(spec=ExecutionPlan)
        new_plan.id = uuid4()
        
        node = DerivePlanNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.derive_plan.ExecutionPlan', return_value=new_plan) as mock_execution_plan:
            result = await node.execute()
            
            # Verificar que se usaron los valores personalizados
            call_args = mock_execution_plan.call_args
            assert call_args[1]["ttl_ms"] == 60000
            assert call_args[1]["risk_config"] == {"max_slippage": 0.01}
        
        assert isinstance(result, PlanResult)
    
    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, context, mock_db, mock_plan, mock_event):
        """Test manejo de excepciones."""
        base_plan_id = mock_plan.id
        config = {
            "base_plan_id": str(base_plan_id),
            "strategy": "fill_remaining"
        }
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = DerivePlanNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.derive_plan.ExecutionPlan', side_effect=Exception("Test error")):
            result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Error deriving plan" in result.error
    
    @pytest.mark.asyncio
    async def test_resolve_template_plan_id(self, context):
        """Test resolución de template con plan_id."""
        plan_id = uuid4()
        context.plan_id = plan_id
        node = DerivePlanNode({}, context)
        
        result = node._resolve_template("{{plan.id}}")
        assert result == plan_id or str(result) == str(plan_id)
    
    @pytest.mark.asyncio
    async def test_resolve_template_base_plan_id(self, context):
        """Test resolución de template con base_plan_id."""
        plan_id = uuid4()
        # El contexto puede tener plan_id o last_plan_id, pero no base_plan_id directamente
        # Vamos a usar plan_id que es lo que el código busca
        context.plan_id = plan_id
        node = DerivePlanNode({}, context)
        
        # El código busca plan_id, last_plan_id o base_plan_id en ese orden
        result = node._resolve_template("{{base_plan_id}}")
        # Si no encuentra base_plan_id, buscará plan_id
        assert result == plan_id or str(result) == str(plan_id)
    
    @pytest.mark.asyncio
    async def test_resolve_template_unresolved(self, context):
        """Test que falla con template no resuelto."""
        node = DerivePlanNode({}, context)
        
        with pytest.raises(ValueError, match="could not be resolved"):
            node._resolve_template("{{plan.id}}")
    
    @pytest.mark.asyncio
    async def test_resolve_template_no_template(self, context):
        """Test que retorna valor sin template."""
        node = DerivePlanNode({}, context)
        
        result = node._resolve_template("plain_string")
        assert result == "plain_string"
        
        result = node._resolve_template(None)
        assert result is None
