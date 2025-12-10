"""
Event checker model for dynamic checker system.
"""
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class EventChecker(BaseModel):
    """Event checker definition."""
    
    __tablename__ = "event_checkers"
    
    implementation_key = Column(String, nullable=False, index=True)  # selects which checker class to instantiate
    category = Column(String, nullable=False, index=True)  # sports, crypto, politics, etc.
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    configs = relationship("CheckerConfig", back_populates="checker", cascade="all, delete-orphan")

