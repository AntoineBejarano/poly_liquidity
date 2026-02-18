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


class TelegramFloodError(Exception):
    """Telegram rate limit (PHONE_NUMBER_FLOOD, FloodWait). retry_after_seconds indica cuánto esperar."""

    def __init__(self, message: str, retry_after_seconds: int):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


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
        Returns: {"phone_code_hash": "...", "session_pending_hex": "..."}.
        session_pending DEBE usarse en sign_in: el phone_code_hash está ligado a esa sesión.
        Raises TelegramFloodError si Telegram aplica rate limit (PHONE_NUMBER_FLOOD / FloodWait).
        """
        try:
            from telethon import TelegramClient, errors
            from telethon.sessions import StringSession
        except ImportError:
            raise RuntimeError("telethon not installed; pip install telethon")
        api_id_raw = os.getenv("TELEGRAM_API_ID", "0") or "0"
        api_hash = (os.getenv("TELEGRAM_API_HASH") or "").strip()
        if not api_id_raw or api_id_raw == "0" or not api_hash:
            raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in environment (create an app at my.telegram.org)")
        session = StringSession()
        client = TelegramClient(session, api_id=int(api_id_raw), api_hash=api_hash)
        await client.connect()
        try:
            if not await client.is_user_authorized():
                try:
                    sent = await client.send_code_request(phone)
                except (errors.FloodWaitError, errors.FloodTestPhoneWaitError) as e:
                    secs = getattr(e, "seconds", 60)
                    raise TelegramFloodError(
                        "Demasiadas solicitudes de código. Telegram limita los intentos por número.",
                        retry_after_seconds=max(secs, 60),
                    ) from e
                except errors.RPCError as e:
                    msg = str(e).lower()
                    if "phone_number_flood" in msg or "too many" in msg or "flood" in msg:
                        # PHONE_NUMBER_FLOOD no devuelve retry_after; usamos 1h por seguridad
                        raise TelegramFloodError(
                            "Has pedido el código demasiadas veces. Espera al menos 1 hora antes de intentar de nuevo.",
                            retry_after_seconds=3600,
                        ) from e
                    raise
                session_str = session.save()
                encrypted = encrypt_session(session_str)
                return {"phone_code_hash": sent.phone_code_hash, "session_pending_hex": encrypted.hex()}
        finally:
            if client.is_connected():
                await client.disconnect()
        return {"phone_code_hash": None, "already_authorized": True}

    async def sign_in(
        self,
        phone: str,
        code: str,
        phone_code_hash: str,
        session_pending_hex: str,
        password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Completa el login con el código. REQUIERE session_pending_hex de send_code_request.
        El phone_code_hash solo es válido en la misma sesión que envió el código.
        """
        try:
            from telethon import TelegramClient, errors
            from telethon.sessions import StringSession
        except ImportError:
            raise RuntimeError("telethon not installed")
        encrypted = bytes.fromhex(session_pending_hex)
        session_str = decrypt_session(encrypted)
        session = StringSession(session_str)
        api_id = int(os.getenv("TELEGRAM_API_ID", "0") or 0)
        api_hash = os.getenv("TELEGRAM_API_HASH") or ""
        client = TelegramClient(session, api_id=api_id, api_hash=api_hash)
        await client.connect()
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            if password and not await client.is_user_authorized():
                await client.sign_in(password=password)
        except errors.PhoneCodeExpiredError:
            await client.disconnect()
            raise ValueError("El código ha expirado. Solicita uno nuevo con «Solicitar nuevo código».") from None
        except errors.PhoneCodeInvalidError:
            await client.disconnect()
            raise ValueError("Código incorrecto. Verifica el número de 5 dígitos.") from None
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
