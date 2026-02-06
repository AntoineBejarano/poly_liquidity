"""
Configuración de Polymarket por usuario (proxy, API keys).
Almacenada en DB para que cada usuario gestione sus credenciales desde la UI de wallets.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime
from app.models.base import Base


class UserPolymarketConfig(Base):
    """
    Credenciales y configuración Polymarket por usuario.
    No usa BaseModel: PK es user_id (String).
    """

    __tablename__ = "user_polymarket_config"

    user_id = Column(
        String,
        ForeignKey("neon_auth.users_sync.id"),
        primary_key=True,
        nullable=False,
    )
    polymarket_proxy_address = Column(String, nullable=True)
    api_key = Column(String, nullable=True)
    api_secret = Column(String, nullable=True)
    api_passphrase = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
