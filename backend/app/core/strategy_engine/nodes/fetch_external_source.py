"""
Fetch External Source Node - Obtiene datos de una fuente externa.

Solo para Support Graphs (cold path).
Puede tardar, puede llamar APIs, puede usar IA.
"""
import logging
from typing import Dict, Any
from uuid import UUID

from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult, FailureResult
from app.core.connectors.registry import connector_registry
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class FetchExternalSourceNode(GraphNode):
    """
    Nodo que obtiene datos de una fuente externa.
    
    Solo para Support Graphs (cold path).
    Puede tardar, puede llamar APIs.
    Guarda el resultado en context.fetched_data para que otros nodos lo usen.
    """
    
    async def execute(self) -> SuccessResult:
        """
        Obtiene datos de una fuente externa.
        
        Config:
            source_id: UUID - ID de la fuente externa (desde DB)
            endpoint: str - Endpoint a llamar (relativo a base_url)
            params: Dict - Parámetros de query string o body
            headers: Dict - Headers adicionales (opcional)
            method: str - Método HTTP (default: "GET")
            cache_key: str - Clave para guardar en State Cache (opcional)
        
        Requiere:
            - source_id debe existir en external_data_sources
        """
        source_id_str = self.config.get("source_id")
        if not source_id_str:
            return FailureResult("source_id is required")
        
        try:
            source_id = UUID(source_id_str)
        except ValueError:
            return FailureResult(f"Invalid source_id format: {source_id_str}")
        
        endpoint = self.config.get("endpoint", "/")
        params = self.config.get("params", {})
        headers = self.config.get("headers")
        method = self.config.get("method", "GET")
        cache_key = self.config.get("cache_key")
        
        # Obtener conector desde DB
        db = SessionLocal()
        try:
            connector = connector_registry.get_connector_from_db(db, source_id)
        except Exception as e:
            db.close()
            logger.error(f"Error getting connector for source {source_id}: {e}")
            return FailureResult(f"Error getting connector: {str(e)}")
        finally:
            db.close()
        
        # Obtener datos
        try:
            data = await connector.fetch(
                endpoint=endpoint,
                params=params,
                headers=headers,
                method=method
            )
            
            # Guardar en contexto para que otros nodos lo usen
            if not hasattr(self.context, 'fetched_data'):
                self.context.fetched_data = {}
            
            # Guardar con una clave única para esta fuente
            fetch_key = f"source_{source_id}_{endpoint}"
            self.context.fetched_data[fetch_key] = data
            
            # Si se especificó cache_key, guardar también en State Cache
            if cache_key:
                await self.context.state_cache.set(
                    cache_key=cache_key,
                    value=data,
                    strategy_id=self.context.strategy_id,
                    event_id=self.context.event_id,
                    ttl_seconds=self.config.get("ttl_seconds")
                )
            
            return SuccessResult()
        
        except Exception as e:
            logger.error(f"Error fetching from external source {source_id}: {e}")
            return FailureResult(f"Error fetching data: {str(e)}")

