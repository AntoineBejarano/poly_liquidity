"""
Additional unit tests for Wallet Service new methods.
"""
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from cryptography.fernet import Fernet
from app.core.wallet import WalletService, WalletInMemory
from app.models.wallet import Wallet


class TestWalletServiceNewMethods:
    """Test cases for new Wallet Service methods."""
    
    def test_create_wallet_success(self, db_session):
        """Test creating a wallet successfully."""
        service = WalletService()
        
        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            wallet = service.create_wallet(
                label="Test Wallet",
                address="0x1234567890123456789012345678901234567890",
                private_key="0x" + "1" * 64
            )
        
        assert wallet is not None
        assert wallet.label == "Test Wallet"
        assert wallet.address == "0x1234567890123456789012345678901234567890"
        assert wallet.active is False  # New wallets are inactive
        assert wallet.encrypted_private_key is not None
    
    def test_create_wallet_duplicate_address(self, db_session):
        """Test creating wallet with duplicate address fails."""
        service = WalletService()
        address = "0x1234567890123456789012345678901234567890"
        
        # Create first wallet
        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            service.create_wallet(
                label="Wallet 1",
                address=address,
                private_key="0x" + "1" * 64
            )
            
            # Try to create duplicate
            with pytest.raises(ValueError, match="already exists"):
                service.create_wallet(
                    label="Wallet 2",
                    address=address,
                    private_key="0x" + "2" * 64
                )
    
    def test_list_wallets(self, db_session):
        """Test listing all wallets."""
        service = WalletService()
        
        # Create some wallets
        wallet1 = Wallet(
            id=uuid4(),
            label="Wallet 1",
            address="0x1111111111111111111111111111111111111111",
            encrypted_private_key=b"encrypted1",
            active=True,
        )
        wallet2 = Wallet(
            id=uuid4(),
            label="Wallet 2",
            address="0x2222222222222222222222222222222222222222",
            encrypted_private_key=b"encrypted2",
            active=False,
        )
        db_session.add(wallet1)
        db_session.add(wallet2)
        db_session.commit()
        
        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            wallets = service.list_wallets()
        
        assert len(wallets) == 2
        assert all(isinstance(w, Wallet) for w in wallets)
    
    def test_decrypt_private_key_success(self):
        """Test decrypting private key successfully."""
        service = WalletService()
        private_key = "0x" + "1" * 64
        
        # Encrypt
        encrypted = service._cipher.encrypt(private_key.encode())
        
        # Decrypt
        decrypted = service.decrypt_private_key(encrypted)
        
        assert decrypted == private_key
    
    def test_decrypt_private_key_failure(self):
        """Test decrypting with wrong key fails."""
        service = WalletService()
        
        # Create encrypted data with different key
        other_key = Fernet.generate_key()
        other_cipher = Fernet(other_key)
        encrypted = other_cipher.encrypt(b"0x" + b"1" * 64)
        
        # Try to decrypt with wrong key
        with pytest.raises(ValueError, match="Decryption failed"):
            service.decrypt_private_key(encrypted)
    
    def test_get_active_wallet_async(self, db_session):
        """Test async version of get_active_wallet."""
        from app.settings import settings as app_settings
        service = WalletService()
        
        wallet_id = uuid4()
        encryption_key = Fernet.generate_key()
        cipher = Fernet(encryption_key)
        encrypted_key = cipher.encrypt(b"0x" + b"1" * 64)
        
        wallet = Wallet(
            id=wallet_id,
            label="Test Wallet",
            address="0x1234567890123456789012345678901234567890",
            encrypted_private_key=encrypted_key,
            active=True,
        )
        db_session.add(wallet)
        db_session.commit()
        
        service._encryption_key = encryption_key
        service._cipher = cipher
        
        import asyncio
        
        async def test_async():
            with patch.object(app_settings, "private_key", None), \
                 patch("app.core.wallet.SessionLocal", return_value=db_session):
                wallet_data = await service.get_active_wallet_async()
            
            assert wallet_data is not None
            assert isinstance(wallet_data, WalletInMemory)
            assert wallet_data.id == wallet_id
        
        asyncio.run(test_async())

    def test_get_wallet_by_id_success(self, db_session):
        """get_wallet_by_id returns decrypted wallet when it exists and user matches."""
        from datetime import datetime, timezone

        service = WalletService()
        key = Fernet.generate_key()
        cipher = Fernet(key)
        enc = cipher.encrypt(b"0x" + b"1" * 64)
        wallet_id = uuid4()
        addr = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        w = Wallet(
            id=wallet_id,
            user_id="user-1",
            label="My Wallet",
            address=addr,
            encrypted_private_key=enc,
            active=False,
        )
        db_session.add(w)
        db_session.commit()

        service._encryption_key = key
        service._cipher = cipher

        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            result = service.get_wallet_by_id(wallet_id, user_id="user-1")

        assert result is not None
        assert isinstance(result, WalletInMemory)
        assert result.id == wallet_id
        assert result.address == addr
        assert result.label == "My Wallet"
        assert result.private_key == "0x" + "1" * 64

    def test_get_wallet_by_id_not_found(self, db_session):
        """get_wallet_by_id returns None when wallet does not exist."""
        service = WalletService()
        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            result = service.get_wallet_by_id(uuid4(), user_id="user-1")
        assert result is None

    def test_get_wallet_by_id_other_user_returns_none(self, db_session):
        """get_wallet_by_id returns None when wallet belongs to another user."""
        service = WalletService()
        key = Fernet.generate_key()
        cipher = Fernet(key)
        enc = cipher.encrypt(b"0x" + b"1" * 64)
        wallet_id = uuid4()
        w = Wallet(
            id=wallet_id,
            user_id="user-B",
            label="B Wallet",
            address="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            encrypted_private_key=enc,
            active=False,
        )
        db_session.add(w)
        db_session.commit()

        service._encryption_key = key
        service._cipher = cipher

        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            result = service.get_wallet_by_id(wallet_id, user_id="user-A")
        assert result is None

    def test_get_wallet_by_id_without_user_id_returns_any(self, db_session):
        """get_wallet_by_id without user_id returns wallet if it exists (no user filter)."""
        from datetime import datetime, timezone

        service = WalletService()
        key = Fernet.generate_key()
        cipher = Fernet(key)
        enc = cipher.encrypt(b"0x" + b"2" * 64)
        wallet_id = uuid4()
        addr = "0xcccccccccccccccccccccccccccccccccccccccc"
        w = Wallet(
            id=wallet_id,
            user_id="user-X",
            label="X Wallet",
            address=addr,
            encrypted_private_key=enc,
            active=False,
        )
        db_session.add(w)
        db_session.commit()

        service._encryption_key = key
        service._cipher = cipher

        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            result = service.get_wallet_by_id(wallet_id)

        assert result is not None
        assert result.id == wallet_id
        assert result.private_key == "0x" + "2" * 64
