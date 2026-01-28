"""
Graph Nodes API endpoints.

APIs para obtener información sobre los nodos de grafo disponibles.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.database import get_db
from app.api.auth import get_current_user, User
from app.models.graph_node_definition import GraphNodeDefinition

router = APIRouter(prefix="/graph-nodes", tags=["graph-nodes"])


class GraphNodeResponse(BaseModel):
    """Modelo de respuesta para nodo de grafo."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    node_type: str
    name: str
    description: Optional[str]
    category: str
    path_type: str
    config_schema: dict
    is_builtin: bool
    version: Optional[str]
    icon: Optional[str]
    created_at: str
    updated_at: str


def node_to_dict(node: GraphNodeDefinition, include_schema: bool = True) -> dict:
    """Convierte un modelo GraphNodeDefinition a diccionario."""
    result = {
        "id": str(node.id),
        "node_type": node.node_type,
        "name": node.name,
        "description": node.description,
        "category": node.category,
        "path_type": node.path_type,
        "is_builtin": node.is_builtin,
        "version": node.version,
        "icon": node.icon,
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "updated_at": node.updated_at.isoformat() if node.updated_at else None,
    }
    
    if include_schema:
        result["config_schema"] = node.config_schema
    
    return result


@router.get("", response_model=List[GraphNodeResponse])
async def list_graph_nodes(
    category: Optional[str] = Query(None, description="Filter by category"),
    path_type: Optional[str] = Query(None, description="Filter by path_type ('hot' o 'cold')"),
    is_builtin: Optional[bool] = Query(None, description="Filter by builtin status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todos los nodos de grafo disponibles."""
    query = db.query(GraphNodeDefinition)
    
    if category:
        query = query.filter(GraphNodeDefinition.category == category)
    if path_type:
        query = query.filter(GraphNodeDefinition.path_type == path_type)
    if is_builtin is not None:
        query = query.filter(GraphNodeDefinition.is_builtin == is_builtin)
    
    nodes = query.order_by(GraphNodeDefinition.category, GraphNodeDefinition.name).all()
    return [node_to_dict(n) for n in nodes]


@router.get("/{node_type}", response_model=GraphNodeResponse)
async def get_graph_node(
    node_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene la definición de un nodo específico."""
    node = db.query(GraphNodeDefinition).filter(
        GraphNodeDefinition.node_type == node_type
    ).first()
    
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node type not found"
        )
    
    return node_to_dict(node, include_schema=True)


@router.get("/categories/list")
async def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todas las categorías de nodos disponibles."""
    categories = db.query(GraphNodeDefinition.category).distinct().all()
    return {"categories": [cat[0] for cat in categories]}

