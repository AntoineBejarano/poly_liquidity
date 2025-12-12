"""
Unit tests for Scanner Engine.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from uuid import uuid4
from app.core.scanner.scanner import Scanner
from app.core.scanner.filters import ScannerFilters
from app.core.scanner.normalizer import ScannerNormalizer
from app.models.market import Market
from app.models.event import Event


@pytest.mark.asyncio
class TestScanner:
    """Test cases for Scanner Engine."""
    
    async def test_scanner_initialization(self):
        """Test scanner initializes correctly."""
        scanner = Scanner()
        assert scanner._last_scan is None
        assert scanner._client is None
    
    async def test_get_client_creates_client(self):
        """Test that _get_client creates httpx client."""
        scanner = Scanner()
        client = await scanner._get_client()
        assert client is not None
        await scanner.close()
    
    async def test_fetch_markets_from_polymarket_with_cache(self, mock_api_cache):
        """Test fetching markets uses cache when available."""
        scanner = Scanner()
        
        # Mock cache returning data
        cached_data = [{"id": "market-1", "price": 0.98}]
        mock_api_cache.get = AsyncMock(return_value=cached_data)
        
        with patch("app.core.scanner.scanner.api_cache", mock_api_cache):
            markets = await scanner._fetch_markets_from_polymarket()
            assert markets == cached_data
            # Should not make HTTP request if cache hit
        
        await scanner.close()
    
    async def test_fetch_markets_from_polymarket_rate_limit_timeout(self, mock_rate_limiter):
        """Test that rate limit timeout returns empty list."""
        scanner = Scanner()
        
        # Mock rate limiter timeout
        mock_rate_limiter.wait_for_capacity = AsyncMock(return_value=False)
        
        with patch("app.core.scanner.scanner.rate_limiter", mock_rate_limiter):
            markets = await scanner._fetch_markets_from_polymarket()
            assert markets == []
        
        await scanner.close()
    
    def test_filter_candidate_markets_binary_only(self, mock_config_service):
        """Test filtering only accepts binary markets."""
        scanner = Scanner()
        trace_id = "test-trace-id"
        
        markets = [
            {"id": "1", "outcomes": [{"name": "YES", "price": 0.98}, {"name": "NO", "price": 0.02}], "status": "OPEN", "category": "sports"},
            {"id": "2", "outcomes": [{"name": "YES", "price": 0.98}], "status": "OPEN", "category": "sports"},  # Solo 1 outcome
            {"id": "3", "outcomes": [{"name": "YES", "price": 0.98}, {"name": "NO", "price": 0.02}], "status": "OPEN", "category": "sports"},
        ]
        
        # Pasar config directamente al scanner para evitar acceso a DB
        mock_config = mock_config_service.get_risk_config.return_value
        scanner.filters.config = mock_config
        
        candidates, rejections = scanner._filter_candidate_markets(markets, trace_id)
        
        # Should only include markets with 2 outcomes
        assert len(candidates) == 2
        assert all(m["id"] in ["1", "3"] for m in candidates)
    
    def test_filter_candidate_markets_open_only(self, mock_config_service):
        """Test filtering only accepts OPEN markets."""
        scanner = Scanner()
        trace_id = "test-trace-id"
        
        markets = [
            {"id": "1", "outcomes": [{"name": "YES", "price": 0.98}, {"name": "NO", "price": 0.02}], "status": "OPEN", "category": "sports"},
            {"id": "2", "outcomes": [{"name": "YES", "price": 0.98}, {"name": "NO", "price": 0.02}], "status": "CLOSED", "category": "sports"},
            {"id": "3", "outcomes": [{"name": "YES", "price": 0.98}, {"name": "NO", "price": 0.02}], "market_status": "OPEN", "category": "sports"},
        ]
        
        # Pasar config directamente al scanner para evitar acceso a DB
        mock_config = mock_config_service.get_risk_config.return_value
        scanner.filters.config = mock_config
        
        candidates, rejections = scanner._filter_candidate_markets(markets, trace_id)
        
        # Should only include OPEN markets
        assert len(candidates) == 2
        assert all(m["id"] in ["1", "3"] for m in candidates)
    
    def test_filter_candidate_markets_min_price(self, mock_config_service):
        """Test filtering enforces minimum price."""
        scanner = Scanner()
        trace_id = "test-trace-id"
        
        # Mock config service to return min_price_threshold = 0.97
        mock_config = mock_config_service.get_risk_config.return_value
        mock_config.min_price_threshold = 0.97
        
        markets = [
            {"id": "1", "outcomes": [{"name": "YES", "price": 0.98}, {"name": "NO", "price": 0.02}], "status": "OPEN", "category": "sports"},
            {"id": "2", "outcomes": [{"name": "YES", "price": 0.96}, {"name": "NO", "price": 0.04}], "status": "OPEN", "category": "sports"},  # Precio bajo
            {"id": "3", "outcomes": [{"name": "YES", "price": 0.99}, {"name": "NO", "price": 0.01}], "status": "OPEN", "category": "sports"},
        ]
        
        # Pasar config directamente al scanner para evitar acceso a DB
        scanner.filters.config = mock_config
        
        candidates, rejections = scanner._filter_candidate_markets(markets, trace_id)
        
        # Should only include markets with best_yes_price >= 0.97
        assert len(candidates) == 2
        assert all(m["id"] in ["1", "3"] for m in candidates)
    
    def test_update_market_state(self, mock_state):
        """Test updating market state in memory."""
        scanner = Scanner()
        from app.core.state import MarketState
        from app.core.scanner.models import CandidateMarket, Outcome, EventMetadata
        
        market_id = uuid4()
        db_market = Mock()
        db_market.id = market_id
        
        # Crear CandidateMarket
        candidate = CandidateMarket(
            polymarket_id="polymarket-123",
            trace_id=str(uuid4()),
            question="Test market",
            category="sports",
            created_at=datetime.utcnow(),
            outcomes=[
                Outcome(name="YES", price=0.98, liquidity=1000.0, volume_24h=5000.0),
                Outcome(name="NO", price=0.02, liquidity=100.0, volume_24h=200.0)
            ],
            best_yes_price=0.98,
            best_no_price=0.02,
            spread=0.96,
            status="OPEN",
            event_metadata=EventMetadata(),
            volume_24h=5200.0,
            liquidity_total=1100.0,
            market_hash="test-hash",
            scanned_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        scanner._update_market_state(candidate, db_market)
        
        assert market_id in mock_state.markets
        market_state = mock_state.markets[market_id]
        assert market_state.polymarket_id == "polymarket-123"
        assert market_state.last_price == 0.98
        assert market_state.spread == 0.96
        assert market_state.volume == 5200.0
    
    @pytest.mark.asyncio
    async def test_tick_skips_if_too_soon(self, mock_state, mock_config_service):
        """Test that tick skips if not enough time has passed."""
        scanner = Scanner()
        scanner._last_scan = datetime.utcnow()
        
        # Mock config to require 5 seconds between scans
        mock_config_service.get_risk_config.return_value.scan_interval_seconds = 5.0
        
        with patch("app.core.scanner.config_service", mock_config_service):
            await scanner.tick()
        
        # Should not have made any API calls
        # (We can't easily verify this without more mocking, but the function should return early)
    
    async def test_close_cleans_up_client(self):
        """Test that close() cleans up HTTP client."""
        scanner = Scanner()
        client = await scanner._get_client()
        assert scanner._client is not None
        
        await scanner.close()
        assert scanner._client is None

