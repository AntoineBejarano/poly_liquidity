"""
Clase base abstracta para proveedores de señales.

Implementa funcionalidades comunes:
- Validación de freshness de datos (Stale Data Protection)
- Sistema de memoización para evitar cálculos redundantes
- Propiedades para acceder a estados recopilados
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SignalProvider(ABC):
    """
    Clase base abstracta para proveedores de señales.
    
    Implementa funcionalidades comunes para todos los proveedores:
    - Validación de freshness de datos (Stale Data Protection)
    - Sistema de memoización para evitar cálculos redundantes
    - Propiedades para acceder a estados recopilados
    """
    
    def __init__(self, context: 'GraphExecutionContext'):
        """
        Inicializa el proveedor de señales.
        
        Args:
            context: Contexto de ejecución del grafo
        """
        self.context = context
        self._collected_state = getattr(context, 'collected_state', {})
        self._memo_cache: Dict[str, Any] = {}  # Cache para memoización
        self._memo_timestamps: Dict[str, datetime] = {}  # Timestamps de cache
    
    @property
    def market_state(self) -> Optional[Dict[str, Any]]:
        """Obtiene el estado del mercado desde collected_state."""
        return self._collected_state.get("market_state")
    
    @property
    def event_state(self) -> Optional[Dict[str, Any]]:
        """Obtiene el estado del evento desde collected_state."""
        return self._collected_state.get("event_state")
    
    @property
    def external_data(self) -> Optional[Dict[str, Any]]:
        """Obtiene los datos externos desde collected_state."""
        return self._collected_state.get("external_data")
    
    @property
    def risk_state(self) -> Optional[Dict[str, Any]]:
        """Obtiene el estado de riesgo desde collected_state."""
        return self._collected_state.get("risk_state")
    
    def check_data_freshness(
        self, 
        data: Dict[str, Any], 
        timestamp_key: str = "last_update",
        max_age_ms: int = 5000
    ) -> bool:
        """
        ⚠️ ALERTA DE COMBATE: Valida que los datos no sean obsoletos.
        
        Problema: Un indicador puede tener datos, pero si el orderbook es de hace 10 segundos,
        el book_imbalance es peligroso.
        
        Args:
            data: Diccionario con los datos a validar
            timestamp_key: Clave donde está el timestamp (default: "last_update")
            max_age_ms: Edad máxima permitida en milisegundos (default: 5000ms = 5 segundos)
        
        Returns:
            True si los datos son frescos, False si son obsoletos
        """
        if not data:
            return False
        
        timestamp = data.get(timestamp_key)
        if timestamp is None:
            # Si no hay timestamp, asumir que los datos son frescos (compatibilidad)
            # Pero loggear advertencia
            logger.warning(
                f"Data missing timestamp key '{timestamp_key}', assuming fresh",
                extra={"data_keys": list(data.keys())}
            )
            return True
        
        # Convertir timestamp a datetime si es string o número
        if isinstance(timestamp, str):
            try:
                # Intentar parsear ISO format
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                logger.warning(f"Invalid timestamp format: {timestamp}")
                return False
        elif isinstance(timestamp, (int, float)):
            # Asumir que es Unix timestamp en segundos o milisegundos
            if timestamp > 1e10:  # Milisegundos
                timestamp = datetime.fromtimestamp(timestamp / 1000)
            else:  # Segundos
                timestamp = datetime.fromtimestamp(timestamp)
        elif not isinstance(timestamp, datetime):
            logger.warning(f"Unknown timestamp type: {type(timestamp)}")
            return False
        
        # Calcular edad
        now = datetime.utcnow()
        if timestamp.tzinfo:
            # Si el timestamp tiene timezone, usar datetime.now con timezone
            from datetime import timezone
            now = datetime.now(timezone.utc)
        
        age_ms = (now - timestamp).total_seconds() * 1000
        
        if age_ms > max_age_ms:
            logger.warning(
                f"Data is stale: {age_ms:.0f}ms old (max: {max_age_ms}ms)",
                extra={"age_ms": age_ms, "max_age_ms": max_age_ms}
            )
            return False
        
        return True
    
    def memoize(self, key: str, func: Callable, *args, **kwargs) -> Any:
        """
        ⚠️ ALERTA DE COMBATE: Sistema de memoización para evitar cálculos redundantes.
        
        Problema: Si tienes 20 indicadores y cada uno hace cálculos pesados (ej. procesar
        historial de precios), podrías ralentizar el ControlLoop.
        
        Solución: Si price_drift y tw_volatility usan ambos el historial de precios,
        procesar ese historial una sola vez por tick.
        
        Args:
            key: Clave única para el cache
            func: Función a ejecutar (solo si no está en cache)
            *args, **kwargs: Argumentos para la función
        
        Returns:
            Resultado de la función (desde cache o calculado)
        """
        # Verificar si está en cache y es válido
        if key in self._memo_cache:
            # El cache es válido para este tick (mismo contexto)
            return self._memo_cache[key]
        
        # Calcular y guardar en cache
        result = func(*args, **kwargs)
        self._memo_cache[key] = result
        self._memo_timestamps[key] = datetime.utcnow()
        
        return result
    
    def clear_memo_cache(self):
        """Limpia el cache de memoización (útil para testing o reset)."""
        self._memo_cache.clear()
        self._memo_timestamps.clear()
    
    @abstractmethod
    def validate_data(self) -> bool:
        """
        Valida que los datos necesarios estén disponibles.
        
        Returns:
            True si los datos son válidos, False en caso contrario
        """
        pass
    
    @abstractmethod
    def calculate_all(self) -> Dict[str, Optional[float]]:
        """
        Calcula todos los indicadores.
        
        Returns:
            Dict con claves de indicadores y valores (None si no se puede calcular)
        """
        pass

