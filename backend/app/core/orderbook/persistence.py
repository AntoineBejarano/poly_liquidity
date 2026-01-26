"""
Persistence module for orderbook micro-features.

Guarda features calculadas del orderbook en DB de forma batch para evitar
sobrecarga de escritura. Flush automático por tiempo (10s) o tamaño (100 registros).
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.orderbook.models import OrderbookState
from app.models.market_micro_feature import MarketMicroFeature

logger = logging.getLogger(__name__)


class OrderbookPersistence:
    """
    Persistencia batch de orderbook features.
    
    Características:
    - Buffer en memoria (100 registros o 10s)
    - Batch insert cada 10s o 100 registros
    - Frecuencia adaptativa (opcional: más frecuente en FINISHED_UNRESOLVED)
    - Retención: 30 días (configurable)
    """
    
    def __init__(
        self,
        db: Session,
        batch_size: int = 100,
        flush_interval_seconds: float = 10.0,
        retention_days: int = 30
    ):
        """
        Args:
            db: SQLAlchemy session
            batch_size: Número de registros antes de flush
            flush_interval_seconds: Intervalo de tiempo para flush automático
            retention_days: Días de retención de datos (default: 30)
        """
        self.db = db
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds
        self.retention_days = retention_days
        
        # Buffer en memoria
        self._buffer: List[Dict[str, Any]] = []
        self._last_flush = datetime.utcnow()
        self._lock = asyncio.Lock()
        
        # Background task para flush periódico
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Inicia el background task de flush periódico."""
        if self._running:
            return
        
        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info("OrderbookPersistence started")
    
    async def stop(self):
        """Detiene el background task y hace flush final."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush final
        await self.flush()
        logger.info("OrderbookPersistence stopped")
    
    async def _periodic_flush(self):
        """Background task que hace flush periódico."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval_seconds)
                await self.flush_if_needed()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}", exc_info=True)
    
    async def add_feature(
        self,
        orderbook_state: OrderbookState,
        market_id: Optional[str] = None,
        event_id: Optional[str] = None
    ):
        """
        Añade un feature al buffer.
        
        Args:
            orderbook_state: Estado del orderbook a persistir
            market_id: ID interno del market (opcional)
            event_id: ID interno del event (opcional)
        """
        async with self._lock:
            feature_dict = {
                "asset_id": orderbook_state.asset_id,
                "market_id": market_id,
                "event_id": event_id,
                "ts_ms": orderbook_state.ts_ms,
                "best_bid_price": orderbook_state.best_bid_price,
                "best_bid_size": orderbook_state.best_bid_size,
                "best_ask_price": orderbook_state.best_ask_price,
                "best_ask_size": orderbook_state.best_ask_size,
                "spread_bps": orderbook_state.spread_bps,
                "mid": orderbook_state.mid,
                "depth_usdc_at_25bps": orderbook_state.depth_usdc_at_25bps,
                "depth_usdc_at_50bps": orderbook_state.depth_usdc_at_50bps,
                "depth_usdc_at_100bps": orderbook_state.depth_usdc_at_100bps,
                "impact_bps_for_usdc_100": orderbook_state.impact_bps_for_usdc_100,
                "impact_bps_for_usdc_500": orderbook_state.impact_bps_for_usdc_500,
                "impact_bps_for_usdc_1000": orderbook_state.impact_bps_for_usdc_1000,
                "impact_bps_for_usdc_5000": orderbook_state.impact_bps_for_usdc_5000,
                "concentration_top3_pct": orderbook_state.concentration_top3_pct,
                "update_rate_hz": orderbook_state.update_rate_hz,
                "replenishment_score": orderbook_state.replenishment_score,
                "staleness_ms": orderbook_state.staleness_ms,
                "integrity": orderbook_state.integrity,
            }
            
            self._buffer.append(feature_dict)
            
            # Flush si buffer está lleno
            if len(self._buffer) >= self.batch_size:
                await self.flush()
    
    async def flush_if_needed(self):
        """Flush si ha pasado el intervalo de tiempo."""
        async with self._lock:
            now = datetime.utcnow()
            elapsed = (now - self._last_flush).total_seconds()
            
            if elapsed >= self.flush_interval_seconds and self._buffer:
                await self._flush()
    
    async def flush(self):
        """Fuerza flush inmediato del buffer."""
        async with self._lock:
            await self._flush()
    
    async def _flush(self):
        """Flush interno (debe llamarse con lock adquirido)."""
        if not self._buffer:
            return
        
        try:
            # Convertir dicts a modelos
            features = [
                MarketMicroFeature(**feature_dict)
                for feature_dict in self._buffer
            ]
            
            # Batch insert
            self.db.bulk_save_objects(features)
            self.db.commit()
            
            logger.debug(f"Flushed {len(features)} orderbook features to DB")
            
            # Limpiar buffer
            self._buffer.clear()
            self._last_flush = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error flushing orderbook features: {e}", exc_info=True)
            self.db.rollback()
            # No limpiamos el buffer en caso de error (se reintentará)
    
    async def cleanup_old_features(self):
        """
        Elimina features más antiguos que retention_days.
        
        Debe ejecutarse periódicamente (p.ej. diariamente via cron).
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
            cutoff_ts_ms = int(cutoff_date.timestamp() * 1000)
            
            deleted = self.db.query(MarketMicroFeature).filter(
                MarketMicroFeature.ts_ms < cutoff_ts_ms
            ).delete()
            
            self.db.commit()
            logger.info(f"Cleaned up {deleted} old orderbook features (older than {self.retention_days} days)")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error cleaning up old features: {e}", exc_info=True)
            self.db.rollback()
            return 0

