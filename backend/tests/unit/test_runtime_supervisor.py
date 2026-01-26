"""
Unit tests for Runtime Supervisor.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from app.core.runtime_supervisor import (
    RuntimeSupervisor,
    RuntimeMode,
    CircuitBreaker,
    CircuitBreakerState,
    TradingCircuitBreaker,
    CheckerCircuitBreaker
)
from app.core.runtime_supervisor.fail_safes.trading_fail_safe import TradingFailSafe
from app.core.runtime_supervisor.fail_safes.checker_fail_safe import CheckerFailSafe


@pytest.fixture
def runtime_supervisor():
    """Fixture para RuntimeSupervisor."""
    return RuntimeSupervisor()


@pytest.fixture
def trading_circuit():
    """Fixture para TradingCircuitBreaker."""
    return TradingCircuitBreaker()


@pytest.mark.asyncio
async def test_runtime_supervisor_initial_state(runtime_supervisor):
    """Test estado inicial del Runtime Supervisor."""
    assert runtime_supervisor.get_mode() == RuntimeMode.GREEN
    assert runtime_supervisor.trading_circuit.is_closed()
    assert runtime_supervisor.checker_circuit.is_closed()


@pytest.mark.asyncio
async def test_circuit_breaker_record_success(trading_circuit):
    """Test registro de éxito en circuit breaker."""
    assert trading_circuit.is_closed()
    trading_circuit.record_success()
    assert trading_circuit.is_closed()


@pytest.mark.asyncio
async def test_circuit_breaker_record_failure(trading_circuit):
    """Test registro de fallos en circuit breaker."""
    assert trading_circuit.is_closed()
    
    # Registrar múltiples fallos para abrir el circuito
    for _ in range(5):
        trading_circuit.record_failure()
    
    # El circuito debería abrirse después de 5 fallos
    assert trading_circuit.is_open()


@pytest.mark.asyncio
async def test_circuit_breaker_can_attempt(trading_circuit):
    """Test verificación de si se puede intentar operación."""
    assert trading_circuit.can_attempt() is True
    
    # Abrir el circuito
    for _ in range(5):
        trading_circuit.record_failure()
    
    assert trading_circuit.can_attempt() is False


@pytest.mark.asyncio
async def test_trading_fail_safe_trigger():
    """Test activación de trading fail-safe."""
    fail_safe = TradingFailSafe()
    assert fail_safe.is_triggered() is False
    
    await fail_safe.trigger("test_reason")
    assert fail_safe.is_triggered() is True
    
    await fail_safe.recover()
    assert fail_safe.is_triggered() is False


@pytest.mark.asyncio
async def test_checker_fail_safe_disable():
    """Test deshabilitación de checker."""
    fail_safe = CheckerFailSafe()
    assert fail_safe.is_disabled("test_checker") is False
    
    await fail_safe.trigger("test_checker", "test_reason")
    assert fail_safe.is_disabled("test_checker") is True
    
    await fail_safe.recover("test_checker")
    assert fail_safe.is_disabled("test_checker") is False


@pytest.mark.asyncio
async def test_runtime_supervisor_tick(runtime_supervisor):
    """Test tick del Runtime Supervisor."""
    # El tick debería ejecutarse sin errores
    await runtime_supervisor.tick()
    
    # El modo debería seguir siendo GREEN (sin métricas de error)
    assert runtime_supervisor.get_mode() == RuntimeMode.GREEN


@pytest.mark.asyncio
async def test_runtime_supervisor_get_status(runtime_supervisor):
    """Test obtención de estado del supervisor."""
    status = runtime_supervisor.get_status()
    
    assert "mode" in status
    assert "circuit_breakers" in status
    assert "fail_safes" in status
    assert "metrics" in status
    assert status["mode"] == "GREEN"


@pytest.mark.asyncio
async def test_runtime_supervisor_record_trading_success(runtime_supervisor):
    """Test registro de éxito en trading."""
    # Registrar algunos fallos primero
    for _ in range(3):
        runtime_supervisor.record_trading_failure()
    
    # Registrar éxito
    runtime_supervisor.record_trading_success()
    
    # El circuito debería seguir funcionando
    assert runtime_supervisor.trading_circuit.get_state() in [
        CircuitBreakerState.CLOSED,
        CircuitBreakerState.HALF_OPEN
    ]


@pytest.mark.asyncio
async def test_runtime_supervisor_record_trading_failure(runtime_supervisor):
    """Test registro de fallo en trading."""
    # Registrar múltiples fallos
    for _ in range(5):
        runtime_supervisor.record_trading_failure()
    
    # El circuito debería abrirse
    assert runtime_supervisor.trading_circuit.is_open()


@pytest.mark.asyncio
async def test_runtime_supervisor_get_circuit_state(runtime_supervisor):
    """Test obtención de estado de circuit breaker."""
    state = runtime_supervisor.get_circuit_state("trading")
    assert state == CircuitBreakerState.CLOSED
    
    state = runtime_supervisor.get_circuit_state("checkers")
    assert state == CircuitBreakerState.CLOSED
    
    # Circuit breaker inexistente debería retornar CLOSED
    state = runtime_supervisor.get_circuit_state("nonexistent")
    assert state == CircuitBreakerState.CLOSED

