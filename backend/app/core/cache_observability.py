"""
Cache observability (Plan Redis L2).

Structured logging for cache hit/miss/stale, Redis errors/timeouts,
lock contention (singleflight), and gamma fetch count per request.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def log_cache_event(
    event_type: str,
    *,
    provider: str = "memory",
    key_hash: Optional[str] = None,
    hit_type: Optional[str] = None,
    redis_latency_ms: Optional[float] = None,
    gamma_latency_ms: Optional[float] = None,
    gamma_fetch_count: Optional[int] = None,
    breaker_state: Optional[str] = None,
    lock_contention: bool = False,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """
    Log a cache-related event for aggregation and debugging.

    event_type: "hit" | "miss" | "stale_served" | "redis_error" | "redis_timeout" | "lock_acquired" | "lock_contention"
    provider: "memory" | "redis"
    hit_type: "fresh" | "stale" (when event_type is hit or stale_served)
    """
    payload: dict[str, Any] = {
        "event": "cache",
        "event_type": event_type,
        "provider": provider,
    }
    if key_hash is not None:
        payload["key_hash"] = key_hash
    if hit_type is not None:
        payload["hit_type"] = hit_type
    if redis_latency_ms is not None:
        payload["redis_latency_ms"] = round(redis_latency_ms, 2)
    if gamma_latency_ms is not None:
        payload["gamma_latency_ms"] = round(gamma_latency_ms, 2)
    if gamma_fetch_count is not None:
        payload["gamma_fetch_count"] = gamma_fetch_count
    if breaker_state is not None:
        payload["breaker_state"] = breaker_state
    if lock_contention:
        payload["lock_contention"] = True
    if extra:
        payload["extra"] = extra

    if event_type in ("redis_error", "redis_timeout", "lock_contention"):
        logger.warning("Cache event: %s", payload)
    else:
        logger.debug("Cache event: %s", payload)
