"""
Circuit Breaker - protección contra fallos en cascada.
"""
from enum import Enum
from typing import Optional, Dict
from datetime import datetime, timedelta
from collections import deque


class CircuitBreakerState(str, Enum):
    """Estado de circuit breaker."""
    CLOSED = "CLOSED"      # Funcionando normal
    OPEN = "OPEN"          # Bloqueado
    HALF_OPEN = "HALF_OPEN"  # Probando recuperación


class CircuitBreaker:
    """
    Circuit Breaker base.
    
    Protege contra fallos en cascada abriendo el circuito cuando
    se detectan demasiados fallos en una ventana de tiempo.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        window_seconds: int = 60,
        cooldown_seconds: int = 300,
        half_open_max_attempts: int = 3
    ):
        """
        Inicializa el circuit breaker.
        
        Args:
            name: Nombre del circuit breaker
            failure_threshold: Número de fallos antes de abrir
            window_seconds: Ventana de tiempo para contar fallos
            cooldown_seconds: Tiempo de espera antes de intentar recuperación
            half_open_max_attempts: Intentos máximos en modo HALF_OPEN
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self.half_open_max_attempts = half_open_max_attempts
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_times: deque = deque(maxlen=failure_threshold * 2)
        self.opened_at: Optional[datetime] = None
        self.half_open_attempts = 0
    
    def record_success(self):
        """Registra un éxito."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            # Si estamos en HALF_OPEN y tenemos éxito, cerrar el circuito
            self.state = CircuitBreakerState.CLOSED
            self.half_open_attempts = 0
            self.opened_at = None
        elif self.state == CircuitBreakerState.CLOSED:
            # Limpiar fallos antiguos
            self._clean_old_failures()
    
    def record_failure(self):
        """Registra un fallo."""
        now = datetime.utcnow()
        self.failure_times.append(now)
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            # Si fallamos en HALF_OPEN, volver a abrir
            self.state = CircuitBreakerState.OPEN
            self.opened_at = now
            self.half_open_attempts = 0
        elif self.state == CircuitBreakerState.CLOSED:
            # Verificar si debemos abrir el circuito
            if self._should_open():
                self.state = CircuitBreakerState.OPEN
                self.opened_at = now
    
    def _should_open(self) -> bool:
        """Verifica si el circuito debe abrirse."""
        if len(self.failure_times) < self.failure_threshold:
            return False
        
        # Contar fallos en la ventana de tiempo
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        recent_failures = [
            ft for ft in self.failure_times
            if ft >= window_start
        ]
        
        return len(recent_failures) >= self.failure_threshold
    
    def _clean_old_failures(self):
        """Limpia fallos fuera de la ventana de tiempo."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        self.failure_times = deque(
            [ft for ft in self.failure_times if ft >= window_start],
            maxlen=self.failure_threshold * 2
        )
    
    def can_attempt(self) -> bool:
        """
        Verifica si se puede intentar una operación.
        
        Returns:
            True si el circuito está CLOSED o HALF_OPEN, False si está OPEN
        """
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            # Verificar si ha pasado el cooldown
            if self.opened_at is None:
                return False
            
            now = datetime.utcnow()
            elapsed = (now - self.opened_at).total_seconds()
            
            if elapsed >= self.cooldown_seconds:
                # Intentar recuperación (HALF_OPEN)
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_attempts = 0
                return True
            
            return False
        
        # HALF_OPEN: permitir intentos limitados
        if self.half_open_attempts < self.half_open_max_attempts:
            return True
        
        return False
    
    def is_open(self) -> bool:
        """Verifica si el circuito está abierto."""
        return self.state == CircuitBreakerState.OPEN
    
    def is_closed(self) -> bool:
        """Verifica si el circuito está cerrado."""
        return self.state == CircuitBreakerState.CLOSED
    
    def get_state(self) -> CircuitBreakerState:
        """Obtiene el estado actual."""
        # Auto-transición de OPEN a HALF_OPEN si ha pasado el cooldown
        if self.state == CircuitBreakerState.OPEN and self.opened_at:
            now = datetime.utcnow()
            elapsed = (now - self.opened_at).total_seconds()
            if elapsed >= self.cooldown_seconds:
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_attempts = 0
        
        return self.state
    
    def attempt(self):
        """Marca un intento (para HALF_OPEN)."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_attempts += 1


class TradingCircuitBreaker(CircuitBreaker):
    """Circuit breaker para trading."""
    
    def __init__(self):
        super().__init__(
            name="trading",
            failure_threshold=5,
            window_seconds=60,
            cooldown_seconds=300
        )


class CheckerCircuitBreaker(CircuitBreaker):
    """Circuit breaker para checkers."""
    
    def __init__(self):
        super().__init__(
            name="checkers",
            failure_threshold=3,
            window_seconds=30,
            cooldown_seconds=180
        )


class APICircuitBreaker(CircuitBreaker):
    """Circuit breaker para APIs externas."""
    
    def __init__(self, provider: str):
        super().__init__(
            name=f"api_{provider}",
            failure_threshold=5,
            window_seconds=60,
            cooldown_seconds=300
        )
        self.provider = provider

