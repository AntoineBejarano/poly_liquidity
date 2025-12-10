"""
System configuration model.
"""
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel


class SystemConfig(BaseModel):
    """System configuration model."""
    
    __tablename__ = "system_config"
    
    key = Column(String, unique=True, nullable=False, index=True)  # ej. "tick_seconds", "min_candidate_price"
    value = Column(Text, nullable=False)  # serialized value (JSON or string)
    value_type = Column(String, nullable=False)  # "float", "int", "bool", "string"
    category = Column(String, nullable=False, index=True)  # "system", "risk", "scanner", "event_engine"
    description = Column(String, nullable=True)
    updated_by = Column(String, ForeignKey("neon_auth.users_sync.id"), nullable=True)

