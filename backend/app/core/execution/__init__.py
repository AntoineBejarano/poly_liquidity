"""
Execution Engine - Firma, envío, gestión y confirmación de órdenes.

Refactorizado según especificación en docs/services/execution.md y docs/services/signatures_trazability.md
"""
from app.core.execution.execution import Execution
from app.core.execution.models import (
    SignedOrder, ExecutionRecord, OrderStateHistory, FillRecord, ExecutionConfig
)
from app.core.execution.eip712_signer import EIP712Signer
from app.core.execution.nonce_manager import NonceManager
from app.core.execution.order_lifecycle import OrderLifecycleManager

__all__ = [
    "Execution",
    "SignedOrder",
    "ExecutionRecord",
    "OrderStateHistory",
    "FillRecord",
    "ExecutionConfig",
    "EIP712Signer",
    "NonceManager",
    "OrderLifecycleManager",
]

