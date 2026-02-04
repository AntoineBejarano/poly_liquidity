"""
Redis client for distributed caching.

Supports both:
1. TCP native connection (preferred) - using redis.asyncio
2. REST API (legacy) - using httpx for Upstash REST API

Falls back gracefully if Redis is not configured or fails.
All operations have strict timeouts (200ms) to prevent blocking.
"""
import asyncio
import json
import logging
import ssl
from typing import Optional, Any, Dict, TYPE_CHECKING
from app.settings import settings

logger = logging.getLogger(__name__)

# Try to import redis for TCP connection
try:
    import redis.asyncio as redis
    REDIS_TCP_AVAILABLE = True
    if TYPE_CHECKING:
        RedisType = redis.Redis
    else:
        RedisType = Any
except ImportError:
    REDIS_TCP_AVAILABLE = False
    RedisType = Any
    if getattr(settings, "redis_url", None):
        logger.error(
            "REDIS_URL is set but redis package is not installed. "
            "Install with: pip install 'redis[hiredis]'"
        )
        if getattr(settings, "environment", "development") == "production":
            raise RuntimeError(
                "REDIS_URL requires redis package in production. "
                "Install: pip install 'redis[hiredis]'"
            )
    else:
        logger.warning("redis package not installed, TCP connection unavailable")

# Try to import httpx for REST API (legacy)
try:
    import httpx
    HTTPX_AVAILABLE = True
    if TYPE_CHECKING:
        HttpxClientType = httpx.AsyncClient
    else:
        HttpxClientType = Any
except ImportError:
    HTTPX_AVAILABLE = False
    HttpxClientType = Any
    logger.warning("httpx not available for REST API fallback")


class RedisClient:
    """
    Redis client supporting both TCP native and REST API.
    
    Singleton pattern: All instances share the same connection.
    Falls back gracefully if Redis is not configured or fails.
    All operations have strict timeouts (200ms) to prevent blocking.
    """
    
    # Timeout for all Redis operations (500ms to allow for REST API latency)
    # For TCP connections this is very fast, but REST API (Upstash) may need more time
    OPERATION_TIMEOUT = 0.5
    
    def __init__(self):
        """Initialize Redis client."""
        self._tcp_client: Optional[RedisType] = None
        self._rest_client: Optional[HttpxClientType] = None
        self._enabled: bool = False
        self._connection_type: Optional[str] = None  # 'tcp' or 'rest'
        self._redis_url: Optional[str] = None
        self._rest_base_url: Optional[str] = None
        self._rest_token: Optional[str] = None
        
        # Priority 1: Try TCP connection (redis_url)
        if settings.redis_url and REDIS_TCP_AVAILABLE:
            self._enabled = True
            self._connection_type = 'tcp'
            self._redis_url = settings.redis_url
            logger.info("Redis client enabled (TCP native)")
        # Priority 2: Fallback to REST API (legacy)
        elif settings.upstash_redis_rest_url and settings.upstash_redis_rest_token and HTTPX_AVAILABLE:
            self._enabled = True
            self._connection_type = 'rest'
            self._rest_base_url = settings.upstash_redis_rest_url.rstrip('/')
            self._rest_token = settings.upstash_redis_rest_token
            logger.info("Redis client enabled (REST API - legacy)")
        else:
            logger.warning("Redis not configured - using in-memory cache only")
    
    async def _get_tcp_client(self) -> Optional[RedisType]:
        """Get or create TCP Redis client."""
        if not self._enabled or self._connection_type != 'tcp' or not REDIS_TCP_AVAILABLE:
            return None
        
        if self._tcp_client is None:
            try:
                # rediss:// (TLS): Upstash y entornos cloud a veces requieren ssl_cert_reqs=CERT_NONE
                conn_kwargs: Dict[str, Any] = {
                    "socket_connect_timeout": self.OPERATION_TIMEOUT,
                    "socket_timeout": self.OPERATION_TIMEOUT,
                    "retry_on_timeout": False,
                    "health_check_interval": 30,
                    "decode_responses": True,
                }
                if self._redis_url and self._redis_url.strip().lower().startswith("rediss://"):
                    conn_kwargs["ssl_cert_reqs"] = ssl.CERT_NONE
                self._tcp_client = await redis.from_url(
                    self._redis_url,
                    **conn_kwargs,
                )
                # Test connection
                await asyncio.wait_for(
                    self._tcp_client.ping(),
                    timeout=self.OPERATION_TIMEOUT
                )
            except Exception as e:
                logger.warning(
                    "Redis TCP unavailable, using in-memory cache. "
                    "REDIS_URL is set but connection failed: %s (%s). "
                    "Check URL (no quotes in Railway), network and TLS.",
                    type(e).__name__,
                    str(e) or repr(e),
                )
                self._tcp_client = None
                self._enabled = False
                return None
        
        return self._tcp_client
    
    async def _get_rest_client(self) -> Optional[HttpxClientType]:
        """Get or create REST API client."""
        if not self._enabled or self._connection_type != 'rest' or not HTTPX_AVAILABLE:
            return None
        
        if self._rest_client is None:
            self._rest_client = httpx.AsyncClient(
                timeout=self.OPERATION_TIMEOUT,
                headers={
                    "Authorization": f"Bearer {self._rest_token}",
                    "Content-Type": "application/json"
                }
            )
        return self._rest_client
    
    async def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis with strict timeout.
        
        Args:
            key: Redis key
            
        Returns:
            Value as string, or None if not found, Redis disabled, or timeout
        """
        if not self._enabled:
            return None
        
        try:
            if self._connection_type == 'tcp':
                client = await self._get_tcp_client()
                if client is None:
                    return None
                return await asyncio.wait_for(
                    client.get(key),
                    timeout=self.OPERATION_TIMEOUT
                )
            else:  # REST API
                client = await self._get_rest_client()
                if client is None:
                    return None
                url = f"{self._rest_base_url}/get/{key}"
                response = await asyncio.wait_for(
                    client.get(url),
                    timeout=self.OPERATION_TIMEOUT
                )
                response.raise_for_status()
                data = response.json()
                return data.get("result")
        except asyncio.TimeoutError:
            logger.debug(f"Redis GET timeout for key '{key}', using fallback")
            return None
        except Exception as e:
            logger.debug(f"Redis GET error for key '{key}': {e}, using fallback")
            return None
    
    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        """
        Set value in Redis with optional TTL and strict timeout.
        
        Args:
            key: Redis key
            value: Value to set
            ttl_seconds: Optional TTL in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self._enabled:
            return False
        
        try:
            if self._connection_type == 'tcp':
                client = await self._get_tcp_client()
                if client is None:
                    return False
                if ttl_seconds:
                    await asyncio.wait_for(
                        client.setex(key, ttl_seconds, value),
                        timeout=self.OPERATION_TIMEOUT
                    )
                else:
                    await asyncio.wait_for(
                        client.set(key, value),
                        timeout=self.OPERATION_TIMEOUT
                    )
                return True
            else:  # REST API
                client = await self._get_rest_client()
                if client is None:
                    return False
                url = f"{self._rest_base_url}/set/{key}"
                payload = {"value": value}
                if ttl_seconds:
                    payload["ex"] = ttl_seconds
                
                await asyncio.wait_for(
                    client.post(url, json=payload),
                    timeout=self.OPERATION_TIMEOUT
                )
                return True
        except asyncio.TimeoutError:
            logger.debug(f"Redis SET timeout for key '{key}' (>{self.OPERATION_TIMEOUT}s), using fallback")
            return False
        except Exception as e:
            logger.debug(f"Redis SET error for key '{key}': {e}, using fallback")
            return False
    
    async def setex(self, key: str, value: str, ttl_seconds: int) -> bool:
        """Alias for set with TTL."""
        return await self.set(key, value, ttl_seconds)
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from Redis with strict timeout.
        
        Args:
            key: Redis key
            
        Returns:
            True if successful, False otherwise
        """
        if not self._enabled:
            return False
        
        try:
            if self._connection_type == 'tcp':
                client = await self._get_tcp_client()
                if client is None:
                    return False
                await asyncio.wait_for(
                    client.delete(key),
                    timeout=self.OPERATION_TIMEOUT
                )
                return True
            else:  # REST API
                client = await self._get_rest_client()
                if client is None:
                    return False
                url = f"{self._rest_base_url}/del/{key}"
                await asyncio.wait_for(
                    client.post(url),
                    timeout=self.OPERATION_TIMEOUT
                )
                return True
        except asyncio.TimeoutError:
            logger.debug(f"Redis DEL timeout for key '{key}', using fallback")
            return False
        except Exception as e:
            logger.debug(f"Redis DEL error for key '{key}': {e}, using fallback")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis with strict timeout.
        
        Args:
            key: Redis key
            
        Returns:
            True if key exists, False otherwise
        """
        if not self._enabled:
            return False
        
        try:
            if self._connection_type == 'tcp':
                client = await self._get_tcp_client()
                if client is None:
                    return False
                result = await asyncio.wait_for(
                    client.exists(key),
                    timeout=self.OPERATION_TIMEOUT
                )
                return result > 0
            else:  # REST API
                client = await self._get_rest_client()
                if client is None:
                    return False
                url = f"{self._rest_base_url}/exists/{key}"
                response = await asyncio.wait_for(
                    client.get(url),
                    timeout=self.OPERATION_TIMEOUT
                )
                response.raise_for_status()
                data = response.json()
                return data.get("result", 0) > 0
        except asyncio.TimeoutError:
            logger.debug(f"Redis EXISTS timeout for key '{key}', using fallback")
            return False
        except Exception as e:
            logger.debug(f"Redis EXISTS error for key '{key}': {e}, using fallback")
            return False
    
    async def ttl(self, key: str) -> Optional[int]:
        """
        Get TTL of a key in seconds with strict timeout.
        
        Args:
            key: Redis key
            
        Returns:
            TTL in seconds, -1 if no TTL, None if key doesn't exist or Redis disabled
        """
        if not self._enabled:
            return None
        
        try:
            if self._connection_type == 'tcp':
                client = await self._get_tcp_client()
                if client is None:
                    return None
                result = await asyncio.wait_for(
                    client.ttl(key),
                    timeout=self.OPERATION_TIMEOUT
                )
                return result if result is not None else None
            else:  # REST API
                client = await self._get_rest_client()
                if client is None:
                    return None
                url = f"{self._rest_base_url}/ttl/{key}"
                response = await asyncio.wait_for(
                    client.get(url),
                    timeout=self.OPERATION_TIMEOUT
                )
                response.raise_for_status()
                data = response.json()
                result = data.get("result")
                if result is None:
                    return None
                return int(result)
        except asyncio.TimeoutError:
            logger.debug(f"Redis TTL timeout for key '{key}', using fallback")
            return None
        except Exception as e:
            logger.debug(f"Redis TTL error for key '{key}': {e}, using fallback")
            return None
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get JSON value from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            Parsed JSON as dict, or None if not found or invalid
        """
        value = await self.get(key)
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in Redis key '{key}'")
            return None
    
    async def set_json(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> bool:
        """
        Set JSON value in Redis.
        
        Args:
            key: Redis key
            value: Dict to serialize as JSON
            ttl_seconds: Optional TTL in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            json_str = json.dumps(value)
            return await self.set(key, json_str, ttl_seconds)
        except (TypeError, ValueError) as e:
            logger.warning(f"Error serializing JSON for key '{key}': {e}")
            return False
    
    async def set_nx(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        """
        Set value only if key does not exist (atomic operation for locks).
        
        Args:
            key: Redis key
            value: Value to set
            ttl_seconds: Optional TTL in seconds
            
        Returns:
            True if key was set (didn't exist), False if key already exists
        """
        if not self._enabled:
            return False
        
        try:
            if self._connection_type == 'tcp':
                client = await self._get_tcp_client()
                if client is None:
                    return False
                if ttl_seconds:
                    result = await asyncio.wait_for(
                        client.set(key, value, nx=True, ex=ttl_seconds),
                        timeout=self.OPERATION_TIMEOUT
                    )
                else:
                    result = await asyncio.wait_for(
                        client.set(key, value, nx=True),
                        timeout=self.OPERATION_TIMEOUT
                    )
                return result is True
            else:  # REST API
                client = await self._get_rest_client()
                if client is None:
                    return False
                url = f"{self._rest_base_url}/set/{key}"
                payload: Dict[str, Any] = {
                    "value": value,
                    "nx": True  # Only set if not exists
                }
                if ttl_seconds:
                    payload["ex"] = ttl_seconds
                
                response = await asyncio.wait_for(
                    client.post(url, json=payload),
                    timeout=self.OPERATION_TIMEOUT
                )
                response.raise_for_status()
                data = response.json()
                # Upstash returns "OK" if set, null if key already exists
                return data.get("result") == "OK"
        except asyncio.TimeoutError:
            logger.debug(f"Redis SET NX timeout for key '{key}' (>{self.OPERATION_TIMEOUT}s), using fallback")
            return False
        except Exception as e:
            logger.debug(f"Redis SET NX error for key '{key}': {e}, using fallback")
            return False
    
    async def close(self):
        """Close Redis clients."""
        if self._tcp_client:
            await self._tcp_client.aclose()
            self._tcp_client = None
        if self._rest_client:
            await self._rest_client.aclose()
            self._rest_client = None


# Global Redis client instance (Singleton)
redis_client = RedisClient()
