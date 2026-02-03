"""
Phase 0: Discovery / Directory baseline (SPEC DISCOVERY_UNIVERSE_STRATEGY_BUILDER).

- last_scanned_at expuesto (vía live/status con app.state.scanner).
- Tests de integración para GET /markets y GET /markets/events/list.
- Invariante: rutas de listado para el usuario no realizan llamadas HTTP a Gamma
  cuando se sirve desde cache (markets) o desde DB (events).
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.auth import User, get_current_user, get_admin_user
from app.models.user_sync import UserSync
from app.models.user import UserMetadata


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock de autenticación para tests Phase 0."""
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


class TestLastScannedAtExposed:
    """last_scanned_at consultable tras run del Scanner (Phase 0) vía GET /directory/meta."""

    def test_directory_meta_returns_last_scanned_at_when_scanner_available(self, client):
        """GET /directory/meta devuelve last_scanned_at cuando app.state.scanner tiene get_stats."""
        scanner = Mock()
        scanner.get_stats = Mock(return_value={
            "scan_count": 1,
            "markets_scanned_total": 10,
            "markets_filtered_total": 5,
            "last_scan": "2025-02-03T12:00:00",
        })
        app.state.scanner = scanner

        try:
            response = client.get("/directory/meta")
            assert response.status_code == 200
            data = response.json()
            assert data["last_scanned_at"] == "2025-02-03T12:00:00"
        finally:
            if hasattr(app.state, "scanner"):
                del app.state.scanner

    def test_directory_meta_returns_none_when_no_scanner(self, client):
        """GET /directory/meta devuelve last_scanned_at null cuando no hay scanner en app.state."""
        had = getattr(app.state, "scanner", None)
        if hasattr(app.state, "scanner"):
            del app.state.scanner
        try:
            response = client.get("/directory/meta")
            assert response.status_code == 200
            data = response.json()
            assert data["last_scanned_at"] is None
        finally:
            if had is not None:
                app.state.scanner = had


class TestMarketsAndEventsListIntegration:
    """Tests de integración GET /markets y GET /markets/events/list (Phase 0)."""

    def test_get_markets_returns_200_and_array(self, client):
        """GET /markets devuelve 200 y array (filtros existentes; paginación implícita)."""
        response = client.get("/markets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_markets_accepts_query_params(self, client):
        """GET /markets acepta category, enabled, search, tag_id, series_id."""
        response = client.get("/markets", params={"category": "sports"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_events_list_returns_200_and_array(self, client):
        """GET /markets/events/list devuelve 200 y array."""
        response = client.get("/markets/events/list")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_events_list_accepts_state_and_market_id(self, client):
        """GET /markets/events/list acepta state y market_id."""
        response = client.get("/markets/events/list", params={"state": "ACTIVE"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestInvariantNoGammaCallsOnListEndpoints:
    """
    Invariante Phase 0: las rutas de listado (markets, events/list) no realizan
    llamadas HTTP a Gamma en la request cuando se sirve desde cache o DB.
    """

    @pytest.mark.asyncio
    async def test_list_endpoints_do_not_call_gamma_when_serving_from_cache_or_db(
        self, client
    ):
        """
        Con cache de markets poblado y events desde DB:
        GET /markets y GET /markets/events/list no deben disparar ninguna
        petición HTTP a la API Gamma (polymarket).
        """
        from app.core.api_cache import api_cache
        import httpx

        cache_key = "polymarket_api:markets:closed=false:all_pages"
        fake_markets = [
            {
                "id": "m1",
                "question": "Q1",
                "name": "Q1",
                "category": "sports",
                "tags": [],
            }
        ]
        await api_cache.set(cache_key, fake_markets, ttl=timedelta(seconds=60))

        gamma_requests = []

        async def recording_get(self, url, **kwargs):
            url_str = str(url)
            if "gamma" in url_str.lower() or "polymarket.com" in url_str.lower():
                gamma_requests.append(url_str)
            return await original_get(self, url, **kwargs)

        original_get = httpx.AsyncClient.get
        with patch.object(httpx.AsyncClient, "get", recording_get):
            r_markets = client.get("/markets")
            r_events = client.get("/markets/events/list")

        assert r_markets.status_code == 200, r_markets.text
        assert r_events.status_code == 200, r_events.text
        assert len(gamma_requests) == 0, (
            f"Invariante violado: se realizaron {len(gamma_requests)} "
            f"peticiones a Gamma: {gamma_requests}"
        )
