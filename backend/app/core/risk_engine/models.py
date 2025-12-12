"""
Modelos de datos para Risk Engine.

Según especificación en docs/services/risk_engine.md
"""
from pydantic import BaseModel
from typing import Dict, Set, Optional, Any, List
from uuid import UUID
from datetime import datetime


class ExposureState(BaseModel):
    """
    Estado de exposición por mercado.
    
    Según especificación en docs/services/risk_engine.md
    """
    market_id: UUID
    notional: float  # size * avg_price
    max_allowed: float  # Límite máximo
    breached: bool = False  # Si se excedió el límite
    updated_at: datetime = datetime.utcnow()


class RuntimeState(BaseModel):
    """
    Estado del sistema en tiempo de ejecución.
    
    Según especificación en docs/services/risk_engine.md
    """
    latency_status: str  # "GREEN" | "YELLOW" | "RED"
    system_load: float = 0.0  # Carga del sistema (0.0 - 1.0)
    recent_errors: List[Dict[str, Any]] = []  # Errores recientes
    watch_engine_health: Dict[str, Any] = {}  # Health checks del Watch Engine


class RiskConfig(BaseModel):
    """
    Configuración de riesgo.
    
    Según especificación en docs/services/risk_engine.md
    """
    max_market_exposure: float = 10000.0  # Exposición máxima por mercado
    max_global_exposure: float = 200000.0  # Exposición global máxima
    max_markets_active: int = 10  # Máximo de mercados activos
    max_order_size: float = 5000.0  # Tamaño máximo por orden
    min_order_size: float = 100.0  # Tamaño mínimo por orden
    latency_fail_mode: str = "strict"  # "strict" | "lenient"
    reduce_size_in_yellow: bool = True  # Reducir tamaño en YELLOW
    yellow_size_factor: float = 0.5  # Factor de reducción en YELLOW
    cancel_on_red: bool = True  # Cancelar órdenes en RED
    exposure_method: str = "notional"  # "notional" | "capital_at_risk" | "weighted"
    max_price_swing_pct: float = 0.05  # 5% máximo de cambio de precio
    max_swing_time_seconds: float = 10.0  # Tiempo máximo para detectar swing
    min_realistic_spread: float = 0.001  # Spread mínimo realista


class ApprovedOrderIntent(BaseModel):
    """
    Orden aprobada que pasó validación de riesgo.
    
    Según especificación en docs/services/risk_engine.md
    """
    market_id: UUID
    side: str
    price: float
    size: float  # Tamaño final (puede ser ajustado)
    original_size: float  # Tamaño original del intent
    adjustments: Dict[str, Any] = {}  # Ajustes aplicados
    trace_id: Optional[UUID] = None  # Para trazabilidad


class RejectedOrderIntent(BaseModel):
    """
    Orden rechazada con razón.
    
    Según especificación en docs/services/risk_engine.md
    """
    market_id: UUID
    reason: str  # Razón del rechazo
    limits: Dict[str, Any] = {}  # Límites que se excedieron
    trace_id: Optional[UUID] = None  # Para trazabilidad

