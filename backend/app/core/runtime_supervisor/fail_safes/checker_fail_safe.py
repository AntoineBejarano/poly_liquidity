"""
Checker Fail-Safe - protección automática para checkers.
"""
from typing import Optional, List
from datetime import datetime


class CheckerFailSafe:
    """
    Fail-Safe para checkers.
    
    Acciones automáticas cuando los checkers fallan:
    - Desactivar checkers problemáticos
    - Notificar sobre checkers caídos
    """
    
    def __init__(self):
        """Inicializa el fail-safe."""
        self._disabled_checkers: List[str] = []
        self._last_triggered: Optional[datetime] = None
        self._triggered_count = 0
    
    async def trigger(self, checker_id: str, reason: str):
        """
        Activa el fail-safe para un checker.
        
        Args:
            checker_id: ID del checker
            reason: Razón de la desactivación
        """
        if checker_id not in self._disabled_checkers:
            self._disabled_checkers.append(checker_id)
            self._last_triggered = datetime.utcnow()
            self._triggered_count += 1
            print(f"CHECKER FAIL-SAFE TRIGGERED: Disabled checker {checker_id} - {reason}")
    
    async def recover(self, checker_id: str):
        """
        Recupera un checker.
        
        Args:
            checker_id: ID del checker a recuperar
        """
        if checker_id in self._disabled_checkers:
            self._disabled_checkers.remove(checker_id)
            print(f"CHECKER FAIL-SAFE RECOVERED: Enabled checker {checker_id}")
    
    def is_disabled(self, checker_id: str) -> bool:
        """
        Verifica si un checker está deshabilitado.
        
        Args:
            checker_id: ID del checker
        
        Returns:
            True si está deshabilitado
        """
        return checker_id in self._disabled_checkers
    
    def get_disabled_checkers(self) -> List[str]:
        """Obtiene lista de checkers deshabilitados."""
        return self._disabled_checkers.copy()
    
    def get_info(self) -> dict:
        """Obtiene información del fail-safe."""
        return {
            "disabled_checkers": self._disabled_checkers,
            "last_triggered": self._last_triggered.isoformat() if self._last_triggered else None,
            "triggered_count": self._triggered_count
        }

