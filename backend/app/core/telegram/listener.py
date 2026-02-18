"""
Listener Telethon: escucha NewMessage en monitored_chats y crea TipIntent (PENDING).

Uso: ejecutar como worker o proceso largo.
  run_telegram_listener(strategy_id, telegram_source_id)  # corre hasta cancelación.

Requiere: telethon, TELEGRAM_API_ID, TELEGRAM_API_HASH, WALLET_ENCRYPTION_KEY.
"""
import asyncio
import logging
from typing import Set
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.telegram.service import decrypt_session
from app.core.tipster.message import process_telegram_message
from app.core.tipster.tip_intent_service import create_tip_intent_from_message
from app.database import SessionLocal
from app.models.external_data_source import ExternalDataSource
from app.models.strategy import Strategy

logger = logging.getLogger(__name__)

# Dedup por (chat_id, message_id) para ventana reciente (evitar duplicados por reintentos)
_seen_message_ids: Set[tuple] = set()
_MAX_SEEN = 5000


def _make_key(chat_id: int, message_id: int) -> tuple:
    return (chat_id, message_id)


def _was_seen(chat_id: int, message_id: int) -> bool:
    k = _make_key(chat_id, message_id)
    if k in _seen_message_ids:
        return True
    if len(_seen_message_ids) >= _MAX_SEEN:
        _seen_message_ids.clear()
    _seen_message_ids.add(k)
    return False


async def run_telegram_listener(strategy_id: UUID, telegram_source_id: UUID) -> None:
    """
    Conecta a Telegram con la fuente indicada y escucha mensajes en monitored_chats.
    Por cada mensaje nuevo: parse (texto o imagen) y crea TipIntent PENDING para la estrategia.
    Corre hasta que se cancele la tarea o haya error fatal.
    """
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon import events
    except ImportError:
        raise RuntimeError("telethon not installed; pip install telethon")

    db = SessionLocal()
    try:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")
        source = db.query(ExternalDataSource).filter(
            ExternalDataSource.id == telegram_source_id,
            ExternalDataSource.connector_type == "telegram",
            ExternalDataSource.created_by == strategy.created_by,
        ).first()
        if not source:
            raise ValueError(f"Telegram source {telegram_source_id} not found or not owned by strategy owner")
        config = source.connector_config or {}
        session_hex = config.get("session_encrypted_hex")
        monitored = config.get("monitored_chats") or []
        if not session_hex:
            raise ValueError("Telegram source has no session_encrypted_hex")
        monitored_ids = [int(c) for c in monitored if str(c).lstrip("-").isdigit()]
        if not monitored_ids:
            logger.warning("Telegram source %s has no monitored_chats; listener will not receive messages", telegram_source_id)

        encrypted = bytes.fromhex(session_hex)
        session_str = decrypt_session(encrypted)
        session = StringSession(session_str)
        import os
        api_id = int(os.getenv("TELEGRAM_API_ID", "0") or 0)
        api_hash = os.getenv("TELEGRAM_API_HASH") or ""
        client = TelegramClient(session, api_id=api_id, api_hash=api_hash)

        user_id = strategy.created_by or ""

        async def on_new_message(event) -> None:
            try:
                msg = event.message
                if _was_seen(event.chat_id, msg.id):
                    return
                raw_text = msg.text or getattr(msg, "message", None) or ""
                image_bytes: bytes | None = None
                if msg.photo:
                    try:
                        image_bytes = await msg.download_media(bytes)
                    except Exception as e:
                        logger.warning("Could not download photo: %s", e)
                db = SessionLocal()
                try:
                    tip = create_tip_intent_from_message(
                        db=db,
                        strategy_id=strategy_id,
                        user_id=user_id,
                        telegram_message_id=str(msg.id),
                        telegram_chat_id=str(event.chat_id),
                        raw_text=raw_text or None,
                        image_bytes=image_bytes,
                        caption=raw_text or None,
                    )
                    logger.info("TipIntent created for strategy %s message %s", strategy_id, msg.id)
                    try:
                        from app.core.tipster.tip_intent_events import notify_tip_intent_event
                        await notify_tip_intent_event(
                            str(strategy_id),
                            "created",
                            {"tip_id": str(tip.id), "status": tip.status},
                        )
                    except Exception as e:
                        logger.debug("Could not notify tip_intent event (Redis?): %s", e)
                finally:
                    db.close()
            except Exception as e:
                logger.exception("Error processing Telegram message: %s", e)

        client.add_event_handler(
            on_new_message,
            events.NewMessage(chats=monitored_ids if monitored_ids else None),
        )

        await client.start()
        logger.info("Telegram listener started for strategy %s source %s", strategy_id, telegram_source_id)
        await client.run_until_disconnected()
    finally:
        db.close()


def run_telegram_listener_sync(strategy_id: str, telegram_source_id: str) -> None:
    """Versión síncrona: ejecuta el listener en un loop de asyncio."""
    asyncio.run(run_telegram_listener(UUID(strategy_id), UUID(telegram_source_id)))
