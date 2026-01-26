"""
Unit tests for Wallet Service.
"""
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from cryptography.fernet import Fernet
from app.core.wallet import WalletService, WalletInMemory
from app.models.wallet import Wallet


class TestWalletService:
    """Test cases for Wallet Service."""
    
    def test_wallet_service_initialization(self):
        """Test wallet service initializes correctly."""
        service = WalletService()
        assert service._active_wallet_cache is None
        assert service._encryption_key is not None
        assert service._cipher is not None
    
    def test_load_encryption_key_from_env(self):
        """Test loading encryption key from environment."""
        test_key = Fernet.generate_key()
        
        with patch.dict("os.environ", {"WALLET_ENCRYPTION_KEY": test_key.decode()}):
            service = WalletService()
            assert service._encryption_key == test_key.encode() if isinstance(test_key, str) else test_key
    
    def test_load_encryption_key_generates_new(self):
        """Test generating new encryption key if not in environment."""
        with patch.dict("os.environ", {}, clear=True):
            service = WalletService()
            assert service._encryption_key is not None
            assert service._cipher is not None
    
    def test_get_active_wallet_no_wallet(self, db_session):
        """Test getting active wallet when none exists."""
        service = WalletService()
        
        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            wallet = service.get_active_wallet()
        
        assert wallet is None
    
    def test_get_active_wallet_with_wallet(self, db_session):
        """Test getting active wallet when one exists."""
        service = WalletService()
        
        # Create a wallet in database
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
        
        # Set encryption key in service
        service._encryption_key = encryption_key
        service._cipher = cipher
        
        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            wallet_data = service.get_active_wallet()
        
        assert wallet_data is not None
        assert isinstance(wallet_data, WalletInMemory)
        assert wallet_data.id == wallet_id
        assert wallet_data.address == wallet.address
        assert wallet_data.private_key == "0x" + "1" * 64
    
    def test_get_active_wallet_uses_cache(self, db_session):
        """Test that get_active_wallet uses cache."""
        service = WalletService()
        
        # Set cache
        from datetime import datetime
        cached_wallet = WalletInMemory(
            id=uuid4(),
            label="Cached Wallet",
            address="0x1234567890123456789012345678901234567890",
            private_key="0x" + "1" * 64,
            loaded_at=datetime.utcnow()
        )
        service._active_wallet_cache = cached_wallet
        
        wallet_data = service.get_active_wallet()
        
        # Should return cached wallet without querying DB
        assert wallet_data == cached_wallet
    
    def test_set_active_wallet_success(self, db_session):
        """Test setting active wallet successfully."""
        service = WalletService()
        
        # Create two wallets
        wallet1_id = uuid4()
        wallet2_id = uuid4()
        
        wallet1 = Wallet(
            id=wallet1_id,
            label="Wallet 1",
            address="0x1111111111111111111111111111111111111111",
            encrypted_private_key=b"encrypted1",
            active=True,
        )
        wallet2 = Wallet(
            id=wallet2_id,
            label="Wallet 2",
            address="0x2222222222222222222222222222222222222222",
            encrypted_private_key=b"encrypted2",
            active=False,
        )
        db_session.add(wallet1)
        db_session.add(wallet2)
        db_session.commit()
        
        # Mock SessionLocal to return our test session
        # SessionLocal is a sessionmaker, so we need to mock it to return db_session when called
        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            result = service.set_active_wallet(wallet2_id, cancel_open_orders=False)
        
        assert result is True
        
        # Query fresh from database to get updated state
        wallet1_updated = db_session.query(Wallet).filter(Wallet.id == wallet1_id).first()
        wallet2_updated = db_session.query(Wallet).filter(Wallet.id == wallet2_id).first()
        
        # Verify wallet2 is now active
        assert wallet2_updated.active is True
        
        # Verify wallet1 is no longer active
        assert wallet1_updated.active is False
        
        # Verify cache is invalidated
        assert service._active_wallet_cache is None
    
    def test_set_active_wallet_invalid_id(self, db_session):
        """Test setting active wallet with invalid ID."""
        service = WalletService()
        
        invalid_id = uuid4()
        
        with patch("app.core.wallet.SessionLocal", return_value=db_session):
            result = service.set_active_wallet(invalid_id, cancel_open_orders=False)
        
        assert result is False
    
    def test_invalidate_cache(self):
        """Test invalidating cache."""
        service = WalletService()
        from datetime import datetime
        service._active_wallet_cache = WalletInMemory(
            id=uuid4(),
            label="Test",
            address="0x123",
            private_key="0x" + "1" * 64,
            loaded_at=datetime.utcnow()
        )
        
        service.invalidate_cache()
        
        assert service._active_wallet_cache is None
    
    def test_has_active_wallet_true(self, db_session):
        """Test has_active_wallet returns True when wallet exists."""
        service = WalletService()
        
        # Create active wallet
        wallet = Wallet(
            id=uuid4(),
            label="Test Wallet",
            address="0x1234567890123456789012345678901234567890",
            encrypted_private_key=b"encrypted",
            active=True,
        )
        db_session.add(wallet)
        db_session.commit()
        
        # Mock get_active_wallet to return wallet
        from datetime import datetime
        service.get_active_wallet = Mock(return_value=WalletInMemory(
            id=wallet.id,
            label=wallet.label,
            address=wallet.address,
            private_key="0x" + "1" * 64,
            loaded_at=datetime.utcnow()
        ))
        
        assert service.has_active_wallet() is True
    
    def test_has_active_wallet_false(self):
        """Test has_active_wallet returns False when no wallet exists."""
        service = WalletService()
        service.get_active_wallet = Mock(return_value=None)
        
        assert service.has_active_wallet() is False

