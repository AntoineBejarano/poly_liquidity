"""
Modelos de datos para Strategy Engine.

Según especificación en docs/services/strategy.md
"""
from pydantic import BaseModel
from typing import Dict, Optional, Any
from uuid import UUID
from datetime import datetime


class MarketState(BaseModel):
    """
    Estado del mercado desde el Scanner.
    
    Según especificación en docs/services/strategy.md
    """
    market_id: UUID
    best_bid: float  # Mejor precio de compra
    best_ask: float  # Mejor precio de venta
    last_price: float  # Último precio transado
    spread: float  # Diferencia entre ask y bid
    outcomes: list[str] = ["YES", "NO"]  # ["YES", "NO"]
    open_interest: Optional[float] = None  # Interés abierto
    orderbook_snapshot: Optional[Dict[str, Any]] = None  # Profundidad del orderbook
    close_time: Optional[datetime] = None  # Fecha/hora de cierre del mercado
    volume_24h: Optional[float] = None  # Volumen en últimas 24h


class EventState(BaseModel):
    """
    Estado del evento desde el Watch Engine.
    
    Según especificación en docs/services/strategy.md
    """
    event_status: str  # "LIVE" | "FINISHED_CONFIRMED" | "FINISHED_UNCONFIRMED" | "UNKNOWN"
    confidence_score: float  # 0.0 - 1.0
    sources_state: Dict[str, str] = {}  # { "espn": "FINISHED", "flashscore": "FINISHED" }
    event_finished_at: Optional[datetime] = None  # Cuándo terminó el evento
    last_update: datetime
    event_type: Optional[str] = None  # "sports", "politics", etc.


class StrategyConfig(BaseModel):
    """
    Configuración de la estrategia.
    
    Según especificación en docs/services/strategy.md
    """
    min_entry_price: float = 0.97  # Precio mínimo para entrar
    max_entry_spread: float = 0.02  # Spread máximo permitido
    safety_tick: float = 0.001  # Tick de seguridad para precio
    target_edge: float = 0.01  # Margen objetivo hacia 1.0
    max_order_size: float = 5000.0  # Tamaño máximo por orden (USDC)
    max_exposure_per_market: float = 10000.0  # Exposición máxima por mercado
    max_global_exposure: float = 200000.0  # Exposición global máxima
    latency_mode: str = "GREEN"  # "GREEN" | "YELLOW" | "RED"
    aggressive_mode: bool = False  # Permitir FINISHED_UNCONFIRMED
    min_liquidity_required: float = 1000.0  # Liquidez mínima requerida
    
    # Configuración de tamaño de apuesta (mutuamente excluyentes)
    bet_size_mode: str = "fixed_range"  # "percentage" | "fixed_range"
    bet_size_percentage: Optional[float] = None  # Porcentaje del bank (ej: 5.0 = 5%)
    bet_size_min: Optional[float] = None  # Tamaño mínimo en USDC (cuando mode = "fixed_range")
    bet_size_max: Optional[float] = None  # Tamaño máximo en USDC (cuando mode = "fixed_range")


class OrderIntent(BaseModel):
    """
    Intención de orden antes de validación de riesgo.
    
    Según especificación en docs/services/strategy.md
    
    ⚠️ IMPORTANTE: Ahora opera sobre Events, no Markets.
    - event_id: ID del Event (instancia tradeable)
    - outcome: "YES" o "NO" o "UP" o "DOWN" (resultado dentro del Event)
    - market_id: Se obtiene del Event para cálculos de exposición (agregado)
    """
    event_id: UUID  # ID del Event (instancia tradeable)
    outcome: str  # "YES" o "NO" o "UP" o "DOWN"
    side: str = "BUY"  # Solo compras en esta estrategia
    price: float  # Precio objetivo
    size: float  # Tamaño en shares
    reason: str  # Razón de la entrada
    metadata: Dict[str, Any] = {}  # Metadata adicional (puede incluir market_id para exposición)
    trace_id: Optional[UUID] = None  # Para trazabilidad


class NoEntryReason(BaseModel):
    """
    Razón por la cual no se crea una orden.
    
    Según especificación en docs/services/strategy.md
    
    ⚠️ IMPORTANTE: Ahora opera sobre Events, no Markets.
    """
    event_id: UUID  # ID del Event
    reason: str  # "event_not_finished", "ask_price_too_low", "spread_too_wide", etc.
    details: Dict[str, Any] = {}  # Detalles específicos (puede incluir market_id)
    trace_id: Optional[UUID] = None  # Para trazabilidad

