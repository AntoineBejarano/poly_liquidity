"""
Market Enabled State model - solo guarda el estado enabled de los markets.

Esta es la ÚNICA información que se guarda sobre markets en nuestra DB.
Series y Markets se leen directamente de la API de Polymarket.
"""
from sqlalchemy import Column, String, Boolean, UniqueConstraint
from app.models.base import BaseModel


class MarketEnabledState(BaseModel):
    """
    Market Enabled State - solo guarda si un market está activado o no.
    
    Solo guardamos el estado enabled. Toda la demás información (nombre, categoría, etc.)
    se lee directamente de la API de Polymarket.
    """
    
    __tablename__ = "market_enabled_states"
    
    # ID del market en Polymarket (slug o ID único)
    polymarket_market_id = Column(String, unique=True, nullable=False, index=True)
    
    # Si el market está activado para escanear events
    enabled = Column(Boolean, nullable=False, default=False, index=True)
    
    __table_args__ = (
        UniqueConstraint('polymarket_market_id', name='uq_market_enabled_state'),
    )















