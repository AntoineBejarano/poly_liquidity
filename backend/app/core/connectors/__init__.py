"""
Sistema de Conectores para fuentes de datos externas.

Los conectores son plugins que permiten obtener datos de fuentes externas
(Pinnacle, Bet365, APIs custom, etc.) de forma genérica y configurable.
"""
from app.core.connectors.base import BaseConnector, ConnectorError
from app.core.connectors.registry import ConnectorRegistry, connector_registry
from app.core.connectors.custom_api import CustomAPIConnector

__all__ = [
    "BaseConnector",
    "ConnectorError",
    "ConnectorRegistry",
    "connector_registry",
    "CustomAPIConnector",
]

# Registrar conectores built-in
connector_registry.register("custom_api", CustomAPIConnector)
