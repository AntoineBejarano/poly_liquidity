"""
Tests unitarios para PrecheckNode.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock
from uuid import uuid4

from app.core.strategy_engine.nodes.precheck import PrecheckNode
from app.core.strategy_engine.nodes.base import ConditionalResult
from app.core.strategy_engine.models import GraphExecutionContext


class TestPrecheckNode:
    """Tests para PrecheckNode."""

    @pytest.fixture
    def mock_plan(self):
        """Mock de ExecutionPlan."""
        plan = Mock()
        plan.id = uuid4()
        plan.trace_id = uuid4()
        plan.ttl_ms = 60000  # 60 segundos
        plan.created_at = datetime.now(timezone.utc)
        plan.legs = [
            {
                "leg_id": "leg_1",
                "side": "BUY",
                "target_price": 0.50,
                "size": 100,
                "metadata": {"asset_id": "abc123"}
            }
        ]
        return plan

    @pytest.fixture
    def mock_state_cache(self):
        """Mock de StateCacheService."""
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        return cache

    @pytest.fixture
    def mock_db(self, mock_plan):
        """Mock de DB session."""
        db = Mock()
        query_mock = Mock()
        filter_mock = Mock()
        filter_mock.first = Mock(return_value=mock_plan)
        query_mock.filter = Mock(return_value=filter_mock)
        db.query = Mock(return_value=query_mock)
        return db

    @pytest.fixture
    def context(self, mock_state_cache, mock_db, mock_plan):
        """Contexto de ejecución."""
        context = GraphExecutionContext(
            strategy_id=uuid4(),
            event_id=uuid4(),
            market_id=uuid4(),
            trace_id=uuid4(),
            state_cache=mock_state_cache,
            db=mock_db
        )
        context.plan_id = mock_plan.id
        return context

    @pytest.mark.asyncio
    async def test_precheck_passes_when_all_valid(self, context, mock_state_cache, mock_plan):
        """Test que precheck pasa cuando todas las validaciones son válidas."""
        # Orderbook fresco con precio cercano al target (drift ~1% = 100 bps < 200 bps limit)
        mock_state_cache.get = AsyncMock(return_value={
            "best_ask_price": 0.505,  # Drift = 1% = 100 bps
            "best_bid_price": 0.495,
            "staleness_ms": 500,  # Fresco
            "impact_bps_for_usdc_1000": 50  # Bajo impacto
        })

        config = {
            "plan_id": "{{plan.id}}",
            "max_book_staleness_ms": 2000,
            "drift_bps_limit": 200,  # 2%, suficiente para 1% drift
            "max_impact_bps": 200
        }

        node = PrecheckNode(config, context)
        result = await node.execute()

        assert isinstance(result, ConditionalResult)
        assert result.condition is True
        assert result.data["failures"] == []

    @pytest.mark.asyncio
    async def test_precheck_fails_on_stale_orderbook(self, context, mock_state_cache, mock_plan):
        """Test que precheck falla si el orderbook está desactualizado."""
        mock_state_cache.get = AsyncMock(return_value={
            "best_ask_price": 0.50,
            "staleness_ms": 5000,  # Muy viejo
            "impact_bps_for_usdc_1000": 50
        })

        config = {
            "plan_id": "{{plan.id}}",
            "max_book_staleness_ms": 2000
        }

        node = PrecheckNode(config, context)
        result = await node.execute()

        assert isinstance(result, ConditionalResult)
        assert result.condition is False
        assert any("orderbook_stale" in f for f in result.data["failures"])

    @pytest.mark.asyncio
    async def test_precheck_fails_on_price_drift(self, context, mock_state_cache, mock_plan):
        """Test que precheck falla si el precio se ha movido demasiado."""
        mock_state_cache.get = AsyncMock(return_value={
            "best_ask_price": 0.60,  # Drift = 20% = 2000 bps > 100 bps limit
            "staleness_ms": 500,
            "impact_bps_for_usdc_1000": 50
        })

        config = {
            "plan_id": "{{plan.id}}",
            "drift_bps_limit": 100
        }

        node = PrecheckNode(config, context)
        result = await node.execute()

        assert isinstance(result, ConditionalResult)
        assert result.condition is False
        assert any("price_drift" in f for f in result.data["failures"])

    @pytest.mark.asyncio
    async def test_precheck_fails_on_high_impact(self, context, mock_state_cache, mock_plan):
        """Test que precheck falla si el impacto es muy alto."""
        mock_state_cache.get = AsyncMock(return_value={
            "best_ask_price": 0.50,
            "staleness_ms": 500,
            "impact_bps_for_usdc_1000": 500  # Muy alto
        })

        config = {
            "plan_id": "{{plan.id}}",
            "max_impact_bps": 200
        }

        node = PrecheckNode(config, context)
        result = await node.execute()

        assert isinstance(result, ConditionalResult)
        assert result.condition is False
        assert any("market_impact_high" in f for f in result.data["failures"])

    @pytest.mark.asyncio
    async def test_precheck_fails_on_expired_ttl(self, context, mock_state_cache, mock_plan):
        """Test que precheck falla si el plan ha expirado."""
        # Plan creado hace 2 minutos, TTL de 1 minuto
        mock_plan.ttl_ms = 60000
        mock_plan.created_at = datetime.now(timezone.utc) - timedelta(minutes=2)

        config = {
            "plan_id": "{{plan.id}}",
            "skip_orderbook_check": True  # Skip orderbook para aislar test de TTL
        }

        node = PrecheckNode(config, context)
        result = await node.execute()

        assert isinstance(result, ConditionalResult)
        assert result.condition is False
        assert any("plan_ttl_expired" in f for f in result.data["failures"])

    @pytest.mark.asyncio
    async def test_precheck_passes_without_orderbook(self, context, mock_state_cache, mock_plan):
        """Test que precheck pasa si no hay orderbook (skip_orderbook_check=True)."""
        mock_state_cache.get = AsyncMock(return_value=None)

        config = {
            "plan_id": "{{plan.id}}",
            "skip_orderbook_check": True
        }

        node = PrecheckNode(config, context)
        result = await node.execute()

        assert isinstance(result, ConditionalResult)
        assert result.condition is True

    @pytest.mark.asyncio
    async def test_precheck_fails_when_plan_not_found(self, context, mock_db):
        """Test que precheck falla si el plan no existe."""
        # Simular plan no encontrado
        filter_mock = Mock()
        filter_mock.first = Mock(return_value=None)
        mock_db.query.return_value.filter = Mock(return_value=filter_mock)

        config = {
            "plan_id": str(uuid4())  # Plan que no existe
        }

        node = PrecheckNode(config, context)
        result = await node.execute()

        assert isinstance(result, ConditionalResult)
        assert result.condition is False
        assert any("not found" in f for f in result.data["failures"])

    @pytest.mark.asyncio
    async def test_precheck_fails_without_plan_id(self, context):
        """Test que precheck falla si no hay plan_id."""
        context.plan_id = None

        config = {
            "plan_id": "{{plan.id}}"  # No se resolverá
        }

        node = PrecheckNode(config, context)
        result = await node.execute()

        assert isinstance(result, ConditionalResult)
        assert result.condition is False
        assert any("plan_id is required" in f for f in result.data["failures"])

    @pytest.mark.asyncio
    async def test_precheck_multiple_failures(self, context, mock_state_cache, mock_plan):
        """Test que precheck reporta múltiples fallos."""
        # Plan expirado
        mock_plan.ttl_ms = 60000
        mock_plan.created_at = datetime.now(timezone.utc) - timedelta(minutes=2)

        # Orderbook viejo y con alto impacto
        mock_state_cache.get = AsyncMock(return_value={
            "best_ask_price": 0.70,  # Alto drift
            "staleness_ms": 5000,    # Muy viejo
            "impact_bps_for_usdc_1000": 500  # Alto impacto
        })

        config = {
            "plan_id": "{{plan.id}}",
            "max_book_staleness_ms": 2000,
            "drift_bps_limit": 100,
            "max_impact_bps": 200
        }

        node = PrecheckNode(config, context)
        result = await node.execute()

        assert isinstance(result, ConditionalResult)
        assert result.condition is False
        # Debe tener múltiples fallos
        assert len(result.data["failures"]) >= 3

    @pytest.mark.asyncio
    async def test_precheck_sell_side_uses_bid_price(self, context, mock_state_cache, mock_plan):
        """Test que para SELL side se usa best_bid_price para drift."""
        mock_plan.legs = [
            {
                "leg_id": "leg_1",
                "side": "SELL",
                "target_price": 0.50,
                "size": 100,
                "metadata": {"asset_id": "abc123"}
            }
        ]

        # Ask alto pero bid bajo (para SELL usamos bid)
        mock_state_cache.get = AsyncMock(return_value={
            "best_ask_price": 0.70,  # Este se ignora para SELL
            "best_bid_price": 0.51,  # Este se usa, drift ~2%
            "staleness_ms": 500,
            "impact_bps_for_usdc_1000": 50
        })

        config = {
            "plan_id": "{{plan.id}}",
            "drift_bps_limit": 300  # 3%, suficiente para 2% drift
        }

        node = PrecheckNode(config, context)
        result = await node.execute()

        assert isinstance(result, ConditionalResult)
        assert result.condition is True  # Debería pasar porque usamos bid_price


class TestPrecheckNodeHelpers:
    """Tests para métodos helper de PrecheckNode."""

    @pytest.fixture
    def context(self):
        """Contexto de ejecución básico."""
        context = GraphExecutionContext(
            strategy_id=uuid4(),
            event_id=uuid4(),
            market_id=uuid4(),
            trace_id=uuid4(),
            state_cache=AsyncMock(),
            db=Mock()
        )
        return context

    def test_check_plan_ttl_passes_when_no_ttl(self, context):
        """Test que _check_plan_ttl pasa si el plan no tiene TTL."""
        plan = Mock()
        plan.ttl_ms = None
        plan.created_at = datetime.now(timezone.utc)

        node = PrecheckNode({}, context)
        result = node._check_plan_ttl(plan)

        assert result["passed"] is True

    def test_check_plan_ttl_passes_when_fresh(self, context):
        """Test que _check_plan_ttl pasa si el plan es reciente."""
        plan = Mock()
        plan.ttl_ms = 60000
        plan.created_at = datetime.now(timezone.utc) - timedelta(seconds=30)

        node = PrecheckNode({}, context)
        result = node._check_plan_ttl(plan)

        assert result["passed"] is True

    def test_check_orderbook_staleness_passes_when_no_staleness(self, context):
        """Test que _check_orderbook_staleness pasa si no hay dato de staleness."""
        orderbook_state = {"best_ask_price": 0.50}

        node = PrecheckNode({}, context)
        result = node._check_orderbook_staleness(orderbook_state, 2000)

        assert result["passed"] is True

    def test_check_market_impact_passes_when_no_impact_data(self, context):
        """Test que _check_market_impact pasa si no hay dato de impacto."""
        orderbook_state = {"best_ask_price": 0.50}

        node = PrecheckNode({}, context)
        result = node._check_market_impact(Mock(), orderbook_state, 200)

        assert result["passed"] is True
