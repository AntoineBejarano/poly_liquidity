"""
Tests unitarios para el nodo MatchResolutionPs3838.
"""
import pytest
from unittest.mock import MagicMock

from app.core.strategy_engine.nodes.match_resolution_ps3838 import MatchResolutionPs3838Node
from app.core.strategy_engine.nodes.base import SuccessResult, FailureResult


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.ps3838_data = {
        "ps3838_fixtures": [
            {"id": 1, "homeTeamName": "Real Madrid", "awayTeamName": "Barcelona", "leagueId": 5},
        ],
        "ps3838_odds": [],
    }
    return ctx


class TestMatchResolutionPs3838Node:
    """Tests para MatchResolutionPs3838Node."""

    @pytest.mark.asyncio
    async def test_missing_parsed_tip_returns_failure(self, mock_context):
        """Si no hay parsed_tip en config ni context, retorna FailureResult."""
        mock_context.parsed_tip = None  # MagicMock tiene parsed_tip por defecto; forzar None
        node = MatchResolutionPs3838Node(config={}, context=mock_context)
        result = await node.execute()
        assert isinstance(result, FailureResult)
        assert "parsed_tip" in result.error.lower()

    @pytest.mark.asyncio
    async def test_missing_fixtures_returns_failure(self):
        """Si no hay fixtures en context.ps3838_data, retorna FailureResult."""
        ctx = MagicMock()
        ctx.ps3838_data = {}
        node = MatchResolutionPs3838Node(
            config={"parsed_tip": {"partido": "Real vs Barça"}},
            context=ctx,
        )
        result = await node.execute()
        assert isinstance(result, FailureResult)
        assert "fixtures" in result.error.lower()

    @pytest.mark.asyncio
    async def test_success_writes_match_resolution_to_context(self, mock_context):
        """Si hay parsed_tip y fixtures, escribe match_resolution en context.ps3838_data."""
        node = MatchResolutionPs3838Node(
            config={"parsed_tip": {"partido": "Real Madrid vs Barcelona"}},
            context=mock_context,
        )
        result = await node.execute()
        assert isinstance(result, SuccessResult)
        mr = mock_context.ps3838_data.get("match_resolution")
        assert mr is not None
        assert mr["matched"] is True
        assert mr["ps3838_event_id"] == 1
