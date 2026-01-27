"""
Smoke Tests EXTERNAL - Con Polymarket Real, Staging/Producción.

⚠️ NO ejecuta en CI (marcado con @pytest.mark.skipif(CI)).
Solo para staging/producción o ejecución manual.

**Implementación**:
- Tests en pytest: Usan TestClient(app) (sin servidor real, pero ejecutan el endpoint completo)
- Uso manual/staging: Puede llamarse directamente al endpoint /api/polymarket/smoke?mode=external
  en un servidor real (staging/producción)

Usa el endpoint /api/polymarket/smoke?mode=external para verificar:
- Pipeline health (WS + cache) aunque trading disabled
- Trading readiness (dataflow + trading permitido)
"""
import pytest
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Detectar si estamos en CI
CI = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"


class TestSmokeExternal:
    """Smoke tests EXTERNAL - Con Polymarket real, staging/producción."""
    
    @pytest.mark.skipif(CI, reason="Smoke EXTERNAL no ejecuta en CI (requiere conexión real a Polymarket)")
    def test_smoke_external_pipeline_health(self):
        """
        Smoke test EXTERNAL: Pipeline health (mode=external).
        
        Valida dataflow real (WS + cache) aunque trading disabled.
        Útil para: "¿conecta WS?", "¿llegan datos?", "¿se publica en cache?"
        
        status = PASS si el pipeline funciona
        trading_ready = false si healthy_checkers == 0 (pero pipeline OK)
        """
        response = client.get("/api/polymarket/smoke?mode=external")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Respuesta debe incluir 'status'"
        assert "mode" in data, "Respuesta debe incluir 'mode'"
        assert "trading_ready" in data, "Respuesta debe incluir 'trading_ready'"
        assert "checks" in data, "Respuesta debe incluir 'checks'"
        
        assert data["mode"] == "external", "Mode debe ser 'external'"
        
        # En mode=external, status puede ser PASS aunque trading_ready=false
        # Lo importante es que el pipeline funcione
        if data["status"] == "FAIL":
            # Si falla, mostrar detalles
            failure_reason = data.get("failure_reason", "unknown")
            failed_checks = [c for c in data.get("checks", []) if c.get("status") == "FAIL"]
            pytest.fail(
                f"Smoke EXTERNAL falló: {failure_reason}\n"
                f"Failed checks: {[c['name'] for c in failed_checks]}"
            )
        
        # Verificar que los checks core están presentes
        check_names = [c["name"] for c in data.get("checks", [])]
        assert "execution_mode" in check_names, "Debe incluir check execution_mode"
        assert "checkers_health" in check_names, "Debe incluir check checkers_health"
        assert "risk_engine_status" in check_names, "Debe incluir check risk_engine_status"
        assert "gamma_health" in check_names, "Debe incluir check gamma_health"
        
        # Para mode=external, ws_market_pipeline es opcional (puede fallar si no hay asset_id)
        # pero si está presente, debe estar en checks
        ws_checks = [c for c in data.get("checks", []) if "ws_market" in c.get("name", "")]
        if ws_checks:
            # Si hay checks de WS, al menos uno debe estar presente
            assert len(ws_checks) > 0, "Si hay checks de WS, deben estar presentes"
    
    @pytest.mark.skipif(CI, reason="Smoke EXTERNAL no ejecuta en CI (requiere conexión real a Polymarket)")
    def test_smoke_external_trade_ready(self):
        """
        Smoke test EXTERNAL: Trading readiness (mode=external_trade_ready).
        
        Valida dataflow + trading permitido.
        status = PASS solo si pipeline funciona Y trading está permitido.
        """
        response = client.get("/api/polymarket/smoke?mode=external_trade_ready")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Respuesta debe incluir 'status'"
        assert "mode" in data, "Respuesta debe incluir 'mode'"
        assert "trading_ready" in data, "Respuesta debe incluir 'trading_ready'"
        
        assert data["mode"] == "external_trade_ready", "Mode debe ser 'external_trade_ready'"
        
        # En mode=external_trade_ready, status=PASS requiere trading_ready=true
        if data["status"] == "PASS":
            assert data["trading_ready"] is True, "Si status=PASS, trading_ready debe ser True"
        
        # Si trading_ready=false, status puede ser FAIL
        if data["trading_ready"] is False:
            # Verificar que el failure_reason indica por qué
            failure_reason = data.get("failure_reason")
            assert failure_reason is not None, "Si trading_ready=false, debe haber failure_reason"
            
            # Verificar que checkers_health indica el problema
            checkers_check = next(
                (c for c in data.get("checks", []) if c.get("name") == "checkers_health"),
                None
            )
            if checkers_check:
                details = checkers_check.get("details", {})
                healthy_checkers = details.get("healthy_checkers", 0)
                if healthy_checkers == 0:
                    # Esto es esperado si no hay checkers saludables
                    assert data["status"] == "FAIL", "Si healthy_checkers=0, status debe ser FAIL"
    
    @pytest.mark.skipif(CI, reason="Smoke EXTERNAL no ejecuta en CI (requiere conexión real a Polymarket)")
    def test_smoke_external_with_asset_id(self):
        """
        Smoke test EXTERNAL: Con asset_id específico.
        
        Verifica que el endpoint acepta asset_id como parámetro.
        """
        # Usar un asset_id de ejemplo (puede no existir, pero el endpoint debe manejarlo)
        asset_id = "0x1234567890123456789012345678901234567890"
        response = client.get(f"/api/polymarket/smoke?mode=external&asset_id={asset_id}")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Respuesta debe incluir 'status'"
        assert "mode" in data, "Respuesta debe incluir 'mode'"
        
        # El endpoint debe procesar el asset_id (aunque pueda fallar si no existe)
        # Lo importante es que no retorne 500
        assert data["status"] in ["PASS", "FAIL"], "Status debe ser PASS o FAIL, no error"

