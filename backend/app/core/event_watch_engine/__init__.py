"""
Event Watch Engine - Motor de monitoreo de eventos reales.

Refactorizado según especificación en docs/services/event_watch_engine.md
"""
from app.core.event_watch_engine.coordinator import EventWatchCoordinator
from app.core.event_watch_engine.models import EventState, WatcherState, WatcherStatus

__all__ = [
    "EventWatchCoordinator",
    "EventState",
    "WatcherState",
    "WatcherStatus",
]

