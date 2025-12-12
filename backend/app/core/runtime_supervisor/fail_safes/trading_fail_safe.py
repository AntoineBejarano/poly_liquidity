"""
Trading Fail-Safe - protección automática para trading.
"""
from typing import Optional
from datetime import datetime
from app.core.runtime_supervisor.runtime_mode import RuntimeMode


class TradingFailSafe:
    """
    Fail-Safe para trading.
    
    Acciones automáticas cuando el sistema entra en modo RED:
    - Cancelar órdenes abiertas
    - Rechazar nuevas entradas
    """
    
    def __init__(self, execution_engine=None):
        """
        Inicializa el fail-safe.
        
        Args:
            execution_engine: Referencia al Execution Engine (opcional)
        """
        self.execution_engine = execution_engine
        self._last_triggered: Optional[datetime] = None
        self._triggered_count = 0
    
    async def trigger(self, reason: str):
        """
        Activa el fail-safe.
        
        Args:
            reason: Razón de la activación
        """
        self._last_triggered = datetime.utcnow()
        self._triggered_count += 1
        
        # Cancelar órdenes abiertas si tenemos acceso al Execution Engine
        if self.execution_engine:
            try:
                await self.execution_engine._cancel_all_open_orders()
            except Exception as e:
                print(f"ERROR: Failed to cancel orders in fail-safe: {e}")
        
        print(f"TRADING FAIL-SAFE TRIGGERED: {reason}")
    
    async def recover(self):
        """Recupera del fail-safe."""
        self._last_triggered = None
        print("TRADING FAIL-SAFE RECOVERED")
    
    def is_triggered(self) -> bool:
        """Verifica si el fail-safe está activo."""
        return self._last_triggered is not None
    
    def get_info(self) -> dict:
        """Obtiene información del fail-safe."""
        return {
            "triggered": self.is_triggered(),
            "last_triggered": self._last_triggered.isoformat() if self._last_triggered else None,
            "triggered_count": self._triggered_count
        }

