"""
Observability Service - Emite métricas y eventos según observability_config.

Este servicio permite configurar qué métricas y eventos se emiten
para cada estrategia y nodo.
"""
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

logger = logging.getLogger(__name__)


class ObservabilityService:
    """
    Servicio de observabilidad para estrategias.
    
    Emite métricas y eventos según la configuración de observability_config.
    """
    
    def __init__(self):
        """Inicializa el servicio de observabilidad."""
        self._metrics_service = None
        self._event_bus = None
    
    def _get_metrics_service(self):
        """Obtiene el servicio de métricas (lazy import)."""
        if self._metrics_service is None:
            try:
                from app.core.metrics import Metrics
                metrics = Metrics()
                self._metrics_service = metrics.service
            except ImportError:
                logger.warning("Metrics service not available")
        return self._metrics_service
    
    def _get_event_bus(self):
        """Obtiene el event bus (lazy import)."""
        if self._event_bus is None:
            try:
                from app.core.live_control.event_bus import get_event_bus
                self._event_bus = get_event_bus()
            except ImportError:
                logger.warning("Event bus not available")
        return self._event_bus
    
    def emit_metric(
        self,
        strategy_id: UUID,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, Any]] = None,
        observability_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emite una métrica si está habilitada en observability_config.
        
        Args:
            strategy_id: ID de la estrategia
            metric_name: Nombre de la métrica
            value: Valor de la métrica
            tags: Tags adicionales
            observability_config: Configuración de observabilidad
        """
        # Por defecto, emitir métricas si no hay config o si está explícitamente habilitado
        if observability_config and observability_config.get("emit_metrics") is False:
            return
        
        try:
            metrics_service = self._get_metrics_service()
            if metrics_service:
                # Emitir métrica usando el sistema existente
                # Por ahora, solo loggeamos (el sistema de métricas se integra después)
                logger.debug(
                    f"Metric: strategy={strategy_id}, name={metric_name}, value={value}, tags={tags}"
                )
        except Exception as e:
            logger.warning(f"Error emitting metric: {e}")
    
    def emit_event(
        self,
        strategy_id: UUID,
        event_type: str,
        data: Dict[str, Any],
        observability_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emite un evento si está habilitado en observability_config.
        
        Args:
            strategy_id: ID de la estrategia
            event_type: Tipo de evento
            data: Datos del evento
            observability_config: Configuración de observabilidad
        """
        # Por defecto, emitir eventos si no hay config o si está explícitamente habilitado
        if observability_config and observability_config.get("emit_events") is False:
            return
        
        try:
            event_bus = self._get_event_bus()
            if event_bus:
                # Añadir metadata de estrategia
                event_data = {
                    **data,
                    "strategy_id": str(strategy_id),
                    "timestamp": datetime.utcnow().isoformat()
                }
                event_bus.emit(event_type, event_data)
        except Exception as e:
            logger.warning(f"Error emitting event: {e}")
    
    def log_node_execution(
        self,
        strategy_id: UUID,
        node_id: str,
        node_type: str,
        duration_ms: float,
        success: bool,
        error: Optional[str] = None,
        observability_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Registra la ejecución de un nodo.
        
        Args:
            strategy_id: ID de la estrategia
            node_id: ID del nodo
            node_type: Tipo del nodo
            duration_ms: Duración en milisegundos
            success: Si la ejecución fue exitosa
            error: Mensaje de error si hubo
            observability_config: Configuración de observabilidad
        """
        log_level = observability_config.get("log_level", "INFO") if observability_config else "INFO"
        
        # Verificar si el nodo tiene configuración específica
        node_config = observability_config.get("nodes", {}).get(node_id, {}) if observability_config else {}
        node_log_level = node_config.get("log_level", log_level)
        
        # Emitir métrica de duración
        self.emit_metric(
            strategy_id=strategy_id,
            metric_name=f"node_execution_duration_ms",
            value=duration_ms,
            tags={"node_id": node_id, "node_type": node_type, "success": success},
            observability_config=observability_config
        )
        
        # Emitir métrica de éxito/fallo
        self.emit_metric(
            strategy_id=strategy_id,
            metric_name=f"node_execution_{'success' if success else 'failure'}",
            value=1.0,
            tags={"node_id": node_id, "node_type": node_type},
            observability_config=observability_config
        )
        
        # Log según nivel
        if node_log_level == "DEBUG":
            logger.debug(
                f"Node execution: strategy={strategy_id}, node={node_id}, "
                f"type={node_type}, duration={duration_ms}ms, success={success}"
            )
        elif node_log_level == "INFO" or (not success and node_log_level in ["WARNING", "ERROR"]):
            if success:
                logger.info(
                    f"Node execution: strategy={strategy_id}, node={node_id}, "
                    f"type={node_type}, duration={duration_ms}ms"
                )
            else:
                logger.warning(
                    f"Node execution failed: strategy={strategy_id}, node={node_id}, "
                    f"type={node_type}, error={error}"
                )
        # NOTA: El siguiente elif es código muerto porque el elif anterior (línea 166)
        # siempre captura el caso cuando node_log_level == "ERROR" y not success.
        # Se mantiene por compatibilidad, pero nunca se ejecuta en la práctica.
        # elif not success and node_log_level == "ERROR":
        #     logger.error(
        #         f"Node execution error: strategy={strategy_id}, node={node_id}, "
        #         f"type={node_type}, error={error}"
        #     )


# Instancia global
_observability_service: Optional[ObservabilityService] = None


def get_observability_service() -> ObservabilityService:
    """Obtiene la instancia global del servicio de observabilidad."""
    global _observability_service
    if _observability_service is None:
        _observability_service = ObservabilityService()
    return _observability_service

