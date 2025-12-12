"""
History API endpoints.

Incluye endpoints para Historical Replay según especificación en docs/services/historical_replay.md
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, Path, Body
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models.trade import Trade
from app.models.market import Market
from app.models.position import Position
from app.api.auth import get_current_user
from app.api.auth import User
from app.core.historical_replay import EventStore, ReplayEngine, StrategyComparator

router = APIRouter(prefix="/history", tags=["history"])

# Instancias globales (se inicializarán en startup)
event_store: Optional[EventStore] = None
replay_engine: Optional[ReplayEngine] = None
strategy_comparator: Optional[StrategyComparator] = None


def get_event_store() -> EventStore:
    """Obtiene instancia de EventStore."""
    global event_store
    if event_store is None:
        event_store = EventStore(storage_type="sqlite")
    return event_store


def get_replay_engine() -> ReplayEngine:
    """Obtiene instancia de ReplayEngine."""
    global replay_engine
    if replay_engine is None:
        replay_engine = ReplayEngine(get_event_store())
    return replay_engine


def get_strategy_comparator() -> StrategyComparator:
    """Obtiene instancia de StrategyComparator."""
    global strategy_comparator
    if strategy_comparator is None:
        strategy_comparator = StrategyComparator(
            get_event_store(),
            get_replay_engine()
        )
    return strategy_comparator


@router.get("/trades")
async def get_trades(
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get historical trades (paginated)."""
    query = db.query(Trade).join(Market).order_by(Trade.timestamp.desc())
    
    if cursor:
        # Parse cursor and filter
        # TODO: Implement proper cursor-based pagination
        pass
    
    trades = query.limit(limit).all()
    
    items = [
        {
            "trade_id": str(trade.id),
            "market_id": str(trade.market_id),
            "polymarket_id": trade.market.polymarket_id,
            "fill_price": trade.fill_price,
            "fill_size": trade.fill_size,
            "direction": trade.direction,
            "timestamp": trade.timestamp.isoformat(),
        }
        for trade in trades
    ]
    
    return {
        "items": items,
        "next_cursor": None,  # TODO: Implement cursor
    }


@router.get("/markets")
async def get_markets_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get PnL summary by market."""
    # Get resolved markets with positions
    positions = db.query(Position).filter(Position.resolved == True).all()
    
    result = []
    for position in positions:
        market = position.market
        
        # Calculate cost and payout
        cost_total = position.size * position.avg_price
        payout_total = position.payout or 0.0
        realized_pnl = payout_total - cost_total
        
        result.append({
            "market_id": str(position.market_id),
            "polymarket_id": market.polymarket_id,
            "question": market.question,
            "outcome": market.outcome,
            "resolved": True,
            "resolution_outcome": market.resolution_outcome,
            "cost_total": cost_total,
            "payout_total": payout_total,
            "realized_pnl": realized_pnl,
            "resolved_at": market.resolved_at.isoformat() if market.resolved_at else None,
        })
    
    return result


@router.get("/equity")
async def get_equity_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get equity history over time."""
    # TODO: Implement equity calculation over time
    # This would require storing equity snapshots periodically
    return {
        "data": [],
        "message": "Equity history not yet implemented"
    }


# Historical Replay Endpoints

@router.get("/market/{market_id}")
async def get_market_history(
    market_id: str = Path(..., description="Market ID"),
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener historial completo de un mercado.
    
    Según especificación en docs/services/historical_replay.md
    """
    engine = get_replay_engine()
    
    start_dt = None
    end_dt = None
    
    if start_time:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    if end_time:
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    
    events = await engine.replay_market(
        market_id=market_id,
        start_time=start_dt,
        end_time=end_dt
    )
    
    # Clasificar eventos por tipo
    result = {
        "market_id": market_id,
        "events": [],
        "intents": [],
        "risk": [],
        "execution": [],
        "runtime_updates": []
    }
    
    for event in events:
        event_type = event.get("type", "")
        
        if event_type.startswith("watcher_"):
            result["events"].append(event)
        elif event_type.startswith("strategy_"):
            result["intents"].append(event)
        elif event_type.startswith("risk_"):
            result["risk"].append(event)
        elif event_type.startswith("execution_"):
            result["execution"].append(event)
        elif event_type.startswith("runtime_"):
            result["runtime_updates"].append(event)
    
    return result


@router.get("/event/{event_id}")
async def get_event_history(
    event_id: str = Path(..., description="External event ID"),
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener historial de un evento externo.
    
    Según especificación en docs/services/historical_replay.md
    """
    engine = get_replay_engine()
    
    start_dt = None
    end_dt = None
    
    if start_time:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    if end_time:
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    
    result = await engine.replay_event(
        event_id=event_id,
        start_time=start_dt,
        end_time=end_dt
    )
    
    return result


@router.get("/replay")
async def replay_timeline(
    market_id: Optional[str] = Query(None, description="Market ID"),
    event_id: Optional[str] = Query(None, description="Event ID"),
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    format: str = Query("timeline", description="Response format"),
    current_user: User = Depends(get_current_user),
):
    """
    Replay completo secuencial.
    
    Según especificación en docs/services/historical_replay.md
    """
    engine = get_replay_engine()
    
    start_dt = None
    end_dt = None
    
    if start_time:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    if end_time:
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    
    if market_id:
        events = await engine.replay_market(
            market_id=market_id,
            start_time=start_dt,
            end_time=end_dt
        )
    elif event_id:
        result = await engine.replay_event(
            event_id=event_id,
            start_time=start_dt,
            end_time=end_dt
        )
        # Flatten result into timeline
        events = []
        events.extend(result.get("mappings", []))
        events.extend(result.get("watcher_events", []))
        events.extend(result.get("checker_results", []))
        events.sort(key=lambda x: x.get("timestamp", ""))
    else:
        return {"error": "market_id or event_id required"}
    
    return events


@router.get("/rewind")
async def rewind_to_timestamp(
    timestamp: str = Query(..., description="Timestamp to rewind to (ISO format)"),
    current_user: User = Depends(get_current_user),
):
    """
    Rewind a un timestamp.
    
    Según especificación en docs/services/historical_replay.md
    """
    engine = get_replay_engine()
    
    try:
        timestamp_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return {"error": "Invalid timestamp format"}
    
    system_state = await engine.rewind_to_timestamp(timestamp_dt)
    
    return system_state


@router.get("/replay/step/{step_number}")
async def replay_step(
    step_number: int = Path(..., description="Step number (0-indexed)"),
    market_id: str = Query(..., description="Market ID"),
    current_user: User = Depends(get_current_user),
):
    """
    Replay step-by-step.
    
    Según especificación en docs/services/historical_replay.md
    """
    engine = get_replay_engine()
    
    result = await engine.replay_step_by_step(
        market_id=market_id,
        step=step_number
    )
    
    if result is None:
        return {"error": "Step not found"}
    
    return result


@router.post("/compare-strategies")
async def compare_strategies(
    request: dict = Body(...),
    current_user: User = Depends(get_current_user),
):
    """
    Comparar versiones de estrategia.
    
    Según especificación en docs/services/historical_replay.md
    """
    comparator = get_strategy_comparator()
    
    market_id = request.get("market_id")
    original_strategy_version = request.get("original_strategy_version")
    new_strategy_version = request.get("new_strategy_version")
    start_time_str = request.get("start_time")
    end_time_str = request.get("end_time")
    
    if not market_id:
        return {"error": "market_id required"}
    
    start_time = None
    end_time = None
    
    if start_time_str:
        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
    if end_time_str:
        end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
    
    # TODO: Cargar estrategias desde versiones
    # Por ahora, usamos None como placeholder
    original_strategy = None
    new_strategy = None
    
    comparison = await comparator.compare_strategies(
        market_id=market_id,
        original_strategy=original_strategy,
        new_strategy=new_strategy,
        start_time=start_time,
        end_time=end_time
    )
    
    return {
        "comparison": {
            "original_intents_count": comparison["original_intents_count"],
            "new_intents_count": comparison["new_intents_count"],
            "original_total_size": comparison["original_total_size"],
            "new_total_size": comparison["new_total_size"],
            "simulated_pnl_original": comparison["simulated_pnl_original"],
            "simulated_pnl_new": comparison["simulated_pnl_new"],
            "improvement": comparison["improvement"]
        },
        "differences": comparison["differences"]
    }

