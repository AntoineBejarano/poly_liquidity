"""
Cache provider abstraction (Redis-ready).

Protocolo get/set con TTL para poder sustituir la implementación in-memory
por Redis u otro backend sin cambiar los consumidores.

Key schema (Gamma markets):
  - polymarket_api:markets:closed={closed}:limit={limit}:offset={offset}:order={order}:ascending={ascending}[::tag_id={tag_id}]
  TTL: 60s. En Redis usar el mismo prefijo (ej. gamma:markets:...) y TTL; opcionalmente
  singleflight/semáforo por clave para evitar cache stampede.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional, Protocol, runtime_checkable

from dataclasses import dataclass


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

    async def set(self, key: str, value: Any, ttl_seconds: float = 60.0) -> None:
        """Almacena el valor con TTL en segundos."""
        ...


class InMemoryCacheProvider:
    """
    Implementación en memoria del protocolo CacheProvider.
    Thread-safe para uso async. Sustituible por RedisCacheProvider manteniendo la misma interfaz.
    """

    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._store:
                return None
            entry = self._store[key]
            if datetime.utcnow() > entry.expires_at:
                del self._store[key]
                return None
            return entry.data

    async def set(self, key: str, value: Any, ttl_seconds: float = 60.0) -> None:
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        async with self._lock:
            self._store[key] = _CacheEntry(data=value, expires_at=expires_at)


# Instancia por defecto para Gamma (y en el futuro inyectable vía config/dependency)
gamma_cache_provider: CacheProvider = InMemoryCacheProvider()
