"""
Tests unitarios para modelos del sistema de estrategias basado en grafos.
"""
import pytest
from uuid import uuid4
from datetime import datetime
from decimal import Decimal

from app.models.strategy import Strategy
from app.models.graph_node_definition import GraphNodeDefinition
from app.models.graph_execution import GraphExecution
from app.models.state_cache import StateCache
from app.models.strategy_event import StrategyEvent
from app.models.execution_intent import ExecutionIntent
from app.models.strategy_metric import StrategyMetric
from app.models.external_data_source import ExternalDataSource


class TestStrategy:
    """Tests para el modelo Strategy."""
    
    def test_strategy_creation(self):
        """Test que Strategy se puede crear con campos mínimos."""
        decision_graph = {
            "entry_node": "observe",
            "nodes": {
                "observe": {"type": "collect_state", "next": "end"},
                "end": {"type": "noop"}
            }
        }
        
        strategy = Strategy(
            name="Test Strategy",
            description="Test description",
            decision_graph=decision_graph,
            support_graphs=[],
            control_loop_config={},
            risk_config={}
        )
        
        assert strategy.name == "Test Strategy"
        assert strategy.description == "Test description"
        assert strategy.decision_graph == decision_graph
        assert strategy.support_graphs == []
        # is_active y version tienen default en DB, no en Python al instanciar
        # Verificamos que los campos se pueden establecer
        assert strategy.is_active is False or strategy.is_active is None
        assert strategy.version == 1 or strategy.version is None
    
    def test_strategy_with_all_fields(self):
        """Test que Strategy se puede crear con todos los campos."""
        decision_graph = {"entry_node": "start", "nodes": {}}
        support_graphs = [{"name": "test", "entry_node": "start", "nodes": {}}]
        control_loop_config = {"interval_seconds": 1}
        risk_config = {"max_exposure": 10000}
        tags = ["test", "demo"]
        
        strategy = Strategy(
            name="Full Strategy",
            description="Full description",
            decision_graph=decision_graph,
            support_graphs=support_graphs,
            control_loop_config=control_loop_config,
            risk_config=risk_config,
            tags=tags,
            is_active=True,
            version=2
        )
        
        assert strategy.name == "Full Strategy"
        assert strategy.support_graphs == support_graphs
        assert strategy.control_loop_config == control_loop_config
        assert strategy.risk_config == risk_config
        assert strategy.tags == tags
        assert strategy.is_active is True
        assert strategy.version == 2


class TestGraphNodeDefinition:
    """Tests para el modelo GraphNodeDefinition."""
    
    def test_graph_node_definition_creation(self):
        """Test que GraphNodeDefinition se puede crear."""
        config_schema = {
            "type": "object",
            "properties": {
                "sources": {"type": "array"}
            }
        }
        
        node = GraphNodeDefinition(
            node_type="collect_state",
            name="Collect State",
            description="Collects state from cache",
            category="state",
            path_type="hot",
            config_schema=config_schema
        )
        
        assert node.node_type == "collect_state"
        assert node.name == "Collect State"
        assert node.category == "state"
        assert node.path_type == "hot"
        assert node.config_schema == config_schema
        # is_builtin tiene default en DB, no en Python al instanciar
        assert node.is_builtin is True or node.is_builtin is None


class TestGraphExecution:
    """Tests para el modelo GraphExecution."""
    
    def test_graph_execution_creation(self):
        """Test que GraphExecution se puede crear."""
        strategy_id = uuid4()
        event_id = uuid4()
        trace_id = uuid4()
        started_at = datetime.utcnow()
        
        execution = GraphExecution(
            strategy_id=strategy_id,
            graph_type="decision",
            event_id=event_id,
            status="completed",
            started_at=started_at,
            completed_at=started_at,
            duration_ms=50,
            trace_id=trace_id
        )
        
        assert execution.strategy_id == strategy_id
        assert execution.graph_type == "decision"
        assert execution.event_id == event_id
        assert execution.status == "completed"
        assert execution.duration_ms == 50


class TestStateCache:
    """Tests para el modelo StateCache."""
    
    def test_state_cache_creation(self):
        """Test que StateCache se puede crear."""
        strategy_id = uuid4()
        event_id = uuid4()
        cache_key = f"event.{event_id}.market_state"
        cache_value = {"price": 0.98, "spread": 0.01}
        
        cache = StateCache(
            cache_key=cache_key,
            cache_value=cache_value,
            strategy_id=strategy_id,
            event_id=event_id
        )
        
        assert cache.cache_key == cache_key
        assert cache.cache_value == cache_value
        assert cache.strategy_id == strategy_id
        assert cache.event_id == event_id


class TestStrategyEvent:
    """Tests para el modelo StrategyEvent."""
    
    def test_strategy_event_creation(self):
        """Test que StrategyEvent se puede crear."""
        strategy_id = uuid4()
        event_id = uuid4()
        
        strategy_event = StrategyEvent(
            strategy_id=strategy_id,
            event_id=event_id,
            event_config={"override": True}
        )
        
        assert strategy_event.strategy_id == strategy_id
        assert strategy_event.event_id == event_id
        assert strategy_event.event_config == {"override": True}


class TestExecutionIntent:
    """Tests para el modelo ExecutionIntent."""
    
    def test_execution_intent_creation(self):
        """Test que ExecutionIntent se puede crear."""
        strategy_id = uuid4()
        event_id = uuid4()
        trace_id = uuid4()
        
        intent = ExecutionIntent(
            strategy_id=strategy_id,
            event_id=event_id,
            side="BUY",
            outcome="YES",
            target_price=Decimal("0.98"),
            size=Decimal("100.0"),
            size_usdc=Decimal("98.0"),
            reason="Test reason",
            trace_id=trace_id
        )
        
        assert intent.strategy_id == strategy_id
        assert intent.event_id == event_id
        assert intent.side == "BUY"
        assert intent.outcome == "YES"
        assert intent.target_price == Decimal("0.98")
        assert intent.size == Decimal("100.0")
        # status tiene default en DB, no en Python al instanciar
        assert intent.status == "PENDING" or intent.status is None


class TestStrategyMetric:
    """Tests para el modelo StrategyMetric."""
    
    def test_strategy_metric_creation(self):
        """Test que StrategyMetric se puede crear."""
        strategy_id = uuid4()
        period_start = datetime.utcnow()
        period_end = datetime.utcnow()
        
        metric = StrategyMetric(
            strategy_id=strategy_id,
            period_start=period_start,
            period_end=period_end,
            total_intents=10,
            approved_intents=8,
            executed_intents=5,
            rejected_intents=2
        )
        
        assert metric.strategy_id == strategy_id
        assert metric.period_start == period_start
        assert metric.total_intents == 10
        assert metric.approved_intents == 8


class TestExternalDataSource:
    """Tests para el modelo ExternalDataSource."""
    
    def test_external_data_source_creation(self):
        """Test que ExternalDataSource se puede crear."""
        connector_config = {
            "base_url": "https://api.example.com",
            "api_key": "secret_key",
            "headers": {"Authorization": "Bearer token"}
        }
        
        source = ExternalDataSource(
            name="Test API",
            connector_type="custom_api",
            description="Test external source",
            connector_config=connector_config
        )
        
        assert source.name == "Test API"
        assert source.connector_type == "custom_api"
        assert source.connector_config == connector_config
        # is_active tiene default en DB, no en Python al instanciar
        assert source.is_active is True or source.is_active is None

    def test_external_data_source_connector_type_ps3838(self):
        """ExternalDataSource acepta connector_type ps3838 para cuenta PS3838."""
        source = ExternalDataSource(
            name="Mi cuenta PS3838",
            connector_type="ps3838",
            connector_config={"username": "user", "password_encrypted": "***"},
        )
        assert source.connector_type == "ps3838"
        assert source.connector_config.get("username") == "user"

    def test_external_data_source_connector_type_telegram(self):
        """ExternalDataSource acepta connector_type telegram (sesión + monitored_chats)."""
        source = ExternalDataSource(
            name="Telegram principal",
            connector_type="telegram",
            connector_config={
                "session_encrypted": "***",
                "monitored_chats": [-1001234567890, -1009876543210],
            },
        )
        assert source.connector_type == "telegram"
        assert source.connector_config.get("monitored_chats") == [-1001234567890, -1009876543210]

