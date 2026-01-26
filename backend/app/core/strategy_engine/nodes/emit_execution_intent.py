"""
Emit Execution Intent Node - Emite un Execution Intent.

⚠️ DEPRECATED en Decision Graph: Este nodo está deprecado para uso en Decision Graphs.
    Use `build_plan` + `emit_plan_intent` en su lugar.

Este nodo todavía puede usarse en Execution Graphs si es necesario.
"""
import warnings
from typing import Dict, Any

from app.core.strategy_engine.nodes.base import GraphNode, ExecutionIntentResult, FailureResult
from app.core.strategy.models import OrderIntent


class EmitExecutionIntentNode(GraphNode):
    """
    Nodo que emite un Execution Intent.
    
    ⚠️ DEPRECATED en Decision Graph: Este nodo está deprecado para uso en Decision Graphs.
        Use `build_plan` + `emit_plan_intent` en su lugar.
    
    Este nodo todavía puede usarse en Execution Graphs si es necesario.
    Crea un OrderIntent que será validado por el Risk Engine.
    """
    
    async def execute(self) -> ExecutionIntentResult:
        """
        Emite un Execution Intent.
        
        ⚠️ DEPRECATED en Decision Graph: Este método está deprecado para uso en Decision Graphs.
            Use `build_plan` + `emit_plan_intent` en su lugar.
        
        Config:
            side: str - "BUY" o "SELL" (default: "BUY")
            outcome: str - "YES", "NO", "UP", "DOWN" (default: "YES")
            reason: str - Razón de la entrada (default: "Strategy decision")
        
        Requiere:
            - calculated_price en context
            - calculated_size en context
        """
        side = self.config.get("side", "BUY")
        outcome = self.config.get("outcome", "YES")
        reason = self.config.get("reason", "Strategy decision")
        
        # Obtener precio y tamaño del contexto (calculados por nodos anteriores)
        if not hasattr(self.context, 'calculated_price') or self.context.calculated_price is None:
            return FailureResult("Price must be calculated before emitting intent")
        
        if not hasattr(self.context, 'calculated_size') or self.context.calculated_size is None:
            return FailureResult("Size must be calculated before emitting intent")
        
        price = self.context.calculated_price
        size = self.context.calculated_size
        size_usdc = size * price
        
        # Obtener estado recopilado para metadata
        collected_state = {}
        if hasattr(self.context, 'collected_state'):
            collected_state = self.context.collected_state
        
        # Crear OrderIntent
        intent = OrderIntent(
            event_id=self.context.event_id,
            outcome=outcome,
            side=side,
            price=price,
            size=size,
            reason=reason,
            metadata={
                "strategy_id": str(self.context.strategy_id),
                "market_id": str(self.context.market_id),
                "collected_state": collected_state
            },
            trace_id=self.context.trace_id,
            strategy_id=self.context.strategy_id
        )
        
        return ExecutionIntentResult(intent)

