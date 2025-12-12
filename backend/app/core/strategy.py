"""
Strategy engine - decides when to enter, at what price, and with what size.

DEPRECATED: Este archivo se mantiene por compatibilidad.
Usar app.core.strategy.strategy.Strategy en su lugar.
"""
from app.core.strategy import Strategy as NewStrategy, OrderIntent

# Re-exportar para compatibilidad
Strategy = NewStrategy
    """Strategy service."""
    
    def __init__(self):
        self._last_intents: List[OrderIntent] = []
    
    def _calculate_target_price(self, best_ask: float, best_bid: float) -> float:
        """
        Calculate target price for order.
        Formula: min(best_ask - SAFETY_TICK, 1.0 - TARGET_MARGIN)
        
        Latency-based adjustments:
        - GREEN: Normal target price
        - YELLOW: Increase safety_tick (more conservative)
        - RED: Very conservative (shouldn't enter anyway)
        """
        config = state.risk_config
        
        # Get latency status for fail-safe
        latency_status = latency_monitor.get_status()
        
        # Adjust safety_tick based on latency
        effective_safety_tick = config.safety_tick
        if latency_status == LatencyStatus.YELLOW:
            # Increase safety tick by 2x (more conservative)
            effective_safety_tick = config.safety_tick * 2.0
        elif latency_status == LatencyStatus.RED:
            # Very conservative (though we shouldn't enter in RED anyway)
            effective_safety_tick = config.safety_tick * 3.0
        
        target_price = min(
            best_ask - effective_safety_tick,
            1.0 - config.target_margin
        )
        return max(target_price, best_bid)  # Don't go below best bid
    
    def _calculate_size(
        self,
        market_id: UUID,
        target_price: float,
        orderbook_liquidity: float
    ) -> float:
        """
        Calculate order size based on:
        - max_per_market (in USDC)
        - current_exposure_market
        - liquidity available in orderbook at target price
        - latency status (fail-safe: reduce size if latency is elevated)
        """
        config = state.risk_config
        
        # Get latency status for fail-safe
        latency_status = latency_monitor.get_status()
        
        # Get current exposure for this market
        current_exposure = 0.0
        if market_id in state.exposures:
            current_exposure = state.exposures[market_id].notional
        
        # Calculate remaining capacity
        remaining_capacity = config.max_exposure_per_market - current_exposure
        
        # Size based on remaining capacity
        size_from_capacity = remaining_capacity / target_price if target_price > 0 else 0.0
        
        # Size from orderbook liquidity
        size_from_liquidity = orderbook_liquidity
        
        # Maximum single order size
        max_single = config.max_single_order_size / target_price if target_price > 0 else 0.0
        
        # Take minimum of all constraints
        size = min(
            size_from_capacity,
            size_from_liquidity,
            max_single
        )
        
        # Apply latency-based fail-safe adjustments
        if latency_status == LatencyStatus.RED:
            # RED: No new entries (return 0)
            return 0.0
        elif latency_status == LatencyStatus.YELLOW:
            # YELLOW: Reduce size by 50%
            size = size * 0.5
        
        return max(0.0, size)
    
    def _get_orderbook_liquidity(self, market_id: UUID, target_price: float) -> float:
        """
        Get available liquidity in orderbook at target price.
        This is a placeholder - will need actual orderbook data from scanner.
        """
        # TODO: Get from market_state.orderbook_snapshot
        if market_id in state.markets:
            orderbook = state.markets[market_id].orderbook_snapshot
            if orderbook:
                # Parse orderbook to find liquidity at target_price
                # This is simplified - actual implementation needs proper orderbook parsing
                return orderbook.get("liquidity_at_price", {}).get(str(target_price), 10000.0)
        
        # Default liquidity estimate
        return 10000.0
    
    async def tick(self) -> List[OrderIntent]:
        """
        Decide on orders based on:
        - Market state
        - Event state
        - Exposure state
        
        Returns list of OrderIntents (proposed orders).
        """
        intents: List[OrderIntent] = []
        config = state.risk_config
        
        # Iterate through markets in state
        for market_id, market_state in state.markets.items():
            # Check event state
            event_state = state.events.get(market_id)
            if not event_state:
                continue
            
            # Condition: event_state == FINISHED_CONFIRMED
            if event_state.state != "FINISHED_CONFIRMED":
                continue
            
            # Condition: market_price >= MIN_ENTRY_PRICE
            if not market_state.last_price or market_state.last_price < config.min_entry_price:
                continue
            
            # Get best ask and bid from orderbook
            # This is simplified - actual implementation needs proper orderbook parsing
            best_ask = market_state.last_price + (market_state.spread or 0.0) / 2
            best_bid = market_state.last_price - (market_state.spread or 0.0) / 2
            
            # Calculate target price
            target_price = self._calculate_target_price(best_ask, best_bid)
            
            # Get orderbook liquidity
            liquidity = self._get_orderbook_liquidity(market_id, target_price)
            
            # Calculate size
            size = self._calculate_size(market_id, target_price, liquidity)
            
            # Only create intent if size > 0
            if size > 0:
                intent = OrderIntent(
                    market_id=market_id,
                    side="BUY",
                    price=target_price,
                    size=size
                )
                intents.append(intent)
        
        self._last_intents = intents
        return intents
