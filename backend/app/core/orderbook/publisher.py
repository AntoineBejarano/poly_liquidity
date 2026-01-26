"""
OrderbookPublisher - Publica OrderbookState a State Cache.
"""
import logging
from typing import Optional
from .models import OrderbookState
from app.core.strategy_engine.state_cache_service import StateCacheService

logger = logging.getLogger(__name__)


class OrderbookPublisher:
    """
    Publica OrderbookState a State Cache.
    
    Key: pm.orderbook.{asset_id}
    TTL: 120s
    """
    
    def __init__(self, state_cache_service: StateCacheService):
        """
        Args:
            state_cache_service: Servicio de State Cache
        """
        self.state_cache = state_cache_service
    
    async def publish(
        self,
        asset_id: str,
        orderbook_state: OrderbookState,
        ttl_seconds: int = 120
    ) -> None:
        """
        Publica OrderbookState a State Cache.
        
        Args:
            asset_id: Asset ID (token ID)
            orderbook_state: Estado del orderbook
            ttl_seconds: TTL en segundos (default: 120s)
        """
        cache_key = f"pm.orderbook.{asset_id}"
        
        try:
            # Convertir Pydantic model a dict para serialización
            state_dict = orderbook_state.dict()
            
            await self.state_cache.set(
                cache_key=cache_key,
                value=state_dict,
                ttl_seconds=ttl_seconds
            )
            
            logger.debug(
                f"Published orderbook state for asset_id={asset_id} to State Cache",
                extra={
                    "component": "orderbook",
                    "event": "publish_state",
                    "asset_id": asset_id,
                    "cache_key": cache_key
                }
            )
        except Exception as e:
            logger.error(
                f"Error publishing orderbook state for asset_id={asset_id}: {e}",
                exc_info=True,
                extra={
                    "component": "orderbook",
                    "event": "publish_error",
                    "asset_id": asset_id
                }
            )
            raise


