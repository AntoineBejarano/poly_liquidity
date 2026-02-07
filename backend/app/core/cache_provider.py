"""
Cache provider abstraction (Redis-ready).

Protocolo get/set con TTL para poder sustituir la implementación in-memory
por Redis u otro backend sin cambiar los consumidores.

Plan Redis L2: get_with_meta() devuelve CacheHit (payload + status fresh/stale) para que
el endpoint decida si disparar refresh y setear headers.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional, Protocol, runtime_checkable

from dataclasses import dataclass

logger = logging.getLogger(__name__)

# --- SWR envelope keys (valor en Redis y en L1) ---
_KEY_PAYLOAD = "payload"
_KEY_FETCHED_AT_MS = "fetched_at_ms"
_KEY_SOFT_EXPIRY_MS = "soft_expiry_ms"
_KEY_HARD_EXPIRY_MS = "hard_expiry_ms"


@dataclass
class CacheHit:
    """Resultado de get_with_meta: payload + estado fresh/stale para decisión en endpoint."""
    payload: Any
    status: str  # "fresh" | "stale"
    fetched_at_ms: float
    soft_expiry_ms: float
    hard_expiry_ms: float


@dataclass
class _CacheEntry:
    data: Any
    expires_at: datetime


@runtime_checkable
class CacheProvider(Protocol):
    """Protocolo para backend de cache (in-memory hoy, Redis u otro después)."""

    async def get(self, key: str) -> Optional[Any]:
        """Devuelve el valor si existe y no ha expirado, sino None."""
        ...

    async def get_with_meta(self, key: str) -> Optional[CacheHit]:
        """Devuelve CacheHit (payload + status fresh/stale) o None si no existe o hard-expired."""
        ...

    async def set(self, key: str, value: Any, ttl_seconds: float = 60.0) -> None:
        """Almacena el valor con TTL en segundos."""
        ...


class InMemoryCacheProvider:
    """
    Implementación en memoria del protocolo CacheProvider.
    Thread-safe para uso async. Sustituible por RedisCacheProvider manteniendo la misma interfaz.
    Soporta get_with_meta para compatibilidad con flujo SWR (siempre status=fresh hasta expiry).
    """

    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        hit = await self.get_with_meta(key)
        return hit.payload if hit else None

    async def get_with_meta(self, key: str) -> Optional[CacheHit]:
        async with self._lock:
            if key not in self._store:
                return None
            entry = self._store[key]
            now = datetime.utcnow()
            if now > entry.expires_at:
                del self._store[key]
                return None
            # In-memory: sin soft/hard, todo "fresh" hasta expires_at
            # Usar epoch UTC para evitar que .timestamp() interprete como local (Windows)
            epoch_utc = datetime(1970, 1, 1)
            exp_ts = (entry.expires_at - epoch_utc).total_seconds() * 1000
            # fetched_at aproximado (no guardamos TTL; supongo 60s atrás)
            fetched_ms = exp_ts - 60_000
            return CacheHit(
                payload=entry.data,
                status="fresh",
                fetched_at_ms=fetched_ms,
                soft_expiry_ms=exp_ts,
                hard_expiry_ms=exp_ts,
            )

    async def set(self, key: str, value: Any, ttl_seconds: float = 60.0) -> None:
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        async with self._lock:
            self._store[key] = _CacheEntry(data=value, expires_at=expires_at)


class RedisCacheProvider:
    """
    Provider L2 con Redis y L1 in-memory (SWR).
    Formato en Redis: JSON con payload, fetched_at_ms, soft_expiry_ms, hard_expiry_ms.
    get_with_meta devuelve CacheHit para que el endpoint decida refresh y headers.
    En L2 hit (fresh o stale) siempre se puebla L1. Si Redis falla, se usa solo L1.
    """

    def __init__(
        self,
        redis_client: Any,
        key_prefix: str = "poly:",
        stale_grace_seconds: float = 60.0,
    ) -> None:
        self._redis = redis_client
        self._prefix = key_prefix.rstrip(":") + ":" if key_prefix else ""
        self._stale_grace = stale_grace_seconds
        self._l1: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    async def get_with_meta(self, key: str) -> Optional[CacheHit]:
        now_ms = time.time() * 1000
        full = self._full_key(key)

        async with self._lock:
            if key in self._l1:
                entry = self._l1[key]
                hard_ms = entry[_KEY_HARD_EXPIRY_MS]
                if now_ms >= hard_ms:
                    del self._l1[key]
                else:
                    soft_ms = entry[_KEY_SOFT_EXPIRY_MS]
                    status = "fresh" if now_ms < soft_ms else "stale"
                    return CacheHit(
                        payload=entry[_KEY_PAYLOAD],
                        status=status,
                        fetched_at_ms=entry[_KEY_FETCHED_AT_MS],
                        soft_expiry_ms=soft_ms,
                        hard_expiry_ms=hard_ms,
                    )

        raw = await self._redis.get(full)
        if not raw:
            return None
        try:
            entry = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Invalid SWR JSON in Redis key %s: %s", full, e)
            return None
        payload = entry.get(_KEY_PAYLOAD)
        fetched_ms = entry.get(_KEY_FETCHED_AT_MS, 0)
        soft_ms = entry.get(_KEY_SOFT_EXPIRY_MS, 0)
        hard_ms = entry.get(_KEY_HARD_EXPIRY_MS, 0)
        if now_ms >= hard_ms:
            return None
        status = "fresh" if now_ms < soft_ms else "stale"
        # L2 hit → poblar L1 siempre (coherencia L1/L2)
        async with self._lock:
            self._l1[key] = {
                _KEY_PAYLOAD: payload,
                _KEY_FETCHED_AT_MS: fetched_ms,
                _KEY_SOFT_EXPIRY_MS: soft_ms,
                _KEY_HARD_EXPIRY_MS: hard_ms,
            }
        return CacheHit(
            payload=payload,
            status=status,
            fetched_at_ms=fetched_ms,
            soft_expiry_ms=soft_ms,
            hard_expiry_ms=hard_ms,
        )

    async def get(self, key: str) -> Optional[Any]:
        hit = await self.get_with_meta(key)
        return hit.payload if hit else None

    async def set(self, key: str, value: Any, ttl_seconds: float = 60.0) -> None:
        now_ms = time.time() * 1000
        soft_ttl = ttl_seconds
        hard_ttl = ttl_seconds + self._stale_grace
        soft_exp_ms = now_ms + soft_ttl * 1000
        hard_exp_ms = now_ms + hard_ttl * 1000
        entry = {
            _KEY_PAYLOAD: value,
            _KEY_FETCHED_AT_MS: now_ms,
            _KEY_SOFT_EXPIRY_MS: soft_exp_ms,
            _KEY_HARD_EXPIRY_MS: hard_exp_ms,
        }
        async with self._lock:
            self._l1[key] = entry
        full = self._full_key(key)
        try:
            ok = await self._redis.set_json(full, entry, ttl_seconds=int(hard_ttl))
            if not ok:
                logger.debug("Redis set failed for key %s (L1 updated)", full)
        except Exception as e:
            logger.debug("Redis set error for key %s: %s (L1 updated)", full, e)

    async def delete(self, key: str) -> None:
        full = self._full_key(key)
        async with self._lock:
            self._l1.pop(key, None)
        try:
            await self._redis.delete(full)
        except Exception as e:
            logger.debug("Redis delete error for key %s: %s", full, e)


def _resolve_gamma_cache_provider() -> Any:
    """Resuelve el provider según CACHE_PROVIDER (memory | redis)."""
    from app.settings import settings
    if getattr(settings, "cache_provider", "memory") == "redis":
        from app.core.redis_client import redis_client
        prefix = getattr(settings, "redis_key_prefix", "poly:")
        return RedisCacheProvider(redis_client, key_prefix=prefix, stale_grace_seconds=60.0)
    return InMemoryCacheProvider()


# Instancia por defecto para Gamma (resuelta por CACHE_PROVIDER)
gamma_cache_provider: CacheProvider = _resolve_gamma_cache_provider()
