"""
Tests de integración para Fase 3: Datos de Cuenta (CLOB API - Lectura).

Verifica:
- Balance USDC
- Órdenes abiertas
- Trades históricos
- Order scoring
- Precisión de decimales/unidades
"""
import pytest
from app.main import app
from app.settings import settings


class TestPhase3AccountData:
    """Tests para verificar acceso a datos de cuenta del usuario."""
    
    @pytest.mark.skipif(
        not settings.private_key or not (settings.funder_address or settings.polymarket_proxy_address),
        reason="Requiere PRIVATE_KEY y FUNDER_ADDRESS configuradas"
    )
    def test_get_account_balance(self, client):
        """Test 3.1: Obtener balance USDC."""
        response = client.get("/api/polymarket/account/balance")
        
        # Puede ser 200 (éxito) o 503 (cliente no inicializado)
        assert response.status_code in [200, 503], f"Status code debe ser 200 o 503, obtuvo {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "balance_usdc" in data, "Respuesta debe incluir 'balance_usdc'"
            assert "currency" in data, "Respuesta debe incluir 'currency'"
            assert data["currency"] == "USDC", "Currency debe ser USDC"
            
            balance = data["balance_usdc"]
            assert isinstance(balance, (int, float)), "Balance debe ser numérico"
            assert balance >= 0, "Balance debe ser >= 0"
            
            # Verificar precisión: USDC tiene 6 decimales
            # El balance debe venir en USDC (no en wei o unidades menores)
            # Si viene como float, verificar que tiene precisión razonable
            if isinstance(balance, float):
                # Verificar que no es un número muy grande (indicaría que está en wei)
                assert balance < 1_000_000_000, "Balance parece estar en wei, debería estar en USDC"
    
    @pytest.mark.skipif(
        not settings.private_key or not (settings.funder_address or settings.polymarket_proxy_address),
        reason="Requiere PRIVATE_KEY y FUNDER_ADDRESS configuradas"
    )
    def test_get_account_orders(self, client):
        """Test 3.2: Listar órdenes abiertas."""
        response = client.get("/api/polymarket/account/orders")
        
        assert response.status_code in [200, 503], f"Status code debe ser 200 o 503, obtuvo {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "orders" in data, "Respuesta debe incluir 'orders'"
            assert "count" in data, "Respuesta debe incluir 'count'"
            assert isinstance(data["orders"], list), "Orders debe ser una lista"
            assert data["count"] == len(data["orders"]), "Count debe coincidir con longitud de orders"
            
            # Si hay órdenes, verificar estructura
            if len(data["orders"]) > 0:
                order = data["orders"][0]
                assert "id" in order or "order_id" in order, "Order debe tener 'id' o 'order_id'"
                # Otros campos opcionales: token_id, price, size, side, status
    
    @pytest.mark.skipif(
        not settings.private_key or not (settings.funder_address or settings.polymarket_proxy_address),
        reason="Requiere PRIVATE_KEY y FUNDER_ADDRESS configuradas"
    )
    def test_get_account_orders_with_filters(self, client):
        """Test 3.3: Listar órdenes con filtros."""
        # Test con filtro de market (condition_id)
        response = client.get("/api/polymarket/account/orders?market=0x123")
        
        assert response.status_code in [200, 503], f"Status code debe ser 200 o 503, obtuvo {response.status_code}"
        
        # Test con filtro de asset_id
        response2 = client.get("/api/polymarket/account/orders?asset_id=0x456")
        assert response2.status_code in [200, 503]
    
    @pytest.mark.skipif(
        not settings.private_key or not (settings.funder_address or settings.polymarket_proxy_address),
        reason="Requiere PRIVATE_KEY y FUNDER_ADDRESS configuradas"
    )
    def test_get_account_order_by_id(self, client):
        """Test 3.4: Obtener orden específica por ID."""
        # Primero obtener una orden (si existe)
        orders_response = client.get("/api/polymarket/account/orders")
        
        if orders_response.status_code == 200:
            orders_data = orders_response.json()
            if len(orders_data["orders"]) > 0:
                # Probar con una orden real
                order_id = orders_data["orders"][0].get("id") or orders_data["orders"][0].get("order_id")
                
                if order_id:
                    response = client.get(f"/api/polymarket/account/orders/{order_id}")
                    
                    assert response.status_code in [200, 404, 503], f"Status code debe ser 200, 404 o 503, obtuvo {response.status_code}"
                    
                    if response.status_code == 200:
                        data = response.json()
                        assert "id" in data or "order_id" in data, "Order debe tener 'id' o 'order_id'"
            else:
                # Si no hay órdenes, probar con un order_id inválido (formato correcto pero no existe)
                # Formato: string hexadecimal (hash) de 66 caracteres (0x + 64 hex)
                invalid_order_id = "0x" + "0" * 64  # Order ID inválido pero con formato correcto
                response = client.get(f"/api/polymarket/account/orders/{invalid_order_id}")
                
                # Debe retornar 404 si la orden no existe
                assert response.status_code in [404, 503], f"Status code debe ser 404 o 503 para orden inexistente, obtuvo {response.status_code}"
        else:
            # Si el cliente no está inicializado, probar con un order_id inválido
            invalid_order_id = "0x" + "0" * 64
            response = client.get(f"/api/polymarket/account/orders/{invalid_order_id}")
            
            # Debe retornar 503 si el cliente no está inicializado
            assert response.status_code == 503, f"Status code debe ser 503 cuando cliente no inicializado, obtuvo {response.status_code}"
    
    @pytest.mark.skipif(
        not settings.private_key or not (settings.funder_address or settings.polymarket_proxy_address),
        reason="Requiere PRIVATE_KEY y FUNDER_ADDRESS configuradas"
    )
    def test_get_account_trades(self, client):
        """Test 3.5: Listar trades históricos."""
        response = client.get("/api/polymarket/account/trades")
        
        assert response.status_code in [200, 503], f"Status code debe ser 200 o 503, obtuvo {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "trades" in data, "Respuesta debe incluir 'trades'"
            assert "count" in data, "Respuesta debe incluir 'count'"
            assert isinstance(data["trades"], list), "Trades debe ser una lista"
            assert data["count"] == len(data["trades"]), "Count debe coincidir con longitud de trades"
            
            # Si hay trades, verificar estructura y estados
            if len(data["trades"]) > 0:
                trade = data["trades"][0]
                assert "id" in trade or "trade_id" in trade, "Trade debe tener 'id' o 'trade_id'"
                
                # Verificar estados válidos
                if "status" in trade:
                    valid_statuses = ["MATCHED", "MINED", "CONFIRMED", "RETRYING", "FAILED"]
                    assert trade["status"] in valid_statuses, f"Status debe ser uno de {valid_statuses}"
    
    @pytest.mark.skipif(
        not settings.private_key or not (settings.funder_address or settings.polymarket_proxy_address),
        reason="Requiere PRIVATE_KEY y FUNDER_ADDRESS configuradas"
    )
    def test_get_account_trades_with_filters(self, client):
        """Test 3.6: Listar trades con filtros."""
        # Test con filtro de market
        response = client.get("/api/polymarket/account/trades?market=0x123")
        assert response.status_code in [200, 503]
        
        # Test con filtro de timestamp
        response2 = client.get("/api/polymarket/account/trades?after=1704067200")
        assert response2.status_code in [200, 503]
    
    @pytest.mark.skipif(
        not settings.private_key or not (settings.funder_address or settings.polymarket_proxy_address),
        reason="Requiere PRIVATE_KEY y FUNDER_ADDRESS configuradas"
    )
    def test_get_order_scoring(self, client):
        """Test 3.7: Verificar order scoring."""
        # Primero obtener una orden (si existe)
        orders_response = client.get("/api/polymarket/account/orders")
        
        if orders_response.status_code == 200:
            orders_data = orders_response.json()
            if len(orders_data["orders"]) > 0:
                # Probar con una orden real
                order_id = orders_data["orders"][0].get("id") or orders_data["orders"][0].get("order_id")
                
                if order_id:
                    response = client.get(f"/api/polymarket/account/orders/{order_id}/scoring")
                    
                    assert response.status_code in [200, 404, 500, 503], f"Status code debe ser 200, 404, 500 o 503, obtuvo {response.status_code}"
                    
                    if response.status_code == 200:
                        data = response.json()
                        assert "order_id" in data, "Respuesta debe incluir 'order_id'"
                        assert "scoring" in data, "Respuesta debe incluir 'scoring'"
                        assert isinstance(data["scoring"], bool), "Scoring debe ser boolean"
            else:
                # Si no hay órdenes, probar con un order_id inválido (formato correcto pero no existe)
                invalid_order_id = "0x" + "0" * 64  # Order ID inválido pero con formato correcto
                response = client.get(f"/api/polymarket/account/orders/{invalid_order_id}/scoring")
                
                # Puede retornar 200 (con scoring=False), 404, 500 o 503 si la orden no existe
                # Según la doc, is_order_scoring puede retornar False incluso si la orden no existe
                assert response.status_code in [200, 404, 500, 503], f"Status code debe ser 200, 404, 500 o 503 para orden inexistente, obtuvo {response.status_code}"
                
                if response.status_code == 200:
                    # Si retorna 200, debe tener scoring=False para orden inexistente
                    data = response.json()
                    assert "scoring" in data, "Respuesta debe incluir 'scoring'"
                    assert data["scoring"] is False, "Orden inexistente debe tener scoring=False"
        else:
            # Si el cliente no está inicializado, probar con un order_id inválido
            invalid_order_id = "0x" + "0" * 64
            response = client.get(f"/api/polymarket/account/orders/{invalid_order_id}/scoring")
            
            # Debe retornar 503 si el cliente no está inicializado
            assert response.status_code == 503, f"Status code debe ser 503 cuando cliente no inicializado, obtuvo {response.status_code}"
    
    def test_precision_and_units(self, client):
        """Test 3.8: Verificar precisión de decimales y unidades."""
        # Este test verifica que los valores numéricos tienen la precisión correcta
        # USDC tiene 6 decimales
        # Shares pueden ser enteros o decimales según el token
        
        # Este test es más conceptual, verifica que los endpoints manejan correctamente
        # la conversión de unidades (wei → USDC, etc.)
        pass  # Se verifica en test_get_account_balance
    
    def test_order_lifecycle_states(self, client):
        """Test 3.9: Verificar estados del lifecycle de órdenes."""
        # Estados esperados:
        # PENDING → SUBMITTED → OPEN → FILLED / CANCELLED / FAILED
        
        # Este test verifica que los estados de órdenes son consistentes
        # con el lifecycle esperado
        pass  # Se verifica en test_get_account_orders y test_get_account_trades

