"""
Position model for market positions.
"""
from sqlalchemy import Column, Float, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Position(BaseModel):
    """Position model for market positions."""
    
    __tablename__ = "positions"
    
    market_id = Column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False, unique=True, index=True)
    size = Column(Float, nullable=False, default=0.0)
    avg_price = Column(Float, nullable=False)
    resolved = Column(Boolean, nullable=False, default=False)
    payout = Column(Float, nullable=True)  # payout when market resolves
    
    # Relationships
    market = relationship("Market", back_populates="positions")

