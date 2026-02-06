"""
Unit tests for Strategies API: wallet_id (wallet por estrategia).

Verifica:
- _validate_wallet_for_user (404/403)
- strategy_to_dict y strategy_to_summary_dict incluyen wallet_id
- Create/update estrategia con wallet_id (validación y respuesta)
"""
import pytest
from uuid import uuid4
from fastapi import HTTPException

from app.api.strategies import (
    _validate_wallet_for_user,
    strategy_to_dict,
    strategy_to_summary_dict,
    StrategyCreate,
    StrategyUpdate,
)
from app.models.strategy import Strategy
from app.models.wallet import Wallet


USER_ID = "test-user-id"


class TestValidateWalletForUser:
    """Tests para _validate_wallet_for_user."""

    def test_raises_404_when_wallet_not_found(self, db_session):
        """Si la wallet no existe, lanza 404."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_wallet_for_user(db_session, uuid4(), USER_ID)
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    def test_raises_403_when_wallet_belongs_to_other_user(self, db_session):
        """Si la wallet es de otro usuario, lanza 403."""
        w = Wallet(
            id=uuid4(),
            user_id="other-user",
            label="Other",
            address="0x1111111111111111111111111111111111111111",
            encrypted_private_key=b"enc",
            active=False,
        )
        db_session.add(w)
        db_session.commit()
        wallet_id = w.id

        with pytest.raises(HTTPException) as exc_info:
            _validate_wallet_for_user(db_session, wallet_id, USER_ID)
        assert exc_info.value.status_code == 403
        assert "does not belong" in exc_info.value.detail.lower()

    def test_does_not_raise_when_wallet_belongs_to_user(self, db_session):
        """Si la wallet es del usuario, no lanza."""
        w = Wallet(
            id=uuid4(),
            user_id=USER_ID,
            label="Mine",
            address="0x2222222222222222222222222222222222222222",
            encrypted_private_key=b"enc",
            active=False,
        )
        db_session.add(w)
        db_session.commit()

        _validate_wallet_for_user(db_session, w.id, USER_ID)  # no raise


class TestStrategyDictWalletId:
    """Tests para wallet_id en strategy_to_dict y strategy_to_summary_dict."""

    @pytest.fixture
    def strategy_with_wallet(self, db_session):
        """Strategy con wallet_id."""
        from datetime import datetime, timezone
        s = Strategy(
            id=uuid4(),
            name="With Wallet",
            description="Desc",
            decision_graph={"entry_node": "n", "nodes": {"n": {"type": "collect_state", "config": {}}}},
            support_graphs=[],
            is_active=False,
            wallet_id=uuid4(),
            created_by=USER_ID,
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(s)
        db_session.commit()
        return s

    @pytest.fixture
    def strategy_without_wallet(self, db_session):
        """Strategy sin wallet_id."""
        from datetime import datetime, timezone
        s = Strategy(
            id=uuid4(),
            name="No Wallet",
            description="Desc",
            decision_graph={"entry_node": "n", "nodes": {"n": {"type": "collect_state", "config": {}}}},
            support_graphs=[],
            is_active=False,
            wallet_id=None,
            created_by=USER_ID,
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(s)
        db_session.commit()
        return s

    def test_strategy_to_dict_includes_wallet_id(self, strategy_with_wallet):
        """strategy_to_dict incluye wallet_id."""
        d = strategy_to_dict(strategy_with_wallet)
        assert "wallet_id" in d
        assert d["wallet_id"] == str(strategy_with_wallet.wallet_id)

    def test_strategy_to_dict_wallet_id_none(self, strategy_without_wallet):
        """strategy_to_dict devuelve wallet_id None cuando no hay wallet."""
        d = strategy_to_dict(strategy_without_wallet)
        assert d["wallet_id"] is None

    def test_strategy_to_summary_dict_includes_wallet_id(self, strategy_with_wallet):
        """strategy_to_summary_dict incluye wallet_id."""
        d = strategy_to_summary_dict(strategy_with_wallet)
        assert "wallet_id" in d
        assert d["wallet_id"] == str(strategy_with_wallet.wallet_id)


class TestStrategyCreateUpdateWalletId:
    """Tests para schema y validación de wallet_id en create/update."""

    def test_strategy_create_has_wallet_id_field(self):
        """StrategyCreate tiene campo wallet_id opcional."""
        assert "wallet_id" in StrategyCreate.model_fields
        assert StrategyCreate.model_fields["wallet_id"].is_required() is False

    def test_strategy_update_has_wallet_id_field(self):
        """StrategyUpdate tiene campo wallet_id opcional."""
        assert "wallet_id" in StrategyUpdate.model_fields
        assert StrategyUpdate.model_fields["wallet_id"].is_required() is False

    def test_strategy_create_with_wallet_id_accepts_uuid(self):
        """StrategyCreate acepta wallet_id como UUID."""
        wid = uuid4()
        payload = StrategyCreate(
            name="S",
            decision_graph={"entry_node": "n", "nodes": {"n": {"type": "collect_state", "config": {}}}},
            wallet_id=wid,
        )
        assert payload.wallet_id == wid
