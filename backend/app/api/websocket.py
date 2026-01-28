"""
WebSocket endpoint for real-time events.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import List, Dict, Set
from uuid import UUID
from datetime import datetime, timezone
import json
import logging
from app.core.state import state
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.strategy import Strategy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


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


class StrategyConnectionManager:
    """Manages WebSocket connections per strategy."""
    
    def __init__(self):
        # Dict[strategy_id, Set[WebSocket]]
        self.strategy_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, strategy_id: UUID):
        """Connect a WebSocket to a strategy."""
        await websocket.accept()
        strategy_key = str(strategy_id)
        
        if strategy_key not in self.strategy_connections:
            self.strategy_connections[strategy_key] = set()
        
        self.strategy_connections[strategy_key].add(websocket)
        logger.info(f"WebSocket connected to strategy {strategy_id} (total: {len(self.strategy_connections[strategy_key])})")
    
    def disconnect(self, websocket: WebSocket, strategy_id: UUID):
        """Disconnect a WebSocket from a strategy."""
        strategy_key = str(strategy_id)
        if strategy_key in self.strategy_connections:
            self.strategy_connections[strategy_key].discard(websocket)
            if not self.strategy_connections[strategy_key]:
                del self.strategy_connections[strategy_key]
            logger.info(f"WebSocket disconnected from strategy {strategy_id}")
    
    async def broadcast_to_strategy(self, strategy_id: UUID, message: dict):
        """Broadcast message to all connections for a specific strategy."""
        strategy_key = str(strategy_id)
        if strategy_key not in self.strategy_connections:
            return
        
        disconnected = []
        for connection in self.strategy_connections[strategy_key]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.strategy_connections[strategy_key].discard(conn)
        
        # Clean up if no connections left
        if not self.strategy_connections[strategy_key]:
            del self.strategy_connections[strategy_key]


# Global connection managers
manager = ConnectionManager()
strategy_manager = StrategyConnectionManager()


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


@router.websocket("/strategies/{strategy_id}")
async def websocket_strategy_endpoint(websocket: WebSocket, strategy_id: UUID):
    """
    WebSocket endpoint para updates en tiempo real de una estrategia específica.
    
    Eventos enviados:
    - plan_created: Nuevo plan creado
    - plan_executing: Plan en ejecución
    - plan_filled: Plan completado
    - plan_failed: Plan falló
    - precheck_failed: Precheck falló
    - orderbook_update: Update de orderbook
    - metrics_update: Actualización de métricas
    """
    # Verificar que la estrategia existe
    db = SessionLocal()
    try:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            await websocket.close(code=1008, reason="Strategy not found")
            return
    finally:
        db.close()
    
    # Conectar al manager de estrategias
    await strategy_manager.connect(websocket, strategy_id)
    
    try:
        # Enviar mensaje de bienvenida
        await websocket.send_json({
            "type": "connected",
            "strategy_id": str(strategy_id),
            "strategy_name": strategy.name,
        })
        
        # Mantener conexión viva y escuchar mensajes del cliente
        while True:
            try:
                # Esperar mensajes del cliente (ping/pong o comandos)
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    # Si no es JSON, tratar como texto plano
                    if data == "ping":
                        await websocket.send_json({"type": "pong"})
            except Exception as e:
                logger.warning(f"Error receiving message from strategy {strategy_id} WebSocket: {e}")
                break
                
    except WebSocketDisconnect:
        strategy_manager.disconnect(websocket, strategy_id)
    except Exception as e:
        logger.error(f"Error in strategy {strategy_id} WebSocket: {e}", exc_info=True)
        strategy_manager.disconnect(websocket, strategy_id)


async def broadcast_strategy_event(strategy_id: UUID, event_type: str, payload: dict):
    """
    Broadcast un evento a todos los WebSockets conectados a una estrategia.
    
    Args:
        strategy_id: ID de la estrategia
        event_type: Tipo de evento (plan_created, plan_executing, etc.)
        payload: Datos del evento
    """
    await strategy_manager.broadcast_to_strategy(strategy_id, {
        "type": event_type,
        "strategy_id": str(strategy_id),
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

