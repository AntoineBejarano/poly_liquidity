"""
Series model for Polymarket series.

Series: contenedor lógico / agrupador de Markets relacionados.
Ej.: "Bitcoin Up or Down"
NO es tradeable. Solo se usa para organización y UX.
"""
from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Series(BaseModel):
    """
    Series model - contenedor lógico de Markets relacionados.
    
    Una Series agrupa múltiples Markets relacionados.
    Ejemplo: "Bitcoin Up or Down" es una Series que contiene:
    - Market: "BTC Up or Down – 15 min"
    - Market: "BTC Up or Down – 1h"
    
    NO es tradeable. Solo se usa para organización y UX.
    """
    
    __tablename__ = "series"
    
    # ID de la serie en Polymarket (único)
    polymarket_series_id = Column(String, unique=True, nullable=False, index=True)
    
    # Nombre de la serie (ej. "Bitcoin Up or Down")
    name = Column(String, nullable=False)
    
    # Slug de la serie (para URLs)
    slug = Column(String, nullable=True, index=True)
    
    # Descripción de la serie
    description = Column(String, nullable=True)
    
    # Tipo de serie (best-effort, puede ser NULL)
    # ej: "recurring", "one-time"
    series_type = Column(String, nullable=True)
    
    # Recurrencia (best-effort, puede venir implícito en nombre/tags)
    # ej: "15m", "1h", "daily"
    recurrence = Column(String, nullable=True)
    
    # ⚠️ NO usar 'metadata' - es nombre reservado en SQLAlchemy (colisiona con Base.metadata)
    # Datos raw de Polymarket API
    polymarket_payload = Column(JSON, nullable=True)
    
    # Relationships
    markets = relationship("Market", back_populates="series", cascade="all, delete-orphan")

