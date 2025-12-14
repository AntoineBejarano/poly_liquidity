"""
System state manager - maintains live state in memory.
"""
from typing import Dict, Optional
from datetime import datetime
from app.models.market import Market
from app.models.event import Event
from app.models.order import Order
from app.models.position import Position
from app.models.exposure import Exposure
from app.models.wallet import Wallet
from uuid import UUID


class MarketState:
    """In-memory state for a market."""
    def __init__(self):
        self.market_id: Optional[UUID] = None
        self.polymarket_id: Optional[str] = None
        self.last_price: Optional[float] = None
        self.spread: Optional[float] = None
        self.volume: Optional[float] = None
        self.orderbook_snapshot: Optional[dict] = None
        self.updated_at: Optional[datetime] = None


class EventState:
    """In-memory state for an event."""
    def __init__(self):
        self.event_id: Optional[UUID] = None  # ID interno del Event (UUID)
        self.market_id: Optional[UUID] = None  # Market al que pertenece (para exposición)
        self.polymarket_event_id: Optional[str] = None  # ID externo de Polymarket
        self.state: str = "LIVE"  # LIVE / FINISHED_UNCONFIRMED / FINISHED_CONFIRMED / UNKNOWN / UPCOMING / ACTIVE / FINISHED
        self.confidence: float = 0.0
        self.finished_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None
        # Información de quorum dinámico
        self.quorum_used: Optional[int] = None
        self.quorum_required: Optional[int] = None
        self.checkers_available: int = 0
        self.checkers_used: int = 0
        self.quorum_reason: Optional[str] = None
        self.trading_permitted: bool = False


class OrderState:
    """In-memory state for an order."""
    def __init__(self):
        self.order_id: Optional[UUID] = None
        self.market_id: Optional[UUID] = None
        self.status: str = "NEW"  # NEW / PARTIALLY_FILLED / FILLED / CANCELLED
        self.filled_size: float = 0.0
        self.updated_at: Optional[datetime] = None


class PositionState:
    """In-memory state for a position."""
    def __init__(self):
        self.market_id: Optional[UUID] = None
        self.size: float = 0.0
        self.avg_price: float = 0.0
        self.resolved: bool = False
        self.payout: Optional[float] = None
        self.updated_at: Optional[datetime] = None


class ExposureState:
    """In-memory state for exposure."""
    def __init__(self):
        self.market_id: Optional[UUID] = None
        self.notional: float = 0.0
        self.max_allowed: float = 0.0
        self.breached: bool = False
        self.updated_at: Optional[datetime] = None


class RiskConfig:
    """Risk configuration loaded from system_config."""
    def __init__(self):
        self.max_exposure_per_market: float = 50000.0
        self.max_global_exposure: float = 500000.0
        self.max_markets_active: int = 30
        self.min_entry_price: float = 0.98
        self.target_margin: float = 0.001
        self.min_candidate_price: float = 0.97
        self.safety_tick: float = 0.0001
        self.max_single_order_size: float = 10000.0
        self.tick_seconds: float = 1.0
        self.scan_interval_seconds: float = 30.0
        self.min_feed_confidence: float = 0.8
        self.checker_timeout_seconds: float = 5.0
        
        # Scanner configuration
        self.min_price_threshold: float = 0.97
        self.allowed_categories: List[str] = ["sports"]
        self.allowed_subcategories: List[str] = []  # Empty = allow all
        self.scan_interval_seconds: float = 30.0


class SystemState:
    """
    System state manager - maintains live state in memory.
    State is loaded from DB on startup and updated in memory each tick.
    Relevant changes are persisted asynchronously to Neon.
    """
    
    def __init__(self):
        self.system_active: bool = False
        self.markets: Dict[UUID, MarketState] = {}
        self.events: Dict[UUID, EventState] = {}
        self.orders: Dict[UUID, OrderState] = {}
        self.positions: Dict[UUID, PositionState] = {}
        self.exposures: Dict[UUID, ExposureState] = {}
        self.risk_config: RiskConfig = RiskConfig()
    
    def load_from_db(self, db):
        """
        Load initial state from database.
        This is called on startup.
        """
        # Load markets
        markets = db.query(Market).filter(Market.status == "OPEN").all()
        for market in markets:
            state = MarketState()
            state.market_id = market.id
            state.polymarket_id = market.polymarket_id
            state.last_price = market.last_price
            state.updated_at = market.updated_at
            self.markets[market.id] = state
        
        # Load events
        # ⚠️ IMPORTANTE: Events se indexan por event.id (UUID interno), no por market_id
        events = db.query(Event).all()
        for event in events:
            state = EventState()
            state.event_id = event.id  # UUID interno del Event
            state.market_id = event.market_id  # Market al que pertenece (para exposición)
            state.polymarket_event_id = event.polymarket_event_id  # ID externo de Polymarket
            state.state = event.state
            state.confidence = getattr(event, 'confidence', 0.0)  # Puede no existir en el modelo
            state.finished_at = getattr(event, 'finished_at', None)  # Puede no existir en el modelo
            state.updated_at = event.updated_at
            self.events[event.id] = state  # Indexar por event.id, no por market_id
        
        # Load orders
        orders = db.query(Order).filter(Order.status.in_(["NEW", "PARTIALLY_FILLED"])).all()
        for order in orders:
            state = OrderState()
            state.order_id = order.id
            state.market_id = order.market_id
            state.status = order.status
            state.filled_size = order.filled_size
            state.updated_at = order.updated_at
            self.orders[order.id] = state
        
        # Load positions
        positions = db.query(Position).filter(Position.resolved == False).all()
        for position in positions:
            state = PositionState()
            state.market_id = position.market_id
            state.size = position.size
            state.avg_price = position.avg_price
            state.resolved = position.resolved
            state.payout = position.payout
            state.updated_at = position.updated_at
            self.positions[position.market_id] = state
        
        # Load exposures
        exposures = db.query(Exposure).all()
        for exposure in exposures:
            state = ExposureState()
            state.market_id = exposure.market_id
            state.notional = exposure.notional
            state.max_allowed = exposure.max_allowed
            state.breached = exposure.breached
            state.updated_at = exposure.updated_at
            self.exposures[exposure.market_id] = state
    
    def persist_changes(self, db):
        """
        Persist relevant changes to database asynchronously.
        This is called periodically to sync state to DB.
        """
        # This will be implemented to batch update changes
        # For now, it's a placeholder
        pass


# Global state instance
state = SystemState()

