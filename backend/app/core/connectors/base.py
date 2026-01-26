"""
Base Connector - Clase base para todos los conectores.

Los conectores son plugins que permiten obtener datos de fuentes externas.
Cada conector implementa una interfaz común para que Support Graphs puedan
usarlos de forma genérica.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """
    Clase base para todos los conectores de fuentes externas.
    
    Los conectores son plugins que permiten obtener datos de fuentes externas
    de forma genérica y configurable.
    """
    
    def __init__(self, connector_config: Dict[str, Any]):
        """
        Inicializa el conector con su configuración.
        
        Args:
            connector_config: Configuración del conector (URLs, API keys, headers, etc.)
        """
        self.config = connector_config
        self.connector_type = self.__class__.__name__.replace("Connector", "").lower()
    
    @abstractmethod
    async def fetch(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """
        Obtiene datos de la fuente externa.
        
        Args:
            endpoint: Endpoint a llamar (relativo a base_url)
            params: Parámetros de query string o body
            headers: Headers adicionales (se combinan con headers de config)
            method: Método HTTP (GET, POST, etc.)
        
        Returns:
            Dict con los datos obtenidos
        
        Raises:
            ConnectorError: Si hay un error al obtener los datos
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Verifica el estado de salud del conector.
        
        Returns:
            Dict con información del estado:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "message": str,
                "latency_ms": float (opcional)
            }
        """
        pass
    
    def get_base_url(self) -> str:
        """Obtiene la URL base del conector desde la configuración."""
        return self.config.get("base_url", "")
    
    def get_api_key(self) -> Optional[str]:
        """Obtiene la API key del conector desde la configuración."""
        return self.config.get("api_key")
    
    def get_headers(self) -> Dict[str, str]:
        """Obtiene los headers del conector desde la configuración."""
        return self.config.get("headers", {})
    
    def get_timeout(self) -> float:
        """Obtiene el timeout del conector desde la configuración."""
        return self.config.get("timeout_seconds", 30.0)


class ConnectorError(Exception):
    """Excepción para errores de conectores."""
    pass

