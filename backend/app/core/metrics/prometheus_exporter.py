"""
Prometheus Exporter - exporta métricas en formato Prometheus.
"""
from typing import Dict, Any
from app.core.metrics.store import MetricStore


class PrometheusExporter:
    """
    Exportador de métricas en formato Prometheus.
    
    Permite integración con Prometheus/Grafana para dashboards enterprise.
    """
    
    def __init__(self, metric_store: MetricStore):
        """
        Inicializa el exportador.
        
        Args:
            metric_store: Almacén de métricas
        """
        self.store = metric_store
    
    def export_metrics(self) -> str:
        """
        Exporta métricas en formato Prometheus.
        
        Returns:
            String en formato Prometheus
        """
        lines = []
        
        # Obtener resumen de métricas
        summary = self.store.get_metrics_summary()
        
        # Exportar métricas principales
        metrics_to_export = [
            "tick_duration_ms",
            "checker_latency_ms",
            "execution_latency_ms",
            "backend_latency_ms",
            "risk_exposure_total",
            "watchers_active",
            "markets_active",
            "strategy_intents_total",
            "risk_intents_approved",
            "risk_intents_rejected",
            "execution_orders_sent",
            "execution_orders_filled",
            "execution_orders_rejected",
        ]
        
        for metric_name in metrics_to_export:
            if metric_name in summary:
                metric = summary[metric_name]
                value = metric["value"]
                labels = metric.get("labels", {})
                
                # Construir labels string
                labels_str = ""
                if labels:
                    labels_parts = [f'{k}="{v}"' for k, v in labels.items()]
                    labels_str = "{" + ",".join(labels_parts) + "}"
                
                # Agregar help y type
                help_text = self._get_help_text(metric_name)
                type_text = self._get_type_text(metric_name)
                
                lines.append(f"# HELP {metric_name} {help_text}")
                lines.append(f"# TYPE {metric_name} {type_text}")
                lines.append(f"{metric_name}{labels_str} {value}")
                lines.append("")
        
        # Exportar percentiles si están disponibles
        percentiles = ["p50", "p95", "p99"]
        for metric_name in ["tick_duration_ms", "execution_latency_ms", "checker_latency_ms"]:
            try:
                stats = self.store.calculate_percentiles(metric_name)
                for percentile in percentiles:
                    if percentile in stats:
                        lines.append(f"# HELP {metric_name}_{percentile} {percentile} percentile of {metric_name}")
                        lines.append(f"# TYPE {metric_name}_{percentile} gauge")
                        lines.append(f"{metric_name}_{percentile} {stats[percentile]}")
                        lines.append("")
            except Exception:
                pass
        
        return "\n".join(lines)
    
    def _get_help_text(self, metric_name: str) -> str:
        """Obtiene texto de ayuda para una métrica."""
        help_texts = {
            "tick_duration_ms": "Duration of main tick in milliseconds",
            "checker_latency_ms": "Latency of checker in milliseconds",
            "execution_latency_ms": "Execution latency in milliseconds",
            "backend_latency_ms": "Backend processing latency in milliseconds",
            "risk_exposure_total": "Total risk exposure",
            "watchers_active": "Number of active watchers",
            "markets_active": "Number of active markets",
            "strategy_intents_total": "Total number of intents created by strategy",
            "risk_intents_approved": "Number of intents approved by risk engine",
            "risk_intents_rejected": "Number of intents rejected by risk engine",
            "execution_orders_sent": "Number of orders sent to Polymarket",
            "execution_orders_filled": "Number of orders filled",
            "execution_orders_rejected": "Number of orders rejected",
        }
        return help_texts.get(metric_name, f"Metric {metric_name}")
    
    def _get_type_text(self, metric_name: str) -> str:
        """Obtiene tipo de métrica para Prometheus."""
        # La mayoría son gauges (valores que suben y bajan)
        return "gauge"

