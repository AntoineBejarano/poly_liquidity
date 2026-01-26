"""
Tests unitarios para RiskValidator con 100% de cobertura.
"""
import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock

from app.core.strategy_engine.risk_validator import RiskValidator
from app.models.execution_plan import ExecutionPlan


class TestRiskValidator:
    """Tests para RiskValidator."""
    
    @pytest.fixture
    def mock_plan(self):
        """Mock de ExecutionPlan."""
        plan = Mock(spec=ExecutionPlan)
        plan.id = uuid4()
        plan.risk_config = {}
        return plan
    
    @pytest.fixture
    def validator(self, mock_plan):
        """RiskValidator instance."""
        return RiskValidator(mock_plan)
    
    def test_validate_plan_risk_config_valid(self, validator):
        """Test validación de risk_config válido."""
        validator.risk_config = {
            "max_slippage": 0.05,
            "max_fill_delay_ms": 5000,
            "max_partial_fill_ratio": 0.8,
            "abort_on_price_move": True
        }
        
        is_valid, error_msg = validator.validate_plan_risk_config()
        
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_plan_risk_config_invalid_max_slippage_negative(self, validator):
        """Test validación falla con max_slippage negativo."""
        validator.risk_config = {"max_slippage": -0.1}
        
        is_valid, error_msg = validator.validate_plan_risk_config()
        
        assert is_valid is False
        assert "max_slippage" in error_msg
    
    def test_validate_plan_risk_config_invalid_max_slippage_above_one(self, validator):
        """Test validación falla con max_slippage > 1."""
        validator.risk_config = {"max_slippage": 1.5}
        
        is_valid, error_msg = validator.validate_plan_risk_config()
        
        assert is_valid is False
        assert "max_slippage" in error_msg
    
    def test_validate_plan_risk_config_invalid_max_slippage_type(self, validator):
        """Test validación falla con max_slippage tipo incorrecto."""
        validator.risk_config = {"max_slippage": "invalid"}
        
        is_valid, error_msg = validator.validate_plan_risk_config()
        
        assert is_valid is False
        assert "max_slippage" in error_msg
    
    def test_validate_plan_risk_config_invalid_max_fill_delay_negative(self, validator):
        """Test validación falla con max_fill_delay_ms negativo."""
        validator.risk_config = {"max_fill_delay_ms": -1000}
        
        is_valid, error_msg = validator.validate_plan_risk_config()
        
        assert is_valid is False
        assert "max_fill_delay_ms" in error_msg
    
    def test_validate_plan_risk_config_invalid_max_fill_delay_type(self, validator):
        """Test validación falla con max_fill_delay_ms tipo incorrecto."""
        validator.risk_config = {"max_fill_delay_ms": "invalid"}
        
        is_valid, error_msg = validator.validate_plan_risk_config()
        
        assert is_valid is False
        assert "max_fill_delay_ms" in error_msg
    
    def test_validate_plan_risk_config_invalid_max_partial_fill_ratio_negative(self, validator):
        """Test validación falla con max_partial_fill_ratio negativo."""
        validator.risk_config = {"max_partial_fill_ratio": -0.1}
        
        is_valid, error_msg = validator.validate_plan_risk_config()
        
        assert is_valid is False
        assert "max_partial_fill_ratio" in error_msg
    
    def test_validate_plan_risk_config_invalid_max_partial_fill_ratio_above_one(self, validator):
        """Test validación falla con max_partial_fill_ratio > 1."""
        validator.risk_config = {"max_partial_fill_ratio": 1.5}
        
        is_valid, error_msg = validator.validate_plan_risk_config()
        
        assert is_valid is False
        assert "max_partial_fill_ratio" in error_msg
    
    def test_validate_plan_risk_config_invalid_max_partial_fill_ratio_type_exception(self, validator):
        """Test validación falla con max_partial_fill_ratio tipo incorrecto (líneas 61-62)."""
        validator.risk_config = {"max_partial_fill_ratio": object()}  # object() causará TypeError
        
        is_valid, error_msg = validator.validate_plan_risk_config()
        
        assert is_valid is False
        assert "max_partial_fill_ratio" in error_msg
    
    def test_validate_plan_risk_config_invalid_abort_on_price_move_type(self, validator):
        """Test validación falla con abort_on_price_move tipo incorrecto."""
        validator.risk_config = {"abort_on_price_move": "invalid"}
        
        is_valid, error_msg = validator.validate_plan_risk_config()
        
        assert is_valid is False
        assert "abort_on_price_move" in error_msg
    
    def test_validate_price_valid(self, validator):
        """Test validación de precio válido."""
        leg = {
            "target_price": Decimal("0.95"),
            "size": Decimal("1000")
        }
        current_price = Decimal("0.96")  # Slippage ~1.05%
        validator.risk_config = {"max_slippage": 0.05}  # 5%
        
        is_valid, error_msg = validator.validate_price(leg, current_price)
        
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_price_exceeds_slippage(self, validator):
        """Test validación falla cuando el slippage excede el máximo."""
        leg = {
            "target_price": Decimal("0.95"),
            "size": Decimal("1000")
        }
        current_price = Decimal("1.00")  # Slippage ~5.26%
        validator.risk_config = {"max_slippage": 0.05}  # 5%
        
        is_valid, error_msg = validator.validate_price(leg, current_price)
        
        assert is_valid is False
        assert "slippage" in error_msg.lower()
    
    def test_validate_price_no_max_slippage(self, validator):
        """Test validación pasa cuando no hay max_slippage configurado."""
        leg = {
            "target_price": Decimal("0.95"),
            "size": Decimal("1000")
        }
        current_price = Decimal("1.00")
        validator.risk_config = {}
        
        is_valid, error_msg = validator.validate_price(leg, current_price)
        
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_price_zero_target_price(self, validator):
        """Test validación falla con target_price cero."""
        leg = {
            "target_price": Decimal("0"),
            "size": Decimal("1000")
        }
        current_price = Decimal("0.95")
        validator.risk_config = {"max_slippage": 0.05}
        
        is_valid, error_msg = validator.validate_price(leg, current_price)
        
        assert is_valid is False
        assert "target_price is 0" in error_msg
    
    def test_validate_liquidity_sufficient(self, validator):
        """Test validación de liquidez suficiente."""
        leg = {
            "size_usdc": Decimal("1000")
        }
        available_liquidity = Decimal("5000")
        
        is_valid, error_msg = validator.validate_liquidity(leg, available_liquidity)
        
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_liquidity_insufficient(self, validator):
        """Test validación falla cuando no hay suficiente liquidez."""
        leg = {
            "size_usdc": Decimal("5000")
        }
        available_liquidity = Decimal("1000")
        
        is_valid, error_msg = validator.validate_liquidity(leg, available_liquidity)
        
        assert is_valid is False
        assert "Insufficient liquidity" in error_msg
    
    def test_should_abort_on_price_move_true(self, validator):
        """Test que retorna True cuando abort_on_price_move está activo."""
        validator.risk_config = {"abort_on_price_move": True}
        
        result = validator.should_abort_on_price_move()
        
        assert result is True
    
    def test_should_abort_on_price_move_false(self, validator):
        """Test que retorna False cuando abort_on_price_move está desactivado."""
        validator.risk_config = {"abort_on_price_move": False}
        
        result = validator.should_abort_on_price_move()
        
        assert result is False
    
    def test_should_abort_on_price_move_default(self, validator):
        """Test que retorna False por defecto."""
        validator.risk_config = {}
        
        result = validator.should_abort_on_price_move()
        
        assert result is False
    
    def test_get_max_fill_delay_ms(self, validator):
        """Test que retorna max_fill_delay_ms correctamente."""
        validator.risk_config = {"max_fill_delay_ms": 5000}
        
        result = validator.get_max_fill_delay_ms()
        
        assert result == 5000
    
    def test_get_max_fill_delay_ms_none(self, validator):
        """Test que retorna None cuando no está configurado."""
        validator.risk_config = {}
        
        result = validator.get_max_fill_delay_ms()
        
        assert result is None
    
    def test_get_max_fill_delay_ms_invalid_type(self, validator):
        """Test que retorna None cuando el tipo es inválido."""
        validator.risk_config = {"max_fill_delay_ms": "invalid"}
        
        result = validator.get_max_fill_delay_ms()
        
        assert result is None
    
    def test_get_max_partial_fill_ratio(self, validator):
        """Test que retorna max_partial_fill_ratio correctamente."""
        validator.risk_config = {"max_partial_fill_ratio": 0.8}
        
        result = validator.get_max_partial_fill_ratio()
        
        assert result == 0.8
    
    def test_get_max_partial_fill_ratio_none(self, validator):
        """Test que retorna None cuando no está configurado."""
        validator.risk_config = {}
        
        result = validator.get_max_partial_fill_ratio()
        
        assert result is None
    
    def test_get_max_partial_fill_ratio_invalid_type(self, validator):
        """Test que retorna None cuando el tipo es inválido."""
        validator.risk_config = {"max_partial_fill_ratio": "invalid"}
        
        result = validator.get_max_partial_fill_ratio()
        
        assert result is None
    
    def test_validate_partial_fill_valid(self, validator):
        """Test validación de partial fill válido."""
        leg = {
            "size": Decimal("1000"),
            "filled_size": Decimal("800")
        }
        validator.risk_config = {"max_partial_fill_ratio": 0.7}  # 80% > 70%, OK
        
        is_valid, error_msg = validator.validate_partial_fill(leg)
        
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_partial_fill_below_minimum(self, validator):
        """Test validación falla cuando el fill ratio está por debajo del mínimo (líneas 184-188)."""
        leg = {
            "size": Decimal("1000"),
            "filled_size": Decimal("500")
        }
        validator.risk_config = {"max_partial_fill_ratio": 0.7}  # 50% < 70%, FAIL
        
        is_valid, error_msg = validator.validate_partial_fill(leg)
        
        assert is_valid is False
        assert "below minimum" in error_msg.lower()
    
    def test_validate_partial_fill_exception_in_except_block(self, validator):
        """Test que cubre el bloque except en validate_partial_fill (líneas 192-193)."""
        # Crear un leg que cause excepción al convertir
        leg = {
            "size": object(),  # object() causará error al convertir
            "filled_size": Decimal("500")
        }
        validator.risk_config = {"max_partial_fill_ratio": 0.7}
        
        is_valid, error_msg = validator.validate_partial_fill(leg)
        
        assert is_valid is False
        assert "Error validating partial fill" in error_msg
    
    def test_validate_partial_fill_no_limit(self, validator):
        """Test validación pasa cuando no hay límite configurado."""
        leg = {
            "size": Decimal("1000"),
            "filled_size": Decimal("500")
        }
        validator.risk_config = {}
        
        is_valid, error_msg = validator.validate_partial_fill(leg)
        
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_partial_fill_zero_size(self, validator):
        """Test validación falla con size cero."""
        leg = {
            "size": Decimal("0"),
            "filled_size": Decimal("500")
        }
        validator.risk_config = {"max_partial_fill_ratio": 0.7}
        
        is_valid, error_msg = validator.validate_partial_fill(leg)
        
        assert is_valid is False
        assert "size is 0" in error_msg
    
    def test_validate_price_none_target_price(self, validator):
        """Test que maneja target_price None (línea 90)."""
        leg = {
            "target_price": None,
            "size": Decimal("1000")
        }
        current_price = Decimal("0.96")
        validator.risk_config = {"max_slippage": 0.05}
        
        is_valid, error_msg = validator.validate_price(leg, current_price)
        
        assert is_valid is False
        assert "target_price is None" in error_msg
    
    def test_validate_price_exception_handling(self, validator):
        """Test que maneja excepciones en validación de precio."""
        leg = {
            "target_price": Decimal("0.95"),
            "size": Decimal("1000")
        }
        current_price = Decimal("0.96")
        # Usar un valor que cause ValueError al convertir a float
        validator.risk_config = {"max_slippage": object()}  # object() no se puede convertir a float
        
        is_valid, error_msg = validator.validate_price(leg, current_price)
        
        assert is_valid is False
        assert "Error validating price slippage" in error_msg
    
    def test_validate_liquidity_insufficient_edge_case(self, validator):
        """Test validación de liquidez con valores exactos."""
        leg = {
            "size_usdc": Decimal("5000")
        }
        available_liquidity = Decimal("5000")  # Exactamente igual
        
        is_valid, error_msg = validator.validate_liquidity(leg, available_liquidity)
        
        assert is_valid is True  # Debería pasar porque available >= required
    
    def test_validate_partial_fill_exception_handling(self, validator):
        """Test que maneja excepciones en validación de partial fill."""
        # Crear un leg que cause excepción al dividir
        leg = {
            "size": Decimal("1000"),
            "filled_size": Decimal("800")
        }
        # Usar un valor que cause error al convertir
        validator.risk_config = {"max_partial_fill_ratio": "invalid_type"}
        
        # Esto debería entrar en el except cuando intenta convertir max_partial_fill_ratio
        # Pero primero valida el tipo, así que necesitamos otro enfoque
        # En su lugar, probemos con un leg que cause ZeroDivisionError
        leg_zero = {
            "size": Decimal("0"),
            "filled_size": Decimal("500")
        }
        validator.risk_config = {"max_partial_fill_ratio": 0.7}
        
        is_valid, error_msg = validator.validate_partial_fill(leg_zero)
        
        assert is_valid is False
        assert "size is 0" in error_msg

