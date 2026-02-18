"""
Tests unitarios para el modelo TipIntent.
"""
import pytest
from uuid import uuid4
from decimal import Decimal

from app.models.tip_intent import TipIntent


class TestTipIntent:
    """Tests para el modelo TipIntent."""

    def test_tip_intent_creation_minimal(self):
        strategy_id = uuid4()
        tip = TipIntent(
            strategy_id=strategy_id,
            raw_text="Real Madrid vs Barcelona Over 2.5 @1.85",
            parsed={"partido": "Real Madrid vs Barcelona", "seleccion": "Over 2.5", "cuota": 1.85},
            status="PENDING",
        )
        assert tip.strategy_id == strategy_id
        assert tip.status == "PENDING"
        assert tip.parsed["partido"] == "Real Madrid vs Barcelona"
        assert tip.ps3838_event_id is None
        assert tip.ps3838_bet_id is None

    def test_tip_intent_with_ps3838_resolved(self):
        strategy_id = uuid4()
        tip = TipIntent(
            strategy_id=strategy_id,
            telegram_message_id="12345",
            telegram_chat_id="-100123",
            raw_text="Tip: Madrid vs Barça 1",
            parsed={"home": "Madrid", "away": "Barça", "seleccion": "1"},
            ps3838_event_id=Decimal("999"),
            ps3838_league_id=Decimal("5"),
            ps3838_odds=Decimal("2.10"),
            suggested_stake_usd=Decimal("50.00"),
            risk_class="medium",
            status="APPROVED",
        )
        assert tip.telegram_message_id == "12345"
        assert tip.ps3838_event_id == Decimal("999")
        assert tip.risk_class == "medium"
        assert tip.status == "APPROVED"
