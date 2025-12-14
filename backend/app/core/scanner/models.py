"""
Modelos de datos para el Scanner Engine.
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class Outcome(BaseModel):
    """Outcome de un mercado binario."""
    name: str  # "YES" o "NO"
    price: float
    liquidity: float
    volume_24h: float


class EventMetadata(BaseModel):
    """Metadata del evento extraída del mercado."""
    detected_teams: List[str] = []
    detected_sport: Optional[str] = None
    event_start_time_parsed: Optional[datetime] = None
    timezone: Optional[str] = None
    raw_text: str = ""
    confidence: float = 0.0  # Confianza en el parsing (0.0 - 1.0)


class CandidateMarket(BaseModel):
    """Mercado candidato normalizado y enriquecido."""
    # Identificadores
    market_id: Optional[UUID] = None  # ID interno (se asigna al persistir)
    polymarket_id: str
    trace_id: UUID  # ID de trazabilidad del scan
    
    # Información básica
    question: str
    description: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    
    # Temporalidad
    created_at: datetime
    close_time: Optional[datetime] = None
    event_start_time: Optional[datetime] = None
    
    # Outcomes
    outcomes: List[Outcome]
    
    # Precios consolidados
    best_yes_price: float
    best_no_price: float
    spread: float
    
    # Estado
    status: str  # "OPEN", "CLOSED", "RESOLVED"
    is_binary: bool = True
    
    # Metadata del evento
    event_metadata: EventMetadata
    
    # Metadatos adicionales
    volume_24h: float = 0.0
    liquidity_total: float = 0.0
    market_hash: str  # Hash para tracking
    
    # Campos de Polymarket API (para CLOB/WebSocket)
    condition_id: Optional[str] = None  # Condition ID para WebSocket
    clob_token_ids: Optional[Dict[str, str]] = None  # {"YES": "token_id", "NO": "token_id"}
    
    # Timestamps
    scanned_at: datetime
    updated_at: datetime

