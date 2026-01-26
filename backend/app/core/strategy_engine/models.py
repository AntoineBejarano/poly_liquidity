"""
Modelos de datos para Strategy Engine basado en grafos.

Reutiliza modelos existentes y agrega nuevos para el sistema de grafos.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from dataclasses import dataclass
from decimal import Decimal
from pydantic import BaseModel as PydanticBaseModel, Field, validator

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
    "GraphExecutionResult",
    "PlanLeg",
    "PlanResult"
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
    db: Any = None  # SQLAlchemy Session
    graph_execution_id: Optional[UUID] = None
    plan_id: Optional[UUID] = None  # Para Execution Graphs
    last_plan_id: Optional[UUID] = None  # Para nodos que crean planes
    execution_engine: Any = None  # Execution Engine para Execution Graphs (DEPRECATED: usar trading_platform)
    trading_platform: Any = None  # TradingPlatform para Execution Graphs (nuevo)
    observability_config: Dict[str, Any] = None  # Configuración de observabilidad
    strategy: Any = None  # Strategy object (para acceder a pinned_node_versions)
    current_graph: Dict[str, Any] = None  # Grafo actual (para versionado)
    collected_state: Dict[str, Any] = None  # Estado recopilado por CollectStateNode
    signals: Dict[str, Any] = None  # Indicadores calculados por CalculateIndicatorsNode
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.observability_config is None:
            self.observability_config = {}
        if self.collected_state is None:
            self.collected_state = {}
        if self.signals is None:
            self.signals = {}
        if self.observability_config is None:
            self.observability_config = {}


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


class PlanLeg(PydanticBaseModel):
    """
    Un leg del plan (una orden a ejecutar).
    
    Representa una orden individual dentro de un ExecutionPlan.
    Para near-end: 1 leg. Para surebet: N legs.
    """
    leg_id: str = Field(..., description="Identificador único del leg dentro del plan")
    side: str = Field(..., description="Lado de la orden: BUY o SELL")
    outcome: str = Field(..., description="Outcome: YES, NO, UP, o DOWN")
    target_price: Decimal = Field(..., description="Precio objetivo")
    size: Decimal = Field(..., description="Tamaño en shares")
    size_usdc: Decimal = Field(..., description="Tamaño en USDC")
    
    # Estado del leg
    status: str = Field(default="PENDING", description="Estado: PENDING | EXECUTING | FILLED | PARTIAL | FAILED | CANCELLED")
    filled_size: Decimal = Field(default=Decimal("0"), description="Tamaño ejecutado en shares")
    filled_size_usdc: Decimal = Field(default=Decimal("0"), description="Tamaño ejecutado en USDC")
    
    # Metadata
    reason: str = Field(..., description="Razón de este leg")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contexto adicional")
    
    @validator('side')
    def validate_side(cls, v):
        if v not in ['BUY', 'SELL']:
            raise ValueError('side must be BUY or SELL')
        return v
    
    @validator('outcome')
    def validate_outcome(cls, v):
        if v not in ['YES', 'NO', 'UP', 'DOWN']:
            raise ValueError('outcome must be YES, NO, UP, or DOWN')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['PENDING', 'EXECUTING', 'FILLED', 'PARTIAL', 'FAILED', 'CANCELLED']
        if v not in valid_statuses:
            raise ValueError(f'status must be one of {valid_statuses}')
        return v
    
    def get_fill_ratio(self) -> Decimal:
        """Obtiene el ratio de fill (filled_size / size)."""
        if self.size == 0:
            return Decimal("0")
        return self.filled_size / self.size
    
    def is_complete(self) -> bool:
        """Verifica si el leg está completamente ejecutado."""
        return self.status == "FILLED" and self.filled_size >= self.size
    
    def is_partial(self) -> bool:
        """Verifica si el leg está parcialmente ejecutado."""
        return self.status == "PARTIAL" or (self.filled_size > 0 and self.filled_size < self.size)


# PlanResult movido a nodes/base.py para evitar import circular
