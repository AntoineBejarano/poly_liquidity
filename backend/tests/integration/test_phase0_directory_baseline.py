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


# Usar el client del conftest (inyecta db_session vía setup_test_client) para evitar 500 por BD.


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

    @pytest.mark.asyncio
    async def test_get_markets_includes_clob_token_ids_and_headers(self, client):
        """GET /markets incluye clob_token_ids por market y headers X-Limit, X-Offset, X-Has-More."""
        from app.core.cache_provider import gamma_cache_provider
        from app.api.markets import _build_gamma_cache_key
        cache_key = _build_gamma_cache_key(
            limit=50, offset=0, closed="false", order="createdAt",
            ascending=False, tag_id=None
        )
        fake_markets = [
            {
                "id": "m_with_dict",
                "question": "Q",
                "name": "Q",
                "tags": [],
                "clobTokenIds": {"YES": "y1", "NO": "n1"},
            }
        ]
        await gamma_cache_provider.set(cache_key, fake_markets, ttl_seconds=60)
        response = client.get("/markets")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        m = next((x for x in data if x.get("market_id") == "m_with_dict"), None)
        assert m is not None
        clob = m.get("clob_token_ids")
        assert clob is not None
        assert clob.get("selection_hint") == "primary_yes"
        assert clob.get("primary") == "y1"
        assert clob.get("primary_yes") == "y1"
        assert clob.get("primary_no") == "n1"
        assert response.headers.get("X-Limit") == "50"
        assert response.headers.get("X-Offset") == "0"
        assert "X-Has-More" in response.headers
        assert "X-Gamma-Fetch-Count" in response.headers
        assert "X-Gamma-Scanned" in response.headers

    @pytest.mark.asyncio
    async def test_get_markets_enabled_filter_and_headers_phase2(self, client):
        """Fase 2: enabled filter reduce items; X-Enabled-Filter-Applied, X-Offset-Mode, X-Partial-Page."""
        from app.core.cache_provider import gamma_cache_provider
        from app.api.markets import _build_gamma_cache_key
        # Con enabled=True se usa two-phase: primer chunk limit=100, offset=0
        cache_key = _build_gamma_cache_key(
            limit=100, offset=0, closed="false", order="createdAt",
            ascending=False, tag_id=None
        )
        fake_markets = [
            {"id": "m_enabled", "question": "E", "name": "E", "tags": [], "clobTokenIds": None},
            {"id": "m_disabled", "question": "D", "name": "D", "tags": [], "clobTokenIds": None},
        ]
        await gamma_cache_provider.set(cache_key, fake_markets, ttl_seconds=60)
        patch_resp = client.patch("/markets/m_enabled/enable", json={"enabled": True})
        assert patch_resp.status_code == 200
        response = client.get("/markets", params={"enabled": True})
        assert response.status_code == 200
        assert response.headers.get("X-Enabled-Filter-Applied") == "true"
        assert response.headers.get("X-Offset-Mode") == "filtered"
        assert response.headers.get("X-Partial-Page") == "false"
        data = response.json()
        for m in data:
            assert m.get("enabled") is True
        m_enabled_found = next((x for x in data if x.get("market_id") == "m_enabled"), None)
        assert m_enabled_found is not None

    def test_get_markets_without_enabled_has_gamma_offset_mode(self, client):
        """Sin enabled: X-Offset-Mode=gamma, X-Enabled-Filter-Applied=false."""
        response = client.get("/markets", params={"limit": 10})
        assert response.status_code == 200
        assert response.headers.get("X-Enabled-Filter-Applied") == "false"
        assert response.headers.get("X-Offset-Mode") == "gamma"

    def test_get_markets_returns_503_when_circuit_breaker_open(self, client):
        """Fase 3: circuit breaker abierto → 503 en <500ms."""
        from app.api.markets import _gamma_markets_circuit_breaker
        from app.core.runtime_supervisor.circuit_breaker import CircuitBreakerState
        circuit = _gamma_markets_circuit_breaker()
        for _ in range(4):
            circuit.record_failure()
        assert circuit.is_open() or not circuit.can_attempt()
        try:
            response = client.get("/markets", params={"limit": 10})
            assert response.status_code == 503
            data = response.json()
            assert "unavailable" in data.get("detail", "").lower()
        finally:
            circuit.state = CircuitBreakerState.CLOSED
            circuit.failure_times.clear()
            circuit.opened_at = None

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


class TestOrderbookMetricsPhase4:
    """Fase 4: orderbook-metrics con token_ids, shape fijo, partial."""

    def test_orderbook_metrics_without_token_ids_uses_cache_or_errors(self, client):
        """Sin token_ids: compatibilidad - usa cache de markets o devuelve error informativo."""
        response = client.get("/markets/orderbook-metrics")
        assert response.status_code == 200
        data = response.json()
        assert "found_token_ids_count" in data
        assert "missing_token_ids_count" in data
        assert "partial" in data
        assert "timed_out" in data
        assert "errors" in data
        assert "metrics" in data
        if not data["metrics"]:
            assert any("token_ids" in e or "cache" in e for e in data["errors"])

    def test_orderbook_metrics_400_when_exceeds_max(self, client):
        """token_ids con más de 100 items → 400."""
        ids = ",".join([f"tid{i}" for i in range(101)])
        response = client.get("/markets/orderbook-metrics", params={"token_ids": ids})
        assert response.status_code == 400

    def test_orderbook_metrics_returns_fixed_shape(self, client):
        """Con token_ids válidos: shape fijo con counts y metrics."""
        response = client.get("/markets/orderbook-metrics", params={"token_ids": "t1,t2"})
        assert response.status_code == 200
        data = response.json()
        assert data["found_token_ids_count"] >= 0
        assert data["missing_token_ids_count"] >= 0
        assert "t1" in data["metrics"]
        assert "t2" in data["metrics"]

    @pytest.mark.asyncio
    async def test_orderbook_metrics_compat_uses_markets_cache(self, client):
        """Compatibilidad: sin token_ids pero con cache de markets → deriva tokens y consulta."""
        from app.core.cache_provider import gamma_cache_provider
        from app.api.markets import _build_gamma_cache_key
        cache_key = _build_gamma_cache_key(50, 0, "false", "createdAt", False, None)
        fake_markets = [
            {"id": "m1", "question": "Q1", "clobTokenIds": {"YES": "tok1", "NO": "tok2"}},
        ]
        await gamma_cache_provider.set(cache_key, fake_markets, ttl_seconds=60)
        response = client.get("/markets/orderbook-metrics")
        assert response.status_code == 200
        data = response.json()
        assert "tok1" in data["metrics"]
        assert data["metrics"]["tok1"] is None or isinstance(data["metrics"]["tok1"], dict)


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
        from app.core.cache_provider import gamma_cache_provider
        from app.api.markets import _build_gamma_cache_key
        import httpx

        cache_key = _build_gamma_cache_key(
            limit=50, offset=0, closed="false", order="createdAt",
            ascending=False, tag_id=None
        )
        fake_markets = [
            {
                "id": "m1",
                "question": "Q1",
                "name": "Q1",
                "category": "sports",
                "tags": [],
                "clobTokenIds": {"YES": "tok_yes_1", "NO": "tok_no_1"},
            }
        ]
        await gamma_cache_provider.set(cache_key, fake_markets, ttl_seconds=60)

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
