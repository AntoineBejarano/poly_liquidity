"""
Tests Fase 1 Plan Redis L2: Infra/Config.
- Settings: CACHE_PROVIDER, REDIS_TIMEOUT_MS, REDIS_KEY_PREFIX.
- Redis client usa timeout configurable.
- cache_observability.log_cache_event no falla.
"""
import pytest
from app.settings import settings
from app.core.cache_observability import log_cache_event


class TestPhase1Settings:
    """CACHE_PROVIDER, REDIS_* en settings."""

    def test_cache_provider_exists(self):
        assert hasattr(settings, "cache_provider")
        assert settings.cache_provider in ("memory", "redis")

    def test_redis_timeout_ms_exists(self):
        assert hasattr(settings, "redis_timeout_ms")
        assert 50 <= settings.redis_timeout_ms <= 500

    def test_redis_key_prefix_exists(self):
        assert hasattr(settings, "redis_key_prefix")
        assert isinstance(settings.redis_key_prefix, str)
        assert len(settings.redis_key_prefix) >= 1


class TestPhase1CacheObservability:
    """Log de eventos de cache no debe fallar."""

    def test_log_cache_event_hit(self):
        log_cache_event("hit", provider="memory", hit_type="fresh")

    def test_log_cache_event_miss(self):
        log_cache_event("miss", provider="memory")

    def test_log_cache_event_stale(self):
        log_cache_event("stale_served", provider="redis", hit_type="stale", key_hash="abc")

    def test_log_cache_event_redis_error(self):
        log_cache_event("redis_error", provider="redis", key_hash="x")
