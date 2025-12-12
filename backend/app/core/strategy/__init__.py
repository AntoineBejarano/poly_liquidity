"""
Strategy Engine - Lógica de decisión de entradas en mercados.

Refactorizado según especificación en docs/services/strategy.md
"""
from app.core.strategy.strategy import Strategy
from app.core.strategy.models import OrderIntent, NoEntryReason, MarketState, EventState, StrategyConfig

__all__ = [
    "Strategy",
    "OrderIntent",
    "NoEntryReason",
    "MarketState",
    "EventState",
    "StrategyConfig",
]

