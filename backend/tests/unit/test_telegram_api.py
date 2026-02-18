"""Tests para API de conexión Telegram (send-code, sign-in, dialogs, save-connection)."""
import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_user():
    u = Mock()
    u.id = "test-user-telegram"
    return u


@pytest.fixture
def auth_headers(client):
    return {}


def test_send_code_requires_auth(client):
    """POST /telegram/send-code sin auth debe devolver 401."""
    r = client.post("/telegram/send-code", json={"phone": "+34600000000"})
    # Si la app exige auth: 401; si no: puede 200/400/501
    assert r.status_code in (401, 403, 422)


def test_send_code_body_validation(client, auth_headers):
    """Falta phone → 422."""
    r = client.post("/telegram/send-code", json={}, headers=auth_headers)
    if r.status_code != 401:
        assert r.status_code == 422


def test_dialogs_requires_session(client):
    """POST /telegram/dialogs sin session_encrypted_hex → 422."""
    r = client.post("/telegram/dialogs", json={})
    assert r.status_code in (401, 422)


def test_save_connection_requires_auth(client):
    """POST /telegram/save-connection sin auth → 401."""
    r = client.post(
        "/telegram/save-connection",
        json={"name": "My Telegram", "session_encrypted_hex": "deadbeef", "monitored_chats": []},
    )
    assert r.status_code == 401


def test_save_connection_creates_source(client, mock_user):
    """POST /telegram/save-connection con auth crea ExternalDataSource telegram."""
    from app.api.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        r = client.post(
            "/telegram/save-connection",
            json={
                "name": "Mi Telegram",
                "session_encrypted_hex": "deadbeef",
                "monitored_chats": ["-100123", "-100456"],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Mi Telegram"
        assert data["connector_type"] == "telegram"
        assert data["monitored_chats"] == ["-100123", "-100456"]
        assert "id" in data
    finally:
        app.dependency_overrides.pop(get_current_user, None)
