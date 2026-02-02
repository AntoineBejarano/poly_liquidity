"""
Test funcional: poner la estrategia Near-Resolution a correr.

Flujo:
1. Compilar template liquidity_near_end → decision_graph, support_graphs, risk_config
2. Crear estrategia vía POST /api/strategies
3. Asignar evento (con asset_ids) a la estrategia
4. Activar estrategia vía POST /api/strategies/{id}/activate
5. Verificar GET /api/strategies/{id}/live-status
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.strategy import Strategy
from app.models.strategy_event import StrategyEvent
from app.models.event import Event
from app.models.market import Market

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock de autenticación para todos los tests."""
    from app.api.auth import User, get_current_user, get_admin_user
    from app.models.user_sync import UserSync
    from app.models.user import UserMetadata

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
def market(db_session):
    """Market de prueba con clobTokenIds (necesario para asset_ids en activate)."""
    market = Market(
        polymarket_id="test-market-near-res",
        name="Test Market Near Resolution",
        category="politics",
        enabled=True,
        polymarket_payload={
            "clobTokenIds": {
                "YES": "token_yes_near_123",
                "NO": "token_no_near_456",
            }
        },
    )
    db_session.add(market)
    db_session.commit()
    return market


@pytest.fixture
def event(db_session, market):
    """Evento de prueba con polymarket payload."""
    event = Event(
        polymarket_event_id="test-event-near-res",
        market_id=market.id,
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=1),
        state="ACTIVE",
        polymarket_payload={
            "clobTokenIds": {
                "YES": "token_yes_near_123",
                "NO": "token_no_near_456",
            }
        },
    )
    db_session.add(event)
    db_session.commit()
    return event


class TestNearResolutionFunctional:
    """Test funcional: crear estrategia Near-Resolution, asignar evento, activar, verificar live-status."""

    def test_near_resolution_full_flow_activate_and_live_status(
        self,
        db_session,
        market,
        event,
    ):
        """
        1. Compila template liquidity_near_end.
        2. Crea estrategia con el grafo compilado.
        3. Asigna el evento a la estrategia.
        4. Activa la estrategia.
        5. Comprueba live-status.
        """
        # 1. Compilar template Near-Resolution (defaults)
        compile_body = {
            "event_finished": True,
            "external_confirmation_required": True,
            "allow_ambiguity": False,
            "price_min": 0.95,
            "price_max": 0.98,
            "max_size_per_event": 5000,
            "min_liquidity": 2000,
        }
        compile_resp = client.post(
            "/strategy-templates/liquidity_near_end/compile",
            json=compile_body,
        )
        assert compile_resp.status_code == 200, compile_resp.text
        compiled = compile_resp.json()
        assert "decision_graph" in compiled
        assert "support_graphs" in compiled
        assert "risk_config" in compiled

        # 2. Crear estrategia
        create_body = {
            "name": "Near-Resolution Test Funcional",
            "description": "Estrategia creada por test funcional",
            "decision_graph": compiled["decision_graph"],
            "support_graphs": compiled.get("support_graphs", []),
            "risk_config": compiled.get("risk_config", {}),
        }
        create_resp = client.post("/api/strategies", json=create_body)
        assert create_resp.status_code in (200, 201), create_resp.text
        strategy_data = create_resp.json()
        strategy_id = strategy_data["id"]
        assert strategy_data["is_active"] is False

        # 3. Asignar evento a la estrategia
        assign_resp = client.post(
            f"/api/strategies/{strategy_id}/events/{event.id}",
            json={},
        )
        assert assign_resp.status_code == 200, assign_resp.text

        # 4. Activar estrategia
        activate_resp = client.post(f"/api/strategies/{strategy_id}/activate")
        assert activate_resp.status_code == 200, activate_resp.text
        activated = activate_resp.json()
        assert activated["is_active"] is True

        # 5. Verificar live-status
        status_resp = client.get(f"/api/strategies/{strategy_id}/live-status")
        assert status_resp.status_code == 200, status_resp.text
        status_data = status_resp.json()
        assert "strategy_id" in status_data or "strategy" in status_data or isinstance(status_data, dict)
