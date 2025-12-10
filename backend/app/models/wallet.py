"""
Wallet model for managing execution wallets.
"""
from sqlalchemy import Column, String, Boolean, LargeBinary
from app.models.base import BaseModel


class Wallet(BaseModel):
    """Wallet model for signing orders."""
    
    __tablename__ = "wallets"
    
    label = Column(String, nullable=False)  # "main", "backup", "testing"
    address = Column(String, nullable=False, index=True)  # public address
    encrypted_private_key = Column(LargeBinary, nullable=False)  # encrypted private key
    active = Column(Boolean, nullable=False, default=False, index=True)  # ONLY ONE TRUE

