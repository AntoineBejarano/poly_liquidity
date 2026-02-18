"""
Eventos L2 para TipIntents: Redis pub/sub + WebSocket.

- notify_tip_intent_event: publica en Redis (desde listener o API) para que el API haga broadcast.
- start_tip_intent_subscriber: tarea en background en el API que escucha Redis y hace broadcast_strategy_event.
"""
import asyncio
import json
import logging
from typing import Any, Dict
from uuid import UUID

from app.core.redis_client import redis_client
from app.settings import settings

logger = logging.getLogger(__name__)

CHANNEL_TIP_INTENTS = "tip_intents"


async def notify_tip_intent_event(strategy_id: str, event: str, payload: Dict[str, Any]) -> bool:
    """
    Publica un evento de TipIntent en Redis para que el API (suscriptor) haga broadcast por WebSocket.
    Llamar desde el listener (tras crear un tip) o desde cualquier proceso que quiera notificar.
    """
    message = json.dumps({
        "strategy_id": str(strategy_id),
        "event": event,
        "payload": payload,
    })
    return await redis_client.publish(CHANNEL_TIP_INTENTS, message)


async def start_tip_intent_subscriber() -> None:
    """
    Suscriptor Redis que escucha el canal tip_intents y hace broadcast a WebSocket por estrategia.
    Ejecutar como tarea en background en el lifespan del FastAPI app (solo con Redis TCP).
    """
    if not getattr(settings, "redis_url", None):
        logger.debug("tip_intent_events: Redis no configurado, subscriber no iniciado")
        return
    try:
        import redis.asyncio as redis
    except ImportError:
        logger.debug("tip_intent_events: redis no instalado, subscriber no iniciado")
        return

    from app.api.websocket import broadcast_strategy_event

    try:
        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        pubsub = client.pubsub()
        await pubsub.subscribe(CHANNEL_TIP_INTENTS)
        logger.info("TipIntent L2 subscriber started on channel %s", CHANNEL_TIP_INTENTS)
    except Exception as e:
        logger.warning("TipIntent L2 subscriber could not start: %s", e)
        return

    try:
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is None:
                    continue
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                if not data:
                    continue
                try:
                    body = json.loads(data) if isinstance(data, str) else data
                except json.JSONDecodeError:
                    continue
                strategy_id_s = body.get("strategy_id")
                event = body.get("event")
                payload = body.get("payload") or {}
                if not strategy_id_s or not event:
                    continue
                try:
                    strategy_id = UUID(strategy_id_s)
                except (ValueError, TypeError):
                    continue
                try:
                    await broadcast_strategy_event(strategy_id, f"tip_intent_{event}", payload)
                except Exception as e:
                    logger.warning("broadcast_strategy_event failed: %s", e)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("TipIntent subscriber loop error: %s", e)
                await asyncio.sleep(2)
    finally:
        await pubsub.unsubscribe(CHANNEL_TIP_INTENTS)
        await pubsub.close()
        await client.aclose()
        logger.info("TipIntent L2 subscriber stopped")
