"""
NoOp Node - Nodo que no hace nada, útil para finalizar grafos.
"""
from typing import Dict, Any

from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult


class NoOpNode(GraphNode):
    """
    Nodo que no hace nada.
    
    Útil para finalizar grafos o como placeholder.
    """
    
    async def execute(self) -> SuccessResult:
        """Ejecuta el nodo (no hace nada)."""
        return SuccessResult()

