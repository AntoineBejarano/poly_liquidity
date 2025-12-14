"""
Tests unitarios para verificar que Scanner usa ConfigService.
"""
import pytest
from unittest.mock import Mock, patch
from app.core.scanner.scanner import Scanner
from app.core.scanner.filters import ScannerFilters
from app.core.config_service import config_service


@pytest.fixture
def scanner():
    """Fixture para Scanner."""
    return Scanner()


@pytest.fixture
def scanner_filters():
    """Fixture para ScannerFilters."""
    return ScannerFilters()


@pytest.fixture
def mock_config_service():
    """Mock ConfigService."""
    with patch('app.core.scanner.scanner.config_service') as mock, \
         patch('app.core.scanner.filters.config_service') as mock_filters:
        
        # Mock get_scanner_config
        mock_scanner_config = {
            "min_price_threshold": 0.97,
            "allowed_categories": ["sports"],
            "allowed_subcategories": [],
            "scan_interval_seconds": 30.0,
            "min_volume_24h": 0.0,
            "min_liquidity": 0.0,
        }
        
        mock.get_scanner_config.return_value = mock_scanner_config
        mock_filters.get_scanner_config.return_value = mock_scanner_config
        
        # Mock get para parámetros adicionales
        def get_side_effect(key, default=None):
            params = {
                "scanner_http_timeout_seconds": 30.0,
                "scanner_cache_ttl_seconds": 5,
                "scanner_pagination_limit": 100,
                "scanner_max_pages": 10,
                "scanner_max_event_days_ahead": 7,
            }
            return params.get(key, default)
        
        mock.get.side_effect = get_side_effect
        mock_filters.get.side_effect = get_side_effect
        
        yield mock, mock_filters


def test_scanner_tick_uses_scanner_config(scanner, mock_config_service):
    """Test que tick() usa get_scanner_config() para scan_interval."""
    mock, _ = mock_config_service
    
    # Mock datetime para controlar el tiempo
    with patch('app.core.scanner.scanner.datetime') as mock_datetime:
        from datetime import datetime as dt
        mock_datetime.utcnow.return_value = dt(2024, 1, 1, 12, 0, 0)
        
        # Mock async methods
        with patch.object(scanner, '_fetch_markets_from_polymarket', return_value=[]):
            import asyncio
            asyncio.run(scanner.tick())
        
        # Verificar que se llamó a get_scanner_config
        mock.get_scanner_config.assert_called()


def test_scanner_http_timeout_uses_config_service(scanner, mock_config_service):
    """Test que _get_client() usa scanner_http_timeout_seconds desde ConfigService."""
    mock, _ = mock_config_service
    
    import asyncio
    client = asyncio.run(scanner._get_client())
    
    # Verificar que se obtuvo el timeout
    mock.get.assert_any_call("scanner_http_timeout_seconds", 30.0)
    
    # Verificar que el client tiene el timeout correcto
    assert client.timeout.connect == 30.0


def test_scanner_cache_ttl_uses_config_service(scanner, mock_config_service):
    """Test que _fetch_markets_from_polymarket() usa scanner_cache_ttl_seconds desde ConfigService."""
    mock, _ = mock_config_service
    
    # Mock async methods
    async def mock_cache_get(key):
        return None
    
    async def mock_cache_set(key, value, ttl):
        pass
    
    async def mock_wait_for_capacity(endpoint_type, timeout):
        return True
    
    with patch('app.core.scanner.scanner.api_cache') as mock_cache_module, \
         patch('app.core.scanner.scanner.rate_limiter') as mock_rate_limiter, \
         patch.object(scanner, '_get_client') as mock_client:
        
        mock_cache_module.get = mock_cache_get
        mock_cache_module.set = mock_cache_set
        mock_rate_limiter.wait_for_capacity = mock_wait_for_capacity
        
        mock_httpx_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_httpx_client.get = lambda *args, **kwargs: mock_response
        mock_client.return_value = mock_httpx_client
        
        import asyncio
        asyncio.run(scanner._fetch_markets_from_polymarket())
        
        # Verificar que se obtuvo el TTL
        mock.get.assert_any_call("scanner_cache_ttl_seconds", 5)


def test_scanner_pagination_uses_config_service(scanner, mock_config_service):
    """Test que _fetch_markets_from_polymarket() usa parámetros de paginación desde ConfigService."""
    mock, _ = mock_config_service
    
    # Mock async methods
    async def mock_cache_get(key):
        return None
    
    async def mock_cache_set(key, value, ttl):
        pass
    
    async def mock_wait_for_capacity(endpoint_type, timeout):
        return True
    
    with patch('app.core.scanner.scanner.api_cache') as mock_cache_module, \
         patch('app.core.scanner.scanner.rate_limiter') as mock_rate_limiter, \
         patch.object(scanner, '_get_client') as mock_client:
        
        mock_cache_module.get = mock_cache_get
        mock_cache_module.set = mock_cache_set
        mock_rate_limiter.wait_for_capacity = mock_wait_for_capacity
        
        mock_httpx_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_httpx_client.get = lambda *args, **kwargs: mock_response
        mock_client.return_value = mock_httpx_client
        
        import asyncio
        asyncio.run(scanner._fetch_markets_from_polymarket())
        
        # Verificar que se obtuvieron los parámetros
        mock.get.assert_any_call("scanner_pagination_limit", 100)
        mock.get.assert_any_call("scanner_max_pages", 10)


def test_filters_category_uses_config_service(scanner_filters, mock_config_service):
    """Test que filter_category() usa allowed_categories desde ConfigService."""
    _, mock_filters = mock_config_service
    
    market = {
        "id": "test_market",
        "status": "OPEN",
        "category": "sports",
        "outcomes": [
            {"name": "YES", "price": 0.99},
            {"name": "NO", "price": 0.01}
        ]
    }
    
    passes, reason = scanner_filters.filter_category(market)
    
    # Verificar que se llamó a get_scanner_config
    mock_filters.get_scanner_config.assert_called()
    
    # Debería pasar porque "sports" está en allowed_categories
    assert passes is True


def test_filters_price_uses_config_service(scanner_filters, mock_config_service):
    """Test que filter_price() usa min_price_threshold desde ConfigService."""
    _, mock_filters = mock_config_service
    
    market = {
        "id": "test_market",
        "status": "OPEN",
        "outcomes": [
            {"name": "YES", "price": 0.99},
            {"name": "NO", "price": 0.01}
        ]
    }
    
    passes, reason = scanner_filters.filter_price(market)
    
    # Verificar que se llamó a get_scanner_config
    mock_filters.get_scanner_config.assert_called()
    
    # Debería pasar porque 0.99 >= 0.97
    assert passes is True


def test_filters_temporal_uses_config_service(scanner_filters, mock_config_service):
    """Test que filter_temporal() usa scanner_max_event_days_ahead desde ConfigService."""
    _, mock_filters = mock_config_service
    
    from datetime import datetime, timedelta
    
    event_metadata = {
        "event_start_time_parsed": datetime.utcnow() + timedelta(days=10)
    }
    
    market = {
        "id": "test_market",
        "status": "OPEN",
        "outcomes": [
            {"name": "YES", "price": 0.99},
            {"name": "NO", "price": 0.01}
        ]
    }
    
    passes, reason = scanner_filters.filter_temporal(market, event_metadata)
    
    # Verificar que se obtuvo el parámetro
    mock_filters.get.assert_any_call("scanner_max_event_days_ahead", 7)
    
    # Debería fallar porque 10 días > 7 días máximo
    assert passes is False

