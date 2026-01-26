"""
Tests unitarios para versioning con 100% de cobertura.
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock

from app.core.strategy_engine.versioning import (
    get_node_version,
    validate_pinned_versions,
    record_node_versions
)
from app.models.strategy import Strategy
from app.models.graph_node_definition import GraphNodeDefinition


class TestVersioning:
    """Tests para versioning."""
    
    @pytest.fixture
    def mock_strategy(self):
        """Mock de Strategy."""
        strategy = Mock(spec=Strategy)
        strategy.pinned_node_versions = None
        return strategy
    
    @pytest.fixture
    def mock_db(self):
        """Mock de database session."""
        db = Mock()
        db.query = Mock()
        return db
    
    def test_get_node_version_pinned(self, mock_strategy, mock_db):
        """Test que retorna versión pinned si está definida."""
        mock_strategy.pinned_node_versions = {"build_plan": "1.0.0"}
        
        version = get_node_version("build_plan", mock_strategy, mock_db)
        
        assert version == "1.0.0"
    
    def test_get_node_version_not_pinned(self, mock_strategy, mock_db):
        """Test que retorna versión del catálogo si no está pinned."""
        mock_strategy.pinned_node_versions = {}
        
        mock_node_def = Mock(spec=GraphNodeDefinition)
        mock_node_def.version = "1.2.0"
        mock_node_def.created_at = Mock()
        
        query_mock = Mock()
        query_mock.filter.return_value.order_by.return_value.first.return_value = mock_node_def
        mock_db.query.return_value = query_mock
        
        version = get_node_version("build_plan", mock_strategy, mock_db)
        
        assert version == "1.2.0"
    
    def test_get_node_version_no_strategy(self, mock_db):
        """Test que retorna versión del catálogo si no hay strategy."""
        mock_node_def = Mock(spec=GraphNodeDefinition)
        mock_node_def.version = "1.2.0"
        mock_node_def.created_at = Mock()
        
        query_mock = Mock()
        query_mock.filter.return_value.order_by.return_value.first.return_value = mock_node_def
        mock_db.query.return_value = query_mock
        
        version = get_node_version("build_plan", None, mock_db)
        
        assert version == "1.2.0"
    
    def test_get_node_version_no_db(self, mock_strategy):
        """Test que retorna 'latest' si no hay DB."""
        version = get_node_version("build_plan", mock_strategy, None)
        
        assert version == "latest"
    
    def test_get_node_version_none_version(self, mock_strategy, mock_db):
        """Test que retorna 'latest' si el nodo tiene version None."""
        mock_node_def = Mock(spec=GraphNodeDefinition)
        mock_node_def.version = None
        mock_node_def.created_at = Mock()
        
        query_mock = Mock()
        query_mock.filter.return_value.order_by.return_value.first.return_value = mock_node_def
        mock_db.query.return_value = query_mock
        
        version = get_node_version("build_plan", mock_strategy, mock_db)
        
        assert version == "latest"
    
    def test_validate_pinned_versions_valid(self, mock_db):
        """Test validación de versiones pinned válidas."""
        strategy = Mock(spec=Strategy)
        strategy.pinned_node_versions = {"build_plan": "1.0.0"}
        
        mock_node_def = Mock(spec=GraphNodeDefinition)
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_node_def
        mock_db.query.return_value = query_mock
        
        is_valid, error = validate_pinned_versions(strategy, mock_db)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_pinned_versions_invalid(self, mock_db):
        """Test validación falla con versión pinned que no existe."""
        strategy = Mock(spec=Strategy)
        strategy.pinned_node_versions = {"build_plan": "999.0.0"}
        
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = None
        mock_db.query.return_value = query_mock
        
        is_valid, error = validate_pinned_versions(strategy, mock_db)
        
        assert is_valid is False
        assert "not found" in error
    
    def test_validate_pinned_versions_no_pinned(self, mock_db):
        """Test validación pasa si no hay versiones pinned."""
        strategy = Mock(spec=Strategy)
        strategy.pinned_node_versions = None
        
        is_valid, error = validate_pinned_versions(strategy, mock_db)
        
        assert is_valid is True
        assert error is None
    
    def test_record_node_versions(self, mock_strategy, mock_db):
        """Test registro de versiones de nodos."""
        graph = {
            "node_1": {"type": "build_plan"},
            "node_2": {"type": "emit_plan_intent"}
        }
        
        mock_node_def = Mock(spec=GraphNodeDefinition)
        mock_node_def.version = "1.0.0"
        mock_node_def.created_at = Mock()
        
        query_mock = Mock()
        query_mock.filter.return_value.order_by.return_value.first.return_value = mock_node_def
        mock_db.query.return_value = query_mock
        
        versions = record_node_versions(graph, mock_strategy, mock_db)
        
        assert "build_plan" in versions
        assert "emit_plan_intent" in versions
    
    def test_record_node_versions_no_strategy(self, mock_db):
        """Test registro sin strategy."""
        graph = {"node_1": {"type": "build_plan"}}
        
        mock_node_def = Mock(spec=GraphNodeDefinition)
        mock_node_def.version = "1.0.0"
        mock_node_def.created_at = Mock()
        
        query_mock = Mock()
        query_mock.filter.return_value.order_by.return_value.first.return_value = mock_node_def
        mock_db.query.return_value = query_mock
        
        versions = record_node_versions(graph, None, mock_db)
        
        assert "build_plan" in versions
    
    def test_record_node_versions_no_db(self, mock_strategy):
        """Test registro sin DB."""
        graph = {"node_1": {"type": "build_plan"}}
        
        versions = record_node_versions(graph, mock_strategy, None)
        
        assert "build_plan" in versions
        assert versions["build_plan"] == "latest"
    
    def test_record_node_versions_empty_graph(self, mock_strategy, mock_db):
        """Test registro con grafo vacío."""
        graph = {}
        
        versions = record_node_versions(graph, mock_strategy, mock_db)
        
        assert versions == {}

