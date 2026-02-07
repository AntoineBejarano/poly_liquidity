"""
Tests Fase 3 Plan Redis L2: Singleflight (lock 8-10 s, refresh síncrono).
- try_acquire_refresh_lock: con memory siempre True; con Redis solo uno adquiere.
- release_refresh_lock: libera para que otro pueda adquirir.
"""
import pytest
from unittest.mock import patch, MagicMock


class FakeRedisLock:
    """Fake Redis para lock: set_nx simula NX, delete libera."""

    def __init__(self):
        self._store = {}
        self._enabled = True

    async def set_nx(self, key: str, value: str, ttl_seconds: int | None = None):
        if key in self._store:
            return False
        self._store[key] = value
        return True

    async def delete(self, key: str):
        self._store.pop(key, None)
        return True


class TestSingleflightPhase3:
    """Lock de refresh: solo uno adquiere cuando hay Redis."""

    @pytest.mark.asyncio
    async def test_memory_provider_always_acquires(self):
        from app.core.cache_singleflight import try_acquire_refresh_lock
        with patch("app.settings.settings") as m:
            m.cache_provider = "memory"
            assert await try_acquire_refresh_lock("any_key") is True
            assert await try_acquire_refresh_lock("any_key") is True

    @pytest.mark.asyncio
    async def test_redis_lock_only_one_acquires_then_release(self):
        from app.core.cache_singleflight import try_acquire_refresh_lock, release_refresh_lock
        fake = FakeRedisLock()
        mock_settings = MagicMock()
        mock_settings.cache_provider = "redis"
        mock_settings.redis_key_prefix = "poly:"
        mock_settings.redis_lock_ttl_seconds = 10

        with patch("app.settings.settings", mock_settings), \
             patch("app.core.redis_client.redis_client", fake):
            # Primera petición adquiere
            acq1 = await try_acquire_refresh_lock("markets:q:abc")
            assert acq1 is True
            # Segunda petición misma key no adquiere
            acq2 = await try_acquire_refresh_lock("markets:q:abc")
            assert acq2 is False
            # Liberar
            await release_refresh_lock("markets:q:abc")
            # Tras liberar, se puede adquirir de nuevo
            acq3 = await try_acquire_refresh_lock("markets:q:abc")
            assert acq3 is True

    @pytest.mark.asyncio
    async def test_redis_lock_different_keys_independent(self):
        from app.core.cache_singleflight import try_acquire_refresh_lock
        fake = FakeRedisLock()
        mock_settings = MagicMock()
        mock_settings.cache_provider = "redis"
        mock_settings.redis_key_prefix = "poly:"
        mock_settings.redis_lock_ttl_seconds = 10

        with patch("app.settings.settings", mock_settings), \
             patch("app.core.redis_client.redis_client", fake):
            assert await try_acquire_refresh_lock("key_a") is True
            assert await try_acquire_refresh_lock("key_b") is True
            assert await try_acquire_refresh_lock("key_a") is False
            assert await try_acquire_refresh_lock("key_b") is False
