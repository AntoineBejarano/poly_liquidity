"""
Unit tests for Metrics & Observability Layer.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from app.core.metrics.store import MetricStore
from app.core.metrics.collector import MetricCollector
from app.core.metrics.alerting import AlertingSystem, AlertLevel
from app.core.metrics.prometheus_exporter import PrometheusExporter


@pytest.fixture
def metric_store():
    """Fixture para MetricStore con base de datos en memoria."""
    return MetricStore(database_url="sqlite:///:memory:")


@pytest.fixture
def metric_collector(metric_store):
    """Fixture para MetricCollector."""
    return MetricCollector(metric_store)


@pytest.mark.asyncio
async def test_store_metric(metric_store):
    """Test almacenamiento de métrica."""
    await metric_store.store_metric(
        metric_name="test_metric",
        value=42.5,
        labels={"test": "value"},
        component="test"
    )
    
    latest = metric_store.get_latest_metric("test_metric")
    assert latest is not None
    assert latest["value"] == 42.5
    assert latest["labels"]["test"] == "value"
    assert latest["component"] == "test"


@pytest.mark.asyncio
async def test_get_metric_history(metric_store):
    """Test obtención de historial de métricas."""
    # Almacenar múltiples métricas
    for i in range(5):
        await metric_store.store_metric(
            metric_name="test_metric",
            value=float(i),
            component="test"
        )
        await asyncio.sleep(0.01)  # Pequeña pausa para timestamps diferentes
    
    history = metric_store.get_metric_history("test_metric", limit=10)
    assert len(history) == 5
    
    # Verificar que están ordenadas (más antiguas primero, más recientes al final)
    values = [m["value"] for m in history]
    assert values == [0.0, 1.0, 2.0, 3.0, 4.0]


@pytest.mark.asyncio
async def test_calculate_percentiles(metric_store):
    """Test cálculo de percentiles."""
    # Almacenar métricas con valores conocidos
    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    for value in values:
        await metric_store.store_metric(
            metric_name="test_metric",
            value=float(value),
            component="test"
        )
    
    stats = metric_store.calculate_percentiles("test_metric")
    # Para 10 valores [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
    # p50 debería ser aproximadamente el valor en el índice 4.5 (redondeado a 5) = 60
    # p95 debería ser aproximadamente el valor en el índice 8.55 (redondeado a 9) = 100
    # p99 debería ser aproximadamente el valor en el índice 8.91 (redondeado a 9) = 100
    assert stats["p50"] >= 50.0  # Aproximadamente 50-60
    assert stats["p95"] >= 90.0  # Aproximadamente 90-100
    assert stats["p99"] >= 90.0  # Aproximadamente 90-100
    assert stats["min"] == 10.0
    assert stats["max"] == 100.0
    assert stats["count"] == 10


@pytest.mark.asyncio
async def test_collector_collect_tick_duration(metric_collector):
    """Test recolección de duración de tick."""
    metric_collector.start_tick()
    await asyncio.sleep(0.1)  # Simular trabajo
    await metric_collector.collect_tick_duration()
    
    latest = metric_collector.store.get_latest_metric("tick_duration_ms")
    assert latest is not None
    assert latest["value"] > 0


@pytest.mark.asyncio
async def test_collector_collect_checker_stats(metric_collector):
    """Test recolección de estadísticas de checkers."""
    checker_stats = {
        "espn": {"latency_ms": 95.0, "error_count": 2},
        "flashscore": {"latency_ms": 120.0, "error_count": 0}
    }
    
    await metric_collector.collect_checker_stats(checker_stats)
    
    # Verificar métricas de latencia
    history = metric_collector.store.get_metric_history("checker_latency_ms", limit=10)
    assert len(history) == 2
    
    # Verificar métricas de errores
    error_history = metric_collector.store.get_metric_history("checker_errors", limit=10)
    assert len(error_history) == 2


@pytest.mark.asyncio
async def test_collector_record_event(metric_collector):
    """Test registro de evento."""
    await metric_collector.record_event(
        "test_event",
        {
            "market_id": "pm123",
            "value": 1.0
        },
        component="test"
    )
    
    latest = metric_collector.store.get_latest_metric("test_event")
    assert latest is not None
    assert latest["labels"]["market_id"] == "pm123"


@pytest.mark.asyncio
async def test_alerting_send_alert(monkeypatch):
    """Test envío de alerta."""
    alerting = AlertingSystem()
    
    # Mock HTTP client para evitar llamadas reales
    async def mock_post(*args, **kwargs):
        return None
    
    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    
    await alerting.send_alert(
        level=AlertLevel.WARNING,
        message="Test alert",
        metric="test_metric",
        value=42.0
    )
    
    # Verificar que se guardó en historial
    history = alerting.get_alert_history(limit=1)
    assert len(history) == 1
    assert history[0]["level"] == "WARNING"
    assert history[0]["message"] == "Test alert"


@pytest.mark.asyncio
async def test_alerting_check_latency_alerts(monkeypatch):
    """Test verificación de alertas de latencia."""
    alerting = AlertingSystem()
    
    # Mock HTTP client
    async def mock_post(*args, **kwargs):
        return None
    
    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    
    # Test CRITICAL alert
    await alerting.check_latency_alerts(600.0)  # > 500ms
    
    history = alerting.get_alert_history(limit=1)
    assert len(history) == 1
    assert history[0]["level"] == "CRITICAL"
    
    # Test WARNING alert
    await alerting.check_latency_alerts(250.0)  # > 200ms pero < 500ms
    
    history = alerting.get_alert_history(limit=2)
    assert len(history) == 2
    assert history[1]["level"] == "WARNING"


@pytest.mark.asyncio
async def test_prometheus_exporter(metric_store):
    """Test exportador de Prometheus."""
    # Almacenar algunas métricas
    await metric_store.store_metric("tick_duration_ms", 42.0, component="system")
    await metric_store.store_metric("execution_latency_ms", 120.0, component="execution")
    
    exporter = PrometheusExporter(metric_store)
    prometheus_text = exporter.export_metrics()
    
    assert "tick_duration_ms" in prometheus_text
    assert "execution_latency_ms" in prometheus_text
    assert "# HELP" in prometheus_text
    assert "# TYPE" in prometheus_text

