"""
WebSocket endpoint for real-time events.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json
from app.core.state import state

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time events."""
    await manager.connect(websocket)
    try:
        while True:
            # Wait for client messages (ping/pong)
            data = await websocket.receive_text()
            # Echo back or handle client messages
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Function to broadcast events (called from other modules)
async def broadcast_event(event_type: str, payload: dict):
    """Broadcast an event to all connected WebSocket clients."""
    await manager.broadcast({
        "type": event_type,
        "payload": payload,
    })

