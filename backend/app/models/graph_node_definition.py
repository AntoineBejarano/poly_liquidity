"""
GraphNodeDefinition model - Definiciones de nodos disponibles.

Catálogo de nodos que pueden usarse en Decision Graphs y Support Graphs.
"""
from sqlalchemy import Column, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import BaseModel


class GraphNodeDefinition(BaseModel):
    """
    GraphNodeDefinition model - Definición de un nodo de grafo.
    
    Cada nodo tiene:
    - Tipo único (node_type)
    - Schema de configuración (JSON Schema)
    - Categoría y path_type (hot/cold)
    """
    
    __tablename__ = "graph_node_definitions"
    
    # Identificación
    node_type = Column(String, unique=True, nullable=False, index=True)  # "collect_state", "edge_and_risk_check", etc.
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Categoría
    category = Column(String, nullable=False, index=True)  # "state", "condition", "calculation", "action", "io"
    path_type = Column(String, nullable=False)  # "hot" (Decision Graph) o "cold" (Support Graph)
    
    # Schema de configuración (JSON Schema)
    config_schema = Column(JSONB, nullable=False)  # JSON Schema para validar config del nodo
    
    # Metadata
    is_builtin = Column(Boolean, nullable=False, default=True)
    version = Column(String, nullable=True)
    icon = Column(String, nullable=True)  # Para UI

