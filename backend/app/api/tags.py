"""
Tags API endpoints.

Tags: metadatos transversales de clasificación.
Ejemplos: crypto, bitcoin, 15m, up-down, sports
NO es tradeable. Solo se usa para búsqueda, filtrado y agrupación visual.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.tag import Tag
from app.models.market_tag import MarketTag
from app.models.market import Market
from app.api.auth import get_current_user
from app.api.auth import User
from pydantic import BaseModel

router = APIRouter(prefix="/tags", tags=["tags"])


class TagResponse(BaseModel):
    """Tag response model."""
    tag_id: str
    polymarket_tag_id: str
    name: str
    slug: Optional[str]
    label: Optional[str]
    markets_count: int
    created_at: str
    updated_at: str


@router.get("")
async def get_tags(
    search: Optional[str] = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of all tags.
    
    Tags son metadatos transversales de clasificación.
    NO son tradeables. Solo para búsqueda, filtrado y agrupación visual.
    """
    query = db.query(Tag)
    
    if search:
        query = query.filter(Tag.name.ilike(f"%{search}%"))
    
    tags = query.order_by(Tag.name).all()
    
    result = []
    for tag in tags:
        # Contar markets con este tag
        markets_count = db.query(MarketTag).filter(MarketTag.tag_id == tag.id).count()
        
        result.append({
            "tag_id": str(tag.id),
            "polymarket_tag_id": tag.polymarket_tag_id,
            "name": tag.name,
            "slug": tag.slug,
            "label": tag.label,
            "markets_count": markets_count,
            "created_at": tag.created_at.isoformat(),
            "updated_at": tag.updated_at.isoformat(),
        })
    
    return result


@router.get("/{tag_id}")
async def get_tag_detail(
    tag_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get tag details with markets that have this tag."""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    
    # Get markets with this tag
    market_tags = db.query(MarketTag).filter(MarketTag.tag_id == tag.id).all()
    markets_data = []
    
    for mt in market_tags:
        market = db.query(Market).filter(Market.id == mt.market_id).first()
        if market:
            from app.models.event import Event
            events_count = db.query(Event).filter(Event.market_id == market.id).count()
            
            markets_data.append({
                "market_id": str(market.id),
                "polymarket_id": market.polymarket_id,
                "name": market.name,
                "category": market.category,
                "enabled": market.enabled,
                "events_count": events_count,
            })
    
    return {
        "tag_id": str(tag.id),
        "polymarket_tag_id": tag.polymarket_tag_id,
        "name": tag.name,
        "slug": tag.slug,
        "label": tag.label,
        "polymarket_payload": tag.polymarket_payload,
        "markets": markets_data,
        "created_at": tag.created_at.isoformat(),
        "updated_at": tag.updated_at.isoformat(),
    }


@router.get("/{tag_id}/markets")
async def get_tag_markets(
    tag_id: str,
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get markets that have a specific tag."""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    
    # Get markets with this tag
    query = db.query(Market).join(MarketTag).filter(MarketTag.tag_id == tag.id)
    
    if enabled is not None:
        query = query.filter(Market.enabled == enabled)
    
    markets = query.order_by(Market.name).all()
    
    result = []
    for market in markets:
        from app.models.event import Event
        events_count = db.query(Event).filter(Event.market_id == market.id).count()
        
        result.append({
            "market_id": str(market.id),
            "polymarket_id": market.polymarket_id,
            "name": market.name,
            "category": market.category,
            "enabled": market.enabled,
            "events_count": events_count,
            "created_at": market.created_at.isoformat(),
            "updated_at": market.updated_at.isoformat(),
        })
    
    return result

