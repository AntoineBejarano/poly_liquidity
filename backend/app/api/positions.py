"""
Positions API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.position import Position
from app.models.market import Market
from app.api.auth import get_current_user
from app.api.auth import User

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("")
async def get_positions(
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of positions."""
    query = db.query(Position).join(Market)
    
    if resolved is not None:
        query = query.filter(Position.resolved == resolved)
    
    positions = query.all()
    
    result = []
    for position in positions:
        market = position.market
        
        # Get current price from market
        current_price = market.last_price or 0.0
        
        # Calculate unrealized PnL
        cost_total = position.size * position.avg_price
        theoretical_value = position.size * current_price
        unrealized_pnl = theoretical_value - cost_total
        
        result.append({
            "market_id": str(position.market_id),
            "polymarket_id": market.polymarket_id,
            "question": market.question,
            "size": position.size,
            "avg_price": position.avg_price,
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
            "resolved": position.resolved,
            "payout": position.payout,
        })
    
    return result

