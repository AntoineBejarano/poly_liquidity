"""
History API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.trade import Trade
from app.models.market import Market
from app.models.position import Position
from app.api.auth import get_current_user
from app.api.auth import User

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/trades")
async def get_trades(
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get historical trades (paginated)."""
    query = db.query(Trade).join(Market).order_by(Trade.timestamp.desc())
    
    if cursor:
        # Parse cursor and filter
        # TODO: Implement proper cursor-based pagination
        pass
    
    trades = query.limit(limit).all()
    
    items = [
        {
            "trade_id": str(trade.id),
            "market_id": str(trade.market_id),
            "polymarket_id": trade.market.polymarket_id,
            "fill_price": trade.fill_price,
            "fill_size": trade.fill_size,
            "direction": trade.direction,
            "timestamp": trade.timestamp.isoformat(),
        }
        for trade in trades
    ]
    
    return {
        "items": items,
        "next_cursor": None,  # TODO: Implement cursor
    }


@router.get("/markets")
async def get_markets_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get PnL summary by market."""
    # Get resolved markets with positions
    positions = db.query(Position).filter(Position.resolved == True).all()
    
    result = []
    for position in positions:
        market = position.market
        
        # Calculate cost and payout
        cost_total = position.size * position.avg_price
        payout_total = position.payout or 0.0
        realized_pnl = payout_total - cost_total
        
        result.append({
            "market_id": str(position.market_id),
            "polymarket_id": market.polymarket_id,
            "question": market.question,
            "outcome": market.outcome,
            "resolved": True,
            "resolution_outcome": market.resolution_outcome,
            "cost_total": cost_total,
            "payout_total": payout_total,
            "realized_pnl": realized_pnl,
            "resolved_at": market.resolved_at.isoformat() if market.resolved_at else None,
        })
    
    return result


@router.get("/equity")
async def get_equity_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get equity history over time."""
    # TODO: Implement equity calculation over time
    # This would require storing equity snapshots periodically
    return {
        "data": [],
        "message": "Equity history not yet implemented"
    }

