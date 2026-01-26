"""
Checker registry - maps implementation_key to checker class.

Refactorizado según especificación en docs/services/checker_system.md
"""
from typing import Dict, Type, List
from app.core.checkers.base import BaseChecker


class CheckerRegistry:
    """
    Registro global de checkers.
    
    Según especificación en docs/services/checker_system.md
    """
    
    def __init__(self):
        self._checkers: Dict[str, Type[BaseChecker]] = {}
    
    def register(self, implementation_key: str, checker_class: Type[BaseChecker]):
        """
        Registra un checker.
        
        Args:
            implementation_key: Clave única del checker (ej: "espn_nba_scoreboard_v1")
            checker_class: Clase del checker que extiende BaseChecker
        """
        self._checkers[implementation_key] = checker_class
    
    def get(self, implementation_key: str) -> Type[BaseChecker]:
        """
        Obtiene un checker por implementation_key.
        
        Args:
            implementation_key: Clave del checker
        
        Returns:
            Clase del checker
        
        Raises:
            ValueError: Si el checker no está registrado
        """
        if implementation_key not in self._checkers:
            raise ValueError(f"Checker implementation '{implementation_key}' not found")
        return self._checkers[implementation_key]
    
    def list_all(self) -> Dict[str, Type[BaseChecker]]:
        """Lista todos los checkers registrados."""
        return self._checkers.copy()
    
    def list_by_event_type(self, event_type: str) -> List[Type[BaseChecker]]:
        """
        Lista checkers para un tipo de evento.
        
        Args:
            event_type: Tipo de evento (ej: "sports", "politics", "crypto")
        
        Returns:
            Lista de clases de checkers que soportan ese tipo de evento
        """
        checkers = []
        for checker_class in self._checkers.values():
            # Verificar si el checker soporta este tipo de evento
            # Los checkers deben definir event_types como atributo de clase
            event_types = getattr(checker_class, 'event_types', [])
            if event_type in event_types:
                checkers.append(checker_class)
        return checkers


# Global registry instance
checker_registry = CheckerRegistry()

