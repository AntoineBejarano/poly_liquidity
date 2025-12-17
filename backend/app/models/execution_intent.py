"""
ExecutionIntent model - Intenciones de ejecución generadas por estrategias.

Los Decision Graphs generan ExecutionIntents que luego pasan por Risk Engine.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy import Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ExecutionIntent(BaseModel):
    """
    ExecutionIntent model - Intención de ejecución.
    
    Generado por Decision Graph.
    Pasa por Risk Engine.
    Se ejecuta en Execution Engine.
    """
    
    __tablename__ = "execution_intents"
    
    # Relación con estrategia
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False, index=True)
    
    # Relación con evento (unidad atómica)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    
    # Detalles de la intención
    side = Column(String, nullable=False)  # "BUY", "SELL"
    outcome = Column(String, nullable=False)  # "YES", "NO", "UP", "DOWN"
    target_price = Column(Numeric(18, 8), nullable=False)
    size = Column(Numeric(18, 8), nullable=False)  # En shares
    size_usdc = Column(Numeric(18, 8), nullable=False)  # En USDC
    
    # Razón y contexto
    reason = Column(String, nullable=False)  # Razón de la entrada
    context = Column(JSONB, nullable=True)  # Contexto completo de la decisión
    
    # Estado
    status = Column(String, nullable=False, default="PENDING", index=True)  # "PENDING", "APPROVED", "REJECTED", "EXECUTED", "CANCELLED"
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)
    
    # Trazabilidad
    trace_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    decision_trace_id = Column(UUID(as_uuid=True), ForeignKey("decision_trace.id"), nullable=True)
    graph_execution_id = Column(UUID(as_uuid=True), ForeignKey("graph_executions.id"), nullable=True)
    
    # Relación con orden ejecutada (si se ejecutó)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    
    # Relationships
    strategy = relationship("Strategy", back_populates="execution_intents")
    event = relationship("Event")
    decision_trace = relationship("DecisionTrace")
    graph_execution = relationship("GraphExecution")
    order = relationship("Order")

