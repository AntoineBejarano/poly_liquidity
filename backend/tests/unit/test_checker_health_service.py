"""
Tests unitarios para CheckerHealthService.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from app.core.checkers.health_service import (
    CheckerHealthService,
    CheckerHealthStatus,
    CheckerExecutionRecord
)
from app.models.event_checker import EventChecker
from app.database import SessionLocal


@pytest.fixture
def health_service():
    """Fixture para CheckerHealthService."""
    return CheckerHealthService()


@pytest.fixture
def sample_checker_id():
    """Fixture para un ID de checker de prueba."""
    return uuid4()


def test_record_execution_success(health_service, sample_checker_id):
    """Test que record_execution registra ejecuciones exitosas."""
    health_service.record_execution(
        checker_id=sample_checker_id,
        success=True,
        latency_ms=100.0
    )
    
    assert sample_checker_id in health_service._execution_history
    assert len(health_service._execution_history[sample_checker_id]) == 1
    
    record = health_service._execution_history[sample_checker_id][0]
    assert record.success is True
    assert record.latency_ms == 100.0
    assert record.error_message is None


def test_record_execution_failure(health_service, sample_checker_id):
    """Test que record_execution registra ejecuciones fallidas."""
    health_service.record_execution(
        checker_id=sample_checker_id,
        success=False,
        latency_ms=50.0,
        error_message="Timeout"
    )
    
    record = health_service._execution_history[sample_checker_id][0]
    assert record.success is False
    assert record.error_message == "Timeout"


def test_is_checker_healthy_with_success(health_service, sample_checker_id):
    """Test que un checker con ejecuciones exitosas es saludable."""
    # Registrar varias ejecuciones exitosas
    for _ in range(3):
        health_service.record_execution(
            checker_id=sample_checker_id,
            success=True,
            latency_ms=100.0
        )
    
    assert health_service.is_checker_healthy(sample_checker_id) is True


def test_is_checker_healthy_with_failures(health_service, sample_checker_id):
    """Test que un checker con muchos fallos consecutivos no es saludable."""
    # Configurar max_failures = 3
    health_service._max_failures = 3
    
    # Primero registrar una ejecución exitosa para que el checker tenga historial
    health_service.record_execution(
        checker_id=sample_checker_id,
        success=True,
        latency_ms=100.0
    )
    
    # Registrar 3 fallos consecutivos (dentro del límite)
    for _ in range(3):
        health_service.record_execution(
            checker_id=sample_checker_id,
            success=False,
            latency_ms=50.0
        )
    
    # Aún debería ser saludable (tiene éxito previo y no excede el límite)
    assert health_service.is_checker_healthy(sample_checker_id) is True
    
    # Registrar un fallo más (excede el límite)
    health_service.record_execution(
        checker_id=sample_checker_id,
        success=False,
        latency_ms=50.0
    )
    
    # Ahora debería ser no saludable (excede max_failures)
    assert health_service.is_checker_healthy(sample_checker_id) is False


def test_is_checker_healthy_no_recent_executions(health_service, sample_checker_id):
    """Test que un checker sin ejecuciones recientes no es saludable."""
    # No registrar ejecuciones
    assert health_service.is_checker_healthy(sample_checker_id) is False


def test_get_health_status_metrics(health_service, sample_checker_id):
    """Test que get_health_status calcula métricas correctamente."""
    # Registrar ejecuciones mixtas
    health_service.record_execution(sample_checker_id, True, 100.0)
    health_service.record_execution(sample_checker_id, True, 150.0)
    health_service.record_execution(sample_checker_id, False, 50.0)
    
    status = health_service.get_health_status(sample_checker_id)
    
    assert status.checker_id == sample_checker_id
    assert status.total_executions == 3
    assert status.successful_executions == 2
    assert status.failed_executions == 1
    assert status.consecutive_failures == 1
    assert status.average_latency_ms == 125.0  # (100 + 150) / 2
    assert status.last_latency_ms == 50.0


def test_get_health_status_consecutive_failures(health_service, sample_checker_id):
    """Test que get_health_status calcula fallos consecutivos correctamente."""
    # Registrar: éxito, éxito, fallo, fallo, fallo
    health_service.record_execution(sample_checker_id, True, 100.0)
    health_service.record_execution(sample_checker_id, True, 100.0)
    health_service.record_execution(sample_checker_id, False, 50.0)
    health_service.record_execution(sample_checker_id, False, 50.0)
    health_service.record_execution(sample_checker_id, False, 50.0)
    
    status = health_service.get_health_status(sample_checker_id)
    
    assert status.consecutive_failures == 3
    assert status.is_healthy is True  # Tiene éxitos previos


def test_cleanup_old_records(health_service, sample_checker_id):
    """Test que cleanup_old_records elimina registros antiguos."""
    # Crear un registro antiguo (simulado)
    old_record = CheckerExecutionRecord(
        checker_id=sample_checker_id,
        timestamp=datetime.utcnow() - timedelta(seconds=7200),  # 2 horas atrás
        success=True,
        latency_ms=100.0
    )
    health_service._execution_history[sample_checker_id] = [old_record]
    
    # Agregar un registro reciente
    health_service.record_execution(sample_checker_id, True, 100.0)
    
    # Limpiar registros más antiguos de 1 hora
    health_service.cleanup_old_records(max_age_seconds=3600)
    
    # Solo debería quedar el registro reciente
    assert len(health_service._execution_history[sample_checker_id]) == 1
    assert health_service._execution_history[sample_checker_id][0].timestamp > datetime.utcnow() - timedelta(seconds=3600)


def test_health_window_filtering(health_service, sample_checker_id):
    """Test que solo se consideran ejecuciones dentro de la ventana de tiempo."""
    # Configurar ventana de 1 minuto
    health_service._health_window_seconds = 60
    
    # Crear un registro antiguo (fuera de la ventana)
    old_record = CheckerExecutionRecord(
        checker_id=sample_checker_id,
        timestamp=datetime.utcnow() - timedelta(seconds=120),  # 2 minutos atrás
        success=True,
        latency_ms=100.0
    )
    health_service._execution_history[sample_checker_id] = [old_record]
    
    # Agregar un registro reciente (dentro de la ventana)
    health_service.record_execution(sample_checker_id, True, 100.0)
    
    status = health_service.get_health_status(sample_checker_id)
    
    # Solo debería contar el registro reciente
    assert status.total_executions == 1

