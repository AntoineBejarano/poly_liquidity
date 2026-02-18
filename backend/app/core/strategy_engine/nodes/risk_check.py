"""
Risk Check Node - Guardrail que valida límites de riesgo antes de apostar.

Execution Graph. Config: max_stake_per_tip, max_daily_stake (opcional).
Por ahora retorna condition=True (pasar) para permitir encadenar con place_bet.
En Fase 3 se integrará con TipIntent y Risk Engine.
"""
from typing import Any, Dict

from app.core.strategy_engine.nodes.base import GraphNode, ConditionalResult, FailureResult


class RiskCheckNode(GraphNode):
    """
    Guardrail: valida que el stake no supere límites.
    Retorna ConditionalResult(True) para continuar o ConditionalResult(False) para fall.
    """

    async def execute(self) -> Any:
        # TODO: integrar con TipIntent y Risk Engine (max_daily_stake, max_stake_per_tip)
        _ = self.config.get("max_stake_per_tip")
        _ = self.config.get("max_daily_stake")
        return ConditionalResult(True, {})
