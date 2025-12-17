"""
Tests unitarios para sistema de conectores.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.core.connectors.base import BaseConnector, ConnectorError
from app.core.connectors.registry import ConnectorRegistry, connector_registry
from app.core.connectors.custom_api import CustomAPIConnector


class TestBaseConnector:
    """Tests para BaseConnector."""
    
    def test_init(self):
        """Test inicialización de BaseConnector."""
        class TestConnector(BaseConnector):
            async def fetch(self, endpoint, params=None, headers=None, method="GET"):
                return {}
            
            async def health_check(self):
                return {"status": "healthy"}
        
        connector = TestConnector({"base_url": "https://api.example.com"})
        
        assert connector.config == {"base_url": "https://api.example.com"}
        assert connector.get_base_url() == "https://api.example.com"
    
    def test_get_api_key(self):
        """Test obtener API key."""
        class TestConnector(BaseConnector):
            async def fetch(self, endpoint, params=None, headers=None, method="GET"):
                return {}
            
            async def health_check(self):
                return {"status": "healthy"}
        
        connector = TestConnector({"api_key": "test-key"})
        assert connector.get_api_key() == "test-key"
    
    def test_get_headers(self):
        """Test obtener headers."""
        class TestConnector(BaseConnector):
            async def fetch(self, endpoint, params=None, headers=None, method="GET"):
                return {}
            
            async def health_check(self):
                return {"status": "healthy"}
        
        connector = TestConnector({"headers": {"X-Custom": "value"}})
        assert connector.get_headers() == {"X-Custom": "value"}


class TestConnectorRegistry:
    """Tests para ConnectorRegistry."""
    
    def test_register(self):
        """Test registrar conector."""
        registry = ConnectorRegistry()
        
        class TestConnector(BaseConnector):
            async def fetch(self, endpoint, params=None, headers=None, method="GET"):
                return {}
            
            async def health_check(self):
                return {"status": "healthy"}
        
        registry.register("test", TestConnector)
        
        assert "test" in registry.list_connector_types()
    
    def test_register_invalid(self):
        """Test registrar conector inválido."""
        registry = ConnectorRegistry()
        
        class InvalidConnector:
            pass
        
        with pytest.raises(ValueError, match="must inherit from BaseConnector"):
            registry.register("test", InvalidConnector)
    
    def test_get_connector(self):
        """Test obtener conector."""
        registry = ConnectorRegistry()
        
        class TestConnector(BaseConnector):
            async def fetch(self, endpoint, params=None, headers=None, method="GET"):
                return {}
            
            async def health_check(self):
                return {"status": "healthy"}
        
        registry.register("test", TestConnector)
        
        connector = registry.get_connector("test", {"base_url": "https://api.example.com"})
        
        assert isinstance(connector, TestConnector)
        assert connector.get_base_url() == "https://api.example.com"
    
    def test_get_connector_not_registered(self):
        """Test obtener conector no registrado."""
        registry = ConnectorRegistry()
        
        with pytest.raises(ConnectorError, match="not registered"):
            registry.get_connector("nonexistent", {})


class TestCustomAPIConnector:
    """Tests para CustomAPIConnector."""
    
    @pytest.mark.asyncio
    async def test_fetch_get_success(self):
        """Test GET exitoso."""
        connector = CustomAPIConnector({
            "base_url": "https://api.example.com"
        })
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"result": "success"}
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance
            
            result = await connector.fetch("/api/events", method="GET")
            
            assert result == {"result": "success"}
            mock_client_instance.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_post_success(self):
        """Test POST exitoso."""
        connector = CustomAPIConnector({
            "base_url": "https://api.example.com"
        })
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"result": "created"}
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance
            
            result = await connector.fetch(
                "/api/events",
                params={"name": "test"},
                method="POST"
            )
            
            assert result == {"result": "created"}
            mock_client_instance.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_with_api_key(self):
        """Test fetch con API key."""
        connector = CustomAPIConnector({
            "base_url": "https://api.example.com",
            "api_key": "test-key",
            "api_key_header": "Authorization"
        })
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"result": "success"}
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance
            
            await connector.fetch("/api/events", method="GET")
            
            # Verificar que se agregó el header de API key
            call_args = mock_client_instance.get.call_args
            assert call_args[1]["headers"]["Authorization"] == "test-key"
    
    @pytest.mark.asyncio
    async def test_fetch_http_error(self):
        """Test error HTTP."""
        connector = CustomAPIConnector({
            "base_url": "https://api.example.com"
        })
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_instance.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found",
                    request=MagicMock(),
                    response=mock_response
                )
            )
            mock_client.return_value = mock_client_instance
            
            with pytest.raises(ConnectorError, match="HTTP error"):
                await connector.fetch("/api/events", method="GET")
    
    @pytest.mark.asyncio
    async def test_fetch_timeout(self):
        """Test timeout."""
        connector = CustomAPIConnector({
            "base_url": "https://api.example.com",
            "timeout_seconds": 5.0
        })
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_instance.get = AsyncMock(
                side_effect=httpx.TimeoutException("Request timeout")
            )
            mock_client.return_value = mock_client_instance
            
            with pytest.raises(ConnectorError, match="timeout"):
                await connector.fetch("/api/events", method="GET")
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check exitoso."""
        connector = CustomAPIConnector({
            "base_url": "https://api.example.com",
            "health_endpoint": "/health"
        })
        
        with patch.object(connector, 'fetch', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"status": "ok"}
            
            result = await connector.health_check()
            
            assert result["status"] == "healthy"
            assert "latency_ms" in result
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Test health check fallido."""
        connector = CustomAPIConnector({
            "base_url": "https://api.example.com"
        })
        
        with patch.object(connector, 'fetch', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ConnectorError("Connection failed")
            
            result = await connector.health_check()
            
            assert result["status"] == "unhealthy"
            assert "connection" in result["message"].lower() or "error" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_health_check_no_base_url(self):
        """Test health check sin base_url."""
        connector = CustomAPIConnector({})
        
        result = await connector.health_check()
        
        assert result["status"] == "unhealthy"
        assert "base_url" in result["message"]

