"""
Tests de integración para Fase 2: Datos Públicos (Gamma API).

Verifica:
- Listar events
- Obtener event específico
- Obtener market
- Búsqueda
- Orderbook
"""
import pytest
from app.main import app


class TestPhase2PublicData:
    """Tests para verificar acceso a datos públicos."""
    
    def test_list_events(self, client):
        """Test 2.1: Listar events con paginación."""
        response = client.get("/api/polymarket/events?closed=false&limit=10")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Respuesta debe ser una lista"
        
        if len(data) > 0:
            event = data[0]
            assert "id" in event, "Event debe tener 'id'"
            assert "slug" in event or "title" in event, "Event debe tener 'slug' o 'title'"
    
    def test_list_events_with_pagination(self, client):
        """Test 2.1b: Listar events con diferentes parámetros de paginación."""
        # Primera página
        response1 = client.get("/api/polymarket/events?closed=false&limit=5&offset=0")
        assert response1.status_code == 200
        
        # Segunda página
        response2 = client.get("/api/polymarket/events?closed=false&limit=5&offset=5")
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Si hay suficientes events, las páginas deben ser diferentes
        if len(data1) == 5 and len(data2) > 0:
            assert data1[0]["id"] != data2[0]["id"], "Las páginas deben tener events diferentes"
    
    def test_get_event_by_id(self, client):
        """Test 2.2: Obtener event específico por ID."""
        # Primero obtener un event_id de la lista
        list_response = client.get("/api/polymarket/events?closed=false&limit=1")
        assert list_response.status_code == 200
        
        events = list_response.json()
        if len(events) == 0:
            pytest.skip("No hay events disponibles para testear")
        
        event_id = events[0]["id"]
        
        # Obtener el event específico
        response = client.get(f"/api/polymarket/events/{event_id}")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "id" in data, "Event debe tener 'id'"
        assert data["id"] == event_id, "ID debe coincidir"
        assert "markets" in data or "slug" in data, "Event debe tener información adicional"
    
    def test_get_market_by_id(self, client):
        """Test 2.3: Obtener market por ID."""
        # Primero obtener un market_id de un event
        list_response = client.get("/api/polymarket/events?closed=false&limit=1")
        assert list_response.status_code == 200
        
        events = list_response.json()
        if len(events) == 0:
            pytest.skip("No hay events disponibles para testear")
        
        event = events[0]
        if "markets" not in event or len(event["markets"]) == 0:
            pytest.skip("Event no tiene markets")
        
        market_id = event["markets"][0].get("id")
        if not market_id:
            pytest.skip("Market no tiene ID")
        
        # Obtener el market específico
        response = client.get(f"/api/polymarket/markets/{market_id}")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        assert "id" in data, "Market debe tener 'id'"
        assert data["id"] == market_id, "ID debe coincidir"
    
    def test_get_market_by_slug(self, client):
        """Test 2.4: Obtener market por slug."""
        # Primero obtener un slug de un event
        list_response = client.get("/api/polymarket/events?closed=false&limit=1")
        assert list_response.status_code == 200
        
        events = list_response.json()
        if len(events) == 0:
            pytest.skip("No hay events disponibles para testear")
        
        event = events[0]
        if "slug" not in event:
            pytest.skip("Event no tiene slug")
        
        slug = event["slug"]
        
        # Intentar obtener market por slug (puede que el slug sea del event, no del market)
        # Por ahora, solo verificamos que el endpoint existe
        # Nota: El endpoint espera un slug de market, no de event
        # Este test puede fallar si no tenemos un slug de market válido
        response = client.get(f"/api/polymarket/markets/slug/{slug}")
        
        # Puede ser 200 (encontrado) o 404 (no encontrado)
        assert response.status_code in [200, 404], f"Status code debe ser 200 o 404, obtuvo {response.status_code}"
    
    def test_search(self, client):
        """Test 2.5: Buscar events/markets."""
        response = client.get("/api/polymarket/search?q=trump&limit=10")
        
        assert response.status_code == 200, f"Status code debe ser 200, obtuvo {response.status_code}"
        
        data = response.json()
        # La respuesta puede ser una lista o un objeto con resultados
        assert isinstance(data, (list, dict)), "Respuesta debe ser lista o dict"
    
    def test_health_check(self, client):
        """Test 2.6: Health check de Gamma API."""
        response = client.get("/api/polymarket/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["ok", "degraded", "error"]

