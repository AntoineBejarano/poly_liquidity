"""
Equity Snapshot Service - Guarda snapshots periódicos del equity.

Se usa para generar el Equity Curve histórico.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.exc import OperationalError
from app.database import SessionLocal
from app.models.equity_snapshot import EquitySnapshot
from app.api.dashboard import get_dashboard

logger = logging.getLogger(__name__)


class EquitySnapshotService:
    """
    Servicio para guardar y recuperar snapshots de equity.
    
    Guarda snapshots periódicamente (cada hora por defecto) para poder
    generar el Equity Curve histórico.
    """
    
    def __init__(self, snapshot_interval_minutes: int = 60):
        """
        Inicializa el servicio.
        
        Args:
            snapshot_interval_minutes: Intervalo entre snapshots en minutos (default: 60)
        """
        self.snapshot_interval_minutes = snapshot_interval_minutes
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._logged_table_missing = False
    
    async def take_snapshot(self) -> bool:
        """
        Toma un snapshot del equity actual y lo guarda en la base de datos.
        
        Returns:
            True si se guardó exitosamente, False en caso contrario
        """
        try:
            # Obtener datos del dashboard (equity, PnL, etc.)
            # Nota: get_dashboard requiere un User, pero podemos llamarlo directamente
            # ya que solo necesitamos los datos, no la autenticación
            from app.core.state import state
            from app.core.api_cache import api_cache
            from datetime import timedelta
            
            # Calcular realized PnL
            realized_pnl = 0.0
            # TODO: Calcular desde posiciones resueltas
            
            # Calcular unrealized PnL
            unrealized_pnl = 0.0
            for position_state in state.positions.values():
                if position_state.resolved:
                    continue
                
                market_state = state.markets.get(position_state.market_id)
                if market_state and market_state.last_price:
                    cost_total = position_state.size * position_state.avg_price
                    theoretical_value = position_state.size * market_state.last_price
                    unrealized_pnl += theoretical_value - cost_total
            
            # Calcular global exposure
            global_exposure = 0.0
            for exposure_state in state.exposures.values():
                global_exposure += exposure_state.notional
            
            # Balance: solo con user_id (política v2, no balance global)
            base_equity = 0.0
            user_id = getattr(self, "_snapshot_user_id", None)
            if user_id:
                try:
                    from app.core.execution.polymarket_client_wrapper import get_polymarket_client_for_user
                    cache_key = f"polymarket_balance:{user_id}"
                    cached_balance = await api_cache.get(cache_key)
                    if cached_balance is not None:
                        base_equity = cached_balance
                    else:
                        polymarket_client = get_polymarket_client_for_user(user_id)
                        if polymarket_client.is_available():
                            balance = await polymarket_client.get_balance()
                            if balance is not None:
                                base_equity = balance
                                await api_cache.set(cache_key, balance, ttl=timedelta(seconds=60))
                except Exception as e:
                    logger.warning(f"Error getting balance for snapshot (user_id={user_id}): {e}")
            
            equity = base_equity if base_equity is not None else 0.0
            
            # Guardar snapshot en base de datos
            db: Session = SessionLocal()
            try:
                snapshot = EquitySnapshot(
                    snapshot_time=datetime.utcnow(),
                    equity=equity,
                    base_equity=base_equity,
                    realized_pnl=realized_pnl,
                    unrealized_pnl=unrealized_pnl,
                    global_exposure=global_exposure,
                )
                db.add(snapshot)
                db.commit()
                logger.debug(f"Equity snapshot saved: equity={equity}, time={snapshot.snapshot_time}")
                return True
            except OperationalError as e:
                db.rollback()
                if "no such table" in str(e).lower() and not self._logged_table_missing:
                    self._logged_table_missing = True
                    logger.warning(
                        "equity_snapshots table not found; snapshots disabled. "
                        "Set DATABASE_URL to PostgreSQL and redeploy, or run: alembic upgrade head"
                    )
                return False
            except Exception as e:
                logger.error(f"Error saving equity snapshot: {e}", exc_info=True)
                db.rollback()
                return False
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error taking equity snapshot: {e}", exc_info=True)
            return False
    
    async def get_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Obtiene el historial de equity snapshots.
        
        Args:
            start_time: Tiempo de inicio (opcional)
            end_time: Tiempo de fin (opcional)
            limit: Límite de resultados (default: 1000)
            
        Returns:
            Lista de snapshots como diccionarios
        """
        db: Session = SessionLocal()
        try:
            query = db.query(EquitySnapshot).order_by(desc(EquitySnapshot.snapshot_time))
            
            if start_time:
                query = query.filter(EquitySnapshot.snapshot_time >= start_time)
            if end_time:
                query = query.filter(EquitySnapshot.snapshot_time <= end_time)
            
            snapshots = query.limit(limit).all()
            
            return [
                {
                    "timestamp": snapshot.snapshot_time.isoformat(),
                    "equity": snapshot.equity,
                    "base_equity": snapshot.base_equity,
                    "realized_pnl": snapshot.realized_pnl,
                    "unrealized_pnl": snapshot.unrealized_pnl,
                    "global_exposure": snapshot.global_exposure,
                }
                for snapshot in snapshots
            ]
        except Exception as e:
            logger.error(f"Error getting equity history: {e}", exc_info=True)
            return []
        finally:
            db.close()
    
    async def start_periodic_snapshots(self):
        """Inicia el guardado periódico de snapshots."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._snapshot_loop())
        logger.info(f"Equity snapshot service started (interval: {self.snapshot_interval_minutes} minutes)")
    
    async def stop_periodic_snapshots(self):
        """Detiene el guardado periódico de snapshots."""
        self._running = False
        if self._task:
            await self._task
        logger.info("Equity snapshot service stopped")
    
    async def _snapshot_loop(self):
        """Loop que guarda snapshots periódicamente."""
        while self._running:
            try:
                await self.take_snapshot()
                await asyncio.sleep(self.snapshot_interval_minutes * 60)
            except Exception as e:
                logger.error(f"Error in equity snapshot loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Esperar 1 minuto antes de reintentar


# Instancia global del servicio
equity_snapshot_service = EquitySnapshotService(snapshot_interval_minutes=60)

