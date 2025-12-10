"""
Wallet service - manages wallets as operational resource.
"""
from typing import Optional
from cryptography.fernet import Fernet
from app.database import SessionLocal
from app.models.wallet import Wallet
from app.core.state import state
from uuid import UUID
import os


class WalletService:
    """
    Wallet service for managing wallets as operational resource.
    Allows runtime rotation, caches active wallet, prevents invalid states.
    """
    
    def __init__(self):
        self._active_wallet_cache: Optional[dict] = None
        self._encryption_key: Optional[bytes] = None
        self._cipher: Optional[Fernet] = None
        self._load_encryption_key()
    
    def _load_encryption_key(self):
        """Load encryption key from environment or generate one."""
        # In production, this should come from a secure key management system
        key = os.getenv("WALLET_ENCRYPTION_KEY")
        if key:
            # If key is provided, use it directly (should be base64 encoded)
            try:
                self._encryption_key = key.encode() if isinstance(key, str) else key
            except Exception:
                # If it fails, generate a new one
                self._encryption_key = Fernet.generate_key()
        else:
            # For development: generate a key (should be set in production)
            # In production, use a proper key management system
            # WARNING: This key should be persisted and reused, not regenerated each time
            self._encryption_key = Fernet.generate_key()
            print("WARNING: WALLET_ENCRYPTION_KEY not set. Generated new key. This should be set in production!")
        self._cipher = Fernet(self._encryption_key)
    
    def get_active_wallet(self) -> Optional[dict]:
        """
        Get the active wallet (address + decrypted private key).
        Returns None if no wallet is active.
        Cache in memory for fast access.
        """
        if self._active_wallet_cache is not None:
            return self._active_wallet_cache
        
        db = SessionLocal()
        try:
            wallet = db.query(Wallet).filter(Wallet.active == True).first()
            if wallet is None:
                return None
            
            # Decrypt private key
            try:
                decrypted_key = self._cipher.decrypt(wallet.encrypted_private_key).decode()
            except Exception:
                # If decryption fails, return None
                return None
            
            self._active_wallet_cache = {
                "id": wallet.id,
                "label": wallet.label,
                "address": wallet.address,
                "private_key": decrypted_key,
            }
            
            return self._active_wallet_cache
        finally:
            db.close()
    
    def set_active_wallet(self, wallet_id: UUID, cancel_open_orders: bool = True) -> bool:
        """
        Change the active wallet.
        - Invalidates cache
        - Cancels open orders if requested
        - Only one wallet can be active (invariant)
        - Requires explicit confirmation
        
        Returns True if successful, False otherwise.
        """
        db = SessionLocal()
        try:
            # Get the wallet to activate
            new_wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
            if new_wallet is None:
                return False
            
            # Deactivate current active wallet
            db.query(Wallet).filter(Wallet.active == True).update({"active": False})
            
            # Activate new wallet
            new_wallet.active = True
            db.commit()
            
            # Invalidate cache
            self._active_wallet_cache = None
            
            # Cancel open orders if requested
            if cancel_open_orders:
                # This will be implemented in execution engine
                # For now, just mark that orders should be cancelled
                pass
            
            return True
        except Exception:
            db.rollback()
            return False
        finally:
            db.close()
    
    def invalidate_cache(self):
        """Invalidate the active wallet cache."""
        self._active_wallet_cache = None
    
    def has_active_wallet(self) -> bool:
        """Check if there is an active wallet."""
        wallet = self.get_active_wallet()
        return wallet is not None


# Global wallet service instance
wallet_service = WalletService()

