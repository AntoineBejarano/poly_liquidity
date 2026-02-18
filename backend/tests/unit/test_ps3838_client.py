"""
Tests unitarios para el cliente PS3838 (Lines API y Bets API).
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.core.ps3838.client import PS3838Client, DEFAULT_PS3838_BASE_URL


class TestPS3838Client:
    """Tests para PS3838Client."""

    def test_init_default_base_url(self):
        """El cliente usa la URL por defecto si no se pasa base_url."""
        c = PS3838Client(username="u", password="p")
        assert c.base_url == DEFAULT_PS3838_BASE_URL
        assert c.username == "u"
        assert c.password == "p"

    def test_init_custom_base_url(self):
        """El cliente acepta base_url personalizada."""
        c = PS3838Client(username="u", password="p", base_url="https://custom.ps3838.com")
        assert c.base_url == "https://custom.ps3838.com"

    def test_auth_header_format(self):
        """El header de autorización es Basic base64(user:pass)."""
        c = PS3838Client(username="user", password="secret")
        h = c._auth_header()
        assert h.startswith("Basic ")
        import base64
        decoded = base64.b64decode(h[6:]).decode()
        assert decoded == "user:secret"

    @pytest.mark.asyncio
    async def test_get_fixtures_calls_correct_url(self):
        """get_fixtures llama a /v3/fixtures con sportId si se pasa."""
        from unittest.mock import MagicMock
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"fixtures": []}
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            c = PS3838Client(username="u", password="p", base_url="https://api.test.com")
            out = await c.get_fixtures(sport_id=1)
            assert out == {"fixtures": []}
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert "/v3/fixtures" in call_args[0][0]
            assert call_args[1]["params"].get("sportId") == 1

    @pytest.mark.asyncio
    async def test_get_odds_calls_correct_url(self):
        """get_odds llama a /v4/odds con sportId si se pasa."""
        from unittest.mock import MagicMock
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"odds": []}
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            c = PS3838Client(username="u", password="p", base_url="https://api.test.com")
            out = await c.get_odds(sport_id=1)
            assert out == {"odds": []}
            call_args = mock_client.get.call_args
            assert "/v4/odds" in call_args[0][0]
            assert call_args[1]["params"].get("sportId") == 1

    @pytest.mark.asyncio
    async def test_place_bet_sends_unique_request_id(self):
        """place_bet incluye Unique-Request-Id en headers o en body."""
        from unittest.mock import MagicMock
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"betId": "123"}
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            c = PS3838Client(username="u", password="p", base_url="https://api.test.com")
            out = await c.place_bet(payload={"eventId": 1, "stake": 10})
            assert out == {"betId": "123"}
            call_args = mock_client.post.call_args
            assert "Unique-Request-Id" in call_args[1]["headers"] or "uniqueRequestId" in call_args[1]["json"]
