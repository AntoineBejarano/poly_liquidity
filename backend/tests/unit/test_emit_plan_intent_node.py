"""
Tests unitarios para EmitPlanIntentNode con 100% de cobertura.
"""
import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from app.core.strategy_engine.nodes.emit_plan_intent import EmitPlanIntentNode
from app.core.strategy_engine.nodes.base import SuccessResult, FailureResult
from app.core.strategy_engine.models import GraphExecutionContext
from app.models.execution_plan import ExecutionPlan
from app.models.strategy import Strategy
from app.models.event import Event


class TestEmitPlanIntentNode:
    """Tests para EmitPlanIntentNode."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock de SQLAlchemy Session."""
        db = Mock()
        db.query = Mock()
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
        return context
    
    @pytest.fixture
    def mock_plan(self):
        """Mock de ExecutionPlan."""
        plan = Mock(spec=ExecutionPlan)
        plan.id = uuid4()
        plan.ready_for_execution = False
        plan.queued_at = None
        return plan
    
    @pytest.mark.asyncio
    async def test_emit_plan_intent_success(self, context, mock_plan, mock_db):
        """Test que emit_plan_intent marca plan como listo exitosamente."""
        plan_id = mock_plan.id
        
        # Configurar mock query
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        config = {
            "plan_id": str(plan_id)
        }
        
        node = EmitPlanIntentNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
        assert mock_plan.ready_for_execution is True
        assert mock_plan.queued_at is not None
        mock_db.flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_emit_plan_intent_with_uuid_string(self, context, mock_plan, mock_db):
        """Test que acepta plan_id como string UUID."""
        plan_id = mock_plan.id
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        config = {
            "plan_id": str(plan_id)
        }
        
        node = EmitPlanIntentNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
    
    @pytest.mark.asyncio
    async def test_emit_plan_intent_with_template_plan_id(self, context, mock_plan, mock_db):
        """Test que resuelve template {{plan.id}}."""
        plan_id = mock_plan.id
        context.last_plan_id = plan_id
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        config = {
            "plan_id": "{{plan.id}}"
        }
        
        node = EmitPlanIntentNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
    
    @pytest.mark.asyncio
    async def test_emit_plan_intent_with_template_plan_id_alt(self, context, mock_plan, mock_db):
        """Test que resuelve template {{plan_id}}."""
        plan_id = mock_plan.id
        context.plan_id = plan_id
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        config = {
            "plan_id": "{{plan_id}}"
        }
        
        node = EmitPlanIntentNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
    
    @pytest.mark.asyncio
    async def test_emit_plan_intent_no_db(self, context):
        """Test que falla si no hay DB session."""
        context.db = None
        
        config = {
            "plan_id": str(uuid4())
        }
        
        node = EmitPlanIntentNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Database session required" in result.error
    
    @pytest.mark.asyncio
    async def test_emit_plan_intent_no_plan_id(self, context):
        """Test que falla si no hay plan_id."""
        config = {}
        
        node = EmitPlanIntentNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "plan_id is required" in result.error
    
    @pytest.mark.asyncio
    async def test_emit_plan_intent_plan_not_found(self, context, mock_db):
        """Test que falla si el plan no existe."""
        plan_id = uuid4()
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = None
        mock_db.query.return_value = query_mock
        
        config = {
            "plan_id": str(plan_id)
        }
        
        node = EmitPlanIntentNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "not found" in result.error
    
    @pytest.mark.asyncio
    async def test_emit_plan_intent_invalid_uuid(self, context):
        """Test que falla si plan_id no es un UUID válido."""
        config = {
            "plan_id": "invalid-uuid"
        }
        
        node = EmitPlanIntentNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Invalid plan_id format" in result.error
    
    @pytest.mark.asyncio
    async def test_emit_plan_intent_template_unresolved(self, context):
        """Test que falla si template no se puede resolver."""
        config = {
            "plan_id": "{{plan.id}}"
        }
        # No hay last_plan_id ni plan_id en context
        
        node = EmitPlanIntentNode(config, context)
        # _resolve_template lanza ValueError, pero execute lo captura y retorna FailureResult
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "could not be resolved" in result.error or "plan_id could not be resolved" in result.error
    
    @pytest.mark.asyncio
    async def test_emit_plan_intent_db_error(self, context, mock_plan, mock_db):
        """Test que maneja errores de DB correctamente."""
        plan_id = mock_plan.id
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        mock_db.flush.side_effect = Exception("DB Error")
        
        config = {
            "plan_id": str(plan_id)
        }
        
        node = EmitPlanIntentNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "Error updating plan" in result.error
    
    @pytest.mark.asyncio
    async def test_emit_plan_intent_from_context_last_plan_id(self, context, mock_plan, mock_db):
        """Test que obtiene plan_id del contexto si no está en config."""
        plan_id = mock_plan.id
        context.last_plan_id = plan_id
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_plan
        mock_db.query.return_value = query_mock
        
        config = {}  # Sin plan_id
        
        node = EmitPlanIntentNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
    
    def test_resolve_template_simple(self, context):
        """Test método _resolve_template con template simple."""
        plan_id = uuid4()
        context.last_plan_id = plan_id
        
        node = EmitPlanIntentNode({}, context)
        
        # Template {{plan.id}}
        result = node._resolve_template("{{plan.id}}")
        assert result == plan_id or str(result) == str(plan_id)
        
        # Template {{plan_id}}
        result = node._resolve_template("{{plan_id}}")
        assert result == plan_id or str(result) == str(plan_id)
        
        # Sin template
        result = node._resolve_template(str(plan_id))
        assert result == str(plan_id)
        
        # None
        result = node._resolve_template(None)
        assert result is None
    
    def test_resolve_template_unresolved(self, context):
        """Test método _resolve_template con template no resuelto."""
        node = EmitPlanIntentNode({}, context)
        # No hay last_plan_id ni plan_id en context
        
        with pytest.raises(ValueError, match="could not be resolved"):
            node._resolve_template("{{plan.id}}")
    
    def test_resolve_template_partial(self, context):
        """Test método _resolve_template con template parcial."""
        plan_id = uuid4()
        context.last_plan_id = plan_id
        
        node = EmitPlanIntentNode({}, context)
        
        # Template parcial
        result = node._resolve_template("Plan: {{plan.id}}")
        assert result == f"Plan: {plan_id}"
    
    def test_resolve_template_returns_none(self, context):
        """Test que _resolve_template puede retornar None."""
        node = EmitPlanIntentNode({}, context)
        
        # None debe retornar None
        result = node._resolve_template(None)
        assert result is None
    
    def test_resolve_template_unresolved_after_replacement(self, context):
        """Test que _resolve_template lanza error si quedan templates sin resolver (línea 120)."""
        plan_id = uuid4()
        context.last_plan_id = plan_id
        node = EmitPlanIntentNode({}, context)
        
        # Template que tiene {{plan.id}} que se resuelve pero queda {{unknown}} sin resolver
        # El código resuelve {{plan.id}} a plan_id, pero luego detecta que quedan {{unknown}}
        # Esto debería lanzar ValueError en la línea 120
        with pytest.raises(ValueError, match="Unresolved template"):
            node._resolve_template("{{plan.id}} and {{unknown}}")
    
    @pytest.mark.asyncio
    async def test_emit_plan_intent_plan_id_none_after_resolve(self, context):
        """Test que execute retorna FailureResult si plan_id es None después de resolver (línea 58)."""
        # Simular que _resolve_template retorna None (no plan_id en contexto)
        context.last_plan_id = None
        context.plan_id = None
        
        config = {
            "plan_id": "{{plan.id}}"  # Template que no se puede resolver
        }
        
        node = EmitPlanIntentNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "could not be resolved" in result.error
    
    def test_resolve_template_complete_template_returns_plan_id(self, context):
        """Test que _resolve_template retorna plan_id directamente si el template es completo (línea 114)."""
        plan_id = uuid4()
        context.last_plan_id = plan_id
        
        node = EmitPlanIntentNode({}, context)
        
        # Template completo {{plan.id}} debe retornar plan_id directamente
        result = node._resolve_template("{{plan.id}}")
        assert result == plan_id or str(result) == str(plan_id)
        
        # Template completo {{plan_id}} también debe retornar plan_id directamente
        result = node._resolve_template("{{plan_id}}")
        assert result == plan_id or str(result) == str(plan_id)
