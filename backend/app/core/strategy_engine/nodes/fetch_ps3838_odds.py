"""
Fetch PS3838 Odds Node - Obtiene odds de PS3838 Lines API.

Support Graph (cold path). Config: source_id, sport_id (opcional), since (opcional).
"""
import logging
from typing import Any, Dict
from uuid import UUID

from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult, FailureResult
from app.core.connectors.registry import connector_registry
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class FetchPs3838OddsNode(GraphNode):
    """
    Nodo que obtiene odds de PS3838 (Get Odds, Lines API).
    Config: source_id (requerido), sport_id, since.
    Escribe en context.ps3838_data[output_key].
    """

    async def execute(self) -> Any:
        source_id_str = self.config.get("source_id")
        if not source_id_str:
            return FailureResult("source_id is required")
        try:
            source_id = UUID(source_id_str)
        except ValueError:
            return FailureResult(f"Invalid source_id format: {source_id_str}")
        sport_id = self.config.get("sport_id")
        since = self.config.get("since")
        output_key = self.config.get("output_key", "ps3838_odds")
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
        params: Dict[str, Any] = {}
        if sport_id is not None:
            params["sport_id"] = sport_id
        if since is not None:
            params["since"] = since
        try:
            data = await connector.fetch("/v4/odds", params=params)
        except Exception as e:
            logger.error("Error fetching PS3838 odds: %s", e)
            return FailureResult(f"Error fetching odds: {str(e)}")
        if not hasattr(self.context, "ps3838_data"):
            self.context.ps3838_data = {}
        self.context.ps3838_data[output_key] = data
        return SuccessResult()
