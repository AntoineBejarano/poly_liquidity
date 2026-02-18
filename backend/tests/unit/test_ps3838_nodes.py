"""
Tests unitarios para nodos PS3838 (fetch_ps3838_fixtures, fetch_ps3838_odds, place_bet_ps3838).
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.strategy_engine.nodes.fetch_ps3838_fixtures import FetchPs3838FixturesNode
from app.core.strategy_engine.nodes.fetch_ps3838_odds import FetchPs3838OddsNode
from app.core.strategy_engine.nodes.place_bet_ps3838 import PlaceBetPs3838Node
from app.core.strategy_engine.nodes.base import SuccessResult, FailureResult


@pytest.fixture
def mock_context():
    """Contexto de ejecución mínimo."""
    ctx = MagicMock()
    ctx.ps3838_data = {}
    return ctx


class TestFetchPs3838FixturesNode:
    """Tests para FetchPs3838FixturesNode."""

    @pytest.mark.asyncio
    async def test_missing_source_id_returns_failure(self, mock_context):
        """Si falta source_id, retorna FailureResult."""
        node = FetchPs3838FixturesNode(config={}, context=mock_context)
        result = await node.execute()
        assert isinstance(result, FailureResult)
        assert "source_id" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_source_id_returns_failure(self, mock_context):
        """Si source_id no es UUID válido, retorna FailureResult."""
        node = FetchPs3838FixturesNode(config={"source_id": "not-a-uuid"}, context=mock_context)
        result = await node.execute()
        assert isinstance(result, FailureResult)

    @pytest.mark.asyncio
    async def test_success_stores_fixtures_in_context(self, mock_context):
        """Si el conector devuelve datos, se guardan en context.ps3838_data."""
        source_id = uuid4()
        mock_connector = MagicMock()
        mock_connector.connector_type = "ps3838"
        mock_connector.fetch = AsyncMock(return_value={"fixtures": [{"id": 1}]})
        mock_db = MagicMock()
        with patch("app.core.strategy_engine.nodes.fetch_ps3838_fixtures.connector_registry") as reg:
            reg.get_connector_from_db = MagicMock(return_value=mock_connector)
            with patch("app.core.strategy_engine.nodes.fetch_ps3838_fixtures.SessionLocal", return_value=mock_db):
                node = FetchPs3838FixturesNode(
                    config={"source_id": str(source_id)},
                    context=mock_context,
                )
                result = await node.execute()
        assert isinstance(result, SuccessResult)
        assert getattr(mock_context, "ps3838_data", {}).get("ps3838_fixtures") == {"fixtures": [{"id": 1}]}


class TestFetchPs3838OddsNode:
    """Tests para FetchPs3838OddsNode."""

    @pytest.mark.asyncio
    async def test_missing_source_id_returns_failure(self, mock_context):
        """Si falta source_id, retorna FailureResult."""
        node = FetchPs3838OddsNode(config={}, context=mock_context)
        result = await node.execute()
        assert isinstance(result, FailureResult)
        assert "source_id" in result.error.lower()


class TestPlaceBetPs3838Node:
    """Tests para PlaceBetPs3838Node."""

    @pytest.mark.asyncio
    async def test_missing_source_id_returns_failure(self, mock_context):
        """Si falta source_id, retorna FailureResult."""
        node = PlaceBetPs3838Node(config={}, context=mock_context)
        result = await node.execute()
        assert isinstance(result, FailureResult)
        assert "source_id" in result.error.lower()

    @pytest.mark.asyncio
    async def test_missing_payload_returns_failure(self, mock_context):
        """Si no hay payload en config ni en context, retorna FailureResult."""
        source_id = uuid4()
        # Asegurar que context no tiene bet_payload ni tip_intent (MagicMock los tiene por defecto)
        mock_context.bet_payload = None
        if hasattr(mock_context, "tip_intent"):
            mock_context.tip_intent = None
        node = PlaceBetPs3838Node(
            config={"source_id": str(source_id)},
            context=mock_context,
        )
        result = await node.execute()
        assert isinstance(result, FailureResult)
        assert "payload" in result.error.lower()
