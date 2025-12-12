"""
Metrics Service - servicio principal de métricas.

Este es el punto de entrada principal para el sistema de métricas.
"""
from typing import Optional
from datetime import datetime
from app.core.metrics.store import MetricStore
from app.core.metrics.collector import MetricCollector
from app.core.metrics.sampler import MetricSampler
from app.core.metrics.alerting import AlertingSystem
from app.core.metrics.prometheus_exporter import PrometheusExporter
from app.settings import settings


class MetricsService:
    """
    Servicio principal de métricas.
    
    Coordina todos los componentes del sistema de métricas.
    """
    
    def __init__(self):
        """Inicializa el servicio de métricas."""
        # Crear componentes
        self.store = MetricStore(database_url=settings.database_url)
        self.collector = MetricCollector(self.store)
        self.sampler = MetricSampler(self.collector, interval_seconds=2.0)
        self.alerting = AlertingSystem()
        self.prometheus_exporter = PrometheusExporter(self.store)
        
        self._sampler_started = False
    
    async def start(self):
        """Inicia el servicio de métricas."""
        await self.sampler.start()
        self._sampler_started = True
    
    async def stop(self):
        """Detiene el servicio de métricas."""
        if self._sampler_started:
            await self.sampler.stop()
        await self.alerting.close()
    
    async def tick(self):
        """
        Tick del servicio de métricas.
        
        Este método se llama desde el main loop para recolectar métricas.
        """
        # Marcar inicio del tick
        self.collector.start_tick()
        
        # Recolectar métricas del tick
        await self.collector.collect_tick_duration()
        
        # Recolectar métricas del runtime
        await self.collector.collect_runtime_metrics()
        
        # Recolectar métricas de riesgo
        await self.collector.collect_risk_exposure()
        
        # Verificar alertas
        await self._check_alerts()
    
    async def _check_alerts(self):
        """Verifica métricas y dispara alertas si es necesario."""
        # Obtener percentiles de latencia
        try:
            latency_stats = self.store.calculate_percentiles("execution_latency_ms")
            if latency_stats.get("p95", 0) > 0:
                await self.alerting.check_latency_alerts(latency_stats["p95"])
        except Exception as e:
            print(f"ERROR: Failed to check latency alerts: {e}")
        
        # Obtener ratio de rechazos
        try:
            rejection_stats = self.store.calculate_percentiles("execution_rejection_rate")
            if rejection_stats.get("p50", 0) > 0:
                await self.alerting.check_trading_alerts(rejection_stats["p50"])
        except Exception as e:
            print(f"ERROR: Failed to check trading alerts: {e}")
    
    def get_current_metrics(self) -> dict:
        """
        Obtiene métricas actuales para streaming/API.
        
        Returns:
            Dict con métricas actuales
        """
        summary = self.store.get_metrics_summary()
        
        # Calcular percentiles para métricas clave
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "runtime_mode": self._get_runtime_mode(),
            **summary
        }
        
        # Agregar percentiles
        for metric_name in ["tick_duration_ms", "execution_latency_ms", "checker_latency_ms"]:
            try:
                stats = self.store.calculate_percentiles(metric_name)
                if stats.get("count", 0) > 0:
                    metrics[f"{metric_name}_percentiles"] = {
                        "p50": stats["p50"],
                        "p95": stats["p95"],
                        "p99": stats["p99"]
                    }
            except Exception:
                pass
        
        return metrics
    
    def _get_runtime_mode(self) -> str:
        """Obtiene el runtime mode del Runtime Supervisor."""
        try:
            import app.main as main_module
            runtime_supervisor = main_module.runtime_supervisor
            return runtime_supervisor.get_mode().value
        except Exception:
            return "GREEN"


# Global metrics service instance
metrics_service = MetricsService()

