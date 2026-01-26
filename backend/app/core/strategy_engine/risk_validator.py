"""
Risk Validator - Valida risk_config de ExecutionPlan antes y durante la ejecución.

Valida parámetros de riesgo como max_slippage, max_fill_delay_ms, etc.
"""
import logging
from typing import Dict, Any, Optional
from decimal import Decimal, InvalidOperation
from datetime import datetime

from app.models.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class RiskValidator:
    """
    Validador de configuración de riesgo para ExecutionPlans.
    
    Valida parámetros de riesgo antes y durante la ejecución de un plan.
    """
    
    def __init__(self, plan: ExecutionPlan):
        self.plan = plan
        self.risk_config = plan.risk_config or {}
    
    def validate_plan_risk_config(self) -> tuple[bool, Optional[str]]:
        """
        Valida la configuración de riesgo del plan.
        
        Returns:
            (is_valid, error_message)
        """
        # Validar max_slippage
        max_slippage = self.risk_config.get("max_slippage")
        if max_slippage is not None:
            try:
                max_slippage = float(max_slippage)
                if max_slippage < 0 or max_slippage > 1:
                    return False, f"max_slippage must be between 0 and 1, got {max_slippage}"
            except (ValueError, TypeError):
                return False, f"max_slippage must be a number, got {max_slippage}"
        
        # Validar max_fill_delay_ms
        max_fill_delay_ms = self.risk_config.get("max_fill_delay_ms")
        if max_fill_delay_ms is not None:
            try:
                max_fill_delay_ms = int(max_fill_delay_ms)
                if max_fill_delay_ms < 0:
                    return False, f"max_fill_delay_ms must be >= 0, got {max_fill_delay_ms}"
            except (ValueError, TypeError):
                return False, f"max_fill_delay_ms must be an integer, got {max_fill_delay_ms}"
        
        # Validar max_partial_fill_ratio
        max_partial_fill_ratio = self.risk_config.get("max_partial_fill_ratio")
        if max_partial_fill_ratio is not None:
            try:
                max_partial_fill_ratio = float(max_partial_fill_ratio)
                if max_partial_fill_ratio < 0 or max_partial_fill_ratio > 1:
                    return False, f"max_partial_fill_ratio must be between 0 and 1, got {max_partial_fill_ratio}"
            except (ValueError, TypeError):
                return False, f"max_partial_fill_ratio must be a number, got {max_partial_fill_ratio}"
        
        # Validar abort_on_price_move
        abort_on_price_move = self.risk_config.get("abort_on_price_move")
        if abort_on_price_move is not None and not isinstance(abort_on_price_move, bool):
            return False, f"abort_on_price_move must be a boolean, got {abort_on_price_move}"
        
        return True, None
    
    def validate_price(self, leg: Dict[str, Any], current_price: Decimal) -> tuple[bool, Optional[str]]:
        """
        Valida que el precio actual no exceda max_slippage.
        
        Args:
            leg: Leg del plan
            current_price: Precio actual del mercado
        
        Returns:
            (is_valid, error_message)
        """
        max_slippage = self.risk_config.get("max_slippage")
        if max_slippage is None:
            return True, None  # No hay límite de slippage
        
        try:
            max_slippage = float(max_slippage)
            target_price_val = leg.get("target_price", 0)
            if target_price_val is None:
                return False, "target_price is None, cannot validate slippage"
            target_price = Decimal(str(target_price_val))
            
            if target_price == 0:
                return False, "target_price is 0, cannot validate slippage"
            
            # Calcular slippage
            price_diff = abs(current_price - target_price)
            slippage = float(price_diff / target_price)
            
            if slippage > max_slippage:
                return False, (
                    f"Price slippage {slippage:.4f} exceeds max_slippage {max_slippage:.4f}. "
                    f"Target: {target_price}, Current: {current_price}"
                )
            
            return True, None
            
        except (ValueError, TypeError, ZeroDivisionError, InvalidOperation) as e:
            return False, f"Error validating price slippage: {str(e)}"
    
    def validate_liquidity(self, leg: Dict[str, Any], available_liquidity: Decimal) -> tuple[bool, Optional[str]]:
        """
        Valida que haya suficiente liquidez para ejecutar el leg.
        
        Args:
            leg: Leg del plan
            available_liquidity: Liquidez disponible en el mercado
        
        Returns:
            (is_valid, error_message)
        """
        size_usdc = Decimal(str(leg.get("size_usdc", 0)))
        
        if available_liquidity < size_usdc:
            return False, (
                f"Insufficient liquidity. Required: {size_usdc}, Available: {available_liquidity}"
            )
        
        return True, None
    
    def should_abort_on_price_move(self) -> bool:
        """
        Retorna True si el plan debe abortarse cuando el precio se mueve.
        """
        return self.risk_config.get("abort_on_price_move", False)
    
    def get_max_fill_delay_ms(self) -> Optional[int]:
        """
        Retorna el máximo delay permitido para un fill en milisegundos.
        """
        max_fill_delay_ms = self.risk_config.get("max_fill_delay_ms")
        if max_fill_delay_ms is not None:
            try:
                return int(max_fill_delay_ms)
            except (ValueError, TypeError):
                return None
        return None
    
    def get_max_partial_fill_ratio(self) -> Optional[float]:
        """
        Retorna el máximo ratio de partial fill permitido.
        """
        max_partial_fill_ratio = self.risk_config.get("max_partial_fill_ratio")
        if max_partial_fill_ratio is not None:
            try:
                return float(max_partial_fill_ratio)
            except (ValueError, TypeError):
                return None
        return None
    
    def validate_partial_fill(self, leg: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Valida que un partial fill no exceda max_partial_fill_ratio.
        
        Args:
            leg: Leg del plan con filled_size actualizado
        
        Returns:
            (is_valid, error_message)
        """
        max_partial_fill_ratio = self.get_max_partial_fill_ratio()
        if max_partial_fill_ratio is None:
            return True, None  # No hay límite
        
        try:
            size = Decimal(str(leg.get("size", 0)))
            filled_size = Decimal(str(leg.get("filled_size", 0)))
            
            if size == 0:
                return False, "Leg size is 0, cannot validate partial fill ratio"
            
            fill_ratio = float(filled_size / size)
            
            if fill_ratio < max_partial_fill_ratio:
                return False, (
                    f"Partial fill ratio {fill_ratio:.4f} is below minimum "
                    f"{max_partial_fill_ratio:.4f}. Leg may need to be retried or compensated."
                )
            
            return True, None
            
        except (ValueError, TypeError, ZeroDivisionError, InvalidOperation) as e:
            return False, f"Error validating partial fill: {str(e)}"

