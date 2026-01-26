"""
Metric Sampler - recolección periódica de métricas.
"""
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from app.core.metrics.collector import MetricCollector
from app.core.metrics.store import MetricStore


class MetricSampler:
    """
    Sampler de métricas periódicas.
    
    Ejecuta un loop que recolecta métricas cada N segundos.
    """
    
    def __init__(
        self,
        collector: MetricCollector,
        interval_seconds: float = 2.0
    ):
        """
        Inicializa el sampler.
        
        Args:
            collector: MetricCollector para recolectar métricas
            interval_seconds: Intervalo entre recolecciones (default: 2 segundos)
        """
        self.collector = collector
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Inicia el loop de recolección."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._collection_loop())
    
    async def stop(self):
        """Detiene el loop de recolección."""
        self._running = False
        if self._task:
            await self._task
    
    async def _collection_loop(self):
        """Loop principal de recolección."""
        while self._running:
            try:
                # Recolectar métricas
                await self.collector.collect_tick_duration()
                await self.collector.collect_runtime_metrics()
                await self.collector.collect_risk_exposure()
                
                # Esperar intervalo
                await asyncio.sleep(self.interval_seconds)
            except Exception as e:
                print(f"ERROR: Error in metrics collection loop: {e}")
                await asyncio.sleep(self.interval_seconds)

