"""
Calculate Order Size Node - Calcula el tamaño de orden.

Basado en configuración de riesgo y estado del mercado.
"""
from typing import Dict, Any

from app.core.strategy_engine.nodes.base import GraphNode, CalculationResult


class CalculateOrderSizeNode(GraphNode):
    """
    Nodo que calcula el tamaño de orden.
    
    Basado en configuración de riesgo y estado del mercado.
    Guarda el resultado en context.calculated_price y context.calculated_size.
    """
    
    async def execute(self) -> CalculationResult:
        """
        Calcula el tamaño de orden y precio.
        
        Config:
            method: str - Método de cálculo
                - "fixed_range": Entre min y max
                - "percentage": Porcentaje del bank
                - "capacity_aware": Respeta depth_usdc_at_50bps del orderbook (min(order_usdc, depth * factor))
                - "kelly": Criterio de Kelly (futuro)
            min: float - Tamaño mínimo (USDC) - para fixed_range
            max: float - Tamaño máximo (USDC) - para fixed_range
            percentage: float - Porcentaje del bank - para percentage
        
        Requiere:
            - market_state en context.collected_state (para obtener precio)
        
        Retorna:
            CalculationResult con size, price, size_usdc
        """
        method = self.config.get("method", "fixed_range")
        
        # Obtener precio del mercado (orderbook_state.best_ask_price o market_state.last_price)
        price = self._get_market_price()
        if price is None:
            raise ValueError("Cannot calculate order size: market price not available")
        
        # Calcular tamaño según método
        if method == "fixed_range":
            size_usdc = self._calculate_fixed_range()
        elif method == "percentage":
            size_usdc = self._calculate_percentage()
        elif method == "capacity_aware":
            size_usdc = self._calculate_capacity_aware()
        else:
            raise ValueError(f"Unknown calculation method: {method}")
        
        # Calcular tamaño en shares
        size = size_usdc / price if price > 0 else 0
        
        # Guardar en contexto (para compatibilidad con nodos que aún lo usan)
        if not hasattr(self.context, 'calculated_price'):
            self.context.calculated_price = None
        if not hasattr(self.context, 'calculated_size'):
            self.context.calculated_size = None
        if not hasattr(self.context, 'calculated_size_usdc'):
            self.context.calculated_size_usdc = None
        
        self.context.calculated_price = price
        self.context.calculated_size = size
        self.context.calculated_size_usdc = size_usdc
        
        # Retornar CalculationResult con los datos calculados
        return CalculationResult(size=size, price=price, size_usdc=size_usdc)
    
    def _get_market_price(self) -> float:
        """Obtiene el precio del mercado desde orderbook_state (best_ask_price) o market_state (last_price)."""
        if not hasattr(self.context, 'collected_state') or not self.context.collected_state:
            return None
        cs = self.context.collected_state

        # Preferir orderbook_state.best_ask_price (BUY side)
        orderbook_state = cs.get("orderbook_state")
        if isinstance(orderbook_state, dict):
            price = orderbook_state.get("best_ask_price")
            if price is not None:
                return float(price)

        # Fallback: market_state
        market_state = cs.get("market_state")
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

    def _calculate_capacity_aware(self) -> float:
        """
        Calcula tamaño respetando liquidez disponible en el orderbook.
        size_usdc = min(base_size, depth_usdc_at_50bps * capacity_factor).
        """
        base_size = self._calculate_fixed_range()
        capacity_factor = self.config.get("capacity_factor", 0.5)  # Usar hasta 50% del depth
        orderbook_state = None
        if hasattr(self.context, "collected_state") and self.context.collected_state:
            orderbook_state = self.context.collected_state.get("orderbook_state")
        if not isinstance(orderbook_state, dict):
            return base_size
        depth = orderbook_state.get("depth_usdc_at_50bps")
        if depth is None:
            return base_size
        try:
            depth_f = float(depth)
        except (TypeError, ValueError):
            return base_size
        cap = depth_f * capacity_factor
        min_size = self.config.get("min", 0.0)
        max_size = self.config.get("max", float("inf"))
        return max(min_size, min(base_size, cap, max_size))

