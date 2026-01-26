"""
Values API endpoints.

Endpoints para gestionar valores/configuraciones del sistema.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.api.auth import get_current_user, User
from app.core.state import state

router = APIRouter(prefix="/values", tags=["values"])


class ValueConfigRequest(BaseModel):
    """Request model para configurar valores."""
    key: str = Field(..., description="Clave del valor")
    value: Any = Field(..., description="Valor a configurar")
    description: Optional[str] = Field(None, description="Descripción del valor")


@router.get("/live")
async def get_live_values(
    current_user: User = Depends(get_current_user),
):
    """Obtiene valores en vivo del sistema."""
    return {
        "system_active": state.system_active,
        "markets_count": len(state.markets),
        "events_count": len(state.events),
        "positions_count": len(state.positions),
        "timestamp": state.last_update.isoformat() if state.last_update else None,
    }


@router.get("/global-state")
async def get_global_state(
    current_user: User = Depends(get_current_user),
):
    """Obtiene el estado global del sistema."""
    return {
        "system_active": state.system_active,
        "markets": {
            "total": len(state.markets),
            "active": len([m for m in state.markets.values() if m.last_price]),
        },
        "events": {
            "total": len(state.events),
            "active": len([e for e in state.events.values() if e.state == "ACTIVE"]),
        },
        "positions": {
            "total": len(state.positions),
            "unresolved": len([p for p in state.positions.values() if not p.resolved]),
        },
        "exposures": {
            "total": len(state.exposures),
            "total_notional": sum(e.notional for e in state.exposures.values()),
        },
    }


@router.post("/config")
async def set_value_config(
    config: ValueConfigRequest = Body(...),
    current_user: User = Depends(get_current_user),
):
    """Configura un valor del sistema."""
    # Por ahora, solo retornamos éxito
    # En el futuro, esto podría guardar en DB o actualizar configuración
    return {
        "success": True,
        "key": config.key,
        "value": config.value,
        "message": "Value configured successfully",
    }

