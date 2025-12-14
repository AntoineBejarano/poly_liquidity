"""
Event model for Polymarket event instances.

Event: instancia concreta de un market (ej. "BTC Up or Down 18:00–18:15").
Es lo que realmente se tradea. Un Market puede tener múltiples Events.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Event(BaseModel):
    """
    Event model - instancia concreta de un Market.
    
    Un Event es una instancia tradeable de un Market.
    Ejemplo: "BTC Up or Down 18:00–18:15" es un Event del Market "BTC Up or Down – 15 min".
    
    Solo los Events se pueden tradear, nunca los Markets directamente.
    
    Nota:
    - id (UUID): Identificador interno de nuestra DB (heredado de BaseModel)
    - polymarket_event_id (String): ID del event en Polymarket
    """
    
    __tablename__ = "events"
    
    # ID del event en Polymarket (String, único)
    # ⚠️ Este es el ID externo de Polymarket, no nuestro UUID interno
    polymarket_event_id = Column(String, unique=True, nullable=False, index=True)
    
    # Market al que pertenece este event
    market_id = Column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False, index=True)
    
    # Tiempo de inicio del event
    start_time = Column(DateTime, nullable=False, index=True)
    
    # Tiempo de fin del event
    end_time = Column(DateTime, nullable=False, index=True)
    
    # Estado del event: UPCOMING, ACTIVE, FINISHED
    state = Column(String, nullable=False, default="UPCOMING", index=True)
    
    # ⚠️ NO usar 'metadata' - es nombre reservado en SQLAlchemy (colisiona con Base.metadata)
    # Datos raw de Polymarket API (puede contener question, outcomes, condition_id, clob_token_ids, etc.)
    polymarket_payload = Column(JSON, nullable=True)
    
    # Relationships
    market = relationship("Market", back_populates="events")

