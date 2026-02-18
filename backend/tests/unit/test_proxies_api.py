"""
Tests unitarios para la API de Proxies.
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient


@pytest.fixture
def mock_current_user():
    """Usuario autenticado para tests."""
    user = Mock()
    user.id = "test-user-123"
    user.role = "admin"
    return user


@pytest.fixture
def client_with_auth(client, mock_current_user):
    """Cliente con auth mockeada."""
    from app.main import app
    from app.api.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


class TestProxiesAPI:
    """Tests para endpoints de Proxies."""

    def test_get_proxies_empty(self, client_with_auth, db_session):
        """GET /proxies devuelve lista vacía sin proxies."""
        with patch("app.api.proxies.proxy_service") as mock_svc:
            mock_svc.list_proxies.return_value = []
            r = client_with_auth.get("/proxies")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_proxy(self, client_with_auth):
        """POST /proxies crea un proxy."""
        with patch("app.api.proxies.proxy_service") as mock_svc:
            from app.models.proxy import Proxy
            mock_proxy = Mock(spec=Proxy)
            mock_proxy.id = uuid4()
            mock_proxy.name = "Test Proxy"
            mock_proxy.proxy_type = "SOCKS5"
            mock_proxy.proxy_host = "127.0.0.1"
            mock_proxy.proxy_port = 1080
            mock_proxy.proxy_country = None
            mock_proxy.validation_status = "unknown"
            mock_proxy.last_validation_at = None
            mock_proxy.validation_latency_ms = None
            mock_proxy.created_at = None
            mock_proxy.updated_at = None
            mock_svc.create_proxy.return_value = mock_proxy

            r = client_with_auth.post(
                "/proxies",
                json={
                    "name": "Test Proxy",
                    "proxy_type": "SOCKS5",
                    "proxy_host": "127.0.0.1",
                    "proxy_port": 1080,
                },
            )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Test Proxy"
        assert data["proxy_type"] == "SOCKS5"
        assert data["proxy_host"] == "127.0.0.1"
        assert data["proxy_port"] == 1080
