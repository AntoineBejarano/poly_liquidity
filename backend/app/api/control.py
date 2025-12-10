"""
Control API endpoints for system and market control.
"""
from fastapi import APIRouter, Depends
from app.core.state import state
from app.core.execution import execution
from app.api.auth import get_current_user, get_admin_user
from app.api.auth import User
from uuid import UUID

router = APIRouter(prefix="/control", tags=["control"])


@router.post("/pause")
async def pause_system(
    current_user: User = Depends(get_admin_user),
):
    """Pause the system (admin only)."""
    state.system_active = False
    
    # Cancel all open orders
    await execution._cancel_all_open_orders()
    
    return {"status": "paused", "system_active": False}


@router.post("/resume")
async def resume_system(
    current_user: User = Depends(get_admin_user),
):
    """Resume the system (admin only)."""
    state.system_active = True
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

