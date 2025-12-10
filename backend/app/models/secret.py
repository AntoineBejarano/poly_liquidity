"""
Secret model for checker credentials.
"""
from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Secret(BaseModel):
    """Secret model for checker API credentials."""
    
    __tablename__ = "secrets"
    
    name = Column(String, unique=True, nullable=False, index=True)  # identifier
    value = Column(Text, nullable=False)  # encrypted or plain (depending on security policy)
    description = Column(String, nullable=True)
    
    # Relationships
    checker_configs = relationship("CheckerConfig", back_populates="secret")

