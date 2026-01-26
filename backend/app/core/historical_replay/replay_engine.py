"""
Replay Engine - Motor de replay de eventos históricos.

Según especificación en docs/services/historical_replay.md
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from app.core.historical_replay.event_store import EventStore

logger = logging.getLogger(__name__)


class ReplayEngine:
    """
    Motor de replay de eventos históricos.
    
    Permite reproducir eventos paso a paso, rewindear a timestamps,
    y reconstruir el estado del sistema en momentos pasados.
    """
    
    def __init__(self, event_store: EventStore):
        """
        Inicializa el Replay Engine.
        
        Args:
            event_store: Instancia de EventStore
        """
        self.event_store = event_store
    
    async def replay_market(
        self,
        market_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Reproduce eventos de un mercado.
        
        Args:
            market_id: ID del mercado
            start_time: Timestamp de inicio (opcional)
            end_time: Timestamp de fin (opcional)
            
        Returns:
            Lista de eventos ordenados por timestamp
        """
        events = await self.event_store.get_timeline(
            market_id=market_id,
            start_time=start_time,
            end_time=end_time
        )
        
        # Calcular tiempos relativos
        if events:
            first_timestamp = datetime.fromisoformat(events[0]["timestamp"].replace("Z", "+00:00"))
            
            for event in events:
                event_timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                relative_time_ms = int((event_timestamp - first_timestamp).total_seconds() * 1000)
                
                # Formatear tiempo relativo (HH:MM:SS)
                total_seconds = int((event_timestamp - first_timestamp).total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                relative_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                
                event["relative_time_ms"] = relative_time_ms
                event["t"] = relative_time_str
        
        return events
    
    async def replay_step_by_step(
        self,
        market_id: str,
        step: int
    ) -> Optional[Dict[str, Any]]:
        """
        Reproduce un paso específico.
        
        Args:
            market_id: ID del mercado
            step: Número de paso (0-indexed)
            
        Returns:
            Evento en ese paso, o None si no existe
        """
        events = await self.event_store.get_timeline(market_id=market_id)
        
        if 0 <= step < len(events):
            event = events[step]
            
            # Reconstruir estado del sistema en ese paso
            event_timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
            system_state = await self.event_store.rewind_to_timestamp(event_timestamp)
            
            return {
                "step": step,
                "event": event,
                "system_state_at_step": system_state
            }
        
        return None
    
    async def rewind_to_timestamp(
        self,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Reconstruye estado del sistema en un timestamp.
        
        Args:
            timestamp: Timestamp al que rewindear
            
        Returns:
            Estado reconstruido del sistema
        """
        return await self.event_store.rewind_to_timestamp(timestamp)
    
    async def replay_event(
        self,
        event_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Reproduce eventos relacionados con un evento externo.
        
        Args:
            event_id: ID del evento externo
            start_time: Timestamp de inicio (opcional)
            end_time: Timestamp de fin (opcional)
            
        Returns:
            Diccionario con mappings, watcher_events, checker_results
        """
        events = await self.event_store.get_timeline(
            event_id=event_id,
            start_time=start_time,
            end_time=end_time
        )
        
        # Clasificar eventos por tipo
        result = {
            "event_id": event_id,
            "mappings": [],
            "watcher_events": [],
            "checker_results": []
        }
        
        for event in events:
            event_type = event.get("type", "")
            
            if event_type.startswith("event_mapping_"):
                result["mappings"].append(event)
            elif event_type.startswith("watcher_"):
                result["watcher_events"].append(event)
            elif event_type.startswith("checker_"):
                result["checker_results"].append(event)
        
        return result

