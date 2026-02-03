"""
Unit tests for Execution Engine.

Según especificación en docs/services/execution.md
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from datetime import datetime, timedelta
from app.core.execution import Execution, ExecutionConfig, EIP712Signer, NonceManager, OrderLifecycleManager
from app.core.risk_engine.models import ApprovedOrderIntent
from app.core.latency_monitor import LatencyStatus


class TestEIP712Signer:
    """Test cases for EIP-712 Signer."""
    
    def test_eip712_signer_initialization(self):
        """Test EIP-712 Signer initializes correctly."""
        config = ExecutionConfig()
        signer = EIP712Signer(config)
        assert signer is not None
    
    def test_get_eip712_domain(self):
        """Test getting EIP-712 domain."""
        config = ExecutionConfig()
        signer = EIP712Signer(config)
        domain = signer.get_eip712_domain()
        
        assert domain["name"] == config.eip712_domain_name
        assert domain["version"] == config.eip712_domain_version
        assert domain["chainId"] == config.eip712_chain_id
    
    def test_get_eip712_types(self):
        """Test getting EIP-712 types."""
        config = ExecutionConfig()
        signer = EIP712Signer(config)
        types = signer.get_eip712_types()
        
        assert "EIP712Domain" in types
        assert "Order" in types
        assert len(types["Order"]) > 0
    
    def test_build_order_message(self):
        """Test building order message."""
        config = ExecutionConfig()
        signer = EIP712Signer(config)
        
        message = signer.build_order_message(
            market_id="pm123",
            outcome="YES",
            price=0.979,
            size=5000.0,
            side="BUY",
            nonce=123,
            expiration=1737840000,
            client_order_id="test-order-123"
        )
        
        assert message["marketId"] == "pm123"
        assert message["outcome"] == "YES"
        assert message["side"] == "BUY"
        assert message["nonce"] == 123
        assert message["expiration"] == 1737840000
        assert message["clientOrderId"] == "test-order-123"


class TestNonceManager:
    """Test cases for Nonce Manager."""
    
    def test_nonce_manager_initialization(self):
        """Test Nonce Manager initializes correctly."""
        manager = NonceManager()
        assert manager is not None
    
    def test_get_next_nonce(self):
        """Test getting next nonce."""
        manager = NonceManager()
        
        nonce1 = manager.get_next_nonce()
        nonce2 = manager.get_next_nonce()
        nonce3 = manager.get_next_nonce()
        
        assert nonce1 == 1
        assert nonce2 == 2
        assert nonce3 == 3
    
    def test_sync_nonce(self):
        """Test syncing nonce from external source."""
        manager = NonceManager()
        
        # Incrementar algunos nonces
        manager.get_next_nonce()
        manager.get_next_nonce()
        
        # Sincronizar desde externo
        manager.sync_nonce(external_nonce=100)
        
        # El siguiente nonce debería ser 101
        next_nonce = manager.get_next_nonce()
        assert next_nonce == 101
    
    def test_reset(self):
        """Test resetting nonce manager."""
        manager = NonceManager()
        
        manager.get_next_nonce()
        manager.get_next_nonce()
        
        manager.reset()
        
        # Después de reset, debería empezar desde 1
        nonce = manager.get_next_nonce()
        assert nonce == 1


class TestOrderLifecycleManager:
    """Test cases for Order Lifecycle Manager."""
    
    def test_lifecycle_manager_initialization(self):
        """Test Order Lifecycle Manager initializes correctly."""
        manager = OrderLifecycleManager()
        assert manager is not None
    
    def test_is_valid_transition(self):
        """Test validating state transitions."""
        manager = OrderLifecycleManager()
        
        # Transiciones válidas
        assert manager.is_valid_transition("CREATED", "SIGNED") is True
        assert manager.is_valid_transition("SIGNED", "SUBMITTED") is True
        assert manager.is_valid_transition("SUBMITTED", "ACCEPTED") is True
        assert manager.is_valid_transition("OPEN", "FILLED") is True
        
        # Transiciones inválidas
        assert manager.is_valid_transition("FILLED", "OPEN") is False
        assert manager.is_valid_transition("CANCELLED", "OPEN") is False
        assert manager.is_valid_transition("CREATED", "FILLED") is False
    
    def test_can_retry(self):
        """Test checking if order can be retried."""
        manager = OrderLifecycleManager()
        
        assert manager.can_retry("ERROR") is True
        assert manager.can_retry("TIMEOUT") is True
        assert manager.can_retry("REJECTED") is True
        assert manager.can_retry("FILLED") is False
        assert manager.can_retry("OPEN") is False
    
    def test_is_terminal_state(self):
        """Test checking if state is terminal."""
        manager = OrderLifecycleManager()
        
        assert manager.is_terminal_state("FILLED") is True
        assert manager.is_terminal_state("CANCELLED") is True
        assert manager.is_terminal_state("EXPIRED") is True
        assert manager.is_terminal_state("REJECTED") is True
        assert manager.is_terminal_state("OPEN") is False
        assert manager.is_terminal_state("PARTIALLY_FILLED") is False


class TestExecution:
    """Test cases for Execution Engine."""
    
    def test_execution_initialization(self):
        """Test Execution Engine initializes correctly."""
        execution = Execution()
        assert execution is not None
        assert execution._eip712_signer is not None
        assert execution._nonce_manager is not None
        assert execution._lifecycle_manager is not None
    
    def test_build_order_payload(self):
        """Test building order payload."""
        execution = Execution()
        intent = ApprovedOrderIntent(
            event_id=uuid4(),
            outcome="YES",
            side="BUY",
            price=0.979,
            size=5000.0,
            original_size=5000.0,
            trace_id=uuid4()
        )
        
        nonce = 123
        client_order_id = "test-order-123"
        payload = execution._build_order_payload(intent, nonce, client_order_id)
        
        assert payload["side"] == "BUY"
        assert payload["price"] == 0.979
        assert payload["size"] == 5000.0
        assert payload["nonce"] == 123
        assert payload["clientOrderId"] == client_order_id
        assert "expiration" in payload
    
    @pytest.mark.asyncio
    async def test_tick_with_no_intents(self):
        """Test tick with no approved intents."""
        execution = Execution()
        
        # Mock wallet service para evitar acceso a DB
        with patch("app.core.execution.execution.wallet_service") as mock_wallet_service:
            mock_wallet_service.get_active_wallet = AsyncMock(return_value=None)
            
            # No debería fallar con lista vacía
            await execution.tick([])
    
    @pytest.mark.asyncio
    async def test_tick_with_circuit_breaker_open(self):
        """Test tick when circuit breaker is open."""
        execution = Execution()
        
        intent = ApprovedOrderIntent(
            event_id=uuid4(),
            outcome="YES",
            side="BUY",
            price=0.979,
            size=5000.0,
            original_size=5000.0,
            trace_id=uuid4()
        )
        
        # Mock circuit breaker abierto
        mock_runtime_supervisor = Mock()
        mock_circuit = Mock()
        mock_circuit.is_open.return_value = True
        mock_runtime_supervisor.trading_circuit = mock_circuit
        
        # Mock wallet service para evitar acceso a DB
        with patch("app.core.execution.execution.wallet_service") as mock_wallet_service, \
             patch("app.core.execution.execution.main_module", create=True) as mock_main:
            mock_wallet_service.get_active_wallet = AsyncMock(return_value=None)
            mock_main.runtime_supervisor = mock_runtime_supervisor
            
            # No debería procesar intents
            await execution.tick([intent])
    
    @pytest.mark.asyncio
    async def test_tick_with_no_wallet(self):
        """Test tick when no wallet is available."""
        execution = Execution()
        
        intent = ApprovedOrderIntent(
            event_id=uuid4(),
            outcome="YES",
            side="BUY",
            price=0.979,
            size=5000.0,
            original_size=5000.0,
            trace_id=uuid4()
        )
        
        # Mock wallet service retornando None
        with patch("app.core.execution.execution.wallet_service") as mock_wallet_service:
            mock_wallet_service.get_active_wallet = AsyncMock(return_value=None)
            
            # No debería procesar intents
            await execution.tick([intent])
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing HTTP client."""
        execution = Execution()
        
        # Crear cliente
        await execution._get_client()
        assert execution._client is not None
        
        # Cerrar
        await execution.close()
        assert execution._client is None

