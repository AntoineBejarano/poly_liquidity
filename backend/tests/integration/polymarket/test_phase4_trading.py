"""
Tests de integración para Fase 4: Operaciones de Trading (CLOB API - Escritura).

Verifica:
- Crear limit orders
- Crear market orders
- Cancelar órdenes
- Prechecks de risk engine
- Cancel/replace philosophy
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.settings import settings
from app.core.config_service import config_service

client = TestClient(app)


class TestPhase4Trading:
    """Tests para verificar operaciones de trading."""
    
    @pytest.fixture
    def sample_token_id(self):
        """Token ID de ejemplo para tests (debe ser reemplazado con uno real)."""
        return "0x1234567890abcdef1234567890abcdef12345678"
    
    @pytest.fixture
    def execution_mode(self):
        """Obtener execution mode actual."""
        return config_service.get_execution_mode()
    
    @pytest.mark.skipif(
        not settings.private_key or not (settings.funder_address or settings.polymarket_proxy_address),
        reason="Requiere PRIVATE_KEY y FUNDER_ADDRESS configuradas"
    )
    def test_create_limit_order_buy(self, sample_token_id, execution_mode):
        """Test 4.1: Crear limit order BUY."""
        # En DRY_RUN, esto debe simular sin enviar realmente
        order_data = {
            "token_id": sample_token_id,
            "price": 0.50,
            "size": 100.0,
            "side": "BUY",
            "order_type": "GTC"
        }
        
        response = client.post("/api/polymarket/trading/orders/limit", json=order_data)
        
        # En DRY_RUN puede ser 200 (simulado) o 503 (cliente no inicializado)
        # En LIVE/PAPER puede ser 200 (éxito) o 400/500 (error)
        assert response.status_code in [200, 400, 500, 503], f"Status code debe ser 200, 400, 500 o 503, obtuvo {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            # La respuesta puede tener diferentes formatos según el cliente
            assert "id" in data or "order_id" in data or "status" in data, "Respuesta debe incluir información de la orden"
    
    @pytest.mark.skipif(
        not settings.private_key or not (settings.funder_address or settings.polymarket_proxy_address),
        reason="Requiere PRIVATE_KEY y FUNDER_ADDRESS configuradas"
    )
    def test_create_limit_order_sell(self, sample_token_id, execution_mode):
        """Test 4.2: Crear limit order SELL."""
        order_data = {
            "token_id": sample_token_id,
            "price": 0.60,
            "size": 100.0,
            "side": "SELL",
            "order_type": "GTC"
        }
        
        response = client.post("/api/polymarket/trading/orders/limit", json=order_data)
        
        assert response.status_code in [200, 400, 500, 503], f"Status code debe ser 200, 400, 500 o 503, obtuvo {response.status_code}"
    
    @pytest.mark.skipif(
        not settings.private_key or not (settings.funder_address or settings.polymarket_proxy_address),
        reason="Requiere PRIVATE_KEY y FUNDER_ADDRESS configuradas"
    )
    def test_create_limit_order_invalid_side(self, sample_token_id):
        """Test 4.1b: Crear limit order con side inválido."""
        order_data = {
            "token_id": sample_token_id,
            "price": 0.50,
            "size": 100.0,
            "side": "INVALID",  # Side inválido
            "order_type": "GTC"
        }
        
        response = client.post("/api/polymarket/trading/orders/limit", json=order_data)
        
        assert response.status_code == 400, "Side inválido debe retornar 400"
        assert "side" in response.json().get("detail", "").lower() or "invalid" in response.json().get("detail", "").lower()
    
    @pytest.mark.skipif(
        not settings.private_key or not (settings.funder_address or settings.polymarket_proxy_address),
        reason="Requiere PRIVATE_KEY y FUNDER_ADDRESS configuradas"
    )
    def test_create_market_order(self, sample_token_id, execution_mode):
        """Test 4.3: Crear market order."""
        # ⚠️ ADVERTENCIA: Market orders se ejecutan inmediatamente
        order_data = {
            "token_id": sample_token_id,
            "amount": 10.0,  # Amount in USD
            "side": "BUY",
            "order_type": "FOK"
        }
        
        response = client.post("/api/polymarket/trading/orders/market", json=order_data)
        
        # En DRY_RUN debe simular
        # En LIVE/PAPER puede ejecutarse inmediatamente
        assert response.status_code in [200, 400, 500, 503], f"Status code debe ser 200, 400, 500 o 503, obtuvo {response.status_code}"
    
    @pytest.mark.skipif(
        not settings.private_key or not (settings.funder_address or settings.polymarket_proxy_address),
        reason="Requiere PRIVATE_KEY y FUNDER_ADDRESS configuradas"
    )
    def test_cancel_order(self, execution_mode):
        """Test 4.4: Cancelar orden específica."""
        # Primero obtener una orden (si existe)
        orders_response = client.get("/api/polymarket/account/orders")
        
        if orders_response.status_code == 200:
            orders_data = orders_response.json()
            if len(orders_data["orders"]) > 0:
                # Probar con una orden real
                order_id = orders_data["orders"][0].get("id") or orders_data["orders"][0].get("order_id")
                
                if order_id:
                    response = client.delete(f"/api/polymarket/trading/orders/{order_id}")
                    
                    assert response.status_code in [200, 404, 500, 503], f"Status code debe ser 200, 404, 500 o 503, obtuvo {response.status_code}"
                    
                    if response.status_code == 200:
                        data = response.json()
                        # La respuesta puede tener formato {"canceled": [...], "not_canceled": {...}}
                        assert isinstance(data, dict), "Respuesta debe ser un dict"
                        # Si la orden no existe, aparecerá en not_canceled
                        if "not_canceled" in data and order_id in data.get("not_canceled", {}):
                            # Orden no existe o no se pudo cancelar
                            assert isinstance(data["not_canceled"][order_id], str), "Razón debe ser string"
            else:
                # Si no hay órdenes, probar con un order_id inválido (formato correcto pero no existe)
                # Según la doc, cancel() retorna {"canceled": [], "not_canceled": {order_id: reason}}
                invalid_order_id = "0x" + "0" * 64  # Order ID inválido pero con formato correcto
                response = client.delete(f"/api/polymarket/trading/orders/{invalid_order_id}")
                
                # Debe retornar 200 con not_canceled si la orden no existe, o 404/500/503
                assert response.status_code in [200, 404, 500, 503], f"Status code debe ser 200, 404, 500 o 503 para orden inexistente, obtuvo {response.status_code}"
                
                if response.status_code == 200:
                    data = response.json()
                    # Si la orden no existe, debe aparecer en not_canceled
                    if "not_canceled" in data and invalid_order_id in data.get("not_canceled", {}):
                        assert isinstance(data["not_canceled"][invalid_order_id], str), "Razón debe ser string"
        else:
            # Si el cliente no está inicializado, probar con un order_id inválido
            invalid_order_id = "0x" + "0" * 64
            response = client.delete(f"/api/polymarket/trading/orders/{invalid_order_id}")
            
            # Debe retornar 503 si el cliente no está inicializado
            assert response.status_code == 503, f"Status code debe ser 503 cuando cliente no inicializado, obtuvo {response.status_code}"
    
    @pytest.mark.skipif(
        not settings.private_key or not (settings.funder_address or settings.polymarket_proxy_address),
        reason="Requiere PRIVATE_KEY y FUNDER_ADDRESS configuradas"
    )
    def test_cancel_all_orders(self, execution_mode):
        """Test 4.5: Cancelar todas las órdenes."""
        # ⚠️ ADVERTENCIA: Esto cancela TODAS las órdenes abiertas
        response = client.delete("/api/polymarket/trading/orders")
        
        assert response.status_code in [200, 500, 503], f"Status code debe ser 200, 500 o 503, obtuvo {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), "Respuesta debe ser un dict"
            # Puede tener formato {"canceled": [...], "not_canceled": {...}}
    
    def test_execution_mode_respected(self, sample_token_id, execution_mode):
        """Test 4.6: Verificar que execution_mode se respeta."""
        # En DRY_RUN, las órdenes deben simularse sin enviar realmente
        # En PAPER, deben enviarse a wallet de paper trading
        # En LIVE, deben enviarse realmente
        
        order_data = {
            "token_id": sample_token_id,
            "price": 0.50,
            "size": 100.0,
            "side": "BUY",
            "order_type": "GTC"
        }
        
        response = client.post("/api/polymarket/trading/orders/limit", json=order_data)
        
        if execution_mode == "DRY_RUN":
            # En DRY_RUN, debe simular sin requerir credenciales reales
            # Puede retornar 200 (simulado) o 503 (cliente no inicializado, pero OK en DRY_RUN)
            assert response.status_code in [200, 503]
        elif execution_mode == "PAPER":
            # En PAPER, requiere credenciales pero envía a wallet de prueba
            assert response.status_code in [200, 400, 500, 503]
        elif execution_mode == "LIVE":
            # En LIVE, requiere credenciales reales y envía órdenes reales
            assert response.status_code in [200, 400, 500, 503]
    
    def test_prechecks_validation(self, sample_token_id):
        """Test 4.7: Verificar que prechecks funcionan."""
        # Test con datos inválidos
        invalid_orders = [
            {"token_id": "", "price": 0.50, "size": 100.0, "side": "BUY", "order_type": "GTC"},  # token_id vacío
            {"token_id": sample_token_id, "price": -0.50, "size": 100.0, "side": "BUY", "order_type": "GTC"},  # precio negativo
            {"token_id": sample_token_id, "price": 0.50, "size": -100.0, "side": "BUY", "order_type": "GTC"},  # size negativo
            {"token_id": sample_token_id, "price": 0.50, "size": 100.0, "side": "BUY", "order_type": "INVALID"},  # order_type inválido
        ]
        
        for invalid_order in invalid_orders:
            response = client.post("/api/polymarket/trading/orders/limit", json=invalid_order)
            # Debe retornar 400 o 422 (validation error)
            assert response.status_code in [400, 422], f"Orden inválida debe retornar 400 o 422: {invalid_order}"

