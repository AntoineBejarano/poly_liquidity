"""
Lifecycle Manager - Gestiona el ciclo de vida de watchers.

Según especificación en docs/services/event_watch_engine.md
"""
import logging
from typing import Dict, Optional, TYPE_CHECKING
from datetime import datetime
from app.core.event_watch_engine.models import WatcherState, EventState

if TYPE_CHECKING:
    from app.core.event_watch_engine.watcher import Watcher

logger = logging.getLogger(__name__)


class LifecycleManager:
    """
    Gestiona el ciclo de vida de watchers.
    
    Responsabilidades:
    - Gestionar estados de watchers
    - Prevenir watchers duplicados
    - Limpiar watchers terminados
    - Notificar cambios de estado
    """
    
    def __init__(self):
        """Inicializa el Lifecycle Manager."""
        self._watchers: Dict[str, Watcher] = {}
        self._state_history: Dict[str, list] = {}  # event_id -> lista de estados
    
    def register_watcher(self, watcher: "Watcher") -> bool:
        """
        Registra un watcher.
        
        Args:
            watcher: Watcher a registrar
        
        Returns:
            True si se registró exitosamente, False si ya existe
        """
        event_id = watcher.get_state().event_id
        if event_id in self._watchers:
            logger.warning(f"Watcher for event {event_id} already exists")
            return False
        
        self._watchers[event_id] = watcher
        self._state_history[event_id] = []
        logger.info(f"Registered watcher for event {event_id}")
        return True
    
    def unregister_watcher(self, event_id: str) -> bool:
        """
        Desregistra un watcher.
        
        Args:
            event_id: ID del evento
        
        Returns:
            True si se desregistró exitosamente
        """
        if event_id not in self._watchers:
            return False
        
        del self._watchers[event_id]
        if event_id in self._state_history:
            del self._state_history[event_id]
        
        logger.info(f"Unregistered watcher for event {event_id}")
        return True
    
    def get_watcher(self, event_id: str) -> Optional["Watcher"]:
        """
        Obtiene un watcher por event_id.
        
        Args:
            event_id: ID del evento
        
        Returns:
            Watcher o None si no existe
        """
        return self._watchers.get(event_id)
    
    def get_all_watchers(self) -> Dict[str, "Watcher"]:
        """Obtiene todos los watchers activos."""
        return self._watchers.copy()
    
    async def on_state_transition(self, event_id: str, new_state: EventState):
        """
        Maneja transición de estado de un watcher.
        
        Args:
            event_id: ID del evento
            new_state: Nuevo estado
        """
        if event_id not in self._state_history:
            self._state_history[event_id] = []
        
        self._state_history[event_id].append({
            "state": new_state.state.value,
            "confidence": new_state.confidence,
            "timestamp": datetime.utcnow(),
            "sources": new_state.sources
        })
        
        logger.info(
            f"State transition for event {event_id}: "
            f"{new_state.state.value} (confidence: {new_state.confidence:.2f})"
        )
    
    async def on_watcher_terminated(self, event_id: str, final_state: WatcherState):
        """
        Maneja terminación de un watcher.
        
        Args:
            event_id: ID del evento
            final_state: Estado final del watcher
        """
        logger.info(
            f"Watcher terminated for event {event_id} "
            f"(final state: {final_state.last_state.value}, "
            f"total checks: {final_state.total_checks})"
        )
        
        # Limpiar del registro
        self.unregister_watcher(event_id)
    
    def cleanup_finished_watchers(self, max_age_hours: int = 24):
        """
        Limpia watchers terminados más antiguos que max_age_hours.
        
        Args:
            max_age_hours: Edad máxima en horas
        """
        now = datetime.utcnow()
        to_remove = []
        
        for event_id, watcher in self._watchers.items():
            state = watcher.get_state()
            if state.status.value == "TERMINATED":
                if state.finished_at:
                    age = now - state.finished_at
                    if age.total_seconds() > max_age_hours * 3600:
                        to_remove.append(event_id)
        
        for event_id in to_remove:
            self.unregister_watcher(event_id)
            logger.info(f"Cleaned up old watcher for event {event_id}")

