"""
API endpoints para acceder a Gamma API de Polymarket.

Estos endpoints actúan como proxy para el frontend, proporcionando:
- Rate limiting centralizado
- Cache compartido
- Manejo de errores consistente
- Sin problemas de CORS
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
import httpx
from app.core.rate_limiter import rate_limiter, EndpointType
from app.core.api_cache import api_cache
from app.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/polymarket", tags=["polymarket"])


async def _get_gamma_client() -> httpx.AsyncClient:
    """Obtiene cliente HTTP para Gamma API."""
    return httpx.AsyncClient(timeout=30.0, base_url=settings.polymarket_gamma_api_url)


@router.get("/events")
async def list_events(
    order: str = Query("id", description="Order by field"),
    ascending: bool = Query(False, description="Ascending order"),
    closed: bool = Query(False, description="Include closed events"),
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """
    Lista eventos de Polymarket con paginación.
    
    Proxy para GET /events de Gamma API.
    """
    cache_key = f"polymarket:events:order={order}:asc={ascending}:closed={closed}:limit={limit}:offset={offset}"
    cache_ttl = 5  # 5 segundos
    
    # Check cache
    cached = await api_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Acquire rate limit permission
    if not await rate_limiter.wait_for_capacity(EndpointType.DATA_API, timeout=2.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    client = await _get_gamma_client()
    try:
        params = {
            "order": order,
            "ascending": str(ascending).lower(),
            "closed": str(closed).lower(),
            "limit": limit,
            "offset": offset
        }
        
        response = await client.get("/events", params=params)
        
        if response.status_code == 429:
            await rate_limiter.record_violation(EndpointType.DATA_API)
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        response.raise_for_status()
        data = response.json()
        
        # Cache result
        await api_cache.set(cache_key, data, ttl=cache_ttl)
        return data
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Error fetching events: {e}")
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Events not found")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error fetching events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await client.aclose()


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """
    Obtiene un evento específico por ID.
    
    Proxy para GET /events/{id} de Gamma API.
    """
    cache_key = f"polymarket:event:{event_id}"
    cache_ttl = 10  # 10 segundos (eventos individuales cambian menos)
    
    # Check cache
    cached = await api_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Acquire rate limit permission
    if not await rate_limiter.wait_for_capacity(EndpointType.DATA_API, timeout=2.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    client = await _get_gamma_client()
    try:
        response = await client.get(f"/events/{event_id}")
        
        if response.status_code == 429:
            await rate_limiter.record_violation(EndpointType.DATA_API)
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Event not found")
        
        response.raise_for_status()
        data = response.json()
        
        # Cache result
        await api_cache.set(cache_key, data, ttl=cache_ttl)
        return data
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Error fetching event {event_id}: {e}")
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Event not found")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error fetching event {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await client.aclose()


@router.get("/markets/{market_id}")
async def get_market(market_id: str):
    """
    Obtiene un mercado específico por ID.
    
    Proxy para GET /markets/{id} de Gamma API.
    Incluye información completa: conditionId, clobTokenIds, bestBid, bestAsk, etc.
    """
    cache_key = f"polymarket:market:{market_id}"
    cache_ttl = 5  # 5 segundos (mercados cambian más frecuentemente)
    
    # Check cache
    cached = await api_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Acquire rate limit permission
    if not await rate_limiter.wait_for_capacity(EndpointType.DATA_API, timeout=2.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    client = await _get_gamma_client()
    try:
        response = await client.get(f"/markets/{market_id}")
        
        if response.status_code == 429:
            await rate_limiter.record_violation(EndpointType.DATA_API)
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Market not found")
        
        response.raise_for_status()
        data = response.json()
        
        # Cache result
        await api_cache.set(cache_key, data, ttl=cache_ttl)
        return data
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Error fetching market {market_id}: {e}")
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Market not found")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error fetching market {market_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await client.aclose()


@router.get("/markets/slug/{slug}")
async def get_market_by_slug(slug: str):
    """
    Obtiene un mercado por slug.
    
    Proxy para GET /markets/slug/{slug} de Gamma API.
    Útil para obtener mercado desde URL de Polymarket.
    """
    cache_key = f"polymarket:market:slug:{slug}"
    cache_ttl = 10  # 10 segundos (slugs cambian menos)
    
    # Check cache
    cached = await api_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Acquire rate limit permission
    if not await rate_limiter.wait_for_capacity(EndpointType.DATA_API, timeout=2.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    client = await _get_gamma_client()
    try:
        response = await client.get(f"/markets/slug/{slug}")
        
        if response.status_code == 429:
            await rate_limiter.record_violation(EndpointType.DATA_API)
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Market not found")
        
        response.raise_for_status()
        data = response.json()
        
        # Cache result
        await api_cache.set(cache_key, data, ttl=cache_ttl)
        return data
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Error fetching market by slug {slug}: {e}")
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Market not found")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error fetching market by slug {slug}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await client.aclose()


@router.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """
    Búsqueda pública de eventos, mercados, tags y perfiles.
    
    Proxy para GET /public-search de Gamma API.
    """
    cache_key = f"polymarket:search:q={q}:limit={limit}:offset={offset}"
    cache_ttl = 10  # 10 segundos
    
    # Check cache
    cached = await api_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Acquire rate limit permission
    if not await rate_limiter.wait_for_capacity(EndpointType.DATA_API, timeout=2.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    client = await _get_gamma_client()
    try:
        params = {
            "q": q,
            "limit": limit,
            "offset": offset
        }
        
        response = await client.get("/public-search", params=params)
        
        if response.status_code == 429:
            await rate_limiter.record_violation(EndpointType.DATA_API)
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        response.raise_for_status()
        data = response.json()
        
        # Cache result
        await api_cache.set(cache_key, data, ttl=cache_ttl)
        return data
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Error searching: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error searching: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await client.aclose()


@router.get("/health")
async def health_check():
    """
    Health check para Gamma API.
    
    Verifica que la API esté disponible.
    """
    client = await _get_gamma_client()
    try:
        # Intentar obtener un evento para verificar conectividad
        response = await client.get("/events", params={"limit": 1})
        if response.status_code == 200:
            return {"status": "ok", "api": "gamma-api.polymarket.com"}
        else:
            return {"status": "degraded", "status_code": response.status_code}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        await client.aclose()

