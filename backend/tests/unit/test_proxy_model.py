"""
Tests unitarios para el modelo Proxy.
"""
import pytest
from uuid import uuid4
from datetime import datetime

from app.models.proxy import Proxy


class TestProxy:
    """Tests para el modelo Proxy."""

    def test_proxy_creation(self):
        """Test que Proxy se puede crear con campos mínimos."""
        proxy = Proxy(
            name="Test Proxy",
            proxy_type="SOCKS5",
            proxy_host="127.0.0.1",
            proxy_port=1080,
            created_by="user-123",
        )
        assert proxy.name == "Test Proxy"
        assert proxy.proxy_type == "SOCKS5"
        assert proxy.proxy_host == "127.0.0.1"
        assert proxy.proxy_port == 1080
        assert proxy.created_by == "user-123"
        assert proxy.validation_status is None

    def test_proxy_with_all_fields(self):
        """Test que Proxy se puede crear con todos los campos."""
        proxy = Proxy(
            name="Full Proxy",
            proxy_type="HTTP",
            proxy_host="proxy.example.com",
            proxy_port=8080,
            proxy_username="user",
            encrypted_proxy_password=b"encrypted",
            proxy_country="ES",
            validation_status="healthy",
            validation_latency_ms=100,
            created_by="user-456",
        )
        assert proxy.name == "Full Proxy"
        assert proxy.proxy_type == "HTTP"
        assert proxy.proxy_username == "user"
        assert proxy.proxy_country == "ES"
        assert proxy.validation_status == "healthy"
        assert proxy.validation_latency_ms == 100
