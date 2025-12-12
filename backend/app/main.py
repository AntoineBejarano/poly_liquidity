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
from app.core.event_engine import EventEngine
from app.core.strategy import Strategy
from app.core.risk_engine import RiskEngine
from app.core.execution import Execution
from app.core.metrics import Metrics
from app.core.api_cache import api_cache
from app.core.latency_monitor import latency_monitor

# Import API routers
from app.api import markets, positions, risk, system, wallets, checkers, control, history, dashboard, websocket, metrics, live

# Import checker implementations to auto-register them
import app.core.checkers.implementations  # noqa: F401

# Initialize services
scanner = Scanner()
event_engine = EventEngine()
strategy = Strategy()
risk_engine = RiskEngine()
execution = Execution()
metrics = Metrics()

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
    
    Note: All Polymarket API calls are rate-limited:
    - Scanner uses Data API (200 req/10s) with caching
    - EventEngine uses external checkers (not Polymarket API directly)
    - Execution uses Trading API (2400 req/10s)
    """
    global _approved_intents
    
    while state.system_active:
        try:
            await scanner.tick()         # 1. Escanear mercados (rate-limited, cached)
            await event_engine.tick()    # 2. Actualizar estado de eventos externos
            
            # 3. Decidir órdenes
            intents = await strategy.tick()
            
            # 4. Aplicar límites de riesgo
            _approved_intents = await risk_engine.tick(intents)
            
            # 5. Enviar/cancelar órdenes (rate-limited)
            await execution.tick(_approved_intents)
            
            await metrics.tick()         # 6. Registrar métricas
            
            # Sleep for configured tick interval
            tick_seconds = state.risk_config.tick_seconds
            await asyncio.sleep(tick_seconds)
        except Exception as e:
            # Log error and continue
            print(f"Error in main loop: {e}")
            await asyncio.sleep(1.0)  # Short sleep on error


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
    
    # Close services
    await scanner.close()
    await execution.close()
    await latency_monitor.close()
    
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

