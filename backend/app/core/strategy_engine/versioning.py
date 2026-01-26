"""
Versioning Rules and Utilities - Reglas y utilidades de versionado.

Este módulo documenta y implementa las reglas de versionado para nodos y estrategias.
"""
from typing import Dict, Optional
from app.models.strategy import Strategy
from app.models.graph_node_definition import GraphNodeDefinition


# ============================================================================
# REGLAS DE VERSIONADO
# ============================================================================

"""
REGLAS DE VERSIONADO PARA GRAPH NODES:

1. SEMANTIC VERSIONING (SemVer):
   - Formato: MAJOR.MINOR.PATCH (ej: "1.2.3")
   - MAJOR: Cambios incompatibles en la API o comportamiento
   - MINOR: Nuevas funcionalidades compatibles hacia atrás
   - PATCH: Correcciones de bugs compatibles

2. VERSIONADO DE GraphNodeDefinition:
   - Cada nodo tiene un campo `version` (String)
   - Si version es None, se considera "latest" (última versión disponible)
   - Las versiones se registran en el catálogo (graph_node_definitions)

3. PINNING DE VERSIONES EN Strategy:
   - Una Strategy puede tener `pinned_node_versions: Dict[str, str]`
   - Ejemplo: {"build_plan": "1.0.0", "execution_coordinator": "1.2.0"}
   - Si un nodo está pinned, SOLO se usa esa versión específica
   - Si un nodo NO está pinned, se usa la versión "latest" disponible

4. REGISTRO DE VERSIONES EN ExecutionPlan:
   - Al crear un ExecutionPlan, se registran las versiones de nodos usadas
   - Campo `node_versions: Dict[str, str]` en ExecutionPlan
   - Esto permite reproducir exactamente qué versiones se usaron
   - Útil para debugging, auditoría y reproducción de ejecuciones

5. COMPATIBILIDAD:
   - Si una Strategy tiene pinned_node_versions, se valida que existan
   - Si una versión pinned no existe, se lanza error al ejecutar
   - Si no hay pinned, se usa la versión más reciente disponible

6. MIGRACIÓN DE VERSIONES:
   - Al actualizar un nodo, se crea una nueva entrada en graph_node_definitions
   - Las Strategies existentes siguen usando sus versiones pinned
   - Para usar nueva versión, actualizar pinned_node_versions en Strategy

7. DEPRECACIÓN:
   - Un nodo puede marcarse como deprecated en su definición
   - Las Strategies con versiones deprecated reciben warnings
   - Se recomienda migrar a versiones no deprecated
"""


def get_node_version(
    node_type: str,
    strategy: Optional[Strategy] = None,
    db=None
) -> Optional[str]:
    """
    Obtiene la versión de un nodo a usar.
    
    Prioridad:
    1. Si strategy tiene pinned_node_versions y el nodo está pinned, usar esa versión
    2. Si no, obtener la versión "latest" del catálogo
    
    Args:
        node_type: Tipo del nodo (ej: "build_plan")
        strategy: Strategy opcional (para verificar pinned versions)
        db: Database session opcional (para consultar catálogo)
    
    Returns:
        Versión del nodo a usar, o None si no se encuentra
    """
    # 1. Verificar si está pinned en la estrategia
    if strategy and strategy.pinned_node_versions:
        pinned_version = strategy.pinned_node_versions.get(node_type)
        if pinned_version:
            return pinned_version
    
    # 2. Obtener versión "latest" del catálogo
    if db:
        node_def = db.query(GraphNodeDefinition).filter(
            GraphNodeDefinition.node_type == node_type
        ).order_by(GraphNodeDefinition.created_at.desc()).first()
        
        if node_def:
            return node_def.version or "latest"
    
    return "latest"


def validate_pinned_versions(strategy: Strategy, db) -> tuple[bool, Optional[str]]:
    """
    Valida que todas las versiones pinned en la estrategia existan.
    
    Args:
        strategy: Strategy a validar
        db: Database session
    
    Returns:
        (is_valid, error_message)
    """
    if not strategy.pinned_node_versions:
        return True, None
    
    for node_type, version in strategy.pinned_node_versions.items():
        # Buscar el nodo con esa versión
        node_def = db.query(GraphNodeDefinition).filter(
            GraphNodeDefinition.node_type == node_type,
            GraphNodeDefinition.version == version
        ).first()
        
        if not node_def:
            return False, (
                f"Pinned version '{version}' for node '{node_type}' not found in catalog. "
                f"Available versions can be checked in graph_node_definitions table."
            )
    
    return True, None


def record_node_versions(
    graph: Dict[str, Any],
    strategy: Optional[Strategy] = None,
    db=None
) -> Dict[str, str]:
    """
    Registra las versiones de nodos usadas en un grafo.
    
    Args:
        graph: Grafo (decision_graph, execution_graph, etc.)
        strategy: Strategy opcional (para verificar pinned versions)
        db: Database session opcional (para consultar catálogo)
    
    Returns:
        Dict con {node_type: version} para todos los nodos del grafo
    """
    node_versions = {}
    
    # Recorrer todos los nodos del grafo
    for node_id, node_config in graph.items():
        if isinstance(node_config, dict) and "type" in node_config:
            node_type = node_config["type"]
            version = get_node_version(node_type, strategy, db)
            if version:
                node_versions[node_type] = version
    
    return node_versions

