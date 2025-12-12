"""
Live watchers system for monitoring events in real-time.
Manages concurrent watchers that check Polymarket and sports APIs.
"""
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import logging
from app.services.polymarket_client import polymarket_client
from app.services.sports_client import sports_client

logger = logging.getLogger(__name__)


class WatcherStatus(str, Enum):
    """Watcher status enumeration."""
    PENDING = "pending"
    CHECKING = "checking"
    FINISHED = "finished"
    ERROR = "error"


class Watcher:
    """Represents a single event watcher."""
    
    def __init__(self, event_id: str, event_name: str, market_id: str):
        self.event_id = event_id
        self.event_name = event_name
        self.market_id = market_id
        self.status = WatcherStatus.PENDING
        self.last_polymarket_response: Optional[Dict[str, Any]] = None
        self.last_sports_response: Optional[Dict[str, Any]] = None
        self.estimated_remaining_seconds: Optional[int] = None
        self.last_update: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.created_at = datetime.utcnow()
        self._task: Optional[asyncio.Task] = None
        self._active = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert watcher to dictionary for API response."""
        time_since_update = None
        if self.last_update:
            delta = datetime.utcnow() - self.last_update
            time_since_update = int(delta.total_seconds())
        
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "market_id": self.market_id,
            "status": self.status.value,
            "last_polymarket_response": self.last_polymarket_response,
            "last_sports_response": self.last_sports_response,
            "estimated_remaining_seconds": self.estimated_remaining_seconds,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "time_since_update": time_since_update,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }
    
    async def stop(self):
        """Stop the watcher."""
        self._active = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _watch_loop(self):
        """Main watching loop for this watcher."""
        while self._active:
            try:
                self.status = WatcherStatus.CHECKING
                self.last_update = datetime.utcnow()
                
                # Fetch data from both APIs in parallel
                polymarket_task = asyncio.create_task(
                    polymarket_client.get_market(self.market_id)
                )
                sports_task = asyncio.create_task(
                    sports_client.get_event(self.event_id)
                )
                
                polymarket_data, sports_data = await asyncio.gather(
                    polymarket_task,
                    sports_task,
                    return_exceptions=True
                )
                
                # Handle Polymarket response
                if isinstance(polymarket_data, Exception):
                    logger.error(f"Polymarket error for {self.market_id}: {polymarket_data}")
                    self.last_polymarket_response = {"error": str(polymarket_data)}
                else:
                    self.last_polymarket_response = polymarket_data
                
                # Handle Sports API response
                if isinstance(sports_data, Exception):
                    logger.error(f"Sports API error for {self.event_id}: {sports_data}")
                    self.last_sports_response = {"error": str(sports_data)}
                else:
                    self.last_sports_response = sports_data
                    
                    # Extract time remaining if available
                    if sports_data:
                        self.estimated_remaining_seconds = await sports_client.get_event_time_remaining(
                            self.event_id
                        )
                
                # Check if event is finished
                if self.last_polymarket_response:
                    market_state = self.last_polymarket_response.get("state") or \
                                  self.last_polymarket_response.get("status")
                    if market_state in ["resolved", "closed", "finalized"]:
                        self.status = WatcherStatus.FINISHED
                        self._active = False
                        break
                
                if self.last_sports_response:
                    event_status = self.last_sports_response.get("status") or \
                                  self.last_sports_response.get("state")
                    if event_status in ["finished", "completed", "final"]:
                        self.status = WatcherStatus.FINISHED
                        self._active = False
                        break
                
                self.status = WatcherStatus.PENDING
                
                # Wait 2 seconds before next check
                await asyncio.sleep(2.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in watcher loop for {self.event_id}: {e}")
                self.status = WatcherStatus.ERROR
                self.error_message = str(e)
                # Wait before retrying
                await asyncio.sleep(5.0)


class WatcherManager:
    """Manages all active watchers."""
    
    def __init__(self):
        self._watchers: Dict[str, Watcher] = {}
        self._lock = asyncio.Lock()
    
    async def start_watcher(
        self, 
        event_id: str, 
        event_name: str, 
        market_id: str
    ) -> Watcher:
        """
        Start watching an event.
        
        Args:
            event_id: The sports event ID
            event_name: Human-readable event name
            market_id: The Polymarket market ID
            
        Returns:
            The created Watcher instance
        """
        async with self._lock:
            # If watcher already exists, return it
            if event_id in self._watchers:
                return self._watchers[event_id]
            
            watcher = Watcher(event_id, event_name, market_id)
            self._watchers[event_id] = watcher
            
            # Start the watching task
            watcher._task = asyncio.create_task(watcher._watch_loop())
            
            logger.info(f"Started watcher for event {event_id} ({event_name})")
            return watcher
    
    async def stop_watcher(self, event_id: str) -> bool:
        """
        Stop watching an event.
        
        Args:
            event_id: The event ID to stop watching
            
        Returns:
            True if watcher was found and stopped, False otherwise
        """
        async with self._lock:
            if event_id not in self._watchers:
                return False
            
            watcher = self._watchers[event_id]
            await watcher.stop()
            del self._watchers[event_id]
            
            logger.info(f"Stopped watcher for event {event_id}")
            return True
    
    async def get_watchers(self) -> List[Dict[str, Any]]:
        """
        Get all active watchers.
        
        Returns:
            List of watcher dictionaries
        """
        async with self._lock:
            # Clean up finished watchers older than 1 hour
            now = datetime.utcnow()
            to_remove = []
            for event_id, watcher in self._watchers.items():
                if watcher.status == WatcherStatus.FINISHED:
                    if watcher.last_update:
                        age = now - watcher.last_update
                        if age > timedelta(hours=1):
                            to_remove.append(event_id)
            
            for event_id in to_remove:
                del self._watchers[event_id]
            
            return [watcher.to_dict() for watcher in self._watchers.values()]
    
    async def get_watcher(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific watcher.
        
        Args:
            event_id: The event ID
            
        Returns:
            Watcher dictionary or None if not found
        """
        async with self._lock:
            if event_id not in self._watchers:
                return None
            return self._watchers[event_id].to_dict()
    
    async def stop_all(self):
        """Stop all watchers (for shutdown)."""
        async with self._lock:
            tasks = [watcher.stop() for watcher in self._watchers.values()]
            await asyncio.gather(*tasks, return_exceptions=True)
            self._watchers.clear()


# Global instance
watcher_manager = WatcherManager()

