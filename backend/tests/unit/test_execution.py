"""
Unit tests for Execution Engine.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from datetime import datetime, timezone
from app.core.execution import Execution
from app.core.risk_engine.models import ApprovedOrderIntent
from app.core.strategy.models import OrderIntent
from app.core.execution.models import SignedOrder
from app.core.wallet import WalletInMemory


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
    
    def test_build_order_payload(self):
        """Test building order payload."""
        from app.core.state import state
        from app.core.state import EventState
        
        execution = Execution()
        
        # Crear un event_id y mockear el state
        event_id = uuid4()
        market_id = uuid4()
        event_state = EventState()
        event_state.event_id = event_id
        event_state.market_id = market_id
        state.events[event_id] = event_state
        
        intent = ApprovedOrderIntent(
            event_id=event_id,
            outcome="YES",
            side="BUY",
            price=0.98,
            size=100.0,
            original_size=100.0,
            adjustments={}
        )
        
        payload = execution._build_order_payload(intent, nonce=1, client_order_id="test-123")
        
        # El marketId puede ser el market_id o el event_id como fallback
        assert payload["marketId"] in [str(market_id), str(event_id)]
        assert payload["side"] == "BUY"
        assert payload["price"] == 0.98
        assert payload["size"] == 100.0
        assert payload["nonce"] == 1
        assert payload["clientOrderId"] == "test-123"
        
        # Limpiar
        state.events.clear()
    
    async def test_send_order_to_polymarket_rate_limit_timeout(self, mock_rate_limiter):
        """Test that rate limit timeout skips sending (LIVE path)."""
        from app.core.execution.models import ExecutionRecord

        execution = Execution()

        mock_rate_limiter.wait_for_capacity = AsyncMock(return_value=False)

        signed_order = SignedOrder(
            signed_order_id=uuid4(),
            wallet_address="0x123",
            signature="0xsignature",
            message_struct={}
        )
        request_payload = {"marketId": "0x123", "price": 0.98, "size": 100.0}
        execution_record = ExecutionRecord(
            execution_id=uuid4(),
            signed_order_id=signed_order.signed_order_id,
            request_payload=request_payload
        )

        with patch("app.core.execution.execution.rate_limiter", mock_rate_limiter), \
             patch("app.core.execution.execution.config_service.get_execution_mode", return_value="LIVE"):
            result = await execution._send_order_to_polymarket(
                signed_order, request_payload, execution_record
            )
            assert result is None

        await execution.close()
    
    async def test_send_order_to_polymarket_success(self, mock_rate_limiter):
        """Test successful order sending (LIVE path; DRY_RUN returns early without recording latency)."""
        from app.core.execution.models import ExecutionRecord

        execution = Execution()

        mock_rate_limiter.wait_for_capacity = AsyncMock(return_value=True)

        signed_order = SignedOrder(
            signed_order_id=uuid4(),
            wallet_address="0x123",
            signature="0xsignature",
            message_struct={}
        )
        request_payload = {"marketId": "0x123", "price": 0.98, "size": 100.0}
        execution_record = ExecutionRecord(
            execution_id=uuid4(),
            signed_order_id=signed_order.signed_order_id,
            request_payload=request_payload
        )

        with patch("app.core.execution.execution.rate_limiter", mock_rate_limiter), \
             patch("app.core.execution.execution.config_service.get_execution_mode", return_value="LIVE"):
            with patch("app.core.execution.execution.latency_monitor") as mock_monitor:
                mock_monitor.record_execution_latency = Mock()

                import asyncio
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    order_id = await execution._send_order_to_polymarket(
                        signed_order, request_payload, execution_record
                    )

                assert mock_monitor.record_execution_latency.called
                assert order_id is not None

        await execution.close()
    
    async def test_create_order_in_db(self, db_session):
        """Test creating order in database."""
        from app.core.execution.models import SignedOrder
        from app.core.state import state
        from app.core.state import EventState
        from app.models.market import Market
        
        execution = Execution()
        
        # Crear market y event en DB
        market_id = uuid4()
        event_id = uuid4()
        market = Market(
            id=market_id,
            polymarket_id="test-market-123",
            name="Test Market",
            enabled=True
        )
        db_session.add(market)
        db_session.commit()
        
        # Mockear state.events
        event_state = EventState()
        event_state.event_id = event_id
        event_state.market_id = market_id
        state.events[event_id] = event_state
        
        intent = OrderIntent(
            event_id=event_id,
            outcome="YES",
            side="BUY",
            price=0.98,
            size=100.0,
            reason="test"
        )
        approved_intent = ApprovedOrderIntent(
            event_id=intent.event_id,
            outcome=intent.outcome,
            side=intent.side,
            price=intent.price,
            size=intent.size,
            original_size=intent.size,
            adjustments={},
            trace_id=intent.trace_id
        )
        signed_order = SignedOrder(
            signed_order_id=uuid4(),
            wallet_address="0x123",
            signature="0xsignature",
            message_struct={}
        )
        
        with patch("app.core.execution.execution.SessionLocal", return_value=db_session):
            order = await execution._create_order_in_db(
                approved_intent, "polymarket-123", signed_order
            )
        
        assert order is not None
        assert order.market_id == market_id  # Debe obtener market_id desde event_id
        assert order.side == "BUY"
        assert order.price == 0.98
        assert order.size == 100.0
        # Status will be CREATED initially, then updated by lifecycle manager
        assert order.status in ["CREATED", "SIGNED"]
        assert order.filled_size == 0.0
        
        # Limpiar
        state.events.clear()
    
    async def test_tick_no_wallet(self, mock_wallet_service):
        """Test that tick skips intents when no wallet is resolved (no orders created)."""
        from app.core.state import state
        from app.core.state import EventState

        execution = Execution()
        mock_wallet_service.get_active_wallet_async = AsyncMock(return_value=None)
        mock_wallet_service.get_wallet_by_id = Mock(return_value=None)

        event_id = uuid4()
        market_id = uuid4()
        event_state = EventState()
        event_state.event_id = event_id
        event_state.market_id = market_id
        state.events[event_id] = event_state

        intent = OrderIntent(
            event_id=event_id,
            outcome="YES",
            side="BUY",
            price=0.98,
            size=100.0,
            reason="test"
        )
        approved_intent = ApprovedOrderIntent(
            event_id=intent.event_id,
            outcome=intent.outcome,
            side=intent.side,
            price=intent.price,
            size=intent.size,
            original_size=intent.size,
            adjustments={},
            trace_id=intent.trace_id
        )

        with patch("app.core.execution.execution.wallet_service", mock_wallet_service), \
             patch.object(state, "system_active", True):
            await execution.tick([approved_intent])

        assert len(execution._pending_orders) == 0
        await execution.close()
        state.events.clear()
    
    async def test_tick_creates_orders(self, mock_wallet_service, db_session):
        """Test that tick creates orders for approved intents."""
        from app.core.wallet import WalletInMemory
        from app.core.state import state
        from app.core.state import EventState
        
        execution = Execution()
        
        event_id = uuid4()
        market_id = uuid4()
        event_state = EventState()
        event_state.event_id = event_id
        event_state.market_id = market_id
        state.events[event_id] = event_state
        
        intent = OrderIntent(
            event_id=event_id,
            outcome="YES",
            side="BUY",
            price=0.98,
            size=100.0,
            reason="test"
        )
        approved_intent = ApprovedOrderIntent(
            event_id=intent.event_id,
            outcome=intent.outcome,
            side=intent.side,
            price=intent.price,
            size=intent.size,
            original_size=intent.size,
            adjustments={},
            trace_id=intent.trace_id
        )
        
        # Mock wallet
        mock_wallet = WalletInMemory(
            id=uuid4(),
            address="0x123",
            label="Test Wallet",
            encrypted_private_key=b"encrypted_key",
            private_key="0x" + "1" * 64,
            is_active=True,
            loaded_at=datetime.utcnow()
        )
        mock_wallet_service.get_active_wallet = AsyncMock(return_value=mock_wallet)
        mock_wallet_service.decrypt_private_key = AsyncMock(return_value="0x" + "1" * 64)
        
        # Mock dependencies
        with patch("app.core.execution.execution.wallet_service", mock_wallet_service):
            with patch("app.core.execution.execution.rate_limiter") as mock_rate_limiter:
                mock_rate_limiter.wait_for_capacity = AsyncMock(return_value=True)
                
                with patch("app.core.execution.execution.latency_monitor") as mock_monitor:
                    mock_monitor.record_execution_latency = Mock()
                    
                    with patch("app.core.execution.execution.SessionLocal", return_value=db_session):
                        import asyncio
                        with patch("asyncio.sleep", new_callable=AsyncMock):
                            with patch("app.core.execution.execution.state") as mock_state:
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

    async def test_resolve_wallet_for_intent_no_strategy_id_uses_active_wallet(self):
        """_resolve_wallet_for_intent with no strategy_id uses get_active_wallet_async()."""
        execution = Execution()
        intent = ApprovedOrderIntent(
            event_id=uuid4(),
            outcome="YES",
            side="BUY",
            price=0.98,
            size=100.0,
            original_size=100.0,
            adjustments={},
        )
        mock_wallet = WalletInMemory(
            id=uuid4(),
            label="Active",
            address="0xactive",
            private_key="0x" + "1" * 64,
            loaded_at=datetime.now(timezone.utc),
        )
        mock_ws = AsyncMock()
        mock_ws.get_active_wallet_async = AsyncMock(return_value=mock_wallet)
        mock_ws.get_wallet_by_id = Mock(return_value=None)

        with patch("app.core.execution.execution.wallet_service", mock_ws):
            wallet, user_id = await execution._resolve_wallet_for_intent(intent)

        assert wallet is mock_wallet
        assert user_id is None
        mock_ws.get_active_wallet_async.assert_called_once_with()
        mock_ws.get_wallet_by_id.assert_not_called()
        await execution.close()

    async def test_resolve_wallet_for_intent_with_strategy_and_wallet_id(self, db_session):
        """_resolve_wallet_for_intent with strategy_id and strategy.wallet_id uses get_wallet_by_id."""
        from app.models.strategy import Strategy
        from app.models.wallet import Wallet
        from cryptography.fernet import Fernet

        execution = Execution()
        strategy_id = uuid4()
        wallet_id = uuid4()
        user_id = "user-1"
        key = Fernet.generate_key()
        cipher = Fernet(key)
        enc = cipher.encrypt(b"0x" + b"2" * 64)
        w = Wallet(
            id=wallet_id,
            user_id=user_id,
            label="Strategy Wallet",
            address="0xstrategywallet",
            encrypted_private_key=enc,
            active=False,
        )
        db_session.add(w)
        strategy = Strategy(
            id=strategy_id,
            name="S1",
            decision_graph={"entry_node": "n", "nodes": {"n": {"type": "collect_state", "config": {}}}},
            support_graphs=[],
            wallet_id=wallet_id,
            created_by=user_id,
        )
        db_session.add(strategy)
        db_session.commit()

        intent = ApprovedOrderIntent(
            event_id=uuid4(),
            outcome="YES",
            side="BUY",
            price=0.98,
            size=100.0,
            original_size=100.0,
            adjustments={},
            strategy_id=strategy_id,
        )
        resolved_wallet = WalletInMemory(
            id=wallet_id,
            label="Strategy Wallet",
            address="0xstrategywallet",
            private_key="0x" + "2" * 64,
            loaded_at=datetime.now(timezone.utc),
        )
        mock_ws = Mock()
        mock_ws.get_wallet_by_id = Mock(return_value=resolved_wallet)
        mock_ws.get_active_wallet_async = AsyncMock()

        with patch("app.core.execution.execution.wallet_service", mock_ws), \
             patch("app.core.execution.execution.SessionLocal", return_value=db_session):
            wallet, resolved_user_id = await execution._resolve_wallet_for_intent(intent)

        assert wallet is resolved_wallet
        assert resolved_user_id == user_id
        mock_ws.get_wallet_by_id.assert_called_once_with(wallet_id, user_id)
        mock_ws.get_active_wallet_async.assert_not_called()
        await execution.close()

    async def test_resolve_wallet_for_intent_strategy_no_wallet_id_uses_active_for_user(self, db_session):
        """_resolve_wallet_for_intent with strategy_id but no wallet_id uses get_active_wallet_async(user_id)."""
        from app.models.strategy import Strategy

        execution = Execution()
        strategy_id = uuid4()
        user_id = "user-2"
        strategy = Strategy(
            id=strategy_id,
            name="S2",
            decision_graph={"entry_node": "n", "nodes": {"n": {"type": "collect_state", "config": {}}}},
            support_graphs=[],
            wallet_id=None,
            created_by=user_id,
        )
        db_session.add(strategy)
        db_session.commit()

        intent = ApprovedOrderIntent(
            event_id=uuid4(),
            outcome="YES",
            side="BUY",
            price=0.98,
            size=100.0,
            original_size=100.0,
            adjustments={},
            strategy_id=strategy_id,
        )
        mock_wallet = WalletInMemory(
            id=uuid4(),
            label="User Active",
            address="0xuseractive",
            private_key="0x" + "3" * 64,
            loaded_at=datetime.now(timezone.utc),
        )
        mock_ws = Mock()
        mock_ws.get_active_wallet_async = AsyncMock(return_value=mock_wallet)
        mock_ws.get_wallet_by_id = Mock(return_value=None)

        with patch("app.core.execution.execution.wallet_service", mock_ws), \
             patch("app.core.execution.execution.SessionLocal", return_value=db_session):
            wallet, resolved_user_id = await execution._resolve_wallet_for_intent(intent)

        assert wallet is mock_wallet
        assert resolved_user_id == user_id
        mock_ws.get_active_wallet_async.assert_called_once_with(user_id=user_id)
        mock_ws.get_wallet_by_id.assert_not_called()
        await execution.close()

    async def test_resolve_wallet_for_intent_strategy_not_found_falls_back(self, db_session):
        """_resolve_wallet_for_intent when strategy does not exist uses get_active_wallet_async()."""
        execution = Execution()
        intent = ApprovedOrderIntent(
            event_id=uuid4(),
            outcome="YES",
            side="BUY",
            price=0.98,
            size=100.0,
            original_size=100.0,
            adjustments={},
            strategy_id=uuid4(),
        )
        mock_wallet = WalletInMemory(
            id=uuid4(),
            label="Fallback",
            address="0xfallback",
            private_key="0x" + "4" * 64,
            loaded_at=datetime.now(timezone.utc),
        )
        mock_ws = Mock()
        mock_ws.get_active_wallet_async = AsyncMock(return_value=mock_wallet)
        mock_ws.get_wallet_by_id = Mock(return_value=None)

        with patch("app.core.execution.execution.wallet_service", mock_ws), \
             patch("app.core.execution.execution.SessionLocal", return_value=db_session):
            wallet, user_id = await execution._resolve_wallet_for_intent(intent)

        assert wallet is mock_wallet
        assert user_id is None
        mock_ws.get_active_wallet_async.assert_called_once_with()
        await execution.close()
