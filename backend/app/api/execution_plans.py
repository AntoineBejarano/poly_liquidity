"""
Execution Plans API endpoints.

APIs para gestionar Execution Plans de estrategias.
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.api.auth import get_current_user, User
from app.models.strategy import Strategy
from app.models.execution_plan import ExecutionPlan
from app.core.strategy_engine.invariants import validate_plan_state_transition

router = APIRouter(prefix="/strategies/{strategy_id}/plans", tags=["execution-plans"])


# Pydantic models para response
class PlanLegResponse(BaseModel):
    """Modelo de respuesta para un leg del plan."""
    leg_id: str
    side: str
    outcome: str
    target_price: float
    size: float
    size_usdc: float
    status: str
    filled_size: float
    filled_size_usdc: float
    reason: str
    metadata: dict

    class Config:
        from_attributes = True


class ExecutionPlanResponse(BaseModel):
    """Modelo de respuesta para ExecutionPlan."""
    id: str
    strategy_id: str
    event_id: str
    legs: List[PlanLegResponse]
    ttl_ms: int
    status: str
    risk_config: dict
    trace_id: Optional[str]
    decision_graph_execution_id: Optional[str]
    execution_graph_execution_id: Optional[str]
    expires_at: Optional[str]
    ready_for_execution: bool
    queued_at: Optional[str]
    node_versions: Optional[dict]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PlanAbortRequest(BaseModel):
    """Modelo para abortar un plan."""
    reason: Optional[str] = Field(None, description="Razón del aborto")


def plan_to_dict(plan: ExecutionPlan) -> dict:
    """Convierte un ExecutionPlan a diccionario."""
    return {
        "id": str(plan.id),
        "strategy_id": str(plan.strategy_id),
        "event_id": str(plan.event_id),
        "legs": [
            {
                "leg_id": leg.get("leg_id"),
                "side": leg.get("side"),
                "outcome": leg.get("outcome"),
                "target_price": float(leg.get("target_price", 0)),
                "size": float(leg.get("size", 0)),
                "size_usdc": float(leg.get("size_usdc", 0)),
                "status": leg.get("status", "PENDING"),
                "filled_size": float(leg.get("filled_size", 0)),
                "filled_size_usdc": float(leg.get("filled_size_usdc", 0)),
                "reason": leg.get("reason", ""),
                "metadata": leg.get("metadata", {})
            }
            for leg in (plan.legs or [])
        ],
        "ttl_ms": plan.ttl_ms,
        "status": plan.status,
        "risk_config": plan.risk_config or {},
        "trace_id": str(plan.trace_id) if plan.trace_id else None,
        "decision_graph_execution_id": str(plan.decision_graph_execution_id) if plan.decision_graph_execution_id else None,
        "execution_graph_execution_id": str(plan.execution_graph_execution_id) if plan.execution_graph_execution_id else None,
        "expires_at": plan.expires_at.isoformat() if plan.expires_at else None,
        "ready_for_execution": plan.ready_for_execution,
        "queued_at": plan.queued_at.isoformat() if plan.queued_at else None,
        "node_versions": plan.node_versions,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    }


@router.get("", response_model=List[ExecutionPlanResponse])
async def list_execution_plans(
    strategy_id: UUID,
    status_filter: Optional[str] = Query(None, description="Filtrar por status"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista Execution Plans de una estrategia.
    
    Permite filtrar por status y paginar resultados.
    """
    # Verificar que la estrategia existe
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Construir query
    query = db.query(ExecutionPlan).filter(ExecutionPlan.strategy_id == strategy_id)
    
    # Filtrar por status si se proporciona
    if status_filter:
        valid_statuses = ["PLAN_BUILT", "ABORTED", "EXECUTING", "COMPLETED", "FAILED"]
        if status_filter not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter. Valid values: {', '.join(valid_statuses)}"
            )
        query = query.filter(ExecutionPlan.status == status_filter)
    
    # Ordenar por created_at descendente (más recientes primero)
    query = query.order_by(ExecutionPlan.created_at.desc())
    
    # Paginación
    total = query.count()
    plans = query.offset(offset).limit(limit).all()
    
    return [plan_to_dict(plan) for plan in plans]


@router.get("/{plan_id}", response_model=ExecutionPlanResponse)
async def get_execution_plan(
    strategy_id: UUID,
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene el detalle de un Execution Plan.
    """
    # Verificar que la estrategia existe
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Obtener el plan
    plan = db.query(ExecutionPlan).filter(
        ExecutionPlan.id == plan_id,
        ExecutionPlan.strategy_id == strategy_id
    ).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution plan not found"
        )
    
    return plan_to_dict(plan)


@router.post("/{plan_id}/abort", response_model=ExecutionPlanResponse)
async def abort_execution_plan(
    strategy_id: UUID,
    plan_id: UUID,
    abort_data: PlanAbortRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Aborta un Execution Plan.
    
    Solo se puede abortar si el plan está en estado PLAN_BUILT o EXECUTING.
    """
    # Verificar que la estrategia existe
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Obtener el plan con lock (SELECT FOR UPDATE)
    plan = db.query(ExecutionPlan).filter(
        ExecutionPlan.id == plan_id,
        ExecutionPlan.strategy_id == strategy_id
    ).with_for_update().first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution plan not found"
        )
    
    # Validar que se puede abortar
    if plan.status not in ["PLAN_BUILT", "EXECUTING"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot abort plan in status {plan.status}. Only PLAN_BUILT or EXECUTING plans can be aborted."
        )
    
    # Validar transición de estado
    try:
        validate_plan_state_transition(plan.status, "ABORTED")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Cambiar estado a ABORTED
    plan.status = "ABORTED"
    plan.ready_for_execution = False
    
    # Añadir razón del aborto (almacenar en risk_config o crear campo metadata si existe)
    # Por ahora, almacenamos en risk_config como metadata temporal
    if abort_data.reason:
        if not plan.risk_config:
            plan.risk_config = {}
        if "_abort_metadata" not in plan.risk_config:
            plan.risk_config["_abort_metadata"] = {}
        plan.risk_config["_abort_metadata"]["reason"] = abort_data.reason
        plan.risk_config["_abort_metadata"]["aborted_by"] = current_user.id if current_user else None
        plan.risk_config["_abort_metadata"]["aborted_at"] = datetime.utcnow().isoformat()
    
    db.commit()
    db.refresh(plan)
    
    return plan_to_dict(plan)

