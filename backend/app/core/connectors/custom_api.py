"""
Custom API Connector - Conector genérico para APIs REST.

Permite conectarse a cualquier API REST configurando:
- Base URL
- API Key (opcional)
- Headers personalizados
- Timeout
"""
import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.connectors.base import BaseConnector, ConnectorError

logger = logging.getLogger(__name__)


class CustomAPIConnector(BaseConnector):
    """
    Conector genérico para APIs REST.
    
    Permite conectarse a cualquier API REST configurando:
    - base_url: URL base de la API
    - api_key: API key (opcional, se envía como header o query param)
    - api_key_header: Nombre del header para la API key (default: "X-API-Key")
    - headers: Headers adicionales
    - timeout_seconds: Timeout en segundos (default: 30)
    """
    
    async def fetch(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """
        Obtiene datos de la API.
        
        Args:
            endpoint: Endpoint relativo a base_url (ej. "/api/events")
            params: Parámetros (query string para GET, body para POST)
            headers: Headers adicionales
            method: Método HTTP
        
        Returns:
            Dict con los datos obtenidos
        """
        base_url = self.get_base_url()
        if not base_url:
            raise ConnectorError("base_url not configured")
        
        # Construir URL completa
        if endpoint.startswith("/"):
            url = f"{base_url.rstrip('/')}{endpoint}"
        else:
            url = f"{base_url.rstrip('/')}/{endpoint}"
        
        # Preparar headers
        request_headers = self.get_headers().copy()
        
        # Agregar API key si existe
        api_key = self.get_api_key()
        if api_key:
            api_key_header = self.config.get("api_key_header", "X-API-Key")
            request_headers[api_key_header] = api_key
        
        # Combinar con headers adicionales
        if headers:
            request_headers.update(headers)
        
        # Realizar request
        timeout = self.get_timeout()
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(url, params=params, headers=request_headers)
                elif method.upper() == "POST":
                    response = await client.post(url, json=params, headers=request_headers)
                elif method.upper() == "PUT":
                    response = await client.put(url, json=params, headers=request_headers)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=request_headers)
                else:
                    raise ConnectorError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                
                # Intentar parsear como JSON
                try:
                    return response.json()
                except Exception:
                    # Si no es JSON, retornar texto
                    return {"raw": response.text}
        
        except httpx.HTTPStatusError as e:
            raise ConnectorError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.TimeoutException:
            raise ConnectorError(f"Request timeout after {timeout}s")
        except Exception as e:
            raise ConnectorError(f"Request failed: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Verifica el estado de salud del conector.
        
        Intenta hacer un request simple a la API.
        """
        base_url = self.get_base_url()
        if not base_url:
            return {
                "status": "unhealthy",
                "message": "base_url not configured"
            }
        
        # Intentar hacer un request simple
        health_endpoint = self.config.get("health_endpoint", "/health")
        
        try:
            start_time = datetime.utcnow()
            await self.fetch(health_endpoint, method="GET")
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "status": "healthy",
                "message": "API is reachable",
                "latency_ms": latency_ms
            }
        except ConnectorError as e:
            return {
                "status": "unhealthy",
                "message": str(e)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Unexpected error: {str(e)}"
            }

