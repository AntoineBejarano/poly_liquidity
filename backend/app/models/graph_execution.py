"""
GraphExecution model - Trazabilidad de ejecuciones de grafos.

Registra cada ejecución de un Decision Graph o Support Graph.
"""
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class GraphExecution(BaseModel):
    """
    GraphExecution model - Ejecución de un grafo.
    
    Registra:
    - Qué grafo se ejecutó (decision o support)
    - Para qué estrategia y evento
    - Estado y duración
    - Trazabilidad completa
    """
    
    __tablename__ = "graph_executions"
    
    # Relación con estrategia
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False, index=True)
    
    # Tipo de grafo ejecutado
    graph_type = Column(String, nullable=False, index=True)  # "decision" o "support"
    graph_name = Column(String, nullable=True)  # Nombre del grafo (para support graphs)
    
    # Relación con evento (si aplica)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True, index=True)
    
    # Estado de ejecución
    status = Column(String, nullable=False, index=True)  # "started", "completed", "failed", "timeout"
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)  # Duración en milisegundos
    
    # Resultado
    result = Column(JSONB, nullable=True)  # Resultado de la ejecución
    error_message = Column(Text, nullable=True)
    
    # Trazabilidad
    trace_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    node_executions = Column(JSONB, nullable=True)  # Array de ejecuciones de nodos individuales
    
    # Relationships
    strategy = relationship("Strategy", back_populates="graph_executions")
    event = relationship("Event")

