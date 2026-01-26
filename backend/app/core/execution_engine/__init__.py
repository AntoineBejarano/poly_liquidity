"""
Execution Engine - Abstracción de plataformas de trading.

Este módulo proporciona una capa de abstracción para múltiples plataformas
de trading (Polymarket, Pinnacle, Bet365, etc.), permitiendo que el sistema
sea multi-plataforma sin modificar la lógica de los grafos de ejecución.
"""
from app.core.execution_engine.platform_base import TradingPlatform
from app.core.execution_engine.platform_models import (
    OrderResult,
    OrderStatusUpdate,
    OrderStatus,
    OrderType,
    PlatformFeatureNotSupported
)
from app.core.execution_engine.platforms import PolymarketAdapter

__all__ = [
    "TradingPlatform",
    "OrderResult",
    "OrderStatusUpdate",
    "OrderStatus",
    "OrderType",
    "PlatformFeatureNotSupported",
    "PolymarketAdapter"
]

