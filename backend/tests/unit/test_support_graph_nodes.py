"""
Tests unitarios para nodos de Support Graphs.
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.core.strategy_engine.models import GraphExecutionContext
from app.core.strategy_engine.nodes.fetch_external_source import FetchExternalSourceNode
from app.core.strategy_engine.nodes.update_state_cache import UpdateStateCacheNode
from app.core.strategy_engine.nodes.log import LogNode
from app.core.strategy_engine.nodes.base import SuccessResult, FailureResult
from app.core.connectors.registry import connector_registry
from app.core.connectors.custom_api import CustomAPIConnector


@pytest.fixture
def mock_state_cache():
    """Mock StateCacheService."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


@pytest.fixture
def graph_context(mock_state_cache):
    """Fixture para GraphExecutionContext."""
    context = GraphExecutionContext(
        strategy_id=uuid4(),
        event_id=uuid4(),
        market_id=uuid4(),
        trace_id=uuid4(),
        state_cache=mock_state_cache
    )
    return context


@pytest.fixture
def mock_db():
    """Mock DB session."""
    db = MagicMock()
    db.query = MagicMock()
    db.close = MagicMock()
    return db


class TestFetchExternalSourceNode:
    """Tests para FetchExternalSourceNode."""
    
    @pytest.mark.asyncio
    async def test_fetch_success(self, graph_context, mock_state_cache):
        """Test obtener datos exitosamente."""
        source_id = uuid4()
        test_data = {"result": "success", "data": [1, 2, 3]}
        
        # Mock connector
        mock_connector = AsyncMock()
        mock_connector.fetch = AsyncMock(return_value=test_data)
        
        # Mock registry
        with patch('app.core.strategy_engine.nodes.fetch_external_source.connector_registry') as mock_registry:
            mock_registry.get_connector_from_db = MagicMock(return_value=mock_connector)
            
            # Mock DB
            with patch('app.core.strategy_engine.nodes.fetch_external_source.SessionLocal') as mock_session:
                mock_session.return_value = MagicMock()
                
                node = FetchExternalSourceNode(
                    {
                        "source_id": str(source_id),
                        "endpoint": "/api/events",
                        "method": "GET"
                    },
                    graph_context
                )
                
                result = await node.execute()
                
                assert isinstance(result, SuccessResult)
                assert hasattr(graph_context, 'fetched_data')
                assert f"source_{source_id}_/api/events" in graph_context.fetched_data
                assert graph_context.fetched_data[f"source_{source_id}_/api/events"] == test_data
    
    @pytest.mark.asyncio
    async def test_fetch_with_cache_key(self, graph_context, mock_state_cache):
        """Test obtener datos y guardar en cache."""
        source_id = uuid4()
        test_data = {"result": "success"}
        
        mock_connector = AsyncMock()
        mock_connector.fetch = AsyncMock(return_value=test_data)
        
        with patch('app.core.strategy_engine.nodes.fetch_external_source.connector_registry') as mock_registry:
            mock_registry.get_connector_from_db = MagicMock(return_value=mock_connector)
            
            with patch('app.core.strategy_engine.nodes.fetch_external_source.SessionLocal') as mock_session:
                mock_session.return_value = MagicMock()
                
                node = FetchExternalSourceNode(
                    {
                        "source_id": str(source_id),
                        "endpoint": "/api/events",
                        "cache_key": "event.123.external_data.source1",
                        "ttl_seconds": 300
                    },
                    graph_context
                )
                
                result = await node.execute()
                
                assert isinstance(result, SuccessResult)
                mock_state_cache.set.assert_called_once()
                call_args = mock_state_cache.set.call_args
                assert call_args[1]["cache_key"] == "event.123.external_data.source1"
                assert call_args[1]["value"] == test_data
                assert call_args[1]["ttl_seconds"] == 300
    
    @pytest.mark.asyncio
    async def test_fetch_missing_source_id(self, graph_context):
        """Test sin source_id."""
        node = FetchExternalSourceNode(
            {"endpoint": "/api/events"},
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "source_id" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_fetch_connector_error(self, graph_context):
        """Test error del conector."""
        source_id = uuid4()
        
        with patch('app.core.strategy_engine.nodes.fetch_external_source.connector_registry') as mock_registry:
            mock_registry.get_connector_from_db = MagicMock(
                side_effect=Exception("Connector not found")
            )
            
            with patch('app.core.strategy_engine.nodes.fetch_external_source.SessionLocal') as mock_session:
                mock_session.return_value = MagicMock()
                
                node = FetchExternalSourceNode(
                    {
                        "source_id": str(source_id),
                        "endpoint": "/api/events"
                    },
                    graph_context
                )
                
                result = await node.execute()
                
                assert isinstance(result, FailureResult)
                assert "error" in result.error.lower()


class TestUpdateStateCacheNode:
    """Tests para UpdateStateCacheNode."""
    
    @pytest.mark.asyncio
    async def test_update_success(self, graph_context, mock_state_cache):
        """Test actualizar State Cache exitosamente."""
        node = UpdateStateCacheNode(
            {
                "key": "event.123.market_state",
                "value": {"last_price": 0.98, "spread": 0.01},
                "ttl_seconds": 60
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
        mock_state_cache.set.assert_called_once()
        call_args = mock_state_cache.set.call_args
        assert call_args[1]["cache_key"] == "event.123.market_state"
        assert call_args[1]["value"] == {"last_price": 0.98, "spread": 0.01}
        assert call_args[1]["ttl_seconds"] == 60
    
    @pytest.mark.asyncio
    async def test_update_from_context(self, graph_context, mock_state_cache):
        """Test actualizar desde contexto."""
        # Configurar contexto con datos
        graph_context.fetched_data = {
            "source_123_/api/events": {"result": "success"}
        }
        
        node = UpdateStateCacheNode(
            {
                "key": "event.123.external_data",
                "value_from_context": "fetched_data.source_123_/api/events"
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
        mock_state_cache.set.assert_called_once()
        call_args = mock_state_cache.set.call_args
        assert call_args[1]["value"] == {"result": "success"}
    
    @pytest.mark.asyncio
    async def test_update_missing_key(self, graph_context):
        """Test sin cache key."""
        node = UpdateStateCacheNode(
            {"value": {"data": "test"}},
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "key" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_update_missing_value(self, graph_context):
        """Test sin value."""
        node = UpdateStateCacheNode(
            {"key": "test.key"},
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "value" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_update_value_from_context_not_found(self, graph_context):
        """Test value_from_context no encontrado."""
        node = UpdateStateCacheNode(
            {
                "key": "test.key",
                "value_from_context": "fetched_data.nonexistent"
            },
            graph_context
        )
        
        result = await node.execute()
        
        assert isinstance(result, FailureResult)
        assert "not found" in result.error.lower()


class TestLogNode:
    """Tests para LogNode."""
    
    @pytest.mark.asyncio
    async def test_log_info(self, graph_context):
        """Test log INFO."""
        with patch('app.core.strategy_engine.nodes.log.logger') as mock_logger:
            node = LogNode(
                {
                    "level": "INFO",
                    "message": "Test message",
                    "data": {"key": "value"}
                },
                graph_context
            )
            
            result = await node.execute()
            
            assert isinstance(result, SuccessResult)
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "Test message"
            assert "strategy_id" in call_args[1]["extra"]
    
    @pytest.mark.asyncio
    async def test_log_error(self, graph_context):
        """Test log ERROR."""
        with patch('app.core.strategy_engine.nodes.log.logger') as mock_logger:
            node = LogNode(
                {
                    "level": "ERROR",
                    "message": "Error occurred"
                },
                graph_context
            )
            
            result = await node.execute()
            
            assert isinstance(result, SuccessResult)
            mock_logger.error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_log_without_context(self, graph_context):
        """Test log sin incluir contexto."""
        with patch('app.core.strategy_engine.nodes.log.logger') as mock_logger:
            node = LogNode(
                {
                    "level": "INFO",
                    "message": "Test",
                    "include_context": False
                },
                graph_context
            )
            
            result = await node.execute()
            
            assert isinstance(result, SuccessResult)
            call_args = mock_logger.info.call_args
            assert "strategy_id" not in call_args[1]["extra"]

