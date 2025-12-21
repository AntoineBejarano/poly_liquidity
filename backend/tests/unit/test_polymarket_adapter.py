"""
Tests unitarios para PolymarketAdapter.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal
from uuid import UUID, uuid4

from app.core.execution_engine.platforms.polymarket_adapter import PolymarketAdapter
from app.core.execution_engine.platform_models import (
    OrderResult,
    OrderStatus,
    PlatformFeatureNotSupported
)
from app.core.strategy_engine.models import PlanLeg


class TestPolymarketAdapter:
    """Tests para PolymarketAdapter."""
    
    @pytest.fixture
    def mock_client_wrapper(self):
        """Mock de PolymarketCLOBWrapper."""
        mock = Mock()
        mock.is_available.return_value = True
        mock.create_limit_order = AsyncMock(return_value={"id": "polymarket_order_123"})
        mock.create_market_order = AsyncMock(return_value={"id": "polymarket_order_456"})
        mock.cancel_order = AsyncMock(return_value={"canceled": ["order_123"], "not_canceled": {}})
        return mock
    
    @pytest.fixture
    def adapter(self, mock_client_wrapper):
        """Fixture para PolymarketAdapter con mock."""
        with patch('app.core.execution_engine.platforms.polymarket_adapter.get_polymarket_client', return_value=mock_client_wrapper):
            adapter = PolymarketAdapter()
            adapter._client_wrapper = mock_client_wrapper
            return adapter
    
    @pytest.fixture
    def sample_leg(self):
        """Fixture para un PlanLeg de ejemplo."""
        return PlanLeg(
            leg_id="leg_1",
            side="BUY",
            outcome="YES",
            target_price=Decimal("0.5"),
            size=Decimal("10.0"),
            size_usdc=Decimal("5.0"),
            reason="Test leg",
            metadata={"token_id": "token_123", "event_id": str(uuid4())}
        )
    
    def test_adapter_initialization(self, mock_client_wrapper):
        """Test inicialización del adaptador."""
        with patch('app.core.execution_engine.platforms.polymarket_adapter.get_polymarket_client', return_value=mock_client_wrapper):
            adapter = PolymarketAdapter()
            
            assert adapter.platform_name == "polymarket"
            assert adapter.config == {}
            assert adapter._client_wrapper == mock_client_wrapper
    
    def test_is_available_true(self, adapter, mock_client_wrapper):
        """Test is_available cuando el cliente está disponible."""
        mock_client_wrapper.is_available.return_value = True
        assert adapter.is_available() is True
    
    def test_is_available_false(self, adapter, mock_client_wrapper):
        """Test is_available cuando el cliente no está disponible."""
        mock_client_wrapper.is_available.return_value = False
        assert adapter.is_available() is False
    
    def test_is_available_no_client(self):
        """Test is_available cuando no hay cliente."""
        with patch('app.core.execution_engine.platforms.polymarket_adapter.get_polymarket_client', return_value=None):
            adapter = PolymarketAdapter()
            adapter._client_wrapper = None
            assert adapter.is_available() is False
    
    @pytest.mark.asyncio
    async def test_submit_order_limit_success(self, adapter, sample_leg, mock_client_wrapper):
        """Test submit_order para limit order exitosa."""
        risk_config = {"order_type": "GTC"}
        trace_id = uuid4()
        
        with patch('app.core.execution_engine.platforms.polymarket_adapter.rate_limiter.wait_for_capacity', return_value=True), \
             patch('app.core.execution_engine.platforms.polymarket_adapter.latency_monitor.record_execution_latency'):
            
            result = await adapter.submit_order(sample_leg, risk_config, trace_id)
            
            assert isinstance(result, OrderResult)
            assert result.platform_order_id == "polymarket_order_123"
            assert result.status == OrderStatus.SUBMITTED
            assert result.trace_id == trace_id
            mock_client_wrapper.create_limit_order.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_order_market_success(self, adapter, sample_leg, mock_client_wrapper):
        """Test submit_order para market order exitosa."""
        risk_config = {"order_type": "MARKET", "market_order_type": "FOK"}
        trace_id = uuid4()
        
        with patch('app.core.execution_engine.platforms.polymarket_adapter.rate_limiter.wait_for_capacity', return_value=True), \
             patch('app.core.execution_engine.platforms.polymarket_adapter.latency_monitor.record_execution_latency'):
            
            result = await adapter.submit_order(sample_leg, risk_config, trace_id)
            
            assert isinstance(result, OrderResult)
            assert result.platform_order_id == "polymarket_order_456"
            assert result.status == OrderStatus.SUBMITTED
            assert result.trace_id == trace_id
            mock_client_wrapper.create_market_order.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_order_market_fok_only(self, adapter, sample_leg, mock_client_wrapper):
        """Test que market orders solo soportan FOK e IOC."""
        risk_config = {"order_type": "MARKET", "market_order_type": "GTC"}
        trace_id = uuid4()
        
        with patch('app.core.execution_engine.platforms.polymarket_adapter.rate_limiter.wait_for_capacity', return_value=True), \
             patch('app.core.execution_engine.platforms.polymarket_adapter.latency_monitor.record_execution_latency'):
            
            # GTC no está soportado para market orders, debería lanzar PlatformFeatureNotSupported
            with pytest.raises(PlatformFeatureNotSupported) as exc_info:
                await adapter.submit_order(sample_leg, risk_config, trace_id)
            
            assert "Market order with type GTC" in str(exc_info.value)
            assert "Polymarket only supports FOK and IOC" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_order_no_token_id_in_metadata(self, adapter, sample_leg):
        """Test submit_order cuando no hay token_id en metadata."""
        sample_leg.metadata = {"event_id": str(uuid4())}  # Sin token_id
        risk_config = {"order_type": "GTC"}
        
        # Mock de _get_token_id_from_event
        with patch.object(adapter, '_get_token_id_from_event', return_value="token_from_event") as mock_get_token:
            with patch('app.core.execution_engine.platforms.polymarket_adapter.rate_limiter.wait_for_capacity', return_value=True), \
                 patch('app.core.execution_engine.platforms.polymarket_adapter.latency_monitor.record_execution_latency'):
                
                result = await adapter.submit_order(sample_leg, risk_config)
                assert result.platform_order_id == "polymarket_order_123"
                mock_get_token.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_order_no_token_id_raises(self, adapter, sample_leg):
        """Test que submit_order lanza error si no hay token_id."""
        sample_leg.metadata = {}  # Sin token_id ni event_id
        risk_config = {"order_type": "GTC"}
        
        with pytest.raises(RuntimeError) as exc_info:
            await adapter.submit_order(sample_leg, risk_config)
        
        assert "Could not get token_id" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_order_not_available(self, adapter):
        """Test submit_order cuando la plataforma no está disponible."""
        adapter._client_wrapper = None
        sample_leg = PlanLeg(
            leg_id="leg_1",
            side="BUY",
            outcome="YES",
            target_price=Decimal("0.5"),
            size=Decimal("10.0"),
            size_usdc=Decimal("5.0"),
            reason="Test"
        )
        
        with pytest.raises(RuntimeError) as exc_info:
            await adapter.submit_order(sample_leg, {})
        
        assert "Polymarket client not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_order_rate_limit_timeout(self, adapter, sample_leg):
        """Test submit_order cuando hay timeout de rate limit."""
        risk_config = {"order_type": "GTC"}
        
        with patch('app.core.execution_engine.platforms.polymarket_adapter.rate_limiter.wait_for_capacity', return_value=False):
            with pytest.raises(RuntimeError) as exc_info:
                await adapter.submit_order(sample_leg, risk_config)
            
            assert "Rate limit exceeded" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_cancel_order_success(self, adapter, mock_client_wrapper):
        """Test cancel_order exitoso."""
        order_id = "order_123"
        trace_id = uuid4()
        
        with patch('app.core.execution_engine.platforms.polymarket_adapter.rate_limiter.wait_for_capacity', return_value=True):
            result = await adapter.cancel_order(order_id, trace_id)
            
            assert result is True
            mock_client_wrapper.cancel_order.assert_called_once_with(order_id)
    
    @pytest.mark.asyncio
    async def test_cancel_order_not_canceled(self, adapter, mock_client_wrapper):
        """Test cancel_order cuando la orden no se puede cancelar."""
        order_id = "order_123"
        mock_client_wrapper.cancel_order.return_value = {
            "canceled": [],
            "not_canceled": {order_id: "Order already filled"}
        }
        
        with patch('app.core.execution_engine.platforms.polymarket_adapter.rate_limiter.wait_for_capacity', return_value=True):
            result = await adapter.cancel_order(order_id)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_cancel_order_not_available(self, adapter):
        """Test cancel_order cuando la plataforma no está disponible."""
        adapter._client_wrapper = None
        
        with pytest.raises(RuntimeError) as exc_info:
            await adapter.cancel_order("order_123")
        
        assert "Polymarket client not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_order_status_not_implemented(self, adapter):
        """Test que get_order_status aún no está implementado."""
        with pytest.raises(RuntimeError) as exc_info:
            await adapter.get_order_status("order_123")
        
        assert "get_order_status not yet implemented" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_balances_not_implemented(self, adapter):
        """Test que get_balances aún no está implementado."""
        with pytest.raises(RuntimeError) as exc_info:
            await adapter.get_balances()
        
        assert "get_balances not yet implemented" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_token_id_from_event(self, adapter):
        """Test _get_token_id_from_event."""
        from app.models.event import Event
        
        event_id = uuid4()
        outcome = "YES"
        
        # Mock de la base de datos
        with patch('app.core.execution_engine.platforms.polymarket_adapter.SessionLocal') as mock_session_local:
            # Crear un mock de sesión
            mock_db = Mock()
            mock_db.close = Mock()  # Método close
            
            # Mock de Event con token_id
            mock_event = Mock(spec=Event)
            mock_event.polymarket_payload = {
                "clobTokenIds": {"YES": "token_yes_123", "NO": "token_no_456"}
            }
            mock_event.market_id = None
            
            # Configurar el mock de query correctamente
            # db.query(Event).filter(Event.id == event_id).first()
            mock_query = Mock()
            mock_filter = Mock()
            mock_filter.first.return_value = mock_event
            mock_query.filter.return_value = mock_filter
            mock_db.query.return_value = mock_query
            
            # SessionLocal() retorna la sesión directamente (no es context manager)
            mock_session_local.return_value = mock_db
            
            token_id = await adapter._get_token_id_from_event(event_id, outcome)
            
            assert token_id == "token_yes_123"
            mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_token_id_from_leg_metadata(self, adapter, sample_leg):
        """Test _get_token_id_from_leg cuando está en metadata."""
        token_id = await adapter._get_token_id_from_leg(sample_leg)
        assert token_id == "token_123"
    
    @pytest.mark.asyncio
    async def test_convert_order_type(self, adapter):
        """Test _convert_order_type."""
        assert adapter._convert_order_type({"order_type": "GTC"}) == "GTC"
        assert adapter._convert_order_type({"order_type": "FOK"}) == "FOK"
        assert adapter._convert_order_type({"order_type": "IOC"}) == "IOC"
        assert adapter._convert_order_type({"order_type": "INVALID"}) == "GTC"  # Default
        assert adapter._convert_order_type({}) == "GTC"  # Default
