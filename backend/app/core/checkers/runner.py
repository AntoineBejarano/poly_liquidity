"""
Checker Runner - ejecuta checkers con timeouts, retries y circuit breakers.

Según especificación en docs/services/checker_system.md
"""
import asyncio
import time
from typing import Optional, Dict, List
from datetime import datetime
from app.core.checkers.base import BaseChecker, CheckerResult
from app.core.runtime_supervisor.circuit_breaker import CircuitBreaker, CircuitBreakerState


class CheckerRunner:
    """
    Ejecutor de checkers con soporte para timeouts, retries y circuit breakers.
    
    Responsabilidades:
    - Ejecutar checkers con timeout
    - Manejar retries con backoff exponencial
    - Gestionar circuit breakers por checker
    - Normalizar errores a CheckerResult
    """
    
    def __init__(self):
        """Inicializa el CheckerRunner."""
        # Circuit breakers por checker (key: checker name)
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def _get_circuit_breaker(self, checker_name: str) -> CircuitBreaker:
        """Obtiene o crea el circuit breaker para un checker."""
        if checker_name not in self._circuit_breakers:
            self._circuit_breakers[checker_name] = CircuitBreaker(
                name=f"checker_{checker_name}",
                failure_threshold=5,
                window_seconds=60,
                cooldown_seconds=300,
                half_open_max_attempts=3
            )
        return self._circuit_breakers[checker_name]
    
    async def run_checker(
        self,
        checker_instance: BaseChecker,
        external_event_id: str,
        credentials: Optional[Dict[str, str]] = None
    ) -> CheckerResult:
        """
        Ejecuta un checker con timeout, retries y circuit breaker.
        
        Args:
            checker_instance: Instancia del checker
            external_event_id: ID del evento externo
            credentials: Credenciales para el checker
        
        Returns:
            CheckerResult normalizado (nunca lanza excepciones)
        """
        checker_name = checker_instance.name
        circuit_breaker = self._get_circuit_breaker(checker_name)
        
        # Verificar circuit breaker
        if not circuit_breaker.can_attempt():
            # Circuit breaker está abierto y no puede intentar, retornar UNKNOWN inmediatamente
            return CheckerResult(
                state="UNKNOWN",
                confidence=0.0,
                error="circuit_breaker_open",
                source=checker_name,
                latency_ms=0.0,
                timestamp=datetime.utcnow()
            )
        
        # Marcar intento si está en HALF_OPEN
        if circuit_breaker.get_state().value == "HALF_OPEN":
            circuit_breaker.attempt()
        
        # Ejecutar con retries
        timeout_ms = checker_instance.timeout_ms
        max_retries = checker_instance.max_retries
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                
                # Ejecutar con timeout
                result = await asyncio.wait_for(
                    checker_instance.check(external_event_id, credentials),
                    timeout=timeout_ms / 1000.0
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                # Actualizar latency y timestamp si no están en el resultado
                if not hasattr(result, 'latency_ms') or result.latency_ms == 0.0:
                    result.latency_ms = latency_ms
                if not hasattr(result, 'timestamp') or result.timestamp is None:
                    result.timestamp = datetime.utcnow()
                
                # Registrar éxito en circuit breaker
                circuit_breaker.record_success()
                
                return result
                
            except asyncio.TimeoutError:
                last_error = "timeout"
                # Backoff exponencial
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                circuit_breaker.record_failure()
                
            except Exception as e:
                last_error = f"error: {str(e)}"
                # Backoff exponencial
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                circuit_breaker.record_failure()
        
        # Todos los intentos fallaron
        return CheckerResult(
            state="UNKNOWN",
            confidence=0.0,
            error=last_error or "max_retries_exceeded",
            source=checker_name,
            latency_ms=0.0,
            timestamp=datetime.utcnow(),
            raw_payload={"error": last_error, "attempts": max_retries + 1}
        )
    
    async def run_checkers_parallel(
        self,
        checker_instances: List[BaseChecker],
        external_event_id: str,
        credentials_map: Optional[Dict[str, Dict[str, str]]] = None
    ) -> List[CheckerResult]:
        """
        Ejecuta múltiples checkers en paralelo.
        
        Args:
            checker_instances: Lista de instancias de checkers
            external_event_id: ID del evento externo
            credentials_map: Mapa de checker name -> credentials (opcional)
        
        Returns:
            Lista de CheckerResult (normalizados, sin excepciones)
        """
        tasks = []
        for checker in checker_instances:
            credentials = None
            if credentials_map and checker.name in credentials_map:
                credentials = credentials_map[checker.name]
            
            tasks.append(
                self.run_checker(checker, external_event_id, credentials)
            )
        
        # Ejecutar en paralelo con manejo de excepciones
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Normalizar resultados
        normalized_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Normalizar excepción a CheckerResult
                checker_name = checker_instances[i].name
                normalized_results.append(CheckerResult(
                    state="UNKNOWN",
                    confidence=0.0,
                    error=f"exception: {str(result)}",
                    source=checker_name,
                    latency_ms=0.0,
                    timestamp=datetime.utcnow(),
                    raw_payload={"exception_type": type(result).__name__}
                ))
            else:
                normalized_results.append(result)
        
        return normalized_results

