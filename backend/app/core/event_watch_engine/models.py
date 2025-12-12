"""
Modelos de datos para Event Watch Engine.

Según especificación en docs/services/event_watch_engine.md
"""
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
from uuid import UUID
from enum import Enum
from app.core.checkers.base import CheckerResult


class WatcherStatus(str, Enum):
    """Estados del watcher."""
    INITIALIZING = "INITIALIZING"
    LIVE_MONITORING = "LIVE_MONITORING"
    FINISHED_DETECTED = "FINISHED_DETECTED"
    FINISHED_CONFIRMED = "FINISHED_CONFIRMED"
    TERMINATED = "TERMINATED"
    ERROR_RETRYING = "ERROR_RETRYING"


class EventStateType(str, Enum):
    """Tipos de estado del evento."""
    LIVE = "LIVE"
    FINISHED_CONFIRMED = "FINISHED_CONFIRMED"
    FINISHED_UNCONFIRMED = "FINISHED_UNCONFIRMED"
    UNKNOWN = "UNKNOWN"


class StateSnapshot(BaseModel):
    """Snapshot del estado en un momento dado."""
    state: EventStateType
    confidence: float
    timestamp: datetime
    checker_results: List[CheckerResult] = []


class EventState(BaseModel):
    """
    Estado agregado del evento.
    
    Según especificación en docs/services/event_watch_engine.md
    """
    event_id: str
    state: EventStateType
    confidence: float  # 0.0 - 1.0
    sources: Dict[str, str] = {}  # { "espn": "FINISHED", "flashscore": "FINISHED" }
    last_update: datetime
    finished_at: Optional[datetime] = None
    checker_results: List[CheckerResult] = []
    trace_id: Optional[UUID] = None


class WatcherState(BaseModel):
    """
    Estado interno de un watcher.
    
    Según especificación en docs/services/event_watch_engine.md
    """
    # Identificadores
    event_id: str
    event_type: str
    trace_id: UUID
    
    # Mercados asociados
    markets: List[UUID] = []
    
    # Estado actual
    status: WatcherStatus
    last_state: EventStateType
    confidence: float
    state_history: List[StateSnapshot] = []
    
    # Métricas
    last_check_latency_ms: float = 0.0
    check_failures: int = 0
    total_checks: int = 0
    
    # Timestamps
    created_at: datetime
    last_update: datetime
    finished_at: Optional[datetime] = None
    
    # Checker results
    last_checker_results: List[CheckerResult] = []
    
    # Configuración
    check_interval_seconds: int
    max_duration_hours: int = 48


class WatchEngineConfig(BaseModel):
    """Configuración del Watch Engine."""
    # Frecuencias de actualización por tipo
    check_frequency_sports: int = 3  # segundos
    check_frequency_politics: int = 60  # segundos
    check_frequency_crypto: int = 12  # segundos
    check_frequency_finance: int = 60  # segundos
    check_frequency_weather: int = 600  # segundos (10 minutos)
    
    # Reglas de quorum
    min_checkers_for_confirmed: int = 2  # Mínimo de checkers para FINISHED_CONFIRMED
    min_confidence_threshold: float = 0.8  # Confianza mínima por checker
    
    # Límites
    max_watchers_active: int = 300  # Máximo de watchers simultáneos
    max_watcher_age_hours: int = 24  # Máxima edad de un watcher
    
    # Timeouts
    checker_timeout_seconds: float = 5.0  # Timeout por checker
    watcher_max_duration_hours: int = 48  # Duración máxima de un watcher

