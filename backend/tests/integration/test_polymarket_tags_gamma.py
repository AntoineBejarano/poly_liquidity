"""
Tests GET /api/polymarket/tags (Gamma-first, discovery).
- No requiere auth ni wallet.
- Devuelve shape { items, limit, offset, total? }.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _make_mock_response(json_value):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = json_value
    r.raise_for_status = MagicMock()
    return r


class TestPolymarketTagsGamma:
    """GET /api/polymarket/tags: proxy Gamma, público."""

    def test_tags_route_exists_no_auth_required(self, client):
        """Sin Authorization el endpoint no devuelve 401 (no exige auth)."""
        with patch("app.api.polymarket.rate_limiter.wait_for_capacity", new_callable=AsyncMock, return_value=True):
            with patch("app.api.polymarket.api_cache.get", new_callable=AsyncMock, return_value=None):
                with patch("app.api.polymarket.api_cache.set", new_callable=AsyncMock):
                    with patch("app.api.polymarket.httpx.AsyncClient") as MockClient:
                        mock_get = AsyncMock(return_value=_make_mock_response([
                            {"id": "tag1", "label": "Crypto", "slug": "crypto"},
                        ]))
                        mock_instance = MagicMock()
                        mock_instance.get = mock_get
                        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
                        resp = client.get("/api/polymarket/tags?limit=200&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "limit" in data
        assert "offset" in data
        assert data["limit"] == 200
        assert data["offset"] == 0
        assert data.get("total") is None
        assert isinstance(data["items"], list)
        if data["items"]:
            first = data["items"][0]
            assert "tag_id" in first
            assert "name" in first

    def test_tags_returns_stable_shape(self, client):
        """Respuesta estable: items con tag_id, name, slug?, label?."""
        with patch("app.api.polymarket.rate_limiter.wait_for_capacity", new_callable=AsyncMock, return_value=True):
            with patch("app.api.polymarket.api_cache.get", new_callable=AsyncMock, return_value=None):
                with patch("app.api.polymarket.api_cache.set", new_callable=AsyncMock):
                    with patch("app.api.polymarket.httpx.AsyncClient") as MockClient:
                        mock_get = AsyncMock(return_value=_make_mock_response([
                            {"id": "t1", "label": "Tag A", "slug": "tag-a"},
                        ]))
                        mock_instance = MagicMock()
                        mock_instance.get = mock_get
                        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
                        resp = client.get("/api/polymarket/tags?limit=10&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 10
        assert data["offset"] == 0
        items = data["items"]
        assert len(items) >= 1
        first = items[0]
        assert first.get("tag_id") == "t1"
        assert first.get("name") == "Tag A"
        assert first.get("label") == "Tag A"
        assert first.get("slug") == "tag-a"

    def test_directory_tags_requires_auth(self, client):
        """GET /directory/tags exige auth (legacy DB); sin token devuelve 401.
        Discovery debe usar GET /api/polymarket/tags (público)."""
        resp = client.get("/directory/tags?limit=10&offset=0")
        assert resp.status_code == 401
