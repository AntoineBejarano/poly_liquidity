"""
Tests unitarios para el conector PS3838.
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.core.connectors.ps3838 import Ps3838Connector
from app.core.connectors.base import ConnectorError


class TestPs3838Connector:
    """Tests para Ps3838Connector."""

    @pytest.mark.asyncio
    async def test_fetch_fixtures_delegates_to_client(self):
        """fetch('/v3/fixtures') devuelve lo que devuelve get_fixtures."""
        with patch("app.core.connectors.ps3838.PS3838Client") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_fixtures = AsyncMock(return_value={"fixtures": [{"id": 1}]})
            mock_client_class.return_value = mock_client

            connector = Ps3838Connector(connector_config={"username": "u", "password": "p"})
            out = await connector.fetch("/v3/fixtures", params={})
            assert out == {"fixtures": [{"id": 1}]}
            mock_client.get_fixtures.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_odds_delegates_to_client(self):
        """fetch('/v4/odds') devuelve lo que devuelve get_odds."""
        with patch("app.core.connectors.ps3838.PS3838Client") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_odds = AsyncMock(return_value={"odds": []})
            mock_client_class.return_value = mock_client

            connector = Ps3838Connector(connector_config={"username": "u", "password": "p"})
            out = await connector.fetch("/v4/odds", params={})
            assert out == {"odds": []}

    @pytest.mark.asyncio
    async def test_fetch_requires_username_password(self):
        """Si faltan username o password, fetch lanza ConnectorError."""
        connector = Ps3838Connector(connector_config={})
        with pytest.raises(ConnectorError) as exc_info:
            await connector.fetch("/v3/fixtures", params={})
        assert "username" in exc_info.value.args[0].lower() or "password" in exc_info.value.args[0].lower()

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_on_success(self):
        """health_check devuelve status healthy si fetch funciona."""
        with patch.object(Ps3838Connector, "fetch", new_callable=AsyncMock, return_value={}):
            connector = Ps3838Connector(connector_config={"username": "u", "password": "p"})
            out = await connector.health_check()
            assert out["status"] == "healthy"
