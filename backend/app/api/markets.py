"""
Markets API endpoints.

Markets: plantillas/grupos lógicos (ej. "BTC Up or Down – 15 min").
No son tradeables directamente. Solo se pueden activar/desactivar para escanear events.

IMPORTANTE: Series y Markets se leen directamente de la API de Polymarket.
Solo se guarda el estado `enabled` en nuestra DB.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.market import Market
from app.models.event import Event
from app.models.series import Series
from app.models.tag import Tag
from app.models.market_tag import MarketTag
from app.api.auth import get_current_user
from app.api.auth import User
from app.core.state import state
from app.core.config_service import config_service
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/markets", tags=["markets"])


class MarketResponse(BaseModel):
    """Market response model."""
    market_id: str
    polymarket_id: str
    name: str
    category: Optional[str]
    enabled: bool
    events_count: int
    created_at: str
    updated_at: str


class EventResponse(BaseModel):
    """Event response model."""
    event_id: str
    market_id: str
    market_name: str
    start_time: str
    end_time: str
    state: str
    created_at: str
    updated_at: str


@router.get("")
async def get_markets(
    category: Optional[str] = Query(None, description="Filter by category"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    series_id: Optional[str] = Query(None, description="Filter by series_id"),
    tag_id: Optional[str] = Query(None, description="Filter by tag_id"),
    search: Optional[str] = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of markets (plantillas) - lee directamente de Polymarket API.
    
    Markets son plantillas que generan Events. No son tradeables directamente.
    Solo combina con el estado `enabled` de nuestra DB.
    """
    import httpx
    from app.settings import settings
    from app.core.rate_limiter import rate_limiter, EndpointType
    from app.core.api_cache import api_cache
    from datetime import timedelta
    from app.models.market_enabled_state import MarketEnabledState
    
    # 1. Obtener Markets de la API de Polymarket
    cache_key = f"polymarket_api:markets:closed=false"
    cache_ttl = timedelta(seconds=60)
    
    cached = await api_cache.get(cache_key)
    if cached is None:
        try:
            if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_MARKETS, timeout=5.0):
                logger.warning("Rate limit timeout for markets")
                return []
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{settings.polymarket_gamma_api_url}/markets"
                params = {"closed": "false", "limit": 100}
                response = await client.get(url, params=params)
                
                if response.status_code == 429:
                    await rate_limiter.record_violation(EndpointType.GAMMA_MARKETS)
                    logger.warning("Rate limit exceeded")
                    return []
                
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, list):
                    markets_data = data
                else:
                    markets_data = data.get("data", [])
                
                await api_cache.set(cache_key, markets_data, ttl=cache_ttl)
        except Exception as e:
            logger.error(f"Error fetching markets from Polymarket: {e}", exc_info=True)
            return []
    else:
        markets_data = cached
    
    # 2. Obtener estados enabled de nuestra DB
    enabled_states = {}
    for state in db.query(MarketEnabledState).all():
        enabled_states[state.polymarket_market_id] = state.enabled
    
    # 3. Obtener events count desde DB (mapear por polymarket_id)
    # Necesitamos mapear polymarket_market_id a market_id interno para contar events
    # Por ahora, no mostramos events_count aquí ya que no tenemos el mapeo
    
    # 4. Combinar datos de API con estado enabled
    result = []
    for market_data in markets_data:
        polymarket_id = market_data.get("id") or market_data.get("slug") or str(market_data.get("_id", ""))
        if not polymarket_id:
            continue
        
        # Aplicar filtros
        if category and market_data.get("category") != category:
            continue
        
        if search and search.lower() not in (market_data.get("question") or market_data.get("name") or "").lower():
            continue
        
        # Obtener estado enabled de DB (por defecto False)
        is_enabled = enabled_states.get(polymarket_id, False)
        
        if enabled is not None and is_enabled != enabled:
            continue
        
        # Tags desde la API
        tags_data = market_data.get("tags", [])
        tags = [{"tag_id": str(t.get("id") or t.get("slug", "")), "name": t.get("name", "")} for t in tags_data]
        
        if tag_id:
            # Filtrar por tag
            if not any(t.get("tag_id") == tag_id or str(t.get("id") or t.get("slug", "")) == tag_id for t in tags_data):
                continue
        
        # Series info desde la API
        series_info = market_data.get("series") or {}
        series_polymarket_id = series_info.get("id") or series_info.get("slug")
        
        if series_id and series_polymarket_id != series_id:
            continue
        
        result.append({
            "market_id": polymarket_id,  # Usamos polymarket_id como ID
            "polymarket_id": polymarket_id,
            "name": market_data.get("question") or market_data.get("name", ""),
            "category": market_data.get("category"),
            "enabled": is_enabled,
            "series_id": series_polymarket_id,
            "series_name": series_info.get("name"),
            "tags": tags,
            "events_count": 0,  # TODO: Contar desde DB si es necesario
            "created_at": None,
            "updated_at": None,
        })
    
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    
    # Get events for this market
    events = db.query(Event).filter(Event.market_id == market.id).order_by(Event.start_time.desc()).all()
    
    # Get tags for this market
    market_tags = db.query(MarketTag).filter(MarketTag.market_id == market.id).all()
    tags = [{"tag_id": str(mt.tag_id), "name": mt.tag.name} for mt in market_tags]
    
    return {
        "market_id": str(market.id),
        "polymarket_id": market.polymarket_id,
        "name": market.name,
        "category": market.category,
        "enabled": market.enabled,
        "series_id": str(market.series_id) if market.series_id else None,
        "series_name": market.series.name if market.series else None,
        "tags": tags,
        "polymarket_payload": market.polymarket_payload,
        "events": [
            {
                "event_id": str(event.id),
                "polymarket_event_id": event.polymarket_event_id,
                "start_time": event.start_time.isoformat() if event.start_time else None,
                "end_time": event.end_time.isoformat() if event.end_time else None,
                "state": event.state,
            }
            for event in events
        ],
        "created_at": market.created_at.isoformat(),
        "updated_at": market.updated_at.isoformat(),
    }


class EnableMarketRequest(BaseModel):
    enabled: bool


@router.patch("/{polymarket_market_id}/enable")
async def enable_market(
    polymarket_market_id: str,
    request: EnableMarketRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Activar o desactivar un market.
    
    Solo actualiza el estado enabled en nuestra DB.
    NO crea/actualiza el Market en DB (se lee directamente de la API).
    
    Activar un market:
    - NO inicia trading directamente
    - Solo marca el market como enabled = true en DB
    - El scanner leerá markets activos y descubrirá events
    """
    from app.models.market_enabled_state import MarketEnabledState
    from uuid import uuid4
    
    # Buscar o crear estado enabled
    state = db.query(MarketEnabledState).filter(
        MarketEnabledState.polymarket_market_id == polymarket_market_id
    ).first()
    
    if not state:
        state = MarketEnabledState(
            id=uuid4(),
            polymarket_market_id=polymarket_market_id,
            enabled=request.enabled
        )
        db.add(state)
    else:
        state.enabled = request.enabled
    
    db.commit()
    db.refresh(state)
    
    return {
        "polymarket_market_id": polymarket_market_id,
        "enabled": state.enabled,
        "message": f"Market {'activado' if request.enabled else 'desactivado'} correctamente"
    }


@router.get("/events/list")
async def get_events(
    market_id: Optional[str] = Query(None, description="Filter by market_id"),
    state: Optional[str] = Query(None, description="Filter by state (UPCOMING, ACTIVE, FINISHED)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of events (instancias concretas de markets).
    
    Events son instancias tradeables. Solo los Events se pueden tradear.
    """
    query = db.query(Event).join(Market)
    
    if market_id:
        query = query.filter(Event.market_id == market_id)
    
    if state:
        query = query.filter(Event.state == state)
    
    events = query.order_by(Event.start_time.desc()).limit(100).all()
    
    result = []
    for event in events:
        result.append({
            "event_id": str(event.id),
            "polymarket_event_id": event.polymarket_event_id,
            "market_id": str(event.market_id),
            "market_name": event.market.name,
            "start_time": event.start_time.isoformat() if event.start_time else None,
            "end_time": event.end_time.isoformat() if event.end_time else None,
            "state": event.state,
            "polymarket_payload": event.polymarket_payload,
            "created_at": event.created_at.isoformat(),
            "updated_at": event.updated_at.isoformat(),
        })
    
    return result


@router.get("/events/{event_id}/quorum")
async def get_event_quorum(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get quorum information for a specific event.
    
    Returns:
        - event_id: ID del evento
        - quorum_used: Quorum efectivo usado en la última decisión
        - quorum_required: Quorum base configurado
        - checkers_available: Número de checkers saludables disponibles
        - checkers_used: Número de checkers que participaron en la decisión
        - quorum_reason: Razón de la decisión de quorum
        - trading_permitted: Si el trading está permitido
        - event_state: Estado actual del evento
        - confidence: Confianza de la decisión
        - timestamp: Timestamp de la última actualización
    """
    # Obtener evento de DB
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    
    # Obtener estado del evento desde el state service
    event_state_obj = state.event_state.get(event_id)
    
    if not event_state_obj:
        # Si no hay estado en memoria, retornar información básica
        quorum_base = int(config_service.get("quorum_base", 2))
        return {
            "event_id": str(event_id),
            "quorum_used": None,
            "quorum_required": quorum_base,
            "checkers_available": 0,
            "checkers_used": 0,
            "quorum_reason": "no_state_available",
            "trading_permitted": False,
            "event_state": event.state,
            "confidence": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Event state not available in memory"
        }
    
    # Retornar información completa de quorum
    return {
        "event_id": str(event_id),
        "polymarket_event_id": event.polymarket_event_id,
        "quorum_used": event_state_obj.quorum_used,
        "quorum_required": event_state_obj.quorum_required,
        "checkers_available": event_state_obj.checkers_available,
        "checkers_used": event_state_obj.checkers_used,
        "quorum_reason": event_state_obj.quorum_reason,
        "trading_permitted": event_state_obj.trading_permitted,
        "event_state": event_state_obj.state,
        "confidence": event_state_obj.confidence,
        "finished_at": event_state_obj.finished_at.isoformat() if event_state_obj.finished_at else None,
        "updated_at": event_state_obj.updated_at.isoformat() if event_state_obj.updated_at else None,
        "timestamp": datetime.utcnow().isoformat()
    }
