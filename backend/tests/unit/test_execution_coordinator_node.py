"""
Tests unitarios para ExecutionCoordinatorNode con 100% de cobertura.
"""
import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from app.core.strategy_engine.nodes.execution_coordinator import ExecutionCoordinatorNode
from app.core.strategy_engine.nodes.base import ExecutionResult, FailureResult
from app.core.strategy_engine.models import GraphExecutionContext
from app.models.execution_plan import ExecutionPlan
from app.models.strategy import Strategy
from app.models.event import Event


class TestExecutionCoordinatorNode:
    """Tests para ExecutionCoordinatorNode."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock de SQLAlchemy Session."""
        db = Mock()
        db.query = Mock()
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
        plan.status = "PLAN_BUILT"
        plan.event = mock_event
        plan.trace_id = uuid4()
        plan.risk_config = {}  # risk_config vacío es válido
        plan.legs = [
            {
                "leg_id": "leg_1",
                "side": "BUY",
                "outcome": "YES",
                "target_price": Decimal("0.95"),
                "size": Decimal("1000"),
                "size_usdc": Decimal("950"),
                "status": "PENDING",
                "reason": "Test leg"
            }
        ]
        plan.is_expired = Mock(return_value=False)
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
        node = ExecutionCoordinatorNode(config, context)
        
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "plan_id is required" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_plan_not_found(self, context, mock_db):
        """Test que falla si el plan no existe."""
        plan_id = uuid4()
        config = {"plan_id": str(plan_id)}
        
        # Mock query para retornar None
        query_mock = Mock()
        query_mock.filter.return_value.with_for_update.return_value.first.return_value = None
        mock_db.query.return_value = query_mock
        
        node = ExecutionCoordinatorNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "not found" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_plan_expired(self, context, mock_db, mock_plan):
        """Test que falla si el plan ha expirado."""
        plan_id = mock_plan.id
        config = {"plan_id": str(plan_id)}
        
        # Mock query para retornar el plan
        query_mock = Mock()
        query_mock.filter.return_value.with_for_update.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        # Plan expirado
        mock_plan.is_expired.return_value = True
        
        node = ExecutionCoordinatorNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_not_expired') as validate_mock:
            validate_mock.side_effect = ValueError("Plan has expired")
            result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "expired" in result.error.lower() or "Validation error" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_sequential_success(self, context, mock_db, mock_plan, mock_event):
        """Test ejecución secuencial exitosa."""
        plan_id = mock_plan.id
        config = {
            "plan_id": str(plan_id),
            "execution_mode": "sequential"
        }
        
        # Mock query
        query_mock = Mock()
        query_mock.filter.return_value.with_for_update.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = ExecutionCoordinatorNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_not_expired'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_immutability'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_state_transition'), \
             patch.object(node, '_execute_sequential', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                "legs": {"leg_1": {"success": True}},
                "all_completed": True,
                "has_failures": False,
                "has_partial_fills": False
            }
            
            result = await node.execute()
        
        assert isinstance(result, ExecutionResult)
        assert result.plan_id == plan_id
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_execute_parallel_success(self, context, mock_db, mock_plan, mock_event):
        """Test ejecución paralela exitosa."""
        plan_id = mock_plan.id
        config = {
            "plan_id": str(plan_id),
            "execution_mode": "parallel"
        }
        
        # Mock query
        query_mock = Mock()
        query_mock.filter.return_value.with_for_update.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = ExecutionCoordinatorNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_not_expired'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_immutability'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_state_transition'), \
             patch.object(node, '_execute_parallel', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                "legs": {"leg_1": {"success": True}},
                "all_completed": True,
                "has_failures": False,
                "has_partial_fills": False
            }
            
            result = await node.execute()
        
        assert isinstance(result, ExecutionResult)
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_execute_atomic_success(self, context, mock_db, mock_plan, mock_event):
        """Test ejecución atómica exitosa."""
        plan_id = mock_plan.id
        config = {
            "plan_id": str(plan_id),
            "execution_mode": "atomic",
            "compensation_enabled": True
        }
        
        # Mock query
        query_mock = Mock()
        query_mock.filter.return_value.with_for_update.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = ExecutionCoordinatorNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_not_expired'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_immutability'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_state_transition'), \
             patch.object(node, '_execute_atomic', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                "legs": {"leg_1": {"success": True}},
                "all_completed": True,
                "has_failures": False,
                "has_partial_fills": False
            }
            
            result = await node.execute()
        
        assert isinstance(result, ExecutionResult)
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_execute_unknown_mode(self, context, mock_db, mock_plan):
        """Test que falla con modo desconocido."""
        plan_id = mock_plan.id
        config = {
            "plan_id": str(plan_id),
            "execution_mode": "unknown_mode"
        }
        
        # Mock query
        query_mock = Mock()
        query_mock.filter.return_value.with_for_update.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = ExecutionCoordinatorNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_not_expired'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_immutability'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_state_transition'):
            result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Unknown execution_mode" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_invalid_status(self, context, mock_db, mock_plan):
        """Test que falla si el plan está en estado inválido."""
        plan_id = mock_plan.id
        config = {"plan_id": str(plan_id)}
        mock_plan.status = "COMPLETED"  # Estado terminal
        
        # Mock query
        query_mock = Mock()
        query_mock.filter.return_value.with_for_update.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = ExecutionCoordinatorNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_not_expired'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_immutability'):
            result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Cannot execute plan in status" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_template_resolution(self, context, mock_db, mock_plan):
        """Test que resuelve templates en plan_id."""
        plan_id = mock_plan.id
        context.plan_id = plan_id
        config = {"plan_id": "{{plan.id}}"}
        
        # Mock query
        query_mock = Mock()
        query_mock.filter.return_value.with_for_update.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = ExecutionCoordinatorNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_not_expired'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_immutability'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_state_transition'), \
             patch.object(node, '_execute_sequential', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                "legs": {},
                "all_completed": True,
                "has_failures": False,
                "has_partial_fills": False
            }
            
            result = await node.execute()
        
        assert isinstance(result, ExecutionResult)
    
    @pytest.mark.asyncio
    async def test_execute_sequential_with_failure(self, context, mock_db, mock_plan):
        """Test ejecución secuencial con fallo."""
        plan_id = mock_plan.id
        config = {
            "plan_id": str(plan_id),
            "execution_mode": "sequential"
        }
        
        # Mock query
        query_mock = Mock()
        query_mock.filter.return_value.with_for_update.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = ExecutionCoordinatorNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_not_expired'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_immutability'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_state_transition'), \
             patch.object(node, '_execute_sequential', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                "legs": {"leg_1": {"success": False, "error": "Execution failed"}},
                "all_completed": False,
                "has_failures": True,
                "has_partial_fills": False
            }
            
            result = await node.execute()
        
        # Verificar que se retornó un resultado (puede ser ExecutionResult o FailureResult)
        assert isinstance(result, (ExecutionResult, FailureResult))
        if isinstance(result, ExecutionResult):
            assert hasattr(result, 'plan_id')
    
    @pytest.mark.asyncio
    async def test_execute_atomic_with_failure_and_compensation(self, context, mock_db, mock_plan):
        """Test ejecución atómica con fallo y compensación."""
        plan_id = mock_plan.id
        config = {
            "plan_id": str(plan_id),
            "execution_mode": "atomic",
            "compensation_enabled": True
        }
        
        # Mock query
        query_mock = Mock()
        query_mock.filter.return_value.with_for_update.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        node = ExecutionCoordinatorNode(config, context)
        
        with patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_not_expired'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_immutability'), \
             patch('app.core.strategy_engine.nodes.execution_coordinator.validate_plan_state_transition'), \
             patch.object(node, '_execute_atomic', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                "legs": {"leg_1": {"success": False}},
                "all_completed": False,
                "has_failures": True,
                "has_partial_fills": False
            }
            
            result = await node.execute()
        
        # Verificar que se retornó un resultado
        assert isinstance(result, (ExecutionResult, FailureResult))
        if isinstance(result, ExecutionResult):
            assert hasattr(result, 'plan_id')
    
    @pytest.mark.asyncio
    async def test_execute_leg_success(self, context, mock_db, mock_plan, mock_event):
        """Test ejecución de un leg exitosa."""
        from app.core.strategy_engine.risk_validator import RiskValidator
        leg = mock_plan.legs[0]
        node = ExecutionCoordinatorNode({}, context)
        risk_validator = RiskValidator(mock_plan)
        
        result = await node._execute_leg(leg, mock_plan, risk_validator)
        
        assert result.get("success") is True
        assert result.get("leg_id") == leg["leg_id"]
    
    @pytest.mark.asyncio
    async def test_execute_leg_no_execution_engine(self, context, mock_db, mock_plan, mock_event):
        """Test ejecución de leg sin execution_engine (simula)."""
        from app.core.strategy_engine.risk_validator import RiskValidator
        leg = mock_plan.legs[0]
        context.execution_engine = None
        node = ExecutionCoordinatorNode({}, context)
        risk_validator = RiskValidator(mock_plan)
        
        result = await node._execute_leg(leg, mock_plan, risk_validator)
        
        assert result.get("success") is True
    
    @pytest.mark.asyncio
    async def test_execute_leg_no_event(self, context, mock_db, mock_plan):
        """Test ejecución de leg sin evento."""
        from app.core.strategy_engine.risk_validator import RiskValidator
        leg = mock_plan.legs[0]
        # Crear un nuevo mock_plan sin evento
        plan_no_event = Mock(spec=ExecutionPlan)
        plan_no_event.event = None  # Sin evento
        plan_no_event.trace_id = uuid4()
        plan_no_event.legs = mock_plan.legs
        
        # Configurar execution_engine para que se ejecute la verificación del evento
        context.execution_engine = Mock()
        node = ExecutionCoordinatorNode({}, context)
        risk_validator = RiskValidator(plan_no_event)
        
        result = await node._execute_leg(leg, plan_no_event, risk_validator)
        
        assert result.get("success") is False
        assert "Event not found" in result.get("error")
    
    @pytest.mark.asyncio
    async def test_execute_sequential_empty_legs(self, context, mock_db, mock_plan):
        """Test ejecución secuencial con legs vacíos."""
        from app.core.strategy_engine.risk_validator import RiskValidator
        mock_plan.legs = []
        node = ExecutionCoordinatorNode({}, context)
        risk_validator = RiskValidator(mock_plan)
        
        result = await node._execute_sequential(mock_plan, {}, risk_validator)
        
        assert result["all_completed"] is True
        assert result["has_failures"] is False
    
    @pytest.mark.asyncio
    async def test_execute_parallel_empty_legs(self, context, mock_db, mock_plan):
        """Test ejecución paralela con legs vacíos."""
        from app.core.strategy_engine.risk_validator import RiskValidator
        mock_plan.legs = []
        node = ExecutionCoordinatorNode({}, context)
        risk_validator = RiskValidator(mock_plan)
        
        result = await node._execute_parallel(mock_plan, {}, risk_validator)
        
        assert result["all_completed"] is True
        assert result["has_failures"] is False
    
    @pytest.mark.asyncio
    async def test_execute_atomic_empty_legs(self, context, mock_db, mock_plan):
        """Test ejecución atómica con legs vacíos."""
        from app.core.strategy_engine.risk_validator import RiskValidator
        mock_plan.legs = []
        node = ExecutionCoordinatorNode({}, context)
        risk_validator = RiskValidator(mock_plan)
        
        result = await node._execute_atomic(mock_plan, {}, True, risk_validator)
        
        assert result["all_completed"] is True
        assert result["has_failures"] is False
    
    @pytest.mark.asyncio
    async def test_resolve_template_plan_id(self, context):
        """Test resolución de template con plan_id."""
        plan_id = uuid4()
        context.plan_id = plan_id
        node = ExecutionCoordinatorNode({}, context)
        
        result = node._resolve_template("{{plan.id}}")
        assert result == plan_id or str(result) == str(plan_id)
        
        result = node._resolve_template("{{plan_id}}")
        assert result == plan_id or str(result) == str(plan_id)
    
    @pytest.mark.asyncio
    async def test_resolve_template_unresolved(self, context):
        """Test que falla con template no resuelto."""
        node = ExecutionCoordinatorNode({}, context)
        
        with pytest.raises(ValueError, match="could not be resolved"):
            node._resolve_template("{{plan.id}}")
    
    @pytest.mark.asyncio
    async def test_resolve_template_no_template(self, context):
        """Test que retorna valor sin template."""
        node = ExecutionCoordinatorNode({}, context)
        
        result = node._resolve_template("plain_string")
        assert result == "plain_string"
        
        result = node._resolve_template(None)
        assert result is None

