"""
StateCache model - Cache de estado para grafos.

Support Graphs escriben aquí.
Decision Graph lee desde aquí.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel


class StateCache(BaseModel):
    """
    StateCache model - Cache de estado.
    
    Almacena estado que:
    - Support Graphs escriben (async, cold path)
    - Decision Graph lee (sync, hot path)
    
    Clave típica: "event.{event_id}.market_state"
    """
    
    __tablename__ = "state_cache"
    
    # Clave del estado (ej: "event.{event_id}.market_state", "event.{event_id}.external_confirmation")
    cache_key = Column(String, nullable=False, unique=True, index=True)
    
    # Valor del estado (JSONB)
    cache_value = Column(JSONB, nullable=False)
    
    # Metadata
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=True, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True, index=True)
    
    # TTL
    expires_at = Column(DateTime, nullable=True, index=True)
    # Nota: created_at y updated_at vienen de BaseModel
    
    # Relationships
    strategy = relationship("Strategy")
    event = relationship("Event")

