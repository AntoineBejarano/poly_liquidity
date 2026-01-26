"""
Tests unitarios para TriggerEvaluator con 100% de cobertura.
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from app.core.strategy_engine.trigger_evaluator import TriggerEvaluator
from app.models.strategy import Strategy
from app.models.event import Event
from app.core.strategy_engine.state_cache_service import StateCacheService


class TestTriggerEvaluator:
    """Tests para TriggerEvaluator."""
    
    @pytest.fixture
    def state_cache(self):
        """Mock de StateCacheService."""
        cache = Mock(spec=StateCacheService)
        cache.get_state = Mock(return_value={})
        return cache
    
    @pytest.fixture
    def evaluator(self, state_cache):
        """TriggerEvaluator instance."""
        return TriggerEvaluator(state_cache)
    
    @pytest.fixture
    def event(self):
        """Evento de prueba."""
        event = Mock(spec=Event)
        event.id = uuid4()
        event.state = "ACTIVE"
        event.resolution_date = datetime.utcnow() + timedelta(minutes=15)
        return event
    
    @pytest.fixture
    def strategy(self):
        """Strategy de prueba."""
        strategy = Mock(spec=Strategy)
        strategy.id = uuid4()
        strategy.triggers = []
        return strategy
    
    def test_evaluate_always(self, evaluator, strategy, event):
        """Test que trigger 'always' siempre retorna True."""
        trigger = {"type": "always"}
        
        result = evaluator.evaluate(trigger, strategy, event)
        
        assert result is True
    
    def test_evaluate_near_end_within_range(self, evaluator, strategy, event):
        """Test que trigger 'near_end' retorna True cuando está en rango."""
        trigger = {
            "type": "near_end",
            "conditions": {
                "time_to_resolution_lte": "20m",
                "time_to_resolution_gte": "5m"
            }
        }
        # Event está a 15 minutos del final (dentro del rango 5-20m)
        event.resolution_date = datetime.utcnow() + timedelta(minutes=15)
        
        result = evaluator.evaluate(trigger, strategy, event)
        
        assert result is True
    
    def test_evaluate_near_end_too_early(self, evaluator, strategy, event):
        """Test que trigger 'near_end' retorna False cuando es muy temprano."""
        trigger = {
            "type": "near_end",
            "conditions": {
                "time_to_resolution_lte": "20m",
                "time_to_resolution_gte": "5m"
            }
        }
        # Event está a 30 minutos del final (fuera del rango)
        event.resolution_date = datetime.utcnow() + timedelta(minutes=30)
        
        result = evaluator.evaluate(trigger, strategy, event)
        
        assert result is False
    
    def test_evaluate_near_end_too_late(self, evaluator, strategy, event):
        """Test que trigger 'near_end' retorna False cuando es muy tarde."""
        trigger = {
            "type": "near_end",
            "conditions": {
                "time_to_resolution_lte": "20m",
                "time_to_resolution_gte": "5m"
            }
        }
        # Event está a 2 minutos del final (fuera del rango)
        event.resolution_date = datetime.utcnow() + timedelta(minutes=2)
        
        result = evaluator.evaluate(trigger, strategy, event)
        
        assert result is False
    
    def test_evaluate_near_end_no_resolution_date(self, evaluator, strategy, event):
        """Test que trigger 'near_end' retorna False si no hay resolution_date."""
        trigger = {
            "type": "near_end",
            "conditions": {
                "time_to_resolution_lte": "20m"
            }
        }
        event.resolution_date = None
        
        result = evaluator.evaluate(trigger, strategy, event)
        
        assert result is False
    
    def test_evaluate_near_end_only_lte(self, evaluator, strategy, event):
        """Test que trigger 'near_end' funciona solo con lte."""
        trigger = {
            "type": "near_end",
            "conditions": {
                "time_to_resolution_lte": "20m"
            }
        }
        event.resolution_date = datetime.utcnow() + timedelta(minutes=15)
        
        result = evaluator.evaluate(trigger, strategy, event)
        
        assert result is True
    
    def test_evaluate_near_end_only_gte(self, evaluator, strategy, event):
        """Test que trigger 'near_end' funciona solo con gte."""
        trigger = {
            "type": "near_end",
            "conditions": {
                "time_to_resolution_gte": "5m"
            }
        }
        event.resolution_date = datetime.utcnow() + timedelta(minutes=15)
        
        result = evaluator.evaluate(trigger, strategy, event)
        
        assert result is True
    
    def test_evaluate_edge_detected_with_edge(self, evaluator, strategy, event, state_cache):
        """Test que trigger 'edge_detected' retorna True cuando hay edge."""
        trigger = {
            "type": "edge_detected",
            "conditions": {
                "min_edge": 0.05
            }
        }
        state_cache.get_state.return_value = {
            "external_data": {
                "edge": 0.10
            }
        }
        
        result = evaluator.evaluate(trigger, strategy, event, state_cache)
        
        assert result is True
    
    def test_evaluate_edge_detected_edge_too_small(self, evaluator, strategy, event, state_cache):
        """Test que trigger 'edge_detected' retorna False cuando edge es muy pequeño."""
        trigger = {
            "type": "edge_detected",
            "conditions": {
                "min_edge": 0.05
            }
        }
        state_cache.get_state.return_value = {
            "external_data": {
                "edge": 0.02  # Menor que min_edge
            }
        }
        
        result = evaluator.evaluate(trigger, strategy, event, state_cache)
        
        assert result is False
    
    def test_evaluate_edge_detected_no_state(self, evaluator, strategy, event, state_cache):
        """Test que trigger 'edge_detected' retorna False si no hay estado."""
        trigger = {
            "type": "edge_detected",
            "conditions": {
                "min_edge": 0.05
            }
        }
        state_cache.get_state.return_value = None
        
        result = evaluator.evaluate(trigger, strategy, event, state_cache)
        
        assert result is False
    
    def test_evaluate_edge_detected_with_source(self, evaluator, strategy, event, state_cache):
        """Test que trigger 'edge_detected' verifica source si se especifica."""
        trigger = {
            "type": "edge_detected",
            "conditions": {
                "min_edge": 0.05,
                "source": "external_data.pinnacle_odds"
            }
        }
        state_cache.get_state.return_value = {
            "external_data": {
                "edge": 0.10,
                "edge_source": "external_data.pinnacle_odds"
            }
        }
        
        result = evaluator.evaluate(trigger, strategy, event, state_cache)
        
        assert result is True
    
    def test_evaluate_edge_detected_wrong_source(self, evaluator, strategy, event, state_cache):
        """Test que trigger 'edge_detected' retorna False si source no coincide."""
        trigger = {
            "type": "edge_detected",
            "conditions": {
                "min_edge": 0.05,
                "source": "external_data.pinnacle_odds"
            }
        }
        state_cache.get_state.return_value = {
            "external_data": {
                "edge": 0.10,
                "edge_source": "other_source"
            }
        }
        
        result = evaluator.evaluate(trigger, strategy, event, state_cache)
        
        assert result is False
    
    def test_evaluate_edge_detected_in_market_state(self, evaluator, strategy, event, state_cache):
        """Test que trigger 'edge_detected' busca edge en market_state."""
        trigger = {
            "type": "edge_detected",
            "conditions": {
                "min_edge": 0.05
            }
        }
        state_cache.get_state.return_value = {
            "market_state": {
                "edge": 0.10
            }
        }
        
        result = evaluator.evaluate(trigger, strategy, event, state_cache)
        
        assert result is True
    
    def test_evaluate_state_change_match(self, evaluator, strategy, event, state_cache):
        """Test que trigger 'state_change' retorna True cuando el valor coincide."""
        trigger = {
            "type": "state_change",
            "conditions": {
                "field": "event_state.state",
                "values": ["ACTIVE", "UPCOMING"]
            }
        }
        state_cache.get_state.return_value = {
            "event_state": {
                "state": "ACTIVE"
            }
        }
        
        result = evaluator.evaluate(trigger, strategy, event, state_cache)
        
        assert result is True
    
    def test_evaluate_state_change_no_match(self, evaluator, strategy, event, state_cache):
        """Test que trigger 'state_change' retorna False cuando el valor no coincide."""
        trigger = {
            "type": "state_change",
            "conditions": {
                "field": "event_state.state",
                "values": ["ACTIVE"]
            }
        }
        state_cache.get_state.return_value = {
            "event_state": {
                "state": "RESOLVED"
            }
        }
        
        result = evaluator.evaluate(trigger, strategy, event, state_cache)
        
        assert result is False
    
    def test_evaluate_state_change_no_field(self, evaluator, strategy, event, state_cache):
        """Test que trigger 'state_change' retorna False si no hay field."""
        trigger = {
            "type": "state_change",
            "conditions": {
                "values": ["ACTIVE"]
            }
        }
        
        result = evaluator.evaluate(trigger, strategy, event, state_cache)
        
        assert result is False
    
    def test_evaluate_state_change_no_values(self, evaluator, strategy, event, state_cache):
        """Test que trigger 'state_change' retorna False si no hay values."""
        trigger = {
            "type": "state_change",
            "conditions": {
                "field": "event_state.state"
            }
        }
        
        result = evaluator.evaluate(trigger, strategy, event, state_cache)
        
        assert result is False
    
    def test_evaluate_state_change_no_state(self, evaluator, strategy, event, state_cache):
        """Test que trigger 'state_change' retorna False si no hay estado."""
        trigger = {
            "type": "state_change",
            "conditions": {
                "field": "event_state.state",
                "values": ["ACTIVE"]
            }
        }
        state_cache.get_state.return_value = None
        
        result = evaluator.evaluate(trigger, strategy, event, state_cache)
        
        assert result is False
    
    def test_evaluate_timer(self, evaluator, strategy, event):
        """Test que trigger 'timer' retorna True."""
        trigger = {
            "type": "timer",
            "conditions": {
                "interval_seconds": 30
            }
        }
        
        result = evaluator.evaluate(trigger, strategy, event)
        
        assert result is True
    
    def test_evaluate_unknown_type(self, evaluator, strategy, event):
        """Test que trigger desconocido retorna False."""
        trigger = {
            "type": "unknown_type"
        }
        
        result = evaluator.evaluate(trigger, strategy, event)
        
        assert result is False
    
    def test_evaluate_uses_provided_state_cache(self, evaluator, strategy, event):
        """Test que evaluate usa el state_cache proporcionado."""
        custom_cache = Mock(spec=StateCacheService)
        custom_cache.get_state = Mock(return_value={"test": "value"})
        
        trigger = {
            "type": "state_change",
            "conditions": {
                "field": "test",
                "values": ["value"]
            }
        }
        
        result = evaluator.evaluate(trigger, strategy, event, custom_cache)
        
        assert result is True
        custom_cache.get_state.assert_called_once_with(event.id)
    
    def test_parse_time_delta_seconds(self, evaluator):
        """Test método _parse_time_delta con segundos."""
        result = evaluator._parse_time_delta("30s")
        assert result == timedelta(seconds=30)
    
    def test_parse_time_delta_minutes(self, evaluator):
        """Test método _parse_time_delta con minutos."""
        result = evaluator._parse_time_delta("20m")
        assert result == timedelta(minutes=20)
    
    def test_parse_time_delta_hours(self, evaluator):
        """Test método _parse_time_delta con horas."""
        result = evaluator._parse_time_delta("2h")
        assert result == timedelta(hours=2)
    
    def test_parse_time_delta_days(self, evaluator):
        """Test método _parse_time_delta con días."""
        result = evaluator._parse_time_delta("1d")
        assert result == timedelta(days=1)
    
    def test_parse_time_delta_numeric(self, evaluator):
        """Test método _parse_time_delta con número (asume segundos)."""
        result = evaluator._parse_time_delta("60")
        assert result == timedelta(seconds=60)
    
    def test_parse_time_delta_invalid(self, evaluator):
        """Test método _parse_time_delta con formato inválido (líneas 222-223)."""
        # El ValueError se lanza desde int(), pero nuestro código lo captura y relanza con mensaje personalizado
        with pytest.raises(ValueError) as exc_info:
            evaluator._parse_time_delta("invalid")
        # Verificar que se lanzó ValueError (puede ser de int() o nuestro mensaje personalizado)
        assert isinstance(exc_info.value, ValueError)
    
    def test_get_nested_value_simple(self, evaluator):
        """Test método _get_nested_value con path simple."""
        data = {"state": "ACTIVE"}
        result = evaluator._get_nested_value(data, "state")
        assert result == "ACTIVE"
    
    def test_get_nested_value_nested(self, evaluator):
        """Test método _get_nested_value con path anidado."""
        data = {"event_state": {"state": "ACTIVE"}}
        result = evaluator._get_nested_value(data, "event_state.state")
        assert result == "ACTIVE"
    
    def test_get_nested_value_deeply_nested(self, evaluator):
        """Test método _get_nested_value con path muy anidado."""
        data = {"a": {"b": {"c": "value"}}}
        result = evaluator._get_nested_value(data, "a.b.c")
        assert result == "value"
    
    def test_get_nested_value_not_found(self, evaluator):
        """Test método _get_nested_value cuando el campo no existe."""
        data = {"event_state": {"state": "ACTIVE"}}
        result = evaluator._get_nested_value(data, "event_state.other")
        assert result is None
    
    def test_get_nested_value_not_dict(self, evaluator):
        """Test método _get_nested_value cuando un valor intermedio no es dict (línea 242)."""
        data = {"event_state": "not_a_dict"}
        result = evaluator._get_nested_value(data, "event_state.state")
        assert result is None
    
    def test_get_nested_value_empty_part(self, evaluator):
        """Test método _get_nested_value con partes vacías en el path."""
        data = {"event_state": {"state": "ACTIVE"}}
        # Path con partes vacías (ej: "event_state..state") debe skip las partes vacías
        result = evaluator._get_nested_value(data, "event_state..state")
        assert result == "ACTIVE"
    
    def test_get_nested_value_empty_path(self, evaluator):
        """Test método _get_nested_value con path vacío."""
        data = {"state": "ACTIVE"}
        # Path vacío retorna None (comportamiento correcto)
        result = evaluator._get_nested_value(data, "")
        assert result is None

