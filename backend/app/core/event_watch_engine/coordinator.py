"""
Event Watch Coordinator - Coordinador principal del Event Watch Engine.

Según especificación en docs/services/event_watch_engine.md
"""
import asyncio
import logging
from typing import Dict, List, Optional
from uuid import UUID
from app.core.event_watch_engine.models import (
    WatchEngineConfig, WatcherState, EventState
)
from app.core.event_watch_engine.lifecycle_manager import LifecycleManager
from app.core.event_watch_engine.watcher import Watcher
from app.core.event_mapping_layer.models import EventDescriptor

logger = logging.getLogger(__name__)


class EventWatchCoordinator:
    """
    Coordinador principal del Event Watch Engine.
    
    Responsabilidades:
    - Recibir EventDescriptors del Mapping Layer
    - Crear o reutilizar watchers
    - Gestionar límites (max watchers activos)
    - Limpiar watchers terminados
    - Notificar cambios de estado
    """
    
    def __init__(self, config: Optional[WatchEngineConfig] = None):
        """
        Inicializa el coordinador.
        
        Args:
            config: Configuración del Watch Engine (opcional)
        """
        self.config = config or WatchEngineConfig()
        self.lifecycle_manager = LifecycleManager()
        self._lock = asyncio.Lock()
    
    async def register_event(
        self,
        event_descriptor: EventDescriptor,
        market_id: UUID
    ) -> Optional[Watcher]:
        """
        Registra un evento para monitoreo.
        
        Si ya existe un watcher para este evento, agrega el mercado al watcher existente.
        Si no existe, crea un nuevo watcher.
        
        Args:
            event_descriptor: Descriptor del evento del Mapping Layer
            market_id: ID del mercado que depende de este evento
        
        Returns:
            Watcher creado o existente, o None si no se pudo crear
        """
        async with self._lock:
            # Verificar límite de watchers activos
            active_watchers = len(self.lifecycle_manager.get_all_watchers())
            if active_watchers >= self.config.max_watchers_active:
                logger.warning(
                    f"Max watchers limit reached ({self.config.max_watchers_active}), "
                    f"cannot register new event {event_descriptor.market_id}"
                )
                return None
            
            # Obtener event_id único (canonical_event_id o market_id como fallback)
            event_id = event_descriptor.canonical_event_id or event_descriptor.market_id
            
            # Verificar si ya existe un watcher para este evento
            existing_watcher = self.lifecycle_manager.get_watcher(event_id)
            if existing_watcher:
                # Agregar mercado al watcher existente
                existing_watcher.add_market(market_id)
                logger.info(
                    f"Added market {market_id} to existing watcher for event {event_id}"
                )
                return existing_watcher
            
            # Crear nuevo watcher
            try:
                watcher = Watcher(
                    event_descriptor=event_descriptor,
                    config=self.config,
                    lifecycle_manager=self.lifecycle_manager
                )
                
                # Agregar mercado al watcher
                watcher.add_market(market_id)
                
                # Registrar en lifecycle manager
                if not self.lifecycle_manager.register_watcher(watcher):
                    logger.error(f"Failed to register watcher for event {event_id}")
                    return None
                
                # Iniciar watcher
                await watcher.start()
                
                logger.info(
                    f"Registered new watcher for event {event_id} "
                    f"(type: {event_descriptor.event_type}, market: {market_id})"
                )
                
                return watcher
                
            except Exception as e:
                logger.error(f"Error creating watcher for event {event_id}: {e}", exc_info=True)
                return None
    
    async def unregister_event(self, event_id: str, market_id: Optional[UUID] = None) -> bool:
        """
        Desregistra un evento o remueve un mercado de un watcher.
        
        Args:
            event_id: ID del evento
            market_id: ID del mercado a remover (opcional, si no se proporciona, se desregistra todo el watcher)
        
        Returns:
            True si se desregistró exitosamente
        """
        async with self._lock:
            watcher = self.lifecycle_manager.get_watcher(event_id)
            if not watcher:
                return False
            
            if market_id:
                # Remover solo el mercado
                watcher.remove_market(market_id)
                
                # Si no quedan mercados, terminar el watcher
                state = watcher.get_state()
                if not state.markets:
                    await watcher.stop()
                    self.lifecycle_manager.unregister_watcher(event_id)
                    logger.info(f"Terminated watcher for event {event_id} (no markets left)")
                else:
                    logger.info(f"Removed market {market_id} from watcher {event_id}")
                
                return True
            else:
                # Desregistrar todo el watcher
                await watcher.stop()
                self.lifecycle_manager.unregister_watcher(event_id)
                logger.info(f"Unregistered watcher for event {event_id}")
                return True
    
    async def get_active_watchers(self) -> List[WatcherState]:
        """
        Obtiene todos los watchers activos.
        
        Returns:
            Lista de estados de watchers
        """
        watchers = self.lifecycle_manager.get_all_watchers()
        return [watcher.get_state() for watcher in watchers.values()]
    
    async def get_watcher(self, event_id: str) -> Optional[WatcherState]:
        """
        Obtiene el estado de un watcher específico.
        
        Args:
            event_id: ID del evento
        
        Returns:
            Estado del watcher o None si no existe
        """
        watcher = self.lifecycle_manager.get_watcher(event_id)
        if watcher:
            return watcher.get_state()
        return None
    
    async def cleanup_finished_watchers(self):
        """
        Limpia watchers terminados que exceden la edad máxima.
        
        Se debe llamar periódicamente para evitar acumulación de watchers terminados.
        """
        async with self._lock:
            self.lifecycle_manager.cleanup_finished_watchers(
                max_age_hours=self.config.max_watcher_age_hours
            )
    
    async def stop_all(self):
        """Detiene todos los watchers (para shutdown)."""
        async with self._lock:
            watchers = self.lifecycle_manager.get_all_watchers()
            tasks = [watcher.stop() for watcher in watchers.values()]
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("Stopped all watchers")

