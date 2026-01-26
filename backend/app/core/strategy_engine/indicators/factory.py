"""
Factory para crear proveedores de señales según el tipo de estrategia.
"""
from typing import Dict, Type
import logging

from app.core.strategy_engine.indicators.base import SignalProvider
from app.core.strategy_engine.indicators.liquidity_provider import LiquidityProvider
from app.core.strategy_engine.indicators.arbitrage_provider import ArbitrageProvider

logger = logging.getLogger(__name__)

# Registry de proveedores
_PROVIDER_REGISTRY: Dict[str, Type[SignalProvider]] = {
    "liquidity": LiquidityProvider,
    "liquidity_near_end": LiquidityProvider,  # Alias
    "surebet_arbitrage": ArbitrageProvider,
    "arbitrage": ArbitrageProvider,  # Alias
}


def create_signal_provider(
    strategy_type: str,
    context: 'GraphExecutionContext'
) -> SignalProvider:
    """
    Crea el proveedor de señales apropiado según el strategy_type.
    
    Args:
        strategy_type: Tipo de estrategia ("liquidity", "surebet_arbitrage", etc.)
        context: Contexto de ejecución del grafo
    
    Returns:
        Instancia del proveedor correspondiente
    
    Raises:
        ValueError: Si el strategy_type no está soportado
    """
    provider_class = _PROVIDER_REGISTRY.get(strategy_type)
    if not provider_class:
        raise ValueError(
            f"Unsupported strategy_type: {strategy_type}. "
            f"Supported types: {list(_PROVIDER_REGISTRY.keys())}"
        )
    
    logger.debug(f"Creating signal provider: {strategy_type} -> {provider_class.__name__}")
    return provider_class(context)


def register_provider(strategy_type: str, provider_class: Type[SignalProvider]):
    """
    Registra un nuevo tipo de proveedor (útil para extensibilidad).
    
    Args:
        strategy_type: Tipo de estrategia
        provider_class: Clase del proveedor que hereda de SignalProvider
    """
    if not issubclass(provider_class, SignalProvider):
        raise TypeError(f"provider_class must be a subclass of SignalProvider")
    
    _PROVIDER_REGISTRY[strategy_type] = provider_class
    logger.info(f"Registered signal provider: {strategy_type} -> {provider_class.__name__}")

