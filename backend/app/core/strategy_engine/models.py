"""
Modelos de datos para Strategy Engine basado en grafos.

Reutiliza modelos existentes y agrega nuevos para el sistema de grafos.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from dataclasses import dataclass

# Reutilizar modelos existentes
from app.core.strategy.models import (
    OrderIntent,  # Ya tiene los campos nuevos (strategy_id, graph_execution_id)
    MarketState,
    EventState
)

# Exportar para uso futuro
__all__ = [
    "OrderIntent",
    "MarketState", 
    "EventState",
    "GraphExecutionContext",
    "GraphExecutionResult"
]


@dataclass
class GraphExecutionContext:
    """
    Contexto de ejecución para un grafo.
    
    Contiene información sobre la estrategia, evento, y servicios disponibles.
    """
    strategy_id: UUID
    event_id: UUID
    market_id: UUID
    trace_id: UUID
    state_cache: Any  # StateCacheService
    # Campos adicionales opcionales
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class GraphExecutionResult:
    """
    Resultado de la ejecución de un grafo.
    
    Contiene intents generados, traza de ejecución, y métricas.
    """
    intents: List[OrderIntent]
    execution_trace: List[Dict[str, Any]]
    duration_ms: float
    success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el resultado a diccionario."""
        return {
            "intents_count": len(self.intents),
            "execution_trace": self.execution_trace,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message
        }

# Nota: Los modelos de DB (Strategy, GraphExecution, etc.) se crearán en app/models/

