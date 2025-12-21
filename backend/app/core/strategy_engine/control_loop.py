"""
Control Loop - Infraestructura fija que mantiene las estrategias vivas.

NO es editable por el usuario.
NO contiene lógica de trading.
Solo orquesta el ciclo de vida de las estrategias.
"""
import asyncio
import logging
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.strategy import Strategy
from app.models.strategy_event import StrategyEvent
from app.models.event import Event
from app.models.execution_plan import ExecutionPlan
from app.core.strategy_engine.trigger_evaluator import TriggerEvaluator

logger = logging.getLogger(__name__)


class ControlLoop:
    """
    Control Loop - Infraestructura fija que mantiene las estrategias vivas.
    
    NO es editable por el usuario.
    NO contiene lógica de trading.
    Solo orquesta el ciclo de vida de las estrategias.
    """
    
    def __init__(self, strategy_engine: 'StrategyEngine', risk_engine=None, execution_engine=None):
        self.strategy_engine = strategy_engine
        self.risk_engine = risk_engine  # Opcional: para pasar intents directamente
        self.execution_engine = execution_engine  # Opcional: para pasar approved intents
        self.active_strategies: Dict[UUID, Strategy] = {}
        self.running = False
        
        # Trigger Evaluator (usa el state_cache del strategy_engine)
        # Se inicializará cuando el strategy_engine esté inicializado
        self.trigger_evaluator: Optional[TriggerEvaluator] = None
    
    async def start(self, db: Session):
        """Inicia el control loop."""
        self.running = True
        await self.load_active_strategies(db)
        
        logger.info("Control Loop started")
        
        while self.running:
            try:
                await self.tick(db)
                await asyncio.sleep(0.1)  # 100ms entre ticks
            except Exception as e:
                logger.error(f"Error in control loop: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def stop(self):
        """Detiene el control loop."""
        self.running = False
        logger.info("Control Loop stopped")
    
    async def load_active_strategies(self, db: Session):
        """Carga estrategias activas desde DB."""
        strategies = db.query(Strategy).filter(Strategy.is_active == True).all()
        self.active_strategies = {s.id: s for s in strategies}
        logger.info(f"Loaded {len(self.active_strategies)} active strategies")
    
    async def tick(self, db: Session):
        """
        Tick principal del control loop.
        
        Para cada estrategia activa:
        1. Obtiene eventos asignados
        2. Para cada evento, verifica triggers
        3. Si trigger activado, ejecuta Decision Graph
        4. Ejecuta Support Graphs según sus triggers
        """
        for strategy_id, strategy in self.active_strategies.items():
            try:
                # Obtener eventos asignados a esta estrategia
                strategy_events = db.query(StrategyEvent).filter(
                    StrategyEvent.strategy_id == strategy_id
                ).all()
                
                for strategy_event in strategy_events:
                    event = strategy_event.event
                    
                    # Verificar si debemos observar este evento
                    if not self._should_observe(strategy, event, strategy_event):
                        continue
                    
                    # Verificar triggers de la estrategia
                    if self._evaluate_triggers(strategy, event):
                        # Ejecutar Decision Graph (hot path)
                        try:
                            intents = await self.strategy_engine.execute_decision_graph(
                                strategy, event, db
                            )
                            
                            # Si hay Risk Engine configurado, pasar intents directamente
                            if self.risk_engine and intents:
                                try:
                                    approved_intents = await self.risk_engine.tick(intents)
                                    logger.debug(
                                        f"Risk Engine processed {len(intents)} intents, "
                                        f"approved {len(approved_intents)}"
                                    )
                                    
                                    # Si hay Execution Engine configurado, pasar approved intents
                                    if self.execution_engine and approved_intents:
                                        try:
                                            await self.execution_engine.tick(approved_intents)
                                            logger.debug(
                                                f"Execution Engine processed {len(approved_intents)} approved intents"
                                            )
                                        except Exception as e:
                                            logger.error(
                                                f"Error passing approved intents to Execution Engine: {e}",
                                                exc_info=True
                                            )
                                except Exception as e:
                                    logger.error(
                                        f"Error passing intents to Risk Engine: {e}",
                                        exc_info=True
                                    )
                        except Exception as e:
                            logger.error(
                                f"Error executing decision graph for strategy {strategy_id}, "
                                f"event {event.id}: {e}",
                                exc_info=True
                            )
                    
                    # Ejecutar Support Graphs según sus triggers (cold path, async)
                    await self._execute_support_graphs(strategy, event, db)
                
                # NUEVO: Ejecutar Execution Graphs para planes listos
                await self._execute_ready_plans(strategy, db)
                    
            except Exception as e:
                logger.error(
                    f"Error processing strategy {strategy_id}: {e}",
                    exc_info=True
                )
    
    def _should_observe(self, strategy: Strategy, event: Event, strategy_event: StrategyEvent) -> bool:
        """
        Verifica si debemos observar este evento.
        
        Verifica:
        - Timing (observation_started_at, observation_ended_at)
        - Estado del evento (UPCOMING, ACTIVE)
        """
        now = datetime.utcnow()
        
        # Verificar timing
        if strategy_event.observation_started_at and now < strategy_event.observation_started_at:
            return False
        
        if strategy_event.observation_ended_at and now > strategy_event.observation_ended_at:
            return False
        
        # Verificar estado del evento
        # Solo observamos eventos que están UPCOMING o ACTIVE
        if event.state not in ["UPCOMING", "ACTIVE"]:
            return False
        
        return True
    
    def _evaluate_triggers(self, strategy: Strategy, event: Event) -> bool:
        """
        Evalúa triggers de la estrategia.
        
        Si no hay triggers definidos, retorna True (comportamiento por defecto: siempre ejecutar).
        Si hay triggers, evalúa cada uno y retorna True si al menos uno match.
        """
        triggers = strategy.triggers or []
        
        # Si no hay triggers, ejecutar siempre (comportamiento por defecto)
        if not triggers:
            return True
        
        # Si no hay trigger evaluator, ejecutar siempre (fallback)
        if not self.trigger_evaluator:
            logger.warning(f"No trigger evaluator available for strategy {strategy.id}, executing always")
            return True
        
        # Evaluar cada trigger
        # Si al menos uno match, ejecutar Decision Graph
        for trigger in triggers:
            try:
                if self.trigger_evaluator.evaluate(trigger, strategy, event):
                    return True
            except Exception as e:
                logger.error(
                    f"Error evaluating trigger for strategy {strategy.id}, event {event.id}: {e}",
                    exc_info=True
                )
                # Continuar con el siguiente trigger en caso de error
                continue
        
        # Ningún trigger match
        return False
    
    async def _execute_support_graphs(
        self,
        strategy: Strategy,
        event: Event,
        db: Session
    ):
        """
        Ejecuta Support Graphs según sus triggers.
        
        Support Graphs se ejecutan de forma asíncrona y no bloquean.
        """
        support_graphs = strategy.support_graphs or []
        
        for support_graph in support_graphs:
            try:
                # Verificar trigger del Support Graph
                if not self._check_support_graph_trigger(support_graph, event):
                    continue
                
                # Ejecutar Support Graph (no bloquea, no esperamos)
                # Usar asyncio.create_task para ejecutar en background
                asyncio.create_task(
                    self.strategy_engine.execute_support_graph(
                        strategy, support_graph, event, db
                    )
                )
                
            except Exception as e:
                logger.error(
                    f"Error executing support graph '{support_graph.get('name', 'unnamed')}' "
                    f"for strategy {strategy.id}, event {event.id}: {e}",
                    exc_info=True
                )
    
    def _check_support_graph_trigger(self, support_graph: Dict, event: Event) -> bool:
        """
        Verifica si un Support Graph debe ejecutarse.
        
        Los Support Graphs pueden tener triggers:
        - "timer": cada X segundos
        - "event_state_change": cuando cambia el estado del evento
        - "manual": solo cuando se llama manualmente
        - etc.
        
        Por ahora, siempre retorna True (ejecutar en cada tick).
        """
        trigger = support_graph.get("trigger", {})
        trigger_type = trigger.get("type", "always")
        
        if trigger_type == "always":
            return True
        elif trigger_type == "timer":
            # TODO: Implementar lógica de timer
            # Verificar si ha pasado el intervalo desde la última ejecución
            return True
        elif trigger_type == "event_state_change":
            # TODO: Implementar lógica de cambio de estado
            return True
        else:
            return False
    
    async def _execute_ready_plans(self, strategy: Strategy, db: Session):
        """
        Ejecuta Execution Graphs para planes listos (ready_for_execution=True).
        
        Busca planes con status=PLAN_BUILT y ready_for_execution=True,
        y ejecuta el Execution Graph de la estrategia.
        """
        if not strategy.execution_graph:
            # No hay Execution Graph definido, no hacer nada
            return
        
        # Buscar planes listos para esta estrategia
        ready_plans = db.query(ExecutionPlan).filter(
            ExecutionPlan.strategy_id == strategy.id,
            ExecutionPlan.ready_for_execution == True,
            ExecutionPlan.status == "PLAN_BUILT"
        ).limit(10).all()  # Limitar a 10 planes por tick para no sobrecargar
        
        for plan in ready_plans:
            try:
                # Obtener el evento del plan
                event = plan.event
                if not event:
                    logger.warning(f"Plan {plan.id} has no event, skipping")
                    continue
                
                # Ejecutar Execution Graph
                await self.strategy_engine.execute_execution_graph(
                    strategy, plan, event, db
                )
                
            except Exception as e:
                logger.error(
                    f"Error executing execution graph for plan {plan.id}, "
                    f"strategy {strategy.id}: {e}",
                    exc_info=True
                )

