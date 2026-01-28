"""
Collect State Node - Recopila estado del State Cache.

Solo lee, nunca escribe.
"""
from typing import Dict, Any

from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult


class CollectStateNode(GraphNode):
    """
    Nodo que recopila estado del State Cache.
    
    Solo lee, nunca escribe.
    Lee desde State Cache y guarda en context.collected_state.
    """
    
    async def execute(self) -> SuccessResult:
        """
        Recopila estado del State Cache según las fuentes configuradas.
        
        Config:
            sources: List[str] - Lista de fuentes a recopilar
                - "market_state": Estado del mercado
                - "event_state": Estado del evento
                - "external_data": Datos externos
                - "risk_state": Estado de riesgo
                - "orderbook_state": Estado del orderbook (pm.orderbook.{asset_id})
        """
        sources = self.config.get("sources", [])
        collected_state: Dict[str, Any] = {}
        
        for source in sources:
            if source == "market_state":
                # Leer del State Cache
                cache_key = f"event.{self.context.event_id}.market_state"
                market_state = await self.context.state_cache.get(cache_key)
                collected_state["market_state"] = market_state
            
            elif source == "event_state":
                cache_key = f"event.{self.context.event_id}.event_state"
                event_state = await self.context.state_cache.get(cache_key)
                collected_state["event_state"] = event_state
            
            elif source == "external_data":
                # Leer todas las fuentes externas para este evento
                pattern = f"event.{self.context.event_id}.external_data.*"
                external_data = await self.context.state_cache.get_many(pattern)
                collected_state["external_data"] = external_data
            
            elif source == "risk_state":
                cache_key = f"strategy.{self.context.strategy_id}.risk_state"
                risk_state = await self.context.state_cache.get(cache_key)
                collected_state["risk_state"] = risk_state

            elif source == "orderbook_state":
                # Leer estado de orderbook desde pm.orderbook.{asset_id}
                # asset_id debe estar en context.metadata["asset_id"]
                asset_id = None
                metadata = getattr(self.context, "metadata", None)
                if isinstance(metadata, dict):
                    asset_id = metadata.get("asset_id")
                if asset_id:
                    cache_key = f"pm.orderbook.{asset_id}"
                    orderbook_state = await self.context.state_cache.get(cache_key)
                    collected_state["orderbook_state"] = orderbook_state
        
        # Guardar estado recopilado en el contexto
        if not hasattr(self.context, 'collected_state') or self.context.collected_state is None:
            self.context.collected_state = {}
        self.context.collected_state.update(collected_state)
        
        return SuccessResult()

