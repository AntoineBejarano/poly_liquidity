"""
API cache service to reduce redundant calls to Polymarket Data API.

This cache is critical for staying within rate limits, especially for:
- Market data that doesn't change frequently
- Event data that's checked repeatedly
- Order book snapshots
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cache entry with expiration."""
    data: Any
    expires_at: datetime
    created_at: datetime


class APICache:
    """
    In-memory cache for API responses with TTL.
    
    Thread-safe for async operations.
    """
    
    def __init__(self):
        """Initialize cache with default TTLs."""
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        
        # Default TTLs per cache key pattern
        self._default_ttls = {
            "market_list": timedelta(seconds=30),  # Market list changes frequently
            "market_detail": timedelta(seconds=10),  # Individual market data
            "orderbook": timedelta(seconds=5),  # Order book changes very frequently
            "price": timedelta(seconds=5),  # Price updates frequently
            "event_data": timedelta(seconds=60),  # Event data changes less frequently
        }
    
    def _get_ttl(self, key: str) -> timedelta:
        """Get TTL for a cache key based on pattern."""
        for pattern, ttl in self._default_ttls.items():
            if pattern in key:
                return ttl
        # Default TTL
        return timedelta(seconds=10)
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if it exists and hasn't expired.
        
        Returns:
            Cached value or None if not found or expired.
        """
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if datetime.utcnow() > entry.expires_at:
                del self._cache[key]
                return None
            
            return entry.data
    
    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None):
        """
        Set cached value with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live. If None, uses default TTL based on key pattern.
        """
        async with self._lock:
            if ttl is None:
                ttl = self._get_ttl(key)
            
            expires_at = datetime.utcnow() + ttl
            
            self._cache[key] = CacheEntry(
                data=value,
                expires_at=expires_at,
                created_at=datetime.utcnow()
            )
    
    async def invalidate(self, key: str):
        """Invalidate a specific cache key."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all cache keys matching a pattern."""
        async with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
    
    async def clear(self):
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
    
    async def cleanup_expired(self):
        """Remove expired entries from cache."""
        async with self._lock:
            now = datetime.utcnow()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry.expires_at
            ]
            for key in expired_keys:
                del self._cache[key]


# Global cache instance
api_cache = APICache()


