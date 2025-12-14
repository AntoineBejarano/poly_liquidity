"""
Market model for Polymarket markets.

Market: plantilla / grupo lógico (ej. "BTC Up or Down – 15 min").
No es tradeable directamente. Solo es una plantilla que genera Events.
"""
from sqlalchemy import Column, String, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Market(BaseModel):
    """
    Market model - plantilla/grupo lógico de Polymarket.
    
    Un Market es una plantilla que puede generar múltiples Events.
    Ejemplo: "BTC Up or Down – 15 min" es un Market.
    No se puede tradear directamente sobre un Market.
    """
    
    __tablename__ = "markets"
    
    # ID del market en Polymarket (slug o ID único)
    polymarket_id = Column(String, unique=True, nullable=False, index=True)
    
    # Nombre del market (ej. "BTC Up or Down – 15 min")
    name = Column(String, nullable=False)
    
    # Categoría del market (ej. "crypto", "sports", "politics")
    category = Column(String, nullable=True, index=True)
    
    # Si el market está activado para escanear events
    enabled = Column(Boolean, nullable=False, default=False, index=True)
    
    # Series a la que pertenece este market (opcional)
    series_id = Column(UUID(as_uuid=True), ForeignKey("series.id"), nullable=True, index=True)
    
    # ⚠️ NO usar 'metadata' - es nombre reservado en SQLAlchemy (colisiona con Base.metadata)
    # Datos raw de Polymarket API (puede contener condition_id, clob_token_ids, etc.)
    polymarket_payload = Column(JSON, nullable=True)
    
    # Relationships
    series = relationship("Series", back_populates="markets")
    events = relationship("Event", back_populates="market", cascade="all, delete-orphan")
    tags = relationship("MarketTag", back_populates="market", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="market", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="market", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="market", cascade="all, delete-orphan")
    exposures = relationship("Exposure", back_populates="market", cascade="all, delete-orphan")

