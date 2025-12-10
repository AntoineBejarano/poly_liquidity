"""
Checker configuration model.
"""
from sqlalchemy import Column, String, Float, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class CheckerConfig(BaseModel):
    """Checker runtime configuration."""
    
    __tablename__ = "checker_configs"
    
    checker_id = Column(UUID(as_uuid=True), ForeignKey("event_checkers.id"), nullable=False, index=True)
    secret_name = Column(String, ForeignKey("secrets.name"), nullable=True)  # link to secret
    weight = Column(Float, nullable=False, default=1.0)  # for signal aggregation
    timeout_seconds = Column(Float, nullable=False, default=5.0)
    enabled = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    checker = relationship("EventChecker", back_populates="configs")
    secret = relationship("Secret", back_populates="checker_configs")

