"""
Live Control State Store - Estado agregado en memoria.

Según especificación en docs/services/livecontrol.md
"""
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class EventState:
    """Estado de un evento."""
    event_id: str
    event_type: str
    status: str  # LIVE, FINISHED_CONFIRMED, FINISHED_UNCONFIRMED, UNKNOWN
    confidence: float
    watcher_status: str  # active, idle, error
    markets: list = field(default_factory=list)
    sources: Dict[str, str] = field(default_factory=dict)
    last_update: Optional[datetime] = None


@dataclass
class MarketState:
    """Estado de un mercado."""
    market_id: str
    event_id: Optional[str] = None
    state: str = "UNKNOWN"  # FINISHED_CONFIRMED, etc.
    best_ask: float = 0.0
    best_bid: float = 0.0
    exposure: float = 0.0
    last_intent: Optional[Dict[str, Any]] = None
    last_update: Optional[datetime] = None


@dataclass
class WatcherState:
    """Estado de un watcher."""
    event_id: str
    event_name: Optional[str] = None
    status: str = "active"  # active, idle, error
    checks_per_minute: int = 0
    last_check: Optional[datetime] = None
    sources: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    recent_logs: list = field(default_factory=list)
    last_update: Optional[datetime] = None


@dataclass
class OrderState:
    """Estado de una orden."""
    order_id: str
    market_id: str
    status: str  # submitted, filled, cancelled
    fills: list = field(default_factory=list)
    avg_price: float = 0.0
    timestamp: Optional[datetime] = None


@dataclass
class LatencyState:
    """Estado de latencia."""
    mode: str = "GREEN"  # GREEN, YELLOW, RED
    latency_ms: float = 0.0
    last_update: Optional[datetime] = None


@dataclass
class SystemHealth:
    """Estado de salud del sistema."""
    runtime_mode: str = "GREEN"
    exposure_total: float = 0.0
    markets_active: int = 0
    watchers_active: int = 0
    last_fill: Optional[Dict[str, Any]] = None
    last_error: Optional[str] = None
    last_event_resolved: Optional[str] = None
    circuit_breaker_status: str = "CLOSED"
    trading_status: str = "ACTIVE"
    last_update: Optional[datetime] = None


class LiveControlStore:
    """
    Estado agregado del Live Control.
    
    Mantiene estado en memoria de eventos, mercados, watchers, órdenes,
    latencia y salud del sistema.
    """
    
    def __init__(self):
        """Inicializa el store."""
        self.events: Dict[str, EventState] = {}
        self.markets: Dict[str, MarketState] = {}
        self.watchers: Dict[str, WatcherState] = {}
        self.orders: Dict[str, OrderState] = {}
        self.latency: LatencyState = LatencyState()
        self.system_health: SystemHealth = SystemHealth()
        self._lock = Lock()
    
    def update_event(
        self,
        event_id: str,
        event_type: str,
        status: str,
        confidence: float,
        watcher_status: str = "active",
        markets: Optional[list] = None,
        sources: Optional[Dict[str, str]] = None
    ):
        """Actualiza estado de un evento."""
        with self._lock:
            if event_id not in self.events:
                self.events[event_id] = EventState(
                    event_id=event_id,
                    event_type=event_type,
                    status=status,
                    confidence=confidence,
                    watcher_status=watcher_status
                )
            
            event = self.events[event_id]
            event.status = status
            event.confidence = confidence
            event.watcher_status = watcher_status
            event.last_update = datetime.utcnow()
            
            if markets is not None:
                event.markets = markets
            if sources is not None:
                event.sources = sources
    
    def update_market(
        self,
        market_id: str,
        event_id: Optional[str] = None,
        state: Optional[str] = None,
        best_ask: Optional[float] = None,
        best_bid: Optional[float] = None,
        exposure: Optional[float] = None,
        last_intent: Optional[Dict[str, Any]] = None
    ):
        """Actualiza estado de un mercado."""
        with self._lock:
            if market_id not in self.markets:
                self.markets[market_id] = MarketState(market_id=market_id)
            
            market = self.markets[market_id]
            if event_id is not None:
                market.event_id = event_id
            if state is not None:
                market.state = state
            if best_ask is not None:
                market.best_ask = best_ask
            if best_bid is not None:
                market.best_bid = best_bid
            if exposure is not None:
                market.exposure = exposure
            if last_intent is not None:
                market.last_intent = last_intent
            market.last_update = datetime.utcnow()
    
    def update_watcher(
        self,
        event_id: str,
        event_name: Optional[str] = None,
        status: Optional[str] = None,
        checks_per_minute: Optional[int] = None,
        last_check: Optional[datetime] = None,
        sources: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        """Actualiza estado de un watcher."""
        with self._lock:
            if event_id not in self.watchers:
                self.watchers[event_id] = WatcherState(event_id=event_id)
            
            watcher = self.watchers[event_id]
            if event_name is not None:
                watcher.event_name = event_name
            if status is not None:
                watcher.status = status
            if checks_per_minute is not None:
                watcher.checks_per_minute = checks_per_minute
            if last_check is not None:
                watcher.last_check = last_check
            if sources is not None:
                watcher.sources = sources
            watcher.last_update = datetime.utcnow()
    
    def update_order(
        self,
        order_id: str,
        market_id: str,
        status: str,
        fills: Optional[list] = None,
        avg_price: Optional[float] = None
    ):
        """Actualiza estado de una orden."""
        with self._lock:
            if order_id not in self.orders:
                self.orders[order_id] = OrderState(
                    order_id=order_id,
                    market_id=market_id,
                    status=status
                )
            
            order = self.orders[order_id]
            order.status = status
            if fills is not None:
                order.fills = fills
            if avg_price is not None:
                order.avg_price = avg_price
            order.timestamp = datetime.utcnow()
    
    def update_latency(self, mode: str, latency_ms: float):
        """Actualiza estado de latencia."""
        with self._lock:
            self.latency.mode = mode
            self.latency.latency_ms = latency_ms
            self.latency.last_update = datetime.utcnow()
    
    def update_system_health(
        self,
        runtime_mode: Optional[str] = None,
        exposure_total: Optional[float] = None,
        markets_active: Optional[int] = None,
        watchers_active: Optional[int] = None,
        last_fill: Optional[Dict[str, Any]] = None,
        last_error: Optional[str] = None,
        last_event_resolved: Optional[str] = None,
        circuit_breaker_status: Optional[str] = None,
        trading_status: Optional[str] = None
    ):
        """Actualiza salud del sistema."""
        with self._lock:
            if runtime_mode is not None:
                self.system_health.runtime_mode = runtime_mode
            if exposure_total is not None:
                self.system_health.exposure_total = exposure_total
            if markets_active is not None:
                self.system_health.markets_active = markets_active
            if watchers_active is not None:
                self.system_health.watchers_active = watchers_active
            if last_fill is not None:
                self.system_health.last_fill = last_fill
            if last_error is not None:
                self.system_health.last_error = last_error
            if last_event_resolved is not None:
                self.system_health.last_event_resolved = last_event_resolved
            if circuit_breaker_status is not None:
                self.system_health.circuit_breaker_status = circuit_breaker_status
            if trading_status is not None:
                self.system_health.trading_status = trading_status
            self.system_health.last_update = datetime.utcnow()
    
    def get_state(self) -> Dict[str, Any]:
        """Obtiene todo el estado actual."""
        with self._lock:
            return {
                "events": {
                    event_id: {
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "status": event.status,
                        "confidence": event.confidence,
                        "watcher_status": event.watcher_status,
                        "markets": event.markets,
                        "sources": event.sources,
                        "last_update": event.last_update.isoformat() if event.last_update else None
                    }
                    for event_id, event in self.events.items()
                },
                "markets": {
                    market_id: {
                        "market_id": market.market_id,
                        "event_id": market.event_id,
                        "state": market.state,
                        "best_ask": market.best_ask,
                        "best_bid": market.best_bid,
                        "exposure": market.exposure,
                        "last_intent": market.last_intent,
                        "last_update": market.last_update.isoformat() if market.last_update else None
                    }
                    for market_id, market in self.markets.items()
                },
                "watchers": {
                    event_id: {
                        "event_id": watcher.event_id,
                        "event_name": watcher.event_name,
                        "status": watcher.status,
                        "checks_per_minute": watcher.checks_per_minute,
                        "last_check": watcher.last_check.isoformat() if watcher.last_check else None,
                        "sources": watcher.sources,
                        "last_update": watcher.last_update.isoformat() if watcher.last_update else None
                    }
                    for event_id, watcher in self.watchers.items()
                },
                "orders": {
                    order_id: {
                        "order_id": order.order_id,
                        "market_id": order.market_id,
                        "status": order.status,
                        "fills": order.fills,
                        "avg_price": order.avg_price,
                        "timestamp": order.timestamp.isoformat() if order.timestamp else None
                    }
                    for order_id, order in self.orders.items()
                },
                "latency": {
                    "mode": self.latency.mode,
                    "latency_ms": self.latency.latency_ms,
                    "last_update": self.latency.last_update.isoformat() if self.latency.last_update else None
                },
                "system_health": {
                    "runtime_mode": self.system_health.runtime_mode,
                    "exposure_total": self.system_health.exposure_total,
                    "markets_active": self.system_health.markets_active,
                    "watchers_active": self.system_health.watchers_active,
                    "last_fill": self.system_health.last_fill,
                    "last_error": self.system_health.last_error,
                    "last_event_resolved": self.system_health.last_event_resolved,
                    "circuit_breaker_status": self.system_health.circuit_breaker_status,
                    "trading_status": self.system_health.trading_status,
                    "last_update": self.system_health.last_update.isoformat() if self.system_health.last_update else None
                }
            }

