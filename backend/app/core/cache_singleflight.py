"""
Singleflight / anti-stampede para cache (Plan Redis L2 Fase 3).

Lock por key en Redis: solo un request hace refresh a Gamma; el resto sirve stale.
Lock TTL 8–10 s (gamma timeout ~5 s + margen). Liberar (DELETE) al terminar refresh.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lock key suffix (se combina con prefijo en runtime)
LOCK_KEY_SUFFIX = "lock:"


def _lock_key(prefix: str, cache_key: str) -> str:
    """Key Redis para el lock: {prefix}lock:{cache_key}."""
    p = prefix.rstrip(":") + ":" if prefix else ""
    return f"{p}{LOCK_KEY_SUFFIX}{cache_key}"


async def try_acquire_refresh_lock(cache_key: str) -> bool:
    """
    Intenta adquirir el lock de refresh para esta cache_key.
    Solo un request por key debe hacer refresh; el resto sirve stale.

    - Si CACHE_PROVIDER=redis y Redis disponible: SET NX con TTL redis_lock_ttl_seconds.
    - Si no (memory o Redis no disponible): devuelve True (sin lock distribuido).
    """
    from app.settings import settings
    if getattr(settings, "cache_provider", "memory") != "redis":
        return True
    try:
        from app.core.redis_client import redis_client
        if not redis_client._enabled:
            return True
        key = _lock_key(getattr(settings, "redis_key_prefix", "poly:"), cache_key)
        ttl = getattr(settings, "redis_lock_ttl_seconds", 10)
        acquired = await redis_client.set_nx(key, "1", ttl_seconds=ttl)
        if acquired:
            from app.core.cache_observability import log_cache_event
            log_cache_event("lock_acquired", provider="redis", key_hash=cache_key[-32:] if len(cache_key) > 32 else cache_key)
        else:
            from app.core.cache_observability import log_cache_event
            log_cache_event("lock_contention", provider="redis", lock_contention=True, key_hash=cache_key[-32:] if len(cache_key) > 32 else cache_key)
        return acquired
    except Exception as e:
        logger.debug("Singleflight lock acquire failed (fallback to no lock): %s", e)
        return True


async def release_refresh_lock(cache_key: str) -> None:
    """
    Libera el lock de refresh (DELETE). Llamar tras terminar el refresh síncrono.
    No-op si no se usa Redis o Redis no disponible.
    """
    from app.settings import settings
    if getattr(settings, "cache_provider", "memory") != "redis":
        return
    try:
        from app.core.redis_client import redis_client
        if not redis_client._enabled:
            return
        key = _lock_key(getattr(settings, "redis_key_prefix", "poly:"), cache_key)
        await redis_client.delete(key)
    except Exception as e:
        logger.debug("Singleflight lock release failed: %s", e)
