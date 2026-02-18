"""
Proxies API endpoints.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel

from app.database import get_db
from app.api.auth import get_current_user, User
from app.core.proxy_service import proxy_service

router = APIRouter(prefix="/proxies", tags=["proxies"])


class ProxyCreate(BaseModel):
    name: str
    proxy_type: str = "SOCKS5"
    proxy_host: str
    proxy_port: int
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    proxy_country: Optional[str] = None


class ProxyUpdate(BaseModel):
    name: Optional[str] = None
    proxy_type: Optional[str] = None
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    proxy_country: Optional[str] = None


def _user_id(current_user: User) -> str:
    return current_user.id


def _proxy_to_response(p):
    return {
        "id": str(p.id),
        "name": p.name,
        "proxy_type": p.proxy_type,
        "proxy_host": p.proxy_host,
        "proxy_port": p.proxy_port,
        "proxy_country": p.proxy_country,
        "validation_status": p.validation_status,
        "last_validation_at": p.last_validation_at.isoformat() if p.last_validation_at else None,
        "validation_latency_ms": p.validation_latency_ms,
        "created_at": p.created_at.isoformat() if p.created_at else "",
        "updated_at": p.updated_at.isoformat() if p.updated_at else "",
    }


@router.get("")
async def get_proxies(
    include_inactive: bool = Query(True, description="Incluir todos (no hay is_active en modelo)"),
    status: Optional[str] = Query(None, description="Filtrar por validation_status: healthy, unhealthy, unknown"),
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """Lista proxies del usuario (sin secretos)."""
    proxies = proxy_service.list_proxies(
        user_id=_user_id(current_user),
        status_filter=status,
    )
    return [_proxy_to_response(p) for p in proxies]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_proxy(
    body: ProxyCreate,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Crea un proxy para el usuario."""
    proxy = proxy_service.create_proxy(
        user_id=_user_id(current_user),
        name=body.name,
        proxy_type=body.proxy_type or "SOCKS5",
        proxy_host=body.proxy_host,
        proxy_port=body.proxy_port,
        proxy_username=body.proxy_username,
        proxy_password=body.proxy_password,
        proxy_country=body.proxy_country,
    )
    return _proxy_to_response(proxy)


@router.get("/{proxy_id}")
async def get_proxy(
    proxy_id: UUID,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Obtiene un proxy por ID."""
    proxy = proxy_service.get_proxy(proxy_id, _user_id(current_user))
    if not proxy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy no encontrado")
    return _proxy_to_response(proxy)


@router.put("/{proxy_id}")
async def update_proxy(
    proxy_id: UUID,
    body: ProxyUpdate,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Actualiza un proxy."""
    proxy = proxy_service.update_proxy(
        proxy_id=proxy_id,
        user_id=_user_id(current_user),
        name=body.name,
        proxy_type=body.proxy_type,
        proxy_host=body.proxy_host,
        proxy_port=body.proxy_port,
        proxy_username=body.proxy_username,
        proxy_password=body.proxy_password,
        proxy_country=body.proxy_country,
    )
    if not proxy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy no encontrado")
    return _proxy_to_response(proxy)


@router.delete("/{proxy_id}")
async def delete_proxy(
    proxy_id: UUID,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Elimina un proxy. No permite si está en uso por estrategias activas."""
    success, error = proxy_service.delete_proxy(proxy_id, _user_id(current_user))
    if not success:
        if "no encontrado" in (error or "").lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return {"status": "deleted"}


@router.post("/{proxy_id}/validate")
async def validate_proxy(
    proxy_id: UUID,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Valida conectividad del proxy y actualiza status/latencia."""
    success, status_val, latency_ms = proxy_service.validate_proxy(
        proxy_id, _user_id(current_user)
    )
    if not success and status_val is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy no encontrado")
    return {
        "validation_status": status_val,
        "validation_latency_ms": latency_ms,
    }
