"""
System configuration model.
"""
from sqlalchemy import Column, String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.models.base import BaseModel


class SystemConfig(BaseModel):
    """System configuration model."""
    
    __tablename__ = "system_config"
    
    key = Column(String, unique=True, nullable=False, index=True)  # ej. "tick_seconds", "min_candidate_price"
    value = Column(Text, nullable=False)  # serialized value (JSON or string)
    value_type = Column(String, nullable=False)  # "float", "int", "bool", "string"
    category = Column(String, nullable=False, index=True)  # "system", "risk", "scanner", "event_engine", "strategy", "execution"
    description = Column(String, nullable=True)
    updated_by = Column(String, ForeignKey("neon_auth.users_sync.id"), nullable=True)
    
    # Nuevos campos de la migración 005
    execution_mode = Column(String(50), nullable=True)  # "DRY_RUN", "PAPER", "LIVE"
    min_value = Column(String, nullable=True)  # Valor mínimo para validación
    max_value = Column(String, nullable=True)  # Valor máximo para validación
    is_readonly = Column(Boolean, nullable=False, server_default='false')  # Protección contra errores humanos
    requires_confirmation = Column(Boolean, nullable=False, server_default='false')  # Requiere confirmación antes de cambiar
    validation_rule = Column(JSONB, nullable=True)  # Reglas de validación complejas
    updated_at = Column(DateTime, nullable=True, server_default=func.now())  # Timestamp de última actualización

