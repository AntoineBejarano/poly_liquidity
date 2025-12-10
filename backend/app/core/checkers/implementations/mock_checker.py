"""
Mock checker for testing.
"""
from app.core.checkers.base import BaseChecker, CheckerResult
from typing import Optional, Dict
from datetime import datetime


class MockChecker(BaseChecker):
    """
    Mock checker for testing purposes.
    
    This checker always returns LIVE state with medium confidence.
    Useful for testing the checker system without external API dependencies.
    """
    
    async def check(
        self,
        external_event_id: str,
        credentials: Optional[Dict[str, str]] = None
    ) -> CheckerResult:
        """
        Mock check - always returns LIVE for testing.
        
        Args:
            external_event_id: Event identifier (ignored in mock)
            credentials: Optional credentials (ignored in mock)
        
        Returns:
            CheckerResult with LIVE state and 0.5 confidence
        """
        return CheckerResult(
            state="LIVE",
            confidence=0.5,
            finished_at=None,
            raw_payload={
                "mock": True,
                "external_event_id": external_event_id,
                "note": "This is a mock checker for testing"
            },
            source="mock_checker"
        )

