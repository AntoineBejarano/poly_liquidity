"""
Tag model for Polymarket tags.

Tags: metadatos transversales de clasificación.
Ejemplos: crypto, bitcoin, 15m, up-down, sports
NO es tradeable. Solo se usa para búsqueda, filtrado y agrupación visual.
"""
from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Tag(BaseModel):
    """
    Tag model - metadatos transversales de clasificación.
    
    Un Tag es un metadato que puede aplicarse a múltiples Markets.
    Ejemplos:
    - crypto
    - bitcoin
    - 15m
    - up-down
    - sports
    
    NO es tradeable.
    NO define estructura.
    NO define frecuencia.
    NO tiene lógica propia.
    
    Solo se usa para:
    - Búsqueda
    - Filtrado
    - Agrupación visual
    """
    
    __tablename__ = "tags"
    
    # ID del tag en Polymarket (único)
    polymarket_tag_id = Column(String, unique=True, nullable=False, index=True)
    
    # Nombre del tag (ej. "crypto")
    name = Column(String, nullable=False)
    
    # Slug del tag (para URLs)
    slug = Column(String, nullable=True, index=True)
    
    # Label del tag (puede diferir del name)
    label = Column(String, nullable=True)
    
    # ⚠️ NO usar 'metadata' - es nombre reservado en SQLAlchemy
    # Datos raw de Polymarket API
    polymarket_payload = Column(JSON, nullable=True)
    
    # Relationships
    markets = relationship("MarketTag", back_populates="tag", cascade="all, delete-orphan")

