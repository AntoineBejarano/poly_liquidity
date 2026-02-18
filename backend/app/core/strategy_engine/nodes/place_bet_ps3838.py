"""
Place Bet PS3838 Node - Coloca una apuesta en PS3838 (Bets API).

Execution Graph (cold path). Config: source_id, y payload de apuesta (o desde context).
"""
import logging
from typing import Any, Dict
from uuid import UUID

from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult, FailureResult
from app.core.connectors.registry import connector_registry
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class PlaceBetPs3838Node(GraphNode):
    """
    Nodo que coloca una apuesta en PS3838 (Place Bet, Bets API).
    Config: source_id (requerido), payload (opcional; si no está, se usa context.tip_intent o context.bet_payload).
    """

    async def execute(self) -> Any:
        source_id_str = self.config.get("source_id")
        if not source_id_str:
            return FailureResult("source_id is required")
        try:
            source_id = UUID(source_id_str)
        except ValueError:
            return FailureResult(f"Invalid source_id format: {source_id_str}")
        payload = self.config.get("payload")
        if not payload and hasattr(self.context, "bet_payload"):
            payload = self.context.bet_payload
        if not payload and hasattr(self.context, "tip_intent"):
            # Mapear TipIntent a payload de Place Bet si hace falta
            payload = getattr(self.context.tip_intent, "place_bet_payload", None)
        if not payload:
            return FailureResult("No bet payload in config or context")
        db = SessionLocal()
        try:
            connector = connector_registry.get_connector_from_db(db, source_id)
        except Exception as e:
            db.close()
            logger.error("Error getting PS3838 connector for source %s: %s", source_id, e)
            return FailureResult(f"Error getting connector: {str(e)}")
        finally:
            db.close()
        if connector.connector_type != "ps3838":
            return FailureResult(f"Source {source_id} is not a PS3838 connector")
        try:
            result = await connector.fetch("/v1/bets", params=payload, method="POST")
        except Exception as e:
            logger.error("Error placing PS3838 bet: %s", e)
            return FailureResult(f"Error placing bet: {str(e)}")
        if not hasattr(self.context, "ps3838_data"):
            self.context.ps3838_data = {}
        self.context.ps3838_data["place_bet_response"] = result
        return SuccessResult()
