"""
Tests para política v2: no CLOB global, fail closed con wallet.

- Deactivate con pending orders y sin wallet => 409 WALLET_NOT_CONFIGURED.
- /markets (Gamma) funciona sin wallet; wallet-data falla sin wallet.
- Execution intent sin user_id => no llama CLOB (skip/FAILED).
- WS USER subscribe requiere wallet (409 sin wallet).
- Cuando Strategy tenga execution_user_id, el código debe usarlo (test de regresión).
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from datetime import datetime, timezone

from app.api.errors import WALLET_NOT_CONFIGURED_STATUS, WALLET_NOT_CONFIGURED_DETAIL
from app.models.strategy import Strategy


class TestWalletNotConfiguredResponse:
    """Respuesta estándar 409 WALLET_NOT_CONFIGURED."""

    def test_wallet_not_configured_status_is_409(self):
        assert WALLET_NOT_CONFIGURED_STATUS == 409

    def test_wallet_not_configured_detail_has_error_and_message(self):
        assert WALLET_NOT_CONFIGURED_DETAIL["error"] == "WALLET_NOT_CONFIGURED"
        assert "wallet" in WALLET_NOT_CONFIGURED_DETAIL["message"].lower()


class TestStrategyModelExecutionUserId:
    """
    Plan §3.1: por ahora execution_user_id = created_by.
    Cuando el modelo tenga execution_user_id, los callers deben usarlo.
    Este test falla si el modelo tiene execution_user_id y el código no lo usa
    (regresión: asegurar que no olvidamos migrar).
    """

    def test_strategy_has_no_execution_user_id_yet(self):
        # Cuando se añada Strategy.execution_user_id, actualizar deactivate/adapter
        # para usarlo y cambiar este test a: assert hasattr(Strategy, 'execution_user_id')
        # y añadir test que deactivate usa strategy.execution_user_id cuando está presente.
        assert not hasattr(Strategy, "execution_user_id"), (
            "Strategy tiene execution_user_id: actualizar api/strategies (deactivate), "
            "strategy_engine y polymarket_adapter para usar execution_user_id en lugar de created_by."
        )


@pytest.mark.asyncio
class TestExecutionIntentWithoutUserId:
    """Execution engine: intent sin user_id no debe llamar a CLOB."""

    async def test_tick_without_user_id_for_clob_does_not_call_get_polymarket_client_for_user(self):
        from app.core.execution.execution import Execution
        from app.core.risk_engine.models import ApprovedOrderIntent
        from app.core.state import state

        execution = Execution()
        intent = ApprovedOrderIntent(
            event_id=uuid4(),
            outcome="YES",
            side="BUY",
            price=0.5,
            size=100.0,
            original_size=100.0,
            adjustments={},
        )
        intent.trace_id = str(uuid4())

        # Evitar ramas que tocan DB (system_active, latency, circuit)
        with patch.object(state, "system_active", True):
            with patch.object(execution, "_cancel_all_open_orders", new_callable=AsyncMock):
                with patch.object(
                    execution,
                    "_resolve_wallet_for_intent",
                    new_callable=AsyncMock,
                    return_value=(None, None),
                ):
                    with patch(
                        "app.core.execution.execution.get_polymarket_client_for_user",
                        new_callable=Mock,
                    ) as m_clob:
                        await execution.tick([intent])
                        m_clob.assert_not_called()
        await execution.close()
