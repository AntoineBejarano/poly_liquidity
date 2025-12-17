"""
ExternalDataSource model - Fuentes de datos externas configurables.

Cualquier fuente externa (Pinnacle, Bet365, APIs custom, etc.) configurable desde frontend.
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ExternalDataSource(BaseModel):
    """
    ExternalDataSource model - Fuente de datos externa.
    
    Configuración completa de una fuente externa:
    - Tipo de conector
    - Configuración (URLs, API keys, headers, proxies, etc.)
    - Estado de salud
    """
    
    __tablename__ = "external_data_sources"
    
    # Identificación
    name = Column(String, nullable=False)  # Nombre descriptivo (ej. "Pinnacle Sports API")
    connector_type = Column(String, nullable=False, index=True)  # "pinnacle", "bet365", "custom_api", etc.
    description = Column(Text, nullable=True)
    
    # Configuración del conector (JSONB)
    connector_config = Column(JSONB, nullable=False)  # URLs, API keys, headers, proxies, rate limits, etc.
    
    # Estado
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(String, nullable=True)  # "healthy", "degraded", "unhealthy"
    
    # Metadata
    created_by = Column(String, ForeignKey("neon_auth.users_sync.id"), nullable=True)
    
    # Relationships (se agregarán cuando creemos StrategyExternalDataSource)
    # strategy_sources = relationship("StrategyExternalDataSource", back_populates="external_data_source")

