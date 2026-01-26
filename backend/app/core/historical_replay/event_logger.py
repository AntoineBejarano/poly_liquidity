"""
Event Logger - Helper para registrar eventos en Event Store.

Según especificación en docs/services/historical_replay.md
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from app.core.historical_replay.event_store import EventStore

logger = logging.getLogger(__name__)

# Instancia global de EventStore (se inicializará en startup)
_event_store: Optional[EventStore] = None


def initialize_event_store(event_store: EventStore):
    """Inicializa el Event Store global."""
    global _event_store
    _event_store = event_store


async def log_event(
    event_type: str,
    component: str,
    trace_id: Optional[UUID] = None,
    **kwargs
) -> bool:
    """
    Registra un evento en el Event Store.
    
    Args:
        event_type: Tipo de evento (ej: "strategy_intent_created")
        component: Componente que genera el evento (ej: "strategy", "risk", "execution")
        trace_id: Trace ID para correlación (opcional)
        **kwargs: Datos adicionales del evento
        
    Returns:
        True si se registró correctamente, False en caso contrario
    """
    global _event_store
    
    if _event_store is None:
        # Si no está inicializado, solo loggear (no fallar)
        logger.debug(f"Event Store not initialized, skipping event: {event_type}")
        return False
    
    event = {
        "type": event_type,
        "timestamp": datetime.utcnow(),
        "component": component,
        **kwargs
    }
    
    if trace_id:
        event["trace_id"] = str(trace_id)
    
    try:
        return await _event_store.store_event(event)
    except Exception as e:
        logger.error(f"Error logging event: {e}")
        return False


# Helpers específicos por componente

async def log_watcher_event(
    event_id: str,
    state: str,
    confidence: float,
    trace_id: Optional[UUID] = None,
    **kwargs
) -> bool:
    """Registra evento del Watch Engine."""
    return await log_event(
        event_type="watcher_event_state",
        component="watch_engine",
        event_id=event_id,
        state=state,
        confidence=confidence,
        trace_id=trace_id,
        **kwargs
    )


async def log_strategy_intent(
    market_id: str,
    target_price: float,
    size: float,
    reason: str,
    trace_id: Optional[UUID] = None,
    **kwargs
) -> bool:
    """Registra intent creado por Strategy."""
    return await log_event(
        event_type="strategy_intent_created",
        component="strategy",
        market_id=market_id,
        target_price=target_price,
        size=size,
        reason=reason,
        trace_id=trace_id,
        **kwargs
    )


async def log_risk_decision(
    market_id: str,
    approved: bool,
    final_size: Optional[float] = None,
    price: Optional[float] = None,
    trace_id: Optional[UUID] = None,
    **kwargs
) -> bool:
    """Registra decisión del Risk Engine."""
    return await log_event(
        event_type="risk_decision",
        component="risk",
        market_id=market_id,
        approved=approved,
        final_size=final_size,
        price=price,
        trace_id=trace_id,
        **kwargs
    )


async def log_execution_event(
    event_type: str,
    order_id: Optional[str] = None,
    market_id: Optional[str] = None,
    trace_id: Optional[UUID] = None,
    **kwargs
) -> bool:
    """Registra evento del Execution Engine."""
    return await log_event(
        event_type=event_type,
        component="execution",
        order_id=order_id,
        market_id=market_id,
        trace_id=trace_id,
        **kwargs
    )


async def log_runtime_event(
    event_type: str,
    from_mode: Optional[str] = None,
    to_mode: Optional[str] = None,
    reason: Optional[str] = None,
    **kwargs
) -> bool:
    """Registra evento del Runtime Supervisor."""
    return await log_event(
        event_type=event_type,
        component="runtime",
        from_mode=from_mode,
        to_mode=to_mode,
        reason=reason,
        **kwargs
    )

