"""
Wallets API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.wallet import Wallet
from app.api.auth import get_current_user, get_admin_user
from app.api.auth import User
from app.core.wallet import wallet_service
from app.core.execution import execution
from cryptography.fernet import Fernet
from uuid import UUID
from datetime import datetime

router = APIRouter(prefix="/wallets", tags=["wallets"])


class WalletCreate(BaseModel):
    label: str
    address: str
    private_key: str


class WalletActivate(BaseModel):
    confirm: bool = True
    cancel_open_orders: bool = True


@router.get("")
async def get_wallets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """List all wallets (admin only)."""
    wallets = db.query(Wallet).all()
    
    return [
        {
            "id": str(wallet.id),
            "label": wallet.label,
            "address": wallet.address,
            "active": wallet.active,
            "created_at": wallet.created_at.isoformat(),
            "updated_at": wallet.updated_at.isoformat(),
        }
        for wallet in wallets
    ]


@router.post("")
async def create_wallet(
    wallet_data: WalletCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Create new wallet (admin only)."""
    # Encrypt private key
    cipher = wallet_service._cipher
    encrypted_key = cipher.encrypt(wallet_data.private_key.encode())
    
    wallet = Wallet(
        label=wallet_data.label,
        address=wallet_data.address,
        encrypted_private_key=encrypted_key,
        active=False,  # New wallets are inactive by default
    )
    
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    
    return {
        "id": str(wallet.id),
        "label": wallet.label,
        "address": wallet.address,
        "active": wallet.active,
    }


@router.put("/{wallet_id}/activate")
async def activate_wallet(
    wallet_id: UUID,
    activate: WalletActivate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Activate a wallet (admin only)."""
    if not activate.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required"
        )
    
    # Set active wallet
    success = wallet_service.set_active_wallet(wallet_id, activate.cancel_open_orders)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to activate wallet"
        )
    
    # Cancel open orders if requested
    if activate.cancel_open_orders:
        await execution._cancel_all_open_orders()
    
    return {"status": "activated"}


@router.get("/active")
async def get_active_wallet(
    current_user: User = Depends(get_current_user),
):
    """Get active wallet."""
    wallet = wallet_service.get_active_wallet()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active wallet"
        )
    
    return {
        "id": str(wallet["id"]),
        "label": wallet["label"],
        "address": wallet["address"],
        "active": True,
    }


@router.delete("/{wallet_id}")
async def delete_wallet(
    wallet_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Delete wallet (admin only, cannot delete if active)."""
    wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    
    if wallet.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete active wallet. Deactivate it first."
        )
    
    db.delete(wallet)
    db.commit()
    
    return {"status": "deleted"}

