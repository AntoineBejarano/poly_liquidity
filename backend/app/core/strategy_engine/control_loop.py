"""
Control Loop - Infraestructura fija que mantiene las estrategias vivas.

NO es editable por el usuario.
NO contiene lógica de trading.
Solo orquesta el ciclo de vida de las estrategias.
"""
import asyncio
import logging
from collections import deque
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, cast, String

from app.models.strategy import Strategy
from app.models.strategy_event import StrategyEvent
from app.models.event import Event
from app.models.market import Market
from app.models.execution_plan import ExecutionPlan
from app.core.strategy_engine.trigger_evaluator import TriggerEvaluator
from app.core.directory.service import DirectoryService

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
        self._app = None  # FastAPI app: refresh solo cuando usuario ha pedido estrategias (app.state.control_loop_refresh_requested)
        
        # Trigger Evaluator (usa el state_cache del strategy_engine)
        # Se inicializará cuando el strategy_engine esté inicializado
        self.trigger_evaluator: Optional[TriggerEvaluator] = None
        
        # Counter para auto-attach (se ejecuta cada N ticks, no en cada tick)
        self._auto_attach_counter = 0
        self._auto_attach_interval = 100  # Cada 100 ticks (~10 segundos)
        
        # Counter para refresh de estrategias activas (Gap 4.1)
        # Intervalo configurable; default 50 ticks (~5 segundos con tick 100ms)
        self._refresh_strategies_counter = 0
        self._refresh_strategies_interval = 50  # Cada 50 ticks (~5 segundos)
        
        # Cache de eventos ya procesados para auto-attach (evitar duplicados)
        self._processed_events_cache: Set[Tuple[UUID, UUID]] = set()
        # Phase 4: timestamps de auto-attach por estrategia (para límite por hora)
        self._auto_attach_timestamps: Dict[UUID, deque] = {}

    async def start(self, db: Session, app=None):
        """Inicia el control loop. No carga estrategias al arranque; solo cuando hay usuario logeado y las pide (list/activate)."""
        self.running = True
        self._app = app
        # No llamar load_active_strategies(db) aquí: se cargan en el primer refresh cuando app.state.control_loop_refresh_requested
        logger.info("Control Loop started (strategies load on first authenticated request)")
        
        while self.running:
            try:
                await self.tick(db)
                await asyncio.sleep(0.1)  # 100ms entre ticks
            except Exception as e:
                logger.error(f"Error in control loop: {e}", exc_info=True)
                try:
                    db.rollback()
                except Exception as rb_err:
                    logger.debug("Rollback after tick error: %s", rb_err)
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

    async def _refresh_active_strategies(self, db: Session):
        """
        Refresh de estrategias activas desde DB (Gap 4.1).
        
        Se ejecuta periódicamente (cada _refresh_strategies_interval ticks).
        Garantiza que estrategias activadas/desactivadas por API se reflejen
        en un tiempo acotado sin reiniciar el proceso.
        
        DoD 4.1:
        - Nuevas estrategias activadas se añaden a self.active_strategies
        - Estrategias desactivadas se eliminan de self.active_strategies
        - El loop no genera nuevos trabajos para estrategias desactivadas
        """
        current_active_ids = set(self.active_strategies.keys())
        db_strategies = db.query(Strategy).filter(Strategy.is_active == True).all()
        db_active_ids = {s.id for s in db_strategies}
        db_active_map = {s.id: s for s in db_strategies}

        # Nuevas estrategias activadas (en DB pero no en memoria)
        added_ids = db_active_ids - current_active_ids
        for sid in added_ids:
            self.active_strategies[sid] = db_active_map[sid]
            logger.info(
                f"Strategy {sid} added to active_strategies (activated via API)",
                extra={"component": "control_loop", "event": "strategy_activated_refresh", "strategy_id": str(sid)},
            )

        # Estrategias desactivadas (en memoria pero no activas en DB)
        removed_ids = current_active_ids - db_active_ids
        for sid in removed_ids:
            del self.active_strategies[sid]
            logger.info(
                f"Strategy {sid} removed from active_strategies (deactivated via API)",
                extra={"component": "control_loop", "event": "strategy_deactivated_refresh", "strategy_id": str(sid)},
            )

        if added_ids or removed_ids:
            logger.info(
                f"Active strategies refreshed: added={len(added_ids)}, removed={len(removed_ids)}, total={len(self.active_strategies)}",
                extra={"component": "control_loop", "event": "strategies_refresh_complete"},
            )
    
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
        # Empezar cada tick con sesión limpia (evita PendingRollbackError si el tick anterior falló)
        try:
            db.rollback()
        except Exception:
            pass

        # Refresh de estrategias activas solo si un usuario logeado ya pidió estrategias (list/activate)
        refresh_requested = self._app and getattr(self._app.state, "control_loop_refresh_requested", False)
        if refresh_requested:
            self._refresh_strategies_counter += 1
            if self._refresh_strategies_counter >= self._refresh_strategies_interval:
                self._refresh_strategies_counter = 0
                try:
                    await self._refresh_active_strategies(db)
                except Exception as e:
                    logger.error(f"Error refreshing active strategies: {e}", exc_info=True)
                    try:
                        db.rollback()
                    except Exception:
                        pass

        # Auto-attach de nuevos eventos (cada N ticks)
        self._auto_attach_counter += 1
        if self._auto_attach_counter >= self._auto_attach_interval:
            self._auto_attach_counter = 0
            try:
                await self._check_and_auto_attach_events(db)
            except Exception as e:
                logger.error(f"Error in auto-attach: {e}", exc_info=True)
                try:
                    db.rollback()
                except Exception:
                    pass

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
                                            try:
                                                db.rollback()
                                            except Exception:
                                                pass
                                except Exception as e:
                                    logger.error(
                                        f"Error passing intents to Risk Engine: {e}",
                                        exc_info=True
                                    )
                                    try:
                                        db.rollback()
                                    except Exception:
                                        pass
                        except Exception as e:
                            logger.error(
                                f"Error executing decision graph for strategy {strategy_id}, "
                                f"event {event.id}: {e}",
                                exc_info=True
                            )
                            try:
                                db.rollback()
                            except Exception:
                                pass
                    
                    # Ejecutar Support Graphs según sus triggers (cold path, async)
                    await self._execute_support_graphs(strategy, event, db)
                
                # NUEVO: Ejecutar Execution Graphs para planes listos
                await self._execute_ready_plans(strategy, db)
                    
            except Exception as e:
                logger.error(
                    f"Error processing strategy {strategy_id}: {e}",
                    exc_info=True
                )
                try:
                    db.rollback()
                except Exception:
                    pass
    
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
                
                # Emitir evento WebSocket: plan en ejecución
                try:
                    from app.api.websocket import broadcast_strategy_event
                    payload = {
                        "plan_id": str(plan.id),
                        "strategy_id": str(strategy.id),
                        "event_id": str(plan.event_id),
                        "status": "EXECUTING",
                        "legs": plan.legs,
                        "trace_id": str(plan.trace_id) if plan.trace_id else None,
                        "created_at": plan.created_at.isoformat() if plan.created_at else None,
                    }
                    await broadcast_strategy_event(strategy.id, "plan_executing", payload)
                except Exception as ws_err:
                    logger.warning(f"Failed to broadcast plan_executing: {ws_err}")
                
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
        Verifica si hay nuevos eventos elegibles (vía Directory) y los asigna si auto_attach=True.
        Phase 4: usa Directory, aplica enabled global, deny_list, time_filter; límites y dry-run.
        """
        try:
            from app.core.config_service import config_service
            auto_attach_enabled = config_service.get("auto_attach_enabled")
            if auto_attach_enabled is not None and not auto_attach_enabled:
                return
        except Exception:
            pass

        for strategy_id, strategy in self.active_strategies.items():
            universe = strategy.universe_config or {}
            if not universe.get("auto_attach", False):
                continue

            categories = universe.get("categories", [])
            markets = universe.get("markets", [])
            tags = universe.get("tags", [])
            events_explicit = universe.get("events", [])
            if not categories and not markets and not tags and not events_explicit:
                logger.debug(
                    "Strategy %s has auto_attach but no universe selectors, skipping",
                    strategy_id,
                    extra={"component": "control_loop", "event": "auto_attach_skip_no_filters", "strategy_id": str(strategy_id)},
                )
                continue

            max_events = universe.get("max_events_per_strategy") or 50
            max_per_hour = universe.get("max_auto_attaches_per_hour") or 10
            dry_run = universe.get("auto_attach_dry_run", False)

            try:
                matching_events = DirectoryService.get_events_eligible_for_universe(
                    db, universe, limit=max_events
                )
            except Exception as e:
                logger.error(
                    "Directory unavailable for auto-attach, strategy %s: %s",
                    strategy_id, e,
                    exc_info=True,
                    extra={"component": "control_loop", "event": "auto_attach_directory_error", "strategy_id": str(strategy_id)},
                )
                continue

            current_count = db.query(StrategyEvent).filter(
                StrategyEvent.strategy_id == strategy_id
            ).count()
            if current_count >= max_events:
                logger.debug(
                    "Strategy %s at max_events_per_strategy (%s), skipping auto-attach",
                    strategy_id, max_events,
                    extra={"component": "control_loop", "event": "auto_attach_rejected_max_events", "strategy_id": str(strategy_id)},
                )
                continue

            if strategy_id not in self._auto_attach_timestamps:
                self._auto_attach_timestamps[strategy_id] = deque(maxlen=1000)
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(hours=1)
            while self._auto_attach_timestamps[strategy_id] and self._auto_attach_timestamps[strategy_id][0] < cutoff:
                self._auto_attach_timestamps[strategy_id].popleft()
            if len(self._auto_attach_timestamps[strategy_id]) >= max_per_hour:
                logger.debug(
                    "Strategy %s at max_auto_attaches_per_hour (%s), skipping auto-attach",
                    strategy_id, max_per_hour,
                    extra={"component": "control_loop", "event": "auto_attach_rejected_rate_limit", "strategy_id": str(strategy_id)},
                )
                continue

            try:
                attached = 0
                for event in matching_events:
                    if current_count + attached >= max_events:
                        break
                    if len(self._auto_attach_timestamps[strategy_id]) >= max_per_hour:
                        break

                    existing = db.query(StrategyEvent).filter(
                        StrategyEvent.strategy_id == strategy_id,
                        StrategyEvent.event_id == event.id,
                    ).first()
                    if existing:
                        continue
                    cache_key = (strategy_id, event.id)
                    if cache_key in self._processed_events_cache:
                        continue

                    if dry_run:
                        logger.info(
                            "Auto-attach dry-run: would attach event %s (%s) to strategy %s",
                            event.id, event.polymarket_event_id, strategy_id,
                            extra={"component": "control_loop", "event": "auto_attach_dry_run", "strategy_id": str(strategy_id), "event_id": str(event.id)},
                        )
                        self._processed_events_cache.add(cache_key)
                        continue

                    strategy_event = StrategyEvent(
                        strategy_id=strategy_id,
                        event_id=event.id,
                        event_config={},
                    )
                    db.add(strategy_event)
                    self._processed_events_cache.add(cache_key)
                    self._auto_attach_timestamps[strategy_id].append(now)
                    attached += 1
                    logger.info(
                        "Auto-attached event %s (%s) to strategy %s",
                        event.id, event.polymarket_event_id, strategy_id,
                        extra={"component": "control_loop", "event": "auto_attach_assigned", "strategy_id": str(strategy_id), "event_id": str(event.id)},
                    )
                    await self._subscribe_to_event_orderbooks(strategy_id, event, db)

                if attached > 0:
                    db.commit()
            except Exception as e:
                logger.error(
                    "Error auto-attaching events for strategy %s: %s",
                    strategy_id, e,
                    exc_info=True,
                    extra={"component": "control_loop", "event": "auto_attach_error", "strategy_id": str(strategy_id)},
                )
                db.rollback()
    
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

