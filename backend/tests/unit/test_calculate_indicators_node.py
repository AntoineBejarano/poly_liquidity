"""
Tests unitarios para CalculateIndicatorsNode.
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, patch

from app.core.strategy_engine.nodes.calculate_indicators import CalculateIndicatorsNode
from app.core.strategy_engine.nodes.base import SuccessResult
from app.core.strategy_engine.models import GraphExecutionContext
from app.core.strategy_engine.indicators.liquidity_provider import LiquidityProvider


class TestCalculateIndicatorsNode:
    """Tests para CalculateIndicatorsNode."""
    
    @pytest.fixture
    def context(self):
        """Contexto de ejecución."""
        context = GraphExecutionContext(
            strategy_id=uuid4(),
            event_id=uuid4(),
            market_id=uuid4(),
            trace_id=uuid4(),
            state_cache=Mock()
        )
        context.collected_state = {
            "market_state": {
                "last_price": 0.95,
                "orderbook_snapshot": {
                    "bids": [{"price": 0.94, "size": 1000}],
                    "asks": [{"price": 0.96, "size": 1000}]
                }
            },
            "event_state": {
                "close_time": "2024-12-31T23:59:59Z"
            },
            "risk_state": {
                "current_position": 0,
                "target_position": 0,
                "max_position": 10000
            }
        }
        return context
    
    @pytest.mark.asyncio
    async def test_execute_with_strategy_type_in_config(self, context):
        """Test que calcula indicadores cuando strategy_type está en config."""
        config = {
            "strategy_type": "liquidity"
        }
        
        node = CalculateIndicatorsNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
        assert hasattr(context, "signals")
        assert isinstance(context.signals, dict)
        # Debe tener 14 indicadores (10 técnicos + 4 rentabilidad)
        assert len(context.signals) == 14
        assert "book_imbalance" in context.signals
        assert "toxic_flow" in context.signals
        assert "expected_roi_at_depth" in context.signals
        assert "capital_absorption_capacity" in context.signals
    
    @pytest.mark.asyncio
    async def test_execute_with_strategy_type_in_context(self, context):
        """Test que calcula indicadores cuando strategy_type está en contexto."""
        context.strategy_type = "liquidity"
        config = {}
        
        node = CalculateIndicatorsNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
        assert hasattr(context, "signals")
        assert len(context.signals) == 14
    
    @pytest.mark.asyncio
    async def test_execute_with_default_strategy_type(self, context):
        """Test que usa 'liquidity' como default si no se especifica."""
        config = {}
        
        node = CalculateIndicatorsNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
        assert hasattr(context, "signals")
        assert len(context.signals) == 14
    
    @pytest.mark.asyncio
    async def test_execute_handles_errors_gracefully(self, context):
        """Test que maneja errores sin fallar el nodo."""
        config = {
            "strategy_type": "invalid_type"
        }
        
        node = CalculateIndicatorsNode(config, context)
        result = await node.execute()
        
        # Debe retornar SuccessResult aunque haya error
        assert isinstance(result, SuccessResult)
        # Las señales deben estar vacías o None
        assert hasattr(context, "signals")
    
    @pytest.mark.asyncio
    async def test_execute_injects_signals_into_context(self, context):
        """Test que inyecta señales en el contexto."""
        config = {
            "strategy_type": "liquidity"
        }
        
        node = CalculateIndicatorsNode(config, context)
        result = await node.execute()
        
        assert isinstance(result, SuccessResult)
        # Verificar que las señales están en el contexto
        assert context.signals is not None
        # Al menos algunas señales deben estar calculadas (pueden ser None si faltan datos)
        assert isinstance(context.signals, dict)
    
    @pytest.mark.asyncio
    async def test_execute_saves_signals_to_decision_trace(self, context):
        """Test que las señales se guardan en DecisionTrace."""
        from unittest.mock import patch, MagicMock
        
        config = {
            "strategy_type": "liquidity"
        }
        
        # Mock DecisionTraceService
        with patch('app.core.strategy_engine.nodes.calculate_indicators.DecisionTraceService') as mock_trace_service_class:
            mock_trace_service = MagicMock()
            mock_trace_service_class.return_value = mock_trace_service
            
            node = CalculateIndicatorsNode(config, context)
            result = await node.execute()
            
            # Debe retornar SuccessResult
            assert isinstance(result, SuccessResult)
            
            # Debe haber llamado a log_decision si hay trace_id
            if context.trace_id:
                assert mock_trace_service.log_decision.called
                
                # Verificar argumentos del llamado
                call_args = mock_trace_service.log_decision.call_args
                assert call_args.kwargs["trace_id"] == context.trace_id
                assert call_args.kwargs["component"] == "strategy"
                assert call_args.kwargs["decision_stage"] == "SIGNALS_CALCULATION"
                assert call_args.kwargs["decision"] == "COMPLETED"
                assert "signals" in call_args.kwargs["output_data"]
                assert "signals_count" in call_args.kwargs["output_data"]

