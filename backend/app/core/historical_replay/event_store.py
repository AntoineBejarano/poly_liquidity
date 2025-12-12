"""
Event Store - Almacén de eventos históricos.

Según especificación en docs/services/historical_replay.md
"""
import logging
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.database import SessionLocal
from app.models.event_log import EventLog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Callable

logger = logging.getLogger(__name__)


class EventStore:
    """
    Almacén de eventos históricos.
    
    Soporta almacenamiento en SQLite y JSONL (opcional).
    """
    
    def __init__(
        self,
        storage_type: str = "sqlite",
        jsonl_path: Optional[str] = None,
        db_session_factory: Optional["Callable[[], Session]"] = None
    ):
        """
        Inicializa el Event Store.
        
        Args:
            storage_type: Tipo de almacenamiento ("sqlite" o "hybrid")
            jsonl_path: Ruta al archivo JSONL (opcional, solo para hybrid)
            db_session_factory: Factory para crear sesiones DB (opcional, para testing)
        """
        self.storage_type = storage_type
        self.jsonl_path = jsonl_path
        self.jsonl_file = None
        self._db_session_factory = db_session_factory or SessionLocal
        
        if storage_type == "hybrid" and jsonl_path:
            # Crear directorio si no existe
            jsonl_dir = Path(jsonl_path).parent
            jsonl_dir.mkdir(parents=True, exist_ok=True)
            
            # Abrir archivo en modo append
            self.jsonl_file = open(jsonl_path, "a", encoding="utf-8")
            logger.info(f"JSONL file opened: {jsonl_path}")
    
    def _validate_event(self, event: Dict[str, Any]) -> bool:
        """
        Valida que un evento tenga la estructura correcta.
        
        Args:
            event: Evento a validar
            
        Returns:
            True si es válido, False en caso contrario
        """
        required_fields = ["type", "timestamp"]
        for field in required_fields:
            if field not in event:
                logger.warning(f"Event missing required field: {field}")
                return False
        
        # Validar timestamp
        if not isinstance(event["timestamp"], (datetime, str)):
            logger.warning("Event timestamp must be datetime or ISO string")
            return False
        
        return True
    
    async def store_event(self, event: Dict[str, Any]) -> bool:
        """
        Almacena un evento.
        
        Args:
            event: Evento a almacenar (debe incluir type, timestamp, trace_id opcional, event_data)
            
        Returns:
            True si se almacenó correctamente, False en caso contrario
        """
        if not self._validate_event(event):
            return False
        
        # Normalizar timestamp
        if isinstance(event["timestamp"], str):
            try:
                timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
            except ValueError:
                logger.error(f"Invalid timestamp format: {event['timestamp']}")
                return False
        else:
            timestamp = event["timestamp"]
        
        # Extraer event_data (todo el evento excepto campos de metadatos)
        event_data = {
            k: v for k, v in event.items()
            if k not in ["type", "timestamp", "trace_id"]
        }
        
        # Almacenar en SQLite
        db = self._db_session_factory()
        try:
            event_log = EventLog(
                type=event["type"],
                timestamp=timestamp,
                trace_id=event.get("trace_id"),
                event_data=event_data,
                created_at=datetime.utcnow()
            )
            db.add(event_log)
            db.commit()
            logger.debug(f"Event stored in DB: {event['type']} at {timestamp}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing event in DB: {e}")
            return False
        finally:
            db.close()
        
        # Almacenar en JSONL si está habilitado
        if self.storage_type == "hybrid" and self.jsonl_file:
            try:
                json_line = json.dumps(event, default=str)
                self.jsonl_file.write(json_line + "\n")
                self.jsonl_file.flush()
            except Exception as e:
                logger.error(f"Error writing to JSONL: {e}")
        
        return True
    
    async def get_events(
        self,
        market_id: Optional[str] = None,
        event_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        trace_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene eventos filtrados.
        
        Args:
            market_id: Filtrar por market_id (en event_data)
            event_id: Filtrar por event_id (en event_data)
            event_type: Filtrar por tipo de evento
            start_time: Timestamp de inicio
            end_time: Timestamp de fin
            trace_id: Filtrar por trace_id
            limit: Límite de resultados
            
        Returns:
            Lista de eventos
        """
        db = self._db_session_factory()
        try:
            query = db.query(EventLog)
            
            # Filtros
            if event_type:
                query = query.filter(EventLog.type == event_type)
            
            if trace_id:
                query = query.filter(EventLog.trace_id == trace_id)
            
            if start_time:
                query = query.filter(EventLog.timestamp >= start_time)
            
            if end_time:
                query = query.filter(EventLog.timestamp <= end_time)
            
            # Ordenar por timestamp
            query = query.order_by(EventLog.timestamp.asc())
            
            if limit:
                query = query.limit(limit)
            
            event_logs = query.all()
            
            # Convertir a dicts y aplicar filtros adicionales en memoria
            events = []
            for log in event_logs:
                event = {
                    "type": log.type,
                    "timestamp": log.timestamp.isoformat(),
                    "trace_id": log.trace_id,
                    **log.event_data
                }
                
                # Filtros en event_data
                if market_id and event.get("market_id") != market_id:
                    continue
                
                if event_id and event.get("event_id") != event_id:
                    continue
                
                events.append(event)
            
            return events
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return []
        finally:
            db.close()
    
    async def get_timeline(
        self,
        market_id: Optional[str] = None,
        event_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene timeline ordenado de eventos.
        
        Args:
            market_id: Filtrar por market_id
            event_id: Filtrar por event_id
            start_time: Timestamp de inicio
            end_time: Timestamp de fin
            
        Returns:
            Lista de eventos ordenados por timestamp
        """
        events = await self.get_events(
            market_id=market_id,
            event_id=event_id,
            start_time=start_time,
            end_time=end_time
        )
        
        # Ya están ordenados por timestamp (asc) desde la query
        return events
    
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
        # Obtener todos los eventos hasta el timestamp
        events = await self.get_events(end_time=timestamp)
        
        # Reconstruir estado
        system_state = {
            "timestamp": timestamp.isoformat(),
            "exposure_total": 0.0,
            "runtime_mode": "GREEN",
            "active_markets": set(),
            "watchers_active": 0,
            "event_mappings": {},
            "risk_state": {
                "market_exposure": {},
                "global_exposure": 0.0
            }
        }
        
        # Procesar eventos para reconstruir estado
        for event in events:
            event_type = event.get("type", "")
            
            # Actualizar exposición
            if event_type == "risk_decision" and event.get("approved"):
                market_id = event.get("market_id")
                final_size = event.get("final_size", 0.0)
                price = event.get("price", 0.0)
                
                if market_id:
                    exposure = final_size * price
                    system_state["risk_state"]["market_exposure"][market_id] = \
                        system_state["risk_state"]["market_exposure"].get(market_id, 0.0) + exposure
                    system_state["risk_state"]["global_exposure"] += exposure
                    system_state["exposure_total"] += exposure
                    system_state["active_markets"].add(market_id)
            
            # Actualizar runtime mode
            if event_type == "runtime_mode_changed":
                system_state["runtime_mode"] = event.get("to", "GREEN")
            
            # Actualizar event mappings
            if event_type == "event_mapping_created":
                market_id = event.get("market_id")
                if market_id:
                    system_state["event_mappings"][market_id] = {
                        "event_id": event.get("event_id"),
                        "confidence": event.get("confidence", 0.0)
                    }
            
            # Actualizar watchers
            if event_type == "watcher_started":
                system_state["watchers_active"] += 1
            elif event_type == "watcher_stopped":
                system_state["watchers_active"] = max(0, system_state["watchers_active"] - 1)
        
        # Convertir sets a listas para JSON
        system_state["active_markets"] = list(system_state["active_markets"])
        system_state["risk_state"]["market_exposure"] = {
            k: v for k, v in system_state["risk_state"]["market_exposure"].items()
        }
        
        return system_state
    
    def close(self):
        """Cierra recursos (JSONL file)."""
        if self.jsonl_file:
            self.jsonl_file.close()
            self.jsonl_file = None

