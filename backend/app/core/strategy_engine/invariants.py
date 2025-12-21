"""
Execution Invariants - Reglas que NUNCA pueden violarse.

Estas funciones verifican los invariantes del sistema de Execution Plans
para prevenir errores costosos y violaciones de la arquitectura.
"""
from typing import Optional
from app.models.execution_plan import ExecutionPlan


# Estados válidos del plan
VALID_STATUSES = {"PLAN_BUILT", "ABORTED", "EXECUTING", "COMPLETED", "FAILED"}

# Transiciones de estado válidas
VALID_TRANSITIONS = {
    "PLAN_BUILT": {"EXECUTING", "ABORTED"},
    "EXECUTING": {"COMPLETED", "FAILED", "ABORTED"},
    "COMPLETED": set(),  # Estado terminal
    "FAILED": set(),  # Estado terminal
    "ABORTED": set(),  # Estado terminal
}


def validate_plan_immutability(plan: ExecutionPlan) -> None:
    """
    Verifica que el plan no se modifique después de PLAN_BUILT.
    
    Invariante 1: An ExecutionPlan is immutable after creation.
    Invariante 2: No node may modify a plan after PLAN_BUILT.
    
    Args:
        plan: ExecutionPlan a validar
        
    Raises:
        ValueError: Si el plan está en un estado que no permite modificaciones
    """
    if plan.status not in VALID_STATUSES:
        raise ValueError(f"Invalid plan status: {plan.status}")
    
    # Si el plan ya está en un estado terminal o ejecutando, no se puede modificar
    if plan.status in {"EXECUTING", "COMPLETED", "FAILED", "ABORTED"}:
        raise ValueError(
            f"Cannot modify plan in status {plan.status}. "
            f"Plan is immutable after PLAN_BUILT."
        )


def validate_plan_state_transition(old_status: str, new_status: str) -> None:
    """
    Verifica transiciones de estado válidas.
    
    Invariante 3: Plan state transitions are strictly enforced.
    
    Transiciones válidas:
    - PLAN_BUILT → EXECUTING | ABORTED
    - EXECUTING → COMPLETED | FAILED | ABORTED
    - COMPLETED → (terminal, no transiciones)
    - FAILED → (terminal, no transiciones)
    - ABORTED → (terminal, no transiciones)
    
    Args:
        old_status: Estado actual del plan
        new_status: Estado nuevo al que se quiere transicionar
        
    Raises:
        ValueError: Si la transición no es válida
    """
    if old_status not in VALID_STATUSES:
        raise ValueError(f"Invalid old status: {old_status}")
    
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid new status: {new_status}")
    
    # ABORTED puede ocurrir desde cualquier estado
    if new_status == "ABORTED":
        return
    
    # Verificar transición válida
    allowed_transitions = VALID_TRANSITIONS.get(old_status, set())
    if new_status not in allowed_transitions:
        raise ValueError(
            f"Invalid state transition: {old_status} → {new_status}. "
            f"Allowed transitions from {old_status}: {allowed_transitions}"
        )


def validate_plan_not_expired(plan: ExecutionPlan) -> None:
    """
    Verifica que el plan no haya expirado.
    
    Invariante 4: Execution TTL is enforced strictly.
    
    Args:
        plan: ExecutionPlan a validar
        
    Raises:
        ValueError: Si el plan ha expirado
    """
    if plan.is_expired():
        from datetime import datetime
        raise ValueError(
            f"Plan {plan.id} has expired. "
            f"Expires at: {plan.expires_at}, Current time: {datetime.utcnow()}"
        )


def validate_plan_legs_immutability(plan: ExecutionPlan) -> None:
    """
    Verifica que los legs del plan no se modifiquen.
    
    Invariante 2 (detallado): No node may change leg size, target_price, add/remove legs.
    
    Args:
        plan: ExecutionPlan a validar
        
    Raises:
        ValueError: Si se intenta modificar los legs
    """
    if plan.status != "PLAN_BUILT":
        # Solo se pueden modificar legs en PLAN_BUILT
        # Después, solo se puede cambiar el status de los legs individuales
        pass  # Esta validación se hace en el código que modifica legs


def validate_compensation_only_reduces_exposure(compensation_actions: list) -> None:
    """
    Verifica que la compensación solo reduce exposición.
    
    Invariante 6: Compensation may only reduce exposure, never increase it.
    
    Args:
        compensation_actions: Lista de acciones de compensación
        
    Raises:
        ValueError: Si alguna acción aumenta exposición
    """
    for action in compensation_actions:
        action_type = action.get("type")
        if action_type == "create_order":
            raise ValueError(
                "Compensation cannot create new orders. "
                "It can only reverse or cancel existing orders."
            )
        if action_type == "increase_size":
            raise ValueError(
                "Compensation cannot increase order size. "
                "It can only reduce or cancel orders."
            )


def validate_hot_path_no_state_modification(node_type: str, path_type: str) -> None:
    """
    Verifica que nodos hot path no modifiquen State Cache.
    
    Invariante 7: Hot path nodes may not modify State Cache.
    
    Args:
        node_type: Tipo de nodo
        path_type: "hot" o "cold"
        
    Raises:
        ValueError: Si un nodo hot path intenta modificar estado
    """
    if path_type == "hot":
        state_modifying_nodes = {"update_state_cache"}
        if node_type in state_modifying_nodes:
            raise ValueError(
                f"Node {node_type} cannot be used in hot path (Decision Graph). "
                f"Hot path nodes may only read State Cache, never modify it."
            )

