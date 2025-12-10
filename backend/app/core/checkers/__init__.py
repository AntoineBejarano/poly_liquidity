"""
Checker system for dynamic event detection.
"""
from app.core.checkers.base import BaseChecker, CheckerResult
from app.core.checkers.registry import checker_registry, CheckerRegistry

__all__ = [
    "BaseChecker",
    "CheckerResult",
    "checker_registry",
    "CheckerRegistry",
]
