"""
Proxy model - Proxies configurables por usuario para estrategias.

Los proxies se asignan en la configuración de la estrategia (no a las cuentas).
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel


class Proxy(BaseModel):
    """
    Proxy model - Proxy configurable por usuario.
    
    Cada proxy pertenece a un usuario (created_by). Se usa en estrategias
    para enrutar conexiones (Polymarket, Telegram, PS3838, etc.).
    """
    
    __tablename__ = "proxies"
    
    name = Column(String, nullable=False)
    proxy_type = Column(String, nullable=False, default="SOCKS5")  # SOCKS5, HTTP, MTProto
    proxy_host = Column(String, nullable=False)
    proxy_port = Column(Integer, nullable=False)
    proxy_username = Column(String, nullable=True)
    encrypted_proxy_password = Column(LargeBinary, nullable=True)
    proxy_country = Column(String, nullable=True)
    
    validation_status = Column(String, nullable=True)  # healthy, unhealthy, unknown
    last_validation_at = Column(DateTime, nullable=True)
    validation_latency_ms = Column(Integer, nullable=True)
    
    created_by = Column(String, ForeignKey("neon_auth.users_sync.id"), nullable=True, index=True)
