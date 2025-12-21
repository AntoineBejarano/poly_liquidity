"""
Graph Runtime - Ejecuta grafos (Decision Graph y Support Graphs).

El Decision Graph debe ejecutarse en < 50μs.
Solo lee State Cache, nunca llama APIs.
"""
import time
import logging
import warnings
from typing import Dict, Any, Optional, Type, List
from uuid import uuid4

from app.core.strategy_engine.models import GraphExecutionContext, GraphExecutionResult
from app.core.strategy.models import OrderIntent
from app.core.strategy_engine.nodes.base import (
    GraphNode,
    NodeResult,
    ConditionalResult,
    ExecutionIntentResult,
    SuccessResult,
    FailureResult,
    PlanResult,
    CalculationResult,
    ExecutionResult
)
from app.core.strategy_engine.nodes import (
    NoOpNode,
    CollectStateNode,
    EdgeAndRiskCheckNode,
    CalculateOrderSizeNode,
    EmitExecutionIntentNode,
    BuildPlanNode,
    EmitPlanIntentNode,
    ExecutionCoordinatorNode,
    RetryLegNode,
    CompensatePlanNode,
    DerivePlanNode,
    FetchExternalSourceNode,
    UpdateStateCacheNode,
    CalculateIndicatorsNode,
    LogNode
)

logger = logging.getLogger(__name__)


class GraphRuntime:
    """
    Runtime para ejecutar grafos (Decision Graph y Support Graphs).
    
    El Decision Graph debe ejecutarse en < 50μs.
    Solo lee State Cache, nunca llama APIs.
    """
    
    def __init__(self, state_cache_service: Any):  # StateCacheService
        self.state_cache = state_cache_service
        self.node_registry: Dict[str, Type[GraphNode]] = {}
        self._register_builtin_nodes()
    
    def _register_builtin_nodes(self):
        """Registra nodos predefinidos."""
        # Hot path nodes (Decision Graph)
        self.node_registry["noop"] = NoOpNode
        self.node_registry["collect_state"] = CollectStateNode
        self.node_registry["calculate_indicators"] = CalculateIndicatorsNode
        self.node_registry["edge_and_risk_check"] = EdgeAndRiskCheckNode
        self.node_registry["calculate_order_size"] = CalculateOrderSizeNode
        self.node_registry["build_plan"] = BuildPlanNode
        self.node_registry["emit_plan_intent"] = EmitPlanIntentNode
        self.node_registry["emit_execution_intent"] = EmitExecutionIntentNode  # Deprecated en Decision Graph
        
        # Cold path nodes (Support Graphs)
        self.node_registry["fetch_external_source"] = FetchExternalSourceNode
        self.node_registry["update_state_cache"] = UpdateStateCacheNode
        self.node_registry["log"] = LogNode
        
        # Execution Graph nodes (Cold path - Execution)
        self.node_registry["execution_coordinator"] = ExecutionCoordinatorNode
        self.node_registry["retry_leg"] = RetryLegNode
        self.node_registry["compensate_plan"] = CompensatePlanNode
        self.node_registry["derive_plan"] = DerivePlanNode
    
    def register_node(self, node_type: str, node_class: Type[GraphNode]):
        """Registra un tipo de nodo."""
        self.node_registry[node_type] = node_class
        logger.debug(f"Registered node type: {node_type}")
    
    async def execute_graph(
        self,
        graph: Dict[str, Any],
        context: GraphExecutionContext,
        path_type: str = "hot"  # "hot" o "cold"
    ) -> GraphExecutionResult:
        """
        Ejecuta un grafo.
        
        Args:
            graph: Definición del grafo (JSON)
                {
                    "entry_node": "observe",
                    "nodes": {
                        "observe": {
                            "type": "collect_state",
                            "config": {...},
                            "next": "evaluate"
                        },
                        "evaluate": {
                            "type": "edge_and_risk_check",
                            "config": {...},
                            "on_true": "act",
                            "on_false": "idle"
                        },
                        ...
                    }
                }
            context: Contexto de ejecución (strategy, event, etc.)
            path_type: "hot" (Decision Graph) o "cold" (Support Graph)
        
        Returns:
            GraphExecutionResult con intents generados (si Decision Graph)
        """
        entry_node_id = graph.get("entry_node")
        nodes = graph.get("nodes", {})
        
        if not entry_node_id:
            return GraphExecutionResult(
                intents=[],
                execution_trace=[],
                duration_ms=0.0,
                success=False,
                error_message="Graph missing 'entry_node'"
            )
        
        if entry_node_id not in nodes:
            return GraphExecutionResult(
                intents=[],
                execution_trace=[],
                duration_ms=0.0,
                success=False,
                error_message=f"Entry node '{entry_node_id}' not found in graph"
            )
        
        # Ejecutar grafo de forma secuencial
        current_node_id = entry_node_id
        execution_trace = []
        intents: List[OrderIntent] = []
        error_message: Optional[str] = None
        
        start_time = time.perf_counter()
        
        try:
            while current_node_id:
                node_def = nodes.get(current_node_id)
                if not node_def:
                    logger.warning(f"Node '{current_node_id}' not found in graph definition")
                    break
                
                node_type = node_def.get("type")
                if not node_type:
                    error_message = f"Node '{current_node_id}' missing 'type'"
                    break
                
                node_config = node_def.get("config", {})
                
                # Obtener clase del nodo
                node_class = self.node_registry.get(node_type)
                if not node_class:
                    error_message = f"Unknown node type: {node_type}"
                    logger.error(error_message)
                    break
                
                # Crear instancia del nodo
                node = node_class(node_config, context)
                
                # Ejecutar nodo
                node_start = time.perf_counter()
                try:
                    result = await node.execute()
                except Exception as e:
                    logger.exception(f"Error executing node '{current_node_id}' of type '{node_type}': {e}")
                    error_message = f"Node execution error: {str(e)}"
                    result = FailureResult(error=str(e))
                
                node_duration = (time.perf_counter() - node_start) * 1000  # ms
                
                # Observabilidad: Emitir métricas/eventos si está configurado
                if hasattr(context, 'strategy_id') and hasattr(context, 'observability_config'):
                    try:
                        from app.core.strategy_engine.observability import get_observability_service
                        obs_service = get_observability_service()
                        obs_service.log_node_execution(
                            strategy_id=context.strategy_id,
                            node_id=current_node_id,
                            node_type=node_type,
                            duration_ms=node_duration,
                            success=not isinstance(result, FailureResult),
                            error=result.error if isinstance(result, FailureResult) else None,
                            observability_config=context.observability_config
                        )
                    except Exception as e:
                        logger.warning(f"Error in observability logging: {e}")
                
                # ⚠️ DEPRECATION WARNING: emit_execution_intent está deprecado en Decision Graph
                if node_type == "emit_execution_intent" and path_type == "hot":
                    warnings.warn(
                        f"⚠️ DEPRECATED: Node 'emit_execution_intent' is deprecated in Decision Graphs. "
                        f"Use 'build_plan' + 'emit_plan_intent' instead. "
                        f"This node can still be used in Execution Graphs if needed.",
                        DeprecationWarning,
                        stacklevel=2
                    )
                    logger.warning(
                        f"⚠️ DEPRECATED: Node '{current_node_id}' uses 'emit_execution_intent' in Decision Graph. "
                        f"Consider migrating to 'build_plan' + 'emit_plan_intent'."
                    )
                
                # Registrar ejecución
                execution_trace.append({
                    "node_id": current_node_id,
                    "node_type": node_type,
                    "duration_ms": round(node_duration, 3),
                    "result_type": type(result).__name__,
                    "result": self._result_to_dict(result)
                })
                
                # Si el nodo emitió un intent, agregarlo
                if isinstance(result, ExecutionIntentResult):
                    if result.intent:
                        intents.append(result.intent)
                
                # Si el nodo creó un plan, guardar plan_id en contexto
                if isinstance(result, PlanResult):
                    context.last_plan_id = result.plan_id
                    context.plan_id = result.plan_id  # También en plan_id para compatibilidad
                
                # Si hay un error, detener ejecución
                if isinstance(result, FailureResult):
                    error_message = result.error
                    break
                
                # Determinar siguiente nodo
                current_node_id = self._get_next_node(node_def, result)
                
        except Exception as e:
            logger.exception(f"Error executing graph: {e}")
            error_message = str(e)
        
        total_duration = (time.perf_counter() - start_time) * 1000  # ms
        
        return GraphExecutionResult(
            intents=intents,
            execution_trace=execution_trace,
            duration_ms=round(total_duration, 3),
            success=error_message is None,
            error_message=error_message
        )
    
    def _get_next_node(self, node_def: Dict[str, Any], result: NodeResult) -> Optional[str]:
        """
        Determina el siguiente nodo basado en el resultado.
        
        Soporta:
        - "next": siguiente nodo directo
        - "on_true"/"on_false": para ConditionalResult
        - "on_success"/"on_failure": para SuccessResult/FailureResult
        """
        # Si hay un "next" directo
        if "next" in node_def:
            return node_def["next"]
        
        # Si hay condiciones (on_true, on_false)
        if isinstance(result, ConditionalResult):
            if result.condition and "on_true" in node_def:
                return node_def["on_true"]
            elif not result.condition and "on_false" in node_def:
                return node_def["on_false"]
        
        # Si hay on_success/on_failure
        if isinstance(result, (SuccessResult, PlanResult, CalculationResult, ExecutionResult)):
            if "on_success" in node_def:
                return node_def["on_success"]
        elif isinstance(result, FailureResult):
            if "on_failure" in node_def:
                return node_def["on_failure"]
        
        # No hay siguiente nodo
        return None
    
    def _result_to_dict(self, result: NodeResult) -> Dict[str, Any]:
        """Convierte un resultado de nodo a diccionario."""
        if isinstance(result, ConditionalResult):
            return {
                "condition": result.condition,
                "data": result.data
            }
        elif isinstance(result, ExecutionIntentResult):
            if result.intent:
                return {
                    "intent": {
                        "side": result.intent.side,
                        "outcome": result.intent.outcome,
                        "price": float(result.intent.price),
                        "size": float(result.intent.size),
                    }
                }
            else:
                return {"intent": None}
        elif isinstance(result, PlanResult):
            return {
                "plan_id": str(result.plan_id),
                "success": True
            }
        elif isinstance(result, CalculationResult):
            return {
                "size": result.size,
                "price": result.price,
                "size_usdc": result.size_usdc
            }
        elif isinstance(result, ExecutionResult):
            return {
                "plan_id": str(result.plan_id),
                "legs_status": result.legs_status,
                "success": result.success,
                "error": result.error
            }
        elif isinstance(result, FailureResult):
            return {"error": result.error}
        elif isinstance(result, SuccessResult):
            return {"success": True}
        else:
            return {"type": type(result).__name__}

