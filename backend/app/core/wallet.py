"""
Wallet service - manages wallets as operational resource.

This service manages wallets as operational signing keys for the Execution Engine.
Wallets and Polymarket config are scoped by user_id when provided; otherwise
legacy global/env behavior is used.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import UUID, uuid4
import os
import asyncio
from cryptography.fernet import Fernet
from pydantic import BaseModel
from app.database import SessionLocal
from app.models.wallet import Wallet
from app.models.user_polymarket_config import UserPolymarketConfig
from app.settings import settings


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
        # Cache por user_id (None = global/legacy)
        self._active_wallet_cache: Dict[Optional[str], WalletInMemory] = {}
        self._active_lock = asyncio.Lock()
        self._encryption_key: Optional[bytes] = None
        self._cipher: Optional[Fernet] = None
        self._load_encryption_key()
    
    def _load_encryption_key(self):
        """
        Load encryption key from settings (.env) or generate one.
        
        In production, this should come from a secure key management system.
        """
        raw = getattr(settings, "wallet_encryption_key", None) or os.getenv("WALLET_ENCRYPTION_KEY")
        key = raw.strip() if isinstance(raw, str) and raw else raw
        if isinstance(key, str) and not key:
            key = None
        env_name = getattr(settings, "environment", "development")
        if key:
            # If key is provided, use it directly (should be base64 encoded Fernet key)
            try:
                # Normalize: strip whitespace/newlines (common when pasting in Railway/env)
                self._encryption_key = key.encode() if isinstance(key, str) else key
                if isinstance(self._encryption_key, bytes):
                    self._encryption_key = self._encryption_key.strip()
                # Validate it's a valid Fernet key
                Fernet(self._encryption_key)
            except Exception:
                # If it fails, generate a new one
                self._encryption_key = Fernet.generate_key()
                if env_name == "production":
                    raise ValueError(
                        "WALLET_ENCRYPTION_KEY is invalid (must be a valid Fernet key, 44 chars base64). "
                        "Generate one: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
                        "Then set it in Railway Variables with no spaces or newlines."
                    )
                import logging
                logging.getLogger(__name__).warning(
                    "Invalid WALLET_ENCRYPTION_KEY. Generated new key. Set correctly in production!"
                )
        else:
            if env_name == "production":
                raise ValueError(
                    "WALLET_ENCRYPTION_KEY is required in production. "
                    "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
            # For development: generate a key (set in .env for production)
            self._encryption_key = Fernet.generate_key()
            import logging
            logging.getLogger(__name__).info(
                "WALLET_ENCRYPTION_KEY not set, using generated key. Set in .env for production."
            )
        
        self._cipher = Fernet(self._encryption_key)
    
    def get_active_wallet(self, user_id: Optional[str] = None) -> Optional[WalletInMemory]:
        """
        Obtiene la wallet activa (address + private key descifrada).

        - Si user_id está definido: solo DB, wallet activa de ese usuario (política v2).
        - Si user_id es None: se retorna None (no existe wallet global ni ENV).

        Returns:
            WalletInMemory o None si no hay wallet activa.
        """
        if user_id is None:
            return None
        cache_key = user_id
        if cache_key in self._active_wallet_cache:
            return self._active_wallet_cache[cache_key]

        db = SessionLocal()
        try:
            wallet = (
                db.query(Wallet)
                .filter(Wallet.user_id == user_id, Wallet.active == True)
                .first()
            )
            if wallet is None:
                return None
            try:
                decrypted_key = self._cipher.decrypt(wallet.encrypted_private_key).decode()
            except Exception as e:
                print(f"ERROR: Cannot decrypt wallet private key: {e}")
                return None
            w = WalletInMemory(
                id=wallet.id,
                label=wallet.label,
                address=wallet.address,
                private_key=decrypted_key,
                loaded_at=datetime.now(timezone.utc),
            )
            self._active_wallet_cache[cache_key] = w
            return w
        finally:
            db.close()
    
    async def get_active_wallet_async(self, user_id: Optional[str] = None) -> Optional[WalletInMemory]:
        """Versión async de get_active_wallet con lock. user_id opcional."""
        async with self._active_lock:
            return self.get_active_wallet(user_id=user_id)
    
    def set_active_wallet(
        self,
        wallet_id: UUID,
        cancel_open_orders: bool = True,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Activa la wallet indicada. Si user_id está definido, solo se desactivan
        wallets de ese usuario y la nueva debe ser de ese usuario.
        """
        db = SessionLocal()
        try:
            new_wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
            if new_wallet is None:
                return False
            if user_id is not None and new_wallet.user_id != user_id:
                return False
            # Desactivar la(s) activa(s) del mismo ámbito: si user_id, solo ese usuario; si no, todas
            q = db.query(Wallet).filter(Wallet.active == True)
            if user_id is not None:
                q = q.filter(Wallet.user_id == user_id)
            q.update({"active": False})
            new_wallet.active = True
            db.commit()
            self.invalidate_cache(user_id=user_id)
            return True
        except Exception as e:
            db.rollback()
            print(f"ERROR: Failed to set active wallet: {e}")
            return False
        finally:
            db.close()

    def deactivate_wallet(self, wallet_id: UUID, user_id: Optional[str] = None) -> bool:
        """
        Desactiva la wallet indicada. Solo afecta a esa wallet; no activa otra.
        Si user_id está definido, la wallet debe pertenecer a ese usuario.
        """
        db = SessionLocal()
        try:
            wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
            if wallet is None:
                return False
            if user_id is not None and wallet.user_id != user_id:
                return False
            wallet.active = False
            db.commit()
            self.invalidate_cache(user_id=user_id)
            return True
        except Exception as e:
            db.rollback()
            print(f"ERROR: Failed to deactivate wallet: {e}")
            return False
        finally:
            db.close()

    def create_wallet(
        self,
        label: str,
        address: str,
        private_key: str,
        user_id: Optional[str] = None,
    ) -> Wallet:
        """Crea una wallet cifrando la private key. Opcionalmente asociada a user_id."""
        db = SessionLocal()
        try:
            q = db.query(Wallet).filter(Wallet.address == address)
            if user_id is not None:
                q = q.filter(Wallet.user_id == user_id)
            else:
                q = q.filter(Wallet.user_id.is_(None))
            if q.first():
                raise ValueError(f"Wallet with address {address} already exists")
            try:
                encrypted_key = self._cipher.encrypt(private_key.encode())
            except Exception as e:
                raise ValueError(f"Failed to encrypt private key: {e}")
            wallet = Wallet(
                user_id=user_id,
                label=label,
                address=address,
                encrypted_private_key=encrypted_key,
                active=False,
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
    
    def list_wallets(self, user_id: Optional[str] = None) -> List[Wallet]:
        """Lista wallets (sin revelar claves). Si user_id está definido, solo las de ese usuario."""
        db = SessionLocal()
        try:
            q = db.query(Wallet)
            if user_id is not None:
                q = q.filter(Wallet.user_id == user_id)
            return q.all()
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
    
    def invalidate_cache(self, user_id: Optional[str] = None):
        """Invalida la cache de wallet activa. Si user_id es None, invalida toda."""
        if user_id is None:
            self._active_wallet_cache.clear()
        else:
            self._active_wallet_cache.pop(user_id, None)

    def has_active_wallet(self, user_id: Optional[str] = None) -> bool:
        """Comprueba si hay wallet activa (para el usuario si se indica)."""
        return self.get_active_wallet(user_id=user_id) is not None

    def get_wallet_by_id(
        self,
        wallet_id: UUID,
        user_id: Optional[str] = None,
    ) -> Optional[WalletInMemory]:
        """
        Devuelve una wallet por ID (descifrada). Si user_id está definido, solo si la wallet es de ese usuario.
        """
        db = SessionLocal()
        try:
            q = db.query(Wallet).filter(Wallet.id == wallet_id)
            if user_id is not None:
                q = q.filter(Wallet.user_id == user_id)
            wallet = q.first()
            if wallet is None:
                return None
            try:
                decrypted_key = self._cipher.decrypt(wallet.encrypted_private_key).decode()
            except Exception as e:
                print(f"ERROR: Cannot decrypt wallet private key: {e}")
                return None
            return WalletInMemory(
                id=wallet.id,
                label=wallet.label,
                address=wallet.address,
                private_key=decrypted_key,
                loaded_at=datetime.now(timezone.utc),
            )
        finally:
            db.close()

    def get_polymarket_config(self, user_id: str) -> Optional[UserPolymarketConfig]:
        """Devuelve la configuración Polymarket del usuario, o None."""
        db = SessionLocal()
        try:
            return db.query(UserPolymarketConfig).filter(UserPolymarketConfig.user_id == user_id).first()
        finally:
            db.close()

    def set_polymarket_config(
        self,
        user_id: str,
        polymarket_proxy_address: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        api_passphrase: Optional[str] = None,
    ) -> UserPolymarketConfig:
        """Crea o actualiza la configuración Polymarket del usuario. Valores None no se actualizan."""
        db = SessionLocal()
        try:
            row = db.query(UserPolymarketConfig).filter(UserPolymarketConfig.user_id == user_id).first()
            if row is None:
                row = UserPolymarketConfig(user_id=user_id)
                db.add(row)
            if polymarket_proxy_address is not None:
                row.polymarket_proxy_address = polymarket_proxy_address
            if api_key is not None:
                row.api_key = api_key
            if api_secret is not None:
                row.api_secret = api_secret
            if api_passphrase is not None:
                row.api_passphrase = api_passphrase
            db.commit()
            db.refresh(row)
            return row
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()


# Global wallet service instance
wallet_service = WalletService()
