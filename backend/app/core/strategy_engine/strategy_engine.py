"""
Strategy Engine - Orquestador principal.

Coordina Control Loop, Graph Runtime, State Cache.
"""
import logging
from typing import List, Dict, Any
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.strategy_engine.state_cache_service import StateCacheService
from app.core.strategy_engine.graph_runtime import GraphRuntime
from app.core.strategy_engine.control_loop import ControlLoop
from app.core.strategy_engine.models import GraphExecutionContext
from app.models.graph_execution import GraphExecution
from app.models.execution_intent import ExecutionIntent
from app.core.strategy.models import OrderIntent

logger = logging.getLogger(__name__)


class StrategyEngine:
    """
    Strategy Engine - Orquestador principal.
    
    Coordina Control Loop, Graph Runtime, State Cache.
    """
    
    def __init__(self):
        self.state_cache_service: StateCacheService = None
        self.graph_runtime: GraphRuntime = None
        self.control_loop: ControlLoop = None
        self.execution_engine = None  # Para pasar a Execution Graphs (legacy)
        self.trading_platform = None  # TradingPlatform para Execution Graphs (nuevo)
    
    def initialize(self, db: Session, risk_engine=None, execution_engine=None):
        """Inicializa el engine con una sesión de DB."""
        self.state_cache_service = StateCacheService(db)
        self.graph_runtime = GraphRuntime(self.state_cache_service)
        self.execution_engine = execution_engine  # Guardar para usar en Execution Graphs
        self.control_loop = ControlLoop(
            self,
            risk_engine=risk_engine,
            execution_engine=execution_engine
        )
        # Inicializar trigger evaluator en control loop
        from app.core.strategy_engine.trigger_evaluator import TriggerEvaluator
        self.control_loop.trigger_evaluator = TriggerEvaluator(self.state_cache_service)
        logger.info("StrategyEngine initialized")
    
    async def execute_decision_graph(
        self,
        strategy: 'Strategy',
        event: 'Event',
        db: Session
    ) -> List[OrderIntent]:
        """
        Ejecuta el Decision Graph para una estrategia y evento.
        
        Hot path - debe ser rápido.
        
        Returns:
            List[OrderIntent]: Lista de intents generados
        """
        trace_id = uuid4()
        started_at = datetime.utcnow()
        
        try:
            # Crear contexto
            context = GraphExecutionContext(
                strategy_id=strategy.id,
                event_id=event.id,
                market_id=event.market_id,
                trace_id=trace_id,
                state_cache=self.state_cache_service,
                db=db,
                strategy=strategy,
                observability_config=strategy.observability_config or {}
            )
            # Añadir grafo actual al contexto para versionado
            context.current_graph = strategy.decision_graph
            
            # Ejecutar grafo
            result = await self.graph_runtime.execute_graph(
                graph=strategy.decision_graph,
                context=context,
                path_type="hot"
            )
            
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            # Guardar ejecución en DB
            execution = GraphExecution(
                strategy_id=strategy.id,
                graph_type="decision",
                event_id=event.id,
                status="completed" if result.success else "failed",
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                result={"intents_count": len(result.intents)},
                error_message=result.error_message if not result.success else None,
                trace_id=trace_id,
                node_executions=result.execution_trace
            )
            db.add(execution)
            db.flush()  # Para obtener el ID
            
            # Convertir intents a ExecutionIntent (modelo DB) y guardar
            db_intents = []
            for intent in result.intents:
                db_intent = ExecutionIntent(
                    strategy_id=strategy.id,
                    event_id=event.id,
                    side=intent.side,
                    outcome=intent.outcome,
                    target_price=intent.price,
                    size=intent.size,
                    size_usdc=intent.size * intent.price,
                    reason=intent.reason,
                    context=intent.metadata,
                    status="PENDING",
                    trace_id=trace_id,
                    graph_execution_id=execution.id
                )
                db.add(db_intent)
                db_intents.append(db_intent)
            
            db.commit()
            
            logger.info(
                f"Decision graph executed for strategy {strategy.id}, "
                f"event {event.id}: {len(result.intents)} intents generated"
            )
            
            return result.intents
            
        except Exception as e:
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            # Guardar ejecución fallida
            execution = GraphExecution(
                strategy_id=strategy.id,
                graph_type="decision",
                event_id=event.id,
                status="failed",
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                error_message=str(e),
                trace_id=trace_id
            )
            db.add(execution)
            db.commit()
            
            logger.error(
                f"Error executing decision graph for strategy {strategy.id}, "
                f"event {event.id}: {e}",
                exc_info=True
            )
            raise
    
    async def execute_support_graph(
        self,
        strategy: 'Strategy',
        support_graph: Dict[str, Any],
        event: 'Event',
        db: Session
    ):
        """
        Ejecuta un Support Graph.
        
        Cold path - puede tardar, no bloquea.
        """
        trace_id = uuid4()
        graph_name = support_graph.get("name", "unnamed")
        started_at = datetime.utcnow()
        
        try:
            context = GraphExecutionContext(
                strategy_id=strategy.id,
                event_id=event.id,
                market_id=event.market_id,
                trace_id=trace_id,
                state_cache=self.state_cache_service
            )
            
            result = await self.graph_runtime.execute_graph(
                graph=support_graph,
                context=context,
                path_type="cold"
            )
            
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            execution = GraphExecution(
                strategy_id=strategy.id,
                graph_type="support",
                graph_name=graph_name,
                event_id=event.id,
                status="completed" if result.success else "failed",
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                result={"success": result.success, "intents_count": len(result.intents)},
                error_message=result.error_message if not result.success else None,
                trace_id=trace_id,
                node_executions=result.execution_trace
            )
            
            db.add(execution)
            db.commit()
            
            logger.info(
                f"Support graph '{graph_name}' executed for strategy {strategy.id}, "
                f"event {event.id}: success={result.success}"
            )
            
        except Exception as e:
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            execution = GraphExecution(
                strategy_id=strategy.id,
                graph_type="support",
                graph_name=graph_name,
                event_id=event.id,
                status="failed",
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                error_message=str(e),
                trace_id=trace_id
            )
            
            db.add(execution)
            db.commit()
            
            logger.error(
                f"Error executing support graph '{graph_name}' for strategy {strategy.id}, "
                f"event {event.id}: {e}",
                exc_info=True
            )
    
    async def execute_execution_graph(
        self,
        strategy: 'Strategy',
        plan: 'ExecutionPlan',
        event: 'Event',
        db: Session
    ) -> None:
        """
        Ejecuta Execution Graph para un plan.
        
        Cold path - puede tardar, maneja retries y compensación.
        """
        if not strategy.execution_graph:
            logger.warning(
                f"Strategy {strategy.id} has no execution_graph defined. "
                f"Cannot execute plan {plan.id}"
            )
            return
        
        trace_id = plan.trace_id or uuid4()
        started_at = datetime.utcnow()
        
        try:
            # Crear contexto para Execution Graph
            context = GraphExecutionContext(
                strategy_id=strategy.id,
                event_id=event.id,
                market_id=event.market_id,
                trace_id=trace_id,
                state_cache=self.state_cache_service,
                db=db,
                plan_id=plan.id
            )
            
            # Añadir trading_platform al contexto (preferido)
            # Si no hay trading_platform configurado, crear PolymarketAdapter con user_id del dueño (política v2)
            # TODO(plan §3.1): cuando exista strategy.execution_user_id en el modelo, usar ese en lugar de created_by.
            if self.trading_platform is None:
                from app.core.execution_engine.platforms import PolymarketAdapter
                user_id = getattr(strategy, "created_by", None)
                if not user_id:
                    logger.warning("Strategy %s has no created_by; PolymarketAdapter will have no CLOB", strategy.id)
                self.trading_platform = PolymarketAdapter(config={"user_id": str(user_id)} if user_id else None)
            
            if self.trading_platform and self.trading_platform.is_available():
                context.trading_platform = self.trading_platform
            
            # Añadir execution_engine al contexto si está disponible (legacy)
            if self.execution_engine:
                context.execution_engine = self.execution_engine
            
            # Ejecutar Execution Graph
            result = await self.graph_runtime.execute_graph(
                graph=strategy.execution_graph,
                context=context,
                path_type="cold"
            )
            
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            # Emitir evento WebSocket: plan_filled o plan_failed
            try:
                from app.api.websocket import broadcast_strategy_event
                db.refresh(plan)
                payload = {
                    "plan_id": str(plan.id),
                    "strategy_id": str(strategy.id),
                    "event_id": str(plan.event_id),
                    "status": plan.status,
                    "legs": plan.legs,
                    "trace_id": str(plan.trace_id) if plan.trace_id else None,
                    "created_at": plan.created_at.isoformat() if plan.created_at else None,
                    "success": result.success,
                    "duration_ms": duration_ms,
                }
                await broadcast_strategy_event(
                    strategy.id,
                    "plan_filled" if result.success else "plan_failed",
                    payload,
                )
            except Exception as ws_err:
                logger.warning(f"Failed to broadcast plan_filled/failed: {ws_err}")
            
            # Guardar ejecución en DB
            execution = GraphExecution(
                strategy_id=strategy.id,
                graph_type="execution",
                event_id=event.id,
                status="completed" if result.success else "failed",
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                result={"success": result.success, "plan_id": str(plan.id)},
                error_message=result.error_message if not result.success else None,
                trace_id=trace_id,
                node_executions=result.execution_trace
            )
            db.add(execution)
            db.flush()
            
            # Actualizar plan con execution_graph_execution_id
            plan.execution_graph_execution_id = execution.id
            db.flush()
            
            logger.info(
                f"Execution graph executed for plan {plan.id}, strategy {strategy.id}, "
                f"event {event.id}: success={result.success}"
            )
            
        except Exception as e:
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            # Emitir evento WebSocket: plan_failed (excepción)
            try:
                from app.api.websocket import broadcast_strategy_event
                payload = {
                    "plan_id": str(plan.id),
                    "strategy_id": str(strategy.id),
                    "event_id": str(plan.event_id),
                    "status": "FAILED",
                    "legs": plan.legs,
                    "trace_id": str(plan.trace_id) if plan.trace_id else None,
                    "created_at": plan.created_at.isoformat() if plan.created_at else None,
                    "success": False,
                    "error": str(e),
                    "duration_ms": duration_ms,
                }
                await broadcast_strategy_event(strategy.id, "plan_failed", payload)
            except Exception as ws_err:
                logger.warning(f"Failed to broadcast plan_failed: {ws_err}")
            
            execution = GraphExecution(
                strategy_id=strategy.id,
                graph_type="execution",
                event_id=event.id,
                status="failed",
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                error_message=str(e),
                trace_id=trace_id
            )
            db.add(execution)
            db.flush()
            
            logger.error(
                f"Error executing execution graph for plan {plan.id}, "
                f"strategy {strategy.id}, event {event.id}: {e}",
                exc_info=True
            )
            # No re-raise: Support Graphs no deben bloquear el Control Loop

