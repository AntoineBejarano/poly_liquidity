"""
Strategies API endpoints.

APIs para gestionar estrategias basadas en grafos.
"""
from typing import Optional, List, Dict, Any, Set
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, status, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from app.database import get_db
from app.api.auth import get_current_user, get_admin_user, User
from app.models.strategy import Strategy
from app.models.strategy_event import StrategyEvent
from app.models.event import Event
from app.models.execution_intent import ExecutionIntent
from app.models.graph_execution import GraphExecution
from app.models.strategy_metric import StrategyMetric
from app.models.execution_plan import ExecutionPlan
from app.models.market import Market
from app.models.market_enabled_state import MarketEnabledState

logger = logging.getLogger(__name__)

# Precedencia Universe (Phase 2): enabled global > deny_list > selectors (categories, markets, tags).
# Documentación: DISCOVERY_UNIVERSE_STRATEGY_BUILDER_SPEC.md


def _is_market_enabled_global(db: Session, polymarket_market_id: str) -> bool:
    """True si el market está enabled global (MarketEnabledState o Market.enabled)."""
    state = db.query(MarketEnabledState).filter(
        MarketEnabledState.polymarket_market_id == polymarket_market_id
    ).first()
    if state is not None:
        return state.enabled
    market = db.query(Market).filter(Market.polymarket_id == polymarket_market_id).first()
    return market.enabled if (market and getattr(market, "enabled", None) is not None) else False


def _validate_universe_enabled_global(
    db: Session,
    market_ids: List[str],
    event_ids: List[str],
) -> tuple[bool, List[str], List[str]]:
    """
    Valida que todos los markets y events referenciados estén enabled global.
    market_ids: polymarket_id (string).
    event_ids: nuestros event UUID (string).
    Returns: (ok, not_enabled_market_ids, not_enabled_event_ids).
    """
    not_enabled_markets: List[str] = []
    not_enabled_events: List[str] = []
    for mid in (market_ids or []):
        if not _is_market_enabled_global(db, mid):
            not_enabled_markets.append(mid)
    for eid in (event_ids or []):
        try:
            ev = db.query(Event).filter(Event.id == UUID(str(eid))).first()
        except (ValueError, TypeError):
            ev = None
        if not ev:
            not_enabled_events.append(eid)
            continue
        market = db.query(Market).filter(Market.id == ev.market_id).first()
        if not market:
            not_enabled_events.append(eid)
            continue
        if not _is_market_enabled_global(db, market.polymarket_id):
            not_enabled_events.append(eid)
    ok = len(not_enabled_markets) == 0 and len(not_enabled_events) == 0
    return ok, not_enabled_markets, not_enabled_events

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


def _get_asset_ids_from_strategy(strategy_id: UUID, db: Session) -> Set[str]:
    """
    Obtiene todos los asset_ids (token IDs) de los eventos asignados a una estrategia.
    
    Args:
        strategy_id: ID de la estrategia
        db: Sesión de base de datos
        
    Returns:
        Set de asset_ids (token IDs)
    """
    asset_ids = set()
    
    # Obtener eventos asignados a la estrategia
    strategy_events = db.query(StrategyEvent).filter(
        StrategyEvent.strategy_id == strategy_id
    ).all()
    
    for se in strategy_events:
        event = se.event
        if not event:
            continue
        
        # Intentar obtener clobTokenIds del event
        clob_token_ids = None
        if event.polymarket_payload:
            clob_token_ids = event.polymarket_payload.get("clobTokenIds") or event.polymarket_payload.get("clob_token_ids")
        
        # Si no está en el event, intentar desde el market
        if not clob_token_ids and event.market:
            market = event.market
            if market.polymarket_payload:
                clob_token_ids = market.polymarket_payload.get("clobTokenIds") or market.polymarket_payload.get("clob_token_ids")
        
        # Procesar clobTokenIds
        if clob_token_ids:
            if isinstance(clob_token_ids, dict):
                # Formato: {"YES": "token_id", "NO": "token_id"}
                asset_ids.update(clob_token_ids.values())
            elif isinstance(clob_token_ids, list):
                # Formato: ["token_id_yes", "token_id_no"]
                asset_ids.update(clob_token_ids)
    
    return asset_ids


# Pydantic models para request/response


class TimeFilterConfig(BaseModel):
    """Ventana temporal para elegibilidad de events (Phase 2)."""
    window: Optional[str] = Field(default=None, description="Ventana: UPCOMING, ACTIVE, etc.")
    next_days: Optional[int] = Field(default=None, ge=0, description="Events con end_time en los próximos N días")
    max_time_to_resolution_minutes: Optional[int] = Field(
        default=None, ge=0,
        description="Máximo minutos hasta resolución (end_time - now)"
    )


class UniverseConfig(BaseModel):
    """
    Configuración del universo de mercados/eventos de una estrategia.
    
    Precedencia (Phase 2): enabled global > deny_list > selectors (categories, markets, tags).
    Solo se consideran elegibles markets/events con enabled global = True.
    """
    categories: Optional[List[str]] = Field(default=[], description="Categorías permitidas")
    markets: Optional[List[str]] = Field(default=[], description="Markets específicos (polymarket_id)")
    tags: Optional[List[str]] = Field(default=[], description="Tags permitidos")
    events: Optional[List[str]] = Field(default=[], description="Event IDs (UUID internos) explícitamente incluidos")
    time_filter: Optional[TimeFilterConfig] = Field(default=None, description="Filtro temporal (next_days, max_time_to_resolution_minutes)")
    auto_attach: Optional[bool] = Field(default=False, description="Auto-attach nuevos events")
    deny_list: Optional[List[str]] = Field(default=[], description="Markets/events excluidos")
    # Phase 4: límites y dry-run
    max_events_per_strategy: Optional[int] = Field(default=None, ge=1, le=500, description="Máximo eventos asignados a la estrategia (default 50)")
    max_auto_attaches_per_hour: Optional[int] = Field(default=None, ge=0, le=100, description="Máximo auto-attachs por hora (default 10)")
    auto_attach_dry_run: Optional[bool] = Field(default=False, description="Si True, solo loguea qué se habría asignado, no crea StrategyEvent")


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
    universe_config: Optional[UniverseConfig] = Field(default=None, description="Configuración del universe")
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
    universe_config: Optional[UniverseConfig] = None
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
    universe_config: Dict[str, Any]
    pinned_node_versions: Optional[Dict[str, str]]
    created_by: Optional[str]
    tags: Optional[List[str]]
    version: int
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


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
        "universe_config": strategy.universe_config or {},
        "pinned_node_versions": strategy.pinned_node_versions,
        "created_by": strategy.created_by,
        "tags": strategy.tags,
        "version": strategy.version,
        "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
        "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
    }


def strategy_to_summary_dict(strategy: Strategy) -> Dict[str, Any]:
    """Resumen ligero para listados (sin grafos ni configs pesadas)."""
    return {
        "id": str(strategy.id),
        "name": strategy.name,
        "description": strategy.description,
        "is_active": strategy.is_active,
        "version": strategy.version,
        "tags": strategy.tags,
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


@router.get("/summary")
async def list_strategies_summary(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista estrategias en formato ligero (sin grafos) para listados y sidebar. Mucho más rápido."""
    query = db.query(Strategy)
    if is_active is not None:
        query = query.filter(Strategy.is_active == is_active)
    if search:
        query = query.filter(Strategy.name.ilike(f"%{search}%"))
    strategies = query.order_by(Strategy.created_at.desc()).all()
    return [strategy_to_summary_dict(s) for s in strategies]


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
        universe_config=strategy_data.universe_config.model_dump() if strategy_data.universe_config else {},
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
    if strategy_data.universe_config is not None:
        strategy.universe_config = strategy_data.universe_config.model_dump()
    if strategy_data.pinned_node_versions is not None:
        strategy.pinned_node_versions = strategy_data.pinned_node_versions
    if strategy_data.tags is not None:
        strategy.tags = strategy_data.tags
    
    db.commit()
    db.refresh(strategy)
    
    return strategy_to_dict(strategy)


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Elimina una estrategia y sus datos asociados (eventos, intents, etc.)."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    if strategy.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Detén la estrategia antes de eliminarla"
        )
    db.delete(strategy)
    db.commit()
    logger.info("Strategy %s deleted by user %s", strategy_id, current_user.id)
    return None


@router.get("/{strategy_id}/universe")
async def get_strategy_universe(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene la configuración del universe de una estrategia.
    
    El universe define qué categorías, markets, tags y events la estrategia observa.
    Phase 2: incluye time_filter y events[]; precedencia: enabled global > deny_list > selectors.
    """
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    universe = strategy.universe_config or {}
    time_filter = universe.get("time_filter")
    return {
        "strategy_id": str(strategy_id),
        "universe": {
            "categories": universe.get("categories", []),
            "markets": universe.get("markets", []),
            "tags": universe.get("tags", []),
            "events": universe.get("events", []),
            "time_filter": time_filter,
            "auto_attach": universe.get("auto_attach", False),
            "deny_list": universe.get("deny_list", []),
            "max_events_per_strategy": universe.get("max_events_per_strategy"),
            "max_auto_attaches_per_hour": universe.get("max_auto_attaches_per_hour"),
            "auto_attach_dry_run": universe.get("auto_attach_dry_run", False),
        }
    }


@router.put("/{strategy_id}/universe")
async def update_strategy_universe(
    strategy_id: UUID,
    universe_config: UniverseConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """
    Actualiza la configuración del universe de una estrategia.
    
    El universe define qué categorías, markets, tags y events la estrategia observa.
    Phase 2: solo se permiten markets/events con enabled global; si no, 400.
    Precedencia: enabled global > deny_list > selectors.
    """
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Validar enabled global (Phase 2)
    market_ids = list(universe_config.markets or [])
    event_ids = list(universe_config.events or [])
    ok, not_enabled_markets, not_enabled_events = _validate_universe_enabled_global(db, market_ids, event_ids)
    if not ok:
        detail = "Referenced markets or events are not enabled global."
        if not_enabled_markets:
            detail += f" Markets not enabled: {not_enabled_markets}."
        if not_enabled_events:
            detail += f" Events (or their markets) not enabled: {not_enabled_events}."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    
    strategy.universe_config = universe_config.model_dump()
    
    db.commit()
    db.refresh(strategy)
    
    logger.info("Updated universe for strategy %s", strategy_id)
    
    return {
        "strategy_id": str(strategy_id),
        "universe": strategy.universe_config,
        "message": "Universe updated successfully"
    }


@router.post("/{strategy_id}/activate", response_model=StrategyResponse)
async def activate_strategy(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """
    Activa una estrategia.
    
    Al activar:
    - Marca la estrategia como activa en DB
    - Suscribe a orderbooks de todos los asset_ids de su universe
    - El Control Loop detectará automáticamente la estrategia activa
    """
    logger.info("Activating strategy %s (request from user)", strategy_id)
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
    
    # Suscribir a orderbooks de todos los asset_ids de la estrategia
    try:
        from app.core.orderbook.service import get_orderbook_service
        from app.core.strategy_engine.state_cache_service import StateCacheService
        
        orderbook_service = get_orderbook_service(StateCacheService(db))
        asset_ids = _get_asset_ids_from_strategy(strategy_id, db)
        
        owner_key = f"strategy_{strategy_id}"
        for asset_id in asset_ids:
            orderbook_service.subscribe(asset_id, owner_key)
            logger.info(f"Subscribed strategy {strategy_id} to asset_id={asset_id}")
        
        if asset_ids:
            logger.info(f"Strategy {strategy_id} subscribed to {len(asset_ids)} asset_ids")
        else:
            logger.warning(f"Strategy {strategy_id} has no asset_ids to subscribe to")
    except Exception as e:
        logger.error(f"Error subscribing to orderbooks for strategy {strategy_id}: {e}", exc_info=True)
        # No fallar la activación si hay error en suscripción, solo loguear
    
    strategy.is_active = True
    strategy.enabled_at = datetime.now(timezone.utc)
    strategy.disabled_at = None
    
    db.commit()
    db.refresh(strategy)

    # Evento de observabilidad (§5 SPEC)
    logger.info(
        "strategy_activated",
        extra={
            "event": "strategy_activated",
            "strategy_id": str(strategy_id),
            "component": "strategies_api",
        },
    )
    
    return strategy_to_dict(strategy)


@router.post("/{strategy_id}/deactivate", response_model=StrategyResponse)
async def deactivate_strategy(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """
    Desactiva una estrategia.
    
    Al desactivar:
    - Marca la estrategia como inactiva en DB
    - Desuscribe de orderbooks de todos los asset_ids
    - Cancela órdenes pendientes asociadas a la estrategia
    """
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
    
    # Desuscribir de orderbooks
    try:
        from app.core.orderbook.service import get_orderbook_service
        from app.core.strategy_engine.state_cache_service import StateCacheService
        
        orderbook_service = get_orderbook_service(StateCacheService(db))
        asset_ids = _get_asset_ids_from_strategy(strategy_id, db)
        
        owner_key = f"strategy_{strategy_id}"
        for asset_id in asset_ids:
            orderbook_service.unsubscribe(asset_id, owner_key)
            logger.info(f"Unsubscribed strategy {strategy_id} from asset_id={asset_id}")
        
        if asset_ids:
            logger.info(f"Strategy {strategy_id} unsubscribed from {len(asset_ids)} asset_ids")
    except Exception as e:
        logger.error(f"Error unsubscribing from orderbooks for strategy {strategy_id}: {e}", exc_info=True)
        # No fallar la desactivación si hay error, solo loguear
    
    # Cancelar órdenes pendientes asociadas a la estrategia
    try:
        from app.models.order import Order
        from app.core.execution.polymarket_client_wrapper import get_polymarket_client
        
        # Obtener markets de eventos asignados a esta estrategia
        strategy_events = db.query(StrategyEvent).filter(
            StrategyEvent.strategy_id == strategy_id
        ).all()
        
        event_ids = [se.event_id for se in strategy_events]
        if event_ids:
            # Obtener markets de estos eventos
            events = db.query(Event).filter(Event.id.in_(event_ids)).all()
            market_ids = [event.market_id for event in events]
            
            if market_ids:
                pending_orders = db.query(Order).filter(
                    Order.market_id.in_(market_ids),
                    Order.status.in_(["NEW", "PARTIALLY_FILLED"])
                ).all()
                
                if pending_orders:
                    client_wrapper = get_polymarket_client()
                    if client_wrapper.is_available():
                        for order in pending_orders:
                            try:
                                if order.polymarket_order_id:
                                    await client_wrapper.cancel_order(order.polymarket_order_id)
                                    logger.info(f"Cancelled order {order.id} (polymarket_id: {order.polymarket_order_id})")
                            except Exception as e:
                                logger.warning(f"Error cancelling order {order.id}: {e}")
                        
                        logger.info(f"Cancelled {len(pending_orders)} pending orders for strategy {strategy_id}")
    except Exception as e:
        logger.error(f"Error cancelling orders for strategy {strategy_id}: {e}", exc_info=True)
        # No fallar la desactivación si hay error cancelando órdenes
    
    strategy.is_active = False
    strategy.disabled_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(strategy)

    # Evento de observabilidad (§5 SPEC)
    logger.info(
        "strategy_deactivated",
        extra={
            "event": "strategy_deactivated",
            "strategy_id": str(strategy_id),
            "component": "strategies_api",
        },
    )
    
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
    """
    Obtiene las ejecuciones de una estrategia.
    
    Retorna Execution Plans (planes de ejecución) con estado, legs y fills.
    """
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Obtener Execution Plans
    query = db.query(ExecutionPlan).filter(
        ExecutionPlan.strategy_id == strategy_id
    )
    
    total = query.count()
    plans = query.order_by(ExecutionPlan.created_at.desc()).limit(limit).offset(offset).all()
    
    result = []
    for plan in plans:
        # Obtener fills de órdenes asociadas a este plan
        # Nota: Por ahora los Execution Plans no tienen relación directa con Orders
        # Se puede mejorar en el futuro con una tabla de relación
        
        plan_data = {
            "plan_id": str(plan.id),
            "event_id": str(plan.event_id),
            "status": plan.status,
            "legs": plan.legs or [],
            "ttl_ms": plan.ttl_ms,
            "expires_at": plan.expires_at.isoformat() if plan.expires_at else None,
            "is_expired": plan.is_expired() if hasattr(plan, 'is_expired') else False,
            "ready_for_execution": plan.ready_for_execution,
            "queued_at": plan.queued_at.isoformat() if plan.queued_at else None,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "trace_id": str(plan.trace_id) if plan.trace_id else None,
        }
        
        result.append(plan_data)
    
    return {"executions": result, "total": total}


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


@router.get("/{strategy_id}/positions")
async def get_strategy_positions(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene las posiciones abiertas de una estrategia.
    
    Filtra posiciones por markets de eventos asignados a la estrategia.
    """
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Obtener markets de eventos asignados a la estrategia
    strategy_events = db.query(StrategyEvent).filter(
        StrategyEvent.strategy_id == strategy_id
    ).all()
    
    event_ids = [se.event_id for se in strategy_events]
    if not event_ids:
        return {"positions": []}
    
    # Obtener markets de estos eventos
    events = db.query(Event).filter(Event.id.in_(event_ids)).all()
    market_ids = [event.market_id for event in events]
    
    if not market_ids:
        return {"positions": []}
    
    # Obtener posiciones de estos markets
    from app.models.position import Position
    
    positions = db.query(Position).filter(
        Position.market_id.in_(market_ids)
    ).all()
    
    result = []
    for position in positions:
        market = position.market
        if not market:
            continue
        
        # Calcular PnL no realizado
        # Market no tiene last_price, usar 0.0 como valor por defecto
        current_price = 0.0
        cost_total = position.size * position.avg_price
        theoretical_value = position.size * current_price
        unrealized_pnl = theoretical_value - cost_total
        
        result.append({
            "position_id": str(position.id),
            "market_id": str(position.market_id),
            "polymarket_id": market.polymarket_id,
            "name": market.name,
            "size": position.size,
            "avg_price": position.avg_price,
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
            "resolved": position.resolved,
            "payout": position.payout,
            "created_at": position.created_at.isoformat() if position.created_at else None,
        })
    
    return {"positions": result}


@router.get("/{strategy_id}/live-status")
async def get_strategy_live_status(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene el estado en tiempo real de una estrategia.
    
    Retorna:
    - Estado de estrategia (active/paused/stopped)
    - Métricas: exposición, PnL, órdenes activas
    - Precheck failures (últimos 10)
    - Eventos recientes (últimos 20)
    - Orderbook health por asset_id
    """
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Estado básico
    status_info = {
        "strategy_id": str(strategy_id),
        "name": strategy.name,
        "is_active": strategy.is_active,
        "enabled_at": strategy.enabled_at.isoformat() if strategy.enabled_at else None,
        "disabled_at": strategy.disabled_at.isoformat() if strategy.disabled_at else None,
    }
    
    # Métricas básicas
    metrics = {
        "total_intents": 0,
        "approved_intents": 0,
        "executed_intents": 0,
        "total_exposure_usdc": 0.0,
        "total_pnl_usdc": 0.0,
    }
    
    # Obtener métricas desde StrategyMetric (último período)
    latest_metric = db.query(StrategyMetric).filter(
        StrategyMetric.strategy_id == strategy_id
    ).order_by(StrategyMetric.period_start.desc()).first()
    
    if latest_metric:
        metrics.update({
            "total_intents": latest_metric.total_intents or 0,
            "approved_intents": latest_metric.approved_intents or 0,
            "executed_intents": latest_metric.executed_intents or 0,
            "total_exposure_usdc": float(latest_metric.total_exposure_usdc) if latest_metric.total_exposure_usdc else 0.0,
            "total_pnl_usdc": float(latest_metric.total_pnl_usdc) if latest_metric.total_pnl_usdc else 0.0,
        })
    
    # Órdenes activas (Order tiene market_id; eventos de la estrategia → markets)
    from app.models.order import Order
    strategy_events = db.query(StrategyEvent).filter(
        StrategyEvent.strategy_id == strategy_id
    ).all()
    event_ids = [se.event_id for se in strategy_events]
    market_ids = []
    if event_ids:
        events_for_markets = db.query(Event).filter(Event.id.in_(event_ids)).all()
        market_ids = [e.market_id for e in events_for_markets]
    active_orders_count = 0
    if market_ids:
        active_orders_count = db.query(Order).filter(
            Order.market_id.in_(market_ids),
            Order.status.in_(["NEW", "PARTIALLY_FILLED"])
        ).count()
    
    metrics["active_orders"] = active_orders_count
    
    # Precheck failures (últimos 10)
    # Nota: Los precheck failures se registran como métricas Prometheus
    # Por ahora retornamos lista vacía, se puede mejorar consultando métricas
    precheck_failures = []
    
    # Execution Plans recientes (últimos 20)
    recent_plans = db.query(ExecutionPlan).filter(
        ExecutionPlan.strategy_id == strategy_id
    ).order_by(ExecutionPlan.created_at.desc()).limit(20).all()
    
    plans_data = []
    for plan in recent_plans:
        plans_data.append({
            "plan_id": str(plan.id),
            "event_id": str(plan.event_id),
            "status": plan.status,
            "legs_count": len(plan.legs) if plan.legs else 0,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "expires_at": plan.expires_at.isoformat() if plan.expires_at else None,
            "is_expired": plan.is_expired() if hasattr(plan, 'is_expired') else False,
        })
    
    # Orderbook health por asset_id
    orderbook_health = {}
    try:
        from app.core.orderbook.service import get_orderbook_service
        from app.core.strategy_engine.state_cache_service import StateCacheService
        
        orderbook_service = get_orderbook_service(StateCacheService(db))
        asset_ids = _get_asset_ids_from_strategy(strategy_id, db)
        
        for asset_id in asset_ids:
            book = orderbook_service.get_book(asset_id)
            if book:
                state = book.get_state()
                if state:
                    orderbook_health[asset_id] = {
                        "has_data": True,
                        "staleness_ms": state.staleness_ms,
                        "best_bid_price": float(state.best_bid_price) if state.best_bid_price else None,
                        "best_ask_price": float(state.best_ask_price) if state.best_ask_price else None,
                        "spread_bps": float(state.spread_bps) if state.spread_bps else None,
                    }
                else:
                    orderbook_health[asset_id] = {"has_data": False}
            else:
                orderbook_health[asset_id] = {"has_data": False}
    except Exception as e:
        logger.warning(f"Error getting orderbook health for strategy {strategy_id}: {e}")
    
    return {
        "status": status_info,
        "metrics": metrics,
        "precheck_failures": precheck_failures,
        "recent_plans": plans_data,
        "orderbook_health": orderbook_health,
    }


@router.get("/{strategy_id}/logs")
async def get_strategy_logs(
    strategy_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Devuelve actividad reciente de la estrategia para la sección Logs de la UI.
    Incluye planes de ejecución e intents recientes convertidos a entradas de log.
    """
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )

    logs: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    def _add(log_id: str, ts: datetime, level: str, message: str) -> None:
        key = f"{log_id}_{ts.isoformat()}"
        if key in seen:
            return
        seen.add(key)
        logs.append({
            "id": log_id,
            "timestamp": ts.isoformat() if ts.tzinfo else ts.replace(tzinfo=timezone.utc).isoformat(),
            "level": level,
            "message": message,
        })

    # Planes de ejecución recientes
    plans = (
        db.query(ExecutionPlan)
        .filter(ExecutionPlan.strategy_id == strategy_id)
        .order_by(ExecutionPlan.created_at.desc())
        .limit(limit)
        .all()
    )
    for plan in plans:
        ts = plan.created_at or datetime.now(timezone.utc)
        if getattr(ts, "tzinfo", None) is None:
            ts = ts.replace(tzinfo=timezone.utc)
        status_val = (plan.status or "").upper()
        if status_val in ("FAILED", "EXPIRED", "CANCELLED", "REJECTED"):
            level = "error"
        elif status_val in ("PENDING", "QUEUED", "PARTIAL"):
            level = "warning"
        else:
            level = "info"
        msg = f"Plan {plan.id} — {plan.status or 'unknown'} (event: {plan.event_id})"
        _add(f"plan-{plan.id}", ts, level, msg)

    # Intents recientes (órdenes/intenciones)
    intents = (
        db.query(ExecutionIntent)
        .filter(ExecutionIntent.strategy_id == strategy_id)
        .order_by(ExecutionIntent.created_at.desc())
        .limit(limit)
        .all()
    )
    for intent in intents:
        ts = intent.created_at if intent.created_at else datetime.now(timezone.utc)
        if hasattr(ts, "replace") and getattr(ts, "tzinfo", None) is None:
            ts = ts.replace(tzinfo=timezone.utc)
        status_val = (intent.status or "").upper()
        if status_val == "REJECTED":
            level = "error"
            msg = f"Intent rechazado — {(intent.rejection_reason or 'sin motivo')}"
        elif status_val == "EXECUTED":
            level = "info"
            size_usdc = float(intent.size_usdc) if intent.size_usdc is not None else 0
            price = float(intent.target_price) if intent.target_price is not None else 0
            msg = f"Orden ejecutada — {size_usdc:.2f} USDC @ {price:.4f}"
        elif status_val == "APPROVED":
            level = "info"
            msg = "Intent aprobado por Risk Engine"
        else:
            level = "info"
            msg = f"Intent {intent.status or 'pending'}"
        _add(f"intent-{intent.id}", ts, level, msg)

    # Ordenar por timestamp descendente y limitar
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return logs[:limit]


class SimulationRequest(BaseModel):
    """Modelo de request para simulación."""
    duration_seconds: int = Field(default=3600, ge=60, le=86400, description="Duración de simulación (seg)")
    capital_usdc: float = Field(default=10000.0, ge=100, le=1000000, description="Capital disponible (USDC)")
    fill_mode: str = Field(default="conservative", description="Modo de fill: 'conservative' o 'realistic'")


@router.post("/{strategy_id}/simulate")
async def simulate_strategy(
    strategy_id: UUID,
    request: SimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ejecuta una simulación de la estrategia.
    
    Simula cómo se comportaría la estrategia con los orderbooks actuales,
    sin ejecutar órdenes reales.
    
    Parámetros:
    - duration_seconds: Duración de la simulación (60-86400 seg)
    - capital_usdc: Capital disponible para la simulación (100-1000000 USDC)
    - fill_mode: "conservative" (solo best level) o "realistic" (barre niveles)
    
    Retorna:
    - estimated_pnl: PnL estimado
    - orders_executed: Número de órdenes ejecutadas
    - fills_breakdown: Detalle de cada fill
    """
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Validar fill_mode
    from app.core.strategy_engine.simulation_engine import SimExecutionEngine, FillMode
    
    try:
        fill_mode = FillMode(request.fill_mode)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid fill_mode. Must be 'conservative' or 'realistic'"
        )
    
    # Crear simulation engine
    from app.core.strategy_engine.state_cache_service import StateCacheService
    
    state_cache = StateCacheService(db)
    sim_engine = SimExecutionEngine(state_cache)
    
    # Ejecutar simulación
    try:
        result = await sim_engine.simulate(
            strategy=strategy,
            db=db,
            duration_seconds=request.duration_seconds,
            capital_usdc=request.capital_usdc,
            fill_mode=fill_mode,
        )
        
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"Simulation failed for strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}"
        )

