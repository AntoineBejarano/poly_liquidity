"""
Trade model for order fills.
"""
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Trade(BaseModel):
    """Trade model for order fills."""
    
    __tablename__ = "trades"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    market_id = Column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False, index=True)
    fill_price = Column(Float, nullable=False)
    fill_size = Column(Float, nullable=False)
    direction = Column(String, nullable=False)  # BUY
    timestamp = Column(DateTime, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="trades")
    market = relationship("Market")

