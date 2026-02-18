"""
Proxy service - gestiona proxies como recurso de usuario.

Usa el mismo mecanismo de encriptación que wallets (WALLET_ENCRYPTION_KEY).
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import UUID
import os
import logging
from cryptography.fernet import Fernet

from app.database import SessionLocal
from app.models.proxy import Proxy
from app.models.strategy import Strategy
from app.settings import settings

logger = logging.getLogger(__name__)

# Connection keys canónicos (extensible según conectores)
VALID_CONNECTION_KEYS = frozenset({"telegram", "ps3838", "polymarket", "pinnacle"})


class ProxyService:
    """
    Servicio para CRUD de proxies y encriptación de contraseñas.
    """
    
    def __init__(self):
        self._encryption_key: Optional[bytes] = None
        self._cipher: Optional[Fernet] = None
        self._load_encryption_key()
    
    def _load_encryption_key(self):
        """Carga la clave de encriptación (misma que wallets). En prod: obligatoria."""
        raw = getattr(settings, "wallet_encryption_key", None) or os.getenv("WALLET_ENCRYPTION_KEY")
        key = raw.strip() if isinstance(raw, str) and raw else raw
        if isinstance(key, str) and not key:
            key = None
        env_name = getattr(settings, "environment", "development")
        if key:
            try:
                self._encryption_key = key.encode() if isinstance(key, str) else key
                if isinstance(self._encryption_key, bytes):
                    self._encryption_key = self._encryption_key.strip()
                Fernet(self._encryption_key)
            except Exception:
                if env_name == "production":
                    raise ValueError(
                        "WALLET_ENCRYPTION_KEY is invalid. Fix it or proxies/wallets cannot decrypt. "
                        "Generate: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                    )
                self._encryption_key = Fernet.generate_key()
                logger.warning("Invalid WALLET_ENCRYPTION_KEY, using generated key for proxy service")
        else:
            if env_name == "production":
                raise ValueError(
                    "WALLET_ENCRYPTION_KEY is required in production for proxy/wallet encryption. "
                    "Generate: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
            self._encryption_key = Fernet.generate_key()
            logger.info("WALLET_ENCRYPTION_KEY not set, using generated key (dev only)")
        self._cipher = Fernet(self._encryption_key)
    
    def _encrypt_password(self, password: str) -> bytes:
        if not password:
            return None
        return self._cipher.encrypt(password.encode())
    
    def _decrypt_password(self, encrypted: bytes) -> Optional[str]:
        if not encrypted:
            return None
        try:
            return self._cipher.decrypt(encrypted).decode()
        except Exception as e:
            logger.warning("Failed to decrypt proxy password: %s", e)
            return None
    
    def list_proxies(
        self,
        user_id: str,
        include_inactive: bool = False,
        status_filter: Optional[str] = None,
    ) -> List[Proxy]:
        """Lista proxies del usuario. No devuelve contraseña."""
        db = SessionLocal()
        try:
            q = db.query(Proxy).filter(Proxy.created_by == user_id)
            if status_filter:
                q = q.filter(Proxy.validation_status == status_filter)
            return q.order_by(Proxy.created_at.desc()).all()
        finally:
            db.close()
    
    def get_proxy(self, proxy_id: UUID, user_id: str) -> Optional[Proxy]:
        """Obtiene un proxy por ID (solo si pertenece al usuario)."""
        db = SessionLocal()
        try:
            return db.query(Proxy).filter(
                Proxy.id == proxy_id,
                Proxy.created_by == user_id,
            ).first()
        finally:
            db.close()
    
    def create_proxy(
        self,
        user_id: str,
        name: str,
        proxy_type: str,
        proxy_host: str,
        proxy_port: int,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
        proxy_country: Optional[str] = None,
    ) -> Proxy:
        """Crea un proxy para el usuario."""
        db = SessionLocal()
        try:
            encrypted = self._encrypt_password(proxy_password) if proxy_password else None
            proxy = Proxy(
                name=name,
                proxy_type=proxy_type or "SOCKS5",
                proxy_host=proxy_host,
                proxy_port=proxy_port,
                proxy_username=proxy_username,
                encrypted_proxy_password=encrypted,
                proxy_country=proxy_country,
                created_by=user_id,
                validation_status="unknown",
            )
            db.add(proxy)
            db.commit()
            db.refresh(proxy)
            return proxy
        finally:
            db.close()
    
    def update_proxy(
        self,
        proxy_id: UUID,
        user_id: str,
        name: Optional[str] = None,
        proxy_type: Optional[str] = None,
        proxy_host: Optional[str] = None,
        proxy_port: Optional[int] = None,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
        proxy_country: Optional[str] = None,
    ) -> Optional[Proxy]:
        """Actualiza un proxy. Solo el propietario."""
        db = SessionLocal()
        try:
            proxy = db.query(Proxy).filter(
                Proxy.id == proxy_id,
                Proxy.created_by == user_id,
            ).first()
            if not proxy:
                return None
            if name is not None:
                proxy.name = name
            if proxy_type is not None:
                proxy.proxy_type = proxy_type
            if proxy_host is not None:
                proxy.proxy_host = proxy_host
            if proxy_port is not None:
                proxy.proxy_port = proxy_port
            if proxy_username is not None:
                proxy.proxy_username = proxy_username
            if proxy_password is not None:
                proxy.encrypted_proxy_password = self._encrypt_password(proxy_password) if proxy_password else None
            if proxy_country is not None:
                proxy.proxy_country = proxy_country
            db.commit()
            db.refresh(proxy)
            return proxy
        finally:
            db.close()
    
    def delete_proxy(self, proxy_id: UUID, user_id: str) -> tuple[bool, Optional[str]]:
        """
        Elimina un proxy. No permite si está en uso por estrategias activas.
        Returns (success, error_message).
        """
        db = SessionLocal()
        try:
            proxy = db.query(Proxy).filter(
                Proxy.id == proxy_id,
                Proxy.created_by == user_id,
            ).first()
            if not proxy:
                return False, "Proxy no encontrado"
            
            in_use = self._is_proxy_in_use(db, proxy_id)
            if in_use:
                return False, "Proxy en uso por estrategia(s) activa(s)"
            
            db.delete(proxy)
            db.commit()
            return True, None
        finally:
            db.close()
    
    def _is_proxy_in_use(self, db, proxy_id: UUID) -> bool:
        """Comprueba si el proxy está referenciado por alguna estrategia activa."""
        proxy_id_str = str(proxy_id)
        # Caso 1: proxy_id directo
        if db.query(Strategy).filter(
            Strategy.is_active == True,
            Strategy.proxy_id == proxy_id,
        ).first():
            return True
        # Caso 2: connection_proxies contiene el proxy_id en algún valor
        # Para SQLite/Postgres: buscar en JSONB
        strategies = db.query(Strategy).filter(Strategy.is_active == True).all()
        for s in strategies:
            cp = s.connection_proxies or {}
            if proxy_id_str in (str(v) for v in cp.values()):
                return True
        return False
    
    def validate_proxy(self, proxy_id: UUID, user_id: str) -> tuple[bool, Optional[str], Optional[int]]:
        """
        Valida conectividad del proxy. Actualiza validation_status y validation_latency_ms.
        Intenta conexión real según proxy_type. Si falla, suele ser tipo incorrecto o credenciales.
        Returns (success, status, latency_ms).
        """
        proxy = self.get_proxy(proxy_id, user_id)
        if not proxy:
            return False, None, None

        import time
        import socket
        start = time.perf_counter()
        try:
            pw = self._decrypt_password(proxy.encrypted_proxy_password) if proxy.encrypted_proxy_password else None
            pt = (proxy.proxy_type or "SOCKS5").upper()

            if pt == "HTTP":
                ok, latency_ms = self._validate_http_proxy(
                    proxy.proxy_host, proxy.proxy_port,
                    proxy.proxy_username, pw
                )
            elif pt == "SOCKS5":
                ok, latency_ms = self._validate_socks5_proxy(
                    proxy.proxy_host, proxy.proxy_port,
                    proxy.proxy_username, pw
                )
            elif pt == "MTPROTO":
                ok, latency_ms = self._validate_mtproto_proxy(proxy.proxy_host, proxy.proxy_port)
            else:
                ok, latency_ms = self._validate_socks5_proxy(
                    proxy.proxy_host, proxy.proxy_port,
                    proxy.proxy_username, pw
                )

            status = "healthy" if ok else "unhealthy"
            if not ok:
                latency_ms = None

            db = SessionLocal()
            try:
                p = db.query(Proxy).filter(Proxy.id == proxy_id).first()
                if p:
                    p.validation_status = status
                    p.last_validation_at = datetime.now(timezone.utc)
                    p.validation_latency_ms = latency_ms
                    db.commit()
            finally:
                db.close()
            return ok, status, latency_ms

        except Exception as e:
            logger.warning("Proxy validation failed: %s", e)
            db = SessionLocal()
            try:
                p = db.query(Proxy).filter(Proxy.id == proxy_id).first()
                if p:
                    p.validation_status = "unhealthy"
                    p.last_validation_at = datetime.now(timezone.utc)
                    p.validation_latency_ms = None
                    db.commit()
            finally:
                db.close()
            return False, "unhealthy", None

    def _build_proxy_url(self, scheme: str, host: str, port: int, user: Optional[str], pw: Optional[str]) -> str:
        if user and pw:
            from urllib.parse import quote_plus
            auth = f"{quote_plus(user)}:{quote_plus(pw)}@"
            return f"{scheme}://{auth}{host}:{port}"
        return f"{scheme}://{host}:{port}"

    def _validate_http_proxy(
        self, host: str, port: int, user: Optional[str], pw: Optional[str]
    ) -> tuple[bool, Optional[int]]:
        import time
        import httpx
        url = self._build_proxy_url("http", host, port, user, pw)
        url_safe = url.split("@")[-1] if "@" in url else url
        start = time.perf_counter()
        try:
            with httpx.Client(proxy=url, timeout=15.0) as client:
                r = client.get("https://httpbin.org/ip")
                r.raise_for_status()
            ms = max(1, int((time.perf_counter() - start) * 1000))
            logger.info("HTTP proxy validation OK: %s -> %dms", url_safe, ms)
            return True, ms
        except Exception as e:
            logger.warning("HTTP proxy validation failed %s: %s", url_safe, e)
            return False, None

    def _validate_socks5_proxy(
        self, host: str, port: int, user: Optional[str], pw: Optional[str]
    ) -> tuple[bool, Optional[int]]:
        import time
        import httpx
        url = self._build_proxy_url("socks5", host, port, user, pw)
        # Omitir contraseña en logs
        url_safe = url.split("@")[-1] if "@" in url else url
        start = time.perf_counter()
        try:
            with httpx.Client(proxy=url, timeout=15.0) as client:
                r = client.get("https://httpbin.org/ip")
                r.raise_for_status()
            ms = max(1, int((time.perf_counter() - start) * 1000))  # mín 1ms para indicar validación real
            logger.info("SOCKS5 proxy validation OK: %s -> %dms", url_safe, ms)
            return True, ms
        except Exception as e:
            logger.warning("SOCKS5 proxy validation failed %s: %s", url_safe, e)
            return False, None

    def _validate_mtproto_proxy(self, host: str, port: int) -> tuple[bool, Optional[int]]:
        """MTProto: verifica que el host:puerto sea alcanzable (TCP connect)."""
        import time
        import socket
        start = time.perf_counter()
        try:
            s = socket.create_connection((host, port), timeout=10)
            s.close()
            ms = max(1, int((time.perf_counter() - start) * 1000))
            logger.info("MTProto proxy TCP OK: %s:%s -> %dms", host, port, ms)
            return True, ms
        except Exception as e:
            logger.warning("MTProto proxy TCP check failed %s:%s: %s", host, port, e)
            return False, None
    
    def get_proxy_config_for_connection(
        self,
        strategy_id: UUID,
        connection_key: str,
        db_session=None,
    ) -> Optional[Dict[str, Any]]:
        """
        Resuelve la config de proxy para una conexión.
        Precedencia: connection_proxies[connection_key] -> proxy_id -> None (cloud).
        Si proxy borrado o corrupto: log y devuelve None (cloud fallback).
        """
        from app.models.strategy import Strategy
        db = db_session or SessionLocal()
        try:
            strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
            if not strategy:
                return None
            
            proxy_id = None
            cp = strategy.connection_proxies if strategy.connection_proxies is not None else {}
            if isinstance(cp, dict) and connection_key in cp:
                val = cp[connection_key]
                proxy_id = UUID(str(val)) if val else None
            if proxy_id is None and strategy.proxy_id:
                proxy_id = strategy.proxy_id
            
            if proxy_id is None:
                return None
            
            proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
            if not proxy:
                logger.warning("Proxy %s not found (strategy %s, connection %s), using cloud",
                    proxy_id, strategy_id, connection_key)
                return None
            if not proxy.proxy_host or not proxy.proxy_port:
                logger.warning("Proxy %s missing host/port (strategy %s), using cloud",
                    proxy_id, strategy_id)
                return None
            
            password = self._decrypt_password(proxy.encrypted_proxy_password) if proxy.encrypted_proxy_password else None
            auth = (proxy.proxy_username, password) if proxy.proxy_username and password else None
            return {
                "proxy_type": proxy.proxy_type or "SOCKS5",
                "host": proxy.proxy_host,
                "port": proxy.proxy_port,
                "username": proxy.proxy_username,
                "password": password,
                "auth": auth,
            }
        except Exception as e:
            logger.warning("Failed to resolve proxy for strategy %s connection %s: %s",
                strategy_id, connection_key, e)
            return None
        finally:
            if db_session is None:
                db.close()


proxy_service = ProxyService()
