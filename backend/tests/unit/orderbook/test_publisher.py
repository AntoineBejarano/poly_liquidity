"""
Tests para OrderbookPublisher.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.orderbook.publisher import OrderbookPublisher
from app.core.orderbook.models import OrderbookState, OrderbookLevel


@pytest.mark.asyncio
async def test_publisher_publish_success():
    """Test successful publish to State Cache."""
    # Mock StateCacheService
    mock_state_cache = MagicMock()
    mock_state_cache.set = AsyncMock()
    
    publisher = OrderbookPublisher(mock_state_cache)
    
    orderbook_state = OrderbookState(
        asset_id="123",
        ts_ms=1000,
        best_bid_price=0.50,
        best_ask_price=0.52,
        spread_bps=400.0,
        mid=0.51,
        bids=[OrderbookLevel(price=0.50, size=10)],
        asks=[OrderbookLevel(price=0.52, size=20)],
        depth_usdc_at_50bps=1000.0,
        impact_bps_for_usdc_1000=30.0,
        concentration_top3_pct=0.5,
        update_rate_hz=5.0,
        staleness_ms=100
    )
    
    await publisher.publish("123", orderbook_state, ttl_seconds=120)
    
    # Verificar que se llamó set con los parámetros correctos
    mock_state_cache.set.assert_called_once()
    call_args = mock_state_cache.set.call_args
    assert call_args.kwargs["cache_key"] == "pm.orderbook.123"
    assert call_args.kwargs["ttl_seconds"] == 120
    assert "value" in call_args.kwargs


@pytest.mark.asyncio
async def test_publisher_publish_error():
    """Test publish error handling."""
    # Mock StateCacheService que lanza error
    mock_state_cache = MagicMock()
    mock_state_cache.set = AsyncMock(side_effect=Exception("DB error"))
    
    publisher = OrderbookPublisher(mock_state_cache)
    
    orderbook_state = OrderbookState(
        asset_id="123",
        ts_ms=1000,
        best_bid_price=0.50,
        best_ask_price=0.52
    )
    
    # Debe lanzar la excepción
    with pytest.raises(Exception, match="DB error"):
        await publisher.publish("123", orderbook_state)



