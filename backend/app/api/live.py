"""
Live Control API endpoints for real-time event watchers.

Según especificación en docs/services/livecontrol.md
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import asyncio
from datetime import datetime
from app.api.auth import get_current_user, User
from app.core.live_watchers import watcher_manager
from app.core.live_control import LiveControlStore, LiveControlEventBus
from app.core.live_control.event_bus import get_event_bus
from app.database import SessionLocal
from app.models.user_sync import UserSync
from app.models.user import UserMetadata
from jose import jwt, JWTError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/live", tags=["live"])

# Instancia global del Event Bus
event_bus = get_event_bus()


async def get_user_from_token(token: str) -> User:
    """Validate token and return User (for SSE compatibility)."""
    try:
        decoded = jwt.decode(
            token,
            key="",  # Empty key since we're not verifying signature
            options={
                "verify_signature": False,  # Same as in auth.py
                "verify_aud": False,  # Don't verify audience
                "verify_exp": False,  # Don't verify expiration (for now)
            }
        )
        user_id = decoded.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims"
            )
        
        db = SessionLocal()
        try:
            user_sync = db.query(UserSync).filter(
                UserSync.id == user_id,
                UserSync.deleted_at.is_(None)
            ).first()
            
            if not user_sync:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            metadata = db.query(UserMetadata).filter(
                UserMetadata.user_id == user_id
            ).first()
            
            if not metadata:
                metadata = UserMetadata(user_id=user_id, role="viewer")
                db.add(metadata)
                db.commit()
                db.refresh(metadata)
            
            return User(user_sync, metadata)
        finally:
            db.close()
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


class StartWatcherRequest(BaseModel):
    """Request to start watching an event."""
    event_id: str
    event_name: str
    market_id: str


class WatcherResponse(BaseModel):
    """Watcher response model."""
    event_id: str
    event_name: str
    market_id: str
    status: str
    last_polymarket_response: Optional[dict] = None
    last_sports_response: Optional[dict] = None
    estimated_remaining_seconds: Optional[int] = None
    last_update: Optional[str] = None
    time_since_update: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str


@router.post("/watchers/start")
async def start_watcher(
    request: StartWatcherRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Start watching an event.
    
    Creates a new watcher that will continuously check:
    - Polymarket API for market status
    - Sports API for event status
    """
    try:
        watcher = await watcher_manager.start_watcher(
            event_id=request.event_id,
            event_name=request.event_name,
            market_id=request.market_id,
        )
        return watcher.to_dict()
    except Exception as e:
        logger.error(f"Error starting watcher: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start watcher: {str(e)}"
        )


@router.post("/watchers/{event_id}/stop")
async def stop_watcher(
    event_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Stop watching an event.
    """
    success = await watcher_manager.stop_watcher(event_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watcher for event {event_id} not found"
        )
    return {"status": "stopped", "event_id": event_id}


@router.get("/watchers")
async def get_watchers(
    current_user: User = Depends(get_current_user),
):
    """
    Get all active watchers.
    """
    watchers = await watcher_manager.get_watchers()
    return {"watchers": watchers}


@router.get("/watchers/{event_id}")
async def get_watcher(
    event_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific watcher by event ID.
    """
    watcher = await watcher_manager.get_watcher(event_id)
    if not watcher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watcher for event {event_id} not found"
        )
    return watcher


@router.get("/events")
async def get_events(
    current_user: User = Depends(get_current_user),
):
    """
    Obtener todos los eventos actualmente monitoreados.
    
    Según especificación en docs/services/livecontrol.md
    """
    store = event_bus.store
    events = []
    
    for event_id, event_state in store.events.items():
        events.append({
            "event_id": event_state.event_id,
            "event_type": event_state.event_type,
            "status": event_state.status,
            "confidence": event_state.confidence,
            "watcher_status": event_state.watcher_status,
            "markets": event_state.markets,
            "sources": event_state.sources,
            "last_update": event_state.last_update.isoformat() if event_state.last_update else None
        })
    
    return events


@router.get("/markets")
async def get_markets(
    current_user: User = Depends(get_current_user),
):
    """
    Obtener todos los mercados activos.
    
    Según especificación en docs/services/livecontrol.md
    """
    store = event_bus.store
    markets = []
    
    for market_id, market_state in store.markets.items():
        markets.append({
            "market_id": market_state.market_id,
            "event_id": market_state.event_id,
            "state": market_state.state,
            "best_ask": market_state.best_ask,
            "best_bid": market_state.best_bid,
            "exposure": market_state.exposure,
            "last_intent": market_state.last_intent,
            "last_update": market_state.last_update.isoformat() if market_state.last_update else None
        })
    
    return markets


@router.get("/execution")
async def get_execution(
    current_user: User = Depends(get_current_user),
):
    """
    Obtener flujo reciente de órdenes.
    
    Según especificación en docs/services/livecontrol.md
    """
    store = event_bus.store
    orders = []
    
    for order_id, order_state in store.orders.items():
        orders.append({
            "order_id": order_state.order_id,
            "market_id": order_state.market_id,
            "state": order_state.status,
            "fills": order_state.fills,
            "avg_price": order_state.avg_price,
            "timestamp": order_state.timestamp.isoformat() if order_state.timestamp else None
        })
    
    # Ordenar por timestamp descendente (más recientes primero)
    orders.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    
    return orders


@router.get("/watchers/stream")
async def stream_watchers(
    token: Optional[str] = Query(None, description="Auth token (required for SSE)"),
):
    """
    Server-Sent Events (SSE) stream for real-time updates.
    
    Según especificación en docs/services/livecontrol.md
    
    Envía actualizaciones de:
    - Eventos
    - Mercados
    - Watchers
    - Decisiones de strategy/risk/execution
    - Latencia
    - Salud del sistema
    """
    # Authenticate using token from query parameter
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required (use ?token=... query parameter)"
        )
    
    # Validate token and get user
    try:
        user = await get_user_from_token(token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error authenticating user for SSE: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
    
    # Queue para mensajes pendientes
    message_queue: List[Dict[str, Any]] = []
    
    # Callback para recibir eventos del Event Bus
    def on_event(event_type: str, data: Dict[str, Any]):
        """Callback para eventos del Event Bus."""
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        message_queue.append(message)
    
    # Suscribirse al Event Bus
    event_bus.subscribe(on_event)
    
    async def event_generator():
        """Generate SSE events."""
        try:
            # Enviar estado inicial
            initial_state = event_bus.store.get_state()
            yield f"data: {json.dumps({'type': 'initial_state', 'data': initial_state})}\n\n"
            
            while True:
                # Enviar mensajes pendientes (con throttling)
                if message_queue:
                    # Enviar batch de mensajes (máximo 10 por iteración)
                    batch = message_queue[:10]
                    message_queue[:10] = []
                    
                    for message in batch:
                        yield f"data: {json.dumps(message)}\n\n"
                
                # Enviar snapshot periódico del estado completo (cada 10 segundos)
                # Esto asegura que el cliente tenga el estado completo incluso si se pierden mensajes
                state = event_bus.store.get_state()
                yield f"data: {json.dumps({'type': 'state_snapshot', 'data': state})}\n\n"
                
                # Wait 2 seconds before next update
                await asyncio.sleep(2.0)
                
        except asyncio.CancelledError:
            logger.info("SSE stream cancelled")
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            error_data = {"type": "error", "data": {"error": str(e)}}
            yield f"data: {json.dumps(error_data)}\n\n"
        finally:
            # Desuscribirse del Event Bus
            event_bus.unsubscribe(on_event)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

