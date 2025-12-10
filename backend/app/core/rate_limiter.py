"""
Rate limiter with sliding windows for Polymarket API endpoints.

Key constraints:
- Data API: max 200 req / 10s (primary bottleneck)
- Alternative Data API: 1200 req/min with 10-minute block on violation
- CLOB book/price/midprice: ~200 req / 10s per endpoint
- Trading POST /order: 2400 req / 10s (sufficient for burst execution)
"""
import asyncio
import time
from typing import Dict, List, Optional
from collections import deque
from datetime import datetime, timedelta
from enum import Enum


class EndpointType(Enum):
    """Polymarket API endpoint types with their rate limits."""
    DATA_API = "data_api"  # 200 req / 10s
    ALTERNATIVE_DATA_API = "alternative_data_api"  # 1200 req / min (10-min block on violation)
    CLOB_BOOK = "clob_book"  # ~200 req / 10s
    CLOB_PRICE = "clob_price"  # ~200 req / 10s
    CLOB_MIDPRICE = "clob_midprice"  # ~200 req / 10s
    TRADING_ORDER = "trading_order"  # 2400 req / 10s


class RateLimiter:
    """
    Rate limiter with sliding window per endpoint.
    
    Uses a sliding window algorithm to track requests within the time window.
    Thread-safe for async operations.
    """
    
    # Rate limit configurations per endpoint
    RATE_LIMITS: Dict[EndpointType, Dict[str, float]] = {
        EndpointType.DATA_API: {
            "max_requests": 200,
            "window_seconds": 10.0,
        },
        EndpointType.ALTERNATIVE_DATA_API: {
            "max_requests": 1200,
            "window_seconds": 60.0,
            "block_duration_seconds": 600.0,  # 10 minutes block on violation
        },
        EndpointType.CLOB_BOOK: {
            "max_requests": 200,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_PRICE: {
            "max_requests": 200,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_MIDPRICE: {
            "max_requests": 200,
            "window_seconds": 10.0,
        },
        EndpointType.TRADING_ORDER: {
            "max_requests": 2400,
            "window_seconds": 10.0,
        },
    }
    
    def __init__(self):
        """Initialize rate limiter with sliding windows per endpoint."""
        # Sliding window: deque of timestamps for each endpoint
        self._windows: Dict[EndpointType, deque] = {
            endpoint: deque() for endpoint in EndpointType
        }
        # Blocked endpoints (for Alternative Data API violations)
        self._blocked_until: Dict[EndpointType, float] = {}
        # Lock for thread-safety
        self._locks: Dict[EndpointType, asyncio.Lock] = {
            endpoint: asyncio.Lock() for endpoint in EndpointType
        }
    
    async def acquire(self, endpoint: EndpointType) -> bool:
        """
        Acquire permission to make a request.
        
        Returns:
            True if request is allowed, False if rate limit would be exceeded.
        
        Raises:
            RuntimeError: If endpoint is blocked (Alternative Data API violation).
        """
        async with self._locks[endpoint]:
            # Check if endpoint is blocked
            if endpoint in self._blocked_until:
                block_until = self._blocked_until[endpoint]
                if time.time() < block_until:
                    remaining = block_until - time.time()
                    raise RuntimeError(
                        f"Endpoint {endpoint.value} is blocked for {remaining:.1f} more seconds "
                        f"due to rate limit violation"
                    )
                else:
                    # Block expired, remove it
                    del self._blocked_until[endpoint]
            
            # Get rate limit config
            config = self.RATE_LIMITS[endpoint]
            max_requests = config["max_requests"]
            window_seconds = config["window_seconds"]
            
            # Clean old timestamps outside the window
            now = time.time()
            window = self._windows[endpoint]
            
            # Remove timestamps outside the sliding window
            while window and (now - window[0]) > window_seconds:
                window.popleft()
            
            # Check if we can make the request
            if len(window) >= max_requests:
                return False
            
            # Add current timestamp
            window.append(now)
            return True
    
    async def wait_for_capacity(self, endpoint: EndpointType, timeout: Optional[float] = None) -> bool:
        """
        Wait until capacity is available for a request.
        
        Args:
            endpoint: The endpoint type
            timeout: Maximum time to wait in seconds. None means wait indefinitely.
        
        Returns:
            True if capacity is available, False if timeout exceeded.
        
        Raises:
            RuntimeError: If endpoint is blocked.
        """
        start_time = time.time()
        
        while True:
            if timeout is not None and (time.time() - start_time) >= timeout:
                return False
            
            try:
                if await self.acquire(endpoint):
                    return True
            except RuntimeError:
                # Endpoint is blocked, re-raise
                raise
            
            # Wait a bit before checking again
            await asyncio.sleep(0.1)
    
    async def make_request(self, endpoint: EndpointType, timeout: Optional[float] = None) -> bool:
        """
        Make a request with rate limiting.
        
        This is a convenience method that waits for capacity and then records the request.
        Use this when you want to ensure the request is made within rate limits.
        
        Args:
            endpoint: The endpoint type
            timeout: Maximum time to wait for capacity. None means wait indefinitely.
        
        Returns:
            True if request was made, False if timeout exceeded.
        
        Raises:
            RuntimeError: If endpoint is blocked.
        """
        if await self.wait_for_capacity(endpoint, timeout):
            # Request is already recorded in acquire()
            return True
        return False
    
    def _check_violation(self, endpoint: EndpointType):
        """
        Check if rate limit was violated and apply block if needed.
        
        This should be called when a 429 (Too Many Requests) or similar error is received.
        """
        config = self.RATE_LIMITS[endpoint]
        if "block_duration_seconds" in config:
            # Block the endpoint
            block_duration = config["block_duration_seconds"]
            self._blocked_until[endpoint] = time.time() + block_duration
    
    async def record_violation(self, endpoint: EndpointType):
        """
        Record a rate limit violation (e.g., received 429 response).
        
        For Alternative Data API, this will block the endpoint for 10 minutes.
        """
        async with self._locks[endpoint]:
            self._check_violation(endpoint)
    
    def get_available_capacity(self, endpoint: EndpointType) -> int:
        """
        Get the number of available requests in the current window.
        
        Returns:
            Number of requests that can be made immediately.
        """
        config = self.RATE_LIMITS[endpoint]
        max_requests = config["max_requests"]
        window_seconds = config["window_seconds"]
        
        # Clean old timestamps
        now = time.time()
        window = self._windows[endpoint]
        
        while window and (now - window[0]) > window_seconds:
            window.popleft()
        
        return max(0, max_requests - len(window))
    
    def get_estimated_wait_time(self, endpoint: EndpointType) -> float:
        """
        Estimate how long to wait before the next request can be made.
        
        Returns:
            Estimated wait time in seconds. 0 if request can be made immediately.
        """
        config = self.RATE_LIMITS[endpoint]
        max_requests = config["max_requests"]
        window_seconds = config["window_seconds"]
        
        # Check if blocked
        if endpoint in self._blocked_until:
            return max(0, self._blocked_until[endpoint] - time.time())
        
        # Clean old timestamps
        now = time.time()
        window = self._windows[endpoint]
        
        while window and (now - window[0]) > window_seconds:
            window.popleft()
        
        if len(window) < max_requests:
            return 0.0
        
        # Need to wait until oldest request expires
        oldest_timestamp = window[0]
        wait_time = (oldest_timestamp + window_seconds) - now
        return max(0.0, wait_time)


# Global rate limiter instance
rate_limiter = RateLimiter()


