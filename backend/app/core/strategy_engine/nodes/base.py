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


class PlanResult(NodeResult):
    """Resultado de build_plan node."""
    def __init__(self, plan_id):
        self.plan_id = plan_id


class CalculationResult(NodeResult):
    """Resultado de calculate_order_size node con datos calculados."""
    def __init__(self, size: float, price: float, size_usdc: float):
        self.size = size
        self.price = price
        self.size_usdc = size_usdc


class ExecutionResult(NodeResult):
    """Resultado de execution_coordinator node."""
    def __init__(self, plan_id, legs_status: Dict[str, Any], success: bool = True, error: Optional[str] = None):
        self.plan_id = plan_id
        self.legs_status = legs_status  # Dict con estado de cada leg
        self.success = success
        self.error = error