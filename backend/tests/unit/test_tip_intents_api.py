"""
Tests para API TipIntents: listar, crear, obtener, aprobar, rechazar, ejecutar.
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.api.auth import User, get_current_user


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_user():
    u = type("UserSync", (), {"id": "test-user-id", "email": "test@test.com", "name": "Test", "created_at": None, "updated_at": None})()
    return User(u)


def test_list_tip_intents_requires_auth(client):
    r = client.get(f"/strategies/{uuid4()}/tip-intents")
    assert r.status_code == 401


def test_create_tip_intent_requires_auth(client):
    r = client.post(f"/strategies/{uuid4()}/tip-intents", json={"raw_text": "Team A vs Team B, 1 @ 1.80"})
    assert r.status_code == 401


def test_get_tip_intent_requires_auth(client):
    r = client.get(f"/tip-intents/{uuid4()}")
    assert r.status_code == 401


def test_resolve_approve_reject_execute_require_auth(client):
    tid = uuid4()
    assert client.post(f"/tip-intents/{tid}/resolve").status_code == 401
    assert client.post(f"/tip-intents/{tid}/approve").status_code == 401
    assert client.post(f"/tip-intents/{tid}/reject", json={}).status_code == 401
    assert client.post(f"/tip-intents/{tid}/execute").status_code == 401


def test_list_tip_intents_with_auth_returns_404_for_unknown_strategy(client, mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        r = client.get(f"/strategies/{uuid4()}/tip-intents")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_get_tip_intent_with_auth_returns_404_for_unknown_id(client, mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        r = client.get(f"/tip-intents/{uuid4()}")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_tip_intents_summary_requires_auth(client):
    r = client.get(f"/strategies/{uuid4()}/tip-intents/summary")
    assert r.status_code == 401


def test_tip_intents_summary_with_auth_returns_404_for_unknown_strategy(client, mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        r = client.get(f"/strategies/{uuid4()}/tip-intents/summary")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)
