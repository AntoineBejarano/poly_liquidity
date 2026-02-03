"""
Phase 4: Auto-attach seguro — límites y dry-run.

- PUT/GET universe aceptan y devuelven max_events_per_strategy, max_auto_attaches_per_hour, auto_attach_dry_run.
- DirectoryService.get_events_eligible_for_universe aplica enabled global y deny_list.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from fastapi.testclient import TestClient

from app.main import app
from app.api.auth import User, get_current_user, get_admin_user
from app.models.user_sync import UserSync
from app.models.user import UserMetadata
from app.models.strategy import Strategy
from app.models.market import Market
from app.models.event import Event
from app.models.market_enabled_state import MarketEnabledState
from app.core.directory.service import DirectoryService


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock de autenticación para tests Phase 4."""
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


@pytest.fixture
def strategy_with_empty_universe(db_session):
    """Estrategia con universe_config vacío."""
    s = Strategy(
        name="Phase4 Test Strategy",
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
    """Market habilitado (enabled global)."""
    m = Market(
        polymarket_id="phase4-market-enabled",
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


class TestUniversePhase4Fields:
    """PUT acepta y GET devuelve max_events_per_strategy, max_auto_attaches_per_hour, auto_attach_dry_run."""

    def test_put_universe_accepts_phase4_limits_and_dry_run(
        self, client, strategy_with_empty_universe, market_enabled
    ):
        """PUT con límites y dry_run devuelve 200 y persiste."""
        put_body = {
            "categories": [],
            "markets": [market_enabled.polymarket_id],
            "tags": [],
            "events": [],
            "time_filter": None,
            "auto_attach": True,
            "deny_list": [],
            "max_events_per_strategy": 30,
            "max_auto_attaches_per_hour": 5,
            "auto_attach_dry_run": True,
        }
        response = client.put(
            f"/api/strategies/{strategy_with_empty_universe.id}/universe",
            json=put_body,
        )
        assert response.status_code == 200

    def test_get_universe_returns_phase4_fields_when_set(
        self, client, strategy_with_empty_universe, market_enabled
    ):
        """Tras PUT con Phase 4 fields, GET devuelve los mismos valores."""
        put_body = {
            "categories": [],
            "markets": [market_enabled.polymarket_id],
            "tags": [],
            "events": [],
            "time_filter": None,
            "auto_attach": True,
            "deny_list": [],
            "max_events_per_strategy": 25,
            "max_auto_attaches_per_hour": 3,
            "auto_attach_dry_run": True,
        }
        client.put(
            f"/api/strategies/{strategy_with_empty_universe.id}/universe",
            json=put_body,
        )
        response = client.get(f"/api/strategies/{strategy_with_empty_universe.id}/universe")
        assert response.status_code == 200
        u = response.json()["universe"]
        assert u.get("max_events_per_strategy") == 25
        assert u.get("max_auto_attaches_per_hour") == 3
        assert u.get("auto_attach_dry_run") is True


class TestDirectoryEligibleForUniverse:
    """DirectoryService.get_events_eligible_for_universe aplica enabled global y deny_list."""

    def test_get_events_eligible_returns_only_from_enabled_markets(
        self, db_session, market_enabled
    ):
        """Solo devuelve eventos cuyo market está enabled global."""
        m_disabled = Market(
            polymarket_id="phase4-market-disabled",
            name="Disabled",
            category="crypto",
            enabled=False,
        )
        db_session.add(m_disabled)
        db_session.commit()
        db_session.refresh(m_disabled)
        db_session.add(MarketEnabledState(polymarket_market_id=m_disabled.polymarket_id, enabled=False))
        db_session.commit()

        now = datetime.now(timezone.utc)
        e_enabled = Event(
            polymarket_event_id="phase4-e1",
            market_id=market_enabled.id,
            start_time=now,
            end_time=now + timedelta(hours=1),
            state="ACTIVE",
        )
        e_disabled = Event(
            polymarket_event_id="phase4-e2",
            market_id=m_disabled.id,
            start_time=now,
            end_time=now + timedelta(hours=1),
            state="ACTIVE",
        )
        db_session.add(e_enabled)
        db_session.add(e_disabled)
        db_session.commit()

        universe = {"categories": ["crypto"], "markets": [], "tags": [], "events": [], "deny_list": []}
        result = DirectoryService.get_events_eligible_for_universe(db_session, universe, limit=10)
        event_ids = [e.id for e in result]
        assert e_enabled.id in event_ids
        assert e_disabled.id not in event_ids

    def test_get_events_eligible_respects_deny_list(
        self, db_session, market_enabled
    ):
        """Excluye eventos en deny_list (por event_id o market)."""
        now = datetime.now(timezone.utc)
        e1 = Event(
            polymarket_event_id="phase4-deny-e1",
            market_id=market_enabled.id,
            start_time=now,
            end_time=now + timedelta(hours=1),
            state="ACTIVE",
        )
        db_session.add(e1)
        db_session.commit()
        db_session.refresh(e1)

        universe = {
            "categories": ["crypto"],
            "markets": [],
            "tags": [],
            "events": [],
            "deny_list": [str(e1.id)],
        }
        result = DirectoryService.get_events_eligible_for_universe(db_session, universe, limit=10)
        assert e1.id not in [e.id for e in result]
