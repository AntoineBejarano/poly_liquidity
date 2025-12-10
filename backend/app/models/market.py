"""
Market model for Polymarket markets.
"""
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Market(BaseModel):
    """Market model from Polymarket."""
    
    __tablename__ = "markets"
    
    polymarket_id = Column(String, unique=True, nullable=False, index=True)
    question = Column(String, nullable=False)
    outcome = Column(String, nullable=False)  # YES/NO
    status = Column(String, nullable=False, default="OPEN")  # OPEN / RESOLVED / PAUSED
    last_price = Column(Float, nullable=True)
    resolution_outcome = Column(String, nullable=True)  # YES / NO / NULL
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    events = relationship("Event", back_populates="market", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="market", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="market", cascade="all, delete-orphan")
    exposures = relationship("Exposure", back_populates="market", cascade="all, delete-orphan")

