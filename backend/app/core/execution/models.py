"""
Modelos de datos para Execution Engine.

Según especificación en docs/services/execution.md y docs/services/signatures_trazability.md
"""
from pydantic import BaseModel
from typing import Dict, Optional, Any, List
from uuid import UUID
from datetime import datetime


class SignedOrder(BaseModel):
    """
    Orden firmada lista para enviar a Polymarket.
    
    Según especificación en docs/services/signatures_trazability.md
    """
    signed_order_id: UUID
    intent_id: Optional[UUID] = None  # FK a OrderIntent
    trace_id: Optional[UUID] = None  # Heredado del intent
    
    # Información de la wallet
    wallet_address: str  # Dirección de la wallet usada
    chain_id: int = 137  # Chain ID (137 para Polygon)
    
    # Información EIP-712
    domain_separator: Optional[str] = None  # Hash del domain EIP-712
    domain_json: Dict[str, Any] = {}  # Domain completo (para auditoría)
    message_struct: Dict[str, Any] = {}  # Estructura EIP-712 antes de firmar
    message_hash: Optional[str] = None  # Hash del mensaje firmado
    signature: str  # Firma hex (0x...)
    
    # Metadatos
    created_at: datetime = datetime.utcnow()
    expires_at: Optional[datetime] = None  # Si la orden tiene expiración
    
    # Estado
    status: str = "READY_TO_SEND"  # "READY_TO_SEND" | "SENT" | "SEND_FAILED"


class ExecutionRecord(BaseModel):
    """
    Registro de ejecución de una orden.
    
    Según especificación en docs/services/signatures_trazability.md
    """
    execution_id: UUID
    signed_order_id: UUID  # FK a SignedOrder
    trace_id: Optional[UUID] = None  # Heredado
    
    # Respuesta de Polymarket
    polymarket_order_id: Optional[str] = None  # ID que devuelve Polymarket
    
    # Payloads completos (para auditoría)
    request_payload: Dict[str, Any] = {}  # JSON completo enviado
    request_payload_hash: Optional[str] = None  # Hash para logs (SHA256)
    response_payload: Optional[Dict[str, Any]] = None  # JSON completo de respuesta
    response_payload_hash: Optional[str] = None  # Hash para logs
    
    # Metadatos HTTP
    http_status_code: Optional[int] = None
    http_method: str = "POST"
    endpoint_url: str = ""
    
    # Métricas
    created_at: datetime = datetime.utcnow()
    latency_ms: float = 0.0  # Tiempo request → response
    
    # Estado
    status: str = "PENDING"  # "ACCEPTED" | "REJECTED" | "ERROR" | "TIMEOUT" | "PENDING"
    error_message: Optional[str] = None
    error_code: Optional[str] = None  # Código de error de Polymarket
    
    # Retry info
    retry_count: int = 0
    is_retry: bool = False


class OrderStateHistory(BaseModel):
    """
    Histórico de cambios de estado de la orden.
    
    Según especificación en docs/services/signatures_trazability.md
    """
    order_state_history_id: UUID
    polymarket_order_id: str  # FK a orden en Polymarket
    trace_id: Optional[UUID] = None  # Para correlación
    
    # Timestamp
    timestamp: datetime = datetime.utcnow()
    
    # Estado
    previous_status: Optional[str] = None
    new_status: str  # Estado nuevo
    reason: Optional[str] = None  # Razón del cambio
    
    # Metadatos
    filled_size: float = 0.0  # Tamaño ejecutado hasta ahora
    remaining_size: float = 0.0  # Tamaño restante
    metadata: Dict[str, Any] = {}  # Metadatos adicionales


class FillRecord(BaseModel):
    """
    Registro de un fill de orden.
    
    Según especificación en docs/services/execution.md
    """
    fill_id: UUID
    order_id: UUID
    polymarket_order_id: str
    trace_id: Optional[UUID] = None
    
    # Información del fill
    fill_price: float
    fill_size: float
    timestamp: datetime = datetime.utcnow()
    
    # Metadatos
    fill_type: str = "PARTIAL"  # "PARTIAL" | "COMPLETE"
    metadata: Dict[str, Any] = {}


class ExecutionConfig(BaseModel):
    """
    Configuración del Execution Engine.
    
    Según especificación en docs/services/execution.md
    """
    polymarket_trading_endpoint: str = "https://api.polymarket.com/trades"
    trading_api_keys: Optional[Dict[str, str]] = None
    gas_parameters: Optional[Dict[str, Any]] = None
    timeout: float = 30.0  # Timeout de requests
    order_ttl_seconds: int = 3600  # TTL de órdenes (1 hora)
    max_retries: int = 3  # Máximo de reintentos
    retry_delays: List[float] = [0.2, 0.5, 1.0, 2.0, 4.0]  # Exponential backoff
    
    # EIP-712 Domain
    eip712_domain_name: str = "PolymarketTrading"
    eip712_domain_version: str = "1"
    eip712_chain_id: int = 137  # Polygon
    eip712_verifying_contract: Optional[str] = None
    
    # Polling
    poll_interval_seconds: float = 5.0  # Intervalo de polling de estado
    max_poll_attempts: int = 720  # Máximo de intentos de polling (1 hora a 5s)

