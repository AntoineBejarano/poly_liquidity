"""
Series API endpoints.

Series: contenedor lógico / agrupador de Markets relacionados.
Ej.: "Bitcoin Up or Down"
NO es tradeable. Solo se usa para organización y UX.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.series import Series
from app.models.market import Market
from app.api.auth import get_current_user
from app.api.auth import User
from pydantic import BaseModel

router = APIRouter(prefix="/series", tags=["series"])


class SeriesResponse(BaseModel):
    """Series response model."""
    series_id: str
    polymarket_series_id: str
    name: str
    slug: Optional[str]
    description: Optional[str]
    series_type: Optional[str]
    recurrence: Optional[str]
    markets_count: int
    created_at: str
    updated_at: str


@router.get("")
async def get_series(
    search: Optional[str] = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of all series - lee directamente de Polymarket API.
    
    Series son contenedores lógicos que agrupan Markets relacionados.
    Cache L2 (gamma_cache_provider): key gamma:series:all, SWR + singleflight, TTL 1h (Fase 6).
    """
    import asyncio
    import httpx
    from app.settings import settings
    from app.core.rate_limiter import rate_limiter, EndpointType
    from app.core.api_cache import api_cache
    from app.core.cache_provider import gamma_cache_provider
    from app.core.cache_singleflight import try_acquire_refresh_lock, release_refresh_lock
    from datetime import timedelta
    import logging

    logger = logging.getLogger(__name__)
    SERIES_CACHE_KEY = "gamma:series:all"
    SERIES_SOFT_TTL_SEC = 3600  # 1h

    async def _fetch_series_from_gamma() -> list:
        if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_GENERAL, timeout=5.0):
            return []
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{settings.polymarket_gamma_api_url}/series"
            response = await client.get(url, params={"limit": 100})
            if response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_GENERAL)
                return []
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get("data", [])

    hit = await gamma_cache_provider.get_with_meta(SERIES_CACHE_KEY)
    if hit is not None and hit.status == "fresh":
        series_data = hit.payload
    elif hit is not None and hit.status == "stale":
        series_data = hit.payload
        acquired = await try_acquire_refresh_lock(SERIES_CACHE_KEY)
        if acquired:
            try:
                new_data = await _fetch_series_from_gamma()
                if new_data:
                    await gamma_cache_provider.set(SERIES_CACHE_KEY, new_data, ttl_seconds=float(SERIES_SOFT_TTL_SEC))
                    series_data = new_data
            except Exception as e:
                logger.debug("Error refreshing series cache: %s", e)
            finally:
                await release_refresh_lock(SERIES_CACHE_KEY)
    else:
        acquired = await try_acquire_refresh_lock(SERIES_CACHE_KEY)
        if acquired:
            try:
                series_data = await _fetch_series_from_gamma()
                if series_data:
                    await gamma_cache_provider.set(SERIES_CACHE_KEY, series_data, ttl_seconds=float(SERIES_SOFT_TTL_SEC))
                else:
                    series_data = []
            except Exception as e:
                logger.error("Error fetching series from Polymarket: %s", e, exc_info=True)
                series_data = []
            finally:
                await release_refresh_lock(SERIES_CACHE_KEY)
        else:
            await asyncio.sleep(0.3)
            hit2 = await gamma_cache_provider.get_with_meta(SERIES_CACHE_KEY)
            series_data = (hit2.payload if hit2 else []) or []
    
    # 2. Obtener Markets para contar por serie
    markets_cache_key = f"polymarket_api:markets:closed=false"
    markets_cached = await api_cache.get(markets_cache_key)
    if markets_cached is None:
        try:
            if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_MARKETS, timeout=5.0):
                markets_data = []
            else:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    url = f"{settings.polymarket_gamma_api_url}/markets"
                    params = {"closed": "false", "limit": 100}
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 429:
                        await rate_limiter.record_violation(EndpointType.GAMMA_MARKETS)
                        markets_data = []
                    else:
                        response.raise_for_status()
                        data = response.json()
                        
                        if isinstance(data, list):
                            markets_data = data
                        else:
                            markets_data = data.get("data", [])
                        
                        await api_cache.set(markets_cache_key, markets_data, ttl=timedelta(seconds=60))
        except Exception as e:
            logger.error(f"Error fetching markets for series count: {e}", exc_info=True)
            markets_data = []
    else:
        markets_data = markets_cached
    
    # 3. Agrupar markets por serie
    markets_by_series = {}
    for market in markets_data:
        series_info = market.get("series") or {}
        series_id = series_info.get("id") or series_info.get("slug") or market.get("series_id")
        if series_id:
            if series_id not in markets_by_series:
                markets_by_series[series_id] = []
            markets_by_series[series_id].append(market)
    
    # 4. Procesar Series
    result = []
    for series in series_data:
        series_id = series.get("id") or series.get("slug") or str(series.get("_id", ""))
        if not series_id:
            continue
        
        # Aplicar filtro de búsqueda
        if search and search.lower() not in (series.get("name") or "").lower():
            continue
        
        # Contar markets de esta serie
        markets_count = len(markets_by_series.get(series_id, []))
        
        result.append({
            "series_id": series_id,  # Usamos polymarket_series_id como ID
            "polymarket_series_id": series_id,
            "name": series.get("name", ""),
            "slug": series.get("slug"),
            "description": series.get("description"),
            "series_type": series.get("series_type"),
            "recurrence": series.get("recurrence"),
            "markets_count": markets_count,
            "created_at": None,  # No guardamos en DB
            "updated_at": None,  # No guardamos en DB
        })
    
    return result


@router.get("/{series_id}")
async def get_series_detail(
    series_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get series details with its markets."""
    series = db.query(Series).filter(Series.id == series_id).first()
    if not series:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")
    
    # Get markets for this series
    markets = db.query(Market).filter(Market.series_id == series.id).order_by(Market.name).all()
    
    markets_data = []
    for market in markets:
        # Count events for this market
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
        "series_id": str(series.id),
        "polymarket_series_id": series.polymarket_series_id,
        "name": series.name,
        "slug": series.slug,
        "description": series.description,
        "series_type": series.series_type,
        "recurrence": series.recurrence,
        "polymarket_payload": series.polymarket_payload,
        "markets": markets_data,
        "created_at": series.created_at.isoformat(),
        "updated_at": series.updated_at.isoformat(),
    }


@router.get("/{series_id}/markets")
async def get_series_markets(
    series_id: str,
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get markets for a specific series."""
    series = db.query(Series).filter(Series.id == series_id).first()
    if not series:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")
    
    query = db.query(Market).filter(Market.series_id == series.id)
    
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

