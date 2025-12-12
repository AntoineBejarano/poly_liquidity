"""
Live Control Event Bus - Event bus para eventos de módulos.

Según especificación en docs/services/livecontrol.md
"""
import logging
import asyncio
from typing import Dict, List, Callable, Any, Optional, TYPE_CHECKING
from datetime import datetime
from app.core.live_control.state_store import LiveControlStore

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class LiveControlEventBus:
    """
    Event bus para Live Control.
    
    Permite que los módulos emitan eventos que se propagan al Live Control
    y a los suscriptores SSE.
    """
    
    def __init__(self, store: LiveControlStore):
        """
        Inicializa el Event Bus.
        
        Args:
            store: Instancia de LiveControlStore
        """
        self.store = store
        self.subscribers: List[Callable[[str, Dict[str, Any]], None]] = []
        self._lock = asyncio.Lock()
    
    def emit(self, event_type: str, data: Dict[str, Any]):
        """
        Emite un evento.
        
        Args:
            event_type: Tipo de evento (ej: "event_update", "market_update", "strategy_intent")
            data: Datos del evento
        """
        try:
            # 1. Actualizar store según tipo de evento
            self._update_store(event_type, data)
            
            # 2. Notificar suscriptores (SSE streams)
            for subscriber in self.subscribers:
                try:
                    subscriber(event_type, data)
                except Exception as e:
                    logger.error(f"Error notifying subscriber: {e}")
        except Exception as e:
            logger.error(f"Error emitting event {event_type}: {e}")
    
    def subscribe(self, callback: Callable[[str, Dict[str, Any]], None]):
        """
        Suscribe un callback a eventos.
        
        Args:
            callback: Función que recibe (event_type, data)
        """
        self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[str, Dict[str, Any]], None]):
        """
        Desuscribe un callback.
        
        Args:
            callback: Callback a desuscribir
        """
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def _update_store(self, event_type: str, data: Dict[str, Any]):
        """Actualiza el store según el tipo de evento."""
        if event_type == "event_update":
            # Actualizar estado de evento
            self.store.update_event(
                event_id=data.get("event_id", ""),
                event_type=data.get("event_type", "unknown"),
                status=data.get("status", "UNKNOWN"),
                confidence=data.get("confidence", 0.0),
                watcher_status=data.get("watcher_status", "active"),
                markets=data.get("markets"),
                sources=data.get("sources")
            )
        
        elif event_type == "market_update":
            # Actualizar estado de mercado
            self.store.update_market(
                market_id=data.get("market_id", ""),
                event_id=data.get("event_id"),
                state=data.get("state"),
                best_ask=data.get("best_ask"),
                best_bid=data.get("best_bid"),
                exposure=data.get("exposure")
            )
        
        elif event_type == "strategy_intent":
            # Actualizar último intent del mercado
            market_id = data.get("market_id", "")
            intent = {
                "target_price": data.get("target_price", 0.0),
                "size": data.get("size", 0.0),
                "reason": data.get("reason", ""),
                "timestamp": data.get("timestamp", datetime.utcnow().isoformat())
            }
            self.store.update_market(
                market_id=market_id,
                last_intent=intent
            )
        
        elif event_type == "risk_decision":
            # Actualizar exposición del mercado si fue aprobado
            if data.get("approved"):
                market_id = data.get("market_id", "")
                final_size = data.get("final_size", 0.0)
                price = data.get("price", 0.0)
                exposure = final_size * price
                self.store.update_market(
                    market_id=market_id,
                    exposure=exposure
                )
        
        elif event_type == "execution_update":
            # Actualizar estado de orden
            order_id = data.get("order_id", "")
            market_id = data.get("market_id", "")
            status = data.get("status", "submitted")
            fills = data.get("fills", [])
            avg_price = data.get("avg_price", 0.0)
            
            self.store.update_order(
                order_id=order_id,
                market_id=market_id,
                status=status,
                fills=fills,
                avg_price=avg_price
            )
            
            # Actualizar último fill en system health
            if status == "filled" and fills:
                self.store.update_system_health(
                    last_fill={
                        "order_id": order_id,
                        "market_id": market_id,
                        "size": fills[-1].get("size", 0.0),
                        "price": fills[-1].get("price", 0.0)
                    }
                )
        
        elif event_type == "latency_update":
            # Actualizar latencia
            self.store.update_latency(
                mode=data.get("mode", "GREEN"),
                latency_ms=data.get("latency_ms", 0.0)
            )
        
        elif event_type == "watcher_update":
            # Actualizar estado de watcher
            self.store.update_watcher(
                event_id=data.get("event_id", ""),
                event_name=data.get("event_name"),
                status=data.get("status"),
                checks_per_minute=data.get("checks_per_minute"),
                last_check=data.get("last_check"),
                sources=data.get("sources")
            )
        
        elif event_type == "system_health_update":
            # Actualizar salud del sistema
            self.store.update_system_health(
                runtime_mode=data.get("runtime_mode"),
                exposure_total=data.get("exposure_total"),
                markets_active=data.get("markets_active"),
                watchers_active=data.get("watchers_active"),
                last_error=data.get("last_error"),
                last_event_resolved=data.get("last_event_resolved"),
                circuit_breaker_status=data.get("circuit_breaker_status"),
                trading_status=data.get("trading_status")
            )


# Instancia global del Event Bus (se inicializará en startup)
_event_bus: Optional[LiveControlEventBus] = None


def get_event_bus() -> LiveControlEventBus:
    """Obtiene la instancia global del Event Bus."""
    global _event_bus
    if _event_bus is None:
        store = LiveControlStore()
        _event_bus = LiveControlEventBus(store)
    return _event_bus


def initialize_event_bus(store: LiveControlStore):
    """Inicializa el Event Bus global."""
    global _event_bus
    _event_bus = LiveControlEventBus(store)


def emit_event(event_type: str, data: Dict[str, Any]):
    """
    Helper para emitir eventos al Event Bus.
    
    Args:
        event_type: Tipo de evento
        data: Datos del evento
    """
    bus = get_event_bus()
    bus.emit(event_type, data)

