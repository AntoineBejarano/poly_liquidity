"""
Phase 1: Directory — endpoints de lectura cache-first.

- Endpoints GET /directory/categories, /tags, /markets, /events solo leen DB; no llaman a Gamma.
- Respuestas incluyen _meta (last_scanned_at, freshness, source, data_age_seconds).
- Invariante: cero llamadas HTTP a Gamma en cualquier request a Directory.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.api.auth import User, get_current_user, get_admin_user
from app.models.user_sync import UserSync
from app.models.user import UserMetadata


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock de autenticación para tests Phase 1."""
    mock_user_sync = Mock(spec=UserSync)
    mock_user_sync.id = "test-user-id"
    mock_user_sync.email = "test@example.com"
    mock_user_sync.name = "Test User"
    mock_user_sync.created_at = datetime.now(timezone.utc)
    mock_user_sync.updated_at = datetime.now(timezone.utc)

    mock_metadata = Mock(spec=UserMetadata)
    mock_metadata.role = "admin"

    mock_user = User(mock_user_sync, mock_metadata)

    async def get_current_user_mock():
        return mock_user

    async def get_admin_user_mock():
        return mock_user

    app.dependency_overrides[get_current_user] = get_current_user_mock
    app.dependency_overrides[get_admin_user] = get_admin_user_mock

    yield

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_admin_user, None)


@pytest.fixture
def client():
    return TestClient(app)


class TestDirectoryNoGammaCalls:
    """Invariante: los endpoints Directory no realizan llamadas HTTP a Gamma."""

    @pytest.mark.parametrize("path", [
        "/directory/meta",
        "/directory/categories",
        "/directory/tags",
        "/directory/markets",
        "/directory/events",
    ])
    def test_directory_endpoint_does_not_call_gamma(self, client, path):
        """Cada request a un endpoint Directory no debe invocar httpx a la API Gamma."""
        with patch("httpx.AsyncClient.get") as mock_get:
            response = client.get(path)
            assert response.status_code in (200, 422), f"Unexpected status for {path}: {response.status_code}"
            # Ninguna llamada a Gamma (polymarket gamma URL)
            gamma_calls = [c for c in mock_get.call_args_list if c and len(c) >= 1 and "gamma" in str(c).lower()]
            assert len(gamma_calls) == 0, f"Directory endpoint {path} must not call Gamma; got {mock_get.call_args_list}"


class TestDirectoryMetaContract:
    """Contrato de freshness en respuestas Directory."""

    def test_directory_meta_includes_freshness_fields(self, client):
        """GET /directory/meta devuelve last_scanned_at, freshness, source, data_age_seconds."""
        response = client.get("/directory/meta")
        assert response.status_code == 200
        data = response.json()
        assert "last_scanned_at" in data
        assert "freshness" in data
        assert data["freshness"] in ("fresh", "stale")
        assert "source" in data
        assert data["source"] == "db"
        assert "data_age_seconds" in data

    def test_directory_markets_response_includes_meta(self, client):
        """GET /directory/markets incluye _meta en la respuesta."""
        response = client.get("/directory/markets?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "_meta" in data
        assert "freshness" in data["_meta"]
        assert "source" in data["_meta"]

    def test_directory_events_response_includes_meta(self, client):
        """GET /directory/events incluye _meta en la respuesta."""
        response = client.get("/directory/events?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "_meta" in data


class TestDirectoryPagination:
    """Paginación limit/offset en Directory."""

    def test_directory_markets_respects_limit_offset(self, client):
        """GET /directory/markets con limit y offset devuelve estructura correcta."""
        response = client.get("/directory/markets?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_directory_events_respects_limit_offset(self, client):
        """GET /directory/events con limit y offset devuelve estructura correcta."""
        response = client.get("/directory/events?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["limit"] == 2
        assert data["offset"] == 0
