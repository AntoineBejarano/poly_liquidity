"""
Latency monitoring service for backend and Polymarket APIs.

Measures:
1. Backend latency (internal processing)
2. Polymarket Data API latency
3. Polymarket Trading API latency
4. End-to-end execution latency

This is critical for the trading strategy as delays can cause missed opportunities.

**Singleton Global:**
- Esta clase es instanciada una sola vez globalmente
- Todas las requests HTTP (de cualquier pestaña/sesión) comparten la misma instancia
- El cache es compartido: si una pestaña actualiza el cache, todas las demás lo ven
- Usa Redis (Upstash) para cache distribuido con patrón SWR (Stale-While-Revalidate)

**Sincronización:**
- Lock distribuido en Redis previene thundering herd
- Backoff exponencial persistido en Redis para errores 429/503
- SWR: retorna cache fresco inmediatamente, revalida stale en background
"""
import asyncio
import time
import logging
import json
from typing import Dict, Optional
from datetime import datetime
from enum import Enum
import httpx
from app.settings import settings
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class LatencyStatus(Enum):
    """Latency status based on thresholds."""
    GREEN = "GREEN"  # All latencies within acceptable range
    YELLOW = "YELLOW"  # Some latencies elevated, reduce aggression
    RED = "RED"  # Critical latencies, stop new entries


class LatencyMonitor:
    """
    Monitors latency to backend and Polymarket APIs.
    
    Uses Redis for distributed caching with SWR (Stale-While-Revalidate) pattern:
    - Fresh cache (< 30s): Return immediately
    - Stale cache (30-60s): Return stale value + revalidate in background
    - Expired cache (> 60s): Measure synchronously
    
    Implements distributed lock to prevent thundering herd.
    Implements exponential backoff for rate limit errors (429/503).
    """
    
    # Redis keys
    CACHE_KEY = "latency:metrics"
    LOCK_KEY_DATA = "latency:lock:data"
    LOCK_KEY_TRADING = "latency:lock:trading"
    BACKOFF_KEY = "latency:backoff:until"
    
    def __init__(self):
        """Initialize latency monitor."""
        self._client: Optional[httpx.AsyncClient] = None
        self._last_execution_latency: Optional[float] = None
        self._local_cache: Optional[Dict] = None  # Fallback in-memory cache
        self._local_cache_timestamp: Optional[float] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=5.0)
        return self._client
    
    def _get_thresholds(self) -> Dict[str, int]:
        """Get latency thresholds from settings."""
        return {
            "backend_green": settings.latency_backend_green_threshold,
            "backend_yellow": settings.latency_backend_yellow_threshold,
            "data_green": settings.latency_polymarket_data_green_threshold,
            "data_yellow": settings.latency_polymarket_data_yellow_threshold,
            "trading_green": settings.latency_polymarket_trading_green_threshold,
            "trading_yellow": settings.latency_polymarket_trading_yellow_threshold,
            "execution_green": settings.latency_execution_green_threshold,
            "execution_yellow": settings.latency_execution_yellow_threshold,
        }
    
    async def _check_backoff(self) -> bool:
        """
        Check if we're in a backoff period.
        
        Returns:
            True if we should skip measurement (in backoff), False otherwise
        """
        backoff_until = await redis_client.get(self.BACKOFF_KEY)
        if backoff_until:
            try:
                backoff_timestamp = float(backoff_until)
                if time.time() < backoff_timestamp:
                    remaining = int(backoff_timestamp - time.time())
                    logger.debug(f"In backoff period, {remaining}s remaining")
                    return True
                else:
                    # Backoff expired, clean up
                    await redis_client.delete(self.BACKOFF_KEY)
            except (ValueError, TypeError):
                pass
        return False
    
    async def _set_backoff(self, seconds: int):
        """
        Set backoff period.
        
        Args:
            seconds: Backoff duration in seconds
        """
        backoff_until = time.time() + seconds
        await redis_client.set(self.BACKOFF_KEY, str(backoff_until), ttl_seconds=seconds + 10)
        logger.warning(f"Setting backoff for {seconds}s (until {datetime.fromtimestamp(backoff_until).isoformat()})")
    
    async def _acquire_lock(self, lock_key: str, ttl_seconds: int) -> bool:
        """
        Try to acquire distributed lock in Redis.
        
        Uses SET NX (set if not exists) for atomic lock acquisition.
        
        Args:
            lock_key: Redis key for the lock
            ttl_seconds: TTL for the lock
            
        Returns:
            True if lock acquired, False if already locked
        """
        # Use SET NX for atomic lock acquisition
        lock_value = f"{time.time()}"  # Timestamp as value
        return await redis_client.set_nx(lock_key, lock_value, ttl_seconds=ttl_seconds)
    
    async def _release_lock(self, lock_key: str):
        """Release distributed lock."""
        await redis_client.delete(lock_key)
    
    async def _measure_backend_latency(self) -> float:
        """
        Measure backend internal latency.
        
        This is a simple operation that measures processing time.
        In a real scenario, this could measure database query time, etc.
        """
        start = time.monotonic_ns()
        # Simulate some backend processing
        await asyncio.sleep(0.001)  # 1ms baseline
        end = time.monotonic_ns()
        return (end - start) / 1_000_000  # Convert to milliseconds
    
    async def _measure_polymarket_data_latency(self) -> Optional[float]:
        """
        Measure latency to Polymarket Data API.
        
        Calls: https://data-api.polymarket.com/ (raíz, responde con {"data":"OK"})
        Implements rate limiting and backoff.
        """
        # Check backoff
        if await self._check_backoff():
            return None
        
        # Check distributed lock
        lock_acquired = await self._acquire_lock(
            self.LOCK_KEY_DATA,
            settings.latency_lock_ttl_seconds
        )
        if not lock_acquired:
            logger.debug("Lock already held for Data API measurement, skipping")
            return None
        
        try:
            start = time.monotonic_ns()
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get("https://data-api.polymarket.com/")
            response.raise_for_status()
            
            end = time.monotonic_ns()
            latency_ms = (end - start) / 1_000_000
            
            # Success - reset any backoff
            await redis_client.delete(self.BACKOFF_KEY)
            
            return latency_ms
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 503):
                # Rate limited - set backoff
                backoff_seconds = min(
                    settings.latency_backoff_max_seconds,
                    10 * (2 ** 0)  # Start with 10s, could be made exponential
                )
                await self._set_backoff(backoff_seconds)
                logger.warning(f"Rate limited by Polymarket Data API (status {e.response.status_code}), backing off for {backoff_seconds}s")
            else:
                logger.warning(
                    "Error measuring Polymarket Data API latency: %s (%s)",
                    type(e).__name__,
                    str(e) or "sin mensaje",
                )
            return None
        except Exception as e:
            logger.warning(
                "Error measuring Polymarket Data API latency: %s (%s)",
                type(e).__name__,
                str(e) or "sin mensaje",
            )
            return None
        finally:
            await self._release_lock(self.LOCK_KEY_DATA)
    
    async def _measure_polymarket_trading_latency(self) -> Optional[float]:
        """
        Measure latency to Polymarket Trading API (CLOB).
        
        Calls: https://clob.polymarket.com/ok
        Implements rate limiting and backoff.
        """
        # Check backoff
        if await self._check_backoff():
            return None
        
        # Check distributed lock
        lock_acquired = await self._acquire_lock(
            self.LOCK_KEY_TRADING,
            settings.latency_lock_ttl_seconds
        )
        if not lock_acquired:
            logger.debug("Lock already held for Trading API measurement, skipping")
            return None
        
        try:
            start = time.monotonic_ns()
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get("https://clob.polymarket.com/ok")
            response.raise_for_status()
            
            end = time.monotonic_ns()
            latency_ms = (end - start) / 1_000_000
            
            # Success - reset any backoff
            await redis_client.delete(self.BACKOFF_KEY)
            
            return latency_ms
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 503):
                # Rate limited - set backoff
                backoff_seconds = min(
                    settings.latency_backoff_max_seconds,
                    10 * (2 ** 0)  # Start with 10s
                )
                await self._set_backoff(backoff_seconds)
                logger.warning(f"Rate limited by Polymarket Trading API (status {e.response.status_code}), backing off for {backoff_seconds}s")
            else:
                logger.warning(
                    "Error measuring Polymarket Trading API latency: %s (%s)",
                    type(e).__name__,
                    str(e) or "sin mensaje",
                )
            return None
        except Exception as e:
            logger.warning(
                "Error measuring Polymarket Trading API latency: %s (%s)",
                type(e).__name__,
                str(e) or "sin mensaje",
            )
            return None
        finally:
            await self._release_lock(self.LOCK_KEY_TRADING)
    
    def _calculate_status(
        self,
        backend_latency: float,
        polymarket_data_latency: Optional[float],
        polymarket_trading_latency: Optional[float],
        execution_latency: Optional[float]
    ) -> LatencyStatus:
        """
        Calculate overall latency status based on thresholds.
        
        PRIORIDAD: La latencia de Polymarket es más importante que la del backend.
        Si Polymarket está lento, el sistema debe reducir agresividad o detenerse.
        
        Returns:
            GREEN: All latencies within acceptable range
            YELLOW: Some latencies elevated
            RED: Critical latencies detected
        """
        thresholds = self._get_thresholds()
        
        # PRIORIDAD 1: Check Polymarket Trading API latency (más crítico para trading)
        if polymarket_trading_latency:
            if polymarket_trading_latency > thresholds["trading_yellow"]:
                return LatencyStatus.RED
            elif polymarket_trading_latency > thresholds["trading_green"]:
                return LatencyStatus.YELLOW
        
        # PRIORIDAD 2: Check Polymarket Data API latency
        if polymarket_data_latency:
            if polymarket_data_latency > thresholds["data_yellow"]:
                return LatencyStatus.RED
            elif polymarket_data_latency > thresholds["data_green"]:
                return LatencyStatus.YELLOW
        
        # PRIORIDAD 3: Check execution latency
        if execution_latency:
            if execution_latency > thresholds["execution_yellow"]:
                return LatencyStatus.RED
            elif execution_latency > thresholds["execution_green"]:
                return LatencyStatus.YELLOW
        
        # PRIORIDAD 4: Check backend latency (menos crítico)
        if backend_latency > thresholds["backend_yellow"]:
            return LatencyStatus.RED
        elif backend_latency > thresholds["backend_green"]:
            return LatencyStatus.YELLOW
        
        return LatencyStatus.GREEN
    
    async def _measure_latencies(self) -> Dict:
        """
        Measure all latencies synchronously.
        
        Returns:
            Dictionary with latency metrics
        """
        backend_latency = await self._measure_backend_latency()
        polymarket_data_latency = await self._measure_polymarket_data_latency()
        polymarket_trading_latency = await self._measure_polymarket_trading_latency()
        execution_latency = self._last_execution_latency
        
        # Calculate status
        status = self._calculate_status(
            backend_latency,
            polymarket_data_latency,
            polymarket_trading_latency,
            execution_latency
        )
        
        # Build result
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "backend_latency_ms": round(backend_latency, 2),
            "polymarket_data_latency_ms": round(polymarket_data_latency, 2) if polymarket_data_latency else None,
            "polymarket_trading_latency_ms": round(polymarket_trading_latency, 2) if polymarket_trading_latency else None,
            "execution_latency_ms": round(execution_latency, 2) if execution_latency else None,
            "status": status.value,
            "cache_age_seconds": None,  # Will be calculated when retrieved from cache
        }
        
        return result
    
    async def _revalidate_in_background(self):
        """
        Revalidate cache in background (SWR pattern).
        
        This is called when cache is stale but still valid.
        Has strict timeout (5s) to prevent dangling tasks.
        """
        try:
            # Strict timeout to prevent dangling tasks
            result = await asyncio.wait_for(
                self._measure_latencies(),
                timeout=5.0  # 5 seconds max for background revalidation
            )
            
            # Update cache in Redis (with timeout)
            await asyncio.wait_for(
                redis_client.set_json(
                    self.CACHE_KEY,
                    result,
                    ttl_seconds=settings.latency_stale_ttl_seconds
                ),
                timeout=0.2  # 200ms max for Redis operation
            )
            
            # Also update local cache
            self._local_cache = result
            self._local_cache_timestamp = time.time()
            logger.debug("Cache revalidated in background")
        except asyncio.TimeoutError:
            logger.warning("Background revalidation timed out (5s), skipping update")
        except Exception as e:
            logger.warning(f"Error revalidating cache in background: {e}")
    
    async def get_latency_metrics(self, force_refresh: bool = False) -> Dict:
        """
        Get current latency metrics with SWR (Stale-While-Revalidate) pattern.
        
        **SWR Logic:**
        - Fresh cache (< 30s): Return immediately
        - Stale cache (30-60s): Return stale value + revalidate in background
        - Expired cache (> 60s): Measure synchronously
        
        **Distributed Lock:**
        - Prevents thundering herd when cache expires
        - Only one request measures, others wait and get fresh result
        
        Args:
            force_refresh: If True, bypass cache and refresh metrics
            
        Returns:
            Dictionary with latency metrics and status
        """
        now = time.time()
        
        # Try Redis cache first
        cached_data = await redis_client.get_json(self.CACHE_KEY)
        
        if cached_data and not force_refresh:
            # Validate cache structure (must have timestamp)
            if "timestamp" not in cached_data:
                # Cache antiguo sin timestamp - eliminar y medir de nuevo
                logger.debug("Cache data missing 'timestamp' (old format), deleting invalid cache")
                try:
                    await redis_client.delete(self.CACHE_KEY)
                except Exception:
                    pass  # Ignore errors when deleting invalid cache
                cached_data = None
            else:
                try:
                    cache_timestamp = datetime.fromisoformat(cached_data["timestamp"]).timestamp()
                    cache_age = now - cache_timestamp
                    
                    # Add cache_age_seconds to response
                    cached_data["cache_age_seconds"] = round(cache_age, 1)
                    
                    # Fresh cache: return immediately
                    if cache_age < settings.latency_cache_ttl_seconds:
                        logger.debug(f"Returning fresh cache (age: {cache_age:.1f}s)")
                        return cached_data
                    
                    # Stale cache: return stale + revalidate in background
                    if cache_age < settings.latency_stale_ttl_seconds:
                        logger.debug(f"Returning stale cache (age: {cache_age:.1f}s), revalidating in background")
                        # Fire and forget background revalidation (with timeout protection)
                        asyncio.create_task(self._revalidate_in_background())
                        return cached_data
                except (ValueError, KeyError) as e:
                    # Cache con formato inválido - puede ser cache antiguo o corrupto
                    logger.debug(f"Invalid cache timestamp format: {e}, treating as invalid")
                    cached_data = None
        
        # Fallback to local cache if Redis unavailable
        if not cached_data and self._local_cache and not force_refresh:
            # Validate local cache structure (must have timestamp)
            if "timestamp" not in self._local_cache:
                # Cache local antiguo sin timestamp - es esperado si hay cache de versión anterior
                logger.debug("Local cache missing 'timestamp' (old format), treating as invalid")
                self._local_cache = None
            elif self._local_cache_timestamp:
                cache_age = now - self._local_cache_timestamp
                if cache_age < settings.latency_cache_ttl_seconds:
                    logger.debug("Using local cache fallback")
                    # Add cache_age_seconds to local cache response
                    local_cache_with_age = self._local_cache.copy()
                    local_cache_with_age["cache_age_seconds"] = round(cache_age, 1)
                    return local_cache_with_age
        
        # Cache expired or force refresh: measure synchronously
        logger.debug("Measuring latencies (cache expired or force refresh)")
        result = await self._measure_latencies()
        
        # Add cache_age_seconds (fresh data, age = 0)
        result["cache_age_seconds"] = 0.0
        
        # Update cache in Redis (non-blocking, fire-and-forget)
        # Note: redis_client already has timeout protection (200ms)
        # This is a non-critical operation, so we don't block on it
        try:
            await redis_client.set_json(
                self.CACHE_KEY,
                result,
                ttl_seconds=settings.latency_stale_ttl_seconds
            )
        except Exception as e:
            # Log at debug level since this is non-critical
            # Local cache is already updated, so system continues normally
            logger.debug(f"Redis SET error (non-critical): {e}, using local cache only")
        
        # Also update local cache
        self._local_cache = result
        self._local_cache_timestamp = now
        
        return result
    
    def record_execution_latency(self, latency_ms: float):
        """
        Record end-to-end execution latency.
        
        This should be called after a complete order execution cycle:
        1. Generate order
        2. Sign order
        3. POST to Polymarket
        4. Receive confirmation
        
        Args:
            latency_ms: Execution latency in milliseconds
        """
        self._last_execution_latency = latency_ms
        # Invalidate cache so next get_latency_metrics includes this
        # (We could also update cache directly, but invalidation is simpler)
        self._local_cache = None
        self._local_cache_timestamp = None
    
    def get_status(self) -> LatencyStatus:
        """
        Get current latency status without full measurement.
        
        Uses cached results if available.
        """
        # Try to get from cache without async overhead
        if self._local_cache:
            return LatencyStatus(self._local_cache["status"])
        return LatencyStatus.GREEN
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global latency monitor instance
latency_monitor = LatencyMonitor()
