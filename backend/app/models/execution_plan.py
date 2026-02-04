"""
ExecutionPlan model - Plan de ejecución inmutable.

Un ExecutionPlan representa un plan de ejecución completo que separa la decisión
(Decision Graph) de la ejecución (Execution Graph).
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.models.base import BaseModel


class ExecutionPlan(BaseModel):
    """
    ExecutionPlan model - Plan de ejecución inmutable.
    
    Un ExecutionPlan es una entidad inmutable que representa un plan de ejecución.
    Una vez creado con status PLAN_BUILT, el plan NO puede modificarse.
    Solo se puede cambiar el estado del plan (transiciones permitidas).
    
    Características:
    - Inmutable después de creación (excepto estado)
    - Contiene legs (1 para near-end, N para surebet)
    - Tiene TTL (tiempo de vida)
    - Tiene configuración de riesgo
    """
    
    __tablename__ = "execution_plans"
    
    # Relación con estrategia y evento
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    
    # Plan inmutable (JSONB) - NO se modifica después de PLAN_BUILT
    legs = Column(JSONB, nullable=False)  # List[PlanLeg dict]
    ttl_ms = Column(Integer, nullable=False)  # Tiempo de vida del plan en milisegundos
    
    # Estado del plan
    status = Column(String, nullable=False, index=True, default="PLAN_BUILT")
    # Estados válidos: PLAN_BUILT | ABORTED | EXECUTING | COMPLETED | FAILED
    
    # Risk config a nivel plan
    risk_config = Column(JSONB, nullable=False, default={})
    
    # Trazabilidad
    trace_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    decision_graph_execution_id = Column(UUID(as_uuid=True), ForeignKey("graph_executions.id"), nullable=True)
    execution_graph_execution_id = Column(UUID(as_uuid=True), ForeignKey("graph_executions.id"), nullable=True)
    
    # Timestamps
    # IMPORTANTE: expires_at es INMUTABLE. No se recalcula, no se actualiza, no se extiende.
    # TTL es parte de la inmutabilidad semántica del plan.
    expires_at = Column(DateTime, nullable=True)  # Calculado: created_at + ttl_ms
    
    # Estado de ejecución (para observabilidad)
    ready_for_execution = Column(Boolean, nullable=False, default=False, index=True)
    queued_at = Column(DateTime, nullable=True)  # Timestamp cuando se marcó como listo
    
    # Versionado - Versiones de nodos usadas al crear este plan
    node_versions = Column(JSONB, nullable=True)  # Dict[str, str] - {node_type: version}
    
    # Relationships
    strategy = relationship("Strategy", back_populates="execution_plans")
    event = relationship("Event")
    decision_graph_execution = relationship("GraphExecution", foreign_keys=[decision_graph_execution_id])
    execution_graph_execution = relationship("GraphExecution", foreign_keys=[execution_graph_execution_id])
    
    def __init__(self, **kwargs):
        """Inicializa ExecutionPlan y calcula expires_at automáticamente."""
        super().__init__(**kwargs)
        # Calcular expires_at si no se proporciona y tenemos ttl_ms
        # Nota: created_at puede ser None aquí porque el default de SQLAlchemy 
        # se aplica al insertar, no al instanciar. Usamos datetime.utcnow() en ese caso.
        if self.expires_at is None and self.ttl_ms:
            base_time = self.created_at if self.created_at else datetime.utcnow()
            self.expires_at = base_time + timedelta(milliseconds=self.ttl_ms)
    
    def is_expired(self) -> bool:
        """Verifica si el plan ha expirado."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def get_remaining_ttl_ms(self) -> int:
        """Obtiene el TTL restante en milisegundos."""
        if self.expires_at is None:
            return 0
        remaining = (self.expires_at - datetime.utcnow()).total_seconds() * 1000
        return max(0, int(remaining))

