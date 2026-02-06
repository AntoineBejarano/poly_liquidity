"""
Unit tests for Wallet Service multi-tenant (per-user wallets and polymarket config).
"""
import pytest
from unittest.mock import patch
from uuid import uuid4
from datetime import datetime, timezone
from cryptography.fernet import Fernet

from app.core.wallet import WalletService, WalletInMemory
from app.models.wallet import Wallet
from app.models.user_polymarket_config import UserPolymarketConfig
from app.settings import settings as app_settings


USER_A = "user-a-id"
USER_B = "user-b-id"


class TestWalletMultiTenant:
    """Multi-tenant: wallets and config scoped by user_id."""

    def test_list_wallets_filtered_by_user(self, db_session):
        """list_wallets(user_id) returns only that user's wallets."""
        service = WalletService()
        w_a1 = Wallet(
            id=uuid4(),
            user_id=USER_A,
            label="A1",
            address="0xa111111111111111111111111111111111111111",
            encrypted_private_key=b"enc1",
            active=False,
        )
        w_a2 = Wallet(
            id=uuid4(),
            user_id=USER_A,
            label="A2",
            address="0xa222222222222222222222222222222222222222",
            encrypted_private_key=b"enc2",
            active=True,
        )
        w_b1 = Wallet(
            id=uuid4(),
            user_id=USER_B,
            label="B1",
            address="0xb111111111111111111111111111111111111111",
            encrypted_private_key=b"enc3",
            active=False,
        )
        db_session.add_all([w_a1, w_a2, w_b1])
        db_session.commit()

        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            list_a = service.list_wallets(user_id=USER_A)
            list_b = service.list_wallets(user_id=USER_B)
            list_all = service.list_wallets(user_id=None)

        assert len(list_a) == 2
        assert {w.label for w in list_a} == {"A1", "A2"}
        assert len(list_b) == 1
        assert list_b[0].label == "B1"
        assert len(list_all) == 3

    def test_get_active_wallet_scoped_by_user(self, db_session):
        """get_active_wallet(user_id) returns only that user's active wallet."""
        service = WalletService()
        key = Fernet.generate_key()
        cipher = Fernet(key)
        enc = cipher.encrypt(b"0x" + b"1" * 64)
        addr_a = "0xa111111111111111111111111111111111111111"
        addr_b = "0xb111111111111111111111111111111111111111"

        w_a = Wallet(
            id=uuid4(),
            user_id=USER_A,
            label="A",
            address=addr_a,
            encrypted_private_key=enc,
            active=True,
        )
        w_b = Wallet(
            id=uuid4(),
            user_id=USER_B,
            label="B",
            address=addr_b,
            encrypted_private_key=enc,
            active=True,
        )
        db_session.add_all([w_a, w_b])
        db_session.commit()

        service._encryption_key = key
        service._cipher = cipher

        with patch.object(app_settings, "private_key", None), \
             patch("app.core.wallet.SessionLocal", return_value=db_session):
            active_a = service.get_active_wallet(user_id=USER_A)
            active_b = service.get_active_wallet(user_id=USER_B)

        assert active_a is not None
        assert active_a.label == "A"
        assert active_a.address == addr_a
        assert active_b is not None
        assert active_b.label == "B"
        assert active_b.address == addr_b

    def test_set_active_wallet_rejects_other_users_wallet(self, db_session):
        """set_active_wallet(..., user_id=X) returns False if wallet belongs to another user."""
        service = WalletService()
        w_b = Wallet(
            id=uuid4(),
            user_id=USER_B,
            label="B",
            address="0xb111111111111111111111111111111111111111",
            encrypted_private_key=b"enc",
            active=False,
        )
        db_session.add(w_b)
        db_session.commit()

        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            result = service.set_active_wallet(w_b.id, cancel_open_orders=False, user_id=USER_A)
        assert result is False

    def test_set_active_wallet_success_with_user_scope(self, db_session):
        """set_active_wallet with user_id only deactivates that user's wallets."""
        service = WalletService()
        enc = b"enc"
        w_a1_id = uuid4()
        w_a2_id = uuid4()
        w_b_id = uuid4()
        w_a1 = Wallet(
            id=w_a1_id,
            user_id=USER_A,
            label="A1",
            address="0xa111111111111111111111111111111111111111",
            encrypted_private_key=enc,
            active=True,
        )
        w_a2 = Wallet(
            id=w_a2_id,
            user_id=USER_A,
            label="A2",
            address="0xa222222222222222222222222222222222222222",
            encrypted_private_key=enc,
            active=False,
        )
        w_b = Wallet(
            id=w_b_id,
            user_id=USER_B,
            label="B",
            address="0xb111111111111111111111111111111111111111",
            encrypted_private_key=enc,
            active=True,
        )
        db_session.add_all([w_a1, w_a2, w_b])
        db_session.commit()

        # Prevent service from closing the test session so we can query after
        with patch("app.core.wallet.SessionLocal", return_value=db_session), \
             patch.object(db_session, "close", lambda: None):
            ok = service.set_active_wallet(w_a2_id, cancel_open_orders=False, user_id=USER_A)
        assert ok is True

        r_a1 = db_session.query(Wallet).filter(Wallet.id == w_a1_id).first()
        r_a2 = db_session.query(Wallet).filter(Wallet.id == w_a2_id).first()
        r_b = db_session.query(Wallet).filter(Wallet.id == w_b_id).first()
        assert r_a1.active is False
        assert r_a2.active is True
        assert r_b.active is True  # unchanged (other user)

    def test_create_wallet_with_user_id(self, db_session):
        """create_wallet(..., user_id=X) stores wallet for that user."""
        service = WalletService()
        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            w = service.create_wallet(
                label="My Wallet",
                address="0xcccccccccccccccccccccccccccccccccccccccc",
                private_key="0x" + "c" * 64,
                user_id=USER_A,
            )
        assert w.user_id == USER_A
        assert w.label == "My Wallet"
        assert w.active is False

    def test_same_address_allowed_for_different_users(self, db_session):
        """Same address can exist for different users (duplicate check is per user)."""
        service = WalletService()
        addr = "0xdddddddddddddddddddddddddddddddddddddddd"
        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            service.create_wallet(
                label="A Wallet",
                address=addr,
                private_key="0x" + "1" * 64,
                user_id=USER_A,
            )
            w2 = service.create_wallet(
                label="B Wallet",
                address=addr,
                private_key="0x" + "2" * 64,
                user_id=USER_B,
            )
        assert w2.user_id == USER_B
        assert w2.address == addr

    def test_get_polymarket_config_none(self, db_session):
        """get_polymarket_config returns None when user has no config."""
        service = WalletService()
        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            config = service.get_polymarket_config(USER_A)
        assert config is None

    def test_set_and_get_polymarket_config(self, db_session):
        """set_polymarket_config creates/updates; get_polymarket_config returns it."""
        service = WalletService()
        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            row = service.set_polymarket_config(
                USER_A,
                polymarket_proxy_address="0xproxy",
                api_key="key1",
                api_secret="secret1",
                api_passphrase="pass1",
            )
        assert row.user_id == USER_A
        assert row.polymarket_proxy_address == "0xproxy"
        assert row.api_key == "key1"

        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            config = service.get_polymarket_config(USER_A)
        assert config is not None
        assert config.polymarket_proxy_address == "0xproxy"
        assert config.api_key == "key1"

    def test_set_polymarket_config_partial_update(self, db_session):
        """set_polymarket_config with only some fields updates only those."""
        service = WalletService()
        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            service.set_polymarket_config(
                USER_A,
                polymarket_proxy_address="0xproxy",
                api_key="key1",
            )
            service.set_polymarket_config(USER_A, api_secret="new_secret")
        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            config = service.get_polymarket_config(USER_A)
        assert config.polymarket_proxy_address == "0xproxy"
        assert config.api_key == "key1"
        assert config.api_secret == "new_secret"

    def test_invalidate_cache_for_user(self):
        """invalidate_cache(user_id) clears only that user's cache entry."""
        service = WalletService()
        from datetime import datetime
        service._active_wallet_cache[USER_A] = WalletInMemory(
            id=uuid4(),
            label="A",
            address="0xaaa",
            private_key="0x" + "1" * 64,
            loaded_at=datetime.now(timezone.utc),
        )
        service._active_wallet_cache[USER_B] = WalletInMemory(
            id=uuid4(),
            label="B",
            address="0xbbb",
            private_key="0x" + "2" * 64,
            loaded_at=datetime.now(timezone.utc),
        )
        service.invalidate_cache(user_id=USER_A)
        assert USER_A not in service._active_wallet_cache
        assert USER_B in service._active_wallet_cache
        service.invalidate_cache(user_id=USER_B)
        assert USER_B not in service._active_wallet_cache
