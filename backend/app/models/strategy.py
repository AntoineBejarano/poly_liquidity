"""
Strategy model - Estrategia basada en grafos.

Una Strategy es un proceso vivo que ejecuta Decision Graphs y Support Graphs.
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Strategy(BaseModel):
    """
    Strategy model - Estrategia basada en grafos.
    
    Una Strategy es un proceso vivo que:
    - Tiene un Decision Graph (hot path)
    - Tiene Support Graphs (cold path)
    - Puede activarse/desactivarse
    - Observa eventos asignados
    """
    
    __tablename__ = "strategies"
    
    # Identificación
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Estado (proceso vivo)
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    enabled_at = Column(DateTime, nullable=True)
    disabled_at = Column(DateTime, nullable=True)
    
    # Decision Graph (hot path) - JSON declarativo
    decision_graph = Column(JSONB, nullable=False)
    
    # Support Graphs (cold path) - Array de grafos auxiliares
    support_graphs = Column(JSONB, nullable=False, default=[])
    
    # Execution Graph (cold path) - Grafo para ejecutar planes
    execution_graph = Column(JSONB, nullable=True)
    
    # Strategy Triggers - Condiciones explícitas para activar Decision Graph
    triggers = Column(JSONB, nullable=False, default=[])  # List[Trigger]
    
    # Configuración de Control Loop
    control_loop_config = Column(JSONB, nullable=False, default={})
    
    # Configuración de riesgo y sizing
    risk_config = Column(JSONB, nullable=False, default={})
    
    # Observability Configuration - Configuración de observabilidad
    observability_config = Column(JSONB, nullable=False, default={})
    
    # Universe Configuration - Qué mercados/eventos observar
    # Contiene: categories, markets, tags, auto_attach, deny_list
    universe_config = Column(JSONB, nullable=False, default={})
    
    # Versionado - Pinning de versiones de nodos
    pinned_node_versions = Column(JSONB, nullable=True)  # Dict[str, str] - {node_type: version}
    # Si está definido, solo se usarán estas versiones específicas de nodos
    
    # Metadata
    created_by = Column(String, ForeignKey("neon_auth.users_sync.id"), nullable=True)
    tags = Column(JSONB, nullable=True)
    version = Column(Integer, nullable=False, default=1)  # Versión del grafo
    
    # Relationships
    strategy_events = relationship("StrategyEvent", back_populates="strategy", cascade="all, delete-orphan")
    execution_intents = relationship("ExecutionIntent", back_populates="strategy", cascade="all, delete-orphan")
    strategy_metrics = relationship("StrategyMetric", back_populates="strategy", cascade="all, delete-orphan")
    graph_executions = relationship("GraphExecution", back_populates="strategy", cascade="all, delete-orphan")
    execution_plans = relationship("ExecutionPlan", back_populates="strategy", cascade="all, delete-orphan")

