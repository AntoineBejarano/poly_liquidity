"""
FastAPI application entry point.
"""
import sys
import logging

# Configurar logging detallado desde el inicio
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info("=" * 80)
logger.info("INICIANDO POLYLIQUIDITY DESK")
logger.info("=" * 80)

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger.info("Importando settings...")
from app.settings import settings
logger.info("Settings importado correctamente")

logger.info("Importando database...")
from app.database import SessionLocal
logger.info("Database importado correctamente")

logger.info("Importando state...")
from app.core.state import state
logger.info("State importado correctamente")

logger.info("Importando config_service...")
from app.core.config_service import config_service
logger.info("Config service importado correctamente")
logger.info("Importando Scanner...")
from app.core.scanner import Scanner
logger.info("Scanner importado")

logger.info("Importando EventMappingLayer...")
from app.core.event_mapping_layer import EventMappingLayer
logger.info("EventMappingLayer importado")

logger.info("Importando EventWatchCoordinator...")
from app.core.event_watch_engine import EventWatchCoordinator
logger.info("EventWatchCoordinator importado")

logger.info("Importando EventEngine...")
from app.core.event_engine import EventEngine
logger.info("EventEngine importado")

logger.info("Importando Strategy...")
from app.core.strategy import Strategy
from app.core.strategy.models import OrderIntent
logger.info("Strategy importado")

logger.info("Importando RiskEngine...")
from app.core.risk_engine import RiskEngine
logger.info("RiskEngine importado")

logger.info("Importando Execution...")
from app.core.execution import Execution
logger.info("Execution importado")
# Import Metrics from the metrics.py module (not the metrics package)
# We need to load it directly from the file to avoid package/module name conflict
logger.info("Importando Metrics...")
import importlib.util
from pathlib import Path

_metrics_file = Path(__file__).parent / "core" / "metrics.py"
spec = importlib.util.spec_from_file_location("app.core.metrics_module", _metrics_file)
metrics_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics_module)
Metrics = metrics_module.Metrics
logger.info("Metrics importado")

logger.info("Importando metrics_service...")
from app.core.metrics.metrics_service import metrics_service
logger.info("Metrics service importado")

logger.info("Importando RuntimeSupervisor...")
from app.core.runtime_supervisor import RuntimeSupervisor
logger.info("RuntimeSupervisor importado")

logger.info("Importando api_cache...")
from app.core.api_cache import api_cache
logger.info("API cache importado")

logger.info("Importando latency_monitor...")
from app.core.latency_monitor import latency_monitor
logger.info("Latency monitor importado")

logger.info("Importando Historical Replay...")
from app.core.historical_replay import EventStore, initialize_event_store
from app.core.historical_replay.event_logger import (
    log_event, log_watcher_event, log_strategy_intent, log_risk_decision,
    log_execution_event, log_runtime_event
)
logger.info("Historical Replay importado")

logger.info("Importando Live Control...")
from app.core.live_control import LiveControlStore, initialize_event_bus, emit_event
logger.info("Live Control importado")

# Import API routers
logger.info("Importando API routers...")
from app.api import markets, positions, risk, system, wallets, checkers, control, history, dashboard, websocket, metrics as metrics_api, live, live_status, polymarket, series, tags, strategies, graph_nodes, state_cache
logger.info("API routers importados")

# Import checker implementations to auto-register them
logger.info("Importando checker implementations...")
import app.core.checkers.implementations  # noqa: F401
logger.info("Checker implementations importados")

# Initialize services
logger.info("Inicializando servicios...")
logger.info("  - Scanner...")
scanner = Scanner()
logger.info("  - EventMappingLayer...")
event_mapping_layer = EventMappingLayer()
logger.info("  - EventWatchCoordinator...")
event_watch_coordinator = EventWatchCoordinator()
logger.info("  - EventEngine...")
event_engine = EventEngine()
logger.info("  - RiskEngine...")
risk_engine = RiskEngine()
logger.info("  - Strategy...")
# Inicializar Strategy condicionalmente según feature flag
if settings.use_graph_strategies:
    logger.info("  - StrategyEngine (graph-based)...")
    from app.core.strategy_engine.strategy_engine import StrategyEngine
    strategy_engine = StrategyEngine()
    # Se inicializará después con DB
else:
    logger.info("  - Strategy (legacy)...")
    strategy = Strategy()
logger.info("  - Execution...")
# #region agent log
import json
with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:135","message":"BEFORE Execution() instantiation","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
# #endregion
execution = Execution()
# #region agent log
with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:136","message":"AFTER Execution() instantiation","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
# #endregion
logger.info("  - Metrics...")
metrics = Metrics()
logger.info("  - RuntimeSupervisor...")
runtime_supervisor = RuntimeSupervisor(execution_engine=execution)
logger.info("Todos los servicios inicializados")

# Initialize Historical Replay Event Store
logger.info("Inicializando Event Store...")
event_store = EventStore(storage_type="sqlite")
initialize_event_store(event_store)
logger.info("Event Store inicializado")

# Initialize Live Control Event Bus
logger.info("Inicializando Live Control Event Bus...")
live_control_store = LiveControlStore()
initialize_event_bus(live_control_store)
logger.info("Live Control Event Bus inicializado")

logger.info("=" * 80)
logger.info("IMPORTACIONES Y INICIALIZACIONES COMPLETADAS")
logger.info("=" * 80)

# Store approved intents for execution
_approved_intents = []

# Main loop task
_main_loop_task = None
_cache_cleanup_task = None
_strategy_engine_control_loop_task = None


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
            # Si use_graph_strategies está activado, los intents vienen del Control Loop
            # Si no, usar el sistema legacy
            if settings.use_graph_strategies:
                # Los intents se generan desde el Control Loop y pasan por Risk Engine allí
                # El main loop solo maneja el sistema legacy
                intents = []
            else:
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
    logger.info("=" * 80)
    logger.info("INICIANDO LIFESPAN - STARTUP")
    logger.info("=" * 80)
    
    # Load configuration from DB (non-blocking, allow failures)
    logger.info("[1/7] Cargando configuración desde base de datos...")
    try:
        config_service.load_from_db()
        logger.info("✓ Configuración cargada desde base de datos")
    except Exception as e:
        logger.warning(f"⚠ No se pudo cargar configuración desde base de datos: {e}")
        logger.info("Iniciando con configuración por defecto.")
    
    # Start hot reload for configuration (non-blocking)
    logger.info("[2/7] Iniciando hot reload de configuración...")
    try:
        config_service.start_hot_reload()
        logger.info("✓ Hot reload de configuración iniciado")
    except Exception as e:
        logger.warning(f"⚠ No se pudo iniciar hot reload: {e}")
        logger.info("Los cambios de configuración requerirán reinicio del servidor.")
    
    # Update state with config
    logger.info("[3/7] Actualizando state con configuración...")
    try:
        state.risk_config = config_service.get_risk_config()
        logger.info("✓ State actualizado con configuración de riesgo")
    except Exception as e:
        logger.warning(f"⚠ No se pudo cargar risk config: {e}")
        logger.info("Usando configuración de riesgo por defecto.")
    
    # Load state from DB (non-blocking, allow failures)
    logger.info("[4/7] Cargando state desde base de datos...")
    db = SessionLocal()
    try:
        # Test connection first with timeout
        try:
            from sqlalchemy import text
            logger.info("  - Probando conexión a base de datos...")
            db.execute(text("SELECT 1"))
            db.commit()
            logger.info("  ✓ Conexión a base de datos exitosa")
            logger.info("  - Cargando state...")
            state.load_from_db(db)
            logger.info("  ✓ State cargado desde base de datos")
        except Exception as db_error:
            logger.warning(f"  ⚠ No se pudo cargar state desde base de datos: {db_error}")
            logger.info("  Iniciando con state vacío. Verifica que DATABASE_URL sea correcto.")
            db.rollback()
    except Exception as e:
        logger.warning(f"  ⚠ Error de base de datos durante startup: {e}")
    finally:
        db.close()
        logger.info("  ✓ Conexión de base de datos cerrada")
    
    # Start metrics service (non-blocking, allow failures)
    logger.info("[5/7] Iniciando servicio de métricas...")
    try:
        await metrics_service.start()
        logger.info("  ✓ Servicio de métricas iniciado")
    except Exception as e:
        logger.warning(f"  ⚠ No se pudo iniciar servicio de métricas: {e}")
        logger.info("  El servidor continuará sin servicio de métricas.")
    
    # Start main loop in background (non-blocking)
    logger.info("[6/7] Iniciando main loop...")
    global _main_loop_task, _cache_cleanup_task, _strategy_engine_control_loop_task
    # Start with system paused by default - user must explicitly start it
    state.system_active = False
    logger.info("  - Creando tarea de main loop...")
    _main_loop_task = asyncio.create_task(main_loop())
    logger.info("  - Creando tarea de cache cleanup...")
    _cache_cleanup_task = asyncio.create_task(cache_cleanup_loop())
    
    # Iniciar StrategyEngine Control Loop si está habilitado
    if settings.use_graph_strategies:
        logger.info("  - Inicializando StrategyEngine...")
        db = SessionLocal()
        try:
            strategy_engine.initialize(
                db,
                risk_engine=risk_engine,
                execution_engine=execution
            )
            logger.info("  - Creando tarea de Control Loop...")
            _strategy_engine_control_loop_task = asyncio.create_task(
                strategy_engine.control_loop.start(db)
            )
            logger.info("  ✓ StrategyEngine Control Loop iniciado")
        except Exception as e:
            logger.error(f"  ⚠ Error inicializando StrategyEngine: {e}", exc_info=True)
            db.close()
        # No cerramos la sesión aquí, el Control Loop la usará
    
    logger.info("  ✓ Tareas de main loop creadas")
    
    logger.info("[7/7] Startup completado")
    logger.info("=" * 80)
    logger.info("✓ POLYLIQUIDITY DESK INICIADO EXITOSAMENTE")
    logger.info("=" * 80)
    logger.info("NOTA: El sistema está pausado por defecto.")
    logger.info("      Usa /control/resume para iniciar trading.")
    logger.info(f"      Documentación API: http://localhost:8000/docs")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("=" * 80)
    logger.info("INICIANDO SHUTDOWN")
    logger.info("=" * 80)
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
    
    # Stop StrategyEngine Control Loop if running
    if settings.use_graph_strategies and _strategy_engine_control_loop_task:
        logger.info("Deteniendo StrategyEngine Control Loop...")
        strategy_engine.control_loop.stop()
        _strategy_engine_control_loop_task.cancel()
        try:
            await _strategy_engine_control_loop_task
        except asyncio.CancelledError:
            pass
    
    # Stop metrics service
    await metrics_service.stop()
    
    # Stop config service hot reload
    config_service.stop_hot_reload()
    
    # Close services
    await scanner.close()
    await execution.close()
    await latency_monitor.close()
    
    # Close Event Store
    event_store.close()
    
    # Stop all watchers
    from app.core.live_watchers import watcher_manager
    await watcher_manager.stop_all()
    
    logger.info("=" * 80)
    logger.info("✓ POLYLIQUIDITY DESK DETENIDO")
    logger.info("=" * 80)


# Validate critical settings before creating app
logger.info("Validando configuración crítica...")
try:
    if settings.stack_secret_server_key == "dev-secret-key-change-in-production":
        logger.warning("⚠ Usando STACK_SECRET_SERVER_KEY por defecto. Configura una clave real para producción!")
    if settings.database_url == "sqlite:///./poly_liquidity.db":
        logger.info("ℹ Usando base de datos SQLite por defecto. Configura DATABASE_URL para producción.")
    logger.info("✓ Configuración validada")
except Exception as e:
    logger.error(f"✗ ERROR: Fallo al cargar settings: {e}")
    logger.error("Por favor verifica tu archivo .env y asegúrate de que las variables requeridas estén configuradas.")
    raise

app = FastAPI(
    title="PolyLiquidity Desk API",
    description="API para gestión de liquidez en Polymarket",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
# Permitir múltiples orígenes separados por coma, y también localhost en diferentes puertos
cors_origins_list = [origin.strip() for origin in settings.cors_origins.split(",")]
# Agregar localhost en puertos comunes para desarrollo
if "http://localhost:3000" not in cors_origins_list:
    cors_origins_list.append("http://localhost:3000")
if "http://127.0.0.1:3000" not in cors_origins_list:
    cors_origins_list.append("http://127.0.0.1:3000")
logger.info(f"CORS origins configurados: {cors_origins_list}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routers
app.include_router(series.router)
app.include_router(tags.router)
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
app.include_router(metrics_api.router)
app.include_router(live.router)
app.include_router(live_status.router)
app.include_router(polymarket.router)

# Graph-based strategies APIs
app.include_router(strategies.router)
app.include_router(graph_nodes.router)
app.include_router(state_cache.router)
from app.api import strategy_templates
app.include_router(strategy_templates.router)
try:
    from app.api import runtime
    app.include_router(runtime.router)
except ImportError:
    pass  # runtime router may not exist


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

