"""
Calculate Order Size Node - Calcula el tamaño de orden.

Basado en configuración de riesgo y estado del mercado.
"""
from typing import Dict, Any

from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult


class CalculateOrderSizeNode(GraphNode):
    """
    Nodo que calcula el tamaño de orden.
    
    Basado en configuración de riesgo y estado del mercado.
    Guarda el resultado en context.calculated_price y context.calculated_size.
    """
    
    async def execute(self) -> SuccessResult:
        """
        Calcula el tamaño de orden y precio.
        
        Config:
            method: str - Método de cálculo
                - "fixed_range": Entre min y max
                - "percentage": Porcentaje del bank
                - "kelly": Criterio de Kelly (futuro)
            min: float - Tamaño mínimo (USDC) - para fixed_range
            max: float - Tamaño máximo (USDC) - para fixed_range
            percentage: float - Porcentaje del bank - para percentage
        
        Requiere:
            - market_state en context.collected_state (para obtener precio)
        """
        method = self.config.get("method", "fixed_range")
        
        # Obtener precio del mercado
        price = self._get_market_price()
        if price is None:
            raise ValueError("Cannot calculate order size: market price not available")
        
        # Calcular tamaño según método
        if method == "fixed_range":
            size_usdc = self._calculate_fixed_range()
        elif method == "percentage":
            size_usdc = self._calculate_percentage()
        else:
            raise ValueError(f"Unknown calculation method: {method}")
        
        # Calcular tamaño en shares
        size = size_usdc / price if price > 0 else 0
        
        # Guardar en contexto
        if not hasattr(self.context, 'calculated_price'):
            self.context.calculated_price = None
        if not hasattr(self.context, 'calculated_size'):
            self.context.calculated_size = None
        
        self.context.calculated_price = price
        self.context.calculated_size = size
        
        return SuccessResult()
    
    def _get_market_price(self) -> float:
        """Obtiene el precio del mercado desde el estado recopilado."""
        if not hasattr(self.context, 'collected_state') or not self.context.collected_state:
            return None
        
        market_state = self.context.collected_state.get("market_state")
        if not market_state:
            return None
        
        # Intentar obtener last_price o price
        if isinstance(market_state, dict):
            return market_state.get("last_price") or market_state.get("price")
        
        return None
    
    def _calculate_fixed_range(self) -> float:
        """Calcula tamaño usando rango fijo."""
        min_size = self.config.get("min", 0.0)
        max_size = self.config.get("max", 1000.0)
        
        # Por ahora, usar el máximo (se puede hacer más sofisticado)
        # En el futuro, podría considerar riesgo, exposición, etc.
        return max_size
    
    def _calculate_percentage(self) -> float:
        """Calcula tamaño usando porcentaje del bank."""
        percentage = self.config.get("percentage", 5.0)  # Default 5%
        
        # Obtener bank desde risk_state o usar un valor por defecto
        if hasattr(self.context, 'collected_state') and self.context.collected_state:
            risk_state = self.context.collected_state.get("risk_state")
            if risk_state and isinstance(risk_state, dict):
                bank = risk_state.get("available_bank", 10000.0)  # Default
            else:
                bank = 10000.0  # Default
        else:
            bank = 10000.0  # Default
        
        size_usdc = bank * (percentage / 100.0)
        
        # Aplicar límites si existen
        min_size = self.config.get("min", 0.0)
        max_size = self.config.get("max", float('inf'))
        
        return max(min_size, min(size_usdc, max_size))

