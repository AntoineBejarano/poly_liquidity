"""
Test de Contratos API: Verifica que los endpoints devuelven el formato esperado.

Este test verifica que:
1. Los endpoints devuelven JSON válido
2. Los campos esperados por el frontend están presentes
3. Los tipos de datos son correctos
"""
import pytest
from typing import Dict, Any, List
import json

try:
    import httpx
except ImportError:
    httpx = None

BACKEND_URL = "http://localhost:8000"


# Contratos esperados por el frontend (basados en el código del frontend)
EXPECTED_CONTRACTS = {
    # Series
    ("GET", "/series"): {
        "type": "array",
        "items": {
            "series_id": "string",
            "polymarket_series_id": "string",
            "name": "string",
            "slug": "string|null",
            "description": "string|null",
            "series_type": "string|null",
            "recurrence": "string|null",
            "markets_count": "number",
            "created_at": "string",
            "updated_at": "string"
        }
    },
    
    # Markets
    ("GET", "/markets"): {
        "type": "array",
        "items": {
            "market_id": "string",
            "polymarket_id": "string",
            "name": "string",
            "category": "string|null",
            "enabled": "boolean",
            "series_id": "string|null",
            "series_name": "string|null",
            "tags": "array",
            "events_count": "number",
            "created_at": "string",
            "updated_at": "string"
        }
    },
    
    # Events
    ("GET", "/markets/events/list"): {
        "type": "array",
        "items": {
            "event_id": "string",
            "polymarket_event_id": "string",
            "market_id": "string",
            "market_name": "string",
            "start_time": "string|null",
            "end_time": "string|null",
            "state": "string",  # UPCOMING, ACTIVE, FINISHED
            "created_at": "string",
            "updated_at": "string"
        }
    },
    
    # Tags
    ("GET", "/tags"): {
        "type": "array",
        "items": {
            "tag_id": "string",
            "name": "string"
        }
    },
    
    # Strategies
    ("GET", "/strategies"): {
        "type": "array",
        "items": {
            "id": "string",
            "name": "string",
            "description": "string|null",
            "is_active": "boolean",
            "created_at": "string",
            "updated_at": "string"
        }
    },
    
    # Strategy by ID
    ("GET", "/strategies/{id}"): {
        "type": "object",
        "properties": {
            "id": "string",
            "name": "string",
            "description": "string|null",
            "is_active": "boolean",
            "decision_graph": "object",
            "tags": "array|null"
        }
    },
    
    # Strategy Intents
    ("GET", "/strategies/{id}/intents"): {
        "type": "object",
        "properties": {
            "intents": "array",
            "total": "number"
        }
    },
    
    # Strategy Metrics
    ("GET", "/strategies/{id}/metrics"): {
        "type": "object",
        "properties": {
            "metrics": "array"
        }
    },
}


def check_type(value: Any, expected_type: str) -> bool:
    """Verifica que un valor coincide con el tipo esperado."""
    if expected_type == "string":
        return isinstance(value, str)
    elif expected_type == "number":
        return isinstance(value, (int, float))
    elif expected_type == "boolean":
        return isinstance(value, bool)
    elif expected_type == "array":
        return isinstance(value, list)
    elif expected_type == "object":
        return isinstance(value, dict)
    elif expected_type == "string|null":
        return value is None or isinstance(value, str)
    elif expected_type == "number|null":
        return value is None or isinstance(value, (int, float))
    return False


def validate_contract(data: Any, contract: Dict[str, Any], path: str = "") -> List[str]:
    """Valida que los datos cumplen con el contrato esperado."""
    errors = []
    
    if contract.get("type") == "array":
        if not isinstance(data, list):
            errors.append(f"{path}: Se esperaba array, se recibió {type(data).__name__}")
            return errors
        
        items_contract = contract.get("items", {})
        for i, item in enumerate(data[:5]):  # Validar primeros 5 items
            item_errors = validate_object(item, items_contract, f"{path}[{i}]")
            errors.extend(item_errors)
    
    elif contract.get("type") == "object":
        if not isinstance(data, dict):
            errors.append(f"{path}: Se esperaba object, se recibió {type(data).__name__}")
            return errors
        
        properties = contract.get("properties", {})
        errors.extend(validate_object(data, properties, path))
    
    return errors


def validate_object(obj: Dict[str, Any], properties: Dict[str, str], path: str = "") -> List[str]:
    """Valida que un objeto tiene las propiedades esperadas."""
    errors = []
    
    for prop_name, prop_type in properties.items():
        prop_path = f"{path}.{prop_name}" if path else prop_name
        
        if prop_name not in obj:
            errors.append(f"{prop_path}: Campo faltante")
            continue
        
        value = obj[prop_name]
        if not check_type(value, prop_type):
            errors.append(
                f"{prop_path}: Tipo incorrecto. Esperado: {prop_type}, "
                f"Recibido: {type(value).__name__}"
            )
    
    return errors


@pytest.mark.asyncio
async def test_series_endpoint_contract():
    """Test que verifica el contrato del endpoint /series."""
    if httpx is None:
        pytest.skip("httpx no está instalado. Instalar con: pip install httpx")
    
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as client:
        try:
            response = await client.get("/series")
            if response.status_code == 404:
                pytest.skip("Endpoint /series no existe")
            
            assert response.status_code < 500, f"Error del servidor: {response.status_code}"
            
            if response.status_code == 200:
                data = response.json()
                contract = EXPECTED_CONTRACTS[("GET", "/series")]
                errors = validate_contract(data, contract)
                
                if errors:
                    pytest.fail(f"Contrato no cumplido:\n" + "\n".join(errors))
        except httpx.ConnectError:
            pytest.skip("No se puede conectar al backend")


@pytest.mark.asyncio
async def test_markets_endpoint_contract():
    """Test que verifica el contrato del endpoint /markets."""
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as client:
        try:
            response = await client.get("/markets")
            if response.status_code == 404:
                pytest.skip("Endpoint /markets no existe")
            
            assert response.status_code < 500, f"Error del servidor: {response.status_code}"
            
            if response.status_code == 200:
                data = response.json()
                contract = EXPECTED_CONTRACTS[("GET", "/markets")]
                errors = validate_contract(data, contract)
                
                if errors:
                    pytest.fail(f"Contrato no cumplido:\n" + "\n".join(errors))
        except httpx.ConnectError:
            pytest.skip("No se puede conectar al backend")


@pytest.mark.asyncio
async def test_events_endpoint_contract():
    """Test que verifica el contrato del endpoint /markets/events/list."""
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as client:
        try:
            response = await client.get("/markets/events/list")
            if response.status_code == 404:
                pytest.skip("Endpoint /markets/events/list no existe")
            
            assert response.status_code < 500, f"Error del servidor: {response.status_code}"
            
            if response.status_code == 200:
                data = response.json()
                contract = EXPECTED_CONTRACTS[("GET", "/markets/events/list")]
                errors = validate_contract(data, contract)
                
                if errors:
                    pytest.fail(f"Contrato no cumplido:\n" + "\n".join(errors))
        except httpx.ConnectError:
            pytest.skip("No se puede conectar al backend")


@pytest.mark.asyncio
async def test_tags_endpoint_contract():
    """Test que verifica el contrato del endpoint /tags."""
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as client:
        try:
            response = await client.get("/tags")
            if response.status_code == 404:
                pytest.skip("Endpoint /tags no existe")
            
            assert response.status_code < 500, f"Error del servidor: {response.status_code}"
            
            if response.status_code == 200:
                data = response.json()
                contract = EXPECTED_CONTRACTS[("GET", "/tags")]
                errors = validate_contract(data, contract)
                
                if errors:
                    pytest.fail(f"Contrato no cumplido:\n" + "\n".join(errors))
        except httpx.ConnectError:
            pytest.skip("No se puede conectar al backend")


@pytest.mark.asyncio
async def test_all_endpoints_return_json():
    """Test que verifica que todos los endpoints devuelven JSON válido."""
    endpoints = [
        ("GET", "/series"),
        ("GET", "/markets"),
        ("GET", "/markets/events/list"),
        ("GET", "/tags"),
        ("GET", "/strategies"),
        ("GET", "/system/config"),
    ]
    
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as client:
        for method, path in endpoints:
            try:
                response = await client.request(method, path)
                
                # Si el endpoint existe (no 404) y no es error del servidor
                if response.status_code not in [404, 401, 403] and response.status_code < 500:
                    # Verificar que devuelve JSON
                    content_type = response.headers.get("content-type", "")
                    assert "application/json" in content_type, (
                        f"{method} {path} no devuelve JSON. Content-Type: {content_type}"
                    )
                    
                    # Verificar que es JSON válido
                    try:
                        data = response.json()
                        assert data is not None, f"{method} {path} devuelve JSON null"
                    except json.JSONDecodeError:
                        pytest.fail(f"{method} {path} devuelve JSON inválido")
            except httpx.ConnectError:
                pytest.skip("No se puede conectar al backend")
            except Exception as e:
                # Ignorar errores de endpoints que requieren autenticación
                if response.status_code in [401, 403]:
                    continue
                raise

