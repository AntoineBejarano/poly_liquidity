"""
Match Resolution PS3838 Node - Resuelve tip parseado a evento/línea PS3838.

Support Graph. Lee context.parsed_tip (o config) y context.ps3838_data (fixtures, odds);
escribe context.match_resolution_result con eventId, lineId, odds, confidence.
"""
import logging
from typing import Any, Dict

from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult, FailureResult
from app.core.ps3838.match_resolution import resolve_tip_to_ps3838

logger = logging.getLogger(__name__)


class MatchResolutionPs3838Node(GraphNode):
    """
    Nodo que resuelve un tip parseado al evento y línea de PS3838 (fuzzy match).
    Config: parsed_tip (opcional; si no está, usa context.parsed_tip), min_confidence.
    Requiere context.ps3838_data con "ps3838_fixtures" y opcionalmente "ps3838_odds".
    """

    async def execute(self) -> Any:
        parsed_tip = self.config.get("parsed_tip")
        if not parsed_tip and hasattr(self.context, "parsed_tip"):
            parsed_tip = self.context.parsed_tip
        if not parsed_tip:
            return FailureResult("parsed_tip is required in config or context")
        ps3838_data = getattr(self.context, "ps3838_data", None) or {}
        fixtures = ps3838_data.get("ps3838_fixtures") or ps3838_data.get("fixtures")
        if isinstance(fixtures, dict) and "fixtures" in fixtures:
            fixtures = fixtures["fixtures"]
        if not fixtures:
            return FailureResult("No fixtures in context.ps3838_data (run fetch_ps3838_fixtures first)")
        odds = ps3838_data.get("ps3838_odds") or ps3838_data.get("odds")
        if isinstance(odds, dict) and "odds" in odds:
            odds = odds["odds"]
        if not odds:
            odds = []
        min_confidence = self.config.get("min_confidence", 0.5)
        result = resolve_tip_to_ps3838(
            parsed_tip=parsed_tip,
            fixtures=fixtures,
            odds=odds,
            min_confidence=min_confidence,
        )
        if not hasattr(self.context, "ps3838_data"):
            self.context.ps3838_data = {}
        self.context.ps3838_data["match_resolution"] = result
        if hasattr(self.context, "match_resolution_result"):
            self.context.match_resolution_result = result
        return SuccessResult()
