"""
Watcher individual - Monitorea un evento específico.

Según especificación en docs/services/event_watch_engine.md
"""
import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from app.core.event_watch_engine.models import (
    WatcherState, WatcherStatus, EventStateType, StateSnapshot, WatchEngineConfig
)
from app.core.event_watch_engine.state_aggregator import StateAggregator
from app.core.event_watch_engine.lifecycle_manager import LifecycleManager
from app.core.checkers.runner import CheckerRunner
from app.core.checkers.registry import checker_registry
from app.core.checkers.base import CheckerResult
from app.core.event_mapping_layer.models import EventDescriptor

logger = logging.getLogger(__name__)


class Watcher:
    """
    Watcher individual que monitorea un evento específico.
    
    Responsabilidades:
    - Ejecutar checkers periódicamente
    - Agregar resultados usando quorum rules
    - Gestionar transiciones de estado
    - Notificar cambios de estado
    """
    
    def __init__(
        self,
        event_descriptor: EventDescriptor,
        config: WatchEngineConfig,
        lifecycle_manager: LifecycleManager
    ):
        """
        Inicializa el watcher.
        
        Args:
            event_descriptor: Descriptor del evento a monitorear
            config: Configuración del Watch Engine
            lifecycle_manager: Manager del ciclo de vida
        """
        self.event_descriptor = event_descriptor
        self.config = config
        self.lifecycle_manager = lifecycle_manager
        self.checker_runner = CheckerRunner()
        self.state_aggregator = StateAggregator(config)
        
        # Estado interno
        self._state = WatcherState(
            event_id=event_descriptor.canonical_event_id or event_descriptor.market_id,
            event_type=event_descriptor.event_type,
            trace_id=event_descriptor.trace_id,
            markets=[],  # Se actualizará cuando se registren mercados
            status=WatcherStatus.INITIALIZING,
            last_state=EventStateType.UNKNOWN,
            confidence=0.0,
            created_at=datetime.utcnow(),
            last_update=datetime.utcnow(),
            check_interval_seconds=self._get_check_interval(),
            max_duration_hours=config.watcher_max_duration_hours
        )
        
        self._active = False
        self._task: Optional[asyncio.Task] = None
        
        # Cargar checkers para este tipo de evento
        self._checkers = self._load_checkers()
    
    def _get_check_interval(self) -> int:
        """Obtiene el intervalo de checks según el tipo de evento."""
        event_type = self.event_descriptor.event_type
        if event_type == "sports":
            return self.config.check_frequency_sports
        elif event_type == "politics":
            return self.config.check_frequency_politics
        elif event_type == "crypto":
            return self.config.check_frequency_crypto
        elif event_type == "finance":
            return self.config.check_frequency_finance
        elif event_type == "weather":
            return self.config.check_frequency_weather
        else:
            return 30  # Default
    
    def _load_checkers(self) -> List:
        """
        Carga checkers para este tipo de evento.
        
        Returns:
            Lista de instancias de checkers
        """
        checker_classes = checker_registry.list_by_event_type(self.event_descriptor.event_type)
        checkers = []
        for checker_class in checker_classes:
            try:
                checker_instance = checker_class()
                checkers.append(checker_instance)
            except Exception as e:
                logger.error(f"Error instantiating checker {checker_class.__name__}: {e}")
        
        logger.info(f"Loaded {len(checkers)} checkers for event type {self.event_descriptor.event_type}")
        return checkers
    
    async def start(self):
        """Inicia el watcher."""
        if self._active:
            return
        
        self._active = True
        self._state.status = WatcherStatus.INITIALIZING
        
        # Inicializar checkers
        if not self._checkers:
            logger.warning(f"No checkers available for event {self._state.event_id}")
            self._state.status = WatcherStatus.ERROR_RETRYING
            return
        
        self._state.status = WatcherStatus.LIVE_MONITORING
        self._task = asyncio.create_task(self._watch_loop())
        
        logger.info(
            f"Started watcher for event {self._state.event_id} "
            f"(type: {self._state.event_type}, checkers: {len(self._checkers)})"
        )
    
    async def stop(self):
        """Detiene el watcher."""
        self._active = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        self._state.status = WatcherStatus.TERMINATED
        logger.info(f"Stopped watcher for event {self._state.event_id}")
    
    def add_market(self, market_id: UUID):
        """Agrega un mercado a este watcher."""
        if market_id not in self._state.markets:
            self._state.markets.append(market_id)
            logger.info(f"Added market {market_id} to watcher {self._state.event_id}")
    
    def remove_market(self, market_id: UUID):
        """Remueve un mercado de este watcher."""
        if market_id in self._state.markets:
            self._state.markets.remove(market_id)
            logger.info(f"Removed market {market_id} from watcher {self._state.event_id}")
    
    def get_state(self) -> WatcherState:
        """Obtiene el estado actual del watcher."""
        return self._state
    
    async def _watch_loop(self):
        """Loop principal de monitoreo."""
        while self._active:
            try:
                start_time = datetime.utcnow()
                
                # 1. Ejecutar checkers en paralelo
                checker_results = await self._run_checkers()
                
                # 2. Agregar resultados
                aggregated_state = self.state_aggregator.aggregate(
                    checker_results,
                    self._state.event_id,
                    str(self._state.trace_id)
                )
                
                # 3. Verificar cambio de estado
                if aggregated_state.state != self._state.last_state:
                    await self._handle_state_transition(aggregated_state)
                
                # 4. Actualizar estado
                self._state.last_state = aggregated_state.state
                self._state.confidence = aggregated_state.confidence
                self._state.last_checker_results = checker_results
                self._state.last_update = datetime.utcnow()
                
                # Calcular latencia
                latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                self._state.last_check_latency_ms = latency_ms
                self._state.total_checks += 1
                
                # Agregar snapshot al historial
                snapshot = StateSnapshot(
                    state=aggregated_state.state,
                    confidence=aggregated_state.confidence,
                    timestamp=datetime.utcnow(),
                    checker_results=checker_results
                )
                self._state.state_history.append(snapshot)
                
                # Limitar tamaño del historial (mantener últimos 100)
                if len(self._state.state_history) > 100:
                    self._state.state_history = self._state.state_history[-100:]
                
                # 5. Verificar condiciones de terminación
                if self._should_terminate(aggregated_state):
                    await self._terminate(aggregated_state)
                    break
                
                # 6. Esperar intervalo
                await asyncio.sleep(self._state.check_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in watcher loop for {self._state.event_id}: {e}", exc_info=True)
                await self._handle_error(e)
                await asyncio.sleep(5.0)  # Backoff en error
    
    async def _run_checkers(self) -> List[CheckerResult]:
        """
        Ejecuta todos los checkers en paralelo.
        
        Returns:
            Lista de resultados de checkers
        """
        if not self._checkers:
            return []
        
        # Obtener external_event_id del descriptor
        external_event_id = self.event_descriptor.canonical_event_id or self.event_descriptor.market_id
        
        # Ejecutar checkers en paralelo
        results = await self.checker_runner.run_checkers_parallel(
            self._checkers,
            external_event_id,
            credentials_map=None  # TODO: Obtener credenciales desde SecretService
        )
        
        return results
    
    async def _handle_state_transition(self, new_state):
        """
        Maneja transición de estado.
        
        Args:
            new_state: Nuevo estado agregado
        """
        old_state = self._state.last_state
        logger.info(
            f"State transition for event {self._state.event_id}: "
            f"{old_state} → {new_state.state} (confidence: {new_state.confidence:.2f})"
        )
        
        # Actualizar estado del lifecycle manager
        if new_state.state == EventStateType.FINISHED_DETECTED:
            self._state.status = WatcherStatus.FINISHED_DETECTED
        elif new_state.state == EventStateType.FINISHED_CONFIRMED:
            self._state.status = WatcherStatus.FINISHED_CONFIRMED
        elif new_state.state == EventStateType.LIVE:
            self._state.status = WatcherStatus.LIVE_MONITORING
        
        # Notificar al lifecycle manager
        await self.lifecycle_manager.on_state_transition(self._state.event_id, new_state)
    
    async def _handle_error(self, error: Exception):
        """Maneja errores en el watcher."""
        self._state.check_failures += 1
        self._state.status = WatcherStatus.ERROR_RETRYING
        
        logger.error(
            f"Error in watcher {self._state.event_id}: {error} "
            f"(failures: {self._state.check_failures})"
        )
        
        # Si hay demasiados fallos consecutivos, terminar
        if self._state.check_failures > 10:
            logger.error(f"Too many failures for watcher {self._state.event_id}, terminating")
            await self._terminate(None)
    
    def _should_terminate(self, aggregated_state) -> bool:
        """
        Verifica si el watcher debe terminar.
        
        Args:
            aggregated_state: Estado agregado actual
        
        Returns:
            True si debe terminar
        """
        # 1. Evento confirmado FINISHED
        if aggregated_state.state == EventStateType.FINISHED_CONFIRMED:
            return True
        
        # 2. Timeout máximo
        age = datetime.utcnow() - self._state.created_at
        if age > timedelta(hours=self._state.max_duration_hours):
            return True
        
        # 3. Error crítico persistente
        if self._state.check_failures > 10:
            return True
        
        # 4. No hay mercados asociados
        if not self._state.markets:
            return True
        
        return False
    
    async def _terminate(self, final_state):
        """
        Termina el watcher y limpia recursos.
        
        Args:
            final_state: Estado final (opcional)
        """
        self._active = False
        self._state.status = WatcherStatus.TERMINATED
        
        if final_state and final_state.finished_at:
            self._state.finished_at = final_state.finished_at
        else:
            self._state.finished_at = datetime.utcnow()
        
        logger.info(
            f"Terminated watcher for event {self._state.event_id} "
            f"(final state: {final_state.state if final_state else 'ERROR'})"
        )
        
        # Notificar al lifecycle manager
        await self.lifecycle_manager.on_watcher_terminated(self._state.event_id, self._state)

