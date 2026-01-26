"""
Unit tests for API Cache.

Según especificación en docs/services/api_cache.md
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch
from app.core.api_cache import APICache, CacheEntry


class TestAPICache:
    """Test cases for API Cache."""
    
    @pytest.fixture
    def cache(self):
        """Fixture para APICache."""
        return APICache()
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache):
        """Test setting and getting from cache."""
        await cache.set("test_key", {"data": "value"})
        result = await cache.get("test_key")
        assert result == {"data": "value"}
    
    @pytest.mark.asyncio
    async def test_cache_get_nonexistent(self, cache):
        """Test getting non-existent key returns None."""
        result = await cache.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, cache):
        """Test cache entries expire after TTL."""
        # Set with very short TTL
        await cache.set("expire_key", "value", ttl=timedelta(seconds=0.1))
        
        # Should be available immediately
        result = await cache.get("expire_key")
        assert result == "value"
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Should be None after expiration
        result = await cache.get("expire_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_invalidate(self, cache):
        """Test invalidating a specific key."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        await cache.invalidate("key1")
        
        assert await cache.get("key1") is None
        assert await cache.get("key2") == "value2"
    
    @pytest.mark.asyncio
    async def test_cache_invalidate_pattern(self, cache):
        """Test invalidating keys by pattern."""
        await cache.set("market_list_1", "value1")
        await cache.set("market_list_2", "value2")
        await cache.set("market_detail_1", "value3")
        
        await cache.invalidate_pattern("market_list")
        
        assert await cache.get("market_list_1") is None
        assert await cache.get("market_list_2") is None
        assert await cache.get("market_detail_1") == "value3"
    
    @pytest.mark.asyncio
    async def test_cache_default_ttl_by_pattern(self, cache):
        """Test default TTL is applied based on key pattern."""
        with patch("app.core.api_cache.datetime") as mock_datetime:
            now = datetime.utcnow()
            mock_datetime.utcnow.return_value = now
            
            # Set without TTL - should use default based on pattern
            await cache.set("market_list_test", "value")
            
            # Verify TTL was set (30 seconds for market_list)
            entry = cache._cache["market_list_test"]
            expected_expires = now + timedelta(seconds=30)
            assert abs((entry.expires_at - expected_expires).total_seconds()) < 1
    
    @pytest.mark.asyncio
    async def test_cache_cleanup_expired(self, cache):
        """Test cleanup_expired removes expired entries."""
        # Set entries with different TTLs
        await cache.set("expire_soon", "value1", ttl=timedelta(seconds=0.1))
        await cache.set("keep_long", "value2", ttl=timedelta(seconds=10))
        
        # Wait for first to expire
        await asyncio.sleep(0.2)
        
        # Cleanup expired
        await cache.cleanup_expired()
        
        # Verify expired entry is removed
        assert await cache.get("expire_soon") is None
        assert await cache.get("keep_long") == "value2"
    
    @pytest.mark.asyncio
    async def test_cache_thread_safety(self, cache):
        """Test cache is thread-safe for concurrent operations."""
        async def set_key(key, value):
            await cache.set(key, value)
            return await cache.get(key)
        
        # Concurrent operations
        results = await asyncio.gather(
            set_key("key1", "value1"),
            set_key("key2", "value2"),
            set_key("key3", "value3"),
        )
        
        assert results == ["value1", "value2", "value3"]

