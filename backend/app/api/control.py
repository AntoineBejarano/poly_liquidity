"""
Control API endpoints for system and market control.
"""
import logging
from fastapi import APIRouter, Depends
from app.core.state import state
from app.core.execution import execution
from app.api.auth import get_current_user, get_admin_user
from app.api.auth import User
from uuid import UUID

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/control", tags=["control"])


@router.post("/pause")
async def pause_system(
    current_user: User = Depends(get_current_user),
):
    """Pause the system (authenticated users only)."""
    state.system_active = False
    
    # Cancel all open orders
    await execution._cancel_all_open_orders()

    # Evento de observabilidad (§5 SPEC)
    logger.info(
        "system_paused",
        extra={"event": "system_paused", "component": "control_api"},
    )
    
    return {"status": "paused", "system_active": False}


@router.post("/resume")
async def resume_system(
    current_user: User = Depends(get_current_user),
):
    """Resume the system (authenticated users only)."""
    state.system_active = True

    # Evento de observabilidad (§5 SPEC)
    logger.info(
        "system_resumed",
        extra={"event": "system_resumed", "component": "control_api"},
    )

    return {"status": "resumed", "system_active": True}


@router.post("/market/{market_id}/pause")
async def pause_market(
    market_id: UUID,
    current_user: User = Depends(get_admin_user),
):
    """Pause a specific market (admin only)."""
    # TODO: Implement market-level pausing
    # For now, this is a placeholder
    # We'll need to add a paused_markets set to state
    
    # Cancel orders for this market
    await execution._cancel_all_open_orders(market_id)
    
    return {"status": "market_paused", "market_id": str(market_id)}

