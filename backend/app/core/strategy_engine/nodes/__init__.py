"""
Nodos del grafo para Strategy Engine.
"""
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
from app.core.strategy_engine.nodes.noop import NoOpNode
from app.core.strategy_engine.nodes.collect_state import CollectStateNode
from app.core.strategy_engine.nodes.edge_and_risk_check import EdgeAndRiskCheckNode
from app.core.strategy_engine.nodes.calculate_order_size import CalculateOrderSizeNode
from app.core.strategy_engine.nodes.emit_execution_intent import EmitExecutionIntentNode
from app.core.strategy_engine.nodes.build_plan import BuildPlanNode
from app.core.strategy_engine.nodes.emit_plan_intent import EmitPlanIntentNode
from app.core.strategy_engine.nodes.fetch_external_source import FetchExternalSourceNode
from app.core.strategy_engine.nodes.update_state_cache import UpdateStateCacheNode
from app.core.strategy_engine.nodes.log import LogNode
from app.core.strategy_engine.nodes.execution_coordinator import ExecutionCoordinatorNode
from app.core.strategy_engine.nodes.retry_leg import RetryLegNode
from app.core.strategy_engine.nodes.compensate_plan import CompensatePlanNode
from app.core.strategy_engine.nodes.derive_plan import DerivePlanNode
from app.core.strategy_engine.nodes.calculate_indicators import CalculateIndicatorsNode
from app.core.strategy_engine.nodes.precheck import PrecheckNode

__all__ = [
    "GraphNode",
    "NodeResult",
    "ConditionalResult",
    "ExecutionIntentResult",
    "SuccessResult",
    "FailureResult",
    "PlanResult",
    "CalculationResult",
    "ExecutionResult",
    "NoOpNode",
    "CollectStateNode",
    "EdgeAndRiskCheckNode",
    "CalculateOrderSizeNode",
    "BuildPlanNode",
    "EmitPlanIntentNode",
    "EmitExecutionIntentNode",
    "ExecutionCoordinatorNode",
    "RetryLegNode",
    "CompensatePlanNode",
    "DerivePlanNode",
    "FetchExternalSourceNode",
    "UpdateStateCacheNode",
    "LogNode",
    "CalculateIndicatorsNode",
    "PrecheckNode",
]
