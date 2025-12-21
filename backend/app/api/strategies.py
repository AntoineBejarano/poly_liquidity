"""
Strategies API endpoints.

APIs para gestionar estrategias basadas en grafos.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.api.auth import get_current_user, get_admin_user, User
from app.models.strategy import Strategy
from app.models.strategy_event import StrategyEvent
from app.models.event import Event
from app.models.execution_intent import ExecutionIntent
from app.models.graph_execution import GraphExecution
from app.models.strategy_metric import StrategyMetric
from app.models.execution_plan import ExecutionPlan

router = APIRouter(prefix="/strategies", tags=["strategies"])


# Pydantic models para request/response
class StrategyCreate(BaseModel):
    """Modelo para crear una estrategia."""
    name: str = Field(..., description="Nombre de la estrategia")
    description: Optional[str] = Field(None, description="Descripción")
    decision_graph: Dict[str, Any] = Field(..., description="Decision Graph (JSON)")
    support_graphs: Optional[List[Dict[str, Any]]] = Field(default=[], description="Support Graphs")
    execution_graph: Optional[Dict[str, Any]] = Field(default=None, description="Execution Graph (JSON)")
    triggers: Optional[List[Dict[str, Any]]] = Field(default=[], description="Strategy Triggers")
    control_loop_config: Optional[Dict[str, Any]] = Field(default={}, description="Configuración del Control Loop")
    risk_config: Optional[Dict[str, Any]] = Field(default={}, description="Configuración de riesgo")
    observability_config: Optional[Dict[str, Any]] = Field(default={}, description="Configuración de observabilidad")
    pinned_node_versions: Optional[Dict[str, str]] = Field(default=None, description="Versiones pinned de nodos")
    tags: Optional[List[str]] = Field(default=None, description="Tags")


class StrategyUpdate(BaseModel):
    """Modelo para actualizar una estrategia."""
    name: Optional[str] = None
    description: Optional[str] = None
    decision_graph: Optional[Dict[str, Any]] = None
    support_graphs: Optional[List[Dict[str, Any]]] = None
    execution_graph: Optional[Dict[str, Any]] = None
    triggers: Optional[List[Dict[str, Any]]] = None
    control_loop_config: Optional[Dict[str, Any]] = None
    risk_config: Optional[Dict[str, Any]] = None
    observability_config: Optional[Dict[str, Any]] = None
    pinned_node_versions: Optional[Dict[str, str]] = None
    tags: Optional[List[str]] = None


class StrategyResponse(BaseModel):
    """Modelo de respuesta para estrategia."""
    id: str
    name: str
    description: Optional[str]
    is_active: bool
    enabled_at: Optional[str]
    disabled_at: Optional[str]
    decision_graph: Dict[str, Any]
    support_graphs: List[Dict[str, Any]]
    execution_graph: Optional[Dict[str, Any]]
    triggers: List[Dict[str, Any]]
    control_loop_config: Dict[str, Any]
    risk_config: Dict[str, Any]
    observability_config: Dict[str, Any]
    pinned_node_versions: Optional[Dict[str, str]]
    created_by: Optional[str]
    tags: Optional[List[str]]
    version: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


def strategy_to_dict(strategy: Strategy) -> Dict[str, Any]:
    """Convierte un modelo Strategy a diccionario."""
    return {
        "id": str(strategy.id),
        "name": strategy.name,
        "description": strategy.description,
        "is_active": strategy.is_active,
        "enabled_at": strategy.enabled_at.isoformat() if strategy.enabled_at else None,
        "disabled_at": strategy.disabled_at.isoformat() if strategy.disabled_at else None,
        "decision_graph": strategy.decision_graph,
        "support_graphs": strategy.support_graphs or [],
        "execution_graph": strategy.execution_graph,
        "triggers": strategy.triggers or [],
        "control_loop_config": strategy.control_loop_config or {},
        "risk_config": strategy.risk_config or {},
        "observability_config": strategy.observability_config or {},
        "pinned_node_versions": strategy.pinned_node_versions,
        "created_by": strategy.created_by,
        "tags": strategy.tags,
        "version": strategy.version,
        "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
        "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
    }


def validate_decision_graph(graph: Dict[str, Any]) -> None:
    """Valida que un Decision Graph tenga la estructura correcta."""
    if "entry_node" not in graph:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision graph must have 'entry_node'"
        )
    if "nodes" not in graph:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision graph must have 'nodes'"
        )
    # Verificar que entry_node existe en nodes
    if graph["entry_node"] not in graph["nodes"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Entry node '{graph['entry_node']}' not found in nodes"
        )


def validate_support_graph(graph: Dict[str, Any]) -> None:
    """Valida que un Support Graph tenga la estructura correcta."""
    if "name" not in graph:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Support graph must have 'name'"
        )
    if "entry_node" not in graph:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Support graph must have 'entry_node'"
        )
    if "nodes" not in graph:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Support graph must have 'nodes'"
        )


def validate_execution_graph(graph: Dict[str, Any]) -> None:
    """Valida que un Execution Graph tenga la estructura correcta."""
    if not graph:
        return  # Execution graph es opcional
    
    if "entry_node" not in graph:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Execution graph must have 'entry_node'"
        )
    if "nodes" not in graph:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Execution graph must have 'nodes'"
        )
    # Verificar que entry_node existe en nodes
    if graph["entry_node"] not in graph["nodes"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Entry node '{graph['entry_node']}' not found in nodes"
        )


def validate_triggers(triggers: List[Dict[str, Any]]) -> None:
    """Valida que los triggers tengan la estructura correcta."""
    if not triggers:
        return  # Triggers es opcional (puede ser lista vacía)
    
    valid_trigger_types = ["always", "near_end", "edge_detected", "state_change", "timer"]
    
    for i, trigger in enumerate(triggers):
        if not isinstance(trigger, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trigger at index {i} must be a dictionary"
            )
        
        trigger_type = trigger.get("type")
        if not trigger_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trigger at index {i} must have 'type' field"
            )
        
        if trigger_type not in valid_trigger_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trigger at index {i} has invalid type '{trigger_type}'. "
                       f"Valid types: {', '.join(valid_trigger_types)}"
            )


@router.get("", response_model=List[StrategyResponse])
async def list_strategies(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todas las estrategias."""
    query = db.query(Strategy)
    
    if is_active is not None:
        query = query.filter(Strategy.is_active == is_active)
    
    if search:
        query = query.filter(Strategy.name.ilike(f"%{search}%"))
    
    strategies = query.order_by(Strategy.created_at.desc()).all()
    return [strategy_to_dict(s) for s in strategies]


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy_data: StrategyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Crea una nueva estrategia con Decision Graph."""
    # Validar Decision Graph
    validate_decision_graph(strategy_data.decision_graph)
    
    # Validar Support Graphs
    for support_graph in strategy_data.support_graphs or []:
        validate_support_graph(support_graph)
    
    # Validar execution_graph si se proporciona
    if strategy_data.execution_graph:
        validate_execution_graph(strategy_data.execution_graph)
    
    # Validar triggers si se proporcionan
    if strategy_data.triggers:
        validate_triggers(strategy_data.triggers)
    
    strategy = Strategy(
        name=strategy_data.name,
        description=strategy_data.description,
        decision_graph=strategy_data.decision_graph,
        support_graphs=strategy_data.support_graphs or [],
        execution_graph=strategy_data.execution_graph,
        triggers=strategy_data.triggers or [],
        control_loop_config=strategy_data.control_loop_config or {},
        risk_config=strategy_data.risk_config or {},
        observability_config=strategy_data.observability_config or {},
        pinned_node_versions=strategy_data.pinned_node_versions,
        created_by=current_user.id,
        tags=strategy_data.tags,
        is_active=False
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    
    return strategy_to_dict(strategy)


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene una estrategia por ID."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    return strategy_to_dict(strategy)


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: UUID,
    strategy_data: StrategyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Actualiza una estrategia."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    if strategy_data.name is not None:
        strategy.name = strategy_data.name
    if strategy_data.description is not None:
        strategy.description = strategy_data.description
    if strategy_data.decision_graph is not None:
        validate_decision_graph(strategy_data.decision_graph)
        strategy.decision_graph = strategy_data.decision_graph
    if strategy_data.support_graphs is not None:
        for support_graph in strategy_data.support_graphs:
            validate_support_graph(support_graph)
        strategy.support_graphs = strategy_data.support_graphs
    if strategy_data.execution_graph is not None:
        validate_execution_graph(strategy_data.execution_graph)
        strategy.execution_graph = strategy_data.execution_graph
    if strategy_data.triggers is not None:
        validate_triggers(strategy_data.triggers)
        strategy.triggers = strategy_data.triggers
    if strategy_data.control_loop_config is not None:
        strategy.control_loop_config = strategy_data.control_loop_config
    if strategy_data.risk_config is not None:
        strategy.risk_config = strategy_data.risk_config
    if strategy_data.observability_config is not None:
        strategy.observability_config = strategy_data.observability_config
    if strategy_data.pinned_node_versions is not None:
        strategy.pinned_node_versions = strategy_data.pinned_node_versions
    if strategy_data.tags is not None:
        strategy.tags = strategy_data.tags
    
    db.commit()
    db.refresh(strategy)
    
    return strategy_to_dict(strategy)


@router.post("/{strategy_id}/activate", response_model=StrategyResponse)
async def activate_strategy(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Activa una estrategia."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    if strategy.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is already active"
        )
    
    strategy.is_active = True
    strategy.enabled_at = datetime.utcnow()
    strategy.disabled_at = None
    
    db.commit()
    db.refresh(strategy)
    
    return strategy_to_dict(strategy)


@router.post("/{strategy_id}/deactivate", response_model=StrategyResponse)
async def deactivate_strategy(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Desactiva una estrategia."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    if not strategy.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is already inactive"
        )
    
    strategy.is_active = False
    strategy.disabled_at = datetime.utcnow()
    
    db.commit()
    db.refresh(strategy)
    
    return strategy_to_dict(strategy)


@router.get("/{strategy_id}/graph")
async def get_strategy_graph(
    strategy_id: UUID,
    graph_type: str = Query("decision", description="'decision' o 'support'"),
    graph_name: Optional[str] = Query(None, description="Nombre del support graph"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene el grafo de una estrategia."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    if graph_type == "decision":
        return {"graph": strategy.decision_graph}
    elif graph_type == "support":
        if graph_name:
            support_graph = next(
                (g for g in (strategy.support_graphs or []) if g.get("name") == graph_name),
                None
            )
            if not support_graph:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Support graph not found"
                )
            return {"graph": support_graph}
        else:
            return {"graphs": strategy.support_graphs or []}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid graph_type. Must be 'decision' or 'support'"
        )


@router.put("/{strategy_id}/graph")
async def update_strategy_graph(
    strategy_id: UUID,
    graph_type: str = Query("decision", description="'decision' o 'support'"),
    graph_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Actualiza el grafo de una estrategia."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    if strategy.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update graph of active strategy"
        )
    
    # Validar grafo
    if graph_type == "decision":
        validate_decision_graph(graph_data)
        strategy.decision_graph = graph_data
    elif graph_type == "support":
        validate_support_graph(graph_data)
        # Actualizar o agregar support graph
        support_graphs = strategy.support_graphs or []
        graph_name = graph_data.get("name")
        
        if graph_name:
            # Buscar si existe
            found = False
            for i, sg in enumerate(support_graphs):
                if sg.get("name") == graph_name:
                    support_graphs[i] = graph_data
                    found = True
                    break
            
            if not found:
                support_graphs.append(graph_data)
        else:
            support_graphs.append(graph_data)
        
        strategy.support_graphs = support_graphs
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid graph_type. Must be 'decision' or 'support'"
        )
    
    strategy.version += 1
    db.commit()
    db.refresh(strategy)
    
    return strategy_to_dict(strategy)


@router.get("/{strategy_id}/events")
async def get_strategy_events(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene los eventos asignados a una estrategia."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    strategy_events = db.query(StrategyEvent).filter(
        StrategyEvent.strategy_id == strategy_id
    ).all()
    
    result = []
    for se in strategy_events:
        event = se.event
        result.append({
            "strategy_event_id": str(se.id),
            "event_id": str(event.id),
            "polymarket_event_id": event.polymarket_event_id,
            "market_id": str(event.market_id),
            "start_time": event.start_time.isoformat() if event.start_time else None,
            "end_time": event.end_time.isoformat() if event.end_time else None,
            "state": event.state,
            "observation_started_at": se.observation_started_at.isoformat() if se.observation_started_at else None,
            "observation_ended_at": se.observation_ended_at.isoformat() if se.observation_ended_at else None,
            "event_config": se.event_config,
        })
    
    return {"events": result}


@router.post("/{strategy_id}/events/{event_id}")
async def assign_event_to_strategy(
    strategy_id: UUID,
    event_id: UUID,
    event_config: Optional[Dict[str, Any]] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Asigna un evento a una estrategia."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Verificar si ya existe
    existing = db.query(StrategyEvent).filter(
        StrategyEvent.strategy_id == strategy_id,
        StrategyEvent.event_id == event_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event already assigned to strategy"
        )
    
    strategy_event = StrategyEvent(
        strategy_id=strategy_id,
        event_id=event_id,
        event_config=event_config
    )
    db.add(strategy_event)
    db.commit()
    db.refresh(strategy_event)
    
    return {
        "strategy_event_id": str(strategy_event.id),
        "strategy_id": str(strategy_id),
        "event_id": str(event_id),
        "message": "Event assigned successfully"
    }


@router.delete("/{strategy_id}/events/{event_id}")
async def unassign_event_from_strategy(
    strategy_id: UUID,
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Desasigna un evento de una estrategia."""
    strategy_event = db.query(StrategyEvent).filter(
        StrategyEvent.strategy_id == strategy_id,
        StrategyEvent.event_id == event_id
    ).first()
    
    if not strategy_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not assigned to strategy"
        )
    
    db.delete(strategy_event)
    db.commit()
    
    return {"message": "Event unassigned successfully"}


@router.get("/{strategy_id}/intents")
async def get_strategy_intents(
    strategy_id: UUID,
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene los intents generados por una estrategia."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    query = db.query(ExecutionIntent).filter(
        ExecutionIntent.strategy_id == strategy_id
    )
    
    if status_filter:
        query = query.filter(ExecutionIntent.status == status_filter)
    
    intents = query.order_by(ExecutionIntent.created_at.desc()).limit(limit).offset(offset).all()
    
    result = []
    for intent in intents:
        result.append({
            "id": str(intent.id),
            "event_id": str(intent.event_id),
            "side": intent.side,
            "outcome": intent.outcome,
            "target_price": float(intent.target_price),
            "size": float(intent.size),
            "size_usdc": float(intent.size_usdc),
            "reason": intent.reason,
            "status": intent.status,
            "context": intent.context,
            "trace_id": str(intent.trace_id) if intent.trace_id else None,
            "graph_execution_id": str(intent.graph_execution_id) if intent.graph_execution_id else None,
            "created_at": intent.created_at.isoformat() if intent.created_at else None,
        })
    
    return {"intents": result, "total": len(result)}


@router.get("/{strategy_id}/executions")
async def get_strategy_executions(
    strategy_id: UUID,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene las ejecuciones (GraphExecution) de una estrategia."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    query = db.query(GraphExecution).filter(
        GraphExecution.strategy_id == strategy_id
    )
    
    executions = query.order_by(GraphExecution.created_at.desc()).limit(limit).offset(offset).all()
    
    result = []
    for execution in executions:
        result.append({
            "id": str(execution.id),
            "strategy_id": str(execution.strategy_id),
            "graph_type": execution.graph_type,
            "status": execution.status,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "error_message": execution.error_message,
            "context": execution.context,
        })
    
    return {"executions": result, "total": len(result)}


@router.get("/{strategy_id}/metrics")
async def get_strategy_metrics(
    strategy_id: UUID,
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene las métricas de una estrategia."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    query = db.query(StrategyMetric).filter(
        StrategyMetric.strategy_id == strategy_id
    )
    
    if period_start:
        query = query.filter(StrategyMetric.period_start >= period_start)
    if period_end:
        query = query.filter(StrategyMetric.period_end <= period_end)
    
    metrics = query.order_by(StrategyMetric.period_start.desc()).all()
    
    result = []
    for metric in metrics:
        result.append({
            "period_start": metric.period_start.isoformat() if metric.period_start else None,
            "period_end": metric.period_end.isoformat() if metric.period_end else None,
            "total_intents": metric.total_intents,
            "approved_intents": metric.approved_intents,
            "executed_intents": metric.executed_intents,
            "rejected_intents": metric.rejected_intents,
            "total_volume_usdc": float(metric.total_volume_usdc) if metric.total_volume_usdc else None,
            "total_pnl_usdc": float(metric.total_pnl_usdc) if metric.total_pnl_usdc else None,
            "total_exposure_usdc": float(metric.total_exposure_usdc) if metric.total_exposure_usdc else None,
            "win_rate": float(metric.win_rate) if metric.win_rate else None,
            "avg_entry_price": float(metric.avg_entry_price) if metric.avg_entry_price else None,
            "avg_exit_price": float(metric.avg_exit_price) if metric.avg_exit_price else None,
            "calculated_at": metric.calculated_at.isoformat() if metric.calculated_at else None,
        })
    
    return {"metrics": result}

