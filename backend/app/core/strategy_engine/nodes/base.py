"""
Base classes para nodos del grafo.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class GraphNode(ABC):
    """Clase base para todos los nodos del grafo."""
    
    def __init__(self, config: Dict[str, Any], context: 'GraphExecutionContext'):
        self.config = config
        self.context = context
    
    @abstractmethod
    async def execute(self) -> 'NodeResult':
        """Ejecuta el nodo y retorna resultado."""
        pass


class NodeResult:
    """Resultado base de un nodo."""
    pass


class ConditionalResult(NodeResult):
    """Resultado con condición booleana."""
    def __init__(self, condition: bool, data: Dict[str, Any] = None):
        self.condition = condition
        self.data = data or {}


class ExecutionIntentResult(NodeResult):
    """Resultado que contiene un Execution Intent."""
    def __init__(self, intent: Any):  # OrderIntent
        self.intent = intent


class SuccessResult(NodeResult):
    """Resultado de éxito."""
    pass


class FailureResult(NodeResult):
    """Resultado de fallo."""
    def __init__(self, error: str):
        self.error = error

