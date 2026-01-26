"""
StrategyEvent model - Asignación de eventos a estrategias.

Relación many-to-many entre Strategy y Event con configuración adicional.
"""
from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class StrategyEvent(BaseModel):
    """
    StrategyEvent model - Asignación de evento a estrategia.
    
    Una estrategia puede observar múltiples eventos.
    Un evento puede ser observado por múltiples estrategias.
    """
    
    __tablename__ = "strategy_events"
    
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    
    # Estado de observación
    observation_started_at = Column(DateTime, nullable=True)
    observation_ended_at = Column(DateTime, nullable=True)
    
    # Configuración específica para este evento (JSONB)
    event_config = Column(JSONB, nullable=True)  # Overrides de configuración para este evento específico
    
    # Relationships
    strategy = relationship("Strategy", back_populates="strategy_events")
    event = relationship("Event")
    
    __table_args__ = (
        UniqueConstraint('strategy_id', 'event_id', name='uq_strategy_event'),
    )

