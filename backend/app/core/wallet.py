"""
Wallet service - manages wallets as operational resource.

This service manages wallets as operational signing keys for the Execution Engine.
It ensures only one wallet is active at a time, provides secure encryption/decryption,
and allows runtime rotation without system restart.
"""
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4
import os
import asyncio
from cryptography.fernet import Fernet
from pydantic import BaseModel
from app.database import SessionLocal
from app.models.wallet import Wallet


class WalletInMemory(BaseModel):
    """Wallet descifrada en memoria."""
    id: UUID
    label: str
    address: str
    private_key: str  # descifrada, solo en RAM
    loaded_at: datetime


class WalletService:
    """
    Wallet service for managing wallets as operational resource.
    Allows runtime rotation, caches active wallet, prevents invalid states.
    
    This is equivalent to a hardware key manager, but implemented in software
    with the guarantees necessary to operate hundreds of thousands of euros in volume.
    """
    
    def __init__(self):
        self._active_wallet_cache: Optional[WalletInMemory] = None
        self._active_lock = asyncio.Lock()
        self._encryption_key: Optional[bytes] = None
        self._cipher: Optional[Fernet] = None
        self._load_encryption_key()
    
    def _load_encryption_key(self):
        """
        Load encryption key from environment or generate one.
        
        In production, this should come from a secure key management system.
        """
        key = os.getenv("WALLET_ENCRYPTION_KEY")
        if key:
            # If key is provided, use it directly (should be base64 encoded Fernet key)
            try:
                # Try to use as-is (should be valid Fernet key)
                self._encryption_key = key.encode() if isinstance(key, str) else key
                # Validate it's a valid Fernet key
                Fernet(self._encryption_key)
            except Exception:
                # If it fails, generate a new one
                self._encryption_key = Fernet.generate_key()
                print("WARNING: Invalid WALLET_ENCRYPTION_KEY. Generated new key. This should be set correctly in production!")
        else:
            # For development: generate a key (should be set in production)
            # WARNING: This key should be persisted and reused, not regenerated each time
            self._encryption_key = Fernet.generate_key()
            print("WARNING: WALLET_ENCRYPTION_KEY not set. Generated new key. This should be set in production!")
        
        self._cipher = Fernet(self._encryption_key)
    
    def get_active_wallet(self) -> Optional[WalletInMemory]:
        """
        Get the active wallet (address + decrypted private key).
        
        Prioridad:
        1. Variables de entorno (PRIVATE_KEY, FUNDER_ADDRESS) - Para producción con Polymarket
        2. Base de datos (wallets table) - Para desarrollo/testing
        
        Returns:
            WalletInMemory: Wallet activa con private key descifrada
            None: Si no hay wallet activa
        """
        # Check cache first (fast path)
        if self._active_wallet_cache is not None:
            return self._active_wallet_cache
        
        # Prioridad 1: Intentar usar variables de entorno (producción)
        from app.settings import settings
        if settings.private_key:
            # Usar PRIVATE_KEY desde variables de entorno
            address = settings.funder_address or settings.polymarket_proxy_address
            if not address:
                print("WARNING: PRIVATE_KEY configurado pero falta FUNDER_ADDRESS o POLYMARKET_PROXY_ADDRESS")
                # Intentar derivar address desde private_key
                try:
                    from eth_account import Account
                    account = Account.from_key(settings.private_key)
                    address = account.address
                except Exception as e:
                    print(f"ERROR: No se pudo derivar address desde PRIVATE_KEY: {e}")
                    return None
            
            self._active_wallet_cache = WalletInMemory(
                id=uuid4(),  # ID temporal para wallets de env
                label="Wallet from ENV",
                address=address,
                private_key=settings.private_key,
                loaded_at=datetime.utcnow()
            )
            return self._active_wallet_cache
        
        # Prioridad 2: Cargar desde base de datos (desarrollo/testing)
        db = SessionLocal()
        try:
            wallet = db.query(Wallet).filter(Wallet.active == True).first()
            if wallet is None:
                return None
            
            # Decrypt private key
            try:
                decrypted_key = self._cipher.decrypt(wallet.encrypted_private_key).decode()
            except Exception as e:
                # If decryption fails, this is a critical error
                # In production, this should trigger a fail-safe
                print(f"ERROR: Cannot decrypt wallet private key: {e}")
                return None
            
            # Build WalletInMemory
            self._active_wallet_cache = WalletInMemory(
                id=wallet.id,
                label=wallet.label,
                address=wallet.address,
                private_key=decrypted_key,
                loaded_at=datetime.utcnow()
            )
            
            return self._active_wallet_cache
        finally:
            db.close()
    
    async def get_active_wallet_async(self) -> Optional[WalletInMemory]:
        """
        Async version of get_active_wallet with lock protection.
        Use this when you need thread-safe access.
        """
        async with self._active_lock:
            return self.get_active_wallet()
    
    def set_active_wallet(self, wallet_id: UUID, cancel_open_orders: bool = True) -> bool:
        """
        Change the active wallet.
        - Invalidates cache
        - Cancels open orders if requested
        - Only one wallet can be active (invariant)
        - Requires explicit confirmation (handled by API endpoint)
        
        Args:
            wallet_id: ID de la wallet a activar
            cancel_open_orders: Si True, cancela órdenes abiertas antes de cambiar
        
        Returns:
            True if successful, False otherwise
        """
        db = SessionLocal()
        try:
            # Get the wallet to activate
            new_wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
            if new_wallet is None:
                return False
            
            # Deactivate current active wallet (atomic operation)
            db.query(Wallet).filter(Wallet.active == True).update({"active": False})
            
            # Activate new wallet
            new_wallet.active = True
            db.commit()
            
            # Invalidate cache (critical: must happen after commit)
            self._active_wallet_cache = None
            
            # Cancel open orders if requested
            # Note: This is handled by the API endpoint that calls this method
            # to ensure proper async execution
            
            return True
        except Exception as e:
            db.rollback()
            print(f"ERROR: Failed to set active wallet: {e}")
            return False
        finally:
            db.close()
    
    def create_wallet(self, label: str, address: str, private_key: str) -> Wallet:
        """
        Create a new wallet encrypting the private key.
        
        Args:
            label: Etiqueta descriptiva
            address: Dirección pública de la wallet
            private_key: Private key en texto plano (se cifra antes de guardar)
        
        Returns:
            Wallet: Wallet creada
        
        Raises:
            ValueError: Si la wallet ya existe o hay error de cifrado
        """
        db = SessionLocal()
        try:
            # Check if address already exists
            existing = db.query(Wallet).filter(Wallet.address == address).first()
            if existing:
                raise ValueError(f"Wallet with address {address} already exists")
            
            # Encrypt private key
            try:
                encrypted_key = self._cipher.encrypt(private_key.encode())
            except Exception as e:
                raise ValueError(f"Failed to encrypt private key: {e}")
            
            # Create wallet
            wallet = Wallet(
                label=label,
                address=address,
                encrypted_private_key=encrypted_key,
                active=False,  # New wallets are inactive by default
            )
            
            db.add(wallet)
            db.commit()
            db.refresh(wallet)
            
            return wallet
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    
    def list_wallets(self) -> List[Wallet]:
        """
        List all wallets (without revealing private keys).
        
        Returns:
            List[Wallet]: Lista de wallets
        """
        db = SessionLocal()
        try:
            wallets = db.query(Wallet).all()
            return wallets
        finally:
            db.close()
    
    def decrypt_private_key(self, encrypted_key: bytes) -> str:
        """
        Decrypt a private key.
        
        Args:
            encrypted_key: Private key cifrada
        
        Returns:
            str: Private key descifrada
        
        Raises:
            ValueError: Si el descifrado falla
        """
        try:
            decrypted = self._cipher.decrypt(encrypted_key).decode()
            return decrypted
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
    
    def invalidate_cache(self):
        """Invalidate the active wallet cache."""
        self._active_wallet_cache = None
    
    def has_active_wallet(self) -> bool:
        """Check if there is an active wallet."""
        wallet = self.get_active_wallet()
        return wallet is not None


# Global wallet service instance
wallet_service = WalletService()
