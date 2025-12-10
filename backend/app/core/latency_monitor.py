"""
Latency monitoring service for backend and Polymarket APIs.

Measures:
1. Backend latency (internal processing)
2. Polymarket Data API latency
3. Polymarket Trading API latency
4. End-to-end execution latency

This is critical for the trading strategy as delays can cause missed opportunities.
"""
import asyncio
import time
from typing import Dict, Optional
from datetime import datetime
from enum import Enum
import httpx
from app.settings import settings


class LatencyStatus(Enum):
    """Latency status based on thresholds."""
    GREEN = "GREEN"  # All latencies within acceptable range
    YELLOW = "YELLOW"  # Some latencies elevated, reduce aggression
    RED = "RED"  # Critical latencies, stop new entries


class LatencyMonitor:
    """
    Monitors latency to backend and Polymarket APIs.
    
    Caches results to avoid hitting Polymarket too frequently.
    Updates every 5-10 seconds.
    """
    
    # Latency thresholds in milliseconds
    BACKEND_GREEN_THRESHOLD = 100  # ms
    BACKEND_YELLOW_THRESHOLD = 200  # ms
    
    POLYMARKET_DATA_GREEN_THRESHOLD = 150  # ms
    POLYMARKET_DATA_YELLOW_THRESHOLD = 300  # ms
    
    POLYMARKET_TRADING_GREEN_THRESHOLD = 150  # ms
    POLYMARKET_TRADING_YELLOW_THRESHOLD = 300  # ms
    
    EXECUTION_GREEN_THRESHOLD = 250  # ms
    EXECUTION_YELLOW_THRESHOLD = 500  # ms
    
    CACHE_TTL_SECONDS = 5  # Cache results for 5 seconds
    
    def __init__(self):
        """Initialize latency monitor."""
        self._client: Optional[httpx.AsyncClient] = None
        self._cached_results: Optional[Dict] = None
        self._cache_timestamp: Optional[float] = None
        self._last_execution_latency: Optional[float] = None
        self._lock = asyncio.Lock()
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=5.0)
        return self._client
    
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
        
        Calls: https://data-api.polymarket.com/ok
        """
        try:
            client = await self._get_client()
            start = time.monotonic_ns()
            
            # TODO: Replace with actual Polymarket Data API health endpoint
            # For now, we'll use a placeholder
            # response = await client.get("https://data-api.polymarket.com/ok", timeout=3.0)
            # response.raise_for_status()
            
            # Placeholder: simulate API call
            await asyncio.sleep(0.1)  # Simulate network latency
            
            end = time.monotonic_ns()
            return (end - start) / 1_000_000  # Convert to milliseconds
        except Exception as e:
            print(f"Error measuring Polymarket Data API latency: {e}")
            return None
    
    async def _measure_polymarket_trading_latency(self) -> Optional[float]:
        """
        Measure latency to Polymarket Trading API (CLOB).
        
        Calls: https://clob.polymarket.com/ok
        """
        try:
            client = await self._get_client()
            start = time.monotonic_ns()
            
            # TODO: Replace with actual Polymarket CLOB health endpoint
            # For now, we'll use a placeholder
            # response = await client.get("https://clob.polymarket.com/ok", timeout=3.0)
            # response.raise_for_status()
            
            # Placeholder: simulate API call
            await asyncio.sleep(0.1)  # Simulate network latency
            
            end = time.monotonic_ns()
            return (end - start) / 1_000_000  # Convert to milliseconds
        except Exception as e:
            print(f"Error measuring Polymarket Trading API latency: {e}")
            return None
    
    def _calculate_status(
        self,
        backend_latency: float,
        polymarket_data_latency: Optional[float],
        polymarket_trading_latency: Optional[float],
        execution_latency: Optional[float]
    ) -> LatencyStatus:
        """
        Calculate overall latency status based on thresholds.
        
        Returns:
            GREEN: All latencies within acceptable range
            YELLOW: Some latencies elevated
            RED: Critical latencies detected
        """
        # Check backend latency
        if backend_latency > self.BACKEND_YELLOW_THRESHOLD:
            return LatencyStatus.RED
        elif backend_latency > self.BACKEND_GREEN_THRESHOLD:
            return LatencyStatus.YELLOW
        
        # Check Polymarket Data API latency
        if polymarket_data_latency:
            if polymarket_data_latency > self.POLYMARKET_DATA_YELLOW_THRESHOLD:
                return LatencyStatus.RED
            elif polymarket_data_latency > self.POLYMARKET_DATA_GREEN_THRESHOLD:
                return LatencyStatus.YELLOW
        
        # Check Polymarket Trading API latency
        if polymarket_trading_latency:
            if polymarket_trading_latency > self.POLYMARKET_TRADING_YELLOW_THRESHOLD:
                return LatencyStatus.RED
            elif polymarket_trading_latency > self.POLYMARKET_TRADING_GREEN_THRESHOLD:
                return LatencyStatus.YELLOW
        
        # Check execution latency
        if execution_latency:
            if execution_latency > self.EXECUTION_YELLOW_THRESHOLD:
                return LatencyStatus.RED
            elif execution_latency > self.EXECUTION_GREEN_THRESHOLD:
                return LatencyStatus.YELLOW
        
        return LatencyStatus.GREEN
    
    async def get_latency_metrics(self, force_refresh: bool = False) -> Dict:
        """
        Get current latency metrics.
        
        Caches results for CACHE_TTL_SECONDS to avoid hitting APIs too frequently.
        
        Args:
            force_refresh: If True, bypass cache and refresh metrics
        
        Returns:
            Dictionary with latency metrics and status
        """
        async with self._lock:
            now = time.time()
            
            # Check cache
            if not force_refresh and self._cached_results and self._cache_timestamp:
                age = now - self._cache_timestamp
                if age < self.CACHE_TTL_SECONDS:
                    return self._cached_results
            
            # Measure all latencies
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
            }
            
            # Cache result
            self._cached_results = result
            self._cache_timestamp = now
            
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
    
    def get_status(self) -> LatencyStatus:
        """
        Get current latency status without full measurement.
        
        Uses cached results if available.
        """
        if self._cached_results:
            return LatencyStatus(self._cached_results["status"])
        return LatencyStatus.GREEN
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global latency monitor instance
latency_monitor = LatencyMonitor()


