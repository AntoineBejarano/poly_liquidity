"""
Tests unitarios para match resolution (tip parseado → PS3838 eventId/lineId).
"""
import pytest

from app.core.ps3838.match_resolution import resolve_tip_to_ps3838, _normalize_team_name, _similarity


class TestNormalizeTeamName:
    """Tests para _normalize_team_name."""

    def test_lowercase_and_strip(self):
        assert _normalize_team_name("  Real Madrid  ") == "real madrid"

    def test_removes_extra_spaces(self):
        assert _normalize_team_name("Real   Madrid") == "real madrid"

    def test_empty_returns_empty(self):
        assert _normalize_team_name("") == ""
        assert _normalize_team_name(None) == ""


class TestSimilarity:
    """Tests para _similarity."""

    def test_identical_returns_one(self):
        assert _similarity("Real Madrid", "Real Madrid") == 1.0

    def test_similar_returns_high(self):
        assert _similarity("Real Madrid", "real madrid") >= 0.9

    def test_different_returns_low(self):
        assert _similarity("Barcelona", "Real Madrid") < 0.5


class TestResolveTipToPs3838:
    """Tests para resolve_tip_to_ps3838."""

    def test_empty_parsed_tip_returns_unmatched(self):
        out = resolve_tip_to_ps3838({}, [{"id": 1, "homeTeamName": "A", "awayTeamName": "B"}], [])
        assert out["matched"] is False
        assert out["confidence"] == 0.0
        assert out["ps3838_event_id"] is None

    def test_partido_vs_splits_to_home_away(self):
        fixtures = [
            {"id": 10, "homeTeamName": "Real Madrid", "awayTeamName": "Barcelona", "leagueId": 1},
        ]
        out = resolve_tip_to_ps3838(
            {"partido": "Real Madrid vs Barcelona"},
            fixtures,
            [],
            min_confidence=0.5,
        )
        assert out["matched"] is True
        assert out["ps3838_event_id"] == 10
        assert out["ps3838_league_id"] == 1
        assert out["confidence"] >= 0.5

    def test_home_away_explicit(self):
        fixtures = [
            {"id": 20, "homeTeamName": "Atletico Madrid", "awayTeamName": "Sevilla"},
        ]
        out = resolve_tip_to_ps3838(
            {"home": "Atletico Madrid", "away": "Sevilla"},
            fixtures,
            [],
            min_confidence=0.5,
        )
        assert out["matched"] is True
        assert out["ps3838_event_id"] == 20

    def test_below_min_confidence_returns_unmatched(self):
        fixtures = [
            {"id": 30, "homeTeamName": "Team A", "awayTeamName": "Team B"},
        ]
        out = resolve_tip_to_ps3838(
            {"partido": "Unknown X vs Unknown Y"},
            fixtures,
            [],
            min_confidence=0.9,
        )
        assert out["matched"] is False
