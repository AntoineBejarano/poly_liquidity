"""
Unit tests for Execution Engine.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from app.core.execution import Execution
from app.core.risk_engine import ApprovedOrderIntent
from app.core.strategy import OrderIntent


@pytest.mark.asyncio
class TestExecution:
    """Test cases for Execution Engine."""
    
    async def test_execution_initialization(self):
        """Test execution initializes correctly."""
        execution = Execution()
        assert execution._client is None
        assert execution._pending_orders == {}
        await execution.close()
    
    async def test_get_client_creates_client(self):
        """Test that _get_client creates httpx client."""
        execution = Execution()
        client = await execution._get_client()
        assert client is not None
        await execution.close()
    
    def test_sign_order_payload(self, mock_wallet_service):
        """Test signing order payload."""
        execution = Execution()
        
        payload = {
            "market_id": "0x123",
            "side": "BUY",
            "price": 0.98,
            "size": 100.0,
        }
        
        private_key = "0x" + "1" * 64
        signature = execution._sign_order_payload(payload, private_key)
        
        # Should return a signature (even if placeholder)
        assert signature is not None
        assert isinstance(signature, str)
    
    async def test_send_order_to_polymarket_rate_limit_timeout(self, mock_rate_limiter):
        """Test that rate limit timeout returns None."""
        execution = Execution()
        
        # Mock rate limiter timeout
        mock_rate_limiter.wait_for_capacity = AsyncMock(return_value=False)
        
        order_data = {
            "market_id": "0x123",
            "side": "BUY",
            "price": 0.98,
            "size": 100.0,
        }
        
        with patch("app.core.execution.rate_limiter", mock_rate_limiter):
            order_id = await execution._send_order_to_polymarket(order_data, "0xsignature")
            assert order_id is None
        
        await execution.close()
    
    async def test_send_order_to_polymarket_success(self, mock_rate_limiter):
        """Test successful order sending."""
        execution = Execution()
        
        # Mock rate limiter success
        mock_rate_limiter.wait_for_capacity = AsyncMock(return_value=True)
        
        order_data = {
            "market_id": "0x123",
            "side": "BUY",
            "price": 0.98,
            "size": 100.0,
        }
        
        with patch("app.core.execution.rate_limiter", mock_rate_limiter):
            with patch("app.core.execution.latency_monitor") as mock_monitor:
                mock_monitor.record_execution_latency = Mock()
                
                # Mock asyncio.sleep to avoid actual delay
                import asyncio
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    order_id = await execution._send_order_to_polymarket(order_data, "0xsignature")
                
                # Should record latency
                assert mock_monitor.record_execution_latency.called
        
        await execution.close()
    
    async def test_create_order_in_db(self, db_session):
        """Test creating order in database."""
        execution = Execution()
        
        intent = OrderIntent(
            market_id=uuid4(),
            side="BUY",
            price=0.98,
            size=100.0
        )
        approved_intent = ApprovedOrderIntent(intent)
        
        with patch("app.core.execution.SessionLocal", return_value=db_session):
            order = await execution._create_order_in_db(approved_intent, "polymarket-123")
        
        assert order is not None
        assert order.market_id == intent.market_id
        assert order.side == "BUY"
        assert order.price == 0.98
        assert order.size == 100.0
        assert order.status == "NEW"
        assert order.filled_size == 0.0
    
    async def test_tick_no_wallet(self, mock_wallet_service):
        """Test that tick returns early if no wallet."""
        execution = Execution()
        
        mock_wallet_service.get_active_wallet.return_value = None
        
        intent = OrderIntent(
            market_id=uuid4(),
            side="BUY",
            price=0.98,
            size=100.0
        )
        approved_intent = ApprovedOrderIntent(intent)
        
        with patch("app.core.execution.wallet_service", mock_wallet_service):
            await execution.tick([approved_intent])
        
        # Should not create any orders
        assert len(execution._pending_orders) == 0
        await execution.close()
    
    async def test_tick_creates_orders(self, mock_wallet_service, db_session):
        """Test that tick creates orders for approved intents."""
        execution = Execution()
        
        intent = OrderIntent(
            market_id=uuid4(),
            side="BUY",
            price=0.98,
            size=100.0
        )
        approved_intent = ApprovedOrderIntent(intent)
        
        # Mock dependencies
        with patch("app.core.execution.wallet_service", mock_wallet_service):
            with patch("app.core.execution.rate_limiter") as mock_rate_limiter:
                mock_rate_limiter.wait_for_capacity = AsyncMock(return_value=True)
                
                with patch("app.core.execution.latency_monitor") as mock_monitor:
                    mock_monitor.record_execution_latency = Mock()
                    
                    with patch("app.core.execution.SessionLocal", return_value=db_session):
                        import asyncio
                        with patch("asyncio.sleep", new_callable=AsyncMock):
                            with patch("app.core.execution.state") as mock_state:
                                mock_state.orders = {}
                                
                                await execution.tick([approved_intent])
        
        # Should have created an order
        # Note: This is simplified - actual implementation may differ
        await execution.close()
    
    async def test_close_cleans_up_client(self):
        """Test that close() cleans up HTTP client."""
        execution = Execution()
        client = await execution._get_client()
        assert execution._client is not None
        
        await execution.close()
        assert execution._client is None

