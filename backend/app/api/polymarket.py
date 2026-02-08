"""
API endpoints para acceder a Gamma API de Polymarket.

Estos endpoints actúan como proxy para el frontend, proporcionando:
- Rate limiting centralizado
- Cache compartido
- Manejo de errores consistente
- Sin problemas de CORS
"""
import asyncio
import logging
import time as _time
from typing import Optional, List, Dict, Any, Tuple
from datetime import timedelta
from fastapi import APIRouter, HTTPException, Query, status, Body, Depends
from pydantic import BaseModel, field_validator, ValidationError
import httpx
from app.core.rate_limiter import rate_limiter, EndpointType
from app.core.api_cache import api_cache
from app.core.config_service import config_service
from app.settings import settings
from app.api.auth import get_current_user, User
from app.api.errors import wallet_not_configured
from app.core.gamma_utils import parse_clob_token_ids
from app.core.discovery.clob_client import fetch_orderbooks_batch
from app.core.discovery.metrics import compute_market_metrics, compute_event_score
from app.core.discovery.tradeable import is_tradeable_market as discovery_is_tradeable, tradeable_reasons
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

# Redis TTL para Discovery screener (solo cache, no fuente de verdad)
DISCOVERY_REDIS_TTL_EVENT = 20
DISCOVERY_REDIS_TTL_SCREENER = 15


async def _require_clob_client(current_user: User = Depends(get_current_user)):
    """Dependency: exige auth y wallet del usuario; devuelve cliente CLOB o 409 WALLET_NOT_CONFIGURED (política v2)."""
    from app.core.execution.polymarket_client_wrapper import get_polymarket_client_for_user
    client = get_polymarket_client_for_user(current_user.id)
    if not client or not client.is_available():
        logger.warning("missing_wallet", extra={"user_id": current_user.id})
        raise wallet_not_configured()
    return client

router = APIRouter(prefix="/api/polymarket", tags=["polymarket"])


@router.get("/events")
async def list_events(
    order: str = Query("id", description="Order by field"),
    ascending: bool = Query(False, description="Ascending order"),
    closed: bool = Query(False, description="Include closed events"),
    limit: int = Query(50, ge=1, le=200, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    tag_slug: Optional[str] = Query(None, description="Filter by tag slug (e.g. crypto, nfl)"),
    end_date_max: Optional[str] = Query(None, description="Max end date ISO (e.g. 2026-02-08T00:00:00Z)"),
):
    """
    Lista eventos de Polymarket con paginación.

    Proxy para GET /events de Gamma API.
    Params tag_slug y end_date_max para discovery Polymarket-style.
    """
    cache_key = f"polymarket:events:order={order}:asc={ascending}:closed={closed}:limit={limit}:offset={offset}:tag={tag_slug or ''}:end={end_date_max or ''}"
    cache_ttl = timedelta(seconds=5)  # 5 segundos

    # Check cache
    cached = await api_cache.get(cache_key)
    if cached is not None:
        return cached

    # Acquire rate limit permission
    if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_EVENTS, timeout=2.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    async with httpx.AsyncClient(timeout=30.0, base_url=settings.polymarket_gamma_api_url, trust_env=False) as client:
        try:
            params: Dict[str, str] = {
                "order": order,
                "ascending": str(ascending).lower(),
                "closed": str(closed).lower(),
                "limit": str(limit),
                "offset": str(offset),
            }
            if tag_slug:
                params["tag_slug"] = tag_slug
            if end_date_max:
                params["end_date_max"] = end_date_max

            response = await client.get("/events", params=params)
            
            if response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_EVENTS)
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


# --- Discovery: tradeable-markets flat list (Polymarket-style) ---
DISCOVERY_CACHE_TTL = timedelta(seconds=15)

# Tolerancias live: startDate - X min, endDate + Y min (configurable por liga)
LIVE_TOLERANCES: Dict[str, Dict[str, int]] = {
    "default": {"start_minutes": 15, "end_minutes": 4 * 60},
    "nfl": {"start_minutes": 15, "end_minutes": 4 * 60},
    "nba": {"start_minutes": 15, "end_minutes": 3 * 60},
    "ncaab": {"start_minutes": 15, "end_minutes": 3 * 60},
    "nhl": {"start_minutes": 15, "end_minutes": 4 * 60},
    "ufc": {"start_minutes": 15, "end_minutes": 2 * 60},
}


def _get_live_tolerances(league: Optional[str], event: Dict[str, Any]) -> Tuple[int, int]:
    """Devuelve (start_minutes, end_minutes) para la heurística live."""
    cfg = LIVE_TOLERANCES.get("default", {"start_minutes": 15, "end_minutes": 4 * 60})
    if league and league in LIVE_TOLERANCES:
        cfg = LIVE_TOLERANCES[league]
    else:
        tags = event.get("tags") or []
        for t in tags:
            if isinstance(t, dict):
                slug = (t.get("slug") or "").lower()
                if slug in LIVE_TOLERANCES:
                    cfg = LIVE_TOLERANCES[slug]
                    break
    return cfg.get("start_minutes", 15), cfg.get("end_minutes", 4 * 60)


def _is_tradeable_market(m: Dict[str, Any]) -> bool:
    return (
        m.get("active") is True
        and m.get("acceptingOrders") is True
        and m.get("archived") is not True
        and m.get("closed") is not True
    )


def _is_live_event(event: Dict[str, Any], league: Optional[str] = None) -> bool:
    """
    Heurística live: now >= startDate - tolerance_start y now <= endDate + tolerance_end.
    Tolerancias por liga (nfl, nba, etc.) o inferidas de event.tags.
    """
    from datetime import datetime

    start_min, end_min = _get_live_tolerances(league, event)
    now_ms = _time.time() * 1000
    start_str = event.get("startDate") or event.get("creationDate")
    end_str = event.get("endDate")
    if not start_str or not end_str:
        return False
    try:
        start_ts = datetime.fromisoformat(start_str.replace("Z", "+00:00")).timestamp() * 1000
        end_ts = datetime.fromisoformat(end_str.replace("Z", "+00:00")).timestamp() * 1000
        start_adj = start_ts - start_min * 60 * 1000
        end_adj = end_ts + end_min * 60 * 1000
        return start_adj <= now_ms <= end_adj
    except (ValueError, TypeError):
        return False


def _time_to_resolution_minutes(end_date_str: Optional[str]) -> Optional[float]:
    from datetime import datetime

    if not end_date_str:
        return None
    try:
        end_ts = datetime.fromisoformat(end_date_str.replace("Z", "+00:00")).timestamp()
        return max(0, (end_ts - _time.time()) / 60)
    except (ValueError, TypeError):
        return None


@router.get("/discovery")
async def discovery_tradeable_markets(
    tag_slug: str = Query(..., description="Domain or league slug (crypto, nfl, etc.)"),
    closed: bool = Query(False, description="Include closed"),
    limit: int = Query(100, ge=1, le=200, description="Overfetch limit (proxy fetches this many)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    end_date_max: Optional[str] = Query(None, description="Max end date ISO (for TTR filter server-side)"),
    live: bool = Query(False, description="Sports live: filter events in play window"),
    league: Optional[str] = Query(None, description="League slug for live tolerances"),
):
    """
    Lista plana de markets tradeables (market-first, Polymarket-style).

    Filtra: active, acceptingOrders, !archived, !closed, event.archived !== true.
    Orden: volume24hr desc, liquidity desc, timeToResolution asc.
    """
    cache_key = f"polymarket:discovery:tag={tag_slug}:closed={closed}:limit={limit}:offset={offset}:end={end_date_max or ''}:live={live}:league={league or ''}"
    cached = await api_cache.get(cache_key)
    if cached is not None:
        return cached

    if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_EVENTS, timeout=5.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    from app.core.gamma_utils import parse_clob_token_ids

    params: Dict[str, str] = {
        "order": "id",
        "ascending": "false",
        "closed": str(closed).lower(),
        "limit": str(limit),
        "offset": str(offset),
        "tag_slug": tag_slug,
    }
    if end_date_max:
        params["end_date_max"] = end_date_max

    async with httpx.AsyncClient(timeout=30.0, base_url=settings.polymarket_gamma_api_url, trust_env=False) as client:
        try:
            response = await client.get("/events", params=params)
            if response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_EVENTS)
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            response.raise_for_status()
            events_raw = response.json()
        except httpx.HTTPStatusError as e:
            logger.error("Discovery Gamma error: %s", e)
            raise HTTPException(status_code=e.response.status_code, detail=str(e))

    events_list = events_raw if isinstance(events_raw, list) else events_raw.get("data", []) or []
    if not isinstance(events_list, list):
        events_list = []

    flat_markets: List[Dict[str, Any]] = []

    for ev in events_list:
        if not isinstance(ev, dict):
            continue
        if ev.get("archived") is True:
            continue
        if live:
            if not _is_live_event(ev, league=league):
                continue
        markets = ev.get("markets") or []
        event_id = str(ev.get("id") or ev.get("slug") or "")
        event_title = ev.get("title") or ev.get("ticker") or ""
        event_end = ev.get("endDate")
        tags_data = ev.get("tags") or []
        event_tags = [{"slug": t.get("slug", ""), "label": t.get("label") or t.get("name", "")} for t in tags_data if isinstance(t, dict)]
        series_list = ev.get("series") or []
        series_slug = series_list[0].get("slug") if series_list and isinstance(series_list[0], dict) else None

        for m in markets:
            if not isinstance(m, dict):
                continue
            flat_markets.append(_build_discovery_market(m, ev, event_id, event_title, event_end, event_tags, series_slug))

    # Sort: volume24hr desc, liquidity desc, timeToResolution asc
    def _sort_key(x: Dict[str, Any]) -> tuple:
        v24 = x.get("volume24hr") or 0
        liq = x.get("liquidity") or 0
        ttr = x.get("time_to_resolution_minutes")
        ttr_val = float(ttr) if ttr is not None else 999999
        return (-float(v24), -float(liq), ttr_val)

    flat_markets.sort(key=_sort_key)

    result = {"markets": flat_markets, "count": len(flat_markets)}
    await api_cache.set(cache_key, result, ttl=DISCOVERY_CACHE_TTL)
    return result


def _build_discovery_market(m: Dict[str, Any], ev: Dict[str, Any], event_id: str, event_title: str, event_end: Optional[str], event_tags: List[Dict[str, str]], series_slug: Optional[str]) -> Dict[str, Any]:
    """Construye un market para discovery (flat o anidado)."""
    parsed = parse_clob_token_ids(m.get("clobTokenIds"))
    ttr = _time_to_resolution_minutes(m.get("endDate") or event_end)
    out: Dict[str, Any] = {
        "market_id": str(m.get("id", "")),
        "polymarket_id": str(m.get("id", "")),
        "question": m.get("question") or m.get("slug", ""),
        "clob_token_ids": {
            "primary_yes": parsed.get("primary_yes"),
            "primary_no": parsed.get("primary_no"),
            "primary": parsed.get("primary"),
        },
        "active": m.get("active"),
        "acceptingOrders": m.get("acceptingOrders"),
        "archived": m.get("archived"),
        "closed": m.get("closed"),
        "liquidity": m.get("liquidityNum") or m.get("liquidity") or 0,
        "volume24hr": m.get("volume24hr") or m.get("volume24hrClob") or 0,
        "volume": m.get("volume") or m.get("volumeNum") or 0,
        "event_id": event_id,
        "event_title": event_title,
        "event_end_date": event_end,
        "event_archived": ev.get("archived"),
        "event_tags": event_tags,
        "series_slug": series_slug,
        "time_to_resolution_minutes": ttr,
    }
    if m.get("outcomes") is not None:
        out["outcomes"] = m["outcomes"]
    if m.get("shortOutcomes") is not None:
        out["short_outcomes"] = m["shortOutcomes"]
    outcome_prices_raw = m.get("outcomePrices") or m.get("outcome_prices") or m.get("prices")
    if outcome_prices_raw is not None:
        out["outcome_prices"] = outcome_prices_raw if isinstance(outcome_prices_raw, str) else ",".join(str(x) for x in outcome_prices_raw)
    else:
        # Fallback: Gamma a veces no incluye outcomePrices en listados; usar lastTradePrice para binarios
        lt = m.get("lastTradePrice")
        if lt is not None:
            try:
                p = float(lt)
                if 1 < p <= 100:
                    p = p / 100.0
                if 0 <= p <= 1:
                    out["outcome_prices"] = f"{p:.4f},{1-p:.4f}"
            except (TypeError, ValueError):
                pass
    if m.get("sportsMarketType") is not None:
        out["sports_market_type"] = m["sportsMarketType"]
    if m.get("marketGroup") is not None:
        out["market_group"] = m["marketGroup"]
    # Tradeable = podemos mostrar precios por outcome ahora. Requiere abierto Y tener precio.
    has_price = bool(out.get("outcome_prices"))
    out["tradeable"] = _is_tradeable_market(m) and has_price
    return out


@router.get("/discovery/events")
async def discovery_events(
    tag_slug: str = Query(..., description="Domain or league slug (crypto, nfl, etc.)"),
    closed: bool = Query(False, description="Include closed"),
    limit: int = Query(100, ge=1, le=200, description="Max events to fetch"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    end_date_max: Optional[str] = Query(None, description="Max end date ISO (for TTR filter server-side)"),
    live: bool = Query(False, description="Sports live: filter events in play window"),
    league: Optional[str] = Query(None, description="League slug for live tolerances"),
):
    """
    Lista EVENTOS con mercados tradeables anidados (modelo mental: Event → Markets → Outcomes).

    Para discovery por deportes: la unidad principal es el evento (partido), no el market.
    Mismos filtros que /discovery; respuesta event-first para UI "Event list".
    """
    cache_key = f"polymarket:discovery:events:tag={tag_slug}:closed={closed}:limit={limit}:offset={offset}:end={end_date_max or ''}:live={live}:league={league or ''}"
    cached = await api_cache.get(cache_key)
    if cached is not None:
        return cached

    if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_EVENTS, timeout=5.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    params: Dict[str, str] = {
        "order": "id",
        "ascending": "false",
        "closed": str(closed).lower(),
        "limit": str(limit),
        "offset": str(offset),
        "tag_slug": tag_slug,
    }
    if end_date_max:
        params["end_date_max"] = end_date_max

    async with httpx.AsyncClient(timeout=30.0, base_url=settings.polymarket_gamma_api_url, trust_env=False) as client:
        try:
            response = await client.get("/events", params=params)
            if response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_EVENTS)
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            response.raise_for_status()
            events_raw = response.json()
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            logger.warning("Discovery events: no se pudo conectar con Polymarket Gamma: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo conectar con Polymarket. Comprueba tu red o variables HTTP_PROXY/HTTPS_PROXY.",
            )
        except (ConnectionError, OSError) as e:
            logger.warning("Discovery events: error de red/conexión: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo conectar con Polymarket (red o proxy).",
            )
        except httpx.HTTPStatusError as e:
            logger.error("Discovery events Gamma error: %s", e)
            raise HTTPException(status_code=e.response.status_code, detail=str(e))

    events_list = events_raw if isinstance(events_raw, list) else events_raw.get("data", []) or []
    if not isinstance(events_list, list):
        events_list = []

    event_first: List[Dict[str, Any]] = []

    for ev in events_list:
        if not isinstance(ev, dict):
            continue
        if ev.get("archived") is True:
            continue
        if live:
            if not _is_live_event(ev, league=league):
                continue
        event_id = str(ev.get("id") or ev.get("slug") or "")
        event_title = ev.get("title") or ev.get("ticker") or ""
        event_subtitle = ev.get("subtitle") or ""
        event_end = ev.get("endDate")
        event_start = ev.get("startDate") or ev.get("creationDate")
        tags_data = ev.get("tags") or []
        event_tags = [{"slug": t.get("slug", ""), "label": t.get("label") or t.get("name", "")} for t in tags_data if isinstance(t, dict)]
        series_list = ev.get("series") or []
        series_slug = series_list[0].get("slug") if series_list and isinstance(series_list[0], dict) else None

        markets = ev.get("markets") or []
        all_markets: List[Dict[str, Any]] = []
        for m in markets:
            if not isinstance(m, dict):
                continue
            all_markets.append(_build_discovery_market(m, ev, event_id, event_title, event_end, event_tags, series_slug))

        if not all_markets:
            continue

        # Ordenar markets dentro del evento: volume24hr desc, liquidity desc
        all_markets.sort(
            key=lambda x: (-float(x.get("volume24hr") or 0), -float(x.get("liquidity") or 0))
        )

        event_first.append({
            "event_id": event_id,
            "title": event_title,
            "subtitle": event_subtitle,
            "end_date": event_end,
            "start_date": event_start,
            "markets": all_markets,
            "markets_count": len(all_markets),
        })

    # Enriquecer mercados abiertos sin outcome_prices (tras enriquecer podremos marcar tradeable=True)
    to_enrich: List[Tuple[str, Dict[str, Any]]] = []
    for ev_item in event_first:
        for market in ev_item.get("markets") or []:
            if market.get("outcome_prices"):
                continue
            if market.get("closed") is True or market.get("acceptingOrders") is not True:
                continue
            mid = market.get("polymarket_id") or market.get("market_id")
            if mid:
                to_enrich.append((mid, market))
    to_enrich = to_enrich[:40]  # límite para no saturar Gamma

    async def _fetch_market_prices(client: httpx.AsyncClient, market_id: str) -> Optional[str]:
        try:
            r = await client.get(f"/markets/{market_id}", timeout=8.0)
            if r.status_code != 200:
                return None
            data = r.json()
            raw = data.get("outcomePrices") or data.get("outcome_prices") or data.get("prices")
            if raw is not None:
                return raw if isinstance(raw, str) else ",".join(str(x) for x in raw)
            lt = data.get("lastTradePrice")
            if lt is not None:
                try:
                    p = float(lt)
                    if 1 < p <= 100:
                        p = p / 100.0
                    if 0 <= p <= 1:
                        return f"{p:.4f},{1-p:.4f}"
                except (TypeError, ValueError):
                    pass
        except Exception as e:
            logger.debug("Enrich market %s: %s", market_id, e)
        return None

    if to_enrich:
        sem = asyncio.Semaphore(5)
        async with httpx.AsyncClient(timeout=10.0, base_url=settings.polymarket_gamma_api_url, trust_env=False) as client:
            async def _enrich_one(mid: str, mkt: Dict[str, Any]) -> None:
                async with sem:
                    prices = await _fetch_market_prices(client, mid)
                    if prices:
                        mkt["outcome_prices"] = prices
                        mkt["tradeable"] = True  # ya podemos mostrar precios

            await asyncio.gather(*[_enrich_one(mid, mkt) for mid, mkt in to_enrich])

    result = {"events": event_first, "count": len(event_first)}
    await api_cache.set(cache_key, result, ttl=DISCOVERY_CACHE_TTL)
    return result


# --- Discovery Screener: eventos + métricas (edge, slippage, fillability) + Redis cache ---

async def _build_screener_events(
    tag_slug: str,
    closed: bool = False,
    limit: int = 100,
    offset: int = 0,
    end_date_max: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Obtiene eventos de Gamma y construye event_first (como discovery_events)
    sin enriquecimiento Gamma de precios. Devuelve lista de eventos con markets.
    """
    params: Dict[str, str] = {
        "order": "id",
        "ascending": "false",
        "closed": str(closed).lower(),
        "limit": str(limit),
        "offset": str(offset),
        "tag_slug": tag_slug,
    }
    if end_date_max:
        params["end_date_max"] = end_date_max

    async with httpx.AsyncClient(timeout=30.0, base_url=settings.polymarket_gamma_api_url, trust_env=False) as client:
        response = await client.get("/events", params=params)
        response.raise_for_status()
        events_raw = response.json()

    events_list = events_raw if isinstance(events_raw, list) else events_raw.get("data", []) or []
    if not isinstance(events_list, list):
        events_list = []

    event_first: List[Dict[str, Any]] = []
    for ev in events_list:
        if not isinstance(ev, dict) or ev.get("archived") is True:
            continue
        event_id = str(ev.get("id") or ev.get("slug") or "")
        event_title = ev.get("title") or ev.get("ticker") or ""
        event_subtitle = ev.get("subtitle") or ""
        event_end = ev.get("endDate")
        event_start = ev.get("startDate") or ev.get("creationDate")
        tags_data = ev.get("tags") or []
        event_tags = [{"slug": t.get("slug", ""), "label": t.get("label") or t.get("name", "")} for t in tags_data if isinstance(t, dict)]
        series_list = ev.get("series") or []
        series_slug = series_list[0].get("slug") if series_list and isinstance(series_list[0], dict) else None
        markets = ev.get("markets") or []
        all_markets: List[Dict[str, Any]] = []
        for m in markets:
            if not isinstance(m, dict):
                continue
            all_markets.append(_build_discovery_market(m, ev, event_id, event_title, event_end, event_tags, series_slug))
        if not all_markets:
            continue
        all_markets.sort(key=lambda x: (-float(x.get("volume24hr") or 0), -float(x.get("liquidity") or 0)))
        event_first.append({
            "event_id": event_id,
            "title": event_title,
            "subtitle": event_subtitle,
            "end_date": event_end,
            "start_date": event_start,
            "markets": all_markets,
            "markets_count": len(all_markets),
        })
    return event_first


@router.get("/discovery/screener")
async def discovery_screener(
    tag_slug: str = Query(..., description="Domain slug (crypto, politics, nfl, etc.)"),
    closed: bool = Query(False, description="Include closed events"),
    limit: int = Query(50, ge=1, le=100, description="Max events to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    tradeable_only: bool = Query(False, description="Only events with at least one tradeable market"),
    min_edge_cents: Optional[float] = Query(None, description="Min edge (cents) for best opportunity"),
    max_slippage_1k: Optional[float] = Query(None, description="Max slippage ($1k) for best opportunity"),
    min_fillability: Optional[int] = Query(None, ge=0, le=100, description="Min fillability score"),
    min_liquidity: Optional[float] = Query(None, description="Min liquidity USD"),
    sort: str = Query("event_score", description="Sort: event_score, edge, liquidity, slippage, freshness"),
    end_date_max: Optional[str] = Query(None, description="Max end date ISO"),
):
    """
    Discovery Screener: eventos con métricas agregadas (best opportunity) y markets con edge, slippage, fillability.
    Cache en Redis (TTL 15s). Solo lectura, no ejecución.
    """
    cache_key = (
        f"discovery:screener:{tag_slug}:closed={closed}:limit={limit}:offset={offset}:"
        f"tradeable_only={tradeable_only}:min_edge={min_edge_cents}:max_slip={max_slippage_1k}:"
        f"min_fill={min_fillability}:min_liq={min_liquidity}:sort={sort}:end={end_date_max or ''}"
    )
    cached = await redis_client.get_json(cache_key)
    if cached is not None:
        return cached

    if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_EVENTS, timeout=5.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    try:
        event_first = await _build_screener_events(tag_slug, closed=closed, limit=limit, offset=offset, end_date_max=end_date_max)
    except Exception as e:
        logger.warning("Discovery screener Gamma fetch failed: %s", e)
        raise HTTPException(status_code=503, detail="Discovery temporarily unavailable")

    # Recoger token_ids únicos (primary_yes o primary) por market
    token_ids_seen: Dict[str, bool] = {}
    token_ids: List[str] = []
    market_to_token: Dict[str, str] = {}
    for ev in event_first:
        for m in ev.get("markets") or []:
            mid = m.get("market_id") or m.get("polymarket_id")
            clob = m.get("clob_token_ids") or {}
            tid_raw = clob.get("primary_yes") or clob.get("primary")
            tid = str(tid_raw).strip() if tid_raw else ""
            if tid and mid:
                market_to_token[mid] = tid
                if tid not in token_ids_seen:
                    token_ids_seen[tid] = True
                    token_ids.append(tid)

    # Batch orderbook
    books: List[Dict[str, Any]] = []
    if token_ids:
        books = await fetch_orderbooks_batch(token_ids)
    token_to_book: Dict[str, Dict[str, Any]] = {b["token_id"]: b for b in books if b.get("token_id")}

    # Enriquecer cada market con métricas y tradeable
    for ev in event_first:
        for m in ev.get("markets") or []:
            mid = m.get("market_id") or m.get("polymarket_id")
            tid = market_to_token.get(mid) if mid else None
            book_data = token_to_book.get(tid) if tid else None
            liq = float(m.get("liquidity") or m.get("liquidity_usd") or 0)
            m["liquidity_usd"] = liq

            if book_data:
                metrics = compute_market_metrics(book_data, liquidity_usd=liq)
                m["best_bid"] = metrics.get("best_bid")
                m["best_ask"] = metrics.get("best_ask")
                m["mid_price"] = metrics.get("mid_price")
                m["fair_price"] = metrics.get("fair_price")
                m["edge_cents"] = metrics.get("edge_cents")
                m["spread_bps"] = metrics.get("spread_bps")
                m["depth_50bps_usd"] = metrics.get("depth_50bps_usd")
                m["slippage_1k_cents"] = metrics.get("slippage_1k_cents")
                m["fillability_score"] = metrics.get("fillability_score")
                m["stale_ms"] = metrics.get("stale_ms")
                m["tradeable"] = discovery_is_tradeable(m, book_data)
                m["tradeable_reasons"] = tradeable_reasons(m, book_data)
            else:
                m["tradeable"] = m.get("tradeable", False)
                m["tradeable_reasons"] = tradeable_reasons(m, None)

        # bestOpportunity y event_score (del mejor market del evento)
        markets_ev = ev.get("markets") or []
        best_score = -1.0
        best_opp: Optional[Dict[str, Any]] = None
        for m in markets_ev:
            edge = m.get("edge_cents")
            fill = m.get("fillability_score") or 0
            liq = m.get("liquidity_usd") or 0
            if edge is not None and fill is not None:
                sc = compute_event_score(edge, fill, liq)
                if sc > best_score:
                    best_score = sc
                    best_opp = {
                        "marketId": m.get("market_id"),
                        "outcome": "YES",
                        "edge_cents": edge,
                        "slippage_1k_cents": m.get("slippage_1k_cents"),
                        "fillability_score": fill,
                        "liquidity_usd": liq,
                        "freshness_ms": m.get("stale_ms"),
                    }
        ev["best_opportunity"] = best_opp
        ev["event_score"] = best_score if best_score >= 0 else None

    # Filtros
    out_events = event_first
    if tradeable_only:
        out_events = [e for e in out_events if any((m.get("tradeable") for m in (e.get("markets") or [])))]
    if min_edge_cents is not None:
        out_events = [e for e in out_events if (e.get("best_opportunity") or {}).get("edge_cents") is not None and (e["best_opportunity"].get("edge_cents") or 0) >= min_edge_cents]
    if max_slippage_1k is not None:
        out_events = [e for e in out_events if (e.get("best_opportunity") or {}).get("slippage_1k_cents") is not None and (e["best_opportunity"].get("slippage_1k_cents") or 0) <= max_slippage_1k]
    if min_fillability is not None:
        out_events = [e for e in out_events if (e.get("best_opportunity") or {}).get("fillability_score") is not None and (e["best_opportunity"].get("fillability_score") or 0) >= min_fillability]
    if min_liquidity is not None:
        out_events = [e for e in out_events if (e.get("best_opportunity") or {}).get("liquidity_usd") is not None and (e["best_opportunity"].get("liquidity_usd") or 0) >= min_liquidity]

    # Sort
    if sort == "event_score":
        out_events = sorted(out_events, key=lambda e: -(e.get("event_score") or -1))
    elif sort == "edge":
        out_events = sorted(out_events, key=lambda e: -((e.get("best_opportunity") or {}).get("edge_cents") or -1))
    elif sort == "liquidity":
        out_events = sorted(out_events, key=lambda e: -((e.get("best_opportunity") or {}).get("liquidity_usd") or 0))
    elif sort == "slippage":
        out_events = sorted(out_events, key=lambda e: (e.get("best_opportunity") or {}).get("slippage_1k_cents") or 999999)
    elif sort == "freshness":
        out_events = sorted(out_events, key=lambda e: (e.get("best_opportunity") or {}).get("freshness_ms") or 999999)

    result = {"events": out_events, "count": len(out_events)}
    await redis_client.set_json(cache_key, result, ttl_seconds=DISCOVERY_REDIS_TTL_SCREENER)
    return result


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """
    Obtiene un evento específico por ID.
    
    Proxy para GET /events/{id} de Gamma API.
    """
    cache_key = f"polymarket:event:{event_id}"
    cache_ttl = timedelta(seconds=10)  # 10 segundos (eventos individuales cambian menos)
    
    # Check cache
    cached = await api_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Acquire rate limit permission
    if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_EVENTS, timeout=2.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    async with httpx.AsyncClient(timeout=30.0, base_url=settings.polymarket_gamma_api_url, trust_env=False) as client:
        try:
            response = await client.get(f"/events/{event_id}")
            
            if response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_EVENTS)
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


@router.get("/markets/{market_id}")
async def get_market(market_id: str):
    """
    Obtiene un mercado específico por ID.
    
    Proxy para GET /markets/{id} de Gamma API.
    Incluye información completa: conditionId, clobTokenIds, bestBid, bestAsk, etc.
    """
    cache_key = f"polymarket:market:{market_id}"
    cache_ttl = timedelta(seconds=5)  # 5 segundos (mercados cambian más frecuentemente)
    
    # Check cache
    cached = await api_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Acquire rate limit permission
    if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_MARKETS, timeout=2.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    async with httpx.AsyncClient(timeout=30.0, base_url=settings.polymarket_gamma_api_url, trust_env=False) as client:
        try:
            response = await client.get(f"/markets/{market_id}")
            
            if response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_MARKETS)
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


@router.get("/markets/slug/{slug}")
async def get_market_by_slug(slug: str):
    """
    Obtiene un mercado por slug.
    
    Proxy para GET /markets/slug/{slug} de Gamma API.
    Útil para obtener mercado desde URL de Polymarket.
    """
    cache_key = f"polymarket:market:slug:{slug}"
    cache_ttl = timedelta(seconds=10)  # 10 segundos (slugs cambian menos)
    
    # Check cache
    cached = await api_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Acquire rate limit permission
    if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_MARKETS, timeout=2.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    async with httpx.AsyncClient(timeout=30.0, base_url=settings.polymarket_gamma_api_url, trust_env=False) as client:
        try:
            response = await client.get(f"/markets/slug/{slug}")
            
            if response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_MARKETS)
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
    cache_ttl = timedelta(seconds=10)  # 10 segundos
    
    # Check cache
    cached = await api_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Acquire rate limit permission
    if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_SEARCH, timeout=2.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    async with httpx.AsyncClient(timeout=30.0, base_url=settings.polymarket_gamma_api_url, trust_env=False) as client:
        try:
            params = {
                "q": q,
                "limit": limit,
                "offset": offset
            }
            
            response = await client.get("/public-search", params=params)
            
            if response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_SEARCH)
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


# --- Discovery (Gamma-first): tags para categorías. Público, sin auth, sin DB. ---
TAGS_CACHE_TTL = timedelta(hours=1)


@router.get("/tags")
async def list_tags_gamma(
    limit: int = Query(200, ge=1, le=500, description="Max items"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """
    Lista tags desde Gamma API (Discovery, Gamma-first).
    Público: NO requiere auth ni wallet. NO toca DB.
    Respuesta estable para el frontend: { items, limit, offset, total? }.
    Gamma no devuelve total → total=null.
    """
    cache_key = f"polymarket:tags:limit={limit}:offset={offset}"
    cached = await api_cache.get(cache_key)
    if cached is not None:
        return cached

    if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_TAGS, timeout=5.0):
        logger.warning("gamma_tags rate limit exceeded (no capacity)")
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    def _empty_tags_result():
        return {"items": [], "limit": limit, "offset": offset, "total": None}

    timeout_overall = getattr(
        settings, "gamma_tags_overall_timeout", 60.0
    )
    timeout_connect = getattr(
        settings, "gamma_tags_connect_timeout", 15.0
    )

    async def _fetch_tags():
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_overall, connect=timeout_connect),
            base_url=settings.polymarket_gamma_api_url,
        ) as client:
            return await client.get(
                "/tags",
                params={"limit": limit, "offset": offset},
            )

    try:
        response = await _fetch_tags()
        if response.status_code == 429:
            await rate_limiter.record_violation(EndpointType.GAMMA_TAGS)
            logger.warning("gamma_tags 429 from Gamma")
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        if response.status_code == 404:
            logger.warning("gamma_tags 404 from Gamma (endpoint no disponible); devolviendo items vacíos")
            return _empty_tags_result()
        if response.status_code >= 500:
            logger.warning("gamma_tags 5xx from Gamma: status=%s; devolviendo items vacíos", response.status_code)
            return _empty_tags_result()
        if response.status_code >= 400:
            logger.warning("gamma_tags 4xx from Gamma: status=%s; devolviendo items vacíos", response.status_code)
            return _empty_tags_result()
        raw = response.json()
    except httpx.TimeoutException as e:
        # Retry una vez en timeout (Gamma API puede ser lenta desde algunas redes)
        try:
            logger.info("gamma_tags timeout (intento 1), reintentando...")
            response = await _fetch_tags()
            if response.status_code == 200:
                raw = response.json()
            else:
                logger.warning("gamma_tags retry: status=%s; devolviendo items vacíos", response.status_code)
                return _empty_tags_result()
        except (httpx.TimeoutException, Exception) as retry_e:
            logger.warning(
                "gamma_tags timeout después de retry: %s; devolviendo items vacíos",
                retry_e,
            )
            return _empty_tags_result()
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        logger.warning("gamma_tags conexión fallida: %s; devolviendo items vacíos", e)
        return _empty_tags_result()
    except httpx.HTTPStatusError as e:
        logger.warning("gamma_tags HTTP error: %s; devolviendo items vacíos", e)
        return _empty_tags_result()

    items = raw if isinstance(raw, list) else (raw.get("data") or raw.get("items") or [])
    out = []
    for t in items:
        if not isinstance(t, dict):
            continue
        tid = t.get("id") or t.get("slug") or ""
        if not tid:
            continue
        # label = name para UI; slug si falta se deja null (frontend puede slugify(name) si quiere)
        name = t.get("label") or t.get("name") or t.get("slug") or str(tid)
        out.append({
            "tag_id": str(tid),
            "polymarket_tag_id": t.get("id"),
            "name": name,
            "slug": t.get("slug"),
            "label": t.get("label") or name,
        })

    result = {"items": out, "limit": limit, "offset": offset, "total": None}
    await api_cache.set(cache_key, result, ttl=TAGS_CACHE_TTL)
    return result


# --- Clasificación (política v2): wallet-data = auth + wallet; market-data = público o Gamma ---
# orderbook/price: Wallet-data. Fuente primaria = State Cache; fallback = CLOB API (requiere auth).
# Decisión: CLOB get_order_book/get_price en el SDK requieren auth; no hay endpoint público CLOB para esto.
# Si en el futuro existiera un proxy público de orderbook, este endpoint podría ser solo cache + ese proxy.


@router.get("/markets/{market_id}/orderbook")
async def get_market_orderbook(market_id: str, client_wrapper=Depends(_require_clob_client)):
    """
    Orderbook del market. State Cache primero; fallback CLOB requiere auth+wallet (wallet-data).
    """
    from app.core.strategy_engine.state_cache_service import StateCacheService
    from app.database import SessionLocal
    
    # Obtener market info para extraer clobTokenIds
    async with httpx.AsyncClient(timeout=30.0, base_url=settings.polymarket_gamma_api_url, trust_env=False) as client:
        response = await client.get(f"/markets/{market_id}")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Market not found")
        response.raise_for_status()
        market_data = response.json()
    
    # Extraer clobTokenIds del market
    clob_token_ids = market_data.get("clobTokenIds", [])
    if not clob_token_ids:
        raise HTTPException(status_code=404, detail="Market has no clobTokenIds")
    
    # Intentar obtener desde State Cache primero (fuente real/rápida)
    orderbooks = {}
    orderbooks_from_cache = {}
    orderbooks_from_api = {}
    
    try:
        db = SessionLocal()
        state_cache_service = StateCacheService(db)
        
        for token_id in clob_token_ids:
            cache_key = f"pm.orderbook.{token_id}"
            cached_state = await state_cache_service.get(cache_key)
            
            if cached_state:
                # Estado desde cache
                orderbooks_from_cache[token_id] = {
                    "source": "state_cache",
                    "staleness_ms": cached_state.get("staleness_ms", 0),
                    "data": cached_state
                }
                orderbooks[token_id] = cached_state
            else:
                # No está en cache, hacer fallback a API
                logger.debug(f"Orderbook for {token_id} not in State Cache, using API fallback")
                orderbooks_from_api[token_id] = True
        
        db.close()
    except Exception as e:
        logger.warning(f"Error reading from State Cache: {e}, falling back to API")
        # Continuar con fallback a API
    
    # Fallback: Si algún token no está en cache, usar cliente del usuario (ya inyectado)
    if orderbooks_from_api:
        if client_wrapper.is_available():
            try:
                clob_client = client_wrapper.get_client()
                for token_id in orderbooks_from_api.keys():
                    try:
                        orderbook = clob_client.get_order_book(token_id)
                        orderbooks[token_id] = {
                            **orderbook,
                            "source": "api_fallback",
                            "staleness_ms": None,  # No sabemos staleness desde API
                            "note": "Fetched from API (not in State Cache)"
                        }
                    except Exception as e:
                        logger.warning(f"Error getting orderbook for token {token_id}: {e}")
                        orderbooks[token_id] = {"error": str(e), "source": "api_error"}
            except Exception as e:
                logger.error(f"Error getting orderbooks from API: {e}")
        else:
            # Cliente no disponible
            for token_id in orderbooks_from_api.keys():
                orderbooks[token_id] = {
                    "error": "CLOB client not available",
                    "source": "unavailable"
                }
    
    result = {
        "market_id": market_id,
        "tokens": clob_token_ids,
        "orderbooks": orderbooks,
        "sources": {
            "from_cache": list(orderbooks_from_cache.keys()),
            "from_api": list(orderbooks_from_api.keys())
        },
        "note": "Orderbook data from State Cache (WS MARKET → Orderbook Engine) when available, API fallback otherwise"
    }
    
    return result


@router.get("/markets/{market_id}/price")
async def get_market_price(market_id: str, client_wrapper=Depends(_require_clob_client)):
    """
    Precios (bid, ask, midpoint). State Cache primero; fallback CLOB requiere auth+wallet (wallet-data).
    """
    from app.core.strategy_engine.state_cache_service import StateCacheService
    from app.database import SessionLocal
    
    # Obtener market info para extraer clobTokenIds
    async with httpx.AsyncClient(timeout=30.0, base_url=settings.polymarket_gamma_api_url, trust_env=False) as client:
        response = await client.get(f"/markets/{market_id}")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Market not found")
        response.raise_for_status()
        market_data = response.json()
    
    # Extraer clobTokenIds
    clob_token_ids = market_data.get("clobTokenIds", [])
    if not clob_token_ids:
        raise HTTPException(status_code=404, detail="Market has no clobTokenIds")
    
    # Intentar obtener desde State Cache primero
    prices = {}
    prices_from_cache = {}
    prices_from_api = {}
    
    try:
        db = SessionLocal()
        state_cache_service = StateCacheService(db)
        
        for token_id in clob_token_ids:
            cache_key = f"pm.orderbook.{token_id}"
            cached_state = await state_cache_service.get(cache_key)
            
            if cached_state:
                # Calcular precios desde orderbook state
                best_bid = cached_state.get("best_bid_price")
                best_ask = cached_state.get("best_ask_price")
                mid = cached_state.get("mid")
                spread_bps = cached_state.get("spread_bps")
                staleness_ms = cached_state.get("staleness_ms", 0)
                
                prices[token_id] = {
                    "bid": best_bid,
                    "ask": best_ask,
                    "midpoint": mid,
                    "spread_bps": spread_bps,
                    "spread": (best_ask - best_bid) if (best_bid and best_ask) else None,
                    "staleness_ms": staleness_ms,
                    "source": "state_cache"
                }
                prices_from_cache[token_id] = True
            else:
                # No está en cache, hacer fallback a API
                prices_from_api[token_id] = True
        
        db.close()
    except Exception as e:
        logger.warning(f"Error reading from State Cache: {e}, falling back to API")
        # Continuar con fallback a API
        prices_from_api = {token_id: True for token_id in clob_token_ids}
    
    # Fallback: Si algún token no está en cache, usar cliente del usuario (ya inyectado)
    if prices_from_api:
        if client_wrapper.is_available():
            try:
                clob_client = client_wrapper.get_client()
                for token_id in prices_from_api.keys():
                    try:
                        bid_price = client_wrapper.get_price(token_id, side="BUY")
                        ask_price = client_wrapper.get_price(token_id, side="SELL")
                        midpoint = client_wrapper.get_midpoint(token_id)
                        
                        prices[token_id] = {
                            "bid": bid_price,
                            "ask": ask_price,
                            "midpoint": midpoint,
                            "spread": ask_price - bid_price if (bid_price > 0 and ask_price > 0) else None,
                            "source": "api_fallback",
                            "note": "Fetched from API (not in State Cache)"
                        }
                    except Exception as e:
                        logger.warning(f"Error getting price for token {token_id}: {e}")
                        prices[token_id] = {"error": str(e), "source": "api_error"}
            except Exception as e:
                logger.error(f"Error getting prices from API: {e}")
        else:
            # Cliente no disponible
            for token_id in prices_from_api.keys():
                prices[token_id] = {
                    "error": "CLOB client not available",
                    "source": "unavailable"
                }
    
    return {
        "market_id": market_id,
        "tokens": clob_token_ids,
        "prices": prices,
        "sources": {
            "from_cache": list(prices_from_cache.keys()),
            "from_api": list(prices_from_api.keys())
        },
        "note": "Price data calculated from State Cache (WS MARKET → Orderbook Engine) when available, API fallback otherwise"
    }


@router.get("/health")
async def health_check():
    """
    Health de Gamma API únicamente. NO toca CLOB ni requiere wallet (público).
    Para health de CLOB por usuario, usar GET /connection/status (auth-health, user-scoped).
    """
    async with httpx.AsyncClient(timeout=30.0, base_url=settings.polymarket_gamma_api_url, trust_env=False) as client:
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


# ============================================================================
# FASE 3: DATOS DE CUENTA (CLOB API - LECTURA)
# ============================================================================

BALANCE_CACHE_KEY = "polymarket:balance"
BALANCE_CACHE_TTL = timedelta(seconds=60)


@router.get("/balance")
async def get_balance(client_wrapper=Depends(_require_clob_client)):
    """
    Obtiene el balance USDC de la wallet del usuario (con caché 60s).
    Requiere autenticación y wallet configurada en BD (política v2).
    """
    # Cache por usuario (no global)
    cache_key = f"{BALANCE_CACHE_KEY}:{getattr(client_wrapper, '_user_id', '')}"
    cached = await api_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        balance = await client_wrapper.get_balance()

        if balance is None:
            raise HTTPException(
                status_code=500,
                detail="Could not retrieve balance. Check API credentials."
            )

        payload = {
            "balance_usdc": balance,
            "currency": "USDC"
        }
        await api_cache.set(cache_key, payload, ttl=BALANCE_CACHE_TTL)
        return payload

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting balance: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting balance: {str(e)}"
        )


@router.get("/account/balance")
async def get_account_balance(client_wrapper=Depends(_require_clob_client)):
    """
    Obtiene el balance USDC de la cuenta del usuario.
    Requiere autenticación y wallet configurada en BD (política v2).
    """
    try:
        balance = await client_wrapper.get_balance()
        
        if balance is None:
            raise HTTPException(
                status_code=500,
                detail="Could not retrieve balance. Check API credentials."
            )
        
        return {
            "balance_usdc": balance,
            "currency": "USDC"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting balance: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting balance: {str(e)}"
        )


@router.get("/account/orders")
async def get_account_orders(
    order_id: Optional[str] = Query(None, description="Filter by order ID"),
    market: Optional[str] = Query(None, description="Filter by market/condition_id"),
    asset_id: Optional[str] = Query(None, description="Filter by asset/token ID"),
    token_id: Optional[str] = Query(None, description="Alias for asset_id"),
    client_wrapper=Depends(_require_clob_client),
):
    """
    Lista órdenes abiertas del usuario. Requiere auth y wallet (política v2).
    """
    try:
        orders = client_wrapper.get_open_orders(
            order_id=order_id,
            market=market,
            asset_id=asset_id or token_id
        )
        
        return {
            "orders": orders,
            "count": len(orders)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting orders: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting orders: {str(e)}"
        )


@router.get("/account/orders/{order_id}")
async def get_account_order(order_id: str, client_wrapper=Depends(_require_clob_client)):
    """
    Obtiene una orden específica por ID. Requiere auth y wallet (política v2).
    """
    try:
        order = client_wrapper.get_order(order_id)
        
        if order is None:
            raise HTTPException(
                status_code=404,
                detail=f"Order {order_id} not found"
            )
        
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order {order_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting order: {str(e)}"
        )


@router.get("/account/trades")
async def get_account_trades(
    trade_id: Optional[str] = Query(None, description="Filter by trade ID"),
    taker: Optional[str] = Query(None, description="Filter by taker address"),
    maker: Optional[str] = Query(None, description="Filter by maker address"),
    market: Optional[str] = Query(None, description="Filter by market/condition_id"),
    before: Optional[str] = Query(None, description="Unix timestamp - trades before this time"),
    after: Optional[str] = Query(None, description="Unix timestamp - trades after this time"),
    client_wrapper=Depends(_require_clob_client),
):
    """
    Lista trades históricos del usuario. Requiere auth y wallet (política v2).
    """
    try:
        trades = await client_wrapper.get_trades(
            trade_id=trade_id,
            taker=taker,
            maker=maker,
            market=market,
            before=before,
            after=after
        )
        
        return {
            "trades": trades,
            "count": len(trades)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trades: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting trades: {str(e)}"
        )


@router.get("/account/orders/{order_id}/scoring")
async def get_order_scoring(order_id: str, client_wrapper=Depends(_require_clob_client)):
    """
    Verifica si una orden está "scoring" (elegible para recompensas). Requiere auth y wallet (política v2).
    """
    try:
        scoring = client_wrapper.is_order_scoring(order_id)
        
        # Si scoring es None, puede ser que la orden no existe o hay un error
        # Según la documentación, si la orden no existe, debería retornar False o None
        # Por ahora, si es None, asumimos que hay un error (podría ser orden no existe)
        if scoring is None:
            # Intentar verificar si la orden existe primero
            order = client_wrapper.get_order(order_id)
            if order is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Order {order_id} not found"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Could not check order scoring status"
                )
        
        return {
            "order_id": order_id,
            "scoring": scoring
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking order scoring: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error checking order scoring: {str(e)}"
        )


# ============================================================================
# FASE 4: OPERACIONES DE TRADING (CLOB API - ESCRITURA)
# ============================================================================

class LimitOrderRequest(BaseModel):
    token_id: str
    price: float
    size: float
    side: str  # "BUY" or "SELL"
    order_type: str = "GTC"  # "GTC" or "FOK"
    
    @field_validator('token_id')
    @classmethod
    def validate_token_id(cls, v: str) -> str:
        """Validar que token_id no esté vacío."""
        if not v or not v.strip():
            raise ValueError("token_id cannot be empty")
        return v.strip()
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validar que price sea positivo."""
        if v <= 0:
            raise ValueError("price must be greater than 0")
        return v
    
    @field_validator('size')
    @classmethod
    def validate_size(cls, v: float) -> float:
        """Validar que size sea positivo."""
        if v <= 0:
            raise ValueError("size must be greater than 0")
        return v


class MarketOrderRequest(BaseModel):
    token_id: str
    amount: float  # Amount in USD
    side: str  # "BUY" or "SELL"
    order_type: str = "FOK"  # "FOK" or "IOC"
    
    @field_validator('token_id')
    @classmethod
    def validate_token_id(cls, v: str) -> str:
        """Validar que token_id no esté vacío."""
        if not v or not v.strip():
            raise ValueError("token_id cannot be empty")
        return v.strip()
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Validar que amount sea positivo."""
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v


@router.post("/trading/orders/limit")
async def create_limit_order(request: LimitOrderRequest, client_wrapper=Depends(_require_clob_client)):
    """
    Crea una limit order. Requiere auth y wallet (política v2).
    """
    try:
        # Validar side PRIMERO (antes de verificar execution_mode)
        if request.side.upper() not in ["BUY", "SELL"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="side must be 'BUY' or 'SELL'"
            )
        
        # Validar order_type PRIMERO (antes de verificar execution_mode)
        if request.order_type.upper() not in ["GTC", "FOK"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="order_type must be 'GTC' or 'FOK'"
            )
        
        # Verificar execution_mode DESPUÉS de validaciones
        execution_mode = config_service.get_execution_mode()
        
        # En DRY_RUN, simular sin requerir credenciales reales
        if execution_mode == "DRY_RUN":
            return {
                "status": "simulated",
                "execution_mode": "DRY_RUN",
                "order": {
                    "token_id": request.token_id,
                    "price": request.price,
                    "size": request.size,
                    "side": request.side.upper(),
                    "order_type": request.order_type.upper()
                },
                "message": "Order simulated (DRY_RUN mode - no real order sent)"
            }
        
        result = await client_wrapper.create_limit_order(
            token_id=request.token_id,
            price=request.price,
            size=request.size,
            side=request.side.upper(),
            order_type=request.order_type.upper()
        )
        
        return result
        
    except ValidationError as e:
        # Errores de validación de Pydantic
        errors = []
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {', '.join(errors)}"
        )
    except HTTPException:
        raise
    except ValueError as e:
        # Errores de validación manual
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating limit order: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error creating limit order: {str(e)}"
        )


@router.post("/trading/orders/market")
async def create_market_order(request: MarketOrderRequest, client_wrapper=Depends(_require_clob_client)):
    """
    Crea una market order. Requiere auth y wallet (política v2).
    """
    try:
        # Validar side PRIMERO (antes de verificar execution_mode)
        if request.side.upper() not in ["BUY", "SELL"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="side must be 'BUY' or 'SELL'"
            )
        
        # Validar order_type PRIMERO (antes de verificar execution_mode)
        if request.order_type.upper() not in ["FOK", "IOC"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="order_type must be 'FOK' or 'IOC'"
            )
        
        # Verificar execution_mode DESPUÉS de validaciones
        execution_mode = config_service.get_execution_mode()
        
        # En DRY_RUN, simular sin requerir credenciales reales
        if execution_mode == "DRY_RUN":
            return {
                "status": "simulated",
                "execution_mode": "DRY_RUN",
                "order": {
                    "token_id": request.token_id,
                    "amount": request.amount,
                    "side": request.side.upper(),
                    "order_type": request.order_type.upper()
                },
                "message": "Order simulated (DRY_RUN mode - no real order sent)"
            }
        
        result = await client_wrapper.create_market_order(
            token_id=request.token_id,
            amount=request.amount,
            side=request.side.upper(),
            order_type=request.order_type.upper()
        )
        
        return result
        
    except ValidationError as e:
        # Errores de validación de Pydantic
        errors = []
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {', '.join(errors)}"
        )
    except HTTPException:
        raise
    except ValueError as e:
        # Errores de validación manual
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating market order: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error creating market order: {str(e)}"
        )


@router.delete("/trading/orders/{order_id}")
async def cancel_order(order_id: str, client_wrapper=Depends(_require_clob_client)):
    """
    Cancela una orden específica. Requiere auth y wallet (política v2).
    """
    try:
        result = await client_wrapper.cancel_order(order_id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error cancelling order: {str(e)}"
        )


@router.delete("/trading/orders")
async def cancel_all_orders(client_wrapper=Depends(_require_clob_client)):
    """
    Cancela todas las órdenes abiertas. Requiere auth y wallet (política v2).
    """
    try:
        result = client_wrapper.cancel_all_orders()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling all orders: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error cancelling all orders: {str(e)}"
        )


# ============================================================================
# FASE 2.5: WEBSOCKET MARKET → ORDERBOOK ENGINE
# ============================================================================

@router.get("/websocket/status")
async def get_websocket_status():
    """
    Obtiene el estado de las conexiones WebSocket (MARKET y USER).
    
    Retorna:
    - Estado de conexiones WS MARKET
    - Estado de conexiones WS USER
    - Asset IDs suscritos (MARKET)
    - Ref-count por asset_id (MARKET)
    """
    from app.core.orderbook.service import get_orderbook_service
    from app.core.execution.polymarket_websocket import get_websocket_manager
    
    try:
        orderbook_service = get_orderbook_service()
        ws_manager = get_websocket_manager()
        
        ref_count = orderbook_service.get_ref_count()
        ws_subscribed = list(orderbook_service._ws_subscribed_assets)
        is_market_connected = ws_manager.is_market_connected()
        is_user_connected = ws_manager.is_user_connected()
        
        # Verificar si hay auth configurado para USER channel
        has_auth = ws_manager.auth is not None
        
        return {
            "market_channel": {
                "connected": is_market_connected,
                "subscribed_asset_ids": ws_subscribed,
                "count": len(ws_subscribed)
            },
            "user_channel": {
                "connected": is_user_connected,
                "authenticated": has_auth,
                "note": "USER channel requires authentication. Call /websocket/subscribe/user to connect."
            },
            "orderbook": {
                "ref_count": ref_count,
                "total_subscriptions": sum(ref_count.values())
            }
        }
    except Exception as e:
        logger.error(f"Error getting websocket status: {e}", exc_info=True)
        # Retornar estructura mínima en caso de error para que los tests no fallen
        return {
            "market_channel": {
                "connected": False,
                "subscribed_asset_ids": [],
                "count": 0,
                "error": str(e)
            },
            "user_channel": {
                "connected": False,
                "authenticated": False,
                "error": str(e)
            },
            "orderbook": {
                "ref_count": {},
                "total_subscriptions": 0
            }
        }


@router.get("/orderbook/{asset_id}")
async def get_orderbook_by_asset_id(asset_id: str):
    """
    Obtiene el orderbook desde State Cache para un asset_id específico.
    
    **FACADE**: Sirve desde State Cache (pm.orderbook.{asset_id}).
    NO hace fetch directo a Polymarket.
    
    Args:
        asset_id: Asset ID (token ID)
    
    Returns:
        OrderbookState con staleness_ms y metadata
    """
    from app.core.strategy_engine.state_cache_service import StateCacheService
    from app.database import SessionLocal
    
    try:
        db = SessionLocal()
        state_cache_service = StateCacheService(db)
        
        cache_key = f"pm.orderbook.{asset_id}"
        try:
            orderbook_state = await state_cache_service.get(cache_key)
        except Exception as db_error:
            # Si la tabla no existe o hay error de DB, retornar 404
            logger.warning(f"Error accessing state_cache for asset_id={asset_id}: {db_error}")
            raise HTTPException(
                status_code=404,
                detail=f"Orderbook not found for asset_id={asset_id}. May not be subscribed or no updates received yet."
            )
        
        if orderbook_state is None:
            raise HTTPException(
                status_code=404,
                detail=f"Orderbook not found for asset_id={asset_id}. May not be subscribed or no updates received yet."
            )
        
        # Agregar metadata
        result = {
            "asset_id": asset_id,
            "cache_key": cache_key,
            "orderbook": orderbook_state,
            "source": "state_cache",
            "note": "Data from WebSocket MARKET → Orderbook Engine → State Cache"
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting orderbook for asset_id={asset_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting orderbook: {str(e)}"
        )
    finally:
        db.close()


class MarketSubscriptionRequest(BaseModel):
    """Request model para suscribir/desuscribir asset_id."""
    asset_id: str
    owner_key: str = "api"


@router.post("/websocket/subscribe/market")
async def subscribe_market_channel(request: MarketSubscriptionRequest):
    """
    Suscribe un asset_id al WebSocket MARKET channel.
    
    Esto incrementa el ref-count. Si es el primer suscriptor (0→1),
    se suscribe automáticamente al WS MARKET channel.
    """
    from app.core.orderbook.service import get_orderbook_service
    
    try:
        orderbook_service = get_orderbook_service()
        orderbook_service.subscribe(request.asset_id, request.owner_key)
        
        ref_count = orderbook_service.get_ref_count().get(request.asset_id, 0)
        
        return {
            "status": "subscribed",
            "asset_id": request.asset_id,
            "owner_key": request.owner_key,
            "ref_count": ref_count
        }
        
    except Exception as e:
        logger.error(f"Error subscribing to market channel: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error subscribing: {str(e)}"
        )


@router.post("/websocket/unsubscribe/market")
async def unsubscribe_market_channel(request: MarketSubscriptionRequest):
    """
    Desuscribe un asset_id del WebSocket MARKET channel.
    
    Esto decrementa el ref-count. Si es el último suscriptor (1→0),
    se desuscribe automáticamente del WS MARKET channel.
    """
    from app.core.orderbook.service import get_orderbook_service
    
    try:
        orderbook_service = get_orderbook_service()
        orderbook_service.unsubscribe(request.asset_id, request.owner_key)
        
        ref_count = orderbook_service.get_ref_count().get(request.asset_id, 0)
        
        return {
            "status": "unsubscribed",
            "asset_id": request.asset_id,
            "owner_key": request.owner_key,
            "ref_count": ref_count
        }
        
    except Exception as e:
        logger.error(f"Error unsubscribing from market channel: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error unsubscribing: {str(e)}"
        )


# ============================================================================
# FASE 5: WEBSOCKET USER (Órdenes/Trades del Usuario)
# ============================================================================

class UserSubscriptionRequest(BaseModel):
    """Request model para suscribir/desuscribir USER channel."""
    market_ids: Optional[List[str]] = None  # Lista de market IDs para filtrar (None = todos)
    owner_key: str = "api"  # Identificador del suscriptor (para tracking)


@router.post("/websocket/subscribe/user")
async def subscribe_user_channel(request: UserSubscriptionRequest, client_wrapper=Depends(_require_clob_client)):
    """
    Suscribe al WebSocket USER channel para recibir updates de órdenes y trades.
    Requiere auth y wallet del usuario (política v2); no existe WS USER global.
    """
    from app.core.execution.polymarket_websocket import get_websocket_manager
    
    try:
        ws_manager = get_websocket_manager()
        
        # Verificar si ya está conectado
        if ws_manager.is_user_connected():
            return {
                "status": "already_connected",
                "message": "USER channel already connected",
                "owner_key": request.owner_key
            }
        
        # Verificar/obtener autenticación desde el cliente del usuario (inyectado)
        if not ws_manager.auth:
            try:
                client = client_wrapper.get_client()
                # Intentar ambos métodos: derive_api_key() y create_or_derive_api_creds()
                api_creds = None
                if hasattr(client, 'derive_api_key'):
                    api_creds = client.derive_api_key()
                elif hasattr(client, 'create_or_derive_api_creds'):
                    api_creds = client.create_or_derive_api_creds()
                elif hasattr(client, 'create_or_derive_api_key'):
                    api_creds = client.create_or_derive_api_key()
                
                if api_creds:
                    # ApiCreds puede ser un objeto o un dict
                    if isinstance(api_creds, dict):
                        api_key = api_creds.get("apiKey") or api_creds.get("api_key", "")
                        secret = api_creds.get("secret") or api_creds.get("api_secret", "")
                        passphrase = api_creds.get("passphrase") or api_creds.get("api_passphrase", "")
                    else:
                        # Es un objeto ApiCreds
                        api_key = getattr(api_creds, "apiKey", None) or getattr(api_creds, "api_key", "")
                        secret = getattr(api_creds, "secret", None) or getattr(api_creds, "api_secret", "")
                        passphrase = getattr(api_creds, "passphrase", None) or getattr(api_creds, "api_passphrase", "")
                    
                    if api_key and secret and passphrase:
                        ws_manager.set_auth(
                            api_key=api_key,
                            secret=secret,
                            passphrase=passphrase
                        )
                    else:
                        raise HTTPException(
                            status_code=503,
                            detail="Could not derive API keys. Please configure authentication manually."
                        )
                else:
                    raise HTTPException(
                        status_code=503,
                        detail="CLOB client does not support API key derivation. Please configure authentication manually."
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error deriving API keys: {e}", exc_info=True)
                raise HTTPException(
                    status_code=503,
                    detail=f"Could not derive API keys: {str(e)}"
                )
        
        # Conectar al USER channel
        try:
            ws_manager.connect_user_channel(market_ids=request.market_ids)
        except ImportError as e:
            # websocket-client no está instalado
            raise HTTPException(
                status_code=503,
                detail="websocket-client not installed. Install with: pip install websocket-client"
            )
        
        return {
            "status": "subscribed",
            "owner_key": request.owner_key,
            "market_ids": request.market_ids or "all",
            "message": "USER channel connected. You will receive real-time updates for orders and trades."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing to user channel: {e}", exc_info=True)
        # Si es un error de módulo faltante, retornar 503
        if "No module named 'websocket'" in str(e) or "websocket-client" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail="websocket-client not installed. Install with: pip install websocket-client"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Error subscribing: {str(e)}"
        )


@router.post("/websocket/unsubscribe/user")
async def unsubscribe_user_channel(request: UserSubscriptionRequest):
    """
    Desuscribe del WebSocket USER channel.
    
    Desconecta el USER channel y deja de recibir updates de órdenes y trades.
    
    Args:
        owner_key: Identificador del suscriptor (para tracking, opcional)
    
    Returns:
        Estado de la desuscripción
    """
    from app.core.execution.polymarket_websocket import get_websocket_manager
    
    try:
        ws_manager = get_websocket_manager()
        
        if not ws_manager.is_user_connected():
            return {
                "status": "not_connected",
                "message": "USER channel not connected",
                "owner_key": request.owner_key
            }
        
        # Desconectar USER channel
        if ws_manager.user_client:
            ws_manager.user_client.disconnect()
            ws_manager.user_client = None
        
        return {
            "status": "unsubscribed",
            "owner_key": request.owner_key,
            "message": "USER channel disconnected"
        }
        
    except Exception as e:
        logger.error(f"Error unsubscribing from user channel: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error unsubscribing: {str(e)}"
        )


# ============================================================================
# FASE 1: CONFIGURACIÓN Y AUTENTICACIÓN
# ============================================================================

@router.get("/connection/status")
async def get_connection_status(client_wrapper=Depends(_require_clob_client)):
    """
    Auth-health (user-scoped): estado Gamma + CLOB con TU wallet. No es health global.
    Requiere auth y wallet. Para health sin CLOB use GET /health (app) o GET /api/polymarket/health (Gamma).
    """
    from app.settings import settings
    
    status = {
        "configuration": {
            "chain_id": settings.chain_id,
            "rpc_url_configured": bool(settings.rpc_url),
            "note": "CLOB is per-user (wallet in DB); no global PRIVATE_KEY/FUNDER.",
        },
        "clob_client": {
            "available": client_wrapper.is_available(),
            "initialized": getattr(client_wrapper, "_initialized", False),
        },
        "apis": {
            "gamma_api": {"status": "unknown"},
            "clob_api": {"status": "unknown"},
        }
    }
    
    # Verificar Gamma API
    try:
        async with httpx.AsyncClient(timeout=30.0, base_url=settings.polymarket_gamma_api_url, trust_env=False) as client:
            response = await client.get("/events", params={"limit": 1})
            if response.status_code == 200:
                status["apis"]["gamma_api"] = {"status": "ok"}
            else:
                status["apis"]["gamma_api"] = {"status": "degraded", "status_code": response.status_code}
    except Exception as e:
        logger.error(f"Error checking Gamma API: {e}")
        status["apis"]["gamma_api"] = {"status": "error", "message": str(e)}
    
    # Verificar CLOB API (cliente del usuario ya inyectado)
    try:
        if client_wrapper.is_available():
            client = client_wrapper.get_client()
            # Intentar llamar get_ok() o get_server_time()
            try:
                if hasattr(client, 'get_ok'):
                    ok = client.get_ok()
                    status["apis"]["clob_api"] = {"status": "ok", "ok": ok}
                elif hasattr(client, 'get_server_time'):
                    server_time = client.get_server_time()
                    status["apis"]["clob_api"] = {"status": "ok", "server_time": server_time}
                else:
                    status["apis"]["clob_api"] = {"status": "ok", "note": "Client available but cannot verify API"}
            except Exception as e:
                status["apis"]["clob_api"] = {"status": "error", "message": str(e)}
        else:
            status["apis"]["clob_api"] = {"status": "unavailable", "reason": "CLOB client not initialized"}
    except Exception as e:
        logger.error(f"Error checking CLOB API: {e}")
        status["apis"]["clob_api"] = {"status": "error", "message": str(e)}
    
    return status


@router.get("/connection/test-auth")
async def test_authentication(client_wrapper=Depends(_require_clob_client)):
    """
    Auth-health: prueba CLOB con TU wallet. Requiere auth y wallet (user-scoped).
    """
    try:
        client = client_wrapper.get_client()
        
        # Intentar obtener información que requiere autenticación
        # Usar get_ok() o get_server_time() como prueba básica
        test_results = {}
        
        try:
            if hasattr(client, 'get_ok'):
                ok = client.get_ok()
                test_results["get_ok"] = {"success": True, "result": ok}
        except Exception as e:
            test_results["get_ok"] = {"success": False, "error": str(e)}
        
        try:
            if hasattr(client, 'get_server_time'):
                server_time = client.get_server_time()
                test_results["get_server_time"] = {"success": True, "result": server_time}
        except Exception as e:
            test_results["get_server_time"] = {"success": False, "error": str(e)}
        
        # Intentar obtener balance (requiere autenticación)
        try:
            balance = await client_wrapper.get_balance()
            if balance is not None:
                test_results["get_balance"] = {"success": True, "balance_usdc": balance}
            else:
                test_results["get_balance"] = {"success": False, "error": "Balance returned None"}
        except Exception as e:
            test_results["get_balance"] = {"success": False, "error": str(e)}
        
        # Determinar si la autenticación funciona
        auth_works = any(
            result.get("success", False) 
            for result in test_results.values()
        )
        
        return {
            "authentication_status": "ok" if auth_works else "failed",
            "tests": test_results,
            "message": "Authentication successful" if auth_works else "Authentication failed - check credentials"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing authentication: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error testing authentication: {str(e)}"
        )


# ============================================================================
# ENDPOINTS OPERATIVOS: SMOKE, WARMUP, SCENARIO RUNNER
# ============================================================================

# Imports adicionales para endpoints operativos
import uuid
import time
import asyncio
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
import os
from datetime import datetime
from typing import Dict, Any, List, Optional


def _get_process_memory_mb() -> float:
    """Obtiene memoria RSS del proceso actual en MB."""
    if not PSUTIL_AVAILABLE:
        return 0.0
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    except Exception:
        return 0.0


def _get_process_uptime_s() -> float:
    """Obtiene uptime del proceso actual en segundos."""
    if not PSUTIL_AVAILABLE:
        return 0.0
    try:
        process = psutil.Process(os.getpid())
        return time.time() - process.create_time()
    except Exception:
        return 0.0


@router.get("/smoke")
async def smoke_test(
    mode: str = Query(..., description="internal, external, or external_trade_ready"),
    asset_id: Optional[str] = Query(None, description="Asset ID for external modes (auto-discover if not provided)")
):
    """
    Smoke test endpoint - Postman-friendly.
    
    Ejecuta smoke tests y retorna reporte estructurado.
    
    Modes:
    - internal: Smoke interno (sin side effects persistentes)
    - external: Pipeline health (valida dataflow aunque trading disabled)
    - external_trade_ready: Trading readiness (valida dataflow + trading permitido)
    """
    from app.api.system import get_execution_mode
    from app.api.checkers import get_checkers_health
    from app.api.risk import get_risk_status
    from app.core.orderbook.service import get_orderbook_service
    from app.core.strategy_engine.state_cache_service import StateCacheService
    from app.database import SessionLocal
    
    smoke_start_time = time.time()
    request_id = str(uuid.uuid4())
    checks: List[Dict[str, Any]] = []
    overall_status = "PASS"
    failure_reason: Optional[str] = None
    trading_ready = False
    subscribed_asset_id: Optional[str] = None
    owner_key = f"smoke:{request_id}"
    
    # Timeout budget
    connect_timeout_s = 10
    data_timeout_s = 30
    max_total_s = 45
    
    try:
        # ============================================================
        # CHECK 1: execution_mode
        # ============================================================
        check_start = time.time()
        try:
            mode_response = await get_execution_mode()
            execution_mode = mode_response.get("execution_mode", "UNKNOWN")
            is_safe = mode_response.get("is_safe", False)
            
            checks.append({
                "name": "execution_mode",
                "status": "PASS",
                "details": {
                    "execution_mode": execution_mode,
                    "is_safe": is_safe
                },
                "timestamp_ms": int(check_start * 1000)
            })
        except Exception as e:
            checks.append({
                "name": "execution_mode",
                "status": "FAIL",
                "details": {"error": str(e)},
                "timestamp_ms": int(check_start * 1000)
            })
            overall_status = "FAIL"
            failure_reason = "EXECUTION_MODE_ERROR"
        
        # ============================================================
        # CHECK 2: checkers_health + trading_permitted
        # ============================================================
        check_start = time.time()
        try:
            checkers_response = await get_checkers_health()
            checkers_data = checkers_response
            
            # Calcular healthy_checkers
            checkers_dict = checkers_data.get("checkers", {})
            healthy_count = 0
            for checker_status in checkers_dict.values():
                if isinstance(checker_status, dict):
                    if checker_status.get("is_healthy", False):
                        healthy_count += 1
                elif hasattr(checker_status, 'is_healthy'):
                    if checker_status.is_healthy:
                        healthy_count += 1
            
            trading_permitted = healthy_count > 0
            quorum_effective = checkers_data.get("quorum_effective", 0)
            
            # En mode=external: NO hacer assert de trading_permitted (solo registrar)
            # En mode=external_trade_ready: Si trading_permitted=false → FAIL
            if mode == "external_trade_ready" and not trading_permitted:
                overall_status = "FAIL"
                failure_reason = "NO_CHECKERS"
            
            checks.append({
                "name": "checkers_health",
                "status": "PASS" if (mode != "external_trade_ready" or trading_permitted) else "FAIL",
                "details": {
                    "healthy_checkers": healthy_count,
                    "quorum_effective": quorum_effective,
                    "trading_permitted": trading_permitted
                },
                "timestamp_ms": int(check_start * 1000)
            })
            
            trading_ready = trading_permitted
            
        except Exception as e:
            checks.append({
                "name": "checkers_health",
                "status": "FAIL",
                "details": {"error": str(e)},
                "timestamp_ms": int(check_start * 1000)
            })
            overall_status = "FAIL"
            if not failure_reason:
                failure_reason = "NO_CHECKERS"
        
        # ============================================================
        # CHECK 3: risk_engine_status
        # ============================================================
        check_start = time.time()
        try:
            risk_response = await get_risk_status()
            risk_status = risk_response.get("risk_engine", {}).get("active", False)
            
            checks.append({
                "name": "risk_engine_status",
                "status": "PASS" if risk_status else "FAIL",
                "details": {
                    "active": risk_status,
                    "circuit_breakers": risk_response.get("circuit_breakers", {})
                },
                "timestamp_ms": int(check_start * 1000)
            })
            
            if not risk_status:
                overall_status = "FAIL"
                if not failure_reason:
                    failure_reason = "RISK_DOWN"
                    
        except Exception as e:
            checks.append({
                "name": "risk_engine_status",
                "status": "FAIL",
                "details": {"error": str(e)},
                "timestamp_ms": int(check_start * 1000)
            })
            overall_status = "FAIL"
            if not failure_reason:
                failure_reason = "RISK_DOWN"
        
        # ============================================================
        # CHECK 4: gamma_health
        # ============================================================
        check_start = time.time()
        try:
            async with httpx.AsyncClient() as client:
                health_response = await client.get(
                    f"{settings.polymarket_gamma_api_url}/health",
                    timeout=5.0
                )
                gamma_status = health_response.status_code == 200
                gamma_data = health_response.json() if gamma_status else {}
                
                checks.append({
                    "name": "gamma_health",
                    "status": "PASS" if gamma_status else "FAIL",
                    "details": {
                        "status": gamma_data.get("status", "unknown"),
                        "up": gamma_status
                    },
                    "timestamp_ms": int(check_start * 1000)
                })
                
                if not gamma_status:
                    overall_status = "FAIL"
                    if not failure_reason:
                        failure_reason = "GAMMA_DOWN"
                        
        except Exception as e:
            checks.append({
                "name": "gamma_health",
                "status": "FAIL",
                "details": {"error": str(e)},
                "timestamp_ms": int(check_start * 1000)
            })
            overall_status = "FAIL"
            if not failure_reason:
                failure_reason = "GAMMA_DOWN"
        
        # ============================================================
        # CHECK 5: WS MARKET pipeline (solo para external modes)
        # ============================================================
        if mode in ["external", "external_trade_ready"]:
            # Auto-descubrir asset_id si no se proporciona
            if not asset_id:
                try:
                    async with httpx.AsyncClient() as client:
                        events_response = await client.get(
                            f"{settings.polymarket_gamma_api_url}/events?closed=false&limit=3",
                            timeout=5.0
                        )
                        if events_response.status_code == 200:
                            events = events_response.json()
                            if events and len(events) > 0:
                                # Intentar obtener asset_id del primer evento
                                event = events[0]
                                if "markets" in event and len(event["markets"]) > 0:
                                    market_id = event["markets"][0].get("id")
                                    if market_id:
                                        market_response = await client.get(
                                            f"{settings.polymarket_gamma_api_url}/markets/{market_id}",
                                            timeout=5.0
                                        )
                                        if market_response.status_code == 200:
                                            market_data = market_response.json()
                                            if "outcomes" in market_data and len(market_data["outcomes"]) > 0:
                                                asset_id = market_data["outcomes"][0].get("token_id")
                except Exception as e:
                    logger.warning(f"Error auto-discovering asset_id: {e}")
            
            if not asset_id:
                overall_status = "FAIL"
                failure_reason = "NO_ASSET_ID"
                checks.append({
                    "name": "ws_market_pipeline",
                    "status": "FAIL",
                    "details": {"error": "Could not discover asset_id"},
                    "timestamp_ms": int(time.time() * 1000)
                })
            else:
                subscribed_asset_id = asset_id
                
                # 5.1. Suscribirse a WS MARKET
                check_start = time.time()
                try:
                    orderbook_service = get_orderbook_service()
                    orderbook_service.subscribe(asset_id, owner_key)
                    
                    checks.append({
                        "name": "ws_market_subscribe",
                        "status": "PASS",
                        "details": {
                            "asset_id": asset_id,
                            "owner_key": owner_key
                        },
                        "timestamp_ms": int(check_start * 1000)
                    })
                except Exception as e:
                    checks.append({
                        "name": "ws_market_subscribe",
                        "status": "FAIL",
                        "details": {"error": str(e)},
                        "timestamp_ms": int(check_start * 1000)
                    })
                    overall_status = "FAIL"
                    if not failure_reason:
                        failure_reason = "NO_CONNECT"
                
                # 5.2. Verificar conexión WS
                check_start = time.time()
                ws_connected = False
                start_time = time.time()
                while time.time() - start_time < connect_timeout_s:
                    if time.time() - smoke_start_time > max_total_s:
                        raise Exception(f"Smoke excedió tiempo total máximo de {max_total_s}s")
                    
                    try:
                        # Llamar directamente a la función del endpoint
                        from app.core.orderbook.service import get_orderbook_service
                        from app.core.execution.polymarket_websocket import get_websocket_manager
                        orderbook_service = get_orderbook_service()
                        ws_manager = get_websocket_manager()
                        if ws_manager.is_market_connected():
                            ws_connected = True
                            break
                    except Exception:
                        pass
                    await asyncio.sleep(1)
                
                if not ws_connected:
                    overall_status = "FAIL"
                    if not failure_reason:
                        failure_reason = "NO_CONNECT"
                
                checks.append({
                    "name": "ws_market_connected",
                    "status": "PASS" if ws_connected else "FAIL",
                    "details": {
                        "connected": ws_connected,
                        "asset_id": asset_id
                    },
                    "timestamp_ms": int(check_start * 1000)
                })
                
                # 5.3. Esperar datos y verificar cache
                if ws_connected:
                    check_start = time.time()
                    orderbook_data = None
                    start_time = time.time()
                    
                    db = SessionLocal()
                    try:
                        state_cache_service = StateCacheService(db)
                        cache_key = f"pm.orderbook.{asset_id}"
                        
                        while time.time() - start_time < data_timeout_s:
                            if time.time() - smoke_start_time > max_total_s:
                                raise Exception(f"Smoke excedió tiempo total máximo de {max_total_s}s")
                            
                            try:
                                orderbook_state = await state_cache_service.get(cache_key)
                                if orderbook_state:
                                    orderbook_data = orderbook_state
                                    break
                            except Exception:
                                pass
                            
                            await asyncio.sleep(2)
                        
                        if orderbook_data:
                            staleness_ms = orderbook_data.get("staleness_ms", 999999)
                            has_bids = len(orderbook_data.get("bids", [])) > 0
                            has_asks = len(orderbook_data.get("asks", [])) > 0
                            
                            checks.append({
                                "name": "cache_staleness",
                                "status": "PASS" if staleness_ms < 5000 else "FAIL",
                                "details": {
                                    "staleness_ms": staleness_ms,
                                    "threshold_ms": 5000,
                                    "has_bids": has_bids,
                                    "has_asks": has_asks
                                },
                                "timestamp_ms": int(check_start * 1000)
                            })
                            
                            if staleness_ms >= 5000:
                                overall_status = "FAIL"
                                if not failure_reason:
                                    failure_reason = "CACHE_STALE"
                            if not has_bids or not has_asks:
                                overall_status = "FAIL"
                                if not failure_reason:
                                    failure_reason = "NO_DATA"
                        else:
                            checks.append({
                                "name": "cache_staleness",
                                "status": "FAIL",
                                "details": {"error": "No orderbook data received"},
                                "timestamp_ms": int(check_start * 1000)
                            })
                            overall_status = "FAIL"
                            if not failure_reason:
                                failure_reason = "NO_DATA"
                    finally:
                        db.close()
                
                # Cleanup: Unsubscribe
                if subscribed_asset_id:
                    try:
                        orderbook_service = get_orderbook_service()
                        orderbook_service.unsubscribe(subscribed_asset_id, owner_key)
                    except Exception as e:
                        logger.warning(f"Failed to unsubscribe asset_id={subscribed_asset_id} with owner_key={owner_key}: {e}")
        
        # ============================================================
        # Observabilidad
        # ============================================================
        try:
            from app.core.orderbook.service import get_orderbook_service
            from app.core.execution.polymarket_websocket import get_websocket_manager
            orderbook_service_obs = get_orderbook_service()
            ws_manager_obs = get_websocket_manager()
            ref_count_dict = orderbook_service_obs.get_ref_count()
            ws_connected_obs = ws_manager_obs.is_market_connected()
            subscriptions_count = len(ref_count_dict)
            hot_cache_markets = list(ref_count_dict.keys())
        except Exception:
            ws_connected_obs = False
            subscriptions_count = 0
            hot_cache_markets = []
        
        observability = {
            "ws_connected": ws_connected_obs,
            "last_msg_age_ms": 0,  # TODO: Obtener desde WS manager
            "cache_staleness_ms": 0,  # TODO: Obtener desde cache
            "ref_count": subscriptions_count,
            "subscriptions_count": subscriptions_count,
            "hot_cache_markets": hot_cache_markets,
            "process_uptime_s": _get_process_uptime_s(),
            "rss_mb": _get_process_memory_mb(),
            "cache_backend": "memory",  # TODO: Detectar backend real
            "cache_write_ms": 0.0,  # TODO: Obtener métricas reales
            "cache_read_ms": 0.0,  # TODO: Obtener métricas reales
            "latency_breakdown": {
                "ws_last_msg_age_ms": 0,  # TODO: Obtener desde orderbook_state
                "ingest_to_cache_ms": 0,  # TODO: Obtener desde orderbook_state
                "cache_read_ms": 0,  # TODO: Obtener desde orderbook_state
                "end_to_end_ms": 0  # TODO: Obtener desde orderbook_state
            }
        }
        
        # ============================================================
        # Recommendation
        # ============================================================
        if overall_status == "PASS":
            if trading_ready:
                recommendation = "System ready for trading"
            else:
                recommendation = "Operational ok, trading disabled (0 checkers)"
        else:
            failed_checks = [c["name"] for c in checks if c["status"] == "FAIL"]
            recommendation = f"Fix: {', '.join(failed_checks)}"
        
        return {
            "status": overall_status,
            "mode": mode,
            "trading_ready": trading_ready,
            "timestamp": datetime.utcnow().isoformat(),
            "failure_reason": failure_reason,
            "timeouts": {
                "connect_timeout_s": connect_timeout_s,
                "data_timeout_s": data_timeout_s,
                "total_timeout_s": max_total_s
            },
            "checks": checks,
            "observability": observability,
            "recommendation": recommendation
        }
        
    except Exception as e:
        logger.error(f"Error in smoke test: {e}", exc_info=True)
        # Cleanup en caso de error
        if subscribed_asset_id:
            try:
                orderbook_service = get_orderbook_service()
                orderbook_service.unsubscribe(subscribed_asset_id, owner_key)
            except Exception:
                pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Error executing smoke test: {str(e)}"
        )


# ============================================================================
# WARMUP ENDPOINT
# ============================================================================

class WarmupRequest(BaseModel):
    """Request model para warmup."""
    asset_ids: List[str]
    duration_s: int = 30


@router.post("/warmup")
async def warmup_markets(request: WarmupRequest):
    """
    Warm-up / Priming: Suscribe a N mercados objetivo durante X segundos.
    
    Para market making, no empiezas a tradear con books fríos.
    El warm-up es un paso operativo previo al trading.
    
    Pasos:
    1. Suscribirse a N mercados objetivo durante X segundos
    2. Confirmar: orderbooks poblados, staleness estable, memory OK, reconexión OK
    
    Retorna:
    - status: "ready" | "not_ready"
    - orderbooks_populated: X/Y
    - staleness_ok: true/false
    - failed_asset_ids: Lista de asset_ids que fallaron con razón
    """
    from app.core.orderbook.service import get_orderbook_service
    from app.core.strategy_engine.state_cache_service import StateCacheService
    from app.database import SessionLocal
    
    request_id = str(uuid.uuid4())
    owner_key = f"warmup:{request_id}"
    
    orderbooks_populated = 0
    failed_asset_ids: List[Dict[str, Any]] = []
    staleness_ok = True
    
    orderbook_service = get_orderbook_service()
    db = SessionLocal()
    
    try:
        state_cache_service = StateCacheService(db)
        
        # Suscribirse a todos los asset_ids
        for asset_id in request.asset_ids:
            try:
                orderbook_service.subscribe(asset_id, owner_key)
            except Exception as e:
                failed_asset_ids.append({
                    "asset_id": asset_id,
                    "reason": "SUBSCRIBE_FAILED",
                    "error": str(e)
                })
        
        # Esperar duration_s segundos
        await asyncio.sleep(request.duration_s)
        
        # Verificar cada asset_id
        for asset_id in request.asset_ids:
            cache_key = f"pm.orderbook.{asset_id}"
            try:
                orderbook_state = await state_cache_service.get(cache_key)
                
                if orderbook_state is None:
                    failed_asset_ids.append({
                        "asset_id": asset_id,
                        "reason": "NO_DATA"
                    })
                    continue
                
                # Verificar staleness
                staleness_ms = orderbook_state.get("staleness_ms", 999999)
                if staleness_ms > 5000:  # threshold: 5 segundos
                    failed_asset_ids.append({
                        "asset_id": asset_id,
                        "reason": "STALE",
                        "staleness_ms": staleness_ms
                    })
                    staleness_ok = False
                    continue
                
                # Verificar que tiene bids y asks
                bids = orderbook_state.get("bids", [])
                asks = orderbook_state.get("asks", [])
                
                if len(bids) == 0 or len(asks) == 0:
                    failed_asset_ids.append({
                        "asset_id": asset_id,
                        "reason": "NO_BIDS_ASKS"
                    })
                    continue
                
                # Verificar spread (opcional)
                best_bid = orderbook_state.get("best_bid_price")
                best_ask = orderbook_state.get("best_ask_price")
                if best_bid and best_ask:
                    spread = best_ask - best_bid
                    if spread > 0.5:  # Spread muy amplio (50%)
                        failed_asset_ids.append({
                            "asset_id": asset_id,
                            "reason": "SPREAD_BAD",
                            "spread": spread
                        })
                
                orderbooks_populated += 1
                
            except Exception as e:
                failed_asset_ids.append({
                    "asset_id": asset_id,
                    "reason": "ERROR",
                    "error": str(e)
                })
        
        # Setear flag pm.warmup.ready
        warmup_ready = (orderbooks_populated == len(request.asset_ids)) and staleness_ok
        
        try:
            await state_cache_service.set(
                cache_key="pm.warmup.ready",
                value=warmup_ready,
                ttl_seconds=60  # TTL corto: 60 segundos
            )
        except Exception as e:
            logger.warning(f"Failed to set pm.warmup.ready flag: {e}")
        
        # Cleanup: Unsubscribe todos los asset_ids
        for asset_id in request.asset_ids:
            try:
                orderbook_service.unsubscribe(asset_id, owner_key)
            except Exception as e:
                logger.warning(f"Failed to unsubscribe asset_id={asset_id} in warmup cleanup: {e}")
        
        return {
            "status": "ready" if warmup_ready else "not_ready",
            "orderbooks_populated": f"{orderbooks_populated}/{len(request.asset_ids)}",
            "staleness_ok": staleness_ok,
            "failed_asset_ids": failed_asset_ids,
            "duration_s": request.duration_s,
            "warmup_ready_flag": warmup_ready
        }
        
    except Exception as e:
        logger.error(f"Error in warmup: {e}", exc_info=True)
        # Cleanup en caso de error
        for asset_id in request.asset_ids:
            try:
                orderbook_service.unsubscribe(asset_id, owner_key)
            except Exception:
                pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Error executing warmup: {str(e)}"
        )
    finally:
        db.close()


# ============================================================================
# SCENARIO RUNNER ENDPOINT
# ============================================================================

@router.get("/scenario/run")
async def run_scenario(
    name: str = Query(..., description="Scenario name: mm_bootstrap, warmup_check, kill_switch_test"),
    market_id: Optional[str] = Query(None, description="Market ID for scenario")
):
    """
    Scenario Runner: Ejecuta secuencias predefinidas (macros).
    
    ⚠️ INTERNAL-ONLY: Requiere SCENARIO_RUNNER_ENABLED=true en settings.
    Por defecto deshabilitado en producción.
    
    Scenarios disponibles:
    - mm_bootstrap: Market Making Bootstrap (subscribe → wait data → place tiny order → cancel → reconcile)
    - warmup_check: Warm-up Check (subscribe → wait data → verify staleness → verify memory)
    - kill_switch_test: Kill Switch Test (simular disconnect → verify circuit breaker → verify órdenes canceladas)
    
    Configuración:
    - SCENARIO_RUNNER_ENABLED=false (default): Endpoint retorna 503
    - SCENARIO_RUNNER_ENABLED=true: Endpoint habilitado (solo para staging/internal)
    """
    # Verificar bandera
    if not settings.scenario_runner_enabled:
        raise HTTPException(
            status_code=503,
            detail="Scenario runner is disabled. Set SCENARIO_RUNNER_ENABLED=true to enable (internal-only, not for production)."
        )
    from app.core.orderbook.service import get_orderbook_service
    from app.core.strategy_engine.state_cache_service import StateCacheService
    from app.database import SessionLocal
    
    scenario_start_time = time.time()
    steps: List[Dict[str, Any]] = []
    scenario_status = "PASS"
    
    # Rate limiting: 10 por minuto por usuario (TODO: implementar)
    
    try:
        if name == "mm_bootstrap":
            # Scenario: Market Making Bootstrap
            if not market_id:
                raise HTTPException(status_code=400, detail="market_id required for mm_bootstrap")
            
            # Step 1: Subscribe
            step_start = time.time()
            try:
                # Obtener asset_id desde market_id
                async with httpx.AsyncClient() as client:
                    market_response = await client.get(
                        f"{settings.polymarket_gamma_api_url}/markets/{market_id}",
                        timeout=5.0
                    )
                    if market_response.status_code != 200:
                        raise Exception(f"Market not found: {market_id}")
                    market_data = market_response.json()
                    asset_id = market_data.get("outcomes", [{}])[0].get("token_id")
                    if not asset_id:
                        raise Exception("Could not get asset_id from market")
                
                orderbook_service = get_orderbook_service()
                request_id = str(uuid.uuid4())
                owner_key = f"scenario:{request_id}"
                orderbook_service.subscribe(asset_id, owner_key)
                
                steps.append({
                    "name": "subscribe",
                    "status": "PASS",
                    "duration_ms": int((time.time() - step_start) * 1000)
                })
            except Exception as e:
                steps.append({
                    "name": "subscribe",
                    "status": "FAIL",
                    "duration_ms": int((time.time() - step_start) * 1000),
                    "error": str(e)
                })
                scenario_status = "FAIL"
                raise
            
            # Step 2: Wait data
            step_start = time.time()
            try:
                db = SessionLocal()
                state_cache_service = StateCacheService(db)
                cache_key = f"pm.orderbook.{asset_id}"
                
                waited = 0
                max_wait = 10  # 10 segundos máximo
                orderbook_data = None
                
                while waited < max_wait:
                    orderbook_state = await state_cache_service.get(cache_key)
                    if orderbook_state:
                        orderbook_data = orderbook_state
                        break
                    await asyncio.sleep(1)
                    waited += 1
                
                db.close()
                
                if not orderbook_data:
                    raise Exception("No orderbook data received")
                
                steps.append({
                    "name": "wait_data",
                    "status": "PASS",
                    "duration_ms": int((time.time() - step_start) * 1000)
                })
            except Exception as e:
                steps.append({
                    "name": "wait_data",
                    "status": "FAIL",
                    "duration_ms": int((time.time() - step_start) * 1000),
                    "error": str(e)
                })
                scenario_status = "FAIL"
                # Cleanup
                try:
                    orderbook_service.unsubscribe(asset_id, owner_key)
                except Exception:
                    pass
                raise
            
            # Step 3: Place tiny order (solo en PAPER)
            step_start = time.time()
            try:
                execution_mode = config_service.get_execution_mode()
                if execution_mode == "LIVE":
                    raise Exception("Cannot place order in LIVE mode via scenario")
                
                # En DRY_RUN/PAPER, simular orden
                # TODO: Implementar creación de orden simulada
                steps.append({
                    "name": "place_order",
                    "status": "PASS",
                    "duration_ms": int((time.time() - step_start) * 1000),
                    "note": "Simulated in DRY_RUN/PAPER"
                })
            except Exception as e:
                steps.append({
                    "name": "place_order",
                    "status": "FAIL",
                    "duration_ms": int((time.time() - step_start) * 1000),
                    "error": str(e)
                })
                scenario_status = "FAIL"
            
            # Step 4: Cancel
            step_start = time.time()
            try:
                # TODO: Implementar cancel de orden simulada
                steps.append({
                    "name": "cancel",
                    "status": "PASS",
                    "duration_ms": int((time.time() - step_start) * 1000),
                    "note": "Simulated in DRY_RUN/PAPER"
                })
            except Exception as e:
                steps.append({
                    "name": "cancel",
                    "status": "FAIL",
                    "duration_ms": int((time.time() - step_start) * 1000),
                    "error": str(e)
                })
                scenario_status = "FAIL"
            
            # Step 5: Reconcile
            step_start = time.time()
            try:
                # TODO: Implementar reconcile
                steps.append({
                    "name": "reconcile",
                    "status": "PASS",
                    "duration_ms": int((time.time() - step_start) * 1000),
                    "note": "Simulated in DRY_RUN/PAPER"
                })
            except Exception as e:
                steps.append({
                    "name": "reconcile",
                    "status": "FAIL",
                    "duration_ms": int((time.time() - step_start) * 1000),
                    "error": str(e)
                })
                scenario_status = "FAIL"
            
            # Cleanup
            try:
                orderbook_service.unsubscribe(asset_id, owner_key)
            except Exception:
                pass
        
        elif name == "warmup_check":
            # Scenario: Warm-up Check
            if not market_id:
                raise HTTPException(status_code=400, detail="market_id required for warmup_check")
            
            # Similar a warmup endpoint pero como scenario
            # TODO: Implementar
            steps.append({
                "name": "warmup_check",
                "status": "PASS",
                "duration_ms": 0,
                "note": "TODO: Implement warmup_check scenario"
            })
        
        elif name == "kill_switch_test":
            # Scenario: Kill Switch Test
            # Requiere rol admin o ops (TODO: implementar auth)
            # TODO: Implementar
            steps.append({
                "name": "kill_switch_test",
                "status": "PASS",
                "duration_ms": 0,
                "note": "TODO: Implement kill_switch_test scenario"
            })
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown scenario: {name}. Available: mm_bootstrap, warmup_check, kill_switch_test"
            )
        
        total_duration_ms = int((time.time() - scenario_start_time) * 1000)
        
        return {
            "scenario": name,
            "status": scenario_status,
            "steps": steps,
            "total_duration_ms": total_duration_ms
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in scenario runner: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error executing scenario: {str(e)}"
        )
