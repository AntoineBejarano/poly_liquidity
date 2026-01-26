"""
Tests unitarios para verificar que Execution Engine usa ConfigService y modos de ejecución.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from app.core.execution.execution import Execution
from app.core.execution.models import ExecutionConfig, SignedOrder, ExecutionRecord
from app.core.risk_engine.models import ApprovedOrderIntent
from app.core.config_service import config_service


@pytest.fixture
def execution():
    """Fixture para Execution Engine."""
    return Execution()


@pytest.fixture
def mock_config_service():
    """Mock ConfigService."""
    with patch('app.core.execution.execution.config_service') as mock:
        # Mock get_execution_config
        mock_exec_config = {
            "execution_mode": "DRY_RUN",
            "max_retries": 3,
            "retry_delay_seconds": 1.0,
            "order_timeout_seconds": 3600.0,
            "fill_check_interval_seconds": 5.0,
            "http_timeout_seconds": 30.0,
            "order_ttl_seconds": 3600,
        }
        
        mock.get_execution_config.return_value = mock_exec_config
        mock.get_execution_mode.return_value = "DRY_RUN"
        
        # Mock get para parámetros adicionales
        def get_side_effect(key, default=None):
            params = {
                "execution_max_retries": 3,
                "execution_retry_delay_seconds": 1.0,
                "execution_http_timeout_seconds": 30.0,
            }
            return params.get(key, default)
        
        mock.get.side_effect = get_side_effect
        
        yield mock


def test_execution_init_uses_config_service(mock_config_service):
    """Test que __init__() usa get_execution_config() para cargar configuración."""
    exec_engine = Execution()
    
    # Verificar que se llamó a get_execution_config
    mock_config_service.get_execution_config.assert_called()
    
    # Verificar que el modo de ejecución se cargó
    assert exec_engine._execution_mode == "DRY_RUN"


def test_execution_get_client_uses_config_service(execution, mock_config_service):
    """Test que _get_client() usa http_timeout_seconds desde ConfigService."""
    import asyncio
    
    # Mock httpx.AsyncClient
    with patch('app.core.execution.execution.httpx.AsyncClient') as mock_client:
        asyncio.run(execution._get_client())
        
        # Verificar que se obtuvo el timeout
        mock_config_service.get_execution_config.assert_called()
        
        # Verificar que se creó el client con el timeout correcto
        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args[1]
        assert call_kwargs["timeout"] == 30.0


def test_execution_send_order_dry_run_mode(execution, mock_config_service):
    """Test que _send_order_to_polymarket() respeta DRY_RUN mode."""
    mock_config_service.get_execution_mode.return_value = "DRY_RUN"
    
    signed_order = SignedOrder(
        signed_order_id=uuid4(),
        intent_id=uuid4(),
        trace_id=uuid4(),
        wallet_address="0x123",
        chain_id=137,
        domain_separator="",
        domain_json={},
        message_struct={},
        message_hash="",
        signature="",
        created_at=None,
        expires_at=None,
        status="READY_TO_SEND"
    )
    
    execution_record = ExecutionRecord(
        execution_id=uuid4(),
        signed_order_id=signed_order.signed_order_id,
        trace_id=signed_order.trace_id,
        request_payload={},
        request_payload_hash="",
        http_method="POST",
        endpoint_url="",
        status="PENDING",
        created_at=None
    )
    
    import asyncio
    result = asyncio.run(execution._send_order_to_polymarket(
        signed_order,
        {},
        execution_record
    ))
    
    # Verificar que se obtuvo el modo de ejecución
    mock_config_service.get_execution_mode.assert_called()
    
    # En DRY_RUN, debería retornar un order_id simulado
    assert result is not None
    assert result.startswith("dry_run_")
    assert execution_record.status == "SIMULATED"
    assert signed_order.status == "SIMULATED"


def test_execution_send_order_paper_mode(execution, mock_config_service):
    """Test que _send_order_to_polymarket() respeta PAPER mode."""
    mock_config_service.get_execution_mode.return_value = "PAPER"
    
    signed_order = SignedOrder(
        signed_order_id=uuid4(),
        intent_id=uuid4(),
        trace_id=uuid4(),
        wallet_address="0x123",
        chain_id=137,
        domain_separator="",
        domain_json={},
        message_struct={},
        message_hash="",
        signature="",
        created_at=None,
        expires_at=None,
        status="READY_TO_SEND"
    )
    
    execution_record = ExecutionRecord(
        execution_id=uuid4(),
        signed_order_id=signed_order.signed_order_id,
        trace_id=signed_order.trace_id,
        request_payload={},
        request_payload_hash="",
        http_method="POST",
        endpoint_url="",
        status="PENDING",
        created_at=None
    )
    
    # Mock rate_limiter
    with patch('app.core.execution.execution.rate_limiter') as mock_rate_limiter:
        mock_rate_limiter.wait_for_capacity = AsyncMock(return_value=True)
        
        import asyncio
        result = asyncio.run(execution._send_order_to_polymarket(
            signed_order,
            {},
            execution_record
        ))
        
        # Verificar que se obtuvo el modo de ejecución
        mock_config_service.get_execution_mode.assert_called()
        
        # En PAPER, debería retornar un order_id con prefijo "paper_"
        assert result is not None
        assert result.startswith("paper_")
        assert execution_record.status == "ACCEPTED"
        assert signed_order.status == "SENT"


def test_execution_send_order_uses_max_retries_from_config(execution, mock_config_service):
    """Test que _send_order_to_polymarket() usa max_retries desde ConfigService."""
    mock_config_service.get_execution_mode.return_value = "LIVE"
    mock_config_service.get_execution_config.return_value = {
        "execution_mode": "LIVE",
        "max_retries": 5,  # Cambiar a 5
        "retry_delay_seconds": 1.0,
        "order_timeout_seconds": 3600.0,
        "fill_check_interval_seconds": 5.0,
        "http_timeout_seconds": 30.0,
        "order_ttl_seconds": 3600,
    }
    
    signed_order = SignedOrder(
        signed_order_id=uuid4(),
        intent_id=uuid4(),
        trace_id=uuid4(),
        wallet_address="0x123",
        chain_id=137,
        domain_separator="",
        domain_json={},
        message_struct={},
        message_hash="",
        signature="",
        created_at=None,
        expires_at=None,
        status="READY_TO_SEND"
    )
    
    execution_record = ExecutionRecord(
        execution_id=uuid4(),
        signed_order_id=signed_order.signed_order_id,
        trace_id=signed_order.trace_id,
        request_payload={},
        request_payload_hash="",
        http_method="POST",
        endpoint_url="",
        status="PENDING",
        created_at=None
    )
    
    # Mock rate_limiter para que falle todas las veces
    with patch('app.core.execution.execution.rate_limiter') as mock_rate_limiter:
        mock_rate_limiter.wait_for_capacity = AsyncMock(return_value=False)
        
        import asyncio
        result = asyncio.run(execution._send_order_to_polymarket(
            signed_order,
            {},
            execution_record
        ))
        
        # Verificar que se obtuvo max_retries desde ConfigService
        mock_config_service.get_execution_config.assert_called()
        
        # Debería haber intentado 5 veces (max_retries desde config)
        # Como wait_for_capacity retorna False, debería fallar después de 5 intentos
        assert result is None

