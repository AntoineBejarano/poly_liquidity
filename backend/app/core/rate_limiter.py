"""
Rate limiter with sliding windows for Polymarket API endpoints.

Implements comprehensive rate limiting based on Polymarket API documentation:
- General Rate Limiting: 5000 requests / 10s
- Data API: 200 requests / 10s
- CLOB API: Various limits per endpoint
- GAMMA API: Various limits per endpoint
- Trading endpoints: Burst and sustained limits

All rate limits use Cloudflare's throttling system with sliding time windows.
"""
import asyncio
import time
from typing import Dict, List, Optional
from collections import deque
from datetime import datetime, timedelta
from enum import Enum


class EndpointType(Enum):
    """Polymarket API endpoint types with their rate limits."""
    # General Rate Limits
    GENERAL = "general"  # 5000 req / 10s
    OK_ENDPOINT = "ok_endpoint"  # 50 req / 10s
    
    # Data API
    DATA_API = "data_api"  # 200 req / 10s
    DATA_API_ALTERNATIVE = "data_api_alternative"  # 1200 req / min (10-min block on violation)
    DATA_API_TRADES = "data_api_trades"  # 75 req / 10s
    DATA_API_OK = "data_api_ok"  # 10 req / 10s
    
    # GAMMA API
    GAMMA_GENERAL = "gamma_general"  # 750 req / 10s
    GAMMA_COMMENTS = "gamma_comments"  # 100 req / 10s
    GAMMA_EVENTS = "gamma_events"  # 100 req / 10s
    GAMMA_MARKETS = "gamma_markets"  # 125 req / 10s
    GAMMA_MARKETS_EVENTS_LISTING = "gamma_markets_events_listing"  # 100 req / 10s
    GAMMA_TAGS = "gamma_tags"  # 100 req / 10s
    GAMMA_SEARCH = "gamma_search"  # 300 req / 10s
    
    # CLOB General
    CLOB_GENERAL = "clob_general"  # 5000 req / 10s
    CLOB_BALANCE_ALLOWANCE_GET = "clob_balance_allowance_get"  # 125 req / 10s
    CLOB_BALANCE_ALLOWANCE_UPDATE = "clob_balance_allowance_update"  # 20 req / 10s
    
    # CLOB Market Data
    CLOB_BOOK = "clob_book"  # 200 req / 10s
    CLOB_BOOKS = "clob_books"  # 80 req / 10s
    CLOB_PRICE = "clob_price"  # 200 req / 10s
    CLOB_PRICES = "clob_prices"  # 80 req / 10s
    CLOB_MIDPRICE = "clob_midprice"  # 200 req / 10s
    CLOB_MIDPRICES = "clob_midprices"  # 80 req / 10s
    
    # CLOB Ledger
    CLOB_LEDGER = "clob_ledger"  # 300 req / 10s (trades/orders/notifications/order)
    CLOB_LEDGER_DATA_ORDERS = "clob_ledger_data_orders"  # 150 req / 10s
    CLOB_LEDGER_DATA_TRADES = "clob_ledger_data_trades"  # 150 req / 10s
    CLOB_NOTIFICATIONS = "clob_notifications"  # 125 req / 10s
    
    # CLOB Markets & Pricing
    CLOB_PRICE_HISTORY = "clob_price_history"  # 100 req / 10s
    CLOB_MARKETS = "clob_markets"  # 250 req / 10s
    CLOB_MARKET_TICK_SIZE = "clob_market_tick_size"  # 50 req / 10s
    CLOB_MARKETS_0X = "clob_markets_0x"  # 50 req / 10s
    CLOB_MARKETS_LISTING = "clob_markets_listing"  # 100 req / 10s
    
    # CLOB Authentication
    CLOB_API_KEYS = "clob_api_keys"  # 50 req / 10s
    
    # CLOB Trading Endpoints (Burst + Sustained)
    CLOB_POST_ORDER = "clob_post_order"  # 2400 req / 10s (burst), 24000 req / 10min (sustained)
    CLOB_DELETE_ORDER = "clob_delete_order"  # 2400 req / 10s (burst), 24000 req / 10min (sustained)
    CLOB_POST_ORDERS = "clob_post_orders"  # 800 req / 10s (burst), 12000 req / 10min (sustained)
    CLOB_DELETE_ORDERS = "clob_delete_orders"  # 800 req / 10s (burst), 12000 req / 10min (sustained)
    CLOB_DELETE_CANCEL_ALL = "clob_delete_cancel_all"  # 200 req / 10s (burst), 3000 req / 10min (sustained)
    CLOB_DELETE_CANCEL_MARKET_ORDERS = "clob_delete_cancel_market_orders"  # 800 req / 10s (burst), 12000 req / 10min (sustained)
    
    # Other APIs
    RELAYER_SUBMIT = "relayer_submit"  # 15 req / 1min
    USER_PNL_API = "user_pnl_api"  # 100 req / 10s
    
    # Legacy aliases for backward compatibility
    ALTERNATIVE_DATA_API = "alternative_data_api"  # Alias for DATA_API_ALTERNATIVE
    TRADING_ORDER = "trading_order"  # Alias for CLOB_POST_ORDER


class RateLimiter:
    """
    Rate limiter with sliding window per endpoint.
    
    Uses a sliding window algorithm to track requests within the time window.
    Thread-safe for async operations.
    """
    
    # Rate limit configurations per endpoint
    RATE_LIMITS: Dict[EndpointType, Dict[str, float]] = {
        # General Rate Limits
        EndpointType.GENERAL: {
            "max_requests": 5000,
            "window_seconds": 10.0,
        },
        EndpointType.OK_ENDPOINT: {
            "max_requests": 50,
            "window_seconds": 10.0,
        },
        
        # Data API
        EndpointType.DATA_API: {
            "max_requests": 200,
            "window_seconds": 10.0,
        },
        EndpointType.DATA_API_ALTERNATIVE: {
            "max_requests": 1200,
            "window_seconds": 60.0,
            "block_duration_seconds": 600.0,  # 10 minutes block on violation
        },
        EndpointType.ALTERNATIVE_DATA_API: {  # Legacy alias
            "max_requests": 1200,
            "window_seconds": 60.0,
            "block_duration_seconds": 600.0,
        },
        EndpointType.DATA_API_TRADES: {
            "max_requests": 75,
            "window_seconds": 10.0,
        },
        EndpointType.DATA_API_OK: {
            "max_requests": 10,
            "window_seconds": 10.0,
        },
        
        # GAMMA API
        EndpointType.GAMMA_GENERAL: {
            "max_requests": 750,
            "window_seconds": 10.0,
        },
        EndpointType.GAMMA_COMMENTS: {
            "max_requests": 100,
            "window_seconds": 10.0,
        },
        EndpointType.GAMMA_EVENTS: {
            "max_requests": 100,
            "window_seconds": 10.0,
        },
        EndpointType.GAMMA_MARKETS: {
            "max_requests": 125,
            "window_seconds": 10.0,
        },
        EndpointType.GAMMA_MARKETS_EVENTS_LISTING: {
            "max_requests": 100,
            "window_seconds": 10.0,
        },
        EndpointType.GAMMA_TAGS: {
            "max_requests": 100,
            "window_seconds": 10.0,
        },
        EndpointType.GAMMA_SEARCH: {
            "max_requests": 300,
            "window_seconds": 10.0,
        },
        
        # CLOB General
        EndpointType.CLOB_GENERAL: {
            "max_requests": 5000,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_BALANCE_ALLOWANCE_GET: {
            "max_requests": 125,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_BALANCE_ALLOWANCE_UPDATE: {
            "max_requests": 20,
            "window_seconds": 10.0,
        },
        
        # CLOB Market Data
        EndpointType.CLOB_BOOK: {
            "max_requests": 200,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_BOOKS: {
            "max_requests": 80,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_PRICE: {
            "max_requests": 200,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_PRICES: {
            "max_requests": 80,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_MIDPRICE: {
            "max_requests": 200,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_MIDPRICES: {
            "max_requests": 80,
            "window_seconds": 10.0,
        },
        
        # CLOB Ledger
        EndpointType.CLOB_LEDGER: {
            "max_requests": 300,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_LEDGER_DATA_ORDERS: {
            "max_requests": 150,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_LEDGER_DATA_TRADES: {
            "max_requests": 150,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_NOTIFICATIONS: {
            "max_requests": 125,
            "window_seconds": 10.0,
        },
        
        # CLOB Markets & Pricing
        EndpointType.CLOB_PRICE_HISTORY: {
            "max_requests": 100,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_MARKETS: {
            "max_requests": 250,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_MARKET_TICK_SIZE: {
            "max_requests": 50,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_MARKETS_0X: {
            "max_requests": 50,
            "window_seconds": 10.0,
        },
        EndpointType.CLOB_MARKETS_LISTING: {
            "max_requests": 100,
            "window_seconds": 10.0,
        },
        
        # CLOB Authentication
        EndpointType.CLOB_API_KEYS: {
            "max_requests": 50,
            "window_seconds": 10.0,
        },
        
        # CLOB Trading Endpoints (using burst limits for 10s window, sustained limits tracked separately)
        EndpointType.CLOB_POST_ORDER: {
            "max_requests": 2400,  # Burst: 2400 req / 10s
            "window_seconds": 10.0,
            "sustained_max_requests": 24000,  # Sustained: 24000 req / 10min
            "sustained_window_seconds": 600.0,  # 10 minutes
        },
        EndpointType.CLOB_DELETE_ORDER: {
            "max_requests": 2400,  # Burst: 2400 req / 10s
            "window_seconds": 10.0,
            "sustained_max_requests": 24000,  # Sustained: 24000 req / 10min
            "sustained_window_seconds": 600.0,
        },
        EndpointType.CLOB_POST_ORDERS: {
            "max_requests": 800,  # Burst: 800 req / 10s
            "window_seconds": 10.0,
            "sustained_max_requests": 12000,  # Sustained: 12000 req / 10min
            "sustained_window_seconds": 600.0,
        },
        EndpointType.CLOB_DELETE_ORDERS: {
            "max_requests": 800,  # Burst: 800 req / 10s
            "window_seconds": 10.0,
            "sustained_max_requests": 12000,  # Sustained: 12000 req / 10min
            "sustained_window_seconds": 600.0,
        },
        EndpointType.CLOB_DELETE_CANCEL_ALL: {
            "max_requests": 200,  # Burst: 200 req / 10s
            "window_seconds": 10.0,
            "sustained_max_requests": 3000,  # Sustained: 3000 req / 10min
            "sustained_window_seconds": 600.0,
        },
        EndpointType.CLOB_DELETE_CANCEL_MARKET_ORDERS: {
            "max_requests": 800,  # Burst: 800 req / 10s
            "window_seconds": 10.0,
            "sustained_max_requests": 12000,  # Sustained: 12000 req / 10min
            "sustained_window_seconds": 600.0,
        },
        EndpointType.TRADING_ORDER: {  # Legacy alias
            "max_requests": 2400,
            "window_seconds": 10.0,
            "sustained_max_requests": 24000,
            "sustained_window_seconds": 600.0,
        },
        
        # Other APIs
        EndpointType.RELAYER_SUBMIT: {
            "max_requests": 15,
            "window_seconds": 60.0,  # 1 minute
        },
        EndpointType.USER_PNL_API: {
            "max_requests": 100,
            "window_seconds": 10.0,
        },
    }
    
    def __init__(self):
        """Initialize rate limiter with sliding windows per endpoint."""
        # Sliding window: deque of timestamps for each endpoint (burst limits)
        self._windows: Dict[EndpointType, deque] = {
            endpoint: deque() for endpoint in EndpointType
        }
        # Sustained windows for endpoints with both burst and sustained limits
        self._sustained_windows: Dict[EndpointType, deque] = {}
        # Blocked endpoints (for Alternative Data API violations)
        self._blocked_until: Dict[EndpointType, float] = {}
        # Lock for thread-safety
        self._locks: Dict[EndpointType, asyncio.Lock] = {
            endpoint: asyncio.Lock() for endpoint in EndpointType
        }
        
        # Initialize sustained windows for endpoints that have sustained limits
        for endpoint, config in self.RATE_LIMITS.items():
            if "sustained_max_requests" in config:
                self._sustained_windows[endpoint] = deque()
    
    async def acquire(self, endpoint: EndpointType) -> bool:
        """
        Acquire permission to make a request.
        
        Checks both burst and sustained limits (if applicable).
        
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
            
            # Clean old timestamps outside the window (burst limit)
            now = time.time()
            window = self._windows[endpoint]
            
            # Remove timestamps outside the sliding window
            while window and (now - window[0]) > window_seconds:
                window.popleft()
            
            # Check burst limit
            if len(window) >= max_requests:
                return False
            
            # Check sustained limit if applicable
            if "sustained_max_requests" in config and endpoint in self._sustained_windows:
                sustained_max = config["sustained_max_requests"]
                sustained_window_seconds = config["sustained_window_seconds"]
                sustained_window = self._sustained_windows[endpoint]
                
                # Clean old timestamps outside the sustained window
                while sustained_window and (now - sustained_window[0]) > sustained_window_seconds:
                    sustained_window.popleft()
                
                # Check sustained limit
                if len(sustained_window) >= sustained_max:
                    return False
                
                # Add current timestamp to sustained window
                sustained_window.append(now)
            
            # Add current timestamp to burst window
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
        
        Returns the minimum of burst and sustained capacity (if applicable).
        
        Returns:
            Number of requests that can be made immediately.
        """
        config = self.RATE_LIMITS[endpoint]
        max_requests = config["max_requests"]
        window_seconds = config["window_seconds"]
        
        # Clean old timestamps (burst limit)
        now = time.time()
        window = self._windows[endpoint]
        
        while window and (now - window[0]) > window_seconds:
            window.popleft()
        
        burst_capacity = max(0, max_requests - len(window))
        
        # Check sustained limit if applicable
        if "sustained_max_requests" in config and endpoint in self._sustained_windows:
            sustained_max = config["sustained_max_requests"]
            sustained_window_seconds = config["sustained_window_seconds"]
            sustained_window = self._sustained_windows[endpoint]
            
            while sustained_window and (now - sustained_window[0]) > sustained_window_seconds:
                sustained_window.popleft()
            
            sustained_capacity = max(0, sustained_max - len(sustained_window))
            # Return minimum of both capacities
            return min(burst_capacity, sustained_capacity)
        
        return burst_capacity
    
    def get_estimated_wait_time(self, endpoint: EndpointType) -> float:
        """
        Estimate how long to wait before the next request can be made.
        
        Returns the maximum wait time needed for either burst or sustained limits.
        
        Returns:
            Estimated wait time in seconds. 0 if request can be made immediately.
        """
        config = self.RATE_LIMITS[endpoint]
        max_requests = config["max_requests"]
        window_seconds = config["window_seconds"]
        
        # Check if blocked
        if endpoint in self._blocked_until:
            return max(0, self._blocked_until[endpoint] - time.time())
        
        # Clean old timestamps (burst limit)
        now = time.time()
        window = self._windows[endpoint]
        
        while window and (now - window[0]) > window_seconds:
            window.popleft()
        
        burst_wait = 0.0
        if len(window) >= max_requests:
            oldest_timestamp = window[0]
            burst_wait = max(0.0, (oldest_timestamp + window_seconds) - now)
        
        # Check sustained limit if applicable
        sustained_wait = 0.0
        if "sustained_max_requests" in config and endpoint in self._sustained_windows:
            sustained_max = config["sustained_max_requests"]
            sustained_window_seconds = config["sustained_window_seconds"]
            sustained_window = self._sustained_windows[endpoint]
            
            while sustained_window and (now - sustained_window[0]) > sustained_window_seconds:
                sustained_window.popleft()
            
            if len(sustained_window) >= sustained_max:
                oldest_timestamp = sustained_window[0]
                sustained_wait = max(0.0, (oldest_timestamp + sustained_window_seconds) - now)
        
        # Return maximum wait time (whichever limit is more restrictive)
        return max(burst_wait, sustained_wait)


# Global rate limiter instance
rate_limiter = RateLimiter()


