"""
Runtime Supervisor - supervisión continua del estado de salud del sistema.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.core.runtime_supervisor.runtime_mode import RuntimeMode
from app.core.runtime_supervisor.circuit_breaker import (
    CircuitBreakerState,
    TradingCircuitBreaker,
    CheckerCircuitBreaker,
    APICircuitBreaker
)
from app.core.runtime_supervisor.fail_safes.trading_fail_safe import TradingFailSafe
from app.core.runtime_supervisor.fail_safes.checker_fail_safe import CheckerFailSafe
from app.core.metrics.metrics_service import metrics_service


class RuntimeSupervisorConfig:
    """Configuración del Runtime Supervisor."""
    
    def __init__(self):
        # Thresholds de latencia (ms)
        self.latency_green_threshold: float = 200
        self.latency_yellow_threshold: float = 500
        self.latency_red_threshold: float = 1000
        
        # Thresholds de errores
        self.error_rate_yellow: float = 5.0      # errores por segundo
        self.error_rate_red: float = 10.0          # errores por segundo
        
        # Circuit breakers
        self.trading_circuit_failure_threshold: int = 5
        self.trading_circuit_window_seconds: int = 60
        self.trading_circuit_cooldown_seconds: int = 300
        
        self.checker_circuit_failure_threshold: int = 3
        self.checker_circuit_window_seconds: int = 30
        
        # Fail-safes
        self.auto_cancel_orders_on_red: bool = True
        self.auto_disable_checkers_on_failure: bool = True


class RuntimeSupervisor:
    """
    Runtime Supervisor - controlador de misión del sistema.
    
    Monitoriza continuamente el estado de salud y ajusta el modo de operación.
    """
    
    def __init__(self, execution_engine=None):
        """
        Inicializa el Runtime Supervisor.
        
        Args:
            execution_engine: Referencia al Execution Engine (opcional, para fail-safes)
        """
        self.config = RuntimeSupervisorConfig()
        self.current_mode = RuntimeMode.GREEN
        self.previous_mode = RuntimeMode.GREEN
        self.mode_changed_at: Optional[datetime] = None
        
        # Circuit breakers
        self.trading_circuit = TradingCircuitBreaker()
        self.checker_circuit = CheckerCircuitBreaker()
        self.api_circuits: Dict[str, APICircuitBreaker] = {}
        
        # Fail-safes
        self.trading_fail_safe = TradingFailSafe(execution_engine)
        self.checker_fail_safe = CheckerFailSafe()
        
        # Métricas recientes (para cálculo de modo)
        self._recent_latencies: list = []
        self._recent_errors: list = []
        self._error_window_start: Optional[datetime] = None
    
    def get_mode(self) -> RuntimeMode:
        """
        Obtiene el modo actual.
        
        Returns:
            RuntimeMode actual
        """
        return self.current_mode
    
    def get_circuit_state(self, circuit_id: str) -> CircuitBreakerState:
        """
        Obtiene el estado de un circuit breaker.
        
        Args:
            circuit_id: ID del circuit breaker ("trading", "checkers", o "api_{provider}")
        
        Returns:
            Estado del circuit breaker
        """
        if circuit_id == "trading":
            return self.trading_circuit.get_state()
        elif circuit_id == "checkers":
            return self.checker_circuit.get_state()
        elif circuit_id.startswith("api_"):
            provider = circuit_id[4:]
            if provider in self.api_circuits:
                return self.api_circuits[provider].get_state()
        
        return CircuitBreakerState.CLOSED
    
    async def tick(self):
        """
        Tick del supervisor.
        
        Este método debe llamarse periódicamente para:
        - Recolectar métricas
        - Calcular Runtime Mode
        - Verificar circuit breakers
        - Activar fail-safes si es necesario
        """
        # Recolectar métricas
        await self._collect_metrics()
        
        # Calcular Runtime Mode
        new_mode = await self._calculate_runtime_mode()
        
        # Actualizar modo si cambió
        if new_mode != self.current_mode:
            await self._on_mode_changed(self.current_mode, new_mode)
            self.previous_mode = self.current_mode
            self.current_mode = new_mode
            self.mode_changed_at = datetime.utcnow()
        
        # Verificar circuit breakers
        await self._check_circuit_breakers()
        
        # Activar fail-safes si es necesario
        await self._trigger_fail_safes()
    
    async def _collect_metrics(self):
        """Recolecta métricas del sistema."""
        # Obtener métricas de latencia
        try:
            latency_stats = metrics_service.store.calculate_percentiles("execution_latency_ms")
            if latency_stats.get("p95", 0) > 0:
                self._recent_latencies.append(latency_stats["p95"])
                # Mantener solo últimas 10 mediciones
                if len(self._recent_latencies) > 10:
                    self._recent_latencies.pop(0)
        except Exception as e:
            print(f"ERROR: Failed to collect latency metrics: {e}")
        
        # Obtener métricas de errores (simplificado - contar errores recientes)
        # TODO: Implementar conteo de errores por ventana de tiempo
        try:
            error_history = metrics_service.store.get_metric_history("execution_orders_rejected", limit=100)
            # Contar errores en última ventana (60 segundos)
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=60)
            
            recent_errors = [
                m for m in error_history
                if m.get("timestamp", now) >= window_start
            ]
            
            error_count = len(recent_errors)
            self._recent_errors.append(error_count)
            if len(self._recent_errors) > 10:
                self._recent_errors.pop(0)
        except Exception as e:
            print(f"ERROR: Failed to collect error metrics: {e}")
    
    async def _calculate_runtime_mode(self) -> RuntimeMode:
        """
        Calcula el Runtime Mode basado en métricas.
        
        Returns:
            RuntimeMode calculado
        """
        # Calcular latencia promedio (p95)
        avg_latency = 0.0
        if self._recent_latencies:
            avg_latency = sum(self._recent_latencies) / len(self._recent_latencies)
        
        # Calcular error rate promedio
        avg_error_rate = 0.0
        if self._recent_errors:
            avg_error_rate = sum(self._recent_errors) / len(self._recent_errors)
        
        # Verificar circuit breakers
        trading_open = self.trading_circuit.is_open()
        checker_open = self.checker_circuit.is_open()
        
        # Lógica de decisión
        
        # RED: Condiciones críticas
        if (
            avg_latency > self.config.latency_red_threshold or
            avg_error_rate > self.config.error_rate_red or
            trading_open
        ):
            return RuntimeMode.RED
        
        # YELLOW: Condiciones de advertencia
        if (
            avg_latency > self.config.latency_yellow_threshold or
            avg_error_rate > self.config.error_rate_yellow or
            checker_open
        ):
            return RuntimeMode.YELLOW
        
        # GREEN: Condiciones normales
        return RuntimeMode.GREEN
    
    async def _on_mode_changed(self, from_mode: RuntimeMode, to_mode: RuntimeMode):
        """
        Maneja el cambio de modo.
        
        Args:
            from_mode: Modo anterior
            to_mode: Modo nuevo
        """
        reason = self._get_mode_change_reason(to_mode)
        
        # Emitir evento a métricas
        await metrics_service.collector.record_event(
            "runtime_mode_changed",
            {
                "from": from_mode.value,
                "to": to_mode.value,
                "reason": reason,
                "value": 1.0
            },
            component="runtime_supervisor"
        )
        
        # Notificar al sistema de alertas
        await metrics_service.alerting.on_runtime_mode_changed(
            from_mode.value,
            to_mode.value
        )
        
        print(f"RUNTIME MODE CHANGED: {from_mode.value} → {to_mode.value} ({reason})")
    
    def _get_mode_change_reason(self, mode: RuntimeMode) -> str:
        """Obtiene la razón del cambio de modo."""
        if mode == RuntimeMode.RED:
            if self._recent_latencies and self._recent_latencies[-1] > self.config.latency_red_threshold:
                return "latency_above_red_threshold"
            if self._recent_errors and self._recent_errors[-1] > self.config.error_rate_red:
                return "error_rate_above_red_threshold"
            if self.trading_circuit.is_open():
                return "trading_circuit_open"
        elif mode == RuntimeMode.YELLOW:
            if self._recent_latencies and self._recent_latencies[-1] > self.config.latency_yellow_threshold:
                return "latency_above_yellow_threshold"
            if self._recent_errors and self._recent_errors[-1] > self.config.error_rate_yellow:
                return "error_rate_above_yellow_threshold"
            if self.checker_circuit.is_open():
                return "checker_circuit_open"
        
        return "normal_conditions"
    
    async def _check_circuit_breakers(self):
        """Verifica y actualiza circuit breakers."""
        # Trading circuit breaker se actualiza desde Execution Engine
        # Checker circuit breaker se actualiza desde Event Engine
        # API circuit breakers se actualizan desde los clientes HTTP
        
        # Auto-transición de estados (OPEN → HALF_OPEN después de cooldown)
        self.trading_circuit.get_state()
        self.checker_circuit.get_state()
        for api_circuit in self.api_circuits.values():
            api_circuit.get_state()
    
    async def _trigger_fail_safes(self):
        """Activa fail-safes si es necesario."""
        # Trading fail-safe: activar en RED
        if self.current_mode == RuntimeMode.RED:
            if not self.trading_fail_safe.is_triggered():
                reason = self._get_mode_change_reason(RuntimeMode.RED)
                await self.trading_fail_safe.trigger(reason)
        else:
            if self.trading_fail_safe.is_triggered():
                await self.trading_fail_safe.recover()
        
        # Checker fail-safe: activar si checker circuit está abierto
        if self.checker_circuit.is_open():
            # TODO: Obtener lista de checkers fallidos y deshabilitarlos
            pass
    
    def record_trading_success(self):
        """Registra un éxito en trading."""
        self.trading_circuit.record_success()
    
    def record_trading_failure(self):
        """Registra un fallo en trading."""
        self.trading_circuit.record_failure()
    
    def record_checker_success(self, checker_id: str):
        """Registra un éxito en checker."""
        self.checker_circuit.record_success()
        # Recuperar checker si estaba deshabilitado
        if self.checker_fail_safe.is_disabled(checker_id):
            # TODO: Implementar recuperación automática después de N éxitos
            pass
    
    def record_checker_failure(self, checker_id: str):
        """Registra un fallo en checker."""
        self.checker_circuit.record_failure()
        # Deshabilitar checker si falla repetidamente
        if self.config.auto_disable_checkers_on_failure:
            # TODO: Implementar lógica de deshabilitación después de N fallos
            pass
    
    def record_api_success(self, provider: str):
        """Registra un éxito en API."""
        if provider not in self.api_circuits:
            self.api_circuits[provider] = APICircuitBreaker(provider)
        self.api_circuits[provider].record_success()
    
    def record_api_failure(self, provider: str):
        """Registra un fallo en API."""
        if provider not in self.api_circuits:
            self.api_circuits[provider] = APICircuitBreaker(provider)
        self.api_circuits[provider].record_failure()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado completo del supervisor.
        
        Returns:
            Dict con estado completo
        """
        return {
            "mode": self.current_mode.value,
            "previous_mode": self.previous_mode.value,
            "mode_changed_at": self.mode_changed_at.isoformat() if self.mode_changed_at else None,
            "circuit_breakers": {
                "trading": self.trading_circuit.get_state().value,
                "checkers": self.checker_circuit.get_state().value,
                "apis": {
                    provider: circuit.get_state().value
                    for provider, circuit in self.api_circuits.items()
                }
            },
            "fail_safes": {
                "trading": self.trading_fail_safe.get_info(),
                "checkers": self.checker_fail_safe.get_info()
            },
            "metrics": {
                "avg_latency_p95": sum(self._recent_latencies) / len(self._recent_latencies) if self._recent_latencies else 0.0,
                "avg_error_rate": sum(self._recent_errors) / len(self._recent_errors) if self._recent_errors else 0.0
            }
        }

