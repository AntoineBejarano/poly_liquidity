"""
Servicio TipIntent: crear desde mensaje, resolver contra PS3838, actualizar estado.

Pipeline: mensaje → parse/Vision → (opcional) match resolution → TipIntent PENDING.
"""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.connectors.registry import connector_registry
from app.core.ps3838.match_resolution import resolve_tip_to_ps3838
from app.core.tipster.message import process_telegram_message
from app.models.tip_intent import TipIntent
from app.models.strategy import Strategy

logger = logging.getLogger(__name__)


def _get_ps3838_source_id_from_strategy(strategy: Strategy) -> Optional[UUID]:
    """Extrae ps3838 source_id de los grafos de la estrategia (support_graphs o execution_graph)."""
    for graph in (strategy.support_graphs or []):
        nodes = (graph or {}).get("nodes") or {}
        for node in nodes.values():
            if isinstance(node, dict) and node.get("type") in ("fetch_ps3838_fixtures", "fetch_ps3838_odds", "place_bet_ps3838"):
                sid = (node.get("config") or {}).get("source_id")
                if sid:
                    try:
                        return UUID(sid)
                    except (ValueError, TypeError):
                        pass
    exec_graph = strategy.execution_graph or {}
    nodes = exec_graph.get("nodes") or {}
    for node in nodes.values():
        if isinstance(node, dict) and node.get("type") in ("place_bet_ps3838", "odds_still_valid"):
            sid = (node.get("config") or {}).get("source_id")
            if sid:
                try:
                    return UUID(sid)
                except (ValueError, TypeError):
                    pass
    return None


def _normalize_fixtures_response(data: Any) -> List[Dict[str, Any]]:
    """Convierte respuesta de Get Fixtures a lista de eventos con id, homeTeamName, awayTeamName, leagueId."""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    events = data.get("events") or data.get("fixtures") or data.get("leagues")
    if isinstance(events, list):
        out = []
        for item in events:
            if isinstance(item, dict) and item.get("id") is not None:
                out.append({
                    "id": item.get("id"),
                    "homeTeamName": item.get("homeTeamName") or item.get("home") or item.get("homeTeam"),
                    "awayTeamName": item.get("awayTeamName") or item.get("away") or item.get("awayTeam"),
                    "leagueId": item.get("leagueId") or item.get("league_id"),
                })
            elif isinstance(item, dict) and "events" in item:
                out.extend(_normalize_fixtures_response(item["events"]))
        return out
    if isinstance(events, dict):
        return _normalize_fixtures_response(list(events.values()) if events else [])
    return []


def _normalize_odds_response(data: Any) -> List[Dict[str, Any]]:
    """Convierte respuesta de Get Odds a lista con eventId, lineId, odds."""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    odds_list = data.get("odds") or data.get("lines") or data.get("events")
    if isinstance(odds_list, list):
        out = []
        for item in odds_list:
            if isinstance(item, dict):
                out.append({
                    "eventId": item.get("eventId") or item.get("event_id"),
                    "event_id": item.get("eventId") or item.get("event_id"),
                    "lineId": item.get("lineId") or item.get("line_id"),
                    "line_id": item.get("lineId") or item.get("line_id"),
                    "odds": item.get("odds") or item.get("price"),
                    "price": item.get("odds") or item.get("price"),
                })
        return out
    return []


def create_tip_intent_from_message(
    db: Session,
    strategy_id: UUID,
    user_id: str,
    telegram_message_id: Optional[str] = None,
    telegram_chat_id: Optional[str] = None,
    raw_text: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    caption: Optional[str] = None,
) -> TipIntent:
    """
    Parsea el mensaje (texto o imagen) y crea un TipIntent en estado PENDING.
    No ejecuta match resolution (llamar resolve_tip_intent después si se desea).
    """
    parsed = process_telegram_message(raw_text=raw_text, image_bytes=image_bytes, caption=caption)
    tip = TipIntent(
        strategy_id=strategy_id,
        user_id=user_id,
        telegram_message_id=telegram_message_id,
        telegram_chat_id=telegram_chat_id,
        raw_text=raw_text or "",
        parsed=parsed,
        status="PENDING",
    )
    db.add(tip)
    db.commit()
    db.refresh(tip)
    return tip


async def resolve_tip_intent(db: Session, tip_intent_id: UUID) -> TipIntent:
    """
    Resuelve el tip contra PS3838: obtiene fixtures/odds de la cuenta de la estrategia,
    ejecuta match resolution y actualiza el TipIntent con ps3838_event_id, line_id, odds, etc.
    """
    tip = db.query(TipIntent).filter(TipIntent.id == tip_intent_id).first()
    if not tip:
        raise ValueError(f"TipIntent {tip_intent_id} not found")
    if not tip.parsed or tip.parsed.get("error"):
        return tip

    strategy = db.query(Strategy).filter(Strategy.id == tip.strategy_id).first()
    if not strategy:
        raise ValueError(f"Strategy {tip.strategy_id} not found")
    source_id = _get_ps3838_source_id_from_strategy(strategy)
    if not source_id:
        logger.warning("Strategy %s has no ps3838 source_id in graphs; skip resolution", strategy.id)
        return tip

    connector = connector_registry.get_connector_from_db(db, source_id)
    if connector.connector_type != "ps3838":
        raise ValueError(f"Source {source_id} is not PS3838")

    fixtures_data = await connector.fetch("/v3/fixtures", params={})
    fixtures = _normalize_fixtures_response(fixtures_data)
    if not fixtures and isinstance(fixtures_data, dict):
        leagues = fixtures_data.get("leagues") or []
        for league in (leagues if isinstance(leagues, list) else []):
            if isinstance(league, dict) and "events" in league:
                fixtures.extend(_normalize_fixtures_response(league.get("events")))

    odds_data = await connector.fetch("/v4/odds", params={})
    odds = _normalize_odds_response(odds_data)
    if not odds and isinstance(odds_data, dict):
        for key in ("events", "leagues", "odds"):
            odds = _normalize_odds_response(odds_data.get(key))
            if odds:
                break

    result = resolve_tip_to_ps3838(tip.parsed, fixtures, odds)
    tip.ps3838_event_id = result.get("ps3838_event_id")
    tip.ps3838_league_id = result.get("ps3838_league_id")
    tip.ps3838_period_number = result.get("period_number")
    tip.ps3838_line_id = str(result.get("line_id")) if result.get("line_id") is not None else None
    tip.ps3838_odds = result.get("ps3838_odds")
    if tip.parsed.get("stake") is not None:
        tip.suggested_stake_usd = tip.parsed.get("stake")
    db.commit()
    db.refresh(tip)
    return tip
