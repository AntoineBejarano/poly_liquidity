"""
Tests Fase 2 Plan Redis L2: RedisCacheProvider + SWR + get_with_meta.
- InMemoryCacheProvider: get_with_meta devuelve CacheHit (fresh), get devuelve payload.
- RedisCacheProvider (con fake Redis): fresh hit, stale hit, hard-expired -> miss, redis down -> None.
"""
import json
import time
import pytest
from app.core.cache_provider import (
    InMemoryCacheProvider,
    RedisCacheProvider,
    CacheHit,
)

# Claves del envelope SWR (mismo que cache_provider)
_KEY_PAYLOAD = "payload"
_KEY_FETCHED_AT_MS = "fetched_at_ms"
_KEY_SOFT_EXPIRY_MS = "soft_expiry_ms"
_KEY_HARD_EXPIRY_MS = "hard_expiry_ms"


class FakeRedis:
    """Redis fake: get/set_json/delete en memoria para tests."""

    def __init__(self):
        self._store = {}
        self._get_returns_none = False  # simular Redis down

    async def get(self, key: str):
        if self._get_returns_none:
            return None
        return self._store.get(key)

    async def set_json(self, key: str, value: dict, ttl_seconds: int | None = None):
        self._store[key] = json.dumps(value)
        return True

    async def delete(self, key: str):
        self._store.pop(key, None)
        return True


class TestInMemoryCacheProviderPhase2:
    """InMemoryCacheProvider con get_with_meta y get."""

    @pytest.mark.asyncio
    async def test_get_with_meta_returns_fresh_hit(self):
        provider = InMemoryCacheProvider()
        await provider.set("k1", {"data": 42}, ttl_seconds=60.0)
        hit = await provider.get_with_meta("k1")
        assert hit is not None
        assert isinstance(hit, CacheHit)
        assert hit.payload == {"data": 42}
        assert hit.status == "fresh"
        now_ms = time.time() * 1000
        assert hit.fetched_at_ms <= now_ms + 1000  # fetched in the past (or ~now)
        assert hit.soft_expiry_ms >= now_ms  # expiry in the future (UTC-consistent)
        assert hit.hard_expiry_ms == hit.soft_expiry_ms

    @pytest.mark.asyncio
    async def test_get_returns_payload(self):
        provider = InMemoryCacheProvider()
        await provider.set("k2", [1, 2, 3], ttl_seconds=60.0)
        val = await provider.get("k2")
        assert val == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_get_with_meta_miss_returns_none(self):
        provider = InMemoryCacheProvider()
        hit = await provider.get_with_meta("nonexistent")
        assert hit is None

    @pytest.mark.asyncio
    async def test_get_miss_returns_none(self):
        provider = InMemoryCacheProvider()
        assert await provider.get("nonexistent") is None


class TestRedisCacheProviderPhase2:
    """RedisCacheProvider con fake Redis: fresh, stale, hard-expired, redis down."""

    @pytest.mark.asyncio
    async def test_fresh_hit(self):
        redis = FakeRedis()
        now_ms = time.time() * 1000
        envelope = {
            _KEY_PAYLOAD: {"markets": []},
            _KEY_FETCHED_AT_MS: now_ms - 5000,
            _KEY_SOFT_EXPIRY_MS: now_ms + 10_000,
            _KEY_HARD_EXPIRY_MS: now_ms + 20_000,
        }
        await redis.set_json("poly:markets:foo", envelope, ttl_seconds=30)
        # RedisCacheProvider with prefix "poly:" will request key "markets:foo" -> full key "poly:markets:foo"
        provider = RedisCacheProvider(redis, key_prefix="poly:", stale_grace_seconds=60.0)
        hit = await provider.get_with_meta("markets:foo")
        assert hit is not None
        assert hit.payload == {"markets": []}
        assert hit.status == "fresh"
        assert hit.fetched_at_ms == envelope[_KEY_FETCHED_AT_MS]
        assert hit.soft_expiry_ms == envelope[_KEY_SOFT_EXPIRY_MS]
        assert hit.hard_expiry_ms == envelope[_KEY_HARD_EXPIRY_MS]

    @pytest.mark.asyncio
    async def test_stale_hit(self):
        redis = FakeRedis()
        now_ms = time.time() * 1000
        envelope = {
            _KEY_PAYLOAD: {"list": [1, 2]},
            _KEY_FETCHED_AT_MS: now_ms - 15_000,
            _KEY_SOFT_EXPIRY_MS: now_ms - 5_000,   # ya pasó soft
            _KEY_HARD_EXPIRY_MS: now_ms + 10_000,   # aún dentro de hard
        }
        await redis.set_json("poly:stale_key", envelope, ttl_seconds=30)
        provider = RedisCacheProvider(redis, key_prefix="poly:", stale_grace_seconds=60.0)
        hit = await provider.get_with_meta("stale_key")
        assert hit is not None
        assert hit.payload == {"list": [1, 2]}
        assert hit.status == "stale"

    @pytest.mark.asyncio
    async def test_hard_expired_returns_none(self):
        redis = FakeRedis()
        now_ms = time.time() * 1000
        envelope = {
            _KEY_PAYLOAD: {"old": True},
            _KEY_FETCHED_AT_MS: now_ms - 30_000,
            _KEY_SOFT_EXPIRY_MS: now_ms - 20_000,
            _KEY_HARD_EXPIRY_MS: now_ms - 1_000,   # ya pasó hard
        }
        await redis.set_json("poly:expired_key", envelope, ttl_seconds=30)
        provider = RedisCacheProvider(redis, key_prefix="poly:", stale_grace_seconds=60.0)
        hit = await provider.get_with_meta("expired_key")
        assert hit is None

    @pytest.mark.asyncio
    async def test_redis_down_returns_none(self):
        redis = FakeRedis()
        redis._get_returns_none = True
        provider = RedisCacheProvider(redis, key_prefix="poly:", stale_grace_seconds=60.0)
        hit = await provider.get_with_meta("any_key")
        assert hit is None
        val = await provider.get("any_key")
        assert val is None

    @pytest.mark.asyncio
    async def test_set_populates_l1_and_redis(self):
        redis = FakeRedis()
        provider = RedisCacheProvider(redis, key_prefix="poly:", stale_grace_seconds=60.0)
        await provider.set("mykey", {"x": 1}, ttl_seconds=30.0)
        hit = await provider.get_with_meta("mykey")
        assert hit is not None
        assert hit.payload == {"x": 1}
        assert hit.status == "fresh"
        # L1 fue poblado por set; siguiente get_with_meta puede venir de L1 (mismo resultado)
        hit2 = await provider.get_with_meta("mykey")
        assert hit2 is not None
        assert hit2.payload == {"x": 1}

    @pytest.mark.asyncio
    async def test_l2_hit_populates_l1(self):
        redis = FakeRedis()
        now_ms = time.time() * 1000
        envelope = {
            _KEY_PAYLOAD: "from_l2",
            _KEY_FETCHED_AT_MS: now_ms,
            _KEY_SOFT_EXPIRY_MS: now_ms + 5000,
            _KEY_HARD_EXPIRY_MS: now_ms + 15000,
        }
        await redis.set_json("poly:l2key", envelope, ttl_seconds=30)
        provider = RedisCacheProvider(redis, key_prefix="poly:", stale_grace_seconds=60.0)
        # Primera lectura: L2 hit -> debe poblar L1
        hit1 = await provider.get_with_meta("l2key")
        assert hit1 is not None
        assert hit1.payload == "from_l2"
        # Segunda lectura: debe venir de L1 (sin llamar a redis si quisiéramos verificar; al menos mismo resultado)
        hit2 = await provider.get_with_meta("l2key")
        assert hit2 is not None
        assert hit2.payload == "from_l2"

    @pytest.mark.asyncio
    async def test_delete_removes_l1_and_redis(self):
        redis = FakeRedis()
        provider = RedisCacheProvider(redis, key_prefix="poly:", stale_grace_seconds=60.0)
        await provider.set("delkey", {"a": 1}, ttl_seconds=60.0)
        assert await provider.get("delkey") is not None
        await provider.delete("delkey")
        assert await provider.get("delkey") is None
        assert await provider.get_with_meta("delkey") is None