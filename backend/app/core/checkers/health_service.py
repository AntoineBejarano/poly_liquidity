"""
Checker Health Service - Rastrea la salud de checkers para quorum dinámico.

Según requisitos en docs/PENDING/QUORUM_DINAMICO_REQUISITOS.md
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from dataclasses import dataclass, field
from app.database import SessionLocal
from app.models.event_checker import EventChecker
from app.core.config_service import config_service

logger = logging.getLogger(__name__)


@dataclass
class CheckerHealthStatus:
    """Estado de salud de un checker."""
    checker_id: UUID
    checker_name: str
    is_healthy: bool
    consecutive_failures: int
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    last_latency_ms: Optional[float]
    average_latency_ms: Optional[float]
    total_executions: int
    successful_executions: int
    failed_executions: int
    last_checked_at: Optional[datetime] = None


@dataclass
class CheckerExecutionRecord:
    """Registro de una ejecución de checker."""
    checker_id: UUID
    timestamp: datetime
    success: bool
    latency_ms: float
    error_message: Optional[str] = None


class CheckerHealthService:
    """
    Servicio para rastrear la salud de checkers.
    
    Responsabilidades:
    - Rastrear ejecuciones de checkers (éxito/fallo, latencia)
    - Determinar si un checker está saludable
    - Proporcionar lista de checkers saludables por categoría
    - Limpiar registros antiguos
    """
    
    def __init__(self):
        """Inicializa el servicio de salud de checkers."""
        # Almacenamiento en memoria de ejecuciones recientes
        # Estructura: {checker_id: [CheckerExecutionRecord, ...]}
        self._execution_history: Dict[UUID, List[CheckerExecutionRecord]] = {}
        
        # Cache de estado de salud
        # Estructura: {checker_id: CheckerHealthStatus}
        self._health_cache: Dict[UUID, CheckerHealthStatus] = {}
        
        # Configuración (se carga desde system_config)
        self._health_window_seconds = 300  # 5 minutos por defecto
        self._max_failures = 3  # 3 fallos consecutivos por defecto
        self._max_history_size = 1000  # Máximo de registros por checker
        
        # Cargar configuración inicial
        self._load_config()
    
    def _load_config(self):
        """Carga configuración desde system_config."""
        try:
            self._health_window_seconds = int(config_service.get("checker_health_window_seconds", 300))
            self._max_failures = int(config_service.get("checker_max_failures", 3))
        except Exception as e:
            logger.warning(f"Error cargando configuración de CheckerHealthService: {e}")
    
    def record_execution(
        self,
        checker_id: UUID,
        success: bool,
        latency_ms: float,
        error_message: Optional[str] = None
    ):
        """
        Registra una ejecución de checker.
        
        Args:
            checker_id: ID del checker
            success: True si la ejecución fue exitosa
            latency_ms: Latencia de la ejecución en milisegundos
            error_message: Mensaje de error si falló
        """
        record = CheckerExecutionRecord(
            checker_id=checker_id,
            timestamp=datetime.utcnow(),
            success=success,
            latency_ms=latency_ms,
            error_message=error_message
        )
        
        # Agregar al historial
        if checker_id not in self._execution_history:
            self._execution_history[checker_id] = []
        
        self._execution_history[checker_id].append(record)
        
        # Limitar tamaño del historial
        if len(self._execution_history[checker_id]) > self._max_history_size:
            self._execution_history[checker_id] = self._execution_history[checker_id][-self._max_history_size:]
        
        # Invalidar cache de salud
        if checker_id in self._health_cache:
            del self._health_cache[checker_id]
        
        logger.debug(
            f"Recorded checker execution: checker_id={checker_id}, success={success}, latency_ms={latency_ms}"
        )
    
    def is_checker_healthy(self, checker_id: UUID) -> bool:
        """
        Determina si un checker está saludable.
        
        Un checker es saludable si:
        - Ha tenido al menos una ejecución exitosa en la ventana de tiempo
        - No ha excedido el máximo de fallos consecutivos
        
        Args:
            checker_id: ID del checker
            
        Returns:
            True si el checker está saludable, False en caso contrario
        """
        status = self.get_health_status(checker_id)
        return status.is_healthy
    
    def get_health_status(self, checker_id: UUID) -> CheckerHealthStatus:
        """
        Obtiene el estado de salud completo de un checker.
        
        Args:
            checker_id: ID del checker
            
        Returns:
            CheckerHealthStatus con el estado completo
        """
        # Verificar cache
        if checker_id in self._health_cache:
            cached = self._health_cache[checker_id]
            # Si el cache es reciente (menos de 10 segundos), usarlo
            if cached.last_checked_at and (datetime.utcnow() - cached.last_checked_at).total_seconds() < 10:
                return cached
        
        # Obtener nombre del checker desde DB (opcional, para tests puede no existir)
        checker_name = f"checker_{checker_id}"
        try:
            db = SessionLocal()
            try:
                checker = db.query(EventChecker).filter(EventChecker.id == checker_id).first()
                if checker:
                    checker_name = checker.name
            finally:
                db.close()
        except Exception as e:
            # En tests o si la DB no está disponible, usar nombre por defecto
            logger.debug(f"Could not fetch checker name from DB: {e}")
        
        # Obtener historial de ejecuciones
        history = self._execution_history.get(checker_id, [])
        
        # Filtrar por ventana de tiempo
        window_start = datetime.utcnow() - timedelta(seconds=self._health_window_seconds)
        recent_history = [r for r in history if r.timestamp >= window_start]
        
        # Calcular métricas
        total_executions = len(recent_history)
        successful_executions = sum(1 for r in recent_history if r.success)
        failed_executions = total_executions - successful_executions
        
        # Calcular fallos consecutivos (desde el más reciente hacia atrás)
        consecutive_failures = 0
        for record in reversed(recent_history):
            if record.success:
                break
            consecutive_failures += 1
        
        # Obtener última ejecución exitosa y fallida
        last_success = None
        last_failure = None
        for record in reversed(recent_history):
            if record.success and last_success is None:
                last_success = record.timestamp
            if not record.success and last_failure is None:
                last_failure = record.timestamp
        
        # Calcular latencia promedio de ejecuciones exitosas
        successful_latencies = [r.latency_ms for r in recent_history if r.success]
        average_latency_ms = sum(successful_latencies) / len(successful_latencies) if successful_latencies else None
        last_latency_ms = recent_history[-1].latency_ms if recent_history else None
        
        # Determinar si está saludable
        # Un checker es saludable si:
        # 1. Ha tenido al menos una ejecución exitosa en la ventana de tiempo, O
        # 2. No ha excedido el máximo de fallos consecutivos Y tiene al menos una ejecución reciente
        is_healthy = False
        if successful_executions > 0:
            # Ha tenido éxito recientemente
            is_healthy = True
        elif total_executions > 0 and consecutive_failures < self._max_failures:
            # No ha excedido el máximo de fallos consecutivos y tiene ejecuciones recientes
            is_healthy = True
        # Si no hay ejecuciones recientes, se considera no saludable (no disponible)
        
        status = CheckerHealthStatus(
            checker_id=checker_id,
            checker_name=checker_name,
            is_healthy=is_healthy,
            consecutive_failures=consecutive_failures,
            last_success_at=last_success,
            last_failure_at=last_failure,
            last_latency_ms=last_latency_ms,
            average_latency_ms=average_latency_ms,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            last_checked_at=datetime.utcnow()
        )
        
        # Actualizar cache
        self._health_cache[checker_id] = status
        
        return status
    
    def get_healthy_checkers(self, category: str) -> List[EventChecker]:
        """
        Obtiene lista de checkers saludables para una categoría.
        
        Args:
            category: Categoría de eventos (ej: "sports")
            
        Returns:
            Lista de EventChecker que están saludables y habilitados
        """
        db = SessionLocal()
        try:
            # Obtener todos los checkers habilitados de la categoría
            checkers = db.query(EventChecker).filter(
                EventChecker.category == category,
                EventChecker.enabled == True
            ).all()
            
            # Filtrar por salud
            healthy_checkers = []
            for checker in checkers:
                if self.is_checker_healthy(checker.id):
                    healthy_checkers.append(checker)
            
            return healthy_checkers
        finally:
            db.close()
    
    def get_all_health_statuses(self, category: Optional[str] = None) -> Dict[UUID, CheckerHealthStatus]:
        """
        Obtiene el estado de salud de todos los checkers (opcionalmente filtrado por categoría).
        
        Args:
            category: Categoría opcional para filtrar
            
        Returns:
            Diccionario {checker_id: CheckerHealthStatus}
        """
        db = SessionLocal()
        try:
            query = db.query(EventChecker)
            if category:
                query = query.filter(EventChecker.category == category)
            
            checkers = query.all()
            
            statuses = {}
            for checker in checkers:
                statuses[checker.id] = self.get_health_status(checker.id)
            
            return statuses
        finally:
            db.close()
    
    def cleanup_old_records(self, max_age_seconds: int = 3600):
        """
        Limpia registros antiguos del historial.
        
        Args:
            max_age_seconds: Edad máxima en segundos para mantener registros (default: 1 hora)
        """
        cutoff = datetime.utcnow() - timedelta(seconds=max_age_seconds)
        
        for checker_id in list(self._execution_history.keys()):
            self._execution_history[checker_id] = [
                r for r in self._execution_history[checker_id]
                if r.timestamp >= cutoff
            ]
            
            # Si no quedan registros, eliminar entrada
            if not self._execution_history[checker_id]:
                del self._execution_history[checker_id]
        
        logger.debug(f"Cleaned up execution history older than {max_age_seconds} seconds")


# Instancia global del servicio
checker_health_service = CheckerHealthService()

