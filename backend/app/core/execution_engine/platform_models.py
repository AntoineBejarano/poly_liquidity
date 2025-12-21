"""
Modelos de datos estandarizados para la capa de abstracción de plataformas.

Estos modelos proporcionan una interfaz común para todas las plataformas,
independientemente de sus implementaciones específicas.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from decimal import Decimal
from uuid import UUID
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    """Estados estandarizados de una orden."""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class OrderType(str, Enum):
    """Tipos de orden estandarizados."""
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    GTC = "GTC"  # Good Till Cancel
    FOK = "FOK"  # Fill or Kill
    IOC = "IOC"  # Immediate or Cancel


class OrderResult(BaseModel):
    """
    Resultado de enviar una orden a la plataforma.
    
    Este modelo estandariza la respuesta de todas las plataformas,
    independientemente de su formato específico.
    """
    platform_order_id: str = Field(..., description="ID de la orden en la plataforma")
    status: OrderStatus = Field(..., description="Estado inicial de la orden")
    filled_size: Decimal = Field(default=Decimal("0"), description="Tamaño ejecutado en shares")
    filled_size_usdc: Decimal = Field(default=Decimal("0"), description="Tamaño ejecutado en USDC")
    average_price: Optional[Decimal] = Field(None, description="Precio promedio de ejecución")
    
    # Trazabilidad
    trace_id: Optional[UUID] = Field(None, description="ID de trazabilidad")
    
    # Metadatos específicos de la plataforma
    platform_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos específicos de la plataforma")
    
    # Timestamp
    submitted_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp de envío")
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class OrderStatusUpdate(BaseModel):
    """
    Actualización del estado de una orden.
    
    Usado para polling o actualizaciones via WebSocket.
    """
    platform_order_id: str = Field(..., description="ID de la orden en la plataforma")
    status: OrderStatus = Field(..., description="Estado actual de la orden")
    filled_size: Decimal = Field(..., description="Tamaño ejecutado en shares")
    filled_size_usdc: Decimal = Field(..., description="Tamaño ejecutado en USDC")
    average_price: Optional[Decimal] = Field(None, description="Precio promedio de ejecución")
    remaining_size: Decimal = Field(..., description="Tamaño restante en shares")
    
    # Trazabilidad
    trace_id: Optional[UUID] = Field(None, description="ID de trazabilidad")
    
    # Metadatos específicos de la plataforma
    platform_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos específicos de la plataforma")
    
    # Timestamp
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp de actualización")
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class PlatformFeatureNotSupported(Exception):
    """
    Excepción lanzada cuando una plataforma no soporta una feature específica.
    
    Ejemplo: Market orders en Polymarket, o tipos de orden específicos.
    """
    def __init__(self, platform_name: str, feature: str, reason: Optional[str] = None):
        self.platform_name = platform_name
        self.feature = feature
        self.reason = reason
        message = f"Platform '{platform_name}' does not support feature '{feature}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)

