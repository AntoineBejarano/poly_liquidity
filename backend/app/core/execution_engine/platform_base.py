"""
Trading Platform Base Interface - Abstracción para múltiples plataformas de trading.

Esta interfaz define el contrato que todas las plataformas (Polymarket, Pinnacle, Bet365, etc.)
deben implementar, permitiendo que el Execution Engine sea multi-plataforma.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from decimal import Decimal
from uuid import UUID

from app.core.strategy_engine.models import PlanLeg
from app.core.execution_engine.platform_models import (
    OrderResult,
    OrderStatusUpdate,
    PlatformFeatureNotSupported
)


class TradingPlatform(ABC):
    """
    Interfaz base para todas las plataformas de trading.
    
    Esta clase define el contrato que todas las implementaciones deben seguir,
    permitiendo que el Execution Engine sea agnóstico de la plataforma específica.
    
    Características:
    - Inmutabilidad: Solo lee ExecutionPlan, nunca lo modifica
    - Trazabilidad: Preserva trace_id a través de todas las operaciones
    - Fail-Safe: Lanza excepciones claras para features no soportadas
    """
    
    def __init__(self, platform_name: str, config: Dict[str, Any]):
        """
        Inicializa la plataforma.
        
        Args:
            platform_name: Nombre de la plataforma (ej: "polymarket", "pinnacle")
            config: Configuración específica de la plataforma
        """
        self.platform_name = platform_name
        self.config = config
    
    @abstractmethod
    async def submit_order(
        self,
        leg: PlanLeg,
        risk_config: Dict[str, any],
        trace_id: Optional[UUID] = None
    ) -> OrderResult:
        """
        Envía una orden a la plataforma.
        
        Args:
            leg: PlanLeg con la información de la orden a ejecutar
            risk_config: Configuración de riesgo del ExecutionPlan
            trace_id: ID de trazabilidad (opcional, para logging)
        
        Returns:
            OrderResult con el resultado de la orden
        
        Raises:
            PlatformFeatureNotSupported: Si el tipo de orden no está soportado
            RuntimeError: Si hay un error al enviar la orden
        """
        pass
    
    @abstractmethod
    async def cancel_order(
        self,
        order_id: str,
        trace_id: Optional[UUID] = None
    ) -> bool:
        """
        Cancela una orden en la plataforma.
        
        Args:
            order_id: ID de la orden en la plataforma
            trace_id: ID de trazabilidad (opcional, para logging)
        
        Returns:
            True si la orden fue cancelada exitosamente, False en caso contrario
        
        Raises:
            RuntimeError: Si hay un error al cancelar la orden
        """
        pass
    
    @abstractmethod
    async def get_order_status(
        self,
        order_id: str,
        trace_id: Optional[UUID] = None
    ) -> OrderStatusUpdate:
        """
        Obtiene el estado actual de una orden.
        
        Args:
            order_id: ID de la orden en la plataforma
            trace_id: ID de trazabilidad (opcional, para logging)
        
        Returns:
            OrderStatusUpdate con el estado actual de la orden
        
        Raises:
            RuntimeError: Si hay un error al obtener el estado
        """
        pass
    
    @abstractmethod
    async def get_balances(self) -> Dict[str, Decimal]:
        """
        Obtiene los balances disponibles en la plataforma.
        
        Returns:
            Dict con los balances por moneda (ej: {"USDC": Decimal("1000.00")})
        
        Raises:
            RuntimeError: Si hay un error al obtener los balances
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Verifica si la plataforma está disponible y configurada correctamente.
        
        Returns:
            True si la plataforma está disponible, False en caso contrario
        """
        pass
    
    def get_platform_name(self) -> str:
        """Retorna el nombre de la plataforma."""
        return self.platform_name

