"""
Modelos de datos para Event Mapping Layer.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Literal
from uuid import UUID
from datetime import datetime


class EventType:
    """Tipos de eventos soportados."""
    SPORTS = "sports"
    POLITICS = "politics"
    CRYPTO = "crypto"
    FINANCE = "finance"
    WEATHER = "weather"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class EventDescriptor(BaseModel):
    """
    Descriptor de evento estandarizado.
    
    Resultado del mapping de un mercado de Polymarket a un evento real.
    """
    market_id: str
    mapped: bool  # True si se mapeó exitosamente
    event_type: Literal[
        "sports", "politics", "crypto",
        "finance", "weather", "custom", "unknown"
    ]
    mapping_confidence: float  # 0.0 - 1.0
    canonical_event_id: Optional[str] = None  # ej: "sports:nba:401585236"
    sources: List[str] = []  # ["espn"], ["ap_news"], etc.
    metadata: Dict[str, Any] = {}  # Schema depende de event_type
    reason: Optional[str] = None  # Por qué no se mapeó o baja confianza
    trace_id: UUID  # Para trazabilidad
    created_at: datetime = datetime.utcnow()

