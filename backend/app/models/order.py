"""
Order model for Polymarket orders.
"""
from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Order(BaseModel):
    """Order model for Polymarket orders."""
    
    __tablename__ = "orders"
    
    polymarket_order_id = Column(String, nullable=True, index=True)
    market_id = Column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False, index=True)
    side = Column(String, nullable=False)  # BUY
    price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="NEW")  # NEW / PARTIALLY_FILLED / FILLED / CANCELLED
    filled_size = Column(Float, nullable=False, default=0.0)
    
    # Relationships
    market = relationship("Market", back_populates="orders")
    trades = relationship("Trade", back_populates="order", cascade="all, delete-orphan")

