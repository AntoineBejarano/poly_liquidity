"""
FastAPI application entry point.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.settings import settings
from app.database import SessionLocal
from app.core.state import state
from app.core.config_service import config_service
from app.core.scanner import Scanner
from app.core.event_mapping_layer import EventMappingLayer
from app.core.event_watch_engine import EventWatchCoordinator
from app.core.event_engine import EventEngine
from app.core.strategy import Strategy
from app.core.strategy.models import OrderIntent
from app.core.risk_engine import RiskEngine
from app.core.execution import Execution
from app.core.metrics import Metrics
from app.core.metrics.metrics_service import metrics_service
from app.core.runtime_supervisor import RuntimeSupervisor
from app.core.api_cache import api_cache
from app.core.latency_monitor import latency_monitor
from app.core.historical_replay import EventStore, initialize_event_store
from app.core.historical_replay.event_logger import (
    log_event, log_watcher_event, log_strategy_intent, log_risk_decision,
    log_execution_event, log_runtime_event
)
from app.core.live_control import LiveControlStore, initialize_event_bus, emit_event

# Import API routers
from app.api import markets, positions, risk, system, wallets, checkers, control, history, dashboard, websocket, metrics, live

# Import checker implementations to auto-register them
import app.core.checkers.implementations  # noqa: F401

# Initialize services
scanner = Scanner()
event_mapping_layer = EventMappingLayer()
event_watch_coordinator = EventWatchCoordinator()
event_engine = EventEngine()
strategy = Strategy()
risk_engine = RiskEngine()
execution = Execution()
metrics = Metrics()
runtime_supervisor = RuntimeSupervisor(execution_engine=execution)

# Initialize Historical Replay Event Store
event_store = EventStore(storage_type="sqlite")
initialize_event_store(event_store)

# Initialize Live Control Event Bus
live_control_store = LiveControlStore()
initialize_event_bus(live_control_store)

# Store approved intents for execution
_approved_intents = []

# Main loop task
_main_loop_task = None
_cache_cleanup_task = None


async def cache_cleanup_loop():
    """
    Periodic cache cleanup task.
    Removes expired entries to prevent memory leaks.
    """
    while state.system_active:
        try:
            await api_cache.cleanup_expired()
            # Clean up every 60 seconds
            await asyncio.sleep(60.0)
        except Exception as e:
            print(f"Error in cache cleanup: {e}")
            await asyncio.sleep(60.0)


async def main_loop():
    """
    Main event loop that orchestrates everything.
    Runs continuously while system is active.
    
    Flujo según especificación:
    Scanner → Event Mapping → Event Watch Engine → Strategy → Risk → Execution → Metrics → Runtime Supervisor
    
    Note: All Polymarket API calls are rate-limited:
    - Scanner uses Data API (200 req/10s) with caching
    - EventEngine uses external checkers (not Polymarket API directly)
    - Execution uses Trading API (2400 req/10s)
    """
    import logging
    import traceback
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    global _approved_intents
    
    tick_count = 0
    consecutive_errors = 0
    max_consecutive_errors = 10
    
    while state.system_active:
        tick_start = datetime.utcnow()
        tick_count += 1
        
        try:
            # 1. Scanner: Escanear mercados (rate-limited, cached)
            await scanner.tick()
            
            # 1.5. Limpiar watchers terminados periódicamente
            await event_watch_coordinator.cleanup_finished_watchers()
            
            # 2. Event Engine: Actualizar estado de eventos externos
            await event_engine.tick()
            
            # 3. Strategy: Decidir órdenes (respeta runtime_mode)
            intents = await strategy.tick()
            
            # Emitir eventos de Strategy al Event Bus y Historical Replay
            await metrics_service.collector.collect_strategy_metrics(len(intents))
            for intent in intents:
                # Métricas
                await metrics_service.collector.record_event(
                    "intent_created",
                    {
                        "market_id": str(intent.market_id),
                        "price": intent.price,
                        "size": intent.size,
                        "value": 1.0
                    },
                    component="strategy"
                )
                
                # Live Control Event Bus
                emit_event("strategy_intent", {
                    "market_id": str(intent.market_id),
                    "target_price": intent.price,
                    "size": intent.size,
                    "reason": intent.reason,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Historical Replay
                await log_strategy_intent(
                    market_id=str(intent.market_id),
                    target_price=intent.price,
                    size=intent.size,
                    reason=intent.reason,
                    trace_id=intent.trace_id
                )
            
            # 4. Risk Engine: Aplicar límites de riesgo (respeta runtime_mode)
            _approved_intents = await risk_engine.tick(intents)
            
            # Emitir eventos de Risk al Event Bus y Historical Replay
            approved_count = len(_approved_intents)
            rejected_count = len(intents) - approved_count
            await metrics_service.collector.collect_risk_metrics(approved_count, rejected_count)
            
            for approved in _approved_intents:
                # Live Control Event Bus
                emit_event("risk_decision", {
                    "market_id": str(approved.market_id),
                    "approved": True,
                    "final_size": approved.size,
                    "price": approved.price,
                    "reason": approved.reason,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Historical Replay
                await log_risk_decision(
                    market_id=str(approved.market_id),
                    approved=True,
                    final_size=approved.size,
                    price=approved.price,
                    trace_id=approved.trace_id
                )
            
            # 5. Execution: Enviar/cancelar órdenes (rate-limited, respeta circuit breakers)
            orders_sent = len(_approved_intents)
            orders_filled = 0
            orders_rejected = 0
            
            # Track execution metrics
            execution_start = asyncio.get_event_loop().time()
            await execution.tick(_approved_intents)
            execution_end = asyncio.get_event_loop().time()
            execution_latency_ms = (execution_end - execution_start) * 1000
            
            # Emitir métricas de Execution
            await metrics_service.collector.collect_execution_latency(execution_latency_ms)
            await metrics_service.collector.collect_execution_metrics(
                orders_sent=orders_sent,
                orders_filled=orders_filled,
                orders_rejected=orders_rejected
            )
            
            # 6. Metrics: Registrar métricas
            await metrics.tick()
            
            # 7. Runtime Supervisor: Tick (debe ir después de métricas)
            old_mode = runtime_supervisor.get_mode().value
            await runtime_supervisor.tick()
            new_mode = runtime_supervisor.get_mode().value
            
            # Emitir latencia al Live Control
            emit_event("latency_update", {
                "mode": new_mode,
                "latency_ms": execution_latency_ms,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Emitir cambio de modo si ocurrió
            if old_mode != new_mode:
                emit_event("system_health_update", {
                    "runtime_mode": new_mode,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                await log_runtime_event(
                    event_type="runtime_mode_changed",
                    from_mode=old_mode,
                    to_mode=new_mode,
                    reason="Runtime supervisor mode change"
                )
            
            # Reset error counter on success
            consecutive_errors = 0
            
            # Sleep for configured tick interval
            tick_seconds = state.risk_config.tick_seconds
            await asyncio.sleep(tick_seconds)
            
        except KeyboardInterrupt:
            # Graceful shutdown on Ctrl+C
            logger.info("Main loop interrupted by user")
            state.system_active = False
            break
            
        except Exception as e:
            # Error handling with recovery
            consecutive_errors += 1
            error_msg = f"Error in main loop (tick #{tick_count}, consecutive errors: {consecutive_errors}): {e}"
            logger.error(error_msg, exc_info=True)
            
            # Log error to Historical Replay
            await log_event(
                event_type="system_error",
                component="main_loop",
                error=str(e),
                tick_count=tick_count,
                consecutive_errors=consecutive_errors,
                traceback=traceback.format_exc()
            )
            
            # Emit error to Live Control
            emit_event("system_health_update", {
                "last_error": error_msg,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # If too many consecutive errors, pause system
            if consecutive_errors >= max_consecutive_errors:
                logger.critical(
                    f"Too many consecutive errors ({consecutive_errors}), pausing system"
                )
                state.system_active = False
                await log_runtime_event(
                    event_type="system_paused",
                    reason=f"Too many consecutive errors: {consecutive_errors}"
                )
                break
            
            # Exponential backoff on errors
            sleep_time = min(1.0 * (2 ** min(consecutive_errors, 5)), 60.0)
            await asyncio.sleep(sleep_time)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    print("Starting PolyLiquidity Desk...")
    
    # Load configuration from DB
    config_service.load_from_db()
    
    # Update state with config
    state.risk_config = config_service.get_risk_config()
    
    # Load state from DB
    db = SessionLocal()
    try:
        state.load_from_db(db)
    finally:
        db.close()
    
    # Start metrics service
    await metrics_service.start()
    
    # Start main loop in background
    global _main_loop_task, _cache_cleanup_task
    state.system_active = True
    _main_loop_task = asyncio.create_task(main_loop())
    _cache_cleanup_task = asyncio.create_task(cache_cleanup_loop())
    
    print("PolyLiquidity Desk started")
    
    yield
    
    # Shutdown
    print("Shutting down PolyLiquidity Desk...")
    state.system_active = False
    
    # Wait for main loop to finish
    if _main_loop_task:
        _main_loop_task.cancel()
        try:
            await _main_loop_task
        except asyncio.CancelledError:
            pass
    
    # Wait for cache cleanup to finish
    if _cache_cleanup_task:
        _cache_cleanup_task.cancel()
        try:
            await _cache_cleanup_task
        except asyncio.CancelledError:
            pass
    
    # Stop metrics service
    await metrics_service.stop()
    
    # Close services
    await scanner.close()
    await execution.close()
    await latency_monitor.close()
    
    # Close Event Store
    event_store.close()
    
    # Stop all watchers
    from app.core.live_watchers import watcher_manager
    await watcher_manager.stop_all()
    
    print("PolyLiquidity Desk stopped")


app = FastAPI(
    title="PolyLiquidity Desk API",
    description="API para gestión de liquidez en Polymarket",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routers
app.include_router(markets.router)
app.include_router(positions.router)
app.include_router(risk.router)
app.include_router(system.router)
app.include_router(wallets.router)
app.include_router(checkers.router)
app.include_router(control.router)
app.include_router(history.router)
app.include_router(dashboard.router)
app.include_router(websocket.router)
app.include_router(metrics.router)
app.include_router(live.router)
app.include_router(runtime.router)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Also measures backend latency (Front → Backend → Front).
    This is used by the latency monitor to track backend performance.
    """
    import time
    start = time.monotonic_ns()
    
    # Simple health check logic
    health_data = {
        "status": "ok",
        "version": "0.1.0",
        "environment": settings.environment,
        "system_active": state.system_active,
    }
    
    end = time.monotonic_ns()
    latency_ms = (end - start) / 1_000_000
    
    health_data["backend_latency_ms"] = round(latency_ms, 2)
    
    return health_data

