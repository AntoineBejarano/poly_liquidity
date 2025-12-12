"""
Crypto checker - checks crypto market event finalization.

Refactorizado según especificación en docs/services/checker_system.md
"""
import httpx
from app.core.checkers.base import BaseChecker, CheckerResult
from typing import Optional, Dict, List
from datetime import datetime
import time


class CryptoChecker(BaseChecker):
    """
    Crypto checker implementation.
    
    Verifica eventos relacionados con blockchain (forks, halvings, price targets, etc.).
    
    Expected external_event_id format: "crypto:chain:event_id" (ej: "crypto:ethereum:18449200")
    Expected credentials: {"api_key": "..."}
    """
    
    # Propiedades de configuración (atributos de clase)
    name = "crypto_checker"
    event_types = ["crypto"]
    weight = 1.0
    timeout_ms = 5000  # 5 segundos
    max_retries = 2
    
    async def check(
        self,
        external_event_id: str,
        credentials: Optional[Dict[str, str]] = None
    ) -> CheckerResult:
        """
        Check if crypto event is finished.
        
        Args:
            external_event_id: Event identifier (e.g., "crypto:BTC:50000")
            credentials: Dict with "api_key"
        
        Returns:
            CheckerResult with state and confidence
        """
        start_time = time.time()
        timestamp = datetime.utcnow()
        
        if not credentials or "api_key" not in credentials:
            latency_ms = (time.time() - start_time) * 1000
            return CheckerResult(
                state="UNKNOWN",
                confidence=0.0,
                finished_at=None,
                raw_payload={"error": "No credentials provided"},
                source=self.name,
                latency_ms=latency_ms,
                error="authentication_error",
                timestamp=timestamp
            )
        
        api_key = credentials.get("api_key")
        
        try:
            # Parse external_event_id
            # Expected format: "crypto:chain:block_height" (ej: "crypto:ethereum:18449200")
            parts = external_event_id.split(":")
            if len(parts) >= 3:
                event_type, chain, block_height_str = parts[0], parts[1], parts[2]
                try:
                    target_block = int(block_height_str)
                except ValueError:
                    target_block = None
            else:
                chain = "unknown"
                target_block = None
            
            # Query crypto API o nodo RPC
            # TODO: Implementar integración real con nodo RPC o API de crypto
            async with httpx.AsyncClient(timeout=self.timeout_ms / 1000.0) as client:
                # Ejemplo de llamada real (comentado hasta tener API real):
                # Para forks/halvings, consultar nodo RPC:
                # current_block = await get_current_block_height(chain, api_key)
                # confirmations = await get_confirmations(chain, target_block, api_key)
                
                # Lógica según especificación:
                # if current_block >= target_block and confirmations >= 12:
                #     return CheckerResult(state="FINISHED", confidence=0.98, ...)
                # elif current_block >= target_block:
                #     return CheckerResult(state="FINISHED", confidence=0.7, ...)
                # else:
                #     return CheckerResult(state="LIVE", confidence=0.9, ...)
                
                # Por ahora, retornar LIVE como placeholder
                latency_ms = (time.time() - start_time) * 1000
                
                return CheckerResult(
                    state="LIVE",
                    confidence=0.5,
                    finished_at=None,
                    raw_payload={
                        "external_event_id": external_event_id,
                        "chain": chain,
                        "target_block": target_block,
                        "note": "Placeholder implementation - needs actual API/RPC integration"
                    },
                    source=self.name,
                    latency_ms=latency_ms,
                    error=None,
                    timestamp=timestamp
                )
        
        except httpx.TimeoutException:
            latency_ms = (time.time() - start_time) * 1000
            return CheckerResult(
                state="UNKNOWN",
                confidence=0.0,
                finished_at=None,
                raw_payload={"error": "Timeout querying crypto API"},
                source=self.name,
                latency_ms=latency_ms,
                error="timeout",
                timestamp=timestamp
            )
        except httpx.HTTPStatusError as e:
            latency_ms = (time.time() - start_time) * 1000
            error_type = "api_error" if e.response.status_code >= 500 else "authentication_error"
            return CheckerResult(
                state="UNKNOWN",
                confidence=0.0,
                finished_at=None,
                raw_payload={"error": str(e), "status_code": e.response.status_code},
                source=self.name,
                latency_ms=latency_ms,
                error=error_type,
                timestamp=timestamp
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return CheckerResult(
                state="UNKNOWN",
                confidence=0.0,
                finished_at=None,
                raw_payload={"error": str(e)},
                source=self.name,
                latency_ms=latency_ms,
                error="network_error",
                timestamp=timestamp
            )

