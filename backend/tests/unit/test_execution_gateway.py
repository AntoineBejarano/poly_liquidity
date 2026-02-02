"""
Tests unitarios para Execution Gateway (F1 - DoD 4.2, 4.3, 4.4).

Verifican invariantes I1, I2: con execution_mode != LIVE o system_active=false
no se invoca al CLOB (cero llamadas).
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.core.execution.gateway import (
    ExecutionGateway,
    ExecutionGatewayRequest,
    ExecutionGatewayResult,
    GatewayDecision,
    SourcePath,
)


class TestExecutionGateway:
    """Tests para Execution Gateway (I1, I2)."""

    @pytest.fixture
    def mock_clob(self):
        """Mock del cliente CLOB."""
        m = Mock()
        m.is_available = Mock(return_value=True)
        m.create_limit_order = AsyncMock(return_value={"id": "clob_order_123"})
        m.create_market_order = AsyncMock(return_value={"id": "clob_order_456"})
        m.cancel_order = AsyncMock(return_value={"canceled": ["order_1"], "not_canceled": {}})
        return m

    @pytest.fixture
    def submit_request(self):
        """Request de submit_order típica."""
        return ExecutionGatewayRequest(
            trace_id="trace-1",
            strategy_id="strat-1",
            plan_id="plan-1",
            leg_id="leg-1",
            idempotency_key="key-1",
            payload={
                "order_kind": "limit",
                "token_id": "token_1",
                "price": 0.5,
                "size": 10.0,
                "side": "BUY",
                "order_type": "GTC",
            },
            operation="submit_order",
            source_path=SourcePath.PLAN,
        )

    @pytest.mark.asyncio
    async def test_submit_order_dry_run_zero_clob_calls(self, mock_clob, submit_request):
        """DoD 4.2: con execution_mode != LIVE cero llamadas al CLOB."""
        gateway = ExecutionGateway(clob_delegate=mock_clob)
        with patch("app.core.execution.gateway.config_service.get_execution_mode", return_value="DRY_RUN"):
            result = await gateway.submit_order(submit_request)

        assert result.decision == GatewayDecision.SKIP_DRY_RUN
        assert result.platform_order_id is not None
        assert result.platform_order_id.startswith("dry_run_")
        mock_clob.create_limit_order.assert_not_called()
        mock_clob.create_market_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_submit_order_system_paused_zero_clob_calls(self, mock_clob, submit_request):
        """DoD 4.3: con system_active=false cero llamadas al CLOB."""
        gateway = ExecutionGateway(clob_delegate=mock_clob)
        state_mock = Mock()
        state_mock.system_active = False
        with patch("app.core.execution.gateway.config_service.get_execution_mode", return_value="LIVE"), \
             patch("app.core.execution.gateway.state", state_mock):
            result = await gateway.submit_order(submit_request)

        assert result.decision == GatewayDecision.SKIP_PAUSED
        assert result.platform_order_id is not None
        assert result.platform_order_id.startswith("skip_paused_")
        mock_clob.create_limit_order.assert_not_called()
        mock_clob.create_market_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_submit_order_live_sends_to_clob(self, mock_clob, submit_request):
        """Con LIVE y system_active=True el Gateway invoca al CLOB."""
        from app.core.latency_monitor import LatencyStatus

        gateway = ExecutionGateway(clob_delegate=mock_clob)
        state_mock = Mock()
        state_mock.system_active = True
        with patch("app.core.execution.gateway.config_service.get_execution_mode", return_value="LIVE"), \
             patch("app.core.execution.gateway.state", state_mock), \
             patch("app.core.execution.gateway.latency_monitor.get_status", return_value=LatencyStatus.GREEN):
            result = await gateway.submit_order(submit_request)

        assert result.decision == GatewayDecision.SEND
        assert result.platform_order_id == "clob_order_123"
        mock_clob.create_limit_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_order_dry_run_zero_clob_calls(self, mock_clob):
        """DoD 4.2: cancel con execution_mode != LIVE no llama al CLOB."""
        gateway = ExecutionGateway(clob_delegate=mock_clob)
        request = ExecutionGatewayRequest(
            trace_id="trace-1",
            strategy_id="strat-1",
            payload={"platform_order_id": "order_123", "order_id": "order_123"},
            operation="cancel_order",
            source_path=SourcePath.PLAN,
        )
        with patch("app.core.execution.gateway.config_service.get_execution_mode", return_value="DRY_RUN"):
            result = await gateway.cancel_order(request)

        assert result.decision == GatewayDecision.SKIP_DRY_RUN
        mock_clob.cancel_order.assert_not_called()
