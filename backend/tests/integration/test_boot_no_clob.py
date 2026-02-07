"""
Tests política v2: boot sin CLOB ni WS USER.

- App arranca sin PRIVATE_KEY/FUNDER y sin wallets.
- GET /markets (Gamma) funciona sin auth.
- Endpoints wallet-data fallan 4xx si el usuario no tiene wallet (cubierto en test_polymarket_wallet_scope).
- Startup NO abre WS USER ni crea clientes CLOB.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.main import app
from starlette.testclient import TestClient


@pytest.fixture
def client_no_env_wallet(db_session):
    """Client con get_db override; sin PRIVATE_KEY/FUNDER en settings para el test."""
    from app.database import get_db
    from app.settings import settings
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with patch.object(settings, "private_key", None), patch.object(
            settings, "funder_address", None
        ):
            yield TestClient(app, base_url="http://testserver")
    finally:
        app.dependency_overrides.pop(get_db, None)


class TestAppStartsWithoutPrivateKeyFunder:
    """La app arranca sin PRIVATE_KEY/FUNDER y sin wallets en BD."""

    def test_health_returns_200_without_private_key_funder(self, client_no_env_wallet):
        """Con settings sin PRIVATE_KEY/FUNDER, /health responde 200 (arranque correcto)."""
        resp = client_no_env_wallet.get("/health")
        assert resp.status_code == 200


class TestMarketsWithoutAuth:
    """GET /api/polymarket/events (Gamma) no requiere auth ni wallet."""

    def test_events_or_markets_do_not_require_wallet(self, client):
        """Sin auth, Gamma proxy no devuelve 409 por wallet (puede 200 o 401)."""
        resp = client.get("/api/polymarket/events?limit=1")
        # No debe ser 409 WALLET_NOT_CONFIGURED
        if resp.status_code == 409:
            data = resp.json()
            assert data.get("detail", {}).get("error") != "WALLET_NOT_CONFIGURED"
        # Aceptamos 200 (ok) o 401 (no auth) o 500 por red/env (no exigimos red en test)
        assert resp.status_code in (200, 401, 409, 500)


class TestStartupNoWsUserNoClob:
    """Startup no abre WS USER ni crea clientes CLOB."""

    def test_startup_does_not_call_connect_user_channel(self, db_session):
        """Al arrancar la app (lifespan), no se llama connect_user_channel (WS USER)."""
        from app.database import get_db
        app.dependency_overrides[get_db] = lambda: db_session
        connect_mock = MagicMock()
        # Evitar que ControlLoop.start ejecute el loop (query a strategies; DB de test puede no tener tablas)
        noop_start = AsyncMock(return_value=None)
        try:
            with patch(
                "app.core.execution.polymarket_websocket.PolymarketWebSocketManager.connect_user_channel",
                connect_mock,
            ), patch(
                "app.core.strategy_engine.control_loop.ControlLoop.start",
                noop_start,
            ):
                with TestClient(app, base_url="http://testserver") as c:
                    c.get("/health")
        finally:
            app.dependency_overrides.pop(get_db, None)
        connect_mock.assert_not_called()

    def test_startup_does_not_create_global_clob_client(self, db_session):
        """Al arrancar, get_polymarket_client_for_user no debe ser llamado (sin intents/wallet)."""
        from app.database import get_db
        app.dependency_overrides[get_db] = lambda: db_session
        clob_mock = MagicMock()
        noop_start = AsyncMock(return_value=None)
        try:
            with patch(
                "app.core.execution.polymarket_client_wrapper.get_polymarket_client_for_user",
                clob_mock,
            ), patch(
                "app.core.strategy_engine.control_loop.ControlLoop.start",
                noop_start,
            ):
                with TestClient(app, base_url="http://testserver") as c:
                    c.get("/health")
        finally:
            app.dependency_overrides.pop(get_db, None)
        clob_mock.assert_not_called()


class TestNoGlobalClobRegression:
    """Regresión: ningún path crea CLOB global ni usa PRIVATE_KEY/FUNDER."""

    def test_get_polymarket_client_raises(self):
        """get_polymarket_client() debe lanzar; no existe cliente global."""
        from app.core.execution.polymarket_client_wrapper import get_polymarket_client
        import pytest
        with pytest.raises(RuntimeError, match="Global CLOB client is not available"):
            get_polymarket_client()

    def test_initialize_client_raises_no_global_clob(self):
        """_initialize_client() (path legacy) debe lanzar; PRIVATE_KEY/FUNDER no se usan."""
        from app.core.execution.polymarket_client_wrapper import PolymarketCLOBWrapper
        import pytest
        wrapper = PolymarketCLOBWrapper(from_user_id=None)
        with pytest.raises(RuntimeError, match="No global CLOB"):
            wrapper._initialize_client()
