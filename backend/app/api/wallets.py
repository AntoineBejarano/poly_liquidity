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
    current_user: User = Depends(get_admin_user),
):
    """List all wallets (admin only)."""
    wallets = wallet_service.list_wallets()
    
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
    current_user: User = Depends(get_admin_user),
):
    """Create new wallet (admin only)."""
    try:
        wallet = wallet_service.create_wallet(
            label=wallet_data.label,
            address=wallet_data.address,
            private_key=wallet_data.private_key
        )
        
        return {
            "id": str(wallet.id),
            "label": wallet.label,
            "address": wallet.address,
            "active": wallet.active,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{wallet_id}/activate")
async def activate_wallet(
    wallet_id: UUID,
    activate: WalletActivate,
    current_user: User = Depends(get_admin_user),
):
    """
    Activate a wallet (admin only).
    
    Requires explicit confirmation and optionally cancels open orders.
    """
    if not activate.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required. Set 'confirm: true' in request body."
        )
    
    # Cancel open orders BEFORE changing wallet (if requested)
    if activate.cancel_open_orders:
        # Import execution from main module (where it's instantiated)
        # This avoids circular imports while allowing access to the singleton
        import sys
        if 'app.main' in sys.modules:
            main_module = sys.modules['app.main']
            if hasattr(main_module, 'execution'):
                await main_module.execution._cancel_all_open_orders()
    
    # Set active wallet (this invalidates cache)
    success = wallet_service.set_active_wallet(wallet_id, cancel_open_orders=False)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to activate wallet. Wallet may not exist."
        )
    
    return {
        "status": "activated",
        "wallet_id": str(wallet_id)
    }


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
        "id": str(wallet.id),
        "label": wallet.label,
        "address": wallet.address,
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

