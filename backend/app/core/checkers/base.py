"""
Base checker interface for dynamic event detection.

Refactorizado según especificación en docs/services/checker_system.md
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from pydantic import BaseModel
from datetime import datetime, timezone


class CheckerResult(BaseModel):
    """
    Resultado de la ejecución de un checker.
    
    Según especificación en docs/services/checker_system.md
    """
    state: str  # "LIVE", "FINISHED", "UNKNOWN"
    confidence: float  # 0.0-1.0
    finished_at: Optional[datetime] = None
    raw_payload: Dict = {}  # Datos crudos para auditoría
    source: str  # Nombre del checker (ej: "espn_nba_scoreboard_v1")
    latency_ms: float = 0.0  # Tiempo de respuesta en milisegundos
    error: Optional[str] = None  # Si hubo error, descripción
    timestamp: datetime = datetime.now(timezone.utc)  # Cuándo se ejecutó


class BaseChecker(ABC):
    """
    Clase base abstracta para todos los checkers.
    
    Según especificación en docs/services/checker_system.md
    """
    
    # Propiedades de configuración (deben ser definidas por subclases)
    name: str = "unknown_checker"
    event_types: List[str] = []  # ["sports"], ["politics"], etc.
    weight: float = 1.0  # Importancia relativa en quorum (0-1)
    timeout_ms: int = 5000  # Timeout en milisegundos (default 5s)
    max_retries: int = 2  # Máximo de reintentos
    
    @abstractmethod
    async def check(
        self,
        external_event_id: str,
        credentials: Optional[Dict[str, str]] = None
    ) -> CheckerResult:
        """
        Verifica si el evento está finalizado.
        
        Args:
            external_event_id: ID del evento en la API externa
            credentials: Credenciales (API keys, tokens, etc.)
        
        Returns:
            CheckerResult con state, confidence, etc.
        
        Notas:
        - Debe ser idempotente
        - Debe respetar timeout (no bloquear event loop)
        - Debe retornar siempre un CheckerResult válido (nunca lanzar excepciones)
        - Debe normalizar errores a CheckerResult con state="UNKNOWN"
        """
        pass

