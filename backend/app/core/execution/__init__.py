"""
Execution Engine - Firma, envío, gestión y confirmación de órdenes.

Refactorizado según especificación en docs/services/execution.md y docs/services/signatures_trazability.md
"""
from app.core.execution.execution import Execution
from app.core.execution.polymarket_client_wrapper import (
    get_polymarket_client,
    get_polymarket_client_for_user,
    PolymarketCLOBWrapper,
)
from app.core.execution.polymarket_websocket import (
    get_websocket_manager,
    PolymarketWebSocketManager,
    PolymarketWebSocketClient,
    ChannelType,
    WebSocketAuth
)
from app.core.execution.models import (
    SignedOrder, ExecutionRecord, OrderStateHistory, FillRecord, ExecutionConfig
)
from app.core.execution.eip712_signer import EIP712Signer
from app.core.execution.nonce_manager import NonceManager
from app.core.execution.order_lifecycle import OrderLifecycleManager
from app.core.execution.gateway import (
    ExecutionGateway,
    ExecutionGatewayRequest,
    ExecutionGatewayResult,
    GatewayDecision,
    SourcePath,
    get_execution_gateway,
)

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
    "get_polymarket_client",
    "get_polymarket_client_for_user",
    "PolymarketCLOBWrapper",
    "ExecutionGateway",
    "ExecutionGatewayRequest",
    "ExecutionGatewayResult",
    "GatewayDecision",
    "SourcePath",
    "get_execution_gateway",
    "get_websocket_manager",
    "PolymarketWebSocketManager",
    "PolymarketWebSocketClient",
    "ChannelType",
    "WebSocketAuth",
]

