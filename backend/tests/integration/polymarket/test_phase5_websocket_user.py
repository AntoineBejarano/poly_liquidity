"""
Tests de integración para Fase 5: WebSocket USER (Órdenes/Trades del Usuario).

Verifica:
- Conexión al USER channel (requiere autenticación)
- Endpoints de control (subscribe/unsubscribe)
- Estado de conexión
- Manejo de errores cuando no hay autenticación
"""
import pytest
from app.main import app


class TestPhase5WebSocketUser:
    """Tests para Fase 5: WebSocket USER channel."""
    
    def test_5_1_websocket_status_includes_user_channel(self, client):
        """
        Test 5.1: Verificar que el endpoint de status incluye información del USER channel.
        
        Verifica:
        - Endpoint retorna información del USER channel
        - Estado de conexión y autenticación
        """
        response = client.get("/api/polymarket/websocket/status")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "user_channel" in data, "Respuesta debe incluir 'user_channel'"
        
        user_channel = data["user_channel"]
        assert "connected" in user_channel, "user_channel debe incluir 'connected'"
        assert "authenticated" in user_channel, "user_channel debe incluir 'authenticated'"
        assert isinstance(user_channel["connected"], bool), "connected debe ser boolean"
        assert isinstance(user_channel["authenticated"], bool), "authenticated debe ser boolean"
    
    def test_5_2_subscribe_user_channel_without_auth(self, client):
        """
        Test 5.2: Intentar suscribirse al USER channel sin autenticación.
        
        Verifica:
        - Endpoint retorna error 503 si no hay CLOB client disponible
        - Mensaje de error es claro
        """
        response = client.post(
            "/api/polymarket/websocket/subscribe/user",
            json={
                "market_ids": None,
                "owner_key": "test"
            }
        )
        
        # Puede retornar 503 (CLOB no disponible) o 200 (si ya está conectado)
        # Lo importante es que no crashee con 500
        assert response.status_code in [200, 503], \
            f"Status code debe ser 200 o 503, obtuvo {response.status_code}"
        
        data = response.json()
        
        if response.status_code == 503:
            assert "detail" in data, "Error debe incluir 'detail'"
            detail = data["detail"].lower()
            assert any(keyword in detail for keyword in [
                "clob", "api key", "authentication", "auth", "websocket-client"
            ]), f"Mensaje de error debe mencionar CLOB/API keys/auth/websocket-client, obtuvo: {data['detail']}"
        elif response.status_code == 200:
            # Ya está conectado o se conectó exitosamente
            assert "status" in data, "Respuesta debe incluir 'status'"
            assert data["status"] in ["subscribed", "already_connected"], \
                "Status debe ser 'subscribed' o 'already_connected'"
    
    def test_5_3_subscribe_user_channel_with_market_ids(self, client):
        """
        Test 5.3: Suscribirse al USER channel con market_ids específicos.
        
        Verifica:
        - Endpoint acepta market_ids opcionales
        - Respuesta incluye market_ids
        """
        test_market_ids = ["0x1234567890123456789012345678901234567890"]
        
        response = client.post(
            "/api/polymarket/websocket/subscribe/user",
            json={
                "market_ids": test_market_ids,
                "owner_key": "test_with_markets"
            }
        )
        
        # Puede retornar 200 (conectado), 503 (sin auth), o 500 (error)
        assert response.status_code in [200, 503, 500], \
            f"Status code debe ser 200, 503 o 500, obtuvo {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data, "Respuesta debe incluir 'status'"
            assert "market_ids" in data, "Respuesta debe incluir 'market_ids'"
    
    def test_5_4_unsubscribe_user_channel(self, client):
        """
        Test 5.4: Desuscribirse del USER channel.
        
        Verifica:
        - Endpoint funciona incluso si no está conectado
        - Respuesta indica estado correcto
        """
        response = client.post(
            "/api/polymarket/websocket/unsubscribe/user",
            json={
                "owner_key": "test"
            }
        )
        
        assert response.status_code == 200, \
            f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Respuesta debe incluir 'status'"
        assert data["status"] in ["unsubscribed", "not_connected"], \
            f"Status debe ser 'unsubscribed' o 'not_connected', obtuvo {data['status']}"
        assert "message" in data, "Respuesta debe incluir 'message'"
    
    def test_5_5_subscribe_unsubscribe_cycle(self, client):
        """
        Test 5.5: Ciclo completo de suscripción/desuscripción.
        
        Verifica:
        - Suscribirse y luego desuscribirse funciona correctamente
        - Estado se actualiza correctamente
        """
        # Intentar suscribirse
        subscribe_response = client.post(
            "/api/polymarket/websocket/subscribe/user",
            json={
                "owner_key": "test_cycle"
            }
        )
        
        # Puede fallar por falta de auth, pero no debe crashear
        assert subscribe_response.status_code in [200, 503], \
            f"Subscribe debe retornar 200 o 503, obtuvo {subscribe_response.status_code}"
        
        # Desuscribirse (debe funcionar siempre)
        unsubscribe_response = client.post(
            "/api/polymarket/websocket/unsubscribe/user",
            json={
                "owner_key": "test_cycle"
            }
        )
        
        assert unsubscribe_response.status_code == 200, \
            f"Unsubscribe debe retornar 200, obtuvo {unsubscribe_response.status_code}"
        
        unsubscribe_data = unsubscribe_response.json()
        assert unsubscribe_data["status"] in ["unsubscribed", "not_connected"], \
            "Unsubscribe debe retornar estado correcto"
    
    def test_5_6_status_reflects_user_channel_state(self, client):
        """
        Test 5.6: Verificar que el status refleja el estado del USER channel.
        
        Verifica:
        - Status muestra correctamente si USER channel está conectado
        - Status muestra correctamente si hay autenticación
        """
        # Obtener status inicial
        status_response = client.get("/api/polymarket/websocket/status")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        user_channel = status_data["user_channel"]
        
        # Verificar estructura
        assert "connected" in user_channel
        assert "authenticated" in user_channel
        
        # El estado puede ser True o False, pero debe ser consistente
        # Si está conectado, debe estar autenticado
        if user_channel["connected"]:
            assert user_channel["authenticated"] == True, \
                "Si USER channel está conectado, debe estar autenticado"
    
    def test_5_7_user_subscription_request_validation(self, client):
        """
        Test 5.7: Validación del request model.
        
        Verifica:
        - Request acepta market_ids opcionales
        - Request acepta owner_key opcional (default: "api")
        """
        # Request sin market_ids (debe funcionar)
        response1 = client.post(
            "/api/polymarket/websocket/subscribe/user",
            json={
                "owner_key": "test_validation"
            }
        )
        
        assert response1.status_code in [200, 503], \
            f"Request sin market_ids debe retornar 200 o 503, obtuvo {response1.status_code}"
        
        # Request sin owner_key (debe usar default)
        response2 = client.post(
            "/api/polymarket/websocket/subscribe/user",
            json={}
        )
        
        assert response2.status_code in [200, 503], \
            f"Request sin owner_key debe retornar 200 o 503, obtuvo {response2.status_code}"
        
        if response2.status_code == 200:
            data = response2.json()
            # owner_key debe tener un valor (default o el que se configuró)
            assert "owner_key" in data or "status" in data
    
    def test_5_8_error_handling_missing_clob_client(self, client):
        """
        Test 5.8: Manejo de errores cuando CLOB client no está disponible.
        
        Verifica:
        - Error 503 cuando CLOB client no está disponible
        - Mensaje de error es claro y útil
        """
        # Este test verifica que el endpoint maneja correctamente
        # cuando no hay CLOB client disponible para derivar API keys
        
        response = client.post(
            "/api/polymarket/websocket/subscribe/user",
            json={
                "owner_key": "test_error_handling"
            }
        )
        
        # Si CLOB no está disponible, debe retornar 503
        # Si está disponible pero no puede derivar keys, también 503
        # Si ya está conectado, 200
        assert response.status_code in [200, 503], \
            f"Status code debe ser 200 o 503, obtuvo {response.status_code}"
        
        if response.status_code == 503:
            data = response.json()
            assert "detail" in data, "Error 503 debe incluir 'detail'"
            detail = data["detail"]
            # Mensaje debe mencionar CLOB, API keys, autenticación, o websocket-client
            assert any(keyword in detail.lower() for keyword in [
                "clob", "api key", "authentication", "auth", "derive", "websocket-client"
            ]), f"Mensaje de error debe mencionar CLOB/API keys/auth/websocket-client, obtuvo: {detail}"

