"""
Risk engine - validates or rejects order intents according to risk rules.
"""
from typing import List
from app.core.state import state
from app.core.config_service import config_service
from app.core.strategy import OrderIntent
from app.core.latency_monitor import latency_monitor, LatencyStatus
from app.database import SessionLocal
from app.models.exposure import Exposure
from datetime import datetime
from uuid import uuid4


class ApprovedOrderIntent:
    """Approved order intent that passed risk validation."""
    def __init__(self, intent: OrderIntent):
        self.market_id = intent.market_id
        self.side = intent.side
        self.price = intent.price
        self.size = intent.size


class RiskEngine:
    """Risk engine service."""
    
    def _calculate_exposure(self, market_id, size: float, price: float) -> float:
        """Calculate exposure: size * price"""
        return size * price
    
    def _calculate_global_exposure(self) -> float:
        """Calculate total global exposure."""
        total = 0.0
        for exposure_state in state.exposures.values():
            total += exposure_state.notional
        return total
    
    def _check_risk_rules(self, intent: OrderIntent) -> tuple[bool, str]:
        """
        Check risk rules for an order intent.
        Returns (is_valid, reason_if_invalid).
        """
        config = state.risk_config
        
        # Calculate new exposure for this market
        new_exposure_market = self._calculate_exposure(intent.market_id, intent.size, intent.price)
        if intent.market_id in state.exposures:
            new_exposure_market += state.exposures[intent.market_id].notional
        
        # Check: exposure_new_market <= MAX_EXPOSURE_PER_MARKET
        if new_exposure_market > config.max_exposure_per_market:
            return (False, f"Market exposure {new_exposure_market} exceeds max {config.max_exposure_per_market}")
        
        # Calculate new global exposure
        current_global = self._calculate_global_exposure()
        new_exposure_global = current_global + self._calculate_exposure(intent.market_id, intent.size, intent.price)
        
        # Check: exposure_new_global <= MAX_GLOBAL_EXPOSURE
        if new_exposure_global > config.max_global_exposure:
            return (False, f"Global exposure {new_exposure_global} exceeds max {config.max_global_exposure}")
        
        # Count active markets (markets with positions or orders)
        active_markets = set()
        for pos_id in state.positions.keys():
            active_markets.add(pos_id)
        for order_id, order_state in state.orders.items():
            if order_state.status in ("NEW", "PARTIALLY_FILLED"):
                active_markets.add(order_state.market_id)
        
        # If this is a new market, add it to count
        if intent.market_id not in active_markets:
            active_markets.add(intent.market_id)
        
        # Check: num_markets_active <= MAX_MARKETS_ACTIVE
        if len(active_markets) > config.max_markets_active:
            return (False, f"Active markets {len(active_markets)} exceeds max {config.max_markets_active}")
        
        return (True, "")
    
    def _update_exposure_state(self, intent: OrderIntent):
        """Update exposure state after approval."""
        market_id = intent.market_id
        new_exposure = self._calculate_exposure(market_id, intent.size, intent.price)
        
        if market_id not in state.exposures:
            from app.core.state import ExposureState
            state.exposures[market_id] = ExposureState()
            state.exposures[market_id].market_id = market_id
        
        exposure_state = state.exposures[market_id]
        exposure_state.notional += new_exposure
        exposure_state.max_allowed = state.risk_config.max_exposure_per_market
        exposure_state.breached = exposure_state.notional > exposure_state.max_allowed
        exposure_state.updated_at = datetime.utcnow()
        
        # Persist to DB
        db = SessionLocal()
        try:
            db_exposure = db.query(Exposure).filter(Exposure.market_id == market_id).first()
            if not db_exposure:
                db_exposure = Exposure(
                    id=uuid4(),
                    market_id=market_id,
                    notional=exposure_state.notional,
                    max_allowed=exposure_state.max_allowed,
                    breached=exposure_state.breached,
                    timestamp=datetime.utcnow(),
                )
                db.add(db_exposure)
            else:
                db_exposure.notional = exposure_state.notional
                db_exposure.max_allowed = exposure_state.max_allowed
                db_exposure.breached = exposure_state.breached
                db_exposure.timestamp = datetime.utcnow()
            
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error updating exposure in DB: {e}")
        finally:
            db.close()
    
    async def tick(self, intents: List[OrderIntent]) -> List[ApprovedOrderIntent]:
        """
        Apply risk limits to order intents.
        Returns list of approved intents that passed all risk rules.
        
        Also applies latency-based fail-safe:
        - RED: Reject all new intents (stop new entries)
        - YELLOW: Allow but with reduced size (already handled in Strategy)
        - GREEN: Normal operation
        """
        approved: List[ApprovedOrderIntent] = []
        
        # Get latency status for fail-safe
        latency_status = latency_monitor.get_status()
        
        # RED status: Fail-safe - reject all new intents
        if latency_status == LatencyStatus.RED:
            print("Latency status RED: Rejecting all new order intents (fail-safe)")
            return approved
        
        for intent in intents:
            # Check risk rules
            is_valid, reason = self._check_risk_rules(intent)
            
            if not is_valid:
                print(f"Order intent rejected: {reason}")
                continue
            
            # YELLOW status: Additional checks (size already reduced in Strategy)
            if latency_status == LatencyStatus.YELLOW:
                # Additional validation: avoid competing in high-competition markets
                # This is a placeholder - can be enhanced with market competition metrics
                pass
            
            # Create approved intent
            approved_intent = ApprovedOrderIntent(intent)
            approved.append(approved_intent)
            
            # Update exposure state (hypothetical, will be finalized on fill)
            # We update it here to track pending exposure
            self._update_exposure_state(intent)
        
        return approved
