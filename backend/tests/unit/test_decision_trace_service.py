"""
Tests unitarios para DecisionTraceService.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime
from app.core.decision_trace.decision_trace_service import DecisionTraceService, decision_trace_service
from app.core.config_service import config_service


@pytest.fixture
def decision_service():
    """Fixture para DecisionTraceService."""
    return DecisionTraceService()


def test_make_input_data_concise_replaces_orderbook_with_hash(decision_service):
    """Test que _make_input_data_concise() reemplaza orderbooks completos con hash."""
    input_data = {
        "market_id": "test",
        "orderbook": {
            "best_ask": 0.98,
            "best_bid": 0.97,
            "spread": 0.01,
            "total_liquidity": 100000.0,
            "bids": [{"price": 0.97, "size": 1000}] * 100,  # 100 bids
            "asks": [{"price": 0.98, "size": 1000}] * 100,  # 100 asks
        }
    }
    
    concise = decision_service._make_input_data_concise(input_data)
    
    # Debería tener orderbook_hash y orderbook_summary, no orderbook completo
    assert "orderbook" not in concise
    assert "orderbook_hash" in concise
    assert "orderbook_summary" in concise
    assert concise["orderbook_summary"]["best_ask"] == 0.98


def test_make_input_data_concise_replaces_large_history_with_hash(decision_service):
    """Test que _make_input_data_concise() reemplaza historiales extensos con hash."""
    input_data = {
        "price_history": [{"price": 0.97, "timestamp": "2024-01-01"}] * 50  # 50 elementos
    }
    
    concise = decision_service._make_input_data_concise(input_data)
    
    # Debería tener price_history_hash y price_history_count, no el array completo
    assert "price_history_hash" in concise
    assert concise["price_history_count"] == 50
    assert "price_history_first" in concise
    assert "price_history_last" in concise


def test_make_input_data_concise_keeps_small_data(decision_service):
    """Test que _make_input_data_concise() mantiene datos pequeños sin cambios."""
    input_data = {
        "market_id": "test",
        "best_ask": 0.98,
        "best_bid": 0.97,
        "spread": 0.01,
    }
    
    concise = decision_service._make_input_data_concise(input_data)
    
    # Debería mantener todos los campos pequeños
    assert concise["market_id"] == "test"
    assert concise["best_ask"] == 0.98
    assert concise["best_bid"] == 0.97
    assert concise["spread"] == 0.01


def test_get_config_snapshot_returns_dict(decision_service):
    """Test que _get_config_snapshot() retorna un dict."""
    with patch('app.core.decision_trace.decision_trace_service.config_service') as mock_config:
        mock_config.get_scanner_config.return_value = {"test": "value"}
        
        snapshot = decision_service._get_config_snapshot("scanner")
        
        assert isinstance(snapshot, dict)
        mock_config.get_scanner_config.assert_called()


def test_log_decision_creates_record(decision_service):
    """Test que log_decision() crea un registro en la DB."""
    trace_id = uuid4()
    market_id = uuid4()
    
    with patch('app.core.decision_trace.decision_trace_service.SessionLocal') as mock_session_local, \
         patch('app.core.decision_trace.decision_trace_service.config_service') as mock_config:
        
        # Mock DB session
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Mock DecisionTrace
        mock_trace = MagicMock()
        mock_trace.id = uuid4()
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        # Mock config service
        mock_config.get_scanner_config.return_value = {}
        
        # Mock DecisionTrace constructor
        with patch('app.core.decision_trace.decision_trace_service.DecisionTrace') as mock_decision_trace_class:
            mock_decision_trace_class.return_value = mock_trace
            
            result = decision_service.log_decision(
                trace_id=trace_id,
                component="scanner",
                decision_stage="SCAN",
                decision_type="entry",
                decision="APPROVED",
                input_data={"market_id": str(market_id)},
                market_id=market_id
            )
            
            # Verificar que se creó el registro
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            assert result == mock_trace.id


def test_hash_large_data_generates_sha256(decision_service):
    """Test que _hash_large_data() genera hash SHA256."""
    data = {"test": "data"}
    hash_result = decision_service._hash_large_data(data)
    
    # Debería ser un hash SHA256 (64 caracteres hex)
    assert len(hash_result) == 64
    assert isinstance(hash_result, str)
    # Debería ser determinístico
    assert decision_service._hash_large_data(data) == hash_result


def test_set_session_id_stores_session(decision_service):
    """Test que set_session_id() almacena el session_id."""
    session_id = uuid4()
    decision_service.set_session_id(session_id)
    
    assert decision_service._current_session_id == session_id

