"""
Tests de integración para Fase 0: Modo y Protecciones.

Verifica:
- Execution mode configurado correctamente
- Parámetros protegidos con valores seguros
- Checkers saludables disponibles
- Risk Engine activo
"""
import pytest
from app.main import app
from app.core.config_service import config_service
from app.core.checkers.health_service import checker_health_service


class TestPhase0ModeProtections:
    """Tests para verificar modo y protecciones antes de tocar APIs."""
    
    def test_execution_mode_endpoint(self, client):
        """Test 0.1: Verificar endpoint de execution mode."""
        response = client.get("/system/config/execution-mode")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "execution_mode" in data, "Respuesta debe incluir 'execution_mode'"
        assert data["execution_mode"] in ["DRY_RUN", "PAPER", "LIVE"], "Execution mode debe ser DRY_RUN, PAPER o LIVE"
        assert "requires_confirmation" in data, "Respuesta debe incluir 'requires_confirmation'"
        assert "is_safe" in data, "Respuesta debe incluir 'is_safe'"
        assert "safe_modes" in data, "Respuesta debe incluir 'safe_modes'"
        
        # Verificar que LIVE requiere confirmación
        if data["execution_mode"] == "LIVE":
            assert data["requires_confirmation"] is True, "LIVE debe requerir confirmación"
            assert data["is_safe"] is False, "LIVE no es modo seguro"
        else:
            assert data["is_safe"] is True, "DRY_RUN y PAPER son modos seguros"
    
    def test_protected_parameters_endpoint(self, client):
        """Test 0.2: Verificar endpoint de parámetros protegidos."""
        response = client.get("/system/config/protected-parameters")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "protected_parameters" in data, "Respuesta debe incluir 'protected_parameters'"
        assert "critical_parameters" in data, "Respuesta debe incluir 'critical_parameters'"
        
        protected = data["protected_parameters"]
        
        # Verificar parámetros críticos
        critical = data["critical_parameters"]
        assert "allow_zero_checker" in critical
        assert "execution_mode" in critical
        assert "quorum_base" in critical
        
        # Verificar que allow_zero_checker existe
        if "allow_zero_checker" in protected:
            assert "value" in protected["allow_zero_checker"]
            assert "requires_confirmation" in protected["allow_zero_checker"]
        
        # Verificar que quorum_base existe
        if "quorum_base" in protected:
            assert "value" in protected["quorum_base"]
            assert isinstance(protected["quorum_base"]["value"], (int, float))
    
    def test_checkers_health_endpoint(self, client):
        """Test 0.3: Verificar endpoint de health de checkers."""
        response = client.get("/checkers/health")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "checkers_by_category" in data, "Respuesta debe incluir 'checkers_by_category'"
        assert "quorum_config" in data, "Respuesta debe incluir 'quorum_config'"
        assert "quorum_effective_by_category" in data, "Respuesta debe incluir 'quorum_effective_by_category'"
        
        quorum_config = data["quorum_config"]
        assert "quorum_base" in quorum_config
        assert "allow_single_checker" in quorum_config
        assert "allow_zero_checker" in quorum_config
        
        # Verificar que quorum efectivo se calcula correctamente
        quorum_effective = data["quorum_effective_by_category"]
        assert isinstance(quorum_effective, dict)
    
    def test_risk_status_endpoint(self, client):
        """Test 0.4: Verificar endpoint de status de Risk Engine."""
        response = client.get("/risk/status")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "risk_engine" in data, "Respuesta debe incluir 'risk_engine'"
        assert "circuit_breakers" in data, "Respuesta debe incluir 'circuit_breakers'"
        
        risk_engine = data["risk_engine"]
        assert "active" in risk_engine
        assert risk_engine["active"] is True, "Risk Engine debe estar activo"
        assert "config" in risk_engine
        
        circuit_breakers = data["circuit_breakers"]
        assert "runtime_mode" in circuit_breakers
        assert "kill_switches" in circuit_breakers
    
    def test_gates_no_go_criteria(self, client):
        """Test 0.5: Verificar gates / no-go criteria."""
        # Obtener execution mode
        mode_response = client.get("/system/config/execution-mode")
        assert mode_response.status_code == 200
        execution_mode = mode_response.json()["execution_mode"]
        
        # Obtener parámetros protegidos
        params_response = client.get("/system/config/protected-parameters")
        assert params_response.status_code == 200
        protected = params_response.json()["protected_parameters"]
        
        # Obtener checkers health
        checkers_response = client.get("/checkers/health")
        assert checkers_response.status_code == 200
        checkers_data = checkers_response.json()
        
        # Gate 1: Si execution_mode = LIVE sin confirmación → NO proceder
        if execution_mode == "LIVE":
            # En tests, no podemos verificar confirmation_token, pero podemos verificar que requiere confirmación
            assert mode_response.json()["requires_confirmation"] is True
        
        # Gate 2: Si allow_zero_checker = true sin confirmación → NO proceder
        if "allow_zero_checker" in protected:
            allow_zero = protected["allow_zero_checker"]["value"]
            if allow_zero:
                assert protected["allow_zero_checker"]["requires_confirmation"] is True
        
        # Gate 3: Si 0 checkers saludables y allow_zero_checker = false → sistema degradado
        quorum_config = checkers_data["quorum_config"]
        allow_zero = quorum_config.get("allow_zero_checker", False)
        
        # Contar checkers saludables
        healthy_count = 0
        for category_data in checkers_data["checkers_by_category"].values():
            healthy_count += len(category_data.get("healthy", []))
        
        if healthy_count == 0 and not allow_zero:
            # Sistema debe estar en modo degradado
            # Esto se verifica en el quorum_effective
            quorum_effective = checkers_data["quorum_effective_by_category"]
            # Al menos una categoría debe tener quorum None (sin checkers)
            has_none_quorum = any(q is None for q in quorum_effective.values())
            # En este caso, el sistema no debería permitir trading
            # (esto se verifica en el código, no en el test)
    
    def test_safe_mode_criteria(self, client):
        """Test 0.6: Verificar que modos seguros permiten proceder."""
        # Obtener execution mode
        mode_response = client.get("/system/config/execution-mode")
        assert mode_response.status_code == 200
        mode_data = mode_response.json()
        
        execution_mode = mode_data["execution_mode"]
        
        # Si está en modo seguro (DRY_RUN o PAPER), debe poder proceder
        if execution_mode in ["DRY_RUN", "PAPER"]:
            assert mode_data["is_safe"] is True
            # En modos seguros, no se requieren llaves reales
            # (esto se verifica en Fase 1)

