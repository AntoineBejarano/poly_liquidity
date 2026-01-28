"""
Control Loop - Infraestructura fija que mantiene las estrategias vivas.

NO es editable por el usuario.
NO contiene lógica de trading.
Solo orquesta el ciclo de vida de las estrategias.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Set
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.strategy import Strategy
from app.models.strategy_event import StrategyEvent
from app.models.event import Event
from app.models.market import Market
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
        
        # Counter para auto-attach (se ejecuta cada N ticks, no en cada tick)
        self._auto_attach_counter = 0
        self._auto_attach_interval = 100  # Cada 100 ticks (~10 segundos)
        
        # Cache de eventos ya procesados para auto-attach (evitar duplicados)
        self._processed_events_cache: Set[UUID] = set()
    
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
        5. Periódicamente, verifica auto-attach de nuevos eventos
        """
        # Auto-attach de nuevos eventos (cada N ticks)
        self._auto_attach_counter += 1
        if self._auto_attach_counter >= self._auto_attach_interval:
            self._auto_attach_counter = 0
            try:
                await self._check_and_auto_attach_events(db)
            except Exception as e:
                logger.error(f"Error in auto-attach: {e}", exc_info=True)
        
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
        now = datetime.now(timezone.utc)
        
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
    
    async def _check_and_auto_attach_events(self, db: Session):
        """
        Verifica si hay nuevos eventos que cumplan con el universe de alguna estrategia
        con auto_attach=True, y los asigna automáticamente.
        
        Se ejecuta periódicamente (cada ~10 segundos) para no sobrecargar.
        """
        # Obtener estrategias activas con auto_attach habilitado
        for strategy_id, strategy in self.active_strategies.items():
            universe = strategy.universe_config or {}
            
            # Solo procesar si auto_attach está habilitado
            if not universe.get("auto_attach", False):
                continue
            
            categories = universe.get("categories", [])
            markets = universe.get("markets", [])
            tags = universe.get("tags", [])
            deny_list = universe.get("deny_list", [])
            
            # Si no hay filtros definidos, no hacer nada (evitar asignar todos los eventos)
            if not categories and not markets and not tags:
                logger.debug(f"Strategy {strategy_id} has auto_attach but no filters, skipping")
                continue
            
            try:
                # Buscar eventos que cumplan con el universe
                matching_events = self._find_matching_events(
                    db, categories, markets, tags, deny_list
                )
                
                # Asignar eventos que no estén ya asignados
                for event in matching_events:
                    # Verificar si ya está asignado a esta estrategia
                    existing = db.query(StrategyEvent).filter(
                        StrategyEvent.strategy_id == strategy_id,
                        StrategyEvent.event_id == event.id
                    ).first()
                    
                    if existing:
                        continue
                    
                    # Verificar si ya lo procesamos en esta sesión (cache)
                    cache_key = (strategy_id, event.id)
                    if cache_key in self._processed_events_cache:
                        continue
                    
                    # Asignar evento a la estrategia
                    strategy_event = StrategyEvent(
                        strategy_id=strategy_id,
                        event_id=event.id,
                        event_config={}
                    )
                    db.add(strategy_event)
                    
                    # Añadir a cache
                    self._processed_events_cache.add(cache_key)
                    
                    logger.info(
                        f"Auto-attached event {event.id} ({event.polymarket_event_id}) "
                        f"to strategy {strategy_id}"
                    )
                    
                    # Suscribir a orderbooks del nuevo evento
                    await self._subscribe_to_event_orderbooks(strategy_id, event, db)
                
                db.commit()
                
            except Exception as e:
                logger.error(
                    f"Error auto-attaching events for strategy {strategy_id}: {e}",
                    exc_info=True
                )
                db.rollback()
    
    def _find_matching_events(
        self,
        db: Session,
        categories: List[str],
        markets: List[str],
        tags: List[str],
        deny_list: List[str]
    ) -> List[Event]:
        """
        Encuentra eventos que cumplan con los criterios del universe.
        
        Args:
            categories: Categorías permitidas (ej: ["Sports", "Politics"])
            markets: Markets específicos por polymarket_id
            tags: Tags permitidos
            deny_list: Markets/events a excluir
        
        Returns:
            Lista de eventos que cumplen los criterios
        """
        # Query base: eventos UPCOMING o ACTIVE
        query = db.query(Event).filter(
            Event.state.in_(["UPCOMING", "ACTIVE"])
        )
        
        # Filtrar por categorías si están definidas
        # Nota: La categoría está en el Market, no en el Event directamente
        if categories:
            # Join con Market para filtrar por categoría
            query = query.join(Market, Event.market_id == Market.id).filter(
                or_(
                    Market.category.in_(categories),
                    # También verificar en polymarket_payload si existe
                    Market.polymarket_payload["category"].astext.in_(categories)
                )
            )
        
        # Filtrar por markets específicos
        if markets:
            query = query.filter(
                or_(
                    Event.polymarket_event_id.in_(markets),
                    Event.market.has(Market.polymarket_id.in_(markets))
                )
            )
        
        # Excluir deny_list
        if deny_list:
            query = query.filter(
                ~Event.polymarket_event_id.in_(deny_list),
                ~Event.market.has(Market.polymarket_id.in_(deny_list))
            )
        
        # Limitar resultados para no sobrecargar
        return query.limit(50).all()
    
    async def _subscribe_to_event_orderbooks(
        self,
        strategy_id: UUID,
        event: Event,
        db: Session
    ):
        """
        Suscribe a los orderbooks del evento auto-attached.
        """
        try:
            from app.core.orderbook.service import get_orderbook_service
            from app.core.strategy_engine.state_cache_service import StateCacheService
            
            orderbook_service = get_orderbook_service(StateCacheService(db))
            
            # Obtener asset_ids del evento
            asset_ids = set()
            clob_token_ids = None
            
            if event.polymarket_payload:
                clob_token_ids = (
                    event.polymarket_payload.get("clobTokenIds") or 
                    event.polymarket_payload.get("clob_token_ids")
                )
            
            if not clob_token_ids and event.market:
                if event.market.polymarket_payload:
                    clob_token_ids = (
                        event.market.polymarket_payload.get("clobTokenIds") or 
                        event.market.polymarket_payload.get("clob_token_ids")
                    )
            
            if clob_token_ids:
                if isinstance(clob_token_ids, dict):
                    asset_ids.update(clob_token_ids.values())
                elif isinstance(clob_token_ids, list):
                    asset_ids.update(clob_token_ids)
            
            # Suscribir a cada asset_id
            owner_key = f"strategy_{strategy_id}"
            for asset_id in asset_ids:
                orderbook_service.subscribe(asset_id, owner_key)
                logger.debug(
                    f"Subscribed strategy {strategy_id} to asset_id={asset_id} "
                    f"from auto-attached event {event.id}"
                )
                
        except Exception as e:
            logger.warning(
                f"Error subscribing to orderbooks for auto-attached event {event.id}: {e}"
            )

