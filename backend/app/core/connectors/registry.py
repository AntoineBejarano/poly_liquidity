"""
Connector Registry - Registro de conectores disponibles.

Permite registrar y obtener conectores de forma dinámica.
"""
import logging
from typing import Dict, Type, Optional
from sqlalchemy.orm import Session

from app.core.connectors.base import BaseConnector, ConnectorError
from app.models.external_data_source import ExternalDataSource

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """
    Registro de conectores disponibles.
    
    Permite registrar tipos de conectores y obtener instancias
    de conectores desde la base de datos.
    """
    
    def __init__(self):
        self._connector_classes: Dict[str, Type[BaseConnector]] = {}
    
    def register(self, connector_type: str, connector_class: Type[BaseConnector]):
        """
        Registra un tipo de conector.
        
        Args:
            connector_type: Tipo de conector (ej. "pinnacle", "bet365", "custom_api")
            connector_class: Clase del conector (debe heredar de BaseConnector)
        """
        if not issubclass(connector_class, BaseConnector):
            raise ValueError(f"Connector class must inherit from BaseConnector")
        
        self._connector_classes[connector_type] = connector_class
        logger.info(f"Registered connector type: {connector_type}")
    
    def get_connector(
        self,
        connector_type: str,
        connector_config: Dict[str, Any]
    ) -> BaseConnector:
        """
        Obtiene una instancia de un conector.
        
        Args:
            connector_type: Tipo de conector
            connector_config: Configuración del conector
        
        Returns:
            Instancia del conector
        
        Raises:
            ConnectorError: Si el tipo de conector no está registrado
        """
        connector_class = self._connector_classes.get(connector_type)
        if not connector_class:
            raise ConnectorError(f"Connector type '{connector_type}' not registered")
        
        return connector_class(connector_config)
    
    def get_connector_from_db(
        self,
        db: Session,
        source_id: UUID
    ) -> BaseConnector:
        """
        Obtiene un conector desde la base de datos.
        
        Args:
            db: Sesión de base de datos
            source_id: ID de la fuente externa
        
        Returns:
            Instancia del conector
        
        Raises:
            ConnectorError: Si la fuente no existe o el tipo no está registrado
        """
        source = db.query(ExternalDataSource).filter(
            ExternalDataSource.id == source_id
        ).first()
        
        if not source:
            raise ConnectorError(f"External data source {source_id} not found")
        
        if not source.is_active:
            raise ConnectorError(f"External data source {source_id} is not active")
        
        return self.get_connector(source.connector_type, source.connector_config)
    
    def list_connector_types(self) -> list[str]:
        """Lista todos los tipos de conectores registrados."""
        return list(self._connector_classes.keys())


# Instancia global del registro
connector_registry = ConnectorRegistry()

