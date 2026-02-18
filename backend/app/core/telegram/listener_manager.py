"""
Gestiona listeners Telegram por estrategia.
Se arrancan/paran con Play/Stop de la estrategia (activate/deactivate).
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.strategy import Strategy

logger = logging.getLogger(__name__)

# { strategy_id: (holder_list, task) } - holder[0]=client para disconnect, task para cancel
_listeners: Dict[UUID, Tuple[Any, asyncio.Task]] = {}


def _get_telegram_source_id(strategy: Strategy) -> Optional[UUID]:
    """Extrae telegram_source_id del support_graph telegram_listener."""
    for graph in strategy.support_graphs or []:
        if not isinstance(graph, dict) or graph.get("name") != "telegram_listener":
            continue
        for node in (graph.get("nodes") or {}).values():
            if isinstance(node, dict) and node.get("type") == "telegram_listener":
                sid = (node.get("config") or {}).get("source_id")
                if sid:
                    try:
                        return UUID(str(sid))
                    except (ValueError, TypeError):
                        pass
        break
    return None


def get_telegram_listener_strategies(db: Session, active_only: bool = True) -> List[Tuple[UUID, UUID]]:
    """
    Devuelve (strategy_id, telegram_source_id) de estrategias que tienen
    support_graph con telegram_listener y source_id configurado.
    """
    out: List[Tuple[UUID, UUID]] = []
    q = db.query(Strategy)
    if active_only:
        q = q.filter(Strategy.is_active.is_(True))
    for s in q.all():
        source_id = _get_telegram_source_id(s)
        if source_id:
            out.append((s.id, source_id))
    return out


async def start_listener(strategy_id: UUID) -> bool:
    """
    Inicia el listener Telegram para la estrategia si tiene telegram_listener.
    Retorna True si se inició, False si la estrategia no tiene listener Telegram.
    """
    if strategy_id in _listeners:
        logger.warning("Listener ya corriendo para strategy %s", strategy_id)
        return True

    db = SessionLocal()
    try:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return False
        source_id = _get_telegram_source_id(strategy)
        if not source_id:
            return False
    finally:
        db.close()

    from app.core.telegram.listener import run_telegram_listener

    holder: List[Optional[Any]] = [None]

    def on_client_ready(client: Any) -> None:
        holder[0] = client

    async def _run() -> None:
        try:
            await run_telegram_listener(
                strategy_id, source_id, on_client_ready=on_client_ready
            )
        except asyncio.CancelledError:
            logger.info("Telegram listener cancelled for strategy %s", strategy_id)
        except Exception as e:
            logger.exception(
                "Telegram listener error for strategy %s: %s", strategy_id, e
            )
        finally:
            _listeners.pop(strategy_id, None)

    task = asyncio.create_task(_run())
    _listeners[strategy_id] = (holder, task)
    logger.info("Telegram listener started for strategy %s", strategy_id)
    return True


async def stop_listener(strategy_id: UUID) -> bool:
    """
    Para el listener Telegram de la estrategia.
    Retorna True si se paró (o ya estaba parado), False si no había listener.
    """
    entry = _listeners.pop(strategy_id, None)
    if not entry:
        return False
    client_or_holder, task = entry
    client = None
    if isinstance(client_or_holder, list):
        client = client_or_holder[0] if client_or_holder else None
    else:
        client = client_or_holder
    if client is not None:
        try:
            await client.disconnect()
        except Exception as e:
            logger.warning("Error disconnecting Telegram client: %s", e)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Telegram listener stopped for strategy %s", strategy_id)
    return True


async def stop_all_listeners() -> None:
    """Para todos los listeners (shutdown)."""
    ids = list(_listeners.keys())
    for sid in ids:
        await stop_listener(sid)


def has_listener(strategy_id: UUID) -> bool:
    """True si hay un listener activo para la estrategia."""
    return strategy_id in _listeners
