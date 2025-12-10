"""
Markets API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.market import Market
from app.models.event import Event
from app.api.auth import get_current_user
from app.api.auth import User

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("")
async def get_markets(
    status: Optional[str] = Query(None, description="Filter by status"),
    event_state: Optional[str] = Query(None, description="Filter by event state"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of markets."""
    query = db.query(Market)
    
    if status:
        query = query.filter(Market.status == status)
    
    markets = query.order_by(Market.created_at.desc()).limit(100).all()
    
    result = []
    for market in markets:
        # Get event state
        event = db.query(Event).filter(Event.market_id == market.id).first()
        event_state_value = event.state if event else "LIVE"
        
        # Get exposure (simplified)
        exposure = 0.0  # TODO: Calculate from positions
        
        result.append({
            "market_id": str(market.id),
            "polymarket_id": market.polymarket_id,
            "question": market.question,
            "outcome": market.outcome,
            "status": market.status,
            "last_price": market.last_price,
            "event_state": event_state_value,
            "exposure": exposure,
            "created_at": market.created_at.isoformat(),
            "updated_at": market.updated_at.isoformat(),
        })
    
    # Filter by event_state if provided
    if event_state:
        result = [m for m in result if m["event_state"] == event_state]
    
    return result


@router.get("/{market_id}")
async def get_market(
    market_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get market details."""
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    
    event = db.query(Event).filter(Event.market_id == market.id).first()
    
    return {
        "market_id": str(market.id),
        "polymarket_id": market.polymarket_id,
        "question": market.question,
        "outcome": market.outcome,
        "status": market.status,
        "last_price": market.last_price,
        "resolution_outcome": market.resolution_outcome,
        "resolved_at": market.resolved_at.isoformat() if market.resolved_at else None,
        "event": {
            "state": event.state if event else "LIVE",
            "confidence": event.confidence if event else 0.0,
            "finished_at": event.finished_at.isoformat() if event and event.finished_at else None,
        } if event else None,
        "created_at": market.created_at.isoformat(),
        "updated_at": market.updated_at.isoformat(),
    }

