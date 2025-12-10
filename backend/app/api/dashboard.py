"""
Dashboard API endpoint.
"""
from fastapi import APIRouter, Depends
from app.core.state import state
from app.api.auth import get_current_user
from app.api.auth import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    current_user: User = Depends(get_current_user),
):
    """Get dashboard data."""
    # Calculate realized PnL
    realized_pnl = 0.0
    # TODO: Calculate from resolved positions
    
    # Calculate unrealized PnL
    unrealized_pnl = 0.0
    for position_state in state.positions.values():
        if position_state.resolved:
            continue
        
        # Get current price from market
        market_state = state.markets.get(position_state.market_id)
        if market_state and market_state.last_price:
            cost_total = position_state.size * position_state.avg_price
            theoretical_value = position_state.size * market_state.last_price
            unrealized_pnl += theoretical_value - cost_total
    
    # Calculate global exposure
    global_exposure = 0.0
    for exposure_state in state.exposures.values():
        global_exposure += exposure_state.notional
    
    # Count active markets
    active_markets = len([m for m in state.markets.values() if m.last_price])
    
    # Calculate equity (simplified)
    equity = 1000000.0  # TODO: Get from actual capital
    equity += realized_pnl + unrealized_pnl
    
    return {
        "equity": equity,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "global_exposure": global_exposure,
        "active_markets": active_markets,
        "system_active": state.system_active,
    }

