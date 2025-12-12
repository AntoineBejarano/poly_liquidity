"""
Order Lifecycle Manager - Gestión del ciclo de vida de órdenes.

Según especificación en docs/services/execution.md
"""
import logging
from typing import Dict, Set, Optional
from datetime import datetime
from uuid import UUID
from app.database import SessionLocal
from app.models.order import Order

logger = logging.getLogger(__name__)


# Estados válidos de órdenes
ORDER_STATES = {
    "CREATED",
    "SIGNED",
    "SUBMITTED",
    "ACCEPTED",
    "OPEN",
    "PARTIALLY_FILLED",
    "FILLED",
    "EXPIRED",
    "CANCELLED",
    "REJECTED",
    "ERROR",
}

# Transiciones válidas de estado
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    "CREATED": {"SIGNED", "ERROR"},
    "SIGNED": {"SUBMITTED", "ERROR"},
    "SUBMITTED": {"ACCEPTED", "REJECTED", "ERROR", "TIMEOUT"},
    "ACCEPTED": {"OPEN", "REJECTED", "ERROR"},
    "OPEN": {"PARTIALLY_FILLED", "FILLED", "EXPIRED", "CANCELLED", "ERROR"},
    "PARTIALLY_FILLED": {"FILLED", "EXPIRED", "CANCELLED", "ERROR"},
    "FILLED": set(),  # Estado final
    "EXPIRED": set(),  # Estado final
    "CANCELLED": set(),  # Estado final
    "REJECTED": set(),  # Estado final
    "ERROR": {"SUBMITTED"},  # Puede reintentar
    "TIMEOUT": {"SUBMITTED"},  # Puede reintentar
}


class OrderLifecycleManager:
    """
    Gestor del ciclo de vida de órdenes.
    
    Maneja transiciones de estado y validaciones.
    """
    
    def __init__(self):
        """Inicializa el Order Lifecycle Manager."""
        pass
    
    def is_valid_transition(self, current_status: str, new_status: str) -> bool:
        """
        Verifica si una transición de estado es válida.
        
        Args:
            current_status: Estado actual
            new_status: Nuevo estado
        
        Returns:
            True si la transición es válida, False en caso contrario
        """
        if current_status not in VALID_TRANSITIONS:
            return False
        
        return new_status in VALID_TRANSITIONS[current_status]
    
    def update_order_state(
        self,
        order_id: UUID,
        new_status: str,
        reason: Optional[str] = None,
        filled_size: Optional[float] = None
    ) -> bool:
        """
        Actualiza estado de orden con validación de transiciones.
        
        Args:
            order_id: ID de la orden
            new_status: Nuevo estado
            reason: Razón del cambio (opcional)
            filled_size: Tamaño ejecutado (opcional)
        
        Returns:
            True si la actualización fue exitosa, False en caso contrario
        """
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                logger.warning(f"Order {order_id} not found in DB")
                return False
            
            current_status = order.status
            
            # Validar transición
            if not self.is_valid_transition(current_status, new_status):
                logger.warning(
                    f"Invalid state transition for order {order_id}: {current_status} -> {new_status}",
                    extra={
                        "order_id": str(order_id),
                        "current_status": current_status,
                        "new_status": new_status,
                        "reason": reason
                    }
                )
                return False
            
            # Actualizar estado
            order.status = new_status
            order.updated_at = datetime.utcnow()
            
            if filled_size is not None:
                order.filled_size = filled_size
            
            db.commit()
            
            # Loggear transición
            logger.info(
                f"Order state transition: {order_id} {current_status} -> {new_status}",
                extra={
                    "order_id": str(order_id),
                    "previous_status": current_status,
                    "new_status": new_status,
                    "reason": reason,
                    "filled_size": filled_size
                }
            )
            
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating order state: {e}")
            return False
        finally:
            db.close()
    
    def can_retry(self, order_status: str) -> bool:
        """
        Verifica si una orden puede reintentarse.
        
        Args:
            order_status: Estado actual de la orden
        
        Returns:
            True si puede reintentarse, False en caso contrario
        """
        return order_status in ("ERROR", "TIMEOUT", "REJECTED")
    
    def is_terminal_state(self, order_status: str) -> bool:
        """
        Verifica si un estado es terminal (no puede cambiar).
        
        Args:
            order_status: Estado a verificar
        
        Returns:
            True si es terminal, False en caso contrario
        """
        terminal_states = {"FILLED", "EXPIRED", "CANCELLED", "REJECTED"}
        return order_status in terminal_states

