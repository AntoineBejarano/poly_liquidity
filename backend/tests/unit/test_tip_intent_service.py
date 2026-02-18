"""
Tests para tip_intent_service: create_tip_intent_from_message, resolve_tip_intent.
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.tipster.tip_intent_service import (
    create_tip_intent_from_message,
    resolve_tip_intent,
    _get_ps3838_source_id_from_strategy,
    _normalize_fixtures_response,
    _normalize_odds_response,
)
from app.models.tip_intent import TipIntent
from app.models.strategy import Strategy
from app.database import SessionLocal


class TestGetPs3838SourceId:
    def test_extracts_from_support_graphs(self):
        sid = str(uuid4())
        strategy = MagicMock(spec=Strategy)
        strategy.support_graphs = [
            {
                "nodes": {
                    "fetch_fixtures": {
                        "type": "fetch_ps3838_fixtures",
                        "config": {"source_id": sid},
                    },
                },
            },
        ]
        strategy.execution_graph = None
        assert str(_get_ps3838_source_id_from_strategy(strategy)) == sid

    def test_extracts_from_execution_graph(self):
        sid = str(uuid4())
        strategy = MagicMock(spec=Strategy)
        strategy.support_graphs = []
        strategy.execution_graph = {
            "nodes": {
                "place_bet": {
                    "type": "place_bet_ps3838",
                    "config": {"source_id": sid},
                },
            },
        }
        assert str(_get_ps3838_source_id_from_strategy(strategy)) == sid

    def test_returns_none_when_no_ps3838_node(self):
        strategy = MagicMock(spec=Strategy)
        strategy.support_graphs = [{"nodes": {"x": {"type": "noop"}}}]
        strategy.execution_graph = None
        assert _get_ps3838_source_id_from_strategy(strategy) is None


class TestNormalizeFixtures:
    def test_list_passthrough(self):
        data = [{"id": 1, "homeTeamName": "A", "awayTeamName": "B"}]
        assert _normalize_fixtures_response(data) == data

    def test_dict_with_events(self):
        data = {"events": [{"id": 2, "homeTeamName": "X", "awayTeamName": "Y", "leagueId": 10}]}
        out = _normalize_fixtures_response(data)
        assert len(out) == 1
        assert out[0]["id"] == 2 and out[0]["homeTeamName"] == "X"


class TestNormalizeOdds:
    def test_list_passthrough(self):
        data = [{"eventId": 1, "lineId": 100, "odds": 1.85}]
        assert _normalize_odds_response(data) == data

    def test_dict_with_odds_key(self):
        data = {"odds": [{"eventId": 2, "lineId": 200, "odds": 2.0}]}
        out = _normalize_odds_response(data)
        assert len(out) == 1
        assert out[0]["eventId"] == 2


class TestCreateTipIntentFromMessage:
    def test_creates_pending_with_parsed(self):
        """create_tip_intent_from_message parsea texto y crea TipIntent PENDING (requiere DB con tablas)."""
        db = SessionLocal()
        try:
            from app.models.strategy import Strategy
            try:
                strategy = db.query(Strategy).first()
            except Exception as e:
                if "no such table" in str(e).lower():
                    pytest.skip("DB tables not available in unit env")
                raise
            if not strategy:
                pytest.skip("No strategy in DB (unit env may use SQLite without migrations)")
            tip = create_tip_intent_from_message(
                db=db,
                strategy_id=strategy.id,
                user_id=strategy.created_by or "test-user",
                raw_text="Real Madrid vs Barcelona, 1 @ 1.90, 2u",
            )
            assert tip.id is not None
            assert tip.status == "PENDING"
            assert tip.parsed is not None
            assert tip.parsed.get("partido") or "Real" in str(tip.parsed.get("partido", ""))
            db.rollback()
        finally:
            db.close()


class TestResolveTipIntent:
    @pytest.mark.asyncio
    async def test_resolve_updates_ps3838_fields_when_mock_connector(self):
        """resolve_tip_intent actualiza ps3838_* cuando el conector devuelve fixtures/odds (requiere DB)."""
        db = SessionLocal()
        try:
            from app.models.strategy import Strategy
            try:
                strategy = db.query(Strategy).first()
            except Exception as e:
                if "no such table" in str(e).lower():
                    pytest.skip("DB tables not available in unit env")
                raise
            if not strategy:
                pytest.skip("No strategy in DB")
            tip = create_tip_intent_from_message(
                db=db,
                strategy_id=strategy.id,
                user_id=strategy.created_by or "test-user",
                raw_text="Real Madrid vs Barcelona, 1 @ 1.90, 2u",
            )
            tip_id = tip.id
            fixtures = [{"id": 100, "homeTeamName": "Real Madrid", "awayTeamName": "Barcelona", "leagueId": 1}]
            odds = [{"eventId": 100, "event_id": 100, "lineId": 10, "line_id": 10, "odds": 1.92}]
            mock_conn = AsyncMock()
            mock_conn.connector_type = "ps3838"
            mock_conn.fetch = AsyncMock(side_effect=[{"events": fixtures}, {"odds": odds}])
            with patch("app.core.tipster.tip_intent_service.connector_registry") as reg:
                reg.get_connector_from_db.return_value = mock_conn
                with patch("app.core.tipster.tip_intent_service._get_ps3838_source_id_from_strategy") as get_sid:
                    get_sid.return_value = uuid4()
                    updated = await resolve_tip_intent(db, tip_id)
            assert updated.ps3838_event_id is not None
            assert updated.ps3838_league_id is not None
            db.rollback()
        except Exception as e:
            if "no such table" in str(e).lower():
                pytest.skip("DB tables not available in unit env")
            raise
        finally:
            db.close()
