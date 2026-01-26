"""
Tests unitarios para ExecutionPlan model con 100% de cobertura.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import Table, Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.models.execution_plan import ExecutionPlan
from app.models.strategy import Strategy
from app.models.event import Event
from app.core.strategy_engine.models import PlanLeg
from app.database import Base


class TestExecutionPlan:
    """Tests para el modelo ExecutionPlan."""
    
    def test_execution_plan_creation_minimal(self, db_session):
        """Test que ExecutionPlan se puede crear con campos mínimos."""
        # Crear Strategy y Event necesarios
        strategy = Strategy(
            name="Test Strategy",
            decision_graph={"entry_node": "start", "nodes": {}},
            support_graphs=[],
            control_loop_config={},
            risk_config={}
        )
        db_session.add(strategy)
        db_session.flush()
        
        event = Event(
            polymarket_event_id="test-event-1",
            market_id=uuid4(),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            state="ACTIVE"
        )
        db_session.add(event)
        db_session.flush()
        
        # Crear ExecutionPlan
        legs = [
            {
                "leg_id": "leg_1",
                "side": "BUY",
                "outcome": "YES",
                "target_price": "0.95",
                "size": "1000",
                "size_usdc": "950",
                "status": "PENDING",
                "filled_size": "0",
                "filled_size_usdc": "0",
                "reason": "Test leg"
            }
        ]
        
        plan = ExecutionPlan(
            strategy_id=strategy.id,
            event_id=event.id,
            legs=legs,
            ttl_ms=30000,
            status="PLAN_BUILT",
            risk_config={}
        )
        
        db_session.add(plan)
        db_session.commit()
        
        assert plan.strategy_id == strategy.id
        assert plan.event_id == event.id
        assert plan.legs == legs
        assert plan.ttl_ms == 30000
        assert plan.status == "PLAN_BUILT"
        assert plan.ready_for_execution is False
        assert plan.queued_at is None
        assert plan.expires_at is not None  # Se calcula automáticamente
    
    def test_execution_plan_with_all_fields(self, db_session):
        """Test que ExecutionPlan se puede crear con todos los campos."""
        strategy = Strategy(
            name="Full Strategy",
            decision_graph={"entry_node": "start", "nodes": {}},
            support_graphs=[],
            control_loop_config={},
            risk_config={}
        )
        db_session.add(strategy)
        db_session.flush()
        
        event = Event(
            polymarket_event_id="test-event-2",
            market_id=uuid4(),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            state="ACTIVE"
        )
        db_session.add(event)
        db_session.flush()
        
        trace_id = uuid4()
        legs = [
            {
                "leg_id": "leg_1",
                "side": "BUY",
                "outcome": "YES",
                "target_price": "0.95",
                "size": "1000",
                "size_usdc": "950",
                "status": "PENDING",
                "filled_size": "0",
                "filled_size_usdc": "0",
                "reason": "Test leg 1"
            },
            {
                "leg_id": "leg_2",
                "side": "BUY",
                "outcome": "NO",
                "target_price": "0.05",
                "size": "1000",
                "size_usdc": "50",
                "status": "PENDING",
                "filled_size": "0",
                "filled_size_usdc": "0",
                "reason": "Test leg 2"
            }
        ]
        
        risk_config = {
            "max_slippage": 0.01,
            "max_fill_delay_ms": 5000,
            "max_partial_fill_ratio": 0.2
        }
        
        plan = ExecutionPlan(
            strategy_id=strategy.id,
            event_id=event.id,
            legs=legs,
            ttl_ms=60000,
            status="PLAN_BUILT",
            risk_config=risk_config,
            trace_id=trace_id,
            ready_for_execution=True,
            queued_at=datetime.utcnow()
        )
        
        db_session.add(plan)
        db_session.commit()
        
        assert plan.legs == legs
        assert len(plan.legs) == 2
        assert plan.risk_config == risk_config
        assert plan.trace_id == trace_id
        assert plan.ready_for_execution is True
        assert plan.queued_at is not None
    
    def test_execution_plan_expires_at_calculation(self, db_session):
        """Test que expires_at se calcula automáticamente."""
        strategy = Strategy(
            name="Test Strategy",
            decision_graph={"entry_node": "start", "nodes": {}},
            support_graphs=[],
            control_loop_config={},
            risk_config={}
        )
        db_session.add(strategy)
        db_session.flush()
        
        event = Event(
            polymarket_event_id="test-event-3",
            market_id=uuid4(),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            state="ACTIVE"
        )
        db_session.add(event)
        db_session.flush()
        
        legs = [{"leg_id": "leg_1", "side": "BUY", "outcome": "YES", "target_price": "0.95", "size": "1000", "size_usdc": "950", "status": "PENDING", "filled_size": "0", "filled_size_usdc": "0", "reason": "Test"}]
        
        plan = ExecutionPlan(
            strategy_id=strategy.id,
            event_id=event.id,
            legs=legs,
            ttl_ms=30000,  # 30 segundos
            status="PLAN_BUILT",
            risk_config={}
        )
        
        db_session.add(plan)
        db_session.flush()
        
        # expires_at debe calcularse automáticamente
        assert plan.expires_at is not None
        expected_expires = plan.created_at + timedelta(milliseconds=30000)
        # Permitir diferencia de hasta 1 segundo por timing
        assert abs((plan.expires_at - expected_expires).total_seconds()) < 1
    
    def test_execution_plan_is_expired(self, db_session):
        """Test método is_expired()."""
        strategy = Strategy(
            name="Test Strategy",
            decision_graph={"entry_node": "start", "nodes": {}},
            support_graphs=[],
            control_loop_config={},
            risk_config={}
        )
        db_session.add(strategy)
        db_session.flush()
        
        event = Event(
            polymarket_event_id="test-event-4",
            market_id=uuid4(),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            state="ACTIVE"
        )
        db_session.add(event)
        db_session.flush()
        
        legs = [{"leg_id": "leg_1", "side": "BUY", "outcome": "YES", "target_price": "0.95", "size": "1000", "size_usdc": "950", "status": "PENDING", "filled_size": "0", "filled_size_usdc": "0", "reason": "Test"}]
        
        # Plan no expirado
        plan = ExecutionPlan(
            strategy_id=strategy.id,
            event_id=event.id,
            legs=legs,
            ttl_ms=30000,
            status="PLAN_BUILT",
            risk_config={}
        )
        plan.expires_at = datetime.utcnow() + timedelta(seconds=10)
        assert plan.is_expired() is False
        
        # Plan expirado
        plan.expires_at = datetime.utcnow() - timedelta(seconds=10)
        assert plan.is_expired() is True
        
        # Plan sin expires_at
        plan.expires_at = None
        assert plan.is_expired() is False
    
    def test_execution_plan_get_remaining_ttl_ms(self, db_session):
        """Test método get_remaining_ttl_ms()."""
        strategy = Strategy(
            name="Test Strategy",
            decision_graph={"entry_node": "start", "nodes": {}},
            support_graphs=[],
            control_loop_config={},
            risk_config={}
        )
        db_session.add(strategy)
        db_session.flush()
        
        event = Event(
            polymarket_event_id="test-event-5",
            market_id=uuid4(),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            state="ACTIVE"
        )
        db_session.add(event)
        db_session.flush()
        
        legs = [{"leg_id": "leg_1", "side": "BUY", "outcome": "YES", "target_price": "0.95", "size": "1000", "size_usdc": "950", "status": "PENDING", "filled_size": "0", "filled_size_usdc": "0", "reason": "Test"}]
        
        plan = ExecutionPlan(
            strategy_id=strategy.id,
            event_id=event.id,
            legs=legs,
            ttl_ms=30000,
            status="PLAN_BUILT",
            risk_config={}
        )
        
        # Con expires_at futuro
        plan.expires_at = datetime.utcnow() + timedelta(milliseconds=10000)
        remaining = plan.get_remaining_ttl_ms()
        assert remaining > 0
        assert remaining <= 10000  # Debe ser aproximadamente 10000ms
        
        # Con expires_at pasado
        plan.expires_at = datetime.utcnow() - timedelta(milliseconds=1000)
        remaining = plan.get_remaining_ttl_ms()
        assert remaining == 0
        
        # Sin expires_at
        plan.expires_at = None
        remaining = plan.get_remaining_ttl_ms()
        assert remaining == 0
    
    def test_execution_plan_relationships(self, db_session):
        """Test que las relaciones funcionan correctamente."""
        strategy = Strategy(
            name="Test Strategy",
            decision_graph={"entry_node": "start", "nodes": {}},
            support_graphs=[],
            control_loop_config={},
            risk_config={}
        )
        db_session.add(strategy)
        db_session.flush()
        
        event = Event(
            polymarket_event_id="test-event-6",
            market_id=uuid4(),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            state="ACTIVE"
        )
        db_session.add(event)
        db_session.flush()
        
        legs = [{"leg_id": "leg_1", "side": "BUY", "outcome": "YES", "target_price": "0.95", "size": "1000", "size_usdc": "950", "status": "PENDING", "filled_size": "0", "filled_size_usdc": "0", "reason": "Test"}]
        
        plan = ExecutionPlan(
            strategy_id=strategy.id,
            event_id=event.id,
            legs=legs,
            ttl_ms=30000,
            status="PLAN_BUILT",
            risk_config={}
        )
        
        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)
        
        # Verificar relaciones
        assert plan.strategy.id == strategy.id
        assert plan.event.id == event.id
        assert plan in strategy.execution_plans


class TestPlanLeg:
    """Tests para el modelo PlanLeg (Pydantic)."""
    
    def test_plan_leg_creation(self):
        """Test que PlanLeg se puede crear con campos requeridos."""
        leg = PlanLeg(
            leg_id="leg_1",
            side="BUY",
            outcome="YES",
            target_price=Decimal("0.95"),
            size=Decimal("1000"),
            size_usdc=Decimal("950"),
            reason="Test leg"
        )
        
        assert leg.leg_id == "leg_1"
        assert leg.side == "BUY"
        assert leg.outcome == "YES"
        assert leg.target_price == Decimal("0.95")
        assert leg.size == Decimal("1000")
        assert leg.status == "PENDING"  # Default
        assert leg.filled_size == Decimal("0")  # Default
        assert leg.reason == "Test leg"
    
    def test_plan_leg_validation_side(self):
        """Test validación de side."""
        with pytest.raises(ValueError, match="side must be BUY or SELL"):
            PlanLeg(
                leg_id="leg_1",
                side="INVALID",
                outcome="YES",
                target_price=Decimal("0.95"),
                size=Decimal("1000"),
                size_usdc=Decimal("950"),
                reason="Test"
            )
    
    def test_plan_leg_validation_outcome(self):
        """Test validación de outcome."""
        with pytest.raises(ValueError, match="outcome must be YES, NO, UP, or DOWN"):
            PlanLeg(
                leg_id="leg_1",
                side="BUY",
                outcome="INVALID",
                target_price=Decimal("0.95"),
                size=Decimal("1000"),
                size_usdc=Decimal("950"),
                reason="Test"
            )
    
    def test_plan_leg_validation_status(self):
        """Test validación de status."""
        with pytest.raises(ValueError, match="status must be one of"):
            PlanLeg(
                leg_id="leg_1",
                side="BUY",
                outcome="YES",
                target_price=Decimal("0.95"),
                size=Decimal("1000"),
                size_usdc=Decimal("950"),
                status="INVALID",
                reason="Test"
            )
    
    def test_plan_leg_get_fill_ratio(self):
        """Test método get_fill_ratio()."""
        leg = PlanLeg(
            leg_id="leg_1",
            side="BUY",
            outcome="YES",
            target_price=Decimal("0.95"),
            size=Decimal("1000"),
            size_usdc=Decimal("950"),
            reason="Test"
        )
        
        # Sin fill
        assert leg.get_fill_ratio() == Decimal("0")
        
        # Partial fill
        leg.filled_size = Decimal("500")
        assert leg.get_fill_ratio() == Decimal("0.5")
        
        # Full fill
        leg.filled_size = Decimal("1000")
        assert leg.get_fill_ratio() == Decimal("1.0")
        
        # Size cero
        leg.size = Decimal("0")
        assert leg.get_fill_ratio() == Decimal("0")
    
    def test_plan_leg_is_complete(self):
        """Test método is_complete()."""
        leg = PlanLeg(
            leg_id="leg_1",
            side="BUY",
            outcome="YES",
            target_price=Decimal("0.95"),
            size=Decimal("1000"),
            size_usdc=Decimal("950"),
            reason="Test"
        )
        
        # No completo
        assert leg.is_complete() is False
        
        # Completo
        leg.status = "FILLED"
        leg.filled_size = Decimal("1000")
        assert leg.is_complete() is True
        
        # Más que completo (edge case)
        leg.filled_size = Decimal("1100")
        assert leg.is_complete() is True
    
    def test_plan_leg_is_partial(self):
        """Test método is_partial()."""
        leg = PlanLeg(
            leg_id="leg_1",
            side="BUY",
            outcome="YES",
            target_price=Decimal("0.95"),
            size=Decimal("1000"),
            size_usdc=Decimal("950"),
            reason="Test"
        )
        
        # No parcial
        assert leg.is_partial() is False
        
        # Parcial por status
        leg.status = "PARTIAL"
        assert leg.is_partial() is True
        
        # Parcial por filled_size
        leg.status = "PENDING"
        leg.filled_size = Decimal("500")
        assert leg.is_partial() is True
        
        # Completo (no parcial)
        leg.filled_size = Decimal("1000")
        assert leg.is_partial() is False

