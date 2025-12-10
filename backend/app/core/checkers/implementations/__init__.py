"""
Checker implementations.
This module auto-registers all checker implementations.
"""
from app.core.checkers.registry import checker_registry

# Import all checker implementations
from .mock_checker import MockChecker
from .sports_checker import SportsChecker
from .crypto_checker import CryptoChecker

# Auto-register checkers
checker_registry.register("mock_checker", MockChecker)
checker_registry.register("sports_checker", SportsChecker)
checker_registry.register("crypto_checker", CryptoChecker)

__all__ = [
    "MockChecker",
    "SportsChecker",
    "CryptoChecker",
]
