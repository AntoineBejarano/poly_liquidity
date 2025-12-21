"""
Trigger Evaluator - Evalúa condiciones de triggers para activar Decision Graph.

Los triggers son condiciones explícitas que determinan cuándo ejecutar el Decision Graph.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.models.strategy import Strategy
from app.models.event import Event
from app.core.strategy_engine.state_cache_service import StateCacheService


class TriggerEvaluator:
    """
    Evaluador de triggers para estrategias.
    
    Evalúa si un trigger debe activarse basándose en:
    - Tipo de trigger
    - Condiciones específicas
    - Estado del evento
    - Estado del cache
    """
    
    def __init__(self, state_cache: StateCacheService):
        self.state_cache = state_cache
    
    def evaluate(
        self,
        trigger: Dict[str, Any],
        strategy: Strategy,
        event: Event,
        state_cache: Optional[StateCacheService] = None
    ) -> bool:
        """
        Evalúa si un trigger debe activarse.
        
        Args:
            trigger: Definición del trigger
            strategy: Estrategia que contiene el trigger
            event: Evento a evaluar
            state_cache: StateCacheService (opcional, usa self.state_cache si no se proporciona)
        
        Returns:
            True si el trigger debe activarse, False en caso contrario
        """
        if state_cache is None:
            state_cache = self.state_cache
        
        trigger_type = trigger.get("type")
        
        if trigger_type == "always":
            return self._evaluate_always(trigger)
        elif trigger_type == "near_end":
            return self._evaluate_near_end(trigger, event)
        elif trigger_type == "edge_detected":
            return self._evaluate_edge_detected(trigger, event, state_cache)
        elif trigger_type == "state_change":
            return self._evaluate_state_change(trigger, event, state_cache)
        elif trigger_type == "timer":
            return self._evaluate_timer(trigger, strategy, event)
        else:
            # Tipo desconocido, no activar
            return False
    
    def _evaluate_always(self, trigger: Dict[str, Any]) -> bool:
        """
        Evalúa trigger tipo 'always'.
        
        Siempre retorna True (ejecutar en cada tick).
        """
        return True
    
    def _evaluate_near_end(self, trigger: Dict[str, Any], event: Event) -> bool:
        """
        Evalúa trigger tipo 'near_end'.
        
        Verifica si el evento está cerca del final (dentro del rango especificado).
        
        Condiciones soportadas:
            - time_to_resolution_lte: Tiempo máximo hasta resolución (ej: "20m")
            - time_to_resolution_gte: Tiempo mínimo hasta resolución (ej: "5m")
        """
        if not event.resolution_date:
            return False
        
        conditions = trigger.get("conditions", {})
        now = datetime.utcnow()
        time_to_resolution = event.resolution_date - now
        
        # Verificar límite superior
        if "time_to_resolution_lte" in conditions:
            max_time = self._parse_time_delta(conditions["time_to_resolution_lte"])
            if time_to_resolution > max_time:
                return False
        
        # Verificar límite inferior
        if "time_to_resolution_gte" in conditions:
            min_time = self._parse_time_delta(conditions["time_to_resolution_gte"])
            if time_to_resolution < min_time:
                return False
        
        return True
    
    def _evaluate_edge_detected(self, trigger: Dict[str, Any], event: Event, state_cache: StateCacheService) -> bool:
        """
        Evalúa trigger tipo 'edge_detected'.
        
        Verifica si hay un edge detectado en el estado.
        
        Condiciones soportadas:
            - min_edge: Edge mínimo requerido (float)
            - source: Fuente del edge (opcional, ej: "external_data.pinnacle_odds")
        """
        conditions = trigger.get("conditions", {})
        min_edge = conditions.get("min_edge", 0.0)
        
        # Obtener estado del cache
        state = state_cache.get_state(event.id)
        if not state:
            return False
        
        # Buscar edge en external_data o market_state
        external_data = state.get("external_data", {})
        market_state = state.get("market_state", {})
        
        # Buscar edge en external_data
        if isinstance(external_data, dict):
            edge = external_data.get("edge")
            if edge is not None and edge >= min_edge:
                # Verificar source si se especifica
                source = conditions.get("source")
                if source:
                    # Verificar que el edge viene de la fuente especificada
                    edge_source = external_data.get("edge_source")
                    if edge_source == source or (source in str(external_data)):
                        return True
                else:
                    return True
        
        # Buscar edge en market_state
        if isinstance(market_state, dict):
            edge = market_state.get("edge")
            if edge is not None and edge >= min_edge:
                return True
        
        return False
    
    def _evaluate_state_change(self, trigger: Dict[str, Any], event: Event, state_cache: StateCacheService) -> bool:
        """
        Evalúa trigger tipo 'state_change'.
        
        Verifica si un campo específico del estado cambió a un valor específico.
        
        Condiciones soportadas:
            - field: Campo a verificar (ej: "event_state.state")
            - values: Lista de valores que activan el trigger (ej: ["ACTIVE"])
        """
        conditions = trigger.get("conditions", {})
        field = conditions.get("field")
        target_values = conditions.get("values", [])
        
        if not field or not target_values:
            return False
        
        # Obtener estado del cache
        state = state_cache.get_state(event.id)
        if not state:
            return False
        
        # Resolver campo anidado (ej: "event_state.state")
        value = self._get_nested_value(state, field)
        
        return value in target_values
    
    def _evaluate_timer(self, trigger: Dict[str, Any], strategy: Strategy, event: Event) -> bool:
        """
        Evalúa trigger tipo 'timer'.
        
        Verifica si ha pasado el intervalo especificado desde la última ejecución.
        
        Condiciones soportadas:
            - interval_seconds: Intervalo en segundos
        """
        conditions = trigger.get("conditions", {})
        interval_seconds = conditions.get("interval_seconds", 60)
        
        # Por ahora, siempre retornar True si es timer
        # En el futuro, se puede implementar tracking de última ejecución
        # usando una tabla o cache para rastrear last_execution_time por (strategy_id, event_id)
        return True
    
    def _parse_time_delta(self, time_str: str) -> timedelta:
        """
        Parsea un string de tiempo a timedelta.
        
        Formatos soportados:
            - "20m" -> 20 minutos
            - "1h" -> 1 hora
            - "30s" -> 30 segundos
            - "1d" -> 1 día
        """
        time_str = time_str.strip().lower()
        
        if time_str.endswith("s"):
            seconds = int(time_str[:-1])
            return timedelta(seconds=seconds)
        elif time_str.endswith("m"):
            minutes = int(time_str[:-1])
            return timedelta(minutes=minutes)
        elif time_str.endswith("h"):
            hours = int(time_str[:-1])
            return timedelta(hours=hours)
        elif time_str.endswith("d"):
            days = int(time_str[:-1])
            return timedelta(days=days)
        else:
            # Intentar parsear como número (asumir segundos)
            try:
                seconds = int(time_str)
                return timedelta(seconds=seconds)
            except ValueError:
                raise ValueError(f"Invalid time format: {time_str}")
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """
        Obtiene un valor anidado de un diccionario usando un path.
        
        Ejemplo:
            data = {"event_state": {"state": "ACTIVE"}}
            field_path = "event_state.state"
            retorna "ACTIVE"
        """
        if not field_path:
            return None
        
        parts = field_path.split(".")
        value = data
        
        for part in parts:
            if not part:  # Skip partes vacías
                continue
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    return None
            else:
                return None
        
        return value

