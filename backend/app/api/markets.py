"""
Markets API endpoints.

Markets: plantillas/grupos lógicos (ej. "BTC Up or Down – 15 min").
No son tradeables directamente. Solo se pueden activar/desactivar para escanear events.

IMPORTANTE: Series y Markets se leen directamente de la API de Polymarket.
Solo se guarda el estado `enabled` en nuestra DB.
"""
from typing import Optional
from collections import deque
from threading import Lock
import time
from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
from fastapi.responses import JSONResponse
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
import json

logger = logging.getLogger(__name__)

# Rate limit orderbook-metrics: 60 req/min por IP (ventana 60s)
_orderbook_metrics_rate: dict = {}
_orderbook_metrics_rate_lock = Lock()
ORDERBOOK_METRICS_RATE_LIMIT = 60
ORDERBOOK_METRICS_RATE_WINDOW_SEC = 60


def _orderbook_metrics_consume_rate(ip: str) -> bool:
    """Devuelve True si se permite la petición, False si hay que devolver 429."""
    now = time.time()
    with _orderbook_metrics_rate_lock:
        if ip not in _orderbook_metrics_rate:
            _orderbook_metrics_rate[ip] = deque()
        q = _orderbook_metrics_rate[ip]
        while q and q[0] < now - ORDERBOOK_METRICS_RATE_WINDOW_SEC:
            q.popleft()
        if len(q) >= ORDERBOOK_METRICS_RATE_LIMIT:
            return False
        q.append(now)
        return True


# Cache órdenes Gamma no soportados (ej. updatedAt 4xx) → no reintentar en 1h
_gamma_unsupported_orders: dict = {}  # order -> expiry_ts
_gamma_orders_lock = Lock()
GAMMA_ORDER_CACHE_TTL_SEC = 3600

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


def _gamma_params_to_dict(limit: int, offset: int, closed: str, order: str, ascending: bool, tag_id: Optional[str]) -> dict:
    """Params que se envían a Gamma (para canonical key)."""
    return {
        "limit": limit,
        "offset": offset,
        "closed": closed,
        "order": order,
        "ascending": ascending,
        "tag_id": tag_id,
    }


def _build_gamma_cache_key(limit: int, offset: int, closed: str, order: str, ascending: bool, tag_id: Optional[str]) -> str:
    """Cache key para Gamma markets (canonical + hash, Fase 4)."""
    from app.core.cache_keys import build_markets_cache_key
    return build_markets_cache_key(_gamma_params_to_dict(limit, offset, closed, order, ascending, tag_id))


TWO_PHASE_CHUNK_LIMIT = 100
TWO_PHASE_MAX_ITERATIONS = 5
TWO_PHASE_MAX_SCANNED = 500

# Fase 3: Timeouts Gamma (connect 1s, read 4s, overall 5s)
GAMMA_CONNECT_TIMEOUT = 1.0
GAMMA_READ_TIMEOUT = 4.0
GAMMA_OVERALL_TIMEOUT = 5.0

# Circuit breaker Gamma markets: in-memory o Redis-backed (Fase 7)
def _gamma_markets_circuit_breaker():
    """Circuit breaker para Gamma markets (Redis-backed si CACHE_PROVIDER=redis)."""
    from app.core.gamma_circuit_breaker import get_gamma_markets_circuit_breaker
    return get_gamma_markets_circuit_breaker()


@router.get("")
async def get_markets(
    limit: int = Query(50, ge=1, le=100, description="Max items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    order: str = Query("createdAt", description="Order field (createdAt, updatedAt, etc.)"),
    ascending: bool = Query(False, description="Ascending order"),
    closed: str = Query("false", description="Include closed markets"),
    tag_id: Optional[str] = Query(None, description="Filter by tag_id (Gamma)"),
    category: Optional[str] = Query(None, description="Filter by category (client-side)"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status (client-side)"),
    series_id: Optional[str] = Query(None, description="Filter by series_id (client-side)"),
    search: Optional[str] = Query(None, description="Search by name (client-side)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of markets (plantillas) - proxy Gamma API.
    
    Params limit, offset, order, ascending, closed, tag_id se reenvían a Gamma.
    Metadata en headers: X-Limit, X-Offset, X-Has-More, etc.
    Cada market incluye enabled (merge DB) y clob_token_ids (selection_hint, primary).
    """
    import httpx
    from app.settings import settings
    from app.core.rate_limiter import rate_limiter, EndpointType
    from app.core.cache_provider import gamma_cache_provider
    from app.core.cache_singleflight import try_acquire_refresh_lock, release_refresh_lock
    from app.core.gamma_utils import parse_clob_token_ids
    from datetime import timedelta
    import asyncio
    from app.models.market_enabled_state import MarketEnabledState

    cache_ttl = timedelta(seconds=60)
    enabled_states: dict = {}
    for mes in db.query(MarketEnabledState).all():
        enabled_states[mes.polymarket_market_id] = mes.enabled

    # Cache órdenes no soportados por Gamma (4xx): no reintentar en 1h
    now_ts = time.time()
    with _gamma_orders_lock:
        for k in list(_gamma_unsupported_orders):
            if _gamma_unsupported_orders[k] <= now_ts:
                del _gamma_unsupported_orders[k]
        effective_order = "createdAt" if order in _gamma_unsupported_orders else order

    def _to_result_item(market_data: dict, is_enabled: bool) -> dict:
        polymarket_id = market_data.get("id") or market_data.get("slug") or str(market_data.get("_id", ""))
        tags_data = market_data.get("tags", [])
        tags = [{"tag_id": str(t.get("id") or t.get("slug", "")), "name": t.get("name", "")} for t in tags_data]
        series_info = market_data.get("series") or {}
        series_polymarket_id = series_info.get("id") or series_info.get("slug")
        clob_raw = market_data.get("clobTokenIds")
        parsed = parse_clob_token_ids(clob_raw)
        clob_token_ids = {
            "primary_yes": parsed["primary_yes"],
            "primary_no": parsed["primary_no"],
            "clob_token_ids_all": parsed["clob_token_ids_all"],
            "clob_token_ids_by_key": parsed["clob_token_ids_by_key"],
            "selection_hint": parsed["selection_hint"],
            "primary": parsed["primary"],
        }
        return {
            "market_id": polymarket_id,
            "polymarket_id": polymarket_id,
            "name": market_data.get("question") or market_data.get("name", ""),
            "category": market_data.get("category"),
            "enabled": is_enabled,
            "series_id": series_polymarket_id,
            "series_name": series_info.get("name"),
            "tags": tags,
            "clob_token_ids": clob_token_ids,
            "events_count": 0,
            "created_at": None,
            "updated_at": None,
        }

    def _passes_filters(market_data: dict, is_enabled: bool) -> bool:
        polymarket_id = market_data.get("id") or market_data.get("slug") or str(market_data.get("_id", ""))
        if not polymarket_id:
            return False
        if category and market_data.get("category") != category:
            return False
        if search and search.lower() not in (market_data.get("question") or market_data.get("name") or "").lower():
            return False
        if enabled is not None and is_enabled != enabled:
            return False
        tags_data = market_data.get("tags", [])
        if tag_id:
            tag_ids_in_market = [str(t.get("id") or t.get("slug", "")) for t in tags_data]
            if tag_id not in tag_ids_in_market:
                return False
        series_info = market_data.get("series") or {}
        series_polymarket_id = series_info.get("id") or series_info.get("slug")
        if series_id and series_polymarket_id != series_id:
            return False
        return True

    def _default_headers(gfc: int, gs: int, has_more: bool) -> dict:
        h = {
            "X-Limit": str(limit),
            "X-Offset": str(offset),
            "X-Has-More": "true" if has_more else "false",
            "X-Order-Effective": effective_order,
            "X-Gamma-Fetch-Count": str(gfc),
            "X-Gamma-Scanned": str(gs),
        }
        if enabled is not None:
            h["X-Enabled-Filter-Applied"] = "true"
            h["X-Offset-Mode"] = "filtered"
        else:
            h["X-Enabled-Filter-Applied"] = "false"
            h["X-Offset-Mode"] = "gamma"
        return h

    def _service_unavailable_503(reason: str, headers_base: dict) -> JSONResponse:
        """Fase 3: 503 cuando Gamma falla o circuit breaker abierto."""
        return JSONResponse(
            status_code=503,
            content={"detail": f"Gamma markets temporarily unavailable: {reason}"},
            headers=headers_base,
        )

    async def _fetch_gamma_chunk(gamma_offset: int, chunk_limit: int, ttl_override: Optional[float] = None) -> list:
        ck = _build_gamma_cache_key(chunk_limit, gamma_offset, closed, effective_order, ascending, tag_id)
        cached = await gamma_cache_provider.get(ck)
        if cached is not None:
            return cached
        circuit = _gamma_markets_circuit_breaker()
        if not await circuit.can_attempt():
            logger.warning("Gamma markets circuit breaker OPEN, skipping fetch")
            raise ValueError("circuit_breaker_open")
        gp = {
            "closed": closed,
            "limit": chunk_limit,
            "offset": gamma_offset,
            "order": effective_order,
            "ascending": str(ascending).lower(),
        }
        if tag_id:
            gp["tag_id"] = tag_id
        gamma_timeout = httpx.Timeout(
            connect=GAMMA_CONNECT_TIMEOUT,
            read=GAMMA_READ_TIMEOUT,
            timeout=GAMMA_OVERALL_TIMEOUT,
        )
        try:
            async with httpx.AsyncClient(timeout=gamma_timeout) as client:
                url = f"{settings.polymarket_gamma_api_url}/markets"
                response = await client.get(url, params=gp)
                if response.status_code == 429:
                    await rate_limiter.record_violation(EndpointType.GAMMA_MARKETS)
                    await circuit.record_failure()
                    logger.warning("Gamma 429 rate limit exceeded for markets")
                    raise ValueError("gamma_429")
                if 400 <= response.status_code < 500:
                    with _gamma_orders_lock:
                        _gamma_unsupported_orders[effective_order] = time.time() + GAMMA_ORDER_CACHE_TTL_SEC
                    logger.warning("Gamma 4xx for markets order=%s status=%s", effective_order, response.status_code)
                    raise ValueError("gamma_4xx_order")
                if response.status_code >= 500:
                    await circuit.record_failure()
                    logger.warning("Gamma 5xx for markets: status=%s", response.status_code)
                    raise ValueError("gamma_5xx")
                response.raise_for_status()
                data = response.json()
                chunk = data if isinstance(data, list) else data.get("data", [])
                await circuit.record_success()
        except httpx.TimeoutException as e:
            await circuit.record_failure()
            logger.warning("Gamma timeout for markets: %s", e)
            raise ValueError("gamma_timeout") from e
        except httpx.HTTPStatusError as e:
            if 400 <= e.response.status_code < 500:
                with _gamma_orders_lock:
                    _gamma_unsupported_orders[effective_order] = time.time() + GAMMA_ORDER_CACHE_TTL_SEC
                logger.warning("Gamma 4xx for markets order=%s: %s", effective_order, e)
            elif e.response.status_code >= 500:
                await circuit.record_failure()
                logger.warning("Gamma HTTP error for markets: %s", e)
            raise ValueError("gamma_http_error") from e
        await gamma_cache_provider.set(ck, chunk, ttl_seconds=ttl_override if ttl_override is not None else 60.0)
        return chunk

    gamma_fetch_count = 0
    gamma_scanned = 0
    result: list = []
    partial_page = False
    partial_reason: Optional[str] = None
    cache_header: Optional[str] = None
    _obs: dict = {}  # Fase 8: observabilidad (bucket, redis_latency_ms, gamma_latency_ms, etc.)

    circuit = _gamma_markets_circuit_breaker()
    if not await circuit.can_attempt():
        logger.warning("Gamma markets circuit breaker OPEN, returning 503")
        return _service_unavailable_503("circuit breaker open", _default_headers(0, 0, False))

    if enabled is not None:
        gamma_offset = offset
        accumulated: list = []
        iterations = 0
        chunk: list = []
        try:
            if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_MARKETS, timeout=5.0):
                logger.warning("Rate limit timeout for markets (two-phase)")
                return JSONResponse(content=[], headers=_default_headers(0, 0, False))
            while len(accumulated) < limit and iterations < TWO_PHASE_MAX_ITERATIONS and gamma_scanned < TWO_PHASE_MAX_SCANNED:
                chunk = await _fetch_gamma_chunk(gamma_offset, TWO_PHASE_CHUNK_LIMIT)
                gamma_fetch_count += 1
                gamma_scanned += len(chunk)
                iterations += 1
                for m in chunk:
                    pid = m.get("id") or m.get("slug") or str(m.get("_id", ""))
                    if not pid:
                        continue
                    is_en = enabled_states.get(pid, False)
                    if not _passes_filters(m, is_en):
                        continue
                    accumulated.append(_to_result_item(m, is_en))
                    if len(accumulated) >= limit:
                        break
                if len(chunk) < TWO_PHASE_CHUNK_LIMIT:
                    break
                gamma_offset += TWO_PHASE_CHUNK_LIMIT
            result = accumulated[:limit]
            if len(result) < limit and (gamma_scanned >= TWO_PHASE_MAX_SCANNED or iterations >= TWO_PHASE_MAX_ITERATIONS):
                partial_page = True
                partial_reason = "max_scanned" if gamma_scanned >= TWO_PHASE_MAX_SCANNED else "max_iterations"
            has_more = len(chunk) >= TWO_PHASE_CHUNK_LIMIT
        except ValueError as e:
            err_msg = str(e)
            if err_msg in ("gamma_429", "gamma_5xx", "circuit_breaker_open", "gamma_timeout", "gamma_http_error"):
                return _service_unavailable_503(err_msg.replace("_", " "), _default_headers(gamma_fetch_count, gamma_scanned, False))
            raise
        except Exception as e:
            logger.error("Error in two-phase fetch: %s", e, exc_info=True)
            return JSONResponse(content=[], headers=_default_headers(gamma_fetch_count, gamma_scanned, False))
    else:
        from app.core.cache_keys import (
            build_markets_cache_key,
            get_markets_bucket,
            get_markets_soft_ttl_seconds,
            should_cache_markets_v1,
        )
        params = {
            "limit": limit,
            "offset": offset,
            "closed": closed,
            "order": effective_order,
            "ascending": ascending,
            "tag_id": tag_id,
            "search": search,
        }
        if not should_cache_markets_v1(params):
            _obs["bucket"] = "no_cache"
            _obs["cache_status"] = "miss"
            cache_header = "miss"
            try:
                if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_MARKETS, timeout=5.0):
                    logger.warning("Rate limit timeout for markets")
                    return JSONResponse(content=[], headers=_default_headers(0, 0, False))
                _t0 = time.perf_counter()
                markets_data = await _fetch_gamma_chunk(offset, limit)
                _obs["gamma_latency_ms"] = round((time.perf_counter() - _t0) * 1000, 2)
                gamma_fetch_count = 1
                gamma_scanned = len(markets_data)
            except ValueError as e:
                err_msg = str(e)
                if err_msg in ("gamma_429", "gamma_5xx", "circuit_breaker_open", "gamma_timeout", "gamma_http_error"):
                    return _service_unavailable_503(err_msg.replace("_", " "), _default_headers(0, 0, False))
                raise
            except Exception as e:
                logger.error("Error fetching markets from Polymarket: %s", e, exc_info=True)
                return JSONResponse(content=[], headers=_default_headers(0, 0, False))
            has_more = len(markets_data) >= limit
        else:
            cache_key = build_markets_cache_key(params)
            bucket = get_markets_bucket(params)
            ttl_sec = get_markets_soft_ttl_seconds(bucket)
            _obs["bucket"] = bucket
            _obs["cache_key"] = cache_key
            _obs.setdefault("cache_refresh", 0)
            _t0_redis = time.perf_counter()
            hit = await gamma_cache_provider.get_with_meta(cache_key)
            _obs["redis_latency_ms"] = round((time.perf_counter() - _t0_redis) * 1000, 2)

            if hit is not None and hit.status == "fresh":
                markets_data = hit.payload
                gamma_scanned = len(markets_data)
                cache_header = "hit"
                _obs["cache_status"] = "hit"
                _obs["serving_fetched_at_ms"] = hit.fetched_at_ms
            elif hit is not None and hit.status == "stale":
                markets_data = hit.payload
                gamma_scanned = len(markets_data)
                cache_header = "stale"
                _obs["cache_status"] = "stale"
                _obs["serving_fetched_at_ms"] = hit.fetched_at_ms
                acquired = await try_acquire_refresh_lock(cache_key)
                if acquired:
                    try:
                        if await rate_limiter.wait_for_capacity(EndpointType.GAMMA_MARKETS, timeout=5.0):
                            _t0_gamma = time.perf_counter()
                            new_data = await _fetch_gamma_chunk(offset, limit, ttl_override=float(ttl_sec))
                            _obs["gamma_latency_ms"] = round((time.perf_counter() - _t0_gamma) * 1000, 2)
                            _obs["cache_refresh"] = 1
                            _obs["serving_fetched_at_ms"] = int(time.time() * 1000)
                            await gamma_cache_provider.set(cache_key, new_data, ttl_seconds=float(ttl_sec))
                            markets_data = new_data
                            gamma_scanned = len(markets_data)
                            gamma_fetch_count = 1
                            cache_header = "hit"
                    except ValueError as e:
                        err_msg = str(e)
                        if err_msg in ("gamma_429", "gamma_5xx", "circuit_breaker_open", "gamma_timeout", "gamma_http_error"):
                            return _service_unavailable_503(err_msg.replace("_", " "), _default_headers(0, 0, False))
                        raise
                    except Exception as e:
                        logger.error("Error refreshing markets cache: %s", e, exc_info=True)
                    finally:
                        await release_refresh_lock(cache_key)
            else:
                _obs["cache_status"] = "miss"
                if not await circuit.can_attempt():
                    logger.warning("Gamma markets circuit breaker OPEN on cache miss, returning 503")
                    return _service_unavailable_503("circuit breaker open", _default_headers(0, 0, False))
                acquired = await try_acquire_refresh_lock(cache_key)
                if acquired:
                    try:
                        if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_MARKETS, timeout=5.0):
                            logger.warning("Rate limit timeout for markets")
                            return JSONResponse(content=[], headers=_default_headers(0, 0, False))
                        _t0_gamma = time.perf_counter()
                        markets_data = await _fetch_gamma_chunk(offset, limit, ttl_override=float(ttl_sec))
                        _obs["gamma_latency_ms"] = round((time.perf_counter() - _t0_gamma) * 1000, 2)
                        _obs["cache_refresh"] = 1
                        _obs["serving_fetched_at_ms"] = int(time.time() * 1000)
                        cache_header = "miss"
                        gamma_fetch_count = 1
                        gamma_scanned = len(markets_data)
                    except ValueError as e:
                        err_msg = str(e)
                        if err_msg in ("gamma_429", "gamma_5xx", "circuit_breaker_open", "gamma_timeout", "gamma_http_error"):
                            return _service_unavailable_503(err_msg.replace("_", " "), _default_headers(0, 0, False))
                        raise
                    except Exception as e:
                        logger.error("Error fetching markets from Polymarket: %s", e, exc_info=True)
                        return JSONResponse(content=[], headers=_default_headers(0, 0, False))
                    finally:
                        await release_refresh_lock(cache_key)
                else:
                    await asyncio.sleep(0.3)
                    _t0_redis2 = time.perf_counter()
                    hit2 = await gamma_cache_provider.get_with_meta(cache_key)
                    _obs["redis_latency_ms"] = round((time.perf_counter() - _t0_redis2) * 1000, 2)
                    if hit2 is not None:
                        markets_data = hit2.payload
                        gamma_scanned = len(markets_data)
                        cache_header = "stale" if hit2.status == "stale" else "hit"
                        _obs["cache_status"] = "stale" if hit2.status == "stale" else "hit"
                        _obs["serving_fetched_at_ms"] = hit2.fetched_at_ms
                    else:
                        if not await circuit.can_attempt():
                            logger.warning("Gamma markets circuit breaker OPEN on cache miss (after wait), returning 503")
                            return _service_unavailable_503("circuit breaker open", _default_headers(0, 0, False))
                        try:
                            if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_MARKETS, timeout=5.0):
                                logger.warning("Rate limit timeout for markets")
                                return JSONResponse(content=[], headers=_default_headers(0, 0, False))
                            _t0_gamma = time.perf_counter()
                            markets_data = await _fetch_gamma_chunk(offset, limit, ttl_override=float(ttl_sec))
                            _obs["gamma_latency_ms"] = round((time.perf_counter() - _t0_gamma) * 1000, 2)
                            _obs["cache_refresh"] = 1
                            _obs["serving_fetched_at_ms"] = int(time.time() * 1000)
                            cache_header = "miss"
                            gamma_fetch_count = 1
                            gamma_scanned = len(markets_data)
                        except ValueError as e:
                            err_msg = str(e)
                            if err_msg in ("gamma_429", "gamma_5xx", "circuit_breaker_open", "gamma_timeout", "gamma_http_error"):
                                return _service_unavailable_503(err_msg.replace("_", " "), _default_headers(0, 0, False))
                            raise
                        except Exception as e:
                            logger.error("Error fetching markets from Polymarket: %s", e, exc_info=True)
                            return JSONResponse(content=[], headers=_default_headers(0, 0, False))
            has_more = len(markets_data) >= limit
        for m in markets_data:
            pid = m.get("id") or m.get("slug") or str(m.get("_id", ""))
            if not pid:
                continue
            is_en = enabled_states.get(pid, False)
            if not _passes_filters(m, is_en):
                continue
            result.append(_to_result_item(m, is_en))
        has_more = len(markets_data) >= limit

    headers = _default_headers(gamma_fetch_count, gamma_scanned, has_more)
    if cache_header is not None:
        headers["X-Cache"] = cache_header
        provider_name = "redis" if type(gamma_cache_provider).__name__ == "RedisCacheProvider" else "memory"
        headers["X-Cache-Provider"] = provider_name
        headers["X-Cache-Refresh"] = "1" if _obs.get("cache_refresh") else "0"
        if _obs.get("serving_fetched_at_ms"):
            age_sec = max(0, int((time.time() * 1000 - _obs["serving_fetched_at_ms"]) / 1000))
            headers["X-Cache-Age"] = str(age_sec)
        if getattr(settings, "debug_cache_headers", False) and _obs.get("cache_key"):
            key_short = _obs["cache_key"].split(":")[-1][-12:] if ":" in _obs["cache_key"] else _obs["cache_key"][-12:]
            headers["X-Cache-Key"] = key_short
    if partial_page and partial_reason:
        headers["X-Partial-Page"] = "true"
        headers["X-Partial-Reason"] = partial_reason
    else:
        headers["X-Partial-Page"] = "false"

    # Fase 8: log estructurado (key_hash, bucket, cache status, redis_latency_ms, gamma_latency_ms, breaker_state)
    if _obs:
        breaker_state = "closed" if await circuit.can_attempt() else "open"
        key_hash = (_obs.get("cache_key") or "").split(":")[-1][-16:] if _obs.get("cache_key") else "-"
        logger.info(
            "markets_cache key_hash=%s bucket=%s cache_status=%s redis_latency_ms=%s gamma_latency_ms=%s breaker_state=%s",
            key_hash,
            _obs.get("bucket", "-"),
            _obs.get("cache_status", "-"),
            _obs.get("redis_latency_ms") if _obs.get("redis_latency_ms") is not None else "-",
            _obs.get("gamma_latency_ms") if _obs.get("gamma_latency_ms") is not None else "-",
            breaker_state,
        )
    return JSONResponse(content=result, headers=headers)


ORDERBOOK_METRICS_MAX_TOKEN_IDS = 100
ORDERBOOK_METRICS_TIMEOUT_MS = 80


class OrderbookMetricsPostBody(BaseModel):
    """Fase 4 (NICE): POST body para orderbook-metrics."""
    token_ids: list[str] = []


async def _orderbook_metrics_for_tokens(token_id_list: list, db: Session) -> dict:
    """Respuesta shape fijo para una lista de token_ids. Usado por GET y POST."""
    from app.core.strategy_engine.state_cache_service import StateCacheService
    import asyncio

    errors: list = []
    partial = False
    timed_out = False
    metrics: dict = {}
    state_cache = StateCacheService(db)

    async def fetch_one(tid: str) -> tuple[str, Optional[dict]]:
        try:
            cache_key = f"pm.orderbook.{tid}"
            data = await state_cache.get(cache_key)
            if data:
                return (
                    tid,
                    {
                        "spread_bps": data.get("spread_bps"),
                        "depth_usdc_at_50bps": data.get("depth_usdc_at_50bps", 0),
                        "impact_bps_for_usdc_1000": data.get("impact_bps_for_usdc_1000", 0),
                        "staleness_ms": data.get("staleness_ms", 0),
                    },
                )
        except Exception as e:
            logger.debug("Orderbook metrics get failed for %s: %s", tid, e)
        return tid, None

    try:
        timeout_sec = ORDERBOOK_METRICS_TIMEOUT_MS / 1000.0
        done, pending = await asyncio.wait(
            [asyncio.create_task(fetch_one(tid)) for tid in token_id_list],
            timeout=timeout_sec,
            return_when=asyncio.ALL_COMPLETED,
        )
        if pending:
            partial = True
            timed_out = True
            errors.append("timeout")
            for p in pending:
                p.cancel()
        for task in done:
            try:
                tid, data = task.result()
                metrics[tid] = data
            except Exception as e:
                partial = True
                errors.append(str(e)[:50])
    except asyncio.TimeoutError:
        partial = True
        timed_out = True
        errors.append("timeout")
    except Exception as e:
        partial = True
        errors.append(str(e)[:50])
        logger.warning("Orderbook metrics error: %s", e)

    found = sum(1 for v in metrics.values() if v is not None)
    missing = len(token_id_list) - found
    for tid in token_id_list:
        if tid not in metrics:
            metrics[tid] = None

    return {
        "found_token_ids_count": found,
        "missing_token_ids_count": missing,
        "partial": partial,
        "timed_out": timed_out,
        "errors": errors[:10],
        "metrics": metrics,
    }


@router.get("/orderbook-metrics")
async def get_markets_orderbook_metrics(
    request: Request,
    token_ids: Optional[str] = Query(None, description="Comma-separated token IDs (max 100). Sin param: usa cache de markets (compatibilidad)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fase 4: Obtiene métricas de orderbook para los token_ids especificados.
    
    Query: token_ids=id1,id2,... (max 100). 400 si excede.
    Sin token_ids (compatibilidad): deriva token IDs desde cache de markets (GET /markets).
    Response shape fijo: found_token_ids_count, missing_token_ids_count, partial, timed_out, errors[], metrics{}.
    Timeout 80ms; responde con partials, nunca falla.
    Rate limit: 60 req/min por IP → 429.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not _orderbook_metrics_consume_rate(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="orderbook-metrics rate limit exceeded (60/min per IP)",
            headers={"Retry-After": str(ORDERBOOK_METRICS_RATE_WINDOW_SEC)},
        )
    from app.core.strategy_engine.state_cache_service import StateCacheService
    from app.core.cache_provider import gamma_cache_provider
    from app.core.gamma_utils import parse_clob_token_ids
    import asyncio

    errors: list = []
    partial = False
    timed_out = False
    metrics: dict = {}

    token_id_list: list = []

    if token_ids and token_ids.strip():
        raw_ids = [x.strip() for x in token_ids.split(",") if x and x.strip()]
        seen: set = set()
        for tid in raw_ids:
            if tid and tid not in seen:
                seen.add(tid)
                token_id_list.append(tid)

        if len(token_id_list) > ORDERBOOK_METRICS_MAX_TOKEN_IDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"token_ids exceeds max {ORDERBOOK_METRICS_MAX_TOKEN_IDS}",
            )
    else:
        # Compatibilidad: derivar token IDs desde cache de markets
        for cache_key in (
            _build_gamma_cache_key(100, 0, "false", "createdAt", False, None),
            _build_gamma_cache_key(50, 0, "false", "createdAt", False, None),
            "polymarket_api:markets:closed=false",
        ):
            cached = await gamma_cache_provider.get(cache_key)
            if cached and isinstance(cached, list):
                seen: set = set()
                for m in cached[:ORDERBOOK_METRICS_MAX_TOKEN_IDS]:
                    parsed = parse_clob_token_ids(m.get("clobTokenIds"))
                    primary = parsed.get("primary") or parsed.get("primary_yes")
                    if primary and primary not in seen:
                        seen.add(primary)
                        token_id_list.append(primary)
                if token_id_list:
                    break
        if not token_id_list:
            errors.append("no token_ids and no markets in cache; call GET /markets first or provide token_ids")

    if not token_id_list:
        return {
            "found_token_ids_count": 0,
            "missing_token_ids_count": 0,
            "partial": False,
            "timed_out": False,
            "errors": errors[:10] if errors else [],
            "metrics": {},
        }

    return await _orderbook_metrics_for_tokens(token_id_list, db)


@router.post("/orderbook-metrics")
async def post_markets_orderbook_metrics(
    request: Request,
    body: OrderbookMetricsPostBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fase 4 (NICE): POST con body { "token_ids": ["id1", "id2", ...] }. Máx 100. Mismo response shape que GET.
    Rate limit: 60 req/min por IP → 429.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not _orderbook_metrics_consume_rate(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="orderbook-metrics rate limit exceeded (60/min per IP)",
            headers={"Retry-After": str(ORDERBOOK_METRICS_RATE_WINDOW_SEC)},
        )
    raw = [x.strip() for x in (body.token_ids or []) if x and str(x).strip()]
    seen: set = set()
    token_id_list: list = []
    for tid in raw:
        t = str(tid).strip()
        if t and t not in seen:
            seen.add(t)
            token_id_list.append(t)
    if len(token_id_list) > ORDERBOOK_METRICS_MAX_TOKEN_IDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"token_ids exceeds max {ORDERBOOK_METRICS_MAX_TOKEN_IDS}",
        )
    if not token_id_list:
        return {
            "found_token_ids_count": 0,
            "missing_token_ids_count": 0,
            "partial": False,
            "timed_out": False,
            "errors": [],
            "metrics": {},
        }
    return await _orderbook_metrics_for_tokens(token_id_list, db)


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
