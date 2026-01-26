"""
Tests para OrderbookWSRouter.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time
from app.core.orderbook.ws_router import OrderbookWSRouter
from app.core.orderbook.orchestrator import OrderbookOrchestrator
from app.core.orderbook.publisher import OrderbookPublisher
from app.core.orderbook.models import OrderbookLevel


@pytest.mark.asyncio
async def test_ws_router_handle_book_update_success():
    """Test successful book update handling."""
    # Mock orchestrator
    mock_orchestrator = MagicMock()
    mock_book = MagicMock()
    mock_book.compute_bbo.return_value = (0.50, 0.52, 0.51, 400.0)
    mock_book.get_bids.return_value = [OrderbookLevel(price=0.50, size=10)]
    mock_book.get_asks.return_value = [OrderbookLevel(price=0.52, size=20)]
    mock_orchestrator.get_book.return_value = mock_book
    
    # Mock publisher
    mock_publisher = MagicMock()
    mock_publisher.publish = AsyncMock()
    
    router = OrderbookWSRouter(mock_orchestrator, mock_publisher)
    
    # Book message
    book_msg = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [{"price": ".50", "size": "10"}],
        "asks": [{"price": ".52", "size": "20"}],
        "timestamp": str(int(time.time() * 1000))
    }
    
    await router.handle_book_update(book_msg)
    
    # Verificar que se llamó ingest_book_msg
    mock_orchestrator.ingest_book_msg.assert_called_once()
    
    # Verificar que se llamó publish
    mock_publisher.publish.assert_called_once()


@pytest.mark.asyncio
async def test_ws_router_handle_book_update_missing_asset_id():
    """Test book update with missing asset_id."""
    mock_orchestrator = MagicMock()
    mock_publisher = MagicMock()
    
    router = OrderbookWSRouter(mock_orchestrator, mock_publisher)
    
    book_msg = {
        "event_type": "book",
        # Missing asset_id
        "bids": [{"price": ".50", "size": "10"}],
        "asks": [{"price": ".52", "size": "20"}],
        "timestamp": "1000"
    }
    
    await router.handle_book_update(book_msg)
    
    # No debe llamar ingest ni publish
    mock_orchestrator.ingest_book_msg.assert_not_called()
    mock_publisher.publish.assert_not_called()


@pytest.mark.asyncio
async def test_ws_router_handle_book_update_no_book():
    """Test book update when book doesn't exist."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.get_book.return_value = None  # No book
    
    mock_publisher = MagicMock()
    
    router = OrderbookWSRouter(mock_orchestrator, mock_publisher)
    
    book_msg = {
        "event_type": "book",
        "asset_id": "123",
        "bids": [{"price": ".50", "size": "10"}],
        "asks": [{"price": ".52", "size": "20"}],
        "timestamp": "1000"
    }
    
    await router.handle_book_update(book_msg)
    
    # No debe llamar publish si no hay book
    mock_publisher.publish.assert_not_called()


@pytest.mark.asyncio
async def test_ws_router_handle_book_update_no_bbo():
    """Test book update when no BBO available."""
    mock_orchestrator = MagicMock()
    mock_book = MagicMock()
    mock_book.compute_bbo.return_value = (None, None, None, None)  # No BBO
    mock_orchestrator.get_book.return_value = mock_book
    
    mock_publisher = MagicMock()
    
    router = OrderbookWSRouter(mock_orchestrator, mock_publisher)
    
    book_msg = {
        "event_type": "book",
        "asset_id": "123",
        "bids": [],
        "asks": [],
        "timestamp": "1000"
    }
    
    await router.handle_book_update(book_msg)
    
    # No debe llamar publish si no hay BBO
    mock_publisher.publish.assert_not_called()


@pytest.mark.asyncio
async def test_ws_router_handle_book_update_error():
    """Test book update error handling."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.ingest_book_msg.side_effect = Exception("Parse error")
    
    mock_publisher = MagicMock()
    
    router = OrderbookWSRouter(mock_orchestrator, mock_publisher)
    
    book_msg = {
        "event_type": "book",
        "asset_id": "123",
        "bids": [{"price": ".50"}],  # Invalid structure
        "asks": [{"price": ".52", "size": "20"}],
        "timestamp": "1000"
    }
    
    # Debe manejar el error sin crashear
    await router.handle_book_update(book_msg)
    
    # No debe llamar publish si hay error
    mock_publisher.publish.assert_not_called()


@pytest.mark.asyncio
async def test_ws_router_handle_book_update_empty_bids_asks():
    """Test book update with empty bids/asks after parsing."""
    mock_orchestrator = MagicMock()
    mock_book = MagicMock()
    mock_book.compute_bbo.return_value = (0.50, 0.52, 0.51, 400.0)
    mock_book.get_bids.return_value = []  # Empty
    mock_book.get_asks.return_value = []  # Empty
    mock_orchestrator.get_book.return_value = mock_book
    
    mock_publisher = MagicMock()
    mock_publisher.publish = AsyncMock()  # Fix: debe ser AsyncMock
    
    router = OrderbookWSRouter(mock_orchestrator, mock_publisher)
    
    book_msg = {
        "event_type": "book",
        "asset_id": "123",
        "bids": [],  # Empty
        "asks": [],  # Empty
        "timestamp": str(int(time.time() * 1000))
    }
    
    await router.handle_book_update(book_msg)
    
    # Debe llamar publish aunque bids/asks estén vacíos (si hay BBO)
    mock_publisher.publish.assert_called_once()


@pytest.mark.asyncio
async def test_ws_router_handle_book_update_timestamp_truncation():
    """Test book update with >100 timestamps (truncation)."""
    mock_orchestrator = MagicMock()
    mock_book = MagicMock()
    mock_book.compute_bbo.return_value = (0.50, 0.52, 0.51, 400.0)
    mock_book.get_bids.return_value = [OrderbookLevel(price=0.50, size=10)]
    mock_book.get_asks.return_value = [OrderbookLevel(price=0.52, size=20)]
    mock_orchestrator.get_book.return_value = mock_book
    
    mock_publisher = MagicMock()
    mock_publisher.publish = AsyncMock()
    
    router = OrderbookWSRouter(mock_orchestrator, mock_publisher)
    
    # Llenar timestamps hasta >100
    now_ms = int(time.time() * 1000)
    for i in range(150):
        router.update_timestamps["123"] = list(range(now_ms - 150000, now_ms - 150000 + i + 1))
    
    book_msg = {
        "event_type": "book",
        "asset_id": "123",
        "bids": [{"price": ".50", "size": "10"}],
        "asks": [{"price": ".52", "size": "20"}],
        "timestamp": str(now_ms)
    }
    
    await router.handle_book_update(book_msg)
    
    # Verificar que se truncó a 100
    assert len(router.update_timestamps["123"]) <= 100

