"""
Secret service - provides credentials to checkers during execution.
"""
from typing import Optional, Dict
from app.database import SessionLocal
from app.models.secret import Secret


class SecretService:
    """
    Secret service to support runtime event detection, not security ceremony.
    
    Responsibilities:
    - Provide checkers with credentials during execution
    - Allow live updates from frontend
    - Cache credentials so checkers are fast
    - Avoid restarting the event engine
    """
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
    
    async def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Get a secret by name.
        Returns None if secret doesn't exist.
        Uses cache for fast access.
        """
        # Check cache first
        if secret_name in self._cache:
            return self._cache[secret_name]
        
        # Load from DB
        db = SessionLocal()
        try:
            secret = db.query(Secret).filter(Secret.name == secret_name).first()
            if secret is None:
                return None
            
            # Cache it
            self._cache[secret_name] = secret.value
            return secret.value
        finally:
            db.close()
    
    async def set_secret(self, secret_name: str, value: str):
        """
        Set or update a secret.
        Invalidates cache for that secret.
        """
        db = SessionLocal()
        try:
            secret = db.query(Secret).filter(Secret.name == secret_name).first()
            if secret:
                secret.value = value
            else:
                secret = Secret(name=secret_name, value=value)
                db.add(secret)
            
            db.commit()
            
            # Update cache
            self._cache[secret_name] = value
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    
    async def delete_secret(self, secret_name: str):
        """Delete a secret and remove from cache."""
        db = SessionLocal()
        try:
            secret = db.query(Secret).filter(Secret.name == secret_name).first()
            if secret:
                db.delete(secret)
                db.commit()
            
            # Remove from cache
            if secret_name in self._cache:
                del self._cache[secret_name]
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    
    def invalidate_cache(self, secret_name: Optional[str] = None):
        """
        Invalidate cache for a specific secret or all secrets.
        If secret_name is None, clears entire cache.
        """
        if secret_name is None:
            self._cache.clear()
        elif secret_name in self._cache:
            del self._cache[secret_name]


# Global secret service instance
secret_service = SecretService()

