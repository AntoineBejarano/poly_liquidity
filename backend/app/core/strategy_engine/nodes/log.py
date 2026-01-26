"""
Log Node - Nodo de logging para Support Graphs.

Útil para debugging y trazabilidad en Support Graphs.
"""
import logging
from typing import Dict, Any

from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult

logger = logging.getLogger(__name__)


class LogNode(GraphNode):
    """
    Nodo que registra información en los logs.
    
    Útil para debugging y trazabilidad en Support Graphs.
    """
    
    async def execute(self) -> SuccessResult:
        """
        Registra información en los logs.
        
        Config:
            level: str - Nivel de log ("DEBUG", "INFO", "WARNING", "ERROR") (default: "INFO")
            message: str - Mensaje a registrar (requerido)
            data: Dict - Datos adicionales a incluir (opcional)
            include_context: bool - Incluir información del contexto (default: True)
        """
        level = self.config.get("level", "INFO").upper()
        message = self.config.get("message", "")
        data = self.config.get("data", {})
        include_context = self.config.get("include_context", True)
        
        # Construir mensaje completo
        log_data = {}
        if include_context:
            log_data.update({
                "strategy_id": str(self.context.strategy_id),
                "event_id": str(self.context.event_id),
                "trace_id": str(self.context.trace_id)
            })
        
        if data:
            log_data.update(data)
        
        # Log según nivel
        if level == "DEBUG":
            logger.debug(message, extra=log_data)
        elif level == "INFO":
            logger.info(message, extra=log_data)
        elif level == "WARNING":
            logger.warning(message, extra=log_data)
        elif level == "ERROR":
            logger.error(message, extra=log_data)
        else:
            logger.info(message, extra=log_data)
        
        return SuccessResult()

