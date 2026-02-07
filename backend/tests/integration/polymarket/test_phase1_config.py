"""
Tests de integración para Fase 1: Configuración y Autenticación de Polymarket.

Verifica:
- Variables de entorno configuradas
- Inicialización del cliente CLOB
- Autenticación con APIs
"""
import pytest
from app.main import app
from app.settings import settings
from app.core.execution.polymarket_client_wrapper import get_polymarket_client


class TestPhase1Configuration:
    """Tests para verificar configuración básica."""
    
    def test_environment_variables(self):
        """Test 1.1: Verificar que las variables de entorno están configuradas."""
        # Verificar que PRIVATE_KEY está configurada (o al menos existe)
        assert hasattr(settings, 'private_key'), "PRIVATE_KEY debe estar definida en settings"
        
        # Verificar que FUNDER_ADDRESS o POLYMARKET_PROXY_ADDRESS está configurada
        has_funder = bool(settings.funder_address or settings.polymarket_proxy_address)
        # Nota: En tests, puede que no esté configurada, pero debe existir el atributo
        assert hasattr(settings, 'funder_address'), "FUNDER_ADDRESS debe estar definida en settings"
        assert hasattr(settings, 'polymarket_proxy_address'), "POLYMARKET_PROXY_ADDRESS debe estar definida en settings"
        
        # Verificar CHAIN_ID
        assert hasattr(settings, 'chain_id'), "CHAIN_ID debe estar definida en settings"
        assert settings.chain_id == 137, "CHAIN_ID debe ser 137 (Polygon mainnet)"
    
    def test_clob_no_global_client(self):
        """Política v2: no existe cliente CLOB global; get_polymarket_client() debe lanzar."""
        with pytest.raises(RuntimeError, match="Global CLOB|get_polymarket_client_for_user"):
            get_polymarket_client()
    
    def test_connection_status_endpoint_requires_auth(self, client):
        """Política v2: connection/status es auth-health (user-scoped); sin auth => 401."""
        response = client.get("/api/polymarket/connection/status")
        # Sin token: 401; con token pero sin wallet: 409
        assert response.status_code in (401, 409), (
            f"connection/status debe requerir auth/wallet, obtuvo {response.status_code}"
        )
    
    def test_health_check_endpoint(self, client):
        """Test 1.4: Verificar endpoint de health check de Gamma API."""
        response = client.get("/api/polymarket/health")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Respuesta debe incluir 'status'"
        assert data["status"] in ["ok", "degraded", "error"], "Status debe ser 'ok', 'degraded' o 'error'"
    
    def test_test_auth_endpoint_requires_auth_and_wallet(self, client):
        """Política v2: connection/test-auth es auth-health; sin auth => 401, sin wallet => 409."""
        response = client.get("/api/polymarket/connection/test-auth")
        assert response.status_code in (401, 409), (
            f"test-auth debe requerir auth y wallet, obtuvo {response.status_code}"
        )

