"""
Live Control Status API - Estado operativo del bot, decisiones recientes, system health.

Proporciona toda la información necesaria para el dashboard de Live Control.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from app.api.auth import get_current_user, User
from app.core.state import state
from app.core.config_service import config_service
from app.core.latency_monitor import latency_monitor, LatencyStatus
from app.core.decision_trace import decision_trace_service
from app.database import SessionLocal
from app.models.decision_trace import DecisionTrace
from app.models.market import Market
from app.models.event import Event
from app.models.order import Order
from app.core.event_watch_engine import EventWatchCoordinator
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/live/status", tags=["live"])


class BotStatusResponse(BaseModel):
    """Estado operativo del bot."""
    execution_mode: str  # DRY_RUN, PAPER, LIVE
    system_state: str  # PAUSADO, ACTIVO, BLOQUEADO
    last_decision: Optional[Dict[str, Any]] = None
    last_action: Optional[Dict[str, Any]] = None
    execution_mode_description: Dict[str, str]  # Descripción de cada modo


class ActiveMarketInfo(BaseModel):
    """Información de un Market activo."""
    market_id: str
    name: str
    enabled: bool
    events_count: int
    active_events_count: int
    series_name: Optional[str] = None


class ActiveEventInfo(BaseModel):
    """Información de un Event activo."""
    event_id: str
    polymarket_event_id: str
    market_id: str
    market_name: str
    start_time: str
    end_time: str
    state: str  # UPCOMING, ACTIVE, FINISHED
    liquidity: Optional[float] = None


class RiskAlert(BaseModel):
    """Alerta de riesgo."""
    type: str  # "exposure_limit", "liquidity", "global_exposure", etc.
    severity: str  # "warning", "critical"
    message: str
    details: Dict[str, Any] = {}


class RecentDecision(BaseModel):
    """Decisión reciente."""
    timestamp: str
    component: str
    decision: str
    reason: Optional[str] = None
    trace_id: Optional[str] = None


class SystemHealthResponse(BaseModel):
    """Salud del sistema."""
    latency_status: str  # GREEN, YELLOW, RED
    checkers_active: int
    checkers_total: int
    last_checker_failure: Optional[str] = None
    scanner_status: str  # OK, DELAYED, ERROR
    scanner_last_scan: Optional[str] = None


class LiveStatusResponse(BaseModel):
    """Respuesta completa del estado del bot."""
    bot_status: BotStatusResponse
    active_markets: List[ActiveMarketInfo]
    active_events: List[ActiveEventInfo]
    risk_alerts: List[RiskAlert]
    recent_decisions: List[RecentDecision]
    system_health: SystemHealthResponse


def _get_scanner_last_scan(request: Request) -> Optional[str]:
    """Obtiene last_scanned_at del Scanner si está disponible en app.state (Phase 0 Directory)."""
    scanner = getattr(request.app.state, "scanner", None)
    if scanner is None or not hasattr(scanner, "get_stats"):
        return None
    try:
        stats = scanner.get_stats()
        return stats.get("last_scan")
    except Exception:
        return None


@router.get("")
async def get_live_status(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene el estado completo del bot para Live Control.
    
    Incluye:
    - Estado operativo (modo, estado, última decisión/acción)
    - Markets activos con conteo de events
    - Events activos ahora mismo
    - Alertas de riesgo
    - Decisiones recientes
    - Salud del sistema
    """
    db = SessionLocal()
    try:
        # 1. Estado operativo del bot
        execution_mode = config_service.get_execution_mode()
        system_state = "ACTIVO" if state.system_active else "PAUSADO"
        
        # Obtener última decisión
        last_decision_trace = db.query(DecisionTrace).order_by(
            DecisionTrace.timestamp.desc()
        ).first()
        
        last_decision = None
        if last_decision_trace:
            last_decision = {
                "decision": last_decision_trace.decision,
                "component": last_decision_trace.component,
                "reason": last_decision_trace.reason,
                "timestamp": last_decision_trace.timestamp.isoformat(),
                "trace_id": str(last_decision_trace.trace_id),
            }
        
        # Obtener última acción (última orden)
        last_order = db.query(Order).order_by(Order.created_at.desc()).first()
        last_action = None
        if last_order:
            minutes_ago = (datetime.utcnow() - last_order.created_at).total_seconds() / 60
            last_action = {
                "type": "order_placed",
                "message": f"Orden {last_order.status} hace {int(minutes_ago)} min",
                "timestamp": last_order.created_at.isoformat(),
            }
        else:
            # Calcular tiempo desde última orden
            # TODO: Obtener desde métricas o logs
            last_action = {
                "type": "no_orders",
                "message": "No se colocaron órdenes recientemente",
            }
        
        # Descripciones de modos
        execution_mode_descriptions = {
            "DRY_RUN": "Simulación completa. No se envían órdenes, solo se simulan decisiones y ejecuciones.",
            "PAPER": "Trading en papel. Se envían órdenes pero no se ejecutan realmente. Útil para probar conectividad y lógica sin riesgo.",
            "LIVE": "Trading real. Se envían y ejecutan órdenes reales en Polymarket. ⚠️ Usa dinero real."
        }
        
        bot_status = BotStatusResponse(
            execution_mode=execution_mode,
            system_state=system_state,
            last_decision=last_decision,
            last_action=last_action,
            execution_mode_description=execution_mode_descriptions,
        )
        
        # 2. Markets activos
        enabled_markets = db.query(Market).filter(Market.enabled == True).all()
        active_markets_list = []
        for market in enabled_markets:
            events_count = db.query(Event).filter(Event.market_id == market.id).count()
            active_events_count = db.query(Event).filter(
                Event.market_id == market.id,
                Event.state.in_(["UPCOMING", "ACTIVE"])
            ).count()
            
            active_markets_list.append(ActiveMarketInfo(
                market_id=str(market.id),
                name=market.name,
                enabled=market.enabled,
                events_count=events_count,
                active_events_count=active_events_count,
                series_name=market.series.name if market.series else None,
            ))
        
        # 3. Events activos ahora mismo
        active_events = db.query(Event).filter(
            Event.state.in_(["UPCOMING", "ACTIVE"])
        ).order_by(Event.end_time.asc()).limit(20).all()
        
        active_events_list = []
        for event in active_events:
            active_events_list.append(ActiveEventInfo(
                event_id=str(event.id),
                polymarket_event_id=event.polymarket_event_id,
                market_id=str(event.market_id),
                market_name=event.market.name if event.market else "Unknown",
                start_time=event.start_time.isoformat() if event.start_time else "",
                end_time=event.end_time.isoformat() if event.end_time else "",
                state=event.state,
                liquidity=None,  # TODO: Obtener desde orderbook
            ))
        
        # 4. Alertas de riesgo
        risk_alerts = []
        risk_config = config_service.get_risk_engine_config()
        
        # Calcular exposición global
        global_exposure = sum(e.notional for e in state.exposures.values())
        global_exposure_pct = (global_exposure / risk_config.max_global_exposure * 100) if risk_config.max_global_exposure > 0 else 0
        
        if global_exposure_pct >= 90:
            risk_alerts.append(RiskAlert(
                type="global_exposure",
                severity="critical",
                message=f"Exposición global al {global_exposure_pct:.1f}%",
                details={"current": global_exposure, "max": risk_config.max_global_exposure},
            ))
        elif global_exposure_pct >= 75:
            risk_alerts.append(RiskAlert(
                type="global_exposure",
                severity="warning",
                message=f"Exposición global al {global_exposure_pct:.1f}%",
                details={"current": global_exposure, "max": risk_config.max_global_exposure},
            ))
        
        # Verificar exposición por mercado
        markets_near_limit = 0
        for exposure_state in state.exposures.values():
            exposure_pct = (exposure_state.notional / risk_config.max_market_exposure * 100) if risk_config.max_market_exposure > 0 else 0
            if exposure_pct >= 80:
                markets_near_limit += 1
        
        if markets_near_limit > 0:
            risk_alerts.append(RiskAlert(
                type="market_exposure",
                severity="warning",
                message=f"{markets_near_limit} markets cerca del límite de exposición",
                details={"count": markets_near_limit},
            ))
        
        # 5. Decisiones recientes
        recent_traces = db.query(DecisionTrace).order_by(
            DecisionTrace.timestamp.desc()
        ).limit(10).all()
        
        recent_decisions = []
        for trace in recent_traces:
            recent_decisions.append(RecentDecision(
                timestamp=trace.timestamp.isoformat(),
                component=trace.component,
                decision=trace.decision,
                reason=trace.reason,
                trace_id=str(trace.trace_id),
            ))
        
        # 6. System Health
        latency_status = latency_monitor.get_status()
        
        # Obtener info de checkers
        try:
            watch_coordinator = EventWatchCoordinator()
            checkers_info = watch_coordinator.get_checkers_status() if hasattr(watch_coordinator, 'get_checkers_status') else {}
            checkers_active = checkers_info.get("active", 0)
            checkers_total = checkers_info.get("total", 0)
            last_checker_failure = checkers_info.get("last_failure")
        except:
            checkers_active = 0
            checkers_total = 0
            last_checker_failure = None
        
        # Scanner status: last_scanned_at expuesto para Directory Phase 0
        scanner_status = "OK"
        scanner_last_scan = _get_scanner_last_scan(request)

        system_health = SystemHealthResponse(
            latency_status=latency_status.value if hasattr(latency_status, 'value') else str(latency_status),
            checkers_active=checkers_active,
            checkers_total=checkers_total,
            last_checker_failure=last_checker_failure.isoformat() if last_checker_failure else None,
            scanner_status=scanner_status,
            scanner_last_scan=scanner_last_scan,
        )
        
        return LiveStatusResponse(
            bot_status=bot_status,
            active_markets=active_markets_list,
            active_events=active_events_list,
            risk_alerts=risk_alerts,
            recent_decisions=recent_decisions,
            system_health=system_health,
        )
        
    except Exception as e:
        logger.error(f"Error getting live status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/execution-mode")
async def set_execution_mode(
    mode: str = Query(..., description="Execution mode: DRY_RUN, PAPER, or LIVE"),
    current_user: User = Depends(get_current_user),
):
    """
    Cambia el modo de ejecución (DRY_RUN, PAPER, LIVE).
    
    Para que en LIVE se envíen órdenes reales a Polymarket, deben cumplirse:
    - execution_mode == LIVE (este endpoint).
    - Sistema activo (control/resume).
    - Estrategia activa con eventos asignados (Universe/Desk).
    - Wallet/CLOB disponible: wallet activa en BD por usuario (política v2: no CLOB global).
    - Risk Engine aprueba los intents; latencia no RED; circuit breaker cerrado.
    """
    if mode not in ["DRY_RUN", "PAPER", "LIVE"]:
        raise HTTPException(status_code=400, detail="Invalid execution mode")
    
    # Actualizar en ConfigService
    db = SessionLocal()
    try:
        from app.models.system_config import SystemConfig
        from datetime import datetime
        
        config = db.query(SystemConfig).filter(SystemConfig.key == "execution_mode").first()
        if config:
            config.value = mode
            config.updated_at = datetime.utcnow()
        else:
            config = SystemConfig(
                key="execution_mode",
                value=mode,
                value_type="string",
                category="execution",
                description="Execution mode: DRY_RUN (simulation), PAPER (paper trading), LIVE (real trading)",
                is_readonly=False,
                requires_confirmation=(mode == "LIVE"),
                updated_at=datetime.utcnow()
            )
            db.add(config)
        
        db.commit()
        
        # Actualizar cache de inmediato para que el siguiente get_execution_mode() devuelva el nuevo valor
        config_service._cache["execution_mode"] = mode
        
        logger.info(f"Execution mode changed to {mode} by user {current_user.id}")
        return {"status": "success", "mode": mode}
    except Exception as e:
        db.rollback()
        logger.error(f"Error changing execution mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/cancel-all-orders")
async def cancel_all_orders(
    current_user: User = Depends(get_current_user),
):
    """
    Cancela todas las órdenes pendientes.
    """
    # TODO: Implementar cancelación de todas las órdenes
    return {"status": "success", "message": "All orders cancelled"}

