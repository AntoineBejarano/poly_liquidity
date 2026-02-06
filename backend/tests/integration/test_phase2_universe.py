"""
Phase 2: Universe — schema ampliado y validación enabled global.

- UniverseConfig con events[] y time_filter (window, next_days, max_time_to_resolution_minutes).
- PUT universe: 400 si se referencian markets o events no enabled global.
- GET universe: devuelve time_filter y events[].
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4
from app.main import app
from app.api.auth import User, get_current_user, get_admin_user
from app.models.user_sync import UserSync
from app.models.user import UserMetadata
from app.models.strategy import Strategy
from app.models.market import Market
from app.models.event import Event
from app.models.market_enabled_state import MarketEnabledState


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock de autenticación para tests Phase 2."""
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


# Usar el client del conftest (inyecta db_session) para que la API use la BD de test


@pytest.fixture
def strategy_with_empty_universe(db_session):
    """Estrategia con universe_config vacío."""
    s = Strategy(
        name="Phase2 Test Strategy",
        decision_graph={"nodes": [], "edges": []},
        support_graphs=[],
        control_loop_config={},
        risk_config={},
        observability_config={},
        universe_config={},
        is_active=False,
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture
def market_enabled(db_session):
    """Market habilitado (enabled global) para tests."""
    m = Market(
        polymarket_id="phase2-market-enabled",
        name="Enabled Market",
        category="crypto",
        enabled=True,
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    state = MarketEnabledState(polymarket_market_id=m.polymarket_id, enabled=True)
    db_session.add(state)
    db_session.commit()
    return m


@pytest.fixture
def market_disabled(db_session):
    """Market no habilitado (enabled global = False)."""
    m = Market(
        polymarket_id="phase2-market-disabled",
        name="Disabled Market",
        category="crypto",
        enabled=False,
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    state = MarketEnabledState(polymarket_market_id=m.polymarket_id, enabled=False)
    db_session.add(state)
    db_session.commit()
    return m


class TestUniverseGetReturnsTimeFilterAndEvents:
    """GET /api/strategies/{id}/universe devuelve time_filter y events."""

    def test_post_universe_markets_adds_market_idempotent(self, client, strategy_with_empty_universe, market_enabled):
        """Fase 4: POST universe/markets añade market; idempotente (added=false si ya existe)."""
        url = f"/api/strategies/{strategy_with_empty_universe.id}/universe/markets"
        r1 = client.post(url, json={"market_id": market_enabled.polymarket_id})
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["added"] is True
        assert market_enabled.polymarket_id in d1["universe"].get("markets", [])

        r2 = client.post(url, json={"market_id": market_enabled.polymarket_id})
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["added"] is False

    def test_post_universe_markets_400_when_disabled(self, client, strategy_with_empty_universe, market_disabled):
        """Fase 4: POST universe/markets con market disabled → 400."""
        url = f"/api/strategies/{strategy_with_empty_universe.id}/universe/markets"
        r = client.post(url, json={"market_id": market_disabled.polymarket_id})
        assert r.status_code == 400
        assert "disabled" in r.json().get("detail", "").lower()

    def test_get_universe_includes_time_filter_and_events(self, client, strategy_with_empty_universe):
        """GET universe incluye keys time_filter y events (aunque vacíos)."""
        response = client.get(f"/api/strategies/{strategy_with_empty_universe.id}/universe")
        assert response.status_code == 200
        data = response.json()
        assert "universe" in data
        u = data["universe"]
        assert "time_filter" in u
        assert "events" in u
        assert u["events"] == []
        assert u.get("time_filter") is None or isinstance(u["time_filter"], dict)

    def test_get_universe_returns_persisted_time_filter_and_events(
        self, client, db_session, strategy_with_empty_universe, market_enabled
    ):
        """Tras PUT con time_filter y events, GET devuelve los mismos valores."""
        from datetime import timedelta
        event = Event(
            polymarket_event_id="phase2-event-1",
            market_id=market_enabled.id,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            state="ACTIVE",
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        put_body = {
            "categories": [],
            "markets": [market_enabled.polymarket_id],
            "tags": [],
            "events": [str(event.id)],
            "time_filter": {"next_days": 7, "max_time_to_resolution_minutes": 60},
            "auto_attach": False,
            "deny_list": [],
        }
        response_put = client.put(
            f"/api/strategies/{strategy_with_empty_universe.id}/universe",
            json=put_body,
        )
        assert response_put.status_code == 200

        response_get = client.get(f"/api/strategies/{strategy_with_empty_universe.id}/universe")
        assert response_get.status_code == 200
        u = response_get.json()["universe"]
        assert u.get("events") == [str(event.id)]
        assert u.get("time_filter") is not None
        assert u["time_filter"].get("next_days") == 7
        assert u["time_filter"].get("max_time_to_resolution_minutes") == 60


class TestUniversePutValidatesEnabledGlobal:
    """PUT universe devuelve 400 si market o event no está enabled global."""

    def test_put_universe_with_disabled_market_returns_400(
        self, client, strategy_with_empty_universe, market_disabled
    ):
        """PUT con market_id no enabled global devuelve 400."""
        put_body = {
            "categories": [],
            "markets": [market_disabled.polymarket_id],
            "tags": [],
            "events": [],
            "auto_attach": False,
            "deny_list": [],
        }
        response = client.put(
            f"/api/strategies/{strategy_with_empty_universe.id}/universe",
            json=put_body,
        )
        assert response.status_code == 400
        assert "not enabled" in response.json().get("detail", "").lower() or "enabled" in response.json().get("detail", "")

    def test_put_universe_with_enabled_market_returns_200(
        self, client, strategy_with_empty_universe, market_enabled
    ):
        """PUT con market_id enabled global devuelve 200."""
        put_body = {
            "categories": [],
            "markets": [market_enabled.polymarket_id],
            "tags": [],
            "events": [],
            "auto_attach": False,
            "deny_list": [],
        }
        response = client.put(
            f"/api/strategies/{strategy_with_empty_universe.id}/universe",
            json=put_body,
        )
        assert response.status_code == 200

    def test_put_universe_with_event_whose_market_is_disabled_returns_400(
        self, client, db_session, strategy_with_empty_universe, market_disabled
    ):
        """PUT con event cuyo market no está enabled devuelve 400."""
        from datetime import timedelta
        event = Event(
            polymarket_event_id="phase2-event-disabled-market",
            market_id=market_disabled.id,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            state="ACTIVE",
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        put_body = {
            "categories": [],
            "markets": [],
            "tags": [],
            "events": [str(event.id)],
            "auto_attach": False,
            "deny_list": [],
        }
        response = client.put(
            f"/api/strategies/{strategy_with_empty_universe.id}/universe",
            json=put_body,
        )
        assert response.status_code == 400
