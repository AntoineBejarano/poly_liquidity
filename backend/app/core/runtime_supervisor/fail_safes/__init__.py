"""
Fail-Safes - acciones automáticas de protección.
"""
from app.core.runtime_supervisor.fail_safes.trading_fail_safe import TradingFailSafe
from app.core.runtime_supervisor.fail_safes.checker_fail_safe import CheckerFailSafe

__all__ = [
    "TradingFailSafe",
    "CheckerFailSafe",
]

