"""
Metric Store - almacenamiento de métricas en memoria y persistente.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.base import Base
from app.models.metric import Metric
from app.settings import settings
import json
import os

# In-memory storage for recent metrics (last N metrics)
IN_MEMORY_LIMIT = 10000  # Keep last 10k metrics in memory


class MetricStore:
    """
    Almacén de métricas.
    
    Mantiene métricas en memoria (para acceso rápido) y persistente (para histórico).
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Inicializa el almacén de métricas.
        
        Args:
            database_url: URL de base de datos para almacenamiento persistente.
                         Si None, usa SQLite en memoria para tests.
        """
        # In-memory storage (circular buffer)
        self._in_memory_store: Dict[str, deque] = defaultdict(lambda: deque(maxlen=IN_MEMORY_LIMIT))
        
        # Persistent storage
        if database_url is None:
            # Use main database URL from settings
            database_url = settings.database_url
        
        # Create engine and session
        # SQLite doesn't support pool_size and max_overflow
        if database_url.startswith("sqlite"):
            self.engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                pool_pre_ping=True,
            )
        else:
            self.engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables (only Metric table)
        # Note: We need to import all models for metadata to work correctly
        # But we only create the Metric table here
        # Make this non-blocking - allow server to start even if DB is not available
        try:
            # Test connection first
            from sqlalchemy import text
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            # Use Base.metadata to create table
            Metric.__table__.create(self.engine, checkfirst=True)
        except Exception as e:
            print(f"WARNING: Could not create Metric table: {e}")
            print("Metrics will be stored in memory only until database is available.")
    
    async def store_metric(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        component: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Almacena una métrica.
        
        Args:
            metric_name: Nombre de la métrica
            value: Valor numérico
            labels: Etiquetas adicionales (dict)
            component: Componente que emite la métrica
            timestamp: Timestamp (default: ahora)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        labels_json = json.dumps(labels) if labels else None
        
        # Store in memory
        metric_data = {
            "metric_name": metric_name,
            "value": value,
            "labels": labels or {},
            "component": component,
            "timestamp": timestamp
        }
        self._in_memory_store[metric_name].append(metric_data)
        
        # Store in persistent DB
        db = self.SessionLocal()
        try:
            metric = Metric(
                timestamp=timestamp,
                metric_name=metric_name,
                value=value,
                labels=labels_json,
                component=component,
                created_at=timestamp
            )
            db.add(metric)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"ERROR: Failed to store metric in DB: {e}")
        finally:
            db.close()
    
    def get_metric_history(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Obtiene historial de una métrica.
        
        Args:
            metric_name: Nombre de la métrica
            start_time: Inicio del rango (opcional)
            end_time: Fin del rango (opcional)
            limit: Límite de resultados
        
        Returns:
            Lista de métricas
        """
        # Try in-memory first
        if metric_name in self._in_memory_store:
            metrics = list(self._in_memory_store[metric_name])
            if start_time or end_time:
                metrics = [
                    m for m in metrics
                    if (not start_time or m["timestamp"] >= start_time)
                    and (not end_time or m["timestamp"] <= end_time)
                ]
            return metrics[-limit:] if limit else metrics
        
        # Fallback to DB
        db = self.SessionLocal()
        try:
            query = db.query(Metric).filter(Metric.metric_name == metric_name)
            
            if start_time:
                query = query.filter(Metric.timestamp >= start_time)
            if end_time:
                query = query.filter(Metric.timestamp <= end_time)
            
            metrics = query.order_by(Metric.timestamp.desc()).limit(limit).all()
            
            # Reverse to get chronological order (oldest first)
            metrics_list = [
                {
                    "metric_name": m.metric_name,
                    "value": m.value,
                    "labels": json.loads(m.labels) if m.labels else {},
                    "component": m.component,
                    "timestamp": m.timestamp
                }
                for m in reversed(metrics)
            ]
            return metrics_list
        finally:
            db.close()
    
    def get_latest_metric(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene la última métrica de un tipo.
        
        Args:
            metric_name: Nombre de la métrica
        
        Returns:
            Última métrica o None
        """
        if metric_name in self._in_memory_store and self._in_memory_store[metric_name]:
            latest = self._in_memory_store[metric_name][-1]
            return latest
        
        # Fallback to DB
        db = self.SessionLocal()
        try:
            metric = db.query(Metric).filter(
                Metric.metric_name == metric_name
            ).order_by(Metric.timestamp.desc()).first()
            
            if metric:
                return {
                    "metric_name": metric.metric_name,
                    "value": metric.value,
                    "labels": json.loads(metric.labels) if metric.labels else {},
                    "component": metric.component,
                    "timestamp": metric.timestamp
                }
            return None
        finally:
            db.close()
    
    def calculate_percentiles(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Calcula percentiles (p50, p95, p99) de una métrica.
        
        Args:
            metric_name: Nombre de la métrica
            start_time: Inicio del rango (opcional)
            end_time: Fin del rango (opcional)
        
        Returns:
            Dict con p50, p95, p99
        """
        history = self.get_metric_history(metric_name, start_time, end_time, limit=10000)
        
        if not history:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
        
        values = sorted([m["value"] for m in history])
        n = len(values)
        
        def percentile(p: float) -> float:
            index = int(n * p)
            if index >= n:
                index = n - 1
            return values[index]
        
        return {
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
            "min": values[0] if values else 0.0,
            "max": values[-1] if values else 0.0,
            "count": n
        }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Obtiene resumen de todas las métricas recientes.
        
        Returns:
            Dict con resumen de métricas
        """
        summary = {}
        
        # Get latest metrics for each type
        metric_names = set(self._in_memory_store.keys())
        
        for metric_name in metric_names:
            latest = self.get_latest_metric(metric_name)
            if latest:
                summary[metric_name] = {
                    "value": latest["value"],
                    "timestamp": latest["timestamp"].isoformat(),
                    "labels": latest.get("labels", {}),
                    "component": latest.get("component")
                }
        
        return summary

