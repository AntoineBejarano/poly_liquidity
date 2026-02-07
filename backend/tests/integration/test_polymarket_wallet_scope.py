"""
Tests política v2: /markets (Gamma) sin wallet; wallet-data (balance, WS subscribe) exige wallet.
Sin PRIVATE_KEY/FUNDER en env: markets funciona, wallet-data falla 409 si no hay wallet.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from app.main import app
from app.api.auth import get_current_user, User
from app.api.errors import WALLET_NOT_CONFIGURED_STATUS, WALLET_NOT_CONFIGURED_DETAIL
from app.models.user_sync import UserSync
from app.models.user import UserMetadata


@pytest.fixture
def auth_user_no_wallet():
    """Usuario autenticado sin wallet (para dependency override)."""
    mock_user_sync = Mock(spec=UserSync)
    mock_user_sync.id = "user-no-wallet"
    mock_user_sync.email = "nowallet@test.com"
    mock_user_sync.name = "No Wallet"
    mock_user_sync.created_at = datetime.now(timezone.utc)
    mock_user_sync.updated_at = datetime.now(timezone.utc)
    mock_meta = Mock(spec=UserMetadata)
    mock_meta.role = "viewer"
    return User(mock_user_sync, mock_meta)


class TestMarketsWithoutWallet:
    """GET /api/polymarket/events (Gamma) no requiere wallet."""

    def test_events_public_no_wallet_required(self, client):
        """Sin auth, Gamma proxy no debe devolver 409 por wallet (puede 200 o 401)."""
        resp = client.get("/api/polymarket/events?limit=1")
        assert resp.status_code != 409 or resp.json().get("detail", {}).get("error") != "WALLET_NOT_CONFIGURED"

    def test_balance_requires_wallet_returns_409(self, client, auth_user_no_wallet):
        """GET /api/polymarket/balance con auth pero sin wallet => 409."""
        async def get_user():
            return auth_user_no_wallet
        app.dependency_overrides[get_current_user] = get_user
        try:
            mock_wrapper = Mock()
            mock_wrapper.is_available = Mock(return_value=False)
            with patch("app.core.execution.polymarket_client_wrapper.get_polymarket_client_for_user", return_value=mock_wrapper):
                resp = client.get("/api/polymarket/balance")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == WALLET_NOT_CONFIGURED_STATUS
        data = resp.json()
        assert data.get("detail", {}).get("error") == WALLET_NOT_CONFIGURED_DETAIL["error"]

    def test_websocket_subscribe_user_requires_wallet_returns_409(self, client, auth_user_no_wallet):
        """POST /api/polymarket/websocket/subscribe/user sin wallet => 409 (WS USER no abre)."""
        async def get_user():
            return auth_user_no_wallet
        app.dependency_overrides[get_current_user] = get_user
        try:
            mock_wrapper = Mock()
            mock_wrapper.is_available = Mock(return_value=False)
            with patch("app.core.execution.polymarket_client_wrapper.get_polymarket_client_for_user", return_value=mock_wrapper):
                resp = client.post(
                    "/api/polymarket/websocket/subscribe/user",
                    json={"owner_key": "test", "market_ids": None},
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == WALLET_NOT_CONFIGURED_STATUS
        data = resp.json()
        assert data.get("detail", {}).get("error") == WALLET_NOT_CONFIGURED_DETAIL["error"]
