"""
Decision Trace model - Rastrea decisiones del bot para explicabilidad.
"""
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import BaseModel
from sqlalchemy.sql import func


class DecisionTrace(BaseModel):
    """
    Rastrea cada decisión del bot para explicabilidad.
    
    Según especificación en docs/PENDING/DECISION_TRACE_GUIDELINES.md
    """
    __tablename__ = "decision_trace"
    
    session_id = Column(UUID(as_uuid=True), ForeignKey("execution_session.id"), nullable=True)
    trace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    
    component = Column(String(100), nullable=False, index=True)  # "scanner", "strategy", "risk", "execution"
    decision_stage = Column(String(50), nullable=False, index=True)  # "SCAN", "EVENT_CONFIRMATION", "STRATEGY", "RISK", "EXECUTION"
    
    market_id = Column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=True, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True)
    
    decision_type = Column(String(100), nullable=False)  # "entry", "reject", "adjust", "cancel"
    decision = Column(String(50), nullable=False, index=True)  # "APPROVED", "REJECTED", "ADJUSTED", "CANCELLED"
    reason = Column(Text, nullable=True)
    
    input_data = Column(JSONB, nullable=False)  # ACOTADO: solo hashes/snapshots relevantes, NO orderbooks completos
    output_data = Column(JSONB, nullable=True)
    config_used = Column(JSONB, nullable=False)
    
    latency_ms = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    extra_metadata = Column(JSONB, nullable=True)  # Renamed from 'metadata' (reserved in SQLAlchemy)
    
    created_at = Column(DateTime, nullable=False, server_default=func.now())

