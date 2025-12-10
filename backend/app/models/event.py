"""
Event model for external event tracking.
"""
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Event(BaseModel):
    """Event model for tracking external event states."""
    
    __tablename__ = "events"
    
    market_id = Column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False, index=True)
    external_event_id = Column(String, nullable=True)
    state = Column(String, nullable=False, default="LIVE")  # LIVE / FINISHED_UNCONFIRMED / FINISHED_CONFIRMED
    confidence = Column(Float, nullable=False, default=0.0)
    feed_a_confirmed = Column(Boolean, nullable=False, default=False)
    feed_b_confirmed = Column(Boolean, nullable=False, default=False)
    finished_at = Column(DateTime, nullable=True)
    
    # Relationships
    market = relationship("Market", back_populates="events")

