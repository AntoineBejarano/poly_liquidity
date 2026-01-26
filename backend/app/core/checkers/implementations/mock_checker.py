"""
Mock checker for testing.

Refactorizado según especificación en docs/services/checker_system.md
"""
from app.core.checkers.base import BaseChecker, CheckerResult
from typing import Optional, Dict, List
from datetime import datetime
import time


class MockChecker(BaseChecker):
    """
    Mock checker for testing purposes.
    
    Este checker siempre retorna LIVE con confianza media.
    Útil para testing del sistema de checkers sin dependencias de APIs externas.
    """
    
    # Propiedades de configuración (atributos de clase)
    name = "mock_checker"
    event_types = ["sports", "politics", "crypto", "finance", "weather"]  # Soporta todos
    weight = 0.5  # Peso bajo para testing
    timeout_ms = 1000  # 1 segundo (rápido para tests)
    max_retries = 0  # Sin retries en mock
    
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
        start_time = time.time()
        timestamp = datetime.utcnow()
        latency_ms = (time.time() - start_time) * 1000
        
        return CheckerResult(
            state="LIVE",
            confidence=0.5,
            finished_at=None,
            raw_payload={
                "mock": True,
                "external_event_id": external_event_id,
                "note": "This is a mock checker for testing"
            },
            source=self.name,
            latency_ms=latency_ms,
            error=None,
            timestamp=timestamp
        )

