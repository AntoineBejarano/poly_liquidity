"""
Update State Cache Node - Actualiza State Cache.

Solo para Support Graphs (cold path).
Escribe en State Cache para que Decision Graph pueda leer.
"""
import logging
from typing import Dict, Any

from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult, FailureResult

logger = logging.getLogger(__name__)


class UpdateStateCacheNode(GraphNode):
    """
    Nodo que actualiza State Cache.
    
    Solo para Support Graphs (cold path).
    Escribe en State Cache para que Decision Graph pueda leer.
    """
    
    async def execute(self) -> SuccessResult:
        """
        Actualiza State Cache.
        
        Config:
            key: str - Clave del cache (requerido)
            value: Any - Valor a guardar (requerido)
            ttl_seconds: int - Tiempo de vida en segundos (opcional)
            value_from_context: str - Ruta en context para obtener el valor (opcional)
                Ejemplo: "fetched_data.source_123_/api/events"
        
        Si se especifica value_from_context, se usa ese valor en lugar de value.
        """
        cache_key = self.config.get("key")
        if not cache_key:
            return FailureResult("cache key is required")
        
        # Obtener valor
        value = self.config.get("value")
        
        # Si se especifica value_from_context, obtener desde el contexto
        value_from_context = self.config.get("value_from_context")
        if value_from_context:
            value = self._get_value_from_context(value_from_context)
            if value is None:
                return FailureResult(f"Value not found in context at path: {value_from_context}")
        
        if value is None:
            return FailureResult("value is required")
        
        # Guardar en State Cache
        try:
            await self.context.state_cache.set(
                cache_key=cache_key,
                value=value,
                strategy_id=self.context.strategy_id,
                event_id=self.context.event_id,
                ttl_seconds=self.config.get("ttl_seconds")
            )
            
            logger.debug(
                f"Updated State Cache: {cache_key} for strategy {self.context.strategy_id}, "
                f"event {self.context.event_id}"
            )
            
            return SuccessResult()
        
        except Exception as e:
            logger.error(f"Error updating State Cache: {e}")
            return FailureResult(f"Error updating State Cache: {str(e)}")
    
    def _get_value_from_context(self, path: str) -> Any:
        """
        Obtiene un valor desde el contexto usando una ruta.
        
        Ejemplo: "fetched_data.source_123_/api/events"
        """
        parts = path.split(".")
        value = self.context
        
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            
            if value is None:
                return None
        
        return value

