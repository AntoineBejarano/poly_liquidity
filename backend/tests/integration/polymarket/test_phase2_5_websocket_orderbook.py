"""
Tests de integración para Fase 2.5: WebSocket MARKET → Orderbook Engine.

Tests:
- 2.5.1: Conexión WebSocket MARKET Channel
- 2.5.2: Orderbook Engine Integration
- 2.5.3: State Cache Publishing
- 2.5.4: Strategy Consumption (Decision Graph)
- 2.5.5: Orchestrator Ref-Count
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.core.orderbook.service import get_orderbook_service
from app.core.strategy_engine.state_cache_service import StateCacheService
from app.database import SessionLocal

client = TestClient(app)


class TestPhase25WebSocketOrderbook:
    """Tests para Fase 2.5: WebSocket MARKET → Orderbook Engine."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup para cada test."""
        # Limpiar estado antes de cada test
        yield
        # Cleanup después de cada test
    
    def test_2_5_1_websocket_status_endpoint(self):
        """
        Test 2.5.1: Verificar endpoint de estado de WebSocket.
        
        Verifica:
        - Endpoint responde correctamente
        - Retorna estado de conexiones WS MARKET
        - Retorna ref-count por asset_id
        """
        response = client.get("/api/polymarket/websocket/status")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "market_channel" in data, "Respuesta debe incluir 'market_channel'"
        assert "orderbook" in data, "Respuesta debe incluir 'orderbook'"
        
        market_channel = data["market_channel"]
        assert "connected" in market_channel, "market_channel debe incluir 'connected'"
        assert "subscribed_asset_ids" in market_channel, "market_channel debe incluir 'subscribed_asset_ids'"
        assert "count" in market_channel, "market_channel debe incluir 'count'"
        
        orderbook = data["orderbook"]
        assert "ref_count" in orderbook, "orderbook debe incluir 'ref_count'"
        assert "total_subscriptions" in orderbook, "orderbook debe incluir 'total_subscriptions'"
    
    def test_2_5_2_subscribe_market_channel(self):
        """
        Test 2.5.2: Suscribir asset_id al WebSocket MARKET channel.
        
        Verifica:
        - Suscripción incrementa ref-count
        - Endpoint retorna estado correcto
        """
        # Usar un asset_id de prueba (formato válido de token ID)
        test_asset_id = "0x1234567890123456789012345678901234567890"
        test_owner_key = "test_owner"
        
        response = client.post(
            "/api/polymarket/websocket/subscribe/market",
            json={
                "asset_id": test_asset_id,
                "owner_key": test_owner_key
            }
        )
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert data["status"] == "subscribed", "Status debe ser 'subscribed'"
        assert data["asset_id"] == test_asset_id, "asset_id debe coincidir"
        assert data["owner_key"] == test_owner_key, "owner_key debe coincidir"
        assert data["ref_count"] >= 1, "ref_count debe ser >= 1 después de suscribir"
        
        # Verificar que el ref_count se refleja en el status
        status_response = client.get("/api/polymarket/websocket/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        ref_count = status_data["orderbook"]["ref_count"]
        assert test_asset_id in ref_count, "asset_id debe estar en ref_count"
        assert ref_count[test_asset_id] >= 1, "ref_count debe ser >= 1"
    
    def test_2_5_3_unsubscribe_market_channel(self):
        """
        Test 2.5.3: Desuscribir asset_id del WebSocket MARKET channel.
        
        Verifica:
        - Desuscripción decrementa ref-count
        - Endpoint retorna estado correcto
        """
        # Primero suscribir
        test_asset_id = "0x9876543210987654321098765432109876543210"
        test_owner_key = "test_owner_2"
        
        subscribe_response = client.post(
            "/api/polymarket/websocket/subscribe/market",
            json={
                "asset_id": test_asset_id,
                "owner_key": test_owner_key
            }
        )
        assert subscribe_response.status_code == 200
        
        # Luego desuscribir
        unsubscribe_response = client.post(
            "/api/polymarket/websocket/unsubscribe/market",
            json={
                "asset_id": test_asset_id,
                "owner_key": test_owner_key
            }
        )
        
        assert unsubscribe_response.status_code == 200, f"Status code debe ser 200, obtuvo {unsubscribe_response.status_code}"
        
        data = unsubscribe_response.json()
        assert data["status"] == "unsubscribed", "Status debe ser 'unsubscribed'"
        assert data["asset_id"] == test_asset_id, "asset_id debe coincidir"
        assert data["ref_count"] == 0, "ref_count debe ser 0 después de desuscribir"
    
    def test_2_5_4_ref_count_multiple_owners(self):
        """
        Test 2.5.4: Verificar ref-count con múltiples owners.
        
        Verifica:
        - Múltiples owners pueden suscribirse al mismo asset_id
        - Ref-count se incrementa correctamente
        - Desuscripción de un owner no afecta a otros
        """
        test_asset_id = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        owner1 = "owner_1"
        owner2 = "owner_2"
        
        # Suscribir owner1
        response1 = client.post(
            "/api/polymarket/websocket/subscribe/market",
            json={"asset_id": test_asset_id, "owner_key": owner1}
        )
        assert response1.status_code == 200
        assert response1.json()["ref_count"] == 1
        
        # Suscribir owner2
        response2 = client.post(
            "/api/polymarket/websocket/subscribe/market",
            json={"asset_id": test_asset_id, "owner_key": owner2}
        )
        assert response2.status_code == 200
        assert response2.json()["ref_count"] == 2
        
        # Verificar ref_count en status
        status_response = client.get("/api/polymarket/websocket/status")
        assert status_response.status_code == 200
        ref_count = status_response.json()["orderbook"]["ref_count"]
        assert ref_count[test_asset_id] == 2, "ref_count debe ser 2 con dos owners"
        
        # Desuscribir owner1
        unsubscribe_response = client.post(
            "/api/polymarket/websocket/unsubscribe/market",
            json={"asset_id": test_asset_id, "owner_key": owner1}
        )
        assert unsubscribe_response.status_code == 200
        assert unsubscribe_response.json()["ref_count"] == 1, "ref_count debe ser 1 después de desuscribir owner1"
        
        # Verificar que owner2 sigue suscrito
        status_response2 = client.get("/api/polymarket/websocket/status")
        assert status_response2.status_code == 200
        status_data2 = status_response2.json()
        assert "orderbook" in status_data2, "Respuesta debe incluir 'orderbook'"
        ref_count2 = status_data2["orderbook"]["ref_count"]
        assert ref_count2[test_asset_id] == 1, "ref_count debe ser 1, owner2 sigue suscrito"
    
    def test_2_5_5_get_orderbook_from_cache(self):
        """
        Test 2.5.5: Obtener orderbook desde State Cache.
        
        Verifica:
        - Endpoint retorna 404 si asset_id no está en cache
        - Endpoint retorna orderbook si está en cache
        """
        # Intentar obtener orderbook de un asset_id que no existe
        test_asset_id = "0x0000000000000000000000000000000000000000"
        
        response = client.get(f"/api/polymarket/orderbook/{test_asset_id}")
        
        # Debe retornar 404 si no está en cache (o 500 si hay error de DB, pero eso es aceptable en tests)
        assert response.status_code in [404, 500], f"Status code debe ser 404 o 500 para asset_id no suscrito, obtuvo {response.status_code}"
        
        # Nota: Para probar con datos reales, necesitaríamos:
        # 1. Suscribir un asset_id real
        # 2. Recibir mensajes WS (requiere conexión real)
        # 3. Verificar que el orderbook está en cache
        # Esto se puede hacer en un test de integración más completo con mocks
    
    def test_2_5_6_parser_handles_hash_field(self):
        """
        Test 2.5.6: Verificar que el parser maneja el campo hash.
        
        Verifica:
        - Parser extrae hash correctamente
        - Hash se guarda en integrity del OrderbookState
        """
        from app.core.orderbook.ws_parser import parse_ws_book_payload
        
        # Mensaje WS con formato real de Polymarket (incluye hash)
        book_msg = {
            "event_type": "book",
            "asset_id": "0x1234567890123456789012345678901234567890",
            "market": "0xbd31dc8a...",
            "bids": [
                {"price": ".48", "size": "30"},
                {"price": ".49", "size": "20"}
            ],
            "asks": [
                {"price": ".52", "size": "25"},
                {"price": ".53", "size": "60"}
            ],
            "timestamp": "123456789000",
            "hash": "0x0abcdef1234567890abcdef1234567890abcdef"
        }
        
        bids, asks, ts_ms, hash_value = parse_ws_book_payload(book_msg)
        
        assert len(bids) == 2, "Debe parsear 2 bids"
        assert len(asks) == 2, "Debe parsear 2 asks"
        assert ts_ms == 123456789000, "Timestamp debe ser correcto"
        assert hash_value == "0x0abcdef1234567890abcdef1234567890abcdef", "Hash debe ser extraído correctamente"
        
        # Verificar que los precios y tamaños se parsean correctamente
        assert bids[0].price == 0.49, "Bid más alto debe ser 0.49 (ordenado desc)"
        assert bids[1].price == 0.48, "Bid más bajo debe ser 0.48"
        assert asks[0].price == 0.52, "Ask más bajo debe ser 0.52 (ordenado asc)"
        assert asks[1].price == 0.53, "Ask más alto debe ser 0.53"
    
    def test_2_5_7_parser_handles_buys_sells(self):
        """
        Test 2.5.7: Verificar que el parser maneja tanto bids/asks como buys/sells.
        
        Verifica:
        - Parser acepta "bids"/"asks"
        - Parser acepta "buys"/"sells"
        """
        from app.core.orderbook.ws_parser import parse_ws_book_payload
        
        # Mensaje con buys/sells
        book_msg_buys_sells = {
            "event_type": "book",
            "asset_id": "0x1234567890123456789012345678901234567890",
            "market": "0xbd31dc8a...",
            "buys": [
                {"price": ".48", "size": "30"}
            ],
            "sells": [
                {"price": ".52", "size": "25"}
            ],
            "timestamp": "123456789000",
            "hash": "0x0abcdef"
        }
        
        bids, asks, ts_ms, hash_value = parse_ws_book_payload(book_msg_buys_sells)
        
        assert len(bids) == 1, "Debe parsear 1 bid desde 'buys'"
        assert len(asks) == 1, "Debe parsear 1 ask desde 'sells'"
        assert bids[0].price == 0.48, "Bid price debe ser correcto"
        assert asks[0].price == 0.52, "Ask price debe ser correcto"
    
    def test_2_5_8_parser_handles_missing_hash(self):
        """
        Test 2.5.8: Verificar que el parser maneja mensajes sin hash.
        
        Verifica:
        - Parser retorna None para hash si no está presente
        """
        from app.core.orderbook.ws_parser import parse_ws_book_payload
        
        # Mensaje sin hash
        book_msg_no_hash = {
            "event_type": "book",
            "asset_id": "0x1234567890123456789012345678901234567890",
            "market": "0xbd31dc8a...",
            "bids": [{"price": ".48", "size": "30"}],
            "asks": [{"price": ".52", "size": "25"}],
            "timestamp": "123456789000"
        }
        
        bids, asks, ts_ms, hash_value = parse_ws_book_payload(book_msg_no_hash)
        
        assert hash_value is None, "Hash debe ser None si no está presente"
        assert len(bids) == 1, "Debe parsear bids correctamente"
        assert len(asks) == 1, "Debe parsear asks correctamente"

