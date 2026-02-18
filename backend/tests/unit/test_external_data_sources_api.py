"""
Tests unitarios para la API de External Data Sources (filtro por connector_type).
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.models.external_data_source import ExternalDataSource


@pytest.fixture
def mock_current_user():
    """Usuario autenticado para tests."""
    user = Mock()
    user.id = "test-user-123"
    user.email = "test@example.com"
    return user


@pytest.fixture
def client_with_auth(client, mock_current_user):
    """Cliente con auth mockeada."""
    from app.main import app
    from app.api.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


class TestExternalDataSourcesAPI:
    """Tests para GET /external-data-sources con filtro connector_type."""

    def test_list_returns_connector_type_in_response(self, client_with_auth, db_session, mock_current_user):
        """La respuesta incluye connector_type (no source_type)."""
        source = ExternalDataSource(
            name="Test PS3838",
            connector_type="ps3838",
            connector_config={"username": "u", "password_encrypted": "p"},
            created_by=mock_current_user.id,
        )
        db_session.add(source)
        db_session.commit()
        r = client_with_auth.get("/external-data-sources")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        item = next((x for x in data if x["name"] == "Test PS3838"), None)
        assert item is not None
        assert "connector_type" in item
        assert item["connector_type"] == "ps3838"
        assert "config" in item

    def test_list_filter_by_connector_type_ps3838(self, client_with_auth, db_session, mock_current_user):
        """Filtrar por connector_type=ps3838 devuelve solo fuentes ps3838."""
        db_session.add(
            ExternalDataSource(
                name="PS3838 One",
                connector_type="ps3838",
                connector_config={},
                created_by=mock_current_user.id,
            )
        )
        db_session.add(
            ExternalDataSource(
                name="Telegram One",
                connector_type="telegram",
                connector_config={"session_encrypted": "x", "monitored_chats": []},
                created_by=mock_current_user.id,
            )
        )
        db_session.commit()
        r = client_with_auth.get("/external-data-sources?connector_type=ps3838")
        assert r.status_code == 200
        data = r.json()
        names = [x["name"] for x in data]
        assert "PS3838 One" in names
        assert "Telegram One" not in names

    def test_list_filter_by_connector_type_telegram(self, client_with_auth, db_session, mock_current_user):
        """Filtrar por connector_type=telegram devuelve solo fuentes telegram."""
        db_session.add(
            ExternalDataSource(
                name="PS3838 One",
                connector_type="ps3838",
                connector_config={},
                created_by=mock_current_user.id,
            )
        )
        db_session.add(
            ExternalDataSource(
                name="Telegram One",
                connector_type="telegram",
                connector_config={"session_encrypted": "x", "monitored_chats": []},
                created_by=mock_current_user.id,
            )
        )
        db_session.commit()
        r = client_with_auth.get("/external-data-sources?connector_type=telegram")
        assert r.status_code == 200
        data = r.json()
        names = [x["name"] for x in data]
        assert "Telegram One" in names
        assert "PS3838 One" not in names

    def test_list_only_returns_current_user_sources(self, client_with_auth, db_session, mock_current_user):
        """Solo se devuelven fuentes con created_by del usuario actual."""
        db_session.add(
            ExternalDataSource(
                name="My PS3838",
                connector_type="ps3838",
                connector_config={},
                created_by=mock_current_user.id,
            )
        )
        db_session.add(
            ExternalDataSource(
                name="Other User Source",
                connector_type="ps3838",
                connector_config={},
                created_by="other-user-456",
            )
        )
        db_session.commit()
        r = client_with_auth.get("/external-data-sources")
        assert r.status_code == 200
        data = r.json()
        names = [x["name"] for x in data]
        assert "My PS3838" in names
        assert "Other User Source" not in names

    def test_create_external_data_source(self, client_with_auth, mock_current_user):
        """POST crea una fuente y la asocia al usuario (verifica credenciales PS3838)."""
        with patch("app.api.external_data_sources.PS3838Client") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.verify_credentials = AsyncMock()
            mock_client_cls.return_value = mock_client
            r = client_with_auth.post(
                "/external-data-sources",
                json={
                    "name": "Mi PS3838",
                    "connector_type": "ps3838",
                    "connector_config": {"username": "user", "password": "secret"},
                },
            )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Mi PS3838"
        assert data["connector_type"] == "ps3838"
        assert data["config"].get("username") == "user"
        assert "id" in data

    def test_create_ps3838_rejects_invalid_credentials(self, client_with_auth, mock_current_user):
        """POST con credenciales PS3838 inválidas devuelve 400."""
        from app.core.ps3838.client import PS3838ClientError
        with patch("app.api.external_data_sources.PS3838Client") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.verify_credentials = AsyncMock(side_effect=PS3838ClientError("Usuario o contraseña incorrectos"))
            mock_client_cls.return_value = mock_client
            r = client_with_auth.post(
                "/external-data-sources",
                json={
                    "name": "Mi PS3838",
                    "connector_type": "ps3838",
                    "connector_config": {"username": "bad", "password": "wrong"},
                },
            )
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data
        assert "incorrectos" in data["detail"].lower() or "contraseña" in data["detail"].lower()
