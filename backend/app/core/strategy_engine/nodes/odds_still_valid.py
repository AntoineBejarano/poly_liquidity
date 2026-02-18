"""
Odds Still Valid Node - Guardrail que verifica que las cuotas sigan vigentes.

Execution Graph. Config: source_id (PS3838).
Por ahora retorna condition=True para permitir encadenar con place_bet.
En Fase 3 se comparará con odds del TipIntent.
"""
from typing import Any

from app.core.strategy_engine.nodes.base import GraphNode, ConditionalResult


class OddsStillValidNode(GraphNode):
    """
    Guardrail: verifica que las odds del evento sigan vigentes en PS3838.
    Retorna ConditionalResult(True) para continuar o False para fall.
    """

    async def execute(self) -> Any:
        # TODO: llamar Get Odds/Get Line y comparar con context.tip_intent
        _ = self.config.get("source_id")
        return ConditionalResult(True, {})
