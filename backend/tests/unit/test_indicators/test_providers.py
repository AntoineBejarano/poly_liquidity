"""
Tests unitarios para proveedores de señales (LiquidityProvider y ArbitrageProvider).
"""
import pytest
from unittest.mock import Mock
from uuid import uuid4

from app.core.strategy_engine.indicators.liquidity_provider import LiquidityProvider
from app.core.strategy_engine.indicators.arbitrage_provider import ArbitrageProvider
from app.core.strategy_engine.models import GraphExecutionContext


@pytest.fixture
def mock_context():
    """Crea un contexto mock para testing."""
    context = Mock(spec=GraphExecutionContext)
    context.strategy_id = uuid4()
    context.event_id = uuid4()
    context.market_id = uuid4()
    context.trace_id = uuid4()
    context.collected_state = {}
    return context


class TestLiquidityProvider:
    """Tests para LiquidityProvider."""
    
    def test_init(self, mock_context):
        """Test inicialización."""
        provider = LiquidityProvider(mock_context)
        
        assert provider.context == mock_context
        assert provider._collected_state == {}
    
    def test_validate_data_with_market_state(self, mock_context):
        """Test validate_data cuando hay market_state."""
        mock_context.collected_state = {"market_state": {"price": 0.98}}
        provider = LiquidityProvider(mock_context)
        
        assert provider.validate_data() is True
    
    def test_validate_data_without_market_state(self, mock_context):
        """Test validate_data cuando no hay market_state."""
        mock_context.collected_state = {}
        provider = LiquidityProvider(mock_context)
        
        assert provider.validate_data() is False
    
    def test_calculate_all_with_valid_data(self, mock_context):
        """Test calculate_all con datos válidos."""
        mock_context.collected_state = {"market_state": {"price": 0.98}}
        provider = LiquidityProvider(mock_context)
        
        signals = provider.calculate_all()
        
        # Debe retornar dict con todas las señales (técnicas + rentabilidad)
        assert isinstance(signals, dict)
        # Indicadores técnicos
        assert "book_imbalance" in signals
        assert "toxic_flow" in signals
        assert "inventory_skew" in signals
        assert "price_drift" in signals
        assert "spread_elasticity" in signals
        assert "cancel_rate" in signals
        assert "rel_liquidity" in signals
        assert "tw_volatility" in signals
        assert "res_gap" in signals
        assert "slippage_impact" in signals
        # Indicadores de rentabilidad (Quant Engine)
        assert "expected_roi_at_depth" in signals
        assert "capital_absorption_capacity" in signals
        assert "time_value_score" in signals
        assert "slippage_impact_100k" in signals
        
        # Total: 14 indicadores (10 técnicos + 4 rentabilidad)
        assert len(signals) == 14
    
    def test_calculate_all_without_valid_data(self, mock_context):
        """Test calculate_all sin datos válidos."""
        mock_context.collected_state = {}
        provider = LiquidityProvider(mock_context)
        
        signals = provider.calculate_all()
        
        # Debe retornar dict con todas las señales en None
        assert isinstance(signals, dict)
        assert len(signals) == 14  # 10 técnicos + 4 rentabilidad
        assert all(v is None for v in signals.values())
    
    def test_calculate_all_clears_memo_cache(self, mock_context):
        """Test que calculate_all limpia el memo cache al inicio."""
        mock_context.collected_state = {"market_state": {"price": 0.98}}
        provider = LiquidityProvider(mock_context)
        
        # Llenar cache antes de calculate_all
        provider.memoize("test_key", lambda: "test_value")
        assert len(provider._memo_cache) == 1
        
        # Llamar calculate_all debe limpiar cache al inicio
        # (aunque durante la ejecución se puede llenar de nuevo con datos nuevos)
        provider.calculate_all()
        # El cache puede tener entradas nuevas de la ejecución, pero las antiguas deben estar limpiadas
        # Verificamos que "test_key" ya no está (fue limpiado)
        assert "test_key" not in provider._memo_cache
    
    def test_empty_signals(self, mock_context):
        """Test método _empty_signals."""
        provider = LiquidityProvider(mock_context)
        
        signals = provider._empty_signals()
        
        assert isinstance(signals, dict)
        assert len(signals) == 14  # 10 técnicos + 4 rentabilidad
        assert all(v is None for v in signals.values())
        # Verificar que incluye los nuevos indicadores
        assert "expected_roi_at_depth" in signals
        assert "capital_absorption_capacity" in signals
        assert "time_value_score" in signals
        assert "slippage_impact_100k" in signals


class TestArbitrageProvider:
    """Tests para ArbitrageProvider."""
    
    def test_init(self, mock_context):
        """Test inicialización."""
        provider = ArbitrageProvider(mock_context)
        
        assert provider.context == mock_context
        assert provider._collected_state == {}
    
    def test_validate_data_with_required_data(self, mock_context):
        """Test validate_data cuando hay market_state y external_data."""
        mock_context.collected_state = {
            "market_state": {"price": 0.98},
            "external_data": {"pinnacle_price": 0.99}
        }
        provider = ArbitrageProvider(mock_context)
        
        assert provider.validate_data() is True
    
    def test_validate_data_without_market_state(self, mock_context):
        """Test validate_data cuando falta market_state."""
        mock_context.collected_state = {
            "external_data": {"pinnacle_price": 0.99}
        }
        provider = ArbitrageProvider(mock_context)
        
        assert provider.validate_data() is False
    
    def test_validate_data_without_external_data(self, mock_context):
        """Test validate_data cuando falta external_data."""
        mock_context.collected_state = {
            "market_state": {"price": 0.98}
        }
        provider = ArbitrageProvider(mock_context)
        
        assert provider.validate_data() is False
    
    def test_calculate_all_with_valid_data(self, mock_context):
        """Test calculate_all con datos válidos."""
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        mock_context.collected_state = {
            "market_state": {
                "last_price": 0.48,
                "last_update": now.isoformat(),
                "liquidity": 5000
            },
            "external_data": {
                "pinnacle_price": 0.50,
                "last_update": now.isoformat(),
                "liquidity": 6000
            }
        }
        provider = ArbitrageProvider(mock_context)
        
        signals = provider.calculate_all()
        
        # Debe retornar dict con todas las señales
        assert isinstance(signals, dict)
        assert "net_arb_gap" in signals
        assert "latency_delta" in signals
        assert "liquidity_match" in signals
        assert "hedge_slippage" in signals
        assert "sync_status" in signals
        assert "price_correlation" in signals
        assert "fill_probability" in signals
        assert "rejection_risk" in signals
        assert "gas_impact" in signals
        assert "arb_persistence" in signals
        
        # Si los datos son confiables, unreliable no debe estar presente o debe ser None
        # Si los datos no son confiables, unreliable debe ser 1.0
        if "unreliable" in signals:
            assert signals["unreliable"] is None or signals["unreliable"] == 1.0
        
        # Al menos algunos indicadores deben estar calculados (pueden ser None si faltan datos)
        # Puede tener 10 o 11 claves dependiendo de si unreliable está presente
        assert len(signals) >= 10
    
    def test_calculate_all_without_valid_data(self, mock_context):
        """Test calculate_all sin datos válidos."""
        mock_context.collected_state = {}
        provider = ArbitrageProvider(mock_context)
        
        signals = provider.calculate_all()
        
        # Debe retornar dict con todas las señales en None
        assert isinstance(signals, dict)
        assert len(signals) == 11  # 10 indicadores + unreliable flag
        assert all(v is None for v in signals.values())
    
    def test_empty_signals(self, mock_context):
        """Test método _empty_signals."""
        provider = ArbitrageProvider(mock_context)
        
        signals = provider._empty_signals()
        
        assert isinstance(signals, dict)
        assert len(signals) == 11  # 10 indicadores + unreliable flag
        assert all(v is None for v in signals.values())
        # Verificar que incluye unreliable
        assert "unreliable" in signals
    
    def test_calculate_all_with_unreliable_data(self, mock_context):
        """Test calculate_all cuando los datos externos no son confiables."""
        from datetime import datetime, timezone, timedelta
        
        # Datos con latencia muy alta (> 2000ms)
        old_time = datetime.now(timezone.utc) - timedelta(seconds=35)  # Más de 30 segundos
        mock_context.collected_state = {
            "market_state": {
                "last_price": 0.48,
                "last_update": datetime.now(timezone.utc).isoformat(),
            },
            "external_data": {
                "pinnacle_price": 0.50,
                "last_update": old_time.isoformat(),  # Muy viejo
            }
        }
        provider = ArbitrageProvider(mock_context)
        
        signals = provider.calculate_all()
        
        # Debe retornar señales con flag unreliable = 1.0
        assert isinstance(signals, dict)
        assert "unreliable" in signals
        assert signals["unreliable"] == 1.0
        # Los demás indicadores deben ser None cuando es unreliable
        assert signals.get("net_arb_gap") is None

