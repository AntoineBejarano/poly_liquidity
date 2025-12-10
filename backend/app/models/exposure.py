"""
Exposure model for risk tracking.
"""
from sqlalchemy import Column, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Exposure(BaseModel):
    """Exposure model for risk tracking."""
    
    __tablename__ = "exposures"
    
    market_id = Column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False, index=True)
    notional = Column(Float, nullable=False)  # size * avg_price
    max_allowed = Column(Float, nullable=False)
    breached = Column(Boolean, nullable=False, default=False)
    timestamp = Column(DateTime, nullable=False)
    
    # Relationships
    market = relationship("Market", back_populates="exposures")

