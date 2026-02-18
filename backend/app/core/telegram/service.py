"""
Servicio de conexión Telegram: send_code_request, sign_in, get_dialogs.
Sesión encriptada con Fernet (WALLET_ENCRYPTION_KEY).
"""
import logging
import os
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet

from app.settings import settings

logger = logging.getLogger(__name__)


def _get_cipher() -> Fernet:
    raw = getattr(settings, "wallet_encryption_key", None) or os.getenv("WALLET_ENCRYPTION_KEY")
    key = raw.strip() if isinstance(raw, str) and raw else raw
    if not key:
        raise ValueError("WALLET_ENCRYPTION_KEY required for Telegram session encryption")
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_session(session_str: str) -> bytes:
    """Encripta el string de sesión Telethon."""
    return _get_cipher().encrypt(session_str.encode())


def decrypt_session(encrypted: bytes) -> str:
    """Desencripta la sesión."""
    return _get_cipher().decrypt(encrypted).decode()


class TelegramConnectionService:
    """
    Flujo de conexión Telegram: send_code_request → sign_in → get_dialogs.
    Sesión se guarda encriptada en ExternalDataSource.connector_config.
    """

    async def send_code_request(self, phone: str) -> Dict[str, Any]:
        """
        Envía código de verificación al teléfono.
        Returns: {"phone_code_hash": "..."} para usar en sign_in.
        """
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except ImportError:
            raise RuntimeError("telethon not installed; pip install telethon")
        api_id_raw = os.getenv("TELEGRAM_API_ID", "0") or "0"
        api_hash = (os.getenv("TELEGRAM_API_HASH") or "").strip()
        if not api_id_raw or api_id_raw == "0" or not api_hash:
            raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in environment (create an app at my.telegram.org)")
        client = TelegramClient(StringSession(), api_id=int(api_id_raw), api_hash=api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            sent = await client.send_code_request(phone)
            return {"phone_code_hash": sent.phone_code_hash}
        await client.disconnect()
        return {"phone_code_hash": None, "already_authorized": True}

    async def sign_in(
        self,
        phone: str,
        code: str,
        phone_code_hash: str,
        password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Completa el login con el código. Devuelve session_encrypted para guardar.
        """
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except ImportError:
            raise RuntimeError("telethon not installed")
        session = StringSession()
        api_id = int(os.getenv("TELEGRAM_API_ID", "0") or 0)
        api_hash = os.getenv("TELEGRAM_API_HASH") or ""
        client = TelegramClient(session, api_id=api_id, api_hash=api_hash)
        await client.connect()
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            if password and not await client.is_user_authorized():
                await client.sign_in(password=password)
        except Exception as e:
            await client.disconnect()
            raise
        session_str = session.save()
        await client.disconnect()
        encrypted = encrypt_session(session_str)
        return {"session_encrypted": encrypted.hex(), "ok": True}

    async def get_dialogs(self, session_encrypted_hex: str) -> List[Dict[str, Any]]:
        """
        Obtiene lista de diálogos (grupos/canales) con la sesión guardada.
        session_encrypted_hex: session encriptada en hex (como se guarda en DB).
        """
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except ImportError:
            raise RuntimeError("telethon not installed")
        encrypted = bytes.fromhex(session_encrypted_hex)
        session_str = decrypt_session(encrypted)
        session = StringSession(session_str)
        api_id = int(os.getenv("TELEGRAM_API_ID", "0") or 0)
        api_hash = os.getenv("TELEGRAM_API_HASH") or ""
        client = TelegramClient(session, api_id=api_id, api_hash=api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            raise ValueError("Session not authorized; reconnect Telegram")
        try:
            dialogs = await client.get_dialogs()
            out = []
            for d in dialogs:
                if d.is_group or d.is_channel:
                    out.append({
                        "id": str(d.id),
                        "title": getattr(d, "title", None) or str(d.id),
                        "is_channel": d.is_channel,
                    })
            return out
        finally:
            await client.disconnect()
