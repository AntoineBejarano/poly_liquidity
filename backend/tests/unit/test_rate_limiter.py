"""
Unit tests for Rate Limiter.

Según especificación en docs/services/rate_limiter.md
"""
import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
from app.core.rate_limiter import RateLimiter, EndpointType


class TestRateLimiter:
    """Test cases for Rate Limiter."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Fixture para RateLimiter."""
        return RateLimiter()
    
    @pytest.mark.asyncio
    async def test_acquire_allows_request(self, rate_limiter):
        """Test acquire allows request when under limit."""
        result = await rate_limiter.acquire(EndpointType.DATA_API)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_acquire_blocks_when_limit_exceeded(self, rate_limiter):
        """Test acquire blocks when rate limit exceeded."""
        # Make 200 requests (the limit for DATA_API)
        for _ in range(200):
            await rate_limiter.acquire(EndpointType.DATA_API)
        
        # Next request should be blocked
        result = await rate_limiter.acquire(EndpointType.DATA_API)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_wait_for_capacity_waits_when_blocked(self, rate_limiter):
        """Test wait_for_capacity waits when capacity is not available."""
        # Fill up the window
        for _ in range(200):
            await rate_limiter.acquire(EndpointType.DATA_API)
        
        # wait_for_capacity should return False immediately if timeout is 0
        result = await rate_limiter.wait_for_capacity(EndpointType.DATA_API, timeout=0.0)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_wait_for_capacity_returns_true_when_available(self, rate_limiter):
        """Test wait_for_capacity returns True when capacity becomes available."""
        # Fill up the window
        for _ in range(200):
            await rate_limiter.acquire(EndpointType.DATA_API)
        
        # Wait a bit for window to slide
        with patch("time.time", return_value=time.time() + 11):  # Move past window
            result = await rate_limiter.wait_for_capacity(EndpointType.DATA_API, timeout=1.0)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_record_violation_blocks_alternative_api(self, rate_limiter):
        """Test record_violation blocks Alternative Data API for 10 minutes."""
        await rate_limiter.record_violation(EndpointType.ALTERNATIVE_DATA_API)
        
        # Should raise RuntimeError when trying to acquire
        with pytest.raises(RuntimeError, match="is blocked"):
            await rate_limiter.acquire(EndpointType.ALTERNATIVE_DATA_API)
    
    @pytest.mark.asyncio
    async def test_sliding_window_removes_old_requests(self, rate_limiter):
        """Test sliding window removes old requests."""
        # Make requests
        for _ in range(100):
            await rate_limiter.acquire(EndpointType.DATA_API)
        
        # Move time forward past window
        with patch("time.time", return_value=time.time() + 11):
            # Should be able to make more requests
            result = await rate_limiter.acquire(EndpointType.DATA_API)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_different_endpoints_independent(self, rate_limiter):
        """Test different endpoints have independent rate limits."""
        # Fill DATA_API
        for _ in range(200):
            await rate_limiter.acquire(EndpointType.DATA_API)
        
        # TRADING_ORDER should still have capacity
        result = await rate_limiter.acquire(EndpointType.TRADING_ORDER)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_acquire_tracks_requests_in_window(self, rate_limiter):
        """Test acquire tracks requests in sliding window."""
        # Make some requests
        for _ in range(50):
            await rate_limiter.acquire(EndpointType.DATA_API)
        
        # Window should have 50 requests
        window = rate_limiter._windows[EndpointType.DATA_API]
        assert len(window) == 50
    
    @pytest.mark.asyncio
    async def test_acquire_window_full_when_at_limit(self, rate_limiter):
        """Test window is full when at limit."""
        # Fill up
        for _ in range(200):
            await rate_limiter.acquire(EndpointType.DATA_API)
        
        # Window should have 200 requests
        window = rate_limiter._windows[EndpointType.DATA_API]
        assert len(window) == 200

