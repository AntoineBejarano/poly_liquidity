"""
Tests unitarios para TelegramConnectionService y encriptación de sesión.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

try:
    import telethon  # noqa: F401
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False

from app.core.telegram.service import encrypt_session, decrypt_session, TelegramConnectionService


class TestEncryptDecryptSession:
    """Tests para encrypt_session y decrypt_session."""

    def test_encrypt_decrypt_roundtrip(self):
        from cryptography.fernet import Fernet
        import os
        key = Fernet.generate_key()
        with patch.dict(os.environ, {"WALLET_ENCRYPTION_KEY": key.decode()}, clear=False):
            encrypted = encrypt_session("my_session_string")
            assert encrypted != b"my_session_string"
            decrypted = decrypt_session(encrypted)
            assert decrypted == "my_session_string"


class TestTelegramConnectionService:
    """Tests para TelegramConnectionService con Telethon mockeado."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not TELETHON_AVAILABLE, reason="telethon not installed")
    async def test_send_code_request_returns_phone_code_hash(self):
        with patch("telethon.TelegramClient") as mock_tc:
            mock_client = MagicMock()
            mock_client.connect = AsyncMock()
            mock_client.is_user_authorized = AsyncMock(return_value=False)
            mock_client.send_code_request = AsyncMock(return_value=MagicMock(phone_code_hash="abc123"))
            mock_client.disconnect = AsyncMock()
            mock_tc.return_value = mock_client
            with patch.dict("os.environ", {"TELEGRAM_API_ID": "1", "TELEGRAM_API_HASH": "hash"}, clear=False):
                svc = TelegramConnectionService()
                out = await svc.send_code_request("+34600000000")
                assert out.get("phone_code_hash") == "abc123"

    @pytest.mark.asyncio
    @pytest.mark.skipif(not TELETHON_AVAILABLE, reason="telethon not installed")
    async def test_sign_in_returns_session_encrypted(self):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        with patch("telethon.TelegramClient") as mock_tc:
            mock_client = MagicMock()
            mock_client.connect = AsyncMock()
            mock_client.sign_in = AsyncMock()
            mock_client.is_user_authorized = AsyncMock(return_value=True)
            mock_client.disconnect = AsyncMock()
            mock_tc.return_value = mock_client
            with patch("telethon.sessions.StringSession") as mock_session:
                mock_session.return_value.save.return_value = "session_string_123"
                with patch.dict("os.environ", {"TELEGRAM_API_ID": "1", "TELEGRAM_API_HASH": "h", "WALLET_ENCRYPTION_KEY": key}, clear=False):
                    svc = TelegramConnectionService()
                    out = await svc.sign_in("+34", "12345", "hash")
                    assert out.get("ok") is True
                    assert "session_encrypted" in out
                    assert isinstance(out["session_encrypted"], str)
                    # Debe ser hex
                    import binascii
                    binascii.unhexlify(out["session_encrypted"])
