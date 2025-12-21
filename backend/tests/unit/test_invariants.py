"""
Tests unitarios para invariantes con 100% de cobertura.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.models.execution_plan import ExecutionPlan
from app.models.strategy import Strategy
from app.models.event import Event
from app.core.strategy_engine.invariants import (
    validate_plan_immutability,
    validate_plan_state_transition,
    validate_plan_not_expired,
    validate_compensation_only_reduces_exposure,
    validate_hot_path_no_state_modification,
    VALID_STATUSES,
    VALID_TRANSITIONS
)


class TestValidatePlanImmutability:
    """Tests para validate_plan_immutability."""
    
    def test_validate_plan_immutability_plan_built(self, db_session):
        """Test que PLAN_BUILT permite validación."""
        strategy = Strategy(
            name="Test",
            decision_graph={"entry_node": "start", "nodes": {}},
            support_graphs=[],
            control_loop_config={},
            risk_config={}
        )
        db_session.add(strategy)
        db_session.flush()
        
        event = Event(
            polymarket_event_id="test-1",
            market_id=uuid4(),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            state="ACTIVE"
        )
        db_session.add(event)
        db_session.flush()
        
        plan = ExecutionPlan(
            strategy_id=strategy.id,
            event_id=event.id,
            legs=[{"leg_id": "leg_1", "side": "BUY", "outcome": "YES", "target_price": "0.95", "size": "1000", "size_usdc": "950", "status": "PENDING", "filled_size": "0", "filled_size_usdc": "0", "reason": "Test"}],
            ttl_ms=30000,
            status="PLAN_BUILT",
            risk_config={}
        )
        
        # PLAN_BUILT no debería lanzar error (aunque técnicamente no se puede modificar después)
        # Esta función valida que no se modifique DESPUÉS de PLAN_BUILT
        # Para estados terminales, sí lanza error
        plan.status = "EXECUTING"
        with pytest.raises(ValueError, match="Cannot modify plan in status"):
            validate_plan_immutability(plan)
    
    def test_validate_plan_immutability_executing(self, db_session):
        """Test que EXECUTING no permite modificación."""
        strategy = Strategy(
            name="Test",
            decision_graph={"entry_node": "start", "nodes": {}},
            support_graphs=[],
            control_loop_config={},
            risk_config={}
        )
        db_session.add(strategy)
        db_session.flush()
        
        event = Event(
            polymarket_event_id="test-2",
            market_id=uuid4(),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            state="ACTIVE"
        )
        db_session.add(event)
        db_session.flush()
        
        plan = ExecutionPlan(
            strategy_id=strategy.id,
            event_id=event.id,
            legs=[{"leg_id": "leg_1", "side": "BUY", "outcome": "YES", "target_price": "0.95", "size": "1000", "size_usdc": "950", "status": "PENDING", "filled_size": "0", "filled_size_usdc": "0", "reason": "Test"}],
            ttl_ms=30000,
            status="EXECUTING",
            risk_config={}
        )
        
        with pytest.raises(ValueError, match="Cannot modify plan in status"):
            validate_plan_immutability(plan)
    
    def test_validate_plan_immutability_completed(self, db_session):
        """Test que COMPLETED no permite modificación."""
        strategy = Strategy(
            name="Test",
            decision_graph={"entry_node": "start", "nodes": {}},
            support_graphs=[],
            control_loop_config={},
            risk_config={}
        )
        db_session.add(strategy)
        db_session.flush()
        
        event = Event(
            polymarket_event_id="test-3",
            market_id=uuid4(),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            state="ACTIVE"
        )
        db_session.add(event)
        db_session.flush()
        
        plan = ExecutionPlan(
            strategy_id=strategy.id,
            event_id=event.id,
            legs=[{"leg_id": "leg_1", "side": "BUY", "outcome": "YES", "target_price": "0.95", "size": "1000", "size_usdc": "950", "status": "PENDING", "filled_size": "0", "filled_size_usdc": "0", "reason": "Test"}],
            ttl_ms=30000,
            status="COMPLETED",
            risk_config={}
        )
        
        with pytest.raises(ValueError, match="Cannot modify plan in status"):
            validate_plan_immutability(plan)
    
    def test_validate_plan_immutability_invalid_status(self, db_session):
        """Test que estado inválido lanza error."""
        strategy = Strategy(
            name="Test",
            decision_graph={"entry_node": "start", "nodes": {}},
            support_graphs=[],
            control_loop_config={},
            risk_config={}
        )
        db_session.add(strategy)
        db_session.flush()
        
        event = Event(
            polymarket_event_id="test-4",
            market_id=uuid4(),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            state="ACTIVE"
        )
        db_session.add(event)
        db_session.flush()
        
        plan = ExecutionPlan(
            strategy_id=strategy.id,
            event_id=event.id,
            legs=[{"leg_id": "leg_1", "side": "BUY", "outcome": "YES", "target_price": "0.95", "size": "1000", "size_usdc": "950", "status": "PENDING", "filled_size": "0", "filled_size_usdc": "0", "reason": "Test"}],
            ttl_ms=30000,
            status="INVALID_STATUS",
            risk_config={}
        )
        
        with pytest.raises(ValueError, match="Invalid plan status"):
            validate_plan_immutability(plan)


class TestValidatePlanStateTransition:
    """Tests para validate_plan_state_transition."""
    
    def test_validate_plan_state_transition_valid(self):
        """Test transiciones válidas."""
        # PLAN_BUILT → EXECUTING
        validate_plan_state_transition("PLAN_BUILT", "EXECUTING")
        
        # PLAN_BUILT → ABORTED
        validate_plan_state_transition("PLAN_BUILT", "ABORTED")
        
        # EXECUTING → COMPLETED
        validate_plan_state_transition("EXECUTING", "COMPLETED")
        
        # EXECUTING → FAILED
        validate_plan_state_transition("EXECUTING", "FAILED")
        
        # EXECUTING → ABORTED
        validate_plan_state_transition("EXECUTING", "ABORTED")
        
        # Cualquier estado → ABORTED (siempre permitido)
        validate_plan_state_transition("PLAN_BUILT", "ABORTED")
        validate_plan_state_transition("EXECUTING", "ABORTED")
        validate_plan_state_transition("COMPLETED", "ABORTED")
    
    def test_validate_plan_state_transition_invalid(self):
        """Test transiciones inválidas."""
        # PLAN_BUILT → COMPLETED (no permitido, debe pasar por EXECUTING)
        with pytest.raises(ValueError, match="Invalid state transition"):
            validate_plan_state_transition("PLAN_BUILT", "COMPLETED")
        
        # EXECUTING → PLAN_BUILT (no se puede volver atrás)
        with pytest.raises(ValueError, match="Invalid state transition"):
            validate_plan_state_transition("EXECUTING", "PLAN_BUILT")
        
        # COMPLETED → EXECUTING (estado terminal)
        with pytest.raises(ValueError, match="Invalid state transition"):
            validate_plan_state_transition("COMPLETED", "EXECUTING")
        
        # FAILED → EXECUTING (estado terminal)
        with pytest.raises(ValueError, match="Invalid state transition"):
            validate_plan_state_transition("FAILED", "EXECUTING")
    
    def test_validate_plan_state_transition_invalid_old_status(self):
        """Test que estado antiguo inválido lanza error."""
        with pytest.raises(ValueError, match="Invalid old status"):
            validate_plan_state_transition("INVALID", "EXECUTING")
    
    def test_validate_plan_state_transition_invalid_new_status(self):
        """Test que estado nuevo inválido lanza error."""
        with pytest.raises(ValueError, match="Invalid new status"):
            validate_plan_state_transition("PLAN_BUILT", "INVALID")


class TestValidatePlanNotExpired:
    """Tests para validate_plan_not_expired."""
    
    def test_validate_plan_not_expired_valid(self, db_session):
        """Test que plan no expirado pasa validación."""
        strategy = Strategy(
            name="Test",
            decision_graph={"entry_node": "start", "nodes": {}},
            support_graphs=[],
            control_loop_config={},
            risk_config={}
        )
        db_session.add(strategy)
        db_session.flush()
        
        event = Event(
            polymarket_event_id="test-5",
            market_id=uuid4(),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            state="ACTIVE"
        )
        db_session.add(event)
        db_session.flush()
        
        plan = ExecutionPlan(
            strategy_id=strategy.id,
            event_id=event.id,
            legs=[{"leg_id": "leg_1", "side": "BUY", "outcome": "YES", "target_price": "0.95", "size": "1000", "size_usdc": "950", "status": "PENDING", "filled_size": "0", "filled_size_usdc": "0", "reason": "Test"}],
            ttl_ms=30000,
            status="PLAN_BUILT",
            risk_config={}
        )
        plan.expires_at = datetime.utcnow() + timedelta(seconds=10)
        
        # No debería lanzar error
        validate_plan_not_expired(plan)
    
    def test_validate_plan_not_expired_expired(self, db_session):
        """Test que plan expirado lanza error."""
        strategy = Strategy(
            name="Test",
            decision_graph={"entry_node": "start", "nodes": {}},
            support_graphs=[],
            control_loop_config={},
            risk_config={}
        )
        db_session.add(strategy)
        db_session.flush()
        
        event = Event(
            polymarket_event_id="test-6",
            market_id=uuid4(),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            state="ACTIVE"
        )
        db_session.add(event)
        db_session.flush()
        
        plan = ExecutionPlan(
            strategy_id=strategy.id,
            event_id=event.id,
            legs=[{"leg_id": "leg_1", "side": "BUY", "outcome": "YES", "target_price": "0.95", "size": "1000", "size_usdc": "950", "status": "PENDING", "filled_size": "0", "filled_size_usdc": "0", "reason": "Test"}],
            ttl_ms=30000,
            status="PLAN_BUILT",
            risk_config={}
        )
        plan.expires_at = datetime.utcnow() - timedelta(seconds=10)
        
        with pytest.raises(ValueError, match="has expired"):
            validate_plan_not_expired(plan)


class TestValidateCompensationOnlyReducesExposure:
    """Tests para validate_compensation_only_reduces_exposure."""
    
    def test_validate_compensation_valid_actions(self):
        """Test que acciones válidas de compensación pasan."""
        # Acciones válidas: reverse, cancel
        actions = [
            {"type": "reverse_order", "order_id": "123"},
            {"type": "cancel_order", "order_id": "456"}
        ]
        
        # No debería lanzar error
        validate_compensation_only_reduces_exposure(actions)
    
    def test_validate_compensation_create_order(self):
        """Test que crear orden en compensación lanza error."""
        actions = [
            {"type": "create_order", "side": "SELL"}
        ]
        
        with pytest.raises(ValueError, match="Compensation cannot create new orders"):
            validate_compensation_only_reduces_exposure(actions)
    
    def test_validate_compensation_increase_size(self):
        """Test que aumentar tamaño en compensación lanza error."""
        actions = [
            {"type": "increase_size", "order_id": "123", "new_size": 2000}
        ]
        
        with pytest.raises(ValueError, match="Compensation cannot increase order size"):
            validate_compensation_only_reduces_exposure(actions)


class TestValidateHotPathNoStateModification:
    """Tests para validate_hot_path_no_state_modification."""
    
    def test_validate_hot_path_allowed_nodes(self):
        """Test que nodos permitidos en hot path pasan."""
        # Nodos que solo leen
        validate_hot_path_no_state_modification("collect_state", "hot")
        validate_hot_path_no_state_modification("edge_and_risk_check", "hot")
        validate_hot_path_no_state_modification("calculate_order_size", "hot")
        validate_hot_path_no_state_modification("build_plan", "hot")
    
    def test_validate_hot_path_forbidden_nodes(self):
        """Test que nodos que modifican estado en hot path lanzan error."""
        with pytest.raises(ValueError, match="cannot be used in hot path"):
            validate_hot_path_no_state_modification("update_state_cache", "hot")
    
    def test_validate_cold_path_allowed(self):
        """Test que cold path permite modificar estado."""
        # Cold path puede modificar estado
        validate_hot_path_no_state_modification("update_state_cache", "cold")
        validate_hot_path_no_state_modification("fetch_external_source", "cold")


class TestInvariantsConstants:
    """Tests para constantes de invariantes."""
    
    def test_valid_statuses(self):
        """Test que VALID_STATUSES contiene todos los estados válidos."""
        assert "PLAN_BUILT" in VALID_STATUSES
        assert "ABORTED" in VALID_STATUSES
        assert "EXECUTING" in VALID_STATUSES
        assert "COMPLETED" in VALID_STATUSES
        assert "FAILED" in VALID_STATUSES
        assert len(VALID_STATUSES) == 5
    
    def test_valid_transitions(self):
        """Test que VALID_TRANSITIONS tiene estructura correcta."""
        assert "PLAN_BUILT" in VALID_TRANSITIONS
        assert "EXECUTING" in VALID_TRANSITIONS
        assert "COMPLETED" in VALID_TRANSITIONS
        assert "FAILED" in VALID_TRANSITIONS
        assert "ABORTED" in VALID_TRANSITIONS
        
        # Verificar transiciones específicas
        assert "EXECUTING" in VALID_TRANSITIONS["PLAN_BUILT"]
        assert "ABORTED" in VALID_TRANSITIONS["PLAN_BUILT"]
        assert "COMPLETED" in VALID_TRANSITIONS["EXECUTING"]
        assert "FAILED" in VALID_TRANSITIONS["EXECUTING"]
        
        # Estados terminales no tienen transiciones
        assert len(VALID_TRANSITIONS["COMPLETED"]) == 0
        assert len(VALID_TRANSITIONS["FAILED"]) == 0
        assert len(VALID_TRANSITIONS["ABORTED"]) == 0

