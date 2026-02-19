"""
Listener Telethon: escucha NewMessage en monitored_chats y crea TipIntent (PENDING).

Uso: ejecutar como worker o proceso largo.
  run_telegram_listener(strategy_id, telegram_source_id)  # corre hasta cancelación.

Requiere: telethon, TELEGRAM_API_ID, TELEGRAM_API_HASH, WALLET_ENCRYPTION_KEY.

Filtros: connector_config puede tener chat_filters: { "chat_id": { "include_regex"?, "exclude_regex"? } }.
Solo se procesan mensajes que pasen los filtros (evita paja y gasto de Vision).
"""
import asyncio
import logging
import re
from typing import Any, Callable, Dict, Optional, Set
from uuid import UUID

from sqlalchemy.orm import Session

from datetime import date, datetime, timezone

from app.core.proxy_service import proxy_service
from app.core.telegram.service import decrypt_session
from app.core.tipster.message import process_telegram_message
from app.core.tipster.tip_intent_service import create_tip_intent_from_message
from app.database import SessionLocal
from app.models.external_data_source import ExternalDataSource
from app.models.strategy import Strategy
from app.models.tip_intent import TipIntent

logger = logging.getLogger(__name__)

# Dedup por (chat_id, message_id) para ventana reciente (evitar duplicados por reintentos)
_seen_message_ids: Set[tuple] = set()
_MAX_SEEN = 5000


def _build_telethon_proxy(proxy_config: Dict[str, Any]) -> tuple:
    """
    Convierte la config del proxy_service al formato que Telethon espera.
    Telethon: ("socks5", host, port) o ("socks5", host, port, True, username, password).
    MTProto: ("mtproxy", host, port).
    """
    pt = (proxy_config.get("proxy_type") or "SOCKS5").upper()
    host = proxy_config.get("host", "")
    port = int(proxy_config.get("port", 0))
    username = proxy_config.get("username")
    password = proxy_config.get("password")
    if pt == "MTPROTO":
        return (pt.lower(), host, port)
    auth = username and password
    if auth:
        return ("socks5", host, port, True, username, password)
    return ("socks5", host, port)


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


def _passes_message_filters(
    raw_text: str,
    chat_id: int,
    has_photo: bool,
    chat_filters: Optional[Dict[str, Dict[str, Any]]] = None,
) -> bool:
    """
    True si el mensaje pasa los filtros regex del chat.
    Si no hay filtros para ese chat, retorna True (procesar todo).
    Mensajes solo con imagen (sin texto): no se aplica include_regex (no hay texto a matchear).
    """
    if not chat_filters:
        return True
    chat_str = str(chat_id)
    filters = chat_filters.get(chat_str) or chat_filters.get(str(chat_id))
    if not filters:
        return True
    text = raw_text or ""
    include_regex = filters.get("include_regex")
    exclude_regex = filters.get("exclude_regex")
    if include_regex and text:
        try:
            if not re.search(include_regex, text, re.IGNORECASE | re.DOTALL):
                return False
        except re.error:
            logger.warning("Invalid include_regex for chat %s: %s", chat_id, include_regex)
    if exclude_regex and text:
        try:
            if re.search(exclude_regex, text, re.IGNORECASE | re.DOTALL):
                return False
        except re.error:
            logger.warning("Invalid exclude_regex for chat %s: %s", chat_id, exclude_regex)
    return True


def _passes_tipster_filters(
    raw_text: str,
    whitelist: list,
    blacklist: list,
) -> bool:
    """True si el mensaje pasa whitelist/blacklist de tipsters (regex sobre raw_text)."""
    text = raw_text or ""
    if whitelist:
        for pat in whitelist:
            try:
                if re.search(pat, text, re.IGNORECASE | re.DOTALL):
                    break
            except re.error:
                continue
        else:
            return False
    if blacklist:
        for pat in blacklist:
            try:
                if re.search(pat, text, re.IGNORECASE | re.DOTALL):
                    return False
            except re.error:
                continue
    return True


def _passes_sport_filters(raw_text: str, sport_filters: list) -> bool:
    """True si el mensaje pasa filtros de deporte/liga (substring match en raw_text)."""
    if not sport_filters:
        return True
    text = (raw_text or "").lower()
    for sport in sport_filters:
        if sport.strip().lower() in text:
            return True
    return False


async def run_telegram_listener(
    strategy_id: UUID,
    telegram_source_id: UUID,
    on_client_ready: Optional[Callable[[Any], None]] = None,
) -> None:
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
        account_proxy_id = None
        proxy_id_raw = config.get("proxy_id")
        if proxy_id_raw:
            try:
                account_proxy_id = UUID(str(proxy_id_raw))
            except (ValueError, TypeError):
                pass
        monitored = config.get("monitored_chats") or []
        conn_chat_filters = config.get("chat_filters") or {}
        rc = strategy.risk_config or {}
        strat_chat_filters = rc.get("chat_filters") or {}
        chat_filters = {**conn_chat_filters, **strat_chat_filters}
        tipster_whitelist = rc.get("tipster_whitelist_regex") or []
        tipster_blacklist = rc.get("tipster_blacklist_regex") or []
        sport_filters = rc.get("sport_filters") or []
        per_channel_limits = rc.get("per_channel_limits") or {}
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
        proxy_config = proxy_service.get_proxy_config_for_connection(
            strategy_id, "telegram", account_proxy_id=account_proxy_id, db_session=db
        )
        proxy_tuple = _build_telethon_proxy(proxy_config) if proxy_config else None
        client = TelegramClient(
            session, api_id=api_id, api_hash=api_hash, proxy=proxy_tuple
        )

        user_id = strategy.created_by or ""

        async def on_new_message(event) -> None:
            try:
                msg = event.message
                if _was_seen(event.chat_id, msg.id):
                    return
                raw_text = msg.text or getattr(msg, "message", None) or ""
                if not _passes_message_filters(raw_text, event.chat_id, bool(msg.photo), chat_filters):
                    logger.debug("Message filtered out (regex) chat=%s msg_id=%s", event.chat_id, msg.id)
                    return
                if not _passes_tipster_filters(raw_text, tipster_whitelist, tipster_blacklist):
                    logger.debug("Message filtered out (tipster) chat=%s msg_id=%s", event.chat_id, msg.id)
                    return
                if not _passes_sport_filters(raw_text, sport_filters):
                    logger.debug("Message filtered out (sport) chat=%s msg_id=%s", event.chat_id, msg.id)
                    return
                chat_str = str(event.chat_id)
                plimit = per_channel_limits.get(chat_str) or per_channel_limits.get(str(event.chat_id))
                if plimit and isinstance(plimit, dict):
                    max_per_day = plimit.get("max_tips_per_day")
                    if max_per_day is not None and int(max_per_day) > 0:
                        today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
                        db_check = SessionLocal()
                        try:
                            count = db_check.query(TipIntent).filter(
                                TipIntent.strategy_id == strategy_id,
                                TipIntent.telegram_chat_id == chat_str,
                                TipIntent.created_at >= today_start,
                            ).count()
                            if count >= int(max_per_day):
                                logger.debug("Channel %s hit max_tips_per_day (%s)", event.chat_id, max_per_day)
                                return
                        finally:
                            db_check.close()
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
        if on_client_ready:
            on_client_ready(client)
        logger.info("Telegram listener started for strategy %s source %s", strategy_id, telegram_source_id)
        await client.run_until_disconnected()
    finally:
        db.close()


def run_telegram_listener_sync(strategy_id: str, telegram_source_id: str) -> None:
    """Versión síncrona: ejecuta el listener en un loop de asyncio."""
    asyncio.run(run_telegram_listener(UUID(strategy_id), UUID(telegram_source_id)))
