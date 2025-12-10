"""
Checker registry - maps implementation_key to checker class.
"""
from typing import Dict, Type
from app.core.checkers.base import BaseChecker


class CheckerRegistry:
    """Registry for checker implementations."""
    
    def __init__(self):
        self._checkers: Dict[str, Type[BaseChecker]] = {}
    
    def register(self, implementation_key: str, checker_class: Type[BaseChecker]):
        """Register a checker implementation."""
        self._checkers[implementation_key] = checker_class
    
    def get(self, implementation_key: str) -> Type[BaseChecker]:
        """Get a checker class by implementation_key."""
        if implementation_key not in self._checkers:
            raise ValueError(f"Checker implementation '{implementation_key}' not found")
        return self._checkers[implementation_key]
    
    def list_all(self) -> Dict[str, Type[BaseChecker]]:
        """List all registered checkers."""
        return self._checkers.copy()


# Global registry instance
checker_registry = CheckerRegistry()

