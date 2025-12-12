"""
Metric Collector - recolección de métricas desde módulos.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.core.metrics.store import MetricStore
from app.core.state import state
from app.core.latency_monitor import latency_monitor


class MetricCollector:
    """
    Recolector de métricas desde módulos del sistema.
    
    Proporciona métodos para recolectar métricas de diferentes componentes.
    """
    
    def __init__(self, metric_store: MetricStore):
        """
        Inicializa el recolector.
        
        Args:
            metric_store: Almacén de métricas
        """
        self.store = metric_store
        self._tick_start_time: Optional[datetime] = None
    
    def start_tick(self):
        """Marca el inicio de un tick (para medir duración)."""
        self._tick_start_time = datetime.utcnow()
    
    async def collect_tick_duration(self):
        """
        Recolecta duración del tick principal.
        
        Mide el tiempo desde start_tick() hasta ahora.
        """
        if self._tick_start_time is None:
            return
        
        duration_ms = (datetime.utcnow() - self._tick_start_time).total_seconds() * 1000
        
        await self.store.store_metric(
            metric_name="tick_duration_ms",
            value=duration_ms,
            component="system"
        )
    
    async def collect_checker_stats(self, checker_stats: Dict[str, Any]):
        """
        Recolecta estadísticas de checkers.
        
        Args:
            checker_stats: Dict con estadísticas por checker
                Ejemplo: {
                    "espn": {"latency_ms": 95, "error_count": 2},
                    "flashscore": {"latency_ms": 120, "error_count": 0}
                }
        """
        for checker_id, stats in checker_stats.items():
            if "latency_ms" in stats:
                await self.store.store_metric(
                    metric_name="checker_latency_ms",
                    value=stats["latency_ms"],
                    labels={"checker": checker_id},
                    component="checker_system"
                )
            
            if "error_count" in stats:
                await self.store.store_metric(
                    metric_name="checker_errors",
                    value=stats["error_count"],
                    labels={"checker": checker_id},
                    component="checker_system"
                )
    
    async def collect_execution_latency(self, latency_ms: float):
        """
        Recolecta latencia de ejecución.
        
        Args:
            latency_ms: Latencia en milisegundos
        """
        await self.store.store_metric(
            metric_name="execution_latency_ms",
            value=latency_ms,
            component="execution"
        )
    
    async def collect_risk_exposure(self):
        """
        Recolecta métricas de exposición de riesgo.
        """
        # Calcular exposición total
        total_exposure = 0.0
        market_exposures = {}
        
        for market_id, exposure_state in state.exposures.items():
            exposure = exposure_state.notional
            total_exposure += exposure
            market_exposures[str(market_id)] = exposure
        
        await self.store.store_metric(
            metric_name="risk_exposure_total",
            value=total_exposure,
            component="risk"
        )
        
        # Exposición por mercado
        for market_id, exposure in market_exposures.items():
            await self.store.store_metric(
                metric_name="risk_exposure_per_market",
                value=exposure,
                labels={"market_id": market_id},
                component="risk"
            )
    
    async def collect_runtime_metrics(self):
        """
        Recolecta métricas del runtime.
        """
        # Número de watchers activos (eventos)
        active_watchers = len(state.events)
        await self.store.store_metric(
            metric_name="watchers_active",
            value=active_watchers,
            component="system"
        )
        
        # Número de mercados activos
        active_markets = len(state.markets)
        await self.store.store_metric(
            metric_name="markets_active",
            value=active_markets,
            component="system"
        )
        
        # Latencia del sistema (desde latency_monitor)
        latency_metrics = await latency_monitor.get_latency_metrics()
        if latency_metrics:
            if "backend_latency_ms" in latency_metrics:
                await self.store.store_metric(
                    metric_name="backend_latency_ms",
                    value=latency_metrics["backend_latency_ms"],
                    component="system"
                )
            
            if "execution_latency_ms" in latency_metrics and latency_metrics["execution_latency_ms"]:
                await self.store.store_metric(
                    metric_name="execution_latency_ms",
                    value=latency_metrics["execution_latency_ms"],
                    component="execution"
                )
    
    async def record_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        component: Optional[str] = None
    ):
        """
        Registra un evento como métrica.
        
        Args:
            event_type: Tipo de evento (ej: "intent_created", "order_filled")
            data: Datos del evento
            component: Componente que emite el evento
        """
        # Extraer valor numérico si existe
        value = data.get("value", 1.0)
        
        # Extraer labels
        labels = {k: str(v) for k, v in data.items() if k != "value"}
        
        await self.store.store_metric(
            metric_name=event_type,
            value=value,
            labels=labels,
            component=component
        )
    
    async def collect_strategy_metrics(self, intents_created: int):
        """
        Recolecta métricas de Strategy Engine.
        
        Args:
            intents_created: Número de intents creados
        """
        await self.store.store_metric(
            metric_name="strategy_intents_total",
            value=intents_created,
            component="strategy"
        )
    
    async def collect_risk_metrics(self, intents_approved: int, intents_rejected: int):
        """
        Recolecta métricas de Risk Engine.
        
        Args:
            intents_approved: Número de intents aprobados
            intents_rejected: Número de intents rechazados
        """
        await self.store.store_metric(
            metric_name="risk_intents_approved",
            value=intents_approved,
            component="risk"
        )
        
        await self.store.store_metric(
            metric_name="risk_intents_rejected",
            value=intents_rejected,
            component="risk"
        )
        
        # Calcular ratio de aprobación
        total = intents_approved + intents_rejected
        if total > 0:
            approval_rate = intents_approved / total
            await self.store.store_metric(
                metric_name="risk_approval_rate",
                value=approval_rate,
                component="risk"
            )
    
    async def collect_execution_metrics(
        self,
        orders_sent: int = 0,
        orders_filled: int = 0,
        orders_rejected: int = 0
    ):
        """
        Recolecta métricas de Execution Engine.
        
        Args:
            orders_sent: Número de órdenes enviadas
            orders_filled: Número de órdenes ejecutadas
            orders_rejected: Número de órdenes rechazadas
        """
        await self.store.store_metric(
            metric_name="execution_orders_sent",
            value=orders_sent,
            component="execution"
        )
        
        await self.store.store_metric(
            metric_name="execution_orders_filled",
            value=orders_filled,
            component="execution"
        )
        
        await self.store.store_metric(
            metric_name="execution_orders_rejected",
            value=orders_rejected,
            component="execution"
        )
        
        # Calcular ratio de fills
        if orders_sent > 0:
            fill_rate = orders_filled / orders_sent
            await self.store.store_metric(
                metric_name="execution_fill_rate",
                value=fill_rate,
                component="execution"
            )
            
            rejection_rate = orders_rejected / orders_sent
            await self.store.store_metric(
                metric_name="execution_rejection_rate",
                value=rejection_rate,
                component="execution"
            )

