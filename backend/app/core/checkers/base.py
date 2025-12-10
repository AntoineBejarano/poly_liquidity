"""
Base checker interface for dynamic event detection.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict
from pydantic import BaseModel
from datetime import datetime


class CheckerResult(BaseModel):
    """Result from a checker execution."""
    state: str  # "LIVE" or "FINISHED"
    confidence: float  # 0.0-1.0
    finished_at: Optional[datetime] = None
    raw_payload: Dict = {}  # for audit
    source: str


class BaseChecker(ABC):
    """Base class for all checkers."""
    
    @abstractmethod
    async def check(
        self,
        external_event_id: str,
        credentials: Optional[Dict[str, str]] = None
    ) -> CheckerResult:
        """
        Check if event is finished according to this external source.
        
        Args:
            external_event_id: External event identifier
            credentials: Dict with API keys, tokens, etc. provided by SecretService
        
        Returns:
            CheckerResult with state, confidence, etc.
        """
        pass

