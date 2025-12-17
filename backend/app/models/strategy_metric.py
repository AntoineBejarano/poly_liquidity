"""
StrategyMetric model - Métricas de rendimiento de estrategias.

Métricas agregadas por período de tiempo.
"""
from sqlalchemy import Column, DateTime, Integer, ForeignKey
from sqlalchemy import Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel


class StrategyMetric(BaseModel):
    """
    StrategyMetric model - Métricas de estrategia.
    
    Métricas agregadas por período:
    - Intents generados, aprobados, ejecutados, rechazados
    - Volumen, PnL, exposición
    - Win rate, precios promedio
    """
    
    __tablename__ = "strategy_metrics"
    
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False, index=True)
    
    # Ventana de tiempo
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    
    # Métricas agregadas
    total_intents = Column(Integer, nullable=False, default=0)
    approved_intents = Column(Integer, nullable=False, default=0)
    executed_intents = Column(Integer, nullable=False, default=0)
    rejected_intents = Column(Integer, nullable=False, default=0)
    
    # Métricas financieras
    total_volume_usdc = Column(Numeric(18, 8), nullable=False, default=0)
    total_pnl_usdc = Column(Numeric(18, 8), nullable=True)  # PnL realizado
    total_exposure_usdc = Column(Numeric(18, 8), nullable=False, default=0)
    
    # Métricas de rendimiento
    win_rate = Column(Numeric(5, 4), nullable=True)  # % de intents que resultaron en ganancia
    avg_entry_price = Column(Numeric(18, 8), nullable=True)
    avg_exit_price = Column(Numeric(18, 8), nullable=True)
    
    # Metadata
    calculated_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    strategy = relationship("Strategy", back_populates="strategy_metrics")

