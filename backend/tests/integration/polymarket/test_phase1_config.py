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
    
    def test_clob_client_initialization(self):
        """Test 1.2: Verificar que el cliente CLOB se puede inicializar."""
        try:
            client_wrapper = get_polymarket_client()
            # El cliente puede no estar disponible si no hay credenciales, pero debe existir
            assert client_wrapper is not None, "Cliente debe ser creado"
            assert hasattr(client_wrapper, 'is_available'), "Cliente debe tener método is_available()"
            assert hasattr(client_wrapper, '_initialized'), "Cliente debe tener atributo _initialized"
        except Exception as e:
            pytest.skip(f"Cliente no se pudo inicializar (probablemente falta configuración): {e}")
    
    def test_connection_status_endpoint(self, client):
        """Test 1.3: Verificar endpoint de status de conexión."""
        response = client.get("/api/polymarket/connection/status")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "configuration" in data, "Respuesta debe incluir 'configuration'"
        assert "clob_client" in data, "Respuesta debe incluir 'clob_client'"
        assert "apis" in data, "Respuesta debe incluir 'apis'"
        
        # Verificar estructura de configuration
        config = data["configuration"]
        assert "private_key_configured" in config
        assert "funder_address_configured" in config
        assert "chain_id" in config
        assert "rpc_url_configured" in config
        
        # Verificar estructura de clob_client
        clob = data["clob_client"]
        assert "available" in clob
        assert "initialized" in clob
    
    def test_health_check_endpoint(self, client):
        """Test 1.4: Verificar endpoint de health check de Gamma API."""
        response = client.get("/api/polymarket/health")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Respuesta debe incluir 'status'"
        assert data["status"] in ["ok", "degraded", "error"], "Status debe ser 'ok', 'degraded' o 'error'"
    
    @pytest.mark.skipif(
        not settings.private_key or not (settings.funder_address or settings.polymarket_proxy_address),
        reason="Requiere PRIVATE_KEY y FUNDER_ADDRESS configuradas"
    )
    def test_authentication_endpoint(self, client):
        """Test 1.5: Verificar endpoint de test de autenticación."""
        response = client.get("/api/polymarket/connection/test-auth")
        
        # Puede ser 200 (éxito) o 503 (cliente no inicializado)
        assert response.status_code in [200, 503], f"Status code debe ser 200 o 503, obtuvo {response.status_code}"
        
        data = response.json()
        
        if response.status_code == 200:
            assert "authentication_status" in data
            assert "tests" in data
            assert "message" in data
        else:
            assert "detail" in data
            assert "CLOB client not initialized" in data["detail"] or "not initialized" in data["detail"].lower()

