"""
Circuit breaker para Gamma markets: in-memory o Redis-backed (Fase 7).

Cuando CACHE_PROVIDER=redis y Redis está disponible, el estado (fallos, OPEN) se guarda
en Redis para que varios pods compartan el mismo breaker. Transiciones logueadas.
Interfaz async para compatibilidad con Redis.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Keys Redis (con prefijo se añade en runtime)
BREAKER_FAILURES_SUFFIX = "breaker:markets:failures"
BREAKER_OPEN_SUFFIX = "breaker:markets:open"
FAILURE_THRESHOLD = 3
WINDOW_TTL_SEC = 60
OPEN_TTL_SEC = 60


def _breaker_failures_key(prefix: str) -> str:
    return f"{prefix.rstrip(':')}:{BREAKER_FAILURES_SUFFIX}"


def _breaker_open_key(prefix: str) -> str:
    return f"{prefix.rstrip(':')}:{BREAKER_OPEN_SUFFIX}"


class RedisGammaCircuitBreaker:
    """
    Circuit breaker Gamma markets con estado en Redis.
    Contador de fallos por ventana (TTL 60s), estado OPEN con TTL 60s.
    """

    def __init__(
        self,
        redis_client: any,
        key_prefix: str = "poly:",
        failure_threshold: int = FAILURE_THRESHOLD,
        window_ttl_sec: int = WINDOW_TTL_SEC,
        open_ttl_sec: int = OPEN_TTL_SEC,
    ):
        self._redis = redis_client
        self._prefix = key_prefix.rstrip(":") + ":" if key_prefix else ""
        self._threshold = failure_threshold
        self._window_ttl = window_ttl_sec
        self._open_ttl = open_ttl_sec

    def _failures_key(self) -> str:
        return _breaker_failures_key(self._prefix)

    def _open_key(self) -> str:
        return _breaker_open_key(self._prefix)

    async def can_attempt(self) -> bool:
        """True si el circuito permite intentar (OPEN key no existe o expiró)."""
        try:
            if not getattr(self._redis, "_enabled", True):
                return True
            exists = await self._redis.exists(self._open_key())
            return not exists
        except Exception as e:
            logger.debug("Gamma breaker can_attempt (Redis): %s, allowing attempt", e)
            return True

    async def record_failure(self) -> None:
        """Incrementa fallos; si alcanza threshold, abre el circuito en Redis y loguea."""
        try:
            if not getattr(self._redis, "_enabled", True):
                return
            fk = self._failures_key()
            ok = self._open_key()
            raw = await self._redis.get(fk)
            count = (int(raw) + 1) if raw else 1
            await self._redis.set(fk, str(count), ttl_seconds=self._window_ttl)
            if count >= self._threshold:
                await self._redis.set(ok, "1", ttl_seconds=self._open_ttl)
                logger.warning(
                    "Gamma markets circuit breaker OPEN (Redis): failure_count=%s threshold=%s",
                    count, self._threshold,
                )
        except Exception as e:
            logger.debug("Gamma breaker record_failure (Redis): %s", e)

    async def record_success(self) -> None:
        """Cierra el circuito (borra OPEN) y opcionalmente resetea fallos."""
        try:
            if not getattr(self._redis, "_enabled", True):
                return
            await self._redis.delete(self._open_key())
            await self._redis.delete(self._failures_key())
        except Exception as e:
            logger.debug("Gamma breaker record_success (Redis): %s", e)


class InMemoryGammaCircuitBreaker:
    """Wrapper async sobre CircuitBreaker in-memory (misma interfaz que Redis)."""

    def __init__(self):
        from app.core.runtime_supervisor.circuit_breaker import CircuitBreaker
        self._cb = CircuitBreaker(
            name="gamma_markets",
            failure_threshold=FAILURE_THRESHOLD,
            window_seconds=WINDOW_TTL_SEC,
            cooldown_seconds=OPEN_TTL_SEC,
        )

    async def can_attempt(self) -> bool:
        return self._cb.can_attempt()

    async def record_failure(self) -> None:
        self._cb.record_failure()

    async def record_success(self) -> None:
        self._cb.record_success()


def get_gamma_markets_circuit_breaker():
    """
    Devuelve el circuit breaker para Gamma markets.
    Si CACHE_PROVIDER=redis y Redis disponible → RedisGammaCircuitBreaker.
    Si no → InMemoryGammaCircuitBreaker.
    """
    from app.settings import settings
    if getattr(settings, "cache_provider", "memory") == "redis":
        try:
            from app.core.redis_client import redis_client
            if getattr(redis_client, "_enabled", False):
                prefix = getattr(settings, "redis_key_prefix", "poly:")
                return RedisGammaCircuitBreaker(redis_client, key_prefix=prefix)
        except Exception as e:
            logger.debug("Gamma breaker using in-memory (Redis unavailable): %s", e)
    return InMemoryGammaCircuitBreaker()
