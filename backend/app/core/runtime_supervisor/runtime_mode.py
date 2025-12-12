"""
Runtime Mode - modos de operación del sistema.
"""
from enum import Enum


class RuntimeMode(str, Enum):
    """Modo de operación del sistema."""
    GREEN = "GREEN"    # Operar normal
    YELLOW = "YELLOW"  # Operar conservador
    RED = "RED"        # Pausar trading

