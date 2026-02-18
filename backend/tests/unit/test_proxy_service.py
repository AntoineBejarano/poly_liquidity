"""
Tests unitarios para ProxyService.
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, patch
from cryptography.fernet import Fernet

from app.core.proxy_service import proxy_service, VALID_CONNECTION_KEYS


class TestProxyService:
    """Tests para ProxyService."""

    def test_valid_connection_keys(self):
        """VALID_CONNECTION_KEYS contiene las claves canónicas."""
        assert "telegram" in VALID_CONNECTION_KEYS
        assert "ps3838" in VALID_CONNECTION_KEYS
        assert "polymarket" in VALID_CONNECTION_KEYS
        assert "pinnacle" in VALID_CONNECTION_KEYS
        assert "invalid_key" not in VALID_CONNECTION_KEYS

    def test_encryption_key_loaded(self):
        """El servicio carga la clave de encriptación."""
        assert proxy_service._encryption_key is not None
        assert proxy_service._cipher is not None

    def test_encrypt_decrypt_password(self):
        """Encriptación y desencriptación de contraseña."""
        password = "secret123"
        encrypted = proxy_service._encrypt_password(password)
        assert encrypted is not None
        assert encrypted != password.encode()
        decrypted = proxy_service._decrypt_password(encrypted)
        assert decrypted == password

    def test_encrypt_empty_password_returns_none(self):
        """Contraseña vacía devuelve None."""
        assert proxy_service._encrypt_password("") is None
        assert proxy_service._encrypt_password(None) is None

    def test_decrypt_none_returns_none(self):
        """Desencriptar None devuelve None."""
        assert proxy_service._decrypt_password(None) is None

    def test_get_proxy_config_for_connection_no_proxy(self, db_session):
        """Sin proxy configurado devuelve None (cloud)."""
        from app.models.strategy import Strategy
        strategy = Strategy(
            name="No Proxy",
            decision_graph={"entry_node": "n", "nodes": {"n": {"type": "noop"}}},
            support_graphs=[],
            proxy_id=None,
            connection_proxies={},
        )
        db_session.add(strategy)
        db_session.commit()
        db_session.refresh(strategy)
        config = proxy_service.get_proxy_config_for_connection(
            strategy.id, "telegram", db_session=db_session
        )
        assert config is None

    def test_get_proxy_config_for_connection_global_proxy(self, db_session):
        """proxy_id global devuelve config."""
        from app.models.proxy import Proxy
        from app.models.strategy import Strategy
        proxy = Proxy(
            name="Global",
            proxy_type="SOCKS5",
            proxy_host="proxy.local",
            proxy_port=1080,
            created_by="u1",
        )
        db_session.add(proxy)
        db_session.commit()
        db_session.refresh(proxy)
        strategy = Strategy(
            name="Global Proxy",
            decision_graph={"entry_node": "n", "nodes": {"n": {"type": "noop"}}},
            support_graphs=[],
            proxy_id=proxy.id,
            connection_proxies={},
        )
        db_session.add(strategy)
        db_session.commit()
        db_session.refresh(strategy)
        config = proxy_service.get_proxy_config_for_connection(
            strategy.id, "telegram", db_session=db_session
        )
        assert config is not None
        assert config["host"] == "proxy.local"
        assert config["port"] == 1080
        assert config["proxy_type"] == "SOCKS5"

    def test_get_proxy_config_for_connection_per_connection_override(self, db_session):
        """connection_proxies override prevalece sobre proxy_id."""
        from app.models.proxy import Proxy
        from app.models.strategy import Strategy
        p1 = Proxy(
            name="P1",
            proxy_type="SOCKS5",
            proxy_host="p1.local",
            proxy_port=1080,
            created_by="u1",
        )
        p2 = Proxy(
            name="P2",
            proxy_type="HTTP",
            proxy_host="p2.local",
            proxy_port=8080,
            created_by="u1",
        )
        db_session.add_all([p1, p2])
        db_session.commit()
        db_session.refresh(p1)
        db_session.refresh(p2)
        strategy = Strategy(
            name="Override",
            decision_graph={"entry_node": "n", "nodes": {"n": {"type": "noop"}}},
            support_graphs=[],
            proxy_id=p1.id,
            connection_proxies={"telegram": str(p2.id)},
        )
        db_session.add(strategy)
        db_session.commit()
        db_session.refresh(strategy)
        config_telegram = proxy_service.get_proxy_config_for_connection(
            strategy.id, "telegram", db_session=db_session
        )
        config_ps3838 = proxy_service.get_proxy_config_for_connection(
            strategy.id, "ps3838", db_session=db_session
        )
        assert config_telegram["host"] == "p2.local"  # override
        assert config_ps3838["host"] == "p1.local"   # global
