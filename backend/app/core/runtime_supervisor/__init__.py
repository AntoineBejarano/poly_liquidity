"""
Runtime Supervisor - capa de protección operacional en tiempo real.

Este módulo proporciona supervisión continua del estado de salud del sistema,
gestión de circuit breakers, y activación de fail-safes automáticos.
"""
from app.core.runtime_supervisor.supervisor import RuntimeSupervisor
from app.core.runtime_supervisor.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    TradingCircuitBreaker,
    CheckerCircuitBreaker,
    APICircuitBreaker
)
from app.core.runtime_supervisor.runtime_mode import RuntimeMode

__all__ = [
    "RuntimeSupervisor",
    "CircuitBreaker",
    "CircuitBreakerState",
    "TradingCircuitBreaker",
    "CheckerCircuitBreaker",
    "APICircuitBreaker",
    "RuntimeMode",
]

