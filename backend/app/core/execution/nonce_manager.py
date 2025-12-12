"""
Nonce Manager - Gestor de nonces para órdenes.

Según especificación en docs/services/execution.md
"""
import logging
from typing import Optional
from app.core.execution.models import ExecutionConfig

logger = logging.getLogger(__name__)


class NonceManager:
    """
    Gestor de nonces para órdenes.
    
    Evita replay attacks y mantiene coherencia.
    """
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        """Inicializa el Nonce Manager."""
        self._config = config
        self._current_nonce: Optional[int] = None
        self._last_sync_time: Optional[float] = None
    
    def get_next_nonce(self) -> int:
        """
        Obtiene siguiente nonce.
        
        Returns:
            Siguiente nonce a usar.
        """
        # Si no tenemos nonce actual, inicializar desde 0
        if self._current_nonce is None:
            self._current_nonce = 0
        
        # Incrementar y retornar
        self._current_nonce += 1
        return self._current_nonce
    
    def sync_nonce(self, external_nonce: Optional[int] = None):
        """
        Sincroniza nonce desde blockchain o API externa.
        
        Args:
            external_nonce: Nonce actual desde blockchain/API (opcional)
        """
        if external_nonce is not None:
            # Usar nonce externo si se proporciona
            self._current_nonce = external_nonce
            logger.info(f"Nonce sincronizado desde externo: {external_nonce}")
        else:
            # TODO: Consultar nonce actual desde Polymarket API o blockchain
            # Por ahora, mantener el nonce actual
            logger.warning("Nonce sync sin external_nonce - manteniendo nonce actual")
    
    def get_current_nonce(self) -> Optional[int]:
        """Obtiene nonce actual sin incrementar."""
        return self._current_nonce
    
    def reset(self):
        """Resetea el nonce manager (útil para testing)."""
        self._current_nonce = None
        self._last_sync_time = None

