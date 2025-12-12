"""
Live Control API endpoints for real-time event watchers.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import asyncio
from app.api.auth import get_current_user, User
from app.core.live_watchers import watcher_manager
from app.database import SessionLocal
from app.models.user_sync import UserSync
from app.models.user import UserMetadata
from jose import jwt, JWTError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/live", tags=["live"])


async def get_user_from_token(token: str) -> User:
    """Validate token and return User (for SSE compatibility)."""
    try:
        decoded = jwt.decode(
            token,
            options={"verify_signature": False}  # Same as in auth.py
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


@router.get("/watchers/stream")
async def stream_watchers(
    token: Optional[str] = Query(None, description="Auth token (required for SSE)"),
):
    """
    Server-Sent Events (SSE) stream for real-time watcher updates.
    
    The frontend can connect to this endpoint to receive continuous
    updates about all watchers every 2 seconds.
    
    Note: Requires token as query parameter for SSE compatibility
    (EventSource doesn't support custom headers).
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
    async def event_generator():
        """Generate SSE events."""
        try:
            while True:
                watchers = await watcher_manager.get_watchers()
                data = {
                    "watchers": watchers,
                    "timestamp": asyncio.get_event_loop().time(),
                }
                
                # Format as SSE
                yield f"data: {json.dumps(data)}\n\n"
                
                # Wait 2 seconds before next update
                await asyncio.sleep(2.0)
                
        except asyncio.CancelledError:
            logger.info("SSE stream cancelled")
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            error_data = {"error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

