"""
Metrics and history engine - calculates and exposes key metrics.

This module is now a compatibility wrapper for the new MetricsService.
The new implementation is in app/core/metrics/metrics_service.py
"""
from app.core.metrics.metrics_service import MetricsService

# Create global instance
_metrics_service = MetricsService()


class Metrics:
    """
    Metrics service (compatibility wrapper).
    
    This class maintains backward compatibility with the old interface
    while using the new MetricsService implementation.
    """
    
    def __init__(self):
        """Inicializa el servicio de métricas."""
        self._service = _metrics_service
    
    async def tick(self):
        """
        Register metrics.
        
        This method is called from the main loop to collect metrics.
        """
        await self._service.tick()
    
    @property
    def service(self) -> MetricsService:
        """Obtiene el servicio de métricas subyacente."""
        return self._service

