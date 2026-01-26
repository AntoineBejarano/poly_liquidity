"""
Filtros para el Scanner Engine.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.config_service import config_service


class ScannerFilters:
    """Filtros para mercados candidatos."""
    
    def __init__(self, config=None):
        """
        Inicializa los filtros con configuración.
        
        Args:
            config: RiskConfig (opcional, para compatibilidad con tests)
        """
        # Mantener config para compatibilidad, pero usar ConfigService directamente
        self.config = config
    
    def filter_structural(self, market: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Filtros estructurales - verifican estructura básica.
        
        Returns:
            (pasa_filtro, razon_si_falla)
        """
        # Filtro 1: status == "OPEN"
        status = market.get("status") or market.get("market_status")
        if status and status != "OPEN":
            return (False, f"Market status is {status}, not OPEN")
        
        # Filtro 2: outcomes.length == 2 (binarios)
        outcomes = market.get("outcomes", [])
        if not isinstance(outcomes, list) or len(outcomes) != 2:
            return (False, f"Market has {len(outcomes) if isinstance(outcomes, list) else 0} outcomes, expected 2")
        
        # Filtro 3: Outcomes tienen precio válido
        for outcome in outcomes:
            price = outcome.get("price") or outcome.get("current_price")
            if price is None or not isinstance(price, (int, float)) or price <= 0:
                return (False, f"Outcome {outcome.get('name', 'unknown')} has invalid price")
        
        # Filtro 4: Mercado tiene polymarket_id
        polymarket_id = market.get("id") or market.get("market_id")
        if not polymarket_id:
            return (False, "Market missing polymarket_id")
        
        return (True, None)
    
    def filter_category(self, market: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Filtros por categoría.
        
        Returns:
            (pasa_filtro, razon_si_falla)
        """
        # Obtener categoría y subcategoría
        category = (market.get("category") or "").lower().strip()
        subcategory = (market.get("subcategory") or "").lower().strip() if market.get("subcategory") else None
        
        # Configuración de categorías permitidas (desde ConfigService)
        scanner_config = config_service.get_scanner_config()
        allowed_categories = scanner_config.get("allowed_categories", ["sports"])
        allowed_subcategories = scanner_config.get("allowed_subcategories", [])
        
        # Verificar categoría
        if category not in allowed_categories:
            return (False, f"Category '{category}' not in allowed categories {allowed_categories}")
        
        # Verificar subcategoría si está configurado
        if allowed_subcategories and subcategory:
            if subcategory not in allowed_subcategories:
                return (False, f"Subcategory '{subcategory}' not in allowed subcategories {allowed_subcategories}")
        
        return (True, None)
    
    def filter_price(self, market: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Filtros por precio.
        
        Returns:
            (pasa_filtro, razon_si_falla)
        """
        # Obtener precios de outcomes
        outcomes = market.get("outcomes", [])
        if len(outcomes) != 2:
            return (False, "Cannot filter price: market must have 2 outcomes")
        
        # Calcular best_yes_price y best_no_price
        prices = []
        for outcome in outcomes:
            price = outcome.get("price") or outcome.get("current_price", 0.0)
            prices.append(float(price))
        
        # Ordenar precios (mayor a menor)
        prices.sort(reverse=True)
        best_yes_price = prices[0]
        best_no_price = prices[1] if len(prices) > 1 else 0.0
        
        # Filtro: best_yes_price >= min_price_threshold (desde ConfigService)
        scanner_config = config_service.get_scanner_config()
        min_price_threshold = scanner_config.get("min_price_threshold", 0.97)
        
        if best_yes_price < min_price_threshold:
            return (False, f"Best YES price {best_yes_price:.3f} < threshold {min_price_threshold:.3f}")
        
        return (True, None)
    
    def filter_temporal(self, market: Dict[str, Any], event_metadata: Optional[Dict[str, Any]] = None) -> tuple[bool, Optional[str]]:
        """
        Filtros por temporalidad.
        
        Por ahora, este filtro es opcional y puede ser configurado.
        
        Returns:
            (pasa_filtro, razon_si_falla)
        """
        # Por defecto, no filtrar por temporalidad
        # Esto se puede mejorar en el futuro para filtrar mercados con fechas muy lejanas
        
        # Si hay event_start_time_parsed, verificar que no sea muy lejano (opcional)
        if event_metadata and event_metadata.get("event_start_time_parsed"):
            event_time = event_metadata["event_start_time_parsed"]
            if isinstance(event_time, datetime):
                # Filtrar eventos más de N días en el futuro (desde ConfigService)
                max_days_ahead = config_service.get("scanner_max_event_days_ahead", 7)
                days_ahead = (event_time - datetime.utcnow()).days
                if days_ahead > max_days_ahead:
                    return (False, f"Event is {days_ahead} days ahead, exceeds max {max_days_ahead}")
        
        return (True, None)
    
    def apply_all_filters(
        self,
        market: Dict[str, Any],
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Aplica todos los filtros en orden.
        
        Returns:
            (pasa_todos_filtros, razon_si_falla)
        """
        # 1. Filtros estructurales (más rápidos primero)
        passes, reason = self.filter_structural(market)
        if not passes:
            return (False, reason)
        
        # 2. Filtros por categoría
        passes, reason = self.filter_category(market)
        if not passes:
            return (False, reason)
        
        # 3. Filtros por precio
        passes, reason = self.filter_price(market)
        if not passes:
            return (False, reason)
        
        # 4. Filtros temporales (opcional)
        passes, reason = self.filter_temporal(market, event_metadata)
        if not passes:
            return (False, reason)
        
        return (True, None)

