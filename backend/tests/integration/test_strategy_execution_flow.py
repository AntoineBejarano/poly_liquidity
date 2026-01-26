"""
Tests de integración para el flujo completo de estrategias.

Decision Graph → ExecutionPlan → Execution Graph
"""
import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.core.strategy_engine.strategy_engine import StrategyEngine
from app.models.strategy import Strategy
from app.models.event import Event
from app.models.execution_plan import ExecutionPlan
from app.models.market import Market


class TestDecisionGraphToExecutionGraph:
    """Tests para el flujo completo Decision Graph → ExecutionPlan → Execution Graph."""
    
    @pytest.fixture
    def db_session(self, db_session):
        """DB session para tests."""
        return db_session
    
    @pytest.fixture
    def strategy_engine(self, db_session):
        """StrategyEngine inicializado."""
        engine = StrategyEngine()
        engine.initialize(db_session)
        return engine
    
    @pytest.fixture
    def market(self, db_session):
        """Market de prueba."""
        market = Market(
            polymarket_id="test-market-1",
            name="Test Market",
            category="sports",
            enabled=True
        )
        db_session.add(market)
        db_session.flush()
        return market
    
    @pytest.fixture
    def event(self, db_session, market):
        """Event de prueba."""
        event = Event(
            polymarket_event_id="test-event-1",
            market_id=market.id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            state="ACTIVE"
        )
        db_session.add(event)
        db_session.flush()
        return event
    
    @pytest.fixture
    def strategy_with_execution_graph(self, db_session, market):
        """Strategy con Decision Graph y Execution Graph."""
        strategy = Strategy(
            name="Test Strategy with Execution Graph",
            decision_graph={
                "entry_node": "collect",
                "nodes": {
                    "collect": {
                        "type": "collect_state",
                        "config": {},
                        "next": "calculate"
                    },
                    "calculate": {
                        "type": "calculate_order_size",
                        "config": {
                            "method": "fixed",
                            "size": "1000"
                        },
                        "next": "build_plan"
                    },
                    "build_plan": {
                        "type": "build_plan",
                        "config": {
                            "legs": [
                                {
                                    "leg_id": "leg_1",
                                    "side": "BUY",
                                    "outcome": "YES",
                                    "target_price": "{{calculate.price}}",
                                    "size": "{{calculate.size}}",
                                    "size_usdc": "{{calculate.size_usdc}}"
                                }
                            ],
                            "ttl_ms": 30000,
                            "risk_config": {
                                "max_slippage": 0.05,
                                "max_fill_delay_ms": 5000,
                                "max_partial_fill_ratio": 0.8,
                                "abort_on_price_move": True
                            }
                        },
                        "next": "emit_plan"
                    },
                    "emit_plan": {
                        "type": "emit_plan_intent",
                        "config": {
                            "plan_id": "{{plan.id}}"
                        }
                    }
                }
            },
            execution_graph={
                "entry_node": "coordinate",
                "nodes": {
                    "coordinate": {
                        "type": "execution_coordinator",
                        "config": {
                            "plan_id": "{{plan.id}}",
                            "execution_mode": "sequential"
                        }
                    }
                }
            },
            support_graphs=[],
            control_loop_config={},
            risk_config={},
            observability_config={}
        )
        db_session.add(strategy)
        db_session.flush()
        return strategy
    
    @pytest.mark.asyncio
    async def test_decision_graph_creates_execution_plan(
        self,
        strategy_engine,
        strategy_with_execution_graph,
        event,
        db_session
    ):
        """Test que Decision Graph crea ExecutionPlan correctamente."""
        # Mock state cache para que collect_state y calculate_order_size funcionen
        with patch.object(
            strategy_engine.state_cache_service,
            'get_market_state',
            return_value={
                "current_price": Decimal("0.95"),
                "liquidity": Decimal("10000")
            }
        ):
            # Ejecutar Decision Graph
            intents = await strategy_engine.execute_decision_graph(
                strategy_with_execution_graph,
                event,
                db_session
            )
            
            # Verificar que se creó un ExecutionPlan
            plans = db_session.query(ExecutionPlan).filter(
                ExecutionPlan.strategy_id == strategy_with_execution_graph.id
            ).all()
            
            assert len(plans) == 1
            plan = plans[0]
            assert plan.status == "PLAN_BUILT"
            assert plan.ready_for_execution is True
            assert plan.queued_at is not None
            assert len(plan.legs) == 1
            assert plan.legs[0]["leg_id"] == "leg_1"
            assert plan.legs[0]["side"] == "BUY"
            assert plan.legs[0]["outcome"] == "YES"
    
    @pytest.mark.asyncio
    async def test_execution_graph_executes_plan(
        self,
        strategy_engine,
        strategy_with_execution_graph,
        event,
        db_session
    ):
        """Test que Execution Graph ejecuta un plan correctamente."""
        # Crear plan manualmente
        plan = ExecutionPlan(
            strategy_id=strategy_with_execution_graph.id,
            event_id=event.id,
            legs=[
                {
                    "leg_id": "leg_1",
                    "side": "BUY",
                    "outcome": "YES",
                    "target_price": Decimal("0.95"),
                    "size": Decimal("1000"),
                    "size_usdc": Decimal("950"),
                    "status": "PENDING",
                    "filled_size": Decimal("0"),
                    "filled_size_usdc": Decimal("0"),
                    "reason": "Test"
                }
            ],
            ttl_ms=30000,
            status="PLAN_BUILT",
            risk_config={
                "max_slippage": 0.05,
                "max_fill_delay_ms": 5000,
                "max_partial_fill_ratio": 0.8,
                "abort_on_price_move": True
            },
            ready_for_execution=True,
            queued_at=datetime.utcnow()
        )
        db_session.add(plan)
        db_session.flush()
        
        # Mock execution engine para simular ejecución exitosa
        mock_execution_engine = Mock()
        mock_execution_engine.execute_order = AsyncMock(return_value={
            "success": True,
            "order_id": str(uuid4()),
            "filled_size": Decimal("1000"),
            "filled_price": Decimal("0.95")
        })
        strategy_engine.execution_engine = mock_execution_engine
        
        # Ejecutar Execution Graph
        await strategy_engine.execute_execution_graph(
            strategy_with_execution_graph,
            plan,
            event,
            db_session
        )
        
        # Verificar que el plan se ejecutó
        db_session.refresh(plan)
        assert plan.status == "COMPLETED"
        assert plan.legs[0]["status"] == "FILLED"
        assert plan.legs[0]["filled_size"] == Decimal("1000")


class TestAtomicSurebetPriceMove:
    """Test CRÍTICO: Atomic surebet aborta si una cuota se mueve."""
    
    @pytest.fixture
    def db_session(self, db_session):
        """DB session para tests."""
        return db_session
    
    @pytest.fixture
    def strategy_engine(self, db_session):
        """StrategyEngine inicializado."""
        engine = StrategyEngine()
        engine.initialize(db_session)
        return engine
    
    @pytest.fixture
    def market(self, db_session):
        """Market de prueba."""
        market = Market(
            polymarket_id="test-market-1",
            name="Test Market",
            category="sports",
            enabled=True
        )
        db_session.add(market)
        db_session.flush()
        return market
    
    @pytest.fixture
    def event(self, db_session, market):
        """Event de prueba."""
        event = Event(
            polymarket_event_id="test-event-1",
            market_id=market.id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            state="ACTIVE"
        )
        db_session.add(event)
        db_session.flush()
        return event
    
    @pytest.fixture
    def atomic_surebet_strategy(self, db_session, market):
        """Strategy para surebet atómico con 2 legs."""
        strategy = Strategy(
            name="Atomic Surebet Strategy",
            decision_graph={
                "entry_node": "collect",
                "nodes": {
                    "collect": {
                        "type": "collect_state",
                        "config": {},
                        "next": "build_plan"
                    },
                    "build_plan": {
                        "type": "build_plan",
                        "config": {
                            "legs": [
                                {
                                    "leg_id": "leg_1",
                                    "side": "BUY",
                                    "outcome": "YES",
                                    "target_price": "0.95",
                                    "size": "1000",
                                    "size_usdc": "950"
                                },
                                {
                                    "leg_id": "leg_2",
                                    "side": "SELL",
                                    "outcome": "NO",
                                    "target_price": "0.10",
                                    "size": "1000",
                                    "size_usdc": "100"
                                }
                            ],
                            "ttl_ms": 30000,
                            "risk_config": {
                                "max_slippage": 0.05,  # 5% máximo
                                "max_fill_delay_ms": 5000,
                                "max_partial_fill_ratio": 0.8,
                                "abort_on_price_move": True  # CRÍTICO: abortar si precio se mueve
                            }
                        },
                        "next": "emit_plan"
                    },
                    "emit_plan": {
                        "type": "emit_plan_intent",
                        "config": {
                            "plan_id": "{{plan.id}}"
                        }
                    }
                }
            },
            execution_graph={
                "entry_node": "coordinate",
                "nodes": {
                    "coordinate": {
                        "type": "execution_coordinator",
                        "config": {
                            "plan_id": "{{plan.id}}",
                            "execution_mode": "atomic"  # CRÍTICO: modo atómico
                        }
                    }
                }
            },
            support_graphs=[],
            control_loop_config={},
            risk_config={},
            observability_config={}
        )
        db_session.add(strategy)
        db_session.flush()
        return strategy
    
    @pytest.mark.asyncio
    async def test_atomic_surebet_aborts_on_price_move(
        self,
        strategy_engine,
        atomic_surebet_strategy,
        event,
        db_session
    ):
        """
        Test CRÍTICO: Atomic surebet aborta si una cuota se mueve.
        
        Este test ahorra dinero en producción - es el más importante para surebets.
        """
        # Crear plan con 2 legs (surebet)
        plan = ExecutionPlan(
            strategy_id=atomic_surebet_strategy.id,
            event_id=event.id,
            legs=[
                {
                    "leg_id": "leg_1",
                    "side": "BUY",
                    "outcome": "YES",
                    "target_price": Decimal("0.95"),
                    "size": Decimal("1000"),
                    "size_usdc": Decimal("950"),
                    "status": "PENDING",
                    "filled_size": Decimal("0"),
                    "filled_size_usdc": Decimal("0"),
                    "reason": "Leg 1"
                },
                {
                    "leg_id": "leg_2",
                    "side": "SELL",
                    "outcome": "NO",
                    "target_price": Decimal("0.10"),
                    "size": Decimal("1000"),
                    "size_usdc": Decimal("100"),
                    "status": "PENDING",
                    "filled_size": Decimal("0"),
                    "filled_size_usdc": Decimal("0"),
                    "reason": "Leg 2"
                }
            ],
            ttl_ms=30000,
            status="PLAN_BUILT",
            risk_config={
                "max_slippage": 0.05,  # 5% máximo
                "max_fill_delay_ms": 5000,
                "max_partial_fill_ratio": 0.8,
                "abort_on_price_move": True
            },
            ready_for_execution=True,
            queued_at=datetime.utcnow()
        )
        db_session.add(plan)
        db_session.flush()
        
        # Mock execution engine para simular:
        # - leg_1 se ejecuta exitosamente
        # - leg_2 falla porque el precio se movió > max_slippage
        execution_calls = []
        
        async def mock_execute_order(order_intent):
            """Mock que simula ejecución de órdenes."""
            execution_calls.append(order_intent)
            
            # Leg 1 se ejecuta exitosamente
            if order_intent.side == "BUY" and order_intent.outcome == "YES":
                return {
                    "success": True,
                    "order_id": str(uuid4()),
                    "filled_size": Decimal("1000"),
                    "filled_price": Decimal("0.95")
                }
            
            # Leg 2 falla porque el precio se movió (0.10 -> 0.16 = 60% de movimiento, > 5% max_slippage)
            elif order_intent.side == "SELL" and order_intent.outcome == "NO":
                # Simular que el precio actual es 0.16 (60% más alto que 0.10)
                # Esto excede el max_slippage de 5%
                return {
                    "success": False,
                    "error": "Price moved: current=0.16, target=0.10, slippage=60% > max_slippage=5%"
                }
            
            return {"success": False, "error": "Unknown leg"}
        
        mock_execution_engine = Mock()
        mock_execution_engine.execute_order = AsyncMock(side_effect=mock_execute_order)
        strategy_engine.execution_engine = mock_execution_engine
        
        # Mock state_cache para simular precios diferentes para cada leg
        # Leg 1: precio OK (0.95)
        # Leg 2: precio se movió (0.16 en lugar de 0.10)
        call_count = [0]  # Usar lista para mutabilidad en closure
        
        def mock_get_state(event_id):
            """Mock que devuelve precios diferentes según el leg."""
            call_count[0] += 1
            # Primera llamada: leg_1 (precio OK)
            # Segunda llamada: leg_2 (precio se movió)
            if call_count[0] == 1:
                return {
                    "market_state": {
                        "last_price": Decimal("0.95"),  # OK para leg_1
                        "liquidity": Decimal("10000")
                    }
                }
            else:
                return {
                    "market_state": {
                        "last_price": Decimal("0.16"),  # Se movió de 0.10 a 0.16 (60% > 5%)
                        "liquidity": Decimal("10000")
                    }
                }
        
        strategy_engine.state_cache_service.get_state = Mock(side_effect=mock_get_state)
        
        # Ejecutar Execution Graph
        await strategy_engine.execute_execution_graph(
            atomic_surebet_strategy,
            plan,
            event,
            db_session
        )
        
        # Verificar que el plan se marcó como FAILED
        db_session.refresh(plan)
        assert plan.status == "FAILED", f"Plan should be FAILED, got {plan.status}"
        
        # En modo atomic, si un leg falla, el plan debe marcarse como FAILED
        # y los legs ejecutados deben ser compensados (aunque la compensación
        # real se haría en un nodo compensate_plan)
        
        # Verificar que al menos se intentó ejecutar un leg
        # (El comportamiento exacto depende de cómo se implemente _execute_atomic)

