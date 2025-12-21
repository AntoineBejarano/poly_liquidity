"""
Equity Snapshot model - Almacena snapshots periódicos del equity.

Se usa para generar el Equity Curve histórico.
"""
from sqlalchemy import Column, Float, DateTime, Index
from app.models.base import BaseModel


class EquitySnapshot(BaseModel):
    """
    Snapshot del equity en un momento específico.
    
    Se guarda periódicamente (cada hora o cuando cambia significativamente)
    para poder generar el Equity Curve histórico.
    """
    
    __tablename__ = "equity_snapshots"
    
    # Timestamp del snapshot
    snapshot_time = Column(DateTime, nullable=False, index=True)
    
    # Valores del equity
    equity = Column(Float, nullable=False)  # Balance total
    base_equity = Column(Float, nullable=False)  # Balance base (sin PnL)
    realized_pnl = Column(Float, nullable=False, default=0.0)
    unrealized_pnl = Column(Float, nullable=False, default=0.0)
    global_exposure = Column(Float, nullable=False, default=0.0)
    
    # Índice compuesto para búsquedas eficientes por rango de tiempo
    __table_args__ = (
        Index('idx_equity_snapshot_time', 'snapshot_time'),
    )

