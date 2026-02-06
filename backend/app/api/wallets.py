"""
Wallets API endpoints. Wallets y configuración Polymarket por usuario.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.wallet import Wallet
from app.api.auth import get_current_user, get_admin_user
from app.api.auth import User
from app.core.wallet import wallet_service
from uuid import UUID

router = APIRouter(prefix="/wallets", tags=["wallets"])


class WalletCreate(BaseModel):
    label: str
    address: str
    private_key: str


class WalletActivate(BaseModel):
    confirm: bool = True
    cancel_open_orders: bool = True


class PolymarketConfigUpdate(BaseModel):
    polymarket_proxy_address: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    api_passphrase: Optional[str] = None


def _user_id(current_user: User) -> str:
    return current_user.id


@router.get("")
async def get_wallets(
    current_user: User = Depends(get_current_user),
):
    """Lista las wallets del usuario actual."""
    wallets = wallet_service.list_wallets(user_id=_user_id(current_user))
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
    current_user: User = Depends(get_current_user),
):
    """Crea una wallet para el usuario actual."""
    try:
        wallet = wallet_service.create_wallet(
            label=wallet_data.label,
            address=wallet_data.address,
            private_key=wallet_data.private_key,
            user_id=_user_id(current_user),
        )
        return {
            "id": str(wallet.id),
            "label": wallet.label,
            "address": wallet.address,
            "active": wallet.active,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{wallet_id}/activate")
async def activate_wallet(
    wallet_id: UUID,
    activate: WalletActivate,
    current_user: User = Depends(get_current_user),
):
    """Activa una wallet del usuario. Requiere confirm y opcionalmente cancela órdenes abiertas."""
    if not activate.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required. Set 'confirm: true' in request body."
        )
    if activate.cancel_open_orders:
        import sys
        if 'app.main' in sys.modules:
            main_module = sys.modules['app.main']
            if hasattr(main_module, 'execution'):
                await main_module.execution._cancel_all_open_orders()
    success = wallet_service.set_active_wallet(
        wallet_id, cancel_open_orders=False, user_id=_user_id(current_user)
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to activate wallet. Wallet may not exist or not belong to you."
        )
    return {"status": "activated", "wallet_id": str(wallet_id)}


@router.get("/active")
async def get_active_wallet(
    current_user: User = Depends(get_current_user),
):
    """Devuelve la wallet activa del usuario (desde sus wallets en DB)."""
    wallet = wallet_service.get_active_wallet(user_id=_user_id(current_user))
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


@router.get("/polymarket-config")
async def get_polymarket_config(
    current_user: User = Depends(get_current_user),
):
    """Obtiene la configuración Polymarket del usuario (proxy, API keys)."""
    config = wallet_service.get_polymarket_config(_user_id(current_user))
    if not config:
        return {
            "polymarket_proxy_address": None,
            "api_key": None,
            "api_secret_configured": False,
            "api_passphrase_configured": False,
        }
    return {
        "polymarket_proxy_address": config.polymarket_proxy_address,
        "api_key": config.api_key,
        "api_secret_configured": bool(config.api_secret),
        "api_passphrase_configured": bool(config.api_passphrase),
    }


@router.put("/polymarket-config")
async def put_polymarket_config(
    body: PolymarketConfigUpdate,
    current_user: User = Depends(get_current_user),
):
    """Crea o actualiza la configuración Polymarket del usuario. Campos no enviados no se modifican."""
    config = wallet_service.set_polymarket_config(
        _user_id(current_user),
        polymarket_proxy_address=body.polymarket_proxy_address,
        api_key=body.api_key,
        api_secret=body.api_secret,
        api_passphrase=body.api_passphrase,
    )
    return {
        "polymarket_proxy_address": config.polymarket_proxy_address,
        "api_key": config.api_key,
        "api_secret_configured": bool(config.api_secret),
        "api_passphrase_configured": bool(config.api_passphrase),
    }


@router.delete("/{wallet_id}")
async def delete_wallet(
    wallet_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina una wallet del usuario (no puede estar activa). Admin puede eliminar cualquiera."""
    wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    is_admin = getattr(current_user, "role", None) == "admin"
    if not is_admin and wallet.user_id != _user_id(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your wallet")
    if wallet.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete active wallet. Deactivate it first."
        )
    db.delete(wallet)
    db.commit()
    return {"status": "deleted"}

