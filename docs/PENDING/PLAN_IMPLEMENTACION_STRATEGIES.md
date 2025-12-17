# Plan de Implementación - Sistema de Estrategias Basado en Grafos

## Objetivo

Implementar un sistema completo de estrategias declarativas basado en grafos, donde los traders profesionales puedan:
- Crear múltiples estrategias independientes desde el frontend
- Configurar estrategias usando grafos visuales (Decision Graph + Support Graphs)
- Activar/desactivar estrategias
- Ver la operativa detallada de cada estrategia
- Comparar rentabilidad entre estrategias

**Arquitectura clave:** Control Loop + Decision Graph (hot path) + Support Graphs (cold path)

---

## Principios Fundamentales

### Del documento STRATEGIES.md:
1. **Strategy es la entidad raíz**, no markets o events
2. **Event es la unidad de ejecución atómica**, no el market
3. **Las estrategias NO llaman APIs directamente**
4. **Las fuentes de datos externas son totalmente configurables desde DB/frontend**
5. **No hay nombres de mercados externos hardcodeados en la lógica del backend**
6. **Solo el venue de ejecución está fijo** (Polymarket)
7. **Todas las demás fuentes de datos son plugins, definidos en runtime**
8. **Las estrategias deben ser declarativas, no lógica hardcodeada**

### Del nuevo diseño de grafos:
9. **Una estrategia NO es un workflow finito**, es un **control loop** que vive
10. **Decision Graph es stateless**, se evalúa una vez por ciclo y termina
11. **Support Graphs son asíncronos**, actualizan State Cache, NO bloquean
12. **Decision Graph solo lee estado**, nunca llama APIs, nunca espera
13. **IA solo para generar/validar grafos**, NO en hot path
14. **Estado vive en servicios especializados**, no en grafos

---

## Arquitectura: División en Niveles

```
Strategy (proceso vivo, long-lived)
 ├── Control Loop (infraestructura fija, no editable)
 │   └── Itera sobre eventos activos
 │   └── Dispara evaluaciones del Decision Graph
 │
 ├── Decision Graph (hot path, declarativo, JSON)
 │   └── Se evalúa una vez por ciclo
 │   └── Stateless, rápido (< 50μs)
 │   └── Solo lee State Cache
 │   └── Emite Execution Intents
 │
 └── Support Graphs (cold path, async)
     └── Alimentan State Cache
     └── Pueden usar IA, APIs, tardar
     └── Se ejecutan por evento/timer/trigger
```

---

## FASE 1: Base de Datos y Modelos

### 1.1. Modelos SQLAlchemy

#### `models/strategy.py` - Modelo principal de estrategia

```python
class Strategy(BaseModel):
    __tablename__ = "strategies"
    
    # Identificación
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Estado (proceso vivo)
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    enabled_at = Column(DateTime, nullable=True)
    disabled_at = Column(DateTime, nullable=True)
    
    # Decision Graph (hot path) - JSON declarativo
    decision_graph = Column(JSONB, nullable=False)  # Grafo principal de decisión
    
    # Support Graphs (cold path) - Array de grafos auxiliares
    support_graphs = Column(JSONB, nullable=False, default=[])  # Lista de grafos de soporte
    
    # Configuración de Control Loop
    control_loop_config = Column(JSONB, nullable=False, default={})  # Intervalo, triggers, etc.
    
    # Configuración de riesgo y sizing
    risk_config = Column(JSONB, nullable=False, default={})  # max_exposure, max_order_size, etc.
    
    # Metadata
    created_by = Column(String, ForeignKey("neon_auth.users_sync.id"), nullable=True)
    tags = Column(JSONB, nullable=True)
    version = Column(Integer, nullable=False, default=1)  # Versión del grafo
    
    # Relationships
    strategy_events = relationship("StrategyEvent", back_populates="strategy", cascade="all, delete-orphan")
    execution_intents = relationship("ExecutionIntent", back_populates="strategy", cascade="all, delete-orphan")
    strategy_metrics = relationship("StrategyMetric", back_populates="strategy", cascade="all, delete-orphan")
    graph_executions = relationship("GraphExecution", back_populates="strategy", cascade="all, delete-orphan")
```

**Estructura del Decision Graph (JSON):**
```json
{
  "entry_node": "observe",
  "nodes": {
    "observe": {
      "type": "collect_state",
      "config": {
        "sources": ["market_state", "event_state", "external_data"]
      },
      "next": "evaluate"
    },
    "evaluate": {
      "type": "edge_and_risk_check",
      "config": {
        "conditions": [
          {"field": "event_state.state", "operator": "==", "value": "FINISHED_CONFIRMED"},
          {"field": "market_state.last_price", "operator": ">=", "value": 0.97},
          {"field": "risk_state.exposure", "operator": "<", "value": "max_exposure"}
        ],
        "logic": "AND"
      },
      "on_true": "calculate_size",
      "on_false": "idle"
    },
    "calculate_size": {
      "type": "calculate_order_size",
      "config": {
        "method": "fixed_range",
        "min": 100,
        "max": 5000
      },
      "next": "emit_intent"
    },
    "emit_intent": {
      "type": "emit_execution_intent",
      "config": {
        "side": "BUY",
        "outcome": "YES"
      },
      "next": "idle"
    },
    "idle": {
      "type": "noop"
    }
  }
}
```

**Estructura de Support Graph (JSON):**
```json
{
  "name": "confirm_event_result",
  "trigger": {
    "type": "event_state_change",
    "condition": {"field": "event.state", "operator": "==", "value": "FINISHED"}
  },
  "entry_node": "fetch_external_data",
  "nodes": {
    "fetch_external_data": {
      "type": "fetch_external_source",
      "config": {
        "source_id": "uuid-of-external-source",
        "endpoint": "/api/result",
        "params": {"event_id": "{{event.id}}"}
      },
      "next": "validate_result"
    },
    "validate_result": {
      "type": "validate_with_ai",
      "config": {
        "model": "gpt-4",
        "prompt_template": "Validate if event {{event.id}} result is confirmed..."
      },
      "on_success": "update_cache",
      "on_failure": "log_error"
    },
    "update_cache": {
      "type": "update_state_cache",
      "config": {
        "key": "event.{{event.id}}.external_confirmation",
        "value": "{{validation_result}}"
      },
      "next": "end"
    },
    "log_error": {
      "type": "log",
      "next": "end"
    },
    "end": {
      "type": "noop"
    }
  }
}
```

#### `models/graph_node_definition.py` - Definiciones de nodos disponibles

```python
class GraphNodeDefinition(BaseModel):
    __tablename__ = "graph_node_definitions"
    
    # Identificación
    node_type = Column(String, unique=True, nullable=False, index=True)  # "collect_state", "edge_and_risk_check", etc.
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Categoría
    category = Column(String, nullable=False, index=True)  # "state", "condition", "calculation", "action", "io"
    path_type = Column(String, nullable=False)  # "hot" (Decision Graph) o "cold" (Support Graph)
    
    # Schema de configuración (JSON Schema)
    config_schema = Column(JSONB, nullable=False)  # JSON Schema para validar config del nodo
    
    # Metadata
    is_builtin = Column(Boolean, nullable=False, default=True)
    version = Column(String, nullable=True)
    icon = Column(String, nullable=True)  # Para UI
```

#### `models/graph_execution.py` - Trazabilidad de ejecuciones de grafos

```python
class GraphExecution(BaseModel):
    __tablename__ = "graph_executions"
    
    # Relación con estrategia
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False, index=True)
    
    # Tipo de grafo ejecutado
    graph_type = Column(String, nullable=False, index=True)  # "decision" o "support"
    graph_name = Column(String, nullable=True)  # Nombre del grafo (para support graphs)
    
    # Relación con evento (si aplica)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True, index=True)
    
    # Estado de ejecución
    status = Column(String, nullable=False, index=True)  # "started", "completed", "failed", "timeout"
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)  # Duración en milisegundos
    
    # Resultado
    result = Column(JSONB, nullable=True)  # Resultado de la ejecución
    error_message = Column(Text, nullable=True)
    
    # Trazabilidad
    trace_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    node_executions = Column(JSONB, nullable=True)  # Array de ejecuciones de nodos individuales
    
    # Relationships
    strategy = relationship("Strategy", back_populates="graph_executions")
    event = relationship("Event")
```

#### `models/state_cache.py` - Cache de estado para grafos

```python
class StateCache(BaseModel):
    __tablename__ = "state_cache"
    
    # Clave del estado (ej: "event.{event_id}.market_state", "event.{event_id}.external_confirmation")
    cache_key = Column(String, nullable=False, unique=True, index=True)
    
    # Valor del estado (JSONB)
    cache_value = Column(JSONB, nullable=False)
    
    # Metadata
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=True, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True, index=True)
    
    # TTL
    expires_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime, nullable=True, onupdate=func.now(), index=True)
    
    # Relationships
    strategy = relationship("Strategy")
    event = relationship("Event")
```

#### `models/external_data_source.py` - Fuentes de datos externas (sin cambios)

```python
class ExternalDataSource(BaseModel):
    __tablename__ = "external_data_sources"
    
    name = Column(String, nullable=False)
    connector_type = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    connector_config = Column(JSONB, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(String, nullable=True)
    created_by = Column(String, ForeignKey("neon_auth.users_sync.id"), nullable=True)
    
    # Relationships
    strategy_sources = relationship("StrategyExternalDataSource", back_populates="external_data_source")
```

#### `models/strategy_event.py` - Eventos asignados a estrategias (sin cambios)

```python
class StrategyEvent(BaseModel):
    __tablename__ = "strategy_events"
    
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    observation_started_at = Column(DateTime, nullable=True)
    observation_ended_at = Column(DateTime, nullable=True)
    event_config = Column(JSONB, nullable=True)
    
    # Relationships
    strategy = relationship("Strategy", back_populates="strategy_events")
    event = relationship("Event")
    
    __table_args__ = (
        UniqueConstraint('strategy_id', 'event_id', name='uq_strategy_event'),
    )
```

#### `models/execution_intent.py` - Intenciones de ejecución (sin cambios significativos)

```python
class ExecutionIntent(BaseModel):
    __tablename__ = "execution_intents"
    
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    side = Column(String, nullable=False)
    outcome = Column(String, nullable=False)
    target_price = Column(Numeric(18, 8), nullable=False)
    size = Column(Numeric(18, 8), nullable=False)
    size_usdc = Column(Numeric(18, 8), nullable=False)
    reason = Column(String, nullable=False)
    context = Column(JSONB, nullable=True)  # Contexto completo de la decisión
    
    status = Column(String, nullable=False, default="PENDING", index=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)
    
    trace_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    decision_trace_id = Column(UUID(as_uuid=True), ForeignKey("decision_traces.id"), nullable=True)
    graph_execution_id = Column(UUID(as_uuid=True), ForeignKey("graph_executions.id"), nullable=True)
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    
    # Relationships
    strategy = relationship("Strategy", back_populates="execution_intents")
    event = relationship("Event")
    decision_trace = relationship("DecisionTrace")
    graph_execution = relationship("GraphExecution")
    order = relationship("Order")
```

#### `models/strategy_metric.py` - Métricas (sin cambios)

```python
class StrategyMetric(BaseModel):
    __tablename__ = "strategy_metrics"
    
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False, index=True)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    total_intents = Column(Integer, nullable=False, default=0)
    approved_intents = Column(Integer, nullable=False, default=0)
    executed_intents = Column(Integer, nullable=False, default=0)
    rejected_intents = Column(Integer, nullable=False, default=0)
    total_volume_usdc = Column(Numeric(18, 8), nullable=False, default=0)
    total_pnl_usdc = Column(Numeric(18, 8), nullable=True)
    total_exposure_usdc = Column(Numeric(18, 8), nullable=False, default=0)
    win_rate = Column(Numeric(5, 4), nullable=True)
    avg_entry_price = Column(Numeric(18, 8), nullable=True)
    avg_exit_price = Column(Numeric(18, 8), nullable=True)
    calculated_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    strategy = relationship("Strategy", back_populates="strategy_metrics")
```

### 1.2. Migración Alembic

**Archivo:** `backend/alembic/versions/010_create_strategies_graph_system.py`

```python
"""create strategies graph system

Revision ID: 010_create_strategies_graphs
Revises: 2025_12_14_2250
Create Date: 2025-01-XX XX:XX:XX
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

def upgrade():
    # Graph node definitions
    op.create_table(
        'graph_node_definitions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('node_type', sa.String, nullable=False, unique=True, index=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String, nullable=False, index=True),
        sa.Column('path_type', sa.String, nullable=False),  # "hot" o "cold"
        sa.Column('config_schema', JSONB, nullable=False),
        sa.Column('is_builtin', sa.Boolean, nullable=False, default=True),
        sa.Column('version', sa.String, nullable=True),
        sa.Column('icon', sa.String, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=True, onupdate=sa.func.now()),
    )
    
    # Strategies
    op.create_table(
        'strategies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=False, index=True),
        sa.Column('enabled_at', sa.DateTime, nullable=True),
        sa.Column('disabled_at', sa.DateTime, nullable=True),
        sa.Column('decision_graph', JSONB, nullable=False),
        sa.Column('support_graphs', JSONB, nullable=False, default=[]),
        sa.Column('control_loop_config', JSONB, nullable=False, default={}),
        sa.Column('risk_config', JSONB, nullable=False, default={}),
        sa.Column('created_by', sa.String, ForeignKey("neon_auth.users_sync.id"), nullable=True),
        sa.Column('tags', JSONB, nullable=True),
        sa.Column('version', sa.Integer, nullable=False, default=1),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=True, onupdate=sa.func.now()),
    )
    
    # State cache
    op.create_table(
        'state_cache',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('cache_key', sa.String, nullable=False, unique=True, index=True),
        sa.Column('cache_value', JSONB, nullable=False),
        sa.Column('strategy_id', UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=True, index=True),
        sa.Column('event_id', UUID(as_uuid=True), ForeignKey("events.id"), nullable=True, index=True),
        sa.Column('expires_at', sa.DateTime, nullable=True, index=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime, nullable=True, onupdate=sa.func.now(), index=True),
    )
    
    # Graph executions
    op.create_table(
        'graph_executions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('strategy_id', UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False, index=True),
        sa.Column('graph_type', sa.String, nullable=False, index=True),
        sa.Column('graph_name', sa.String, nullable=True),
        sa.Column('event_id', UUID(as_uuid=True), ForeignKey("events.id"), nullable=True, index=True),
        sa.Column('status', sa.String, nullable=False, index=True),
        sa.Column('started_at', sa.DateTime, nullable=False, index=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('result', JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('trace_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('node_executions', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=True, onupdate=sa.func.now()),
    )
    
    # Strategy events
    op.create_table(
        'strategy_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('strategy_id', UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False, index=True),
        sa.Column('event_id', UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True),
        sa.Column('observation_started_at', sa.DateTime, nullable=True),
        sa.Column('observation_ended_at', sa.DateTime, nullable=True),
        sa.Column('event_config', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=True, onupdate=sa.func.now()),
        sa.UniqueConstraint('strategy_id', 'event_id', name='uq_strategy_event'),
    )
    
    # Execution intents
    op.create_table(
        'execution_intents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('strategy_id', UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False, index=True),
        sa.Column('event_id', UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True),
        sa.Column('side', sa.String, nullable=False),
        sa.Column('outcome', sa.String, nullable=False),
        sa.Column('target_price', sa.Numeric(18, 8), nullable=False),
        sa.Column('size', sa.Numeric(18, 8), nullable=False),
        sa.Column('size_usdc', sa.Numeric(18, 8), nullable=False),
        sa.Column('reason', sa.String, nullable=False),
        sa.Column('context', JSONB, nullable=True),
        sa.Column('status', sa.String, nullable=False, default="PENDING", index=True),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('rejected_at', sa.DateTime, nullable=True),
        sa.Column('rejection_reason', sa.String, nullable=True),
        sa.Column('trace_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('decision_trace_id', UUID(as_uuid=True), ForeignKey("decision_traces.id"), nullable=True),
        sa.Column('graph_execution_id', UUID(as_uuid=True), ForeignKey("graph_executions.id"), nullable=True),
        sa.Column('order_id', UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=True, onupdate=sa.func.now()),
    )
    
    # Strategy metrics
    op.create_table(
        'strategy_metrics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('strategy_id', UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False, index=True),
        sa.Column('period_start', sa.DateTime, nullable=False, index=True),
        sa.Column('period_end', sa.DateTime, nullable=False, index=True),
        sa.Column('total_intents', sa.Integer, nullable=False, default=0),
        sa.Column('approved_intents', sa.Integer, nullable=False, default=0),
        sa.Column('executed_intents', sa.Integer, nullable=False, default=0),
        sa.Column('rejected_intents', sa.Integer, nullable=False, default=0),
        sa.Column('total_volume_usdc', sa.Numeric(18, 8), nullable=False, default=0),
        sa.Column('total_pnl_usdc', sa.Numeric(18, 8), nullable=True),
        sa.Column('total_exposure_usdc', sa.Numeric(18, 8), nullable=False, default=0),
        sa.Column('win_rate', sa.Numeric(5, 4), nullable=True),
        sa.Column('avg_entry_price', sa.Numeric(18, 8), nullable=True),
        sa.Column('avg_exit_price', sa.Numeric(18, 8), nullable=True),
        sa.Column('calculated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=True, onupdate=sa.func.now()),
    )
    
    # External data sources (si no existe)
    op.create_table(
        'external_data_sources',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('connector_type', sa.String, nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('connector_config', JSONB, nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True, index=True),
        sa.Column('last_health_check', sa.DateTime, nullable=True),
        sa.Column('health_status', sa.String, nullable=True),
        sa.Column('created_by', sa.String, ForeignKey("neon_auth.users_sync.id"), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=True, onupdate=sa.func.now()),
    )
    
    # Índices adicionales
    op.create_index('idx_strategies_active', 'strategies', ['is_active'])
    op.create_index('idx_graph_executions_strategy_event', 'graph_executions', ['strategy_id', 'event_id'])
    op.create_index('idx_state_cache_strategy_event', 'state_cache', ['strategy_id', 'event_id'])
    op.create_index('idx_execution_intents_strategy_status', 'execution_intents', ['strategy_id', 'status'])

def downgrade():
    op.drop_table('strategy_metrics')
    op.drop_table('execution_intents')
    op.drop_table('strategy_events')
    op.drop_table('graph_executions')
    op.drop_table('state_cache')
    op.drop_table('strategies')
    op.drop_table('graph_node_definitions')
    op.drop_table('external_data_sources')
```

### 1.3. Seed de Nodos Predefinidos

**Archivo:** `backend/scripts/seed_graph_node_definitions.py`

Crear script para seedear nodos predefinidos:
- `collect_state` - Recopila estado del State Cache
- `edge_and_risk_check` - Evalúa condiciones y riesgo
- `calculate_order_size` - Calcula tamaño de orden
- `emit_execution_intent` - Emite intent de ejecución
- `fetch_external_source` - Obtiene datos de fuente externa (solo Support Graph)
- `validate_with_ai` - Valida con IA (solo Support Graph)
- `update_state_cache` - Actualiza State Cache (solo Support Graph)
- etc.

---

## FASE 2: Backend - Control Loop y Runtime de Grafos

### 2.1. Control Loop (Infraestructura Fija)

#### `core/strategy_engine/control_loop.py`

```python
class ControlLoop:
    """
    Control Loop - Infraestructura fija que mantiene las estrategias vivas.
    
    NO es editable por el usuario.
    NO contiene lógica de trading.
    Solo orquesta el ciclo de vida de las estrategias.
    """
    
    def __init__(self, strategy_engine: 'StrategyEngine'):
        self.strategy_engine = strategy_engine
        self.active_strategies: Dict[UUID, Strategy] = {}
        self.running = False
    
    async def start(self, db: Session):
        """Inicia el control loop."""
        self.running = True
        await self.load_active_strategies(db)
        
        while self.running:
            try:
                await self.tick(db)
                await asyncio.sleep(0.1)  # 100ms entre ticks
            except Exception as e:
                logger.error(f"Error in control loop: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def load_active_strategies(self, db: Session):
        """Carga estrategias activas desde DB."""
        strategies = db.query(Strategy).filter(Strategy.is_active == True).all()
        self.active_strategies = {s.id: s for s in strategies}
        logger.info(f"Loaded {len(self.active_strategies)} active strategies")
    
    async def tick(self, db: Session):
        """
        Tick principal del control loop.
        
        Para cada estrategia activa:
        1. Obtiene eventos asignados
        2. Para cada evento, verifica triggers
        3. Si trigger activado, ejecuta Decision Graph
        4. Ejecuta Support Graphs según sus triggers
        """
        for strategy_id, strategy in self.active_strategies.items():
            # Obtener eventos asignados a esta estrategia
            strategy_events = db.query(StrategyEvent).filter(
                StrategyEvent.strategy_id == strategy_id
            ).all()
            
            for strategy_event in strategy_events:
                event = strategy_event.event
                
                # Verificar si debemos observar este evento
                if not self._should_observe(strategy, event, strategy_event):
                    continue
                
                # Verificar triggers del Control Loop
                if self._check_triggers(strategy, event):
                    # Ejecutar Decision Graph (hot path)
                    await self.strategy_engine.execute_decision_graph(
                        strategy, event, db
                    )
                
                # Ejecutar Support Graphs según sus triggers (cold path, async)
                await self._execute_support_graphs(strategy, event, db)
    
    def _should_observe(self, strategy: Strategy, event: Event, strategy_event: StrategyEvent) -> bool:
        """Verifica si debemos observar este evento."""
        # Verificar timing (start_time, end_time)
        now = datetime.utcnow()
        
        if strategy_event.observation_started_at and now < strategy_event.observation_started_at:
            return False
        
        if strategy_event.observation_ended_at and now > strategy_event.observation_ended_at:
            return False
        
        # Verificar estado del evento
        if event.state not in ["UPCOMING", "ACTIVE"]:
            return False
        
        return True
    
    def _check_triggers(self, strategy: Strategy, event: Event) -> bool:
        """Verifica si se debe ejecutar el Decision Graph."""
        config = strategy.control_loop_config
        
        # Trigger por intervalo de tiempo
        if "interval_seconds" in config:
            # Implementar lógica de intervalo
            pass
        
        # Trigger por cambio de estado
        if "trigger_on_state_change" in config:
            # Implementar lógica de cambio de estado
            pass
        
        # Por defecto, ejecutar cada tick
        return True
    
    async def _execute_support_graphs(self, strategy: Strategy, event: Event, db: Session):
        """Ejecuta Support Graphs según sus triggers (async, no bloquea)."""
        support_graphs = strategy.support_graphs or []
        
        for support_graph in support_graphs:
            trigger = support_graph.get("trigger", {})
            
            if self._check_support_graph_trigger(trigger, event):
                # Ejecutar en background (no bloquea)
                asyncio.create_task(
                    self.strategy_engine.execute_support_graph(
                        strategy, support_graph, event, db
                    )
                )
    
    def _check_support_graph_trigger(self, trigger: Dict[str, Any], event: Event) -> bool:
        """Verifica si un Support Graph debe ejecutarse."""
        trigger_type = trigger.get("type")
        
        if trigger_type == "event_state_change":
            condition = trigger.get("condition", {})
            # Verificar condición
            return self._evaluate_condition(condition, event)
        
        elif trigger_type == "timer":
            # Implementar lógica de timer
            pass
        
        elif trigger_type == "external":
            # Implementar lógica de trigger externo
            pass
        
        return False
```

### 2.2. Runtime del Decision Graph (Hot Path)

#### `core/strategy_engine/graph_runtime.py`

```python
class GraphRuntime:
    """
    Runtime para ejecutar grafos (Decision Graph y Support Graphs).
    
    El Decision Graph debe ejecutarse en < 50μs.
    Solo lee State Cache, nunca llama APIs.
    """
    
    def __init__(self, state_cache_service: 'StateCacheService'):
        self.state_cache = state_cache_service
        self.node_registry: Dict[str, Type[GraphNode]] = {}
        self._register_builtin_nodes()
    
    def _register_builtin_nodes(self):
        """Registra nodos predefinidos."""
        self.node_registry["collect_state"] = CollectStateNode
        self.node_registry["edge_and_risk_check"] = EdgeAndRiskCheckNode
        self.node_registry["calculate_order_size"] = CalculateOrderSizeNode
        self.node_registry["emit_execution_intent"] = EmitExecutionIntentNode
        self.node_registry["noop"] = NoOpNode
        # ... más nodos
    
    async def execute_graph(
        self,
        graph: Dict[str, Any],
        context: GraphExecutionContext,
        path_type: str = "hot"  # "hot" o "cold"
    ) -> GraphExecutionResult:
        """
        Ejecuta un grafo.
        
        Args:
            graph: Definición del grafo (JSON)
            context: Contexto de ejecución (strategy, event, etc.)
            path_type: "hot" (Decision Graph) o "cold" (Support Graph)
        
        Returns:
            GraphExecutionResult con intents generados (si Decision Graph)
        """
        entry_node_id = graph.get("entry_node")
        nodes = graph.get("nodes", {})
        
        if entry_node_id not in nodes:
            raise ValueError(f"Entry node '{entry_node_id}' not found in graph")
        
        # Ejecutar grafo de forma secuencial
        current_node_id = entry_node_id
        execution_trace = []
        intents = []
        
        start_time = time.perf_counter()
        
        while current_node_id:
            node_def = nodes.get(current_node_id)
            if not node_def:
                break
            
            node_type = node_def.get("type")
            node_config = node_def.get("config", {})
            
            # Obtener instancia del nodo
            node_class = self.node_registry.get(node_type)
            if not node_class:
                raise ValueError(f"Unknown node type: {node_type}")
            
            node = node_class(node_config, context)
            
            # Ejecutar nodo
            node_start = time.perf_counter()
            result = await node.execute()
            node_duration = (time.perf_counter() - node_start) * 1000  # ms
            
            execution_trace.append({
                "node_id": current_node_id,
                "node_type": node_type,
                "duration_ms": node_duration,
                "result": result.to_dict() if hasattr(result, 'to_dict') else str(result)
            })
            
            # Si el nodo emitió un intent, agregarlo
            if isinstance(result, ExecutionIntentResult):
                intents.append(result.intent)
            
            # Determinar siguiente nodo
            current_node_id = self._get_next_node(node_def, result)
        
        total_duration = (time.perf_counter() - start_time) * 1000  # ms
        
        return GraphExecutionResult(
            intents=intents,
            execution_trace=execution_trace,
            duration_ms=total_duration,
            success=True
        )
    
    def _get_next_node(self, node_def: Dict[str, Any], result: NodeResult) -> Optional[str]:
        """Determina el siguiente nodo basado en el resultado."""
        # Si hay un "next" directo
        if "next" in node_def:
            return node_def["next"]
        
        # Si hay condiciones (on_true, on_false, on_success, on_failure)
        if isinstance(result, ConditionalResult):
            if result.condition and "on_true" in node_def:
                return node_def["on_true"]
            elif not result.condition and "on_false" in node_def:
                return node_def["on_false"]
        
        if isinstance(result, SuccessResult):
            if "on_success" in node_def:
                return node_def["on_success"]
        elif isinstance(result, FailureResult):
            if "on_failure" in node_def:
                return node_def["on_failure"]
        
        return None
```

### 2.3. Nodos del Grafo (Implementaciones)

#### `core/strategy_engine/nodes/base.py`

```python
class GraphNode(ABC):
    """Clase base para todos los nodos del grafo."""
    
    def __init__(self, config: Dict[str, Any], context: GraphExecutionContext):
        self.config = config
        self.context = context
    
    @abstractmethod
    async def execute(self) -> NodeResult:
        """Ejecuta el nodo y retorna resultado."""
        pass

class NodeResult:
    """Resultado base de un nodo."""
    pass

class ConditionalResult(NodeResult):
    """Resultado con condición booleana."""
    def __init__(self, condition: bool, data: Dict[str, Any] = None):
        self.condition = condition
        self.data = data or {}

class ExecutionIntentResult(NodeResult):
    """Resultado que contiene un Execution Intent."""
    def __init__(self, intent: ExecutionIntent):
        self.intent = intent

class SuccessResult(NodeResult):
    """Resultado de éxito."""
    pass

class FailureResult(NodeResult):
    """Resultado de fallo."""
    def __init__(self, error: str):
        self.error = error
```

#### `core/strategy_engine/nodes/collect_state.py`

```python
class CollectStateNode(GraphNode):
    """
    Nodo que recopila estado del State Cache.
    
    Solo lee, nunca escribe.
    """
    
    async def execute(self) -> NodeResult:
        sources = self.config.get("sources", [])
        collected_state = {}
        
        for source in sources:
            if source == "market_state":
                # Leer del State Cache
                cache_key = f"event.{self.context.event_id}.market_state"
                market_state = await self.context.state_cache.get(cache_key)
                collected_state["market_state"] = market_state
            
            elif source == "event_state":
                cache_key = f"event.{self.context.event_id}.event_state"
                event_state = await self.context.state_cache.get(cache_key)
                collected_state["event_state"] = event_state
            
            elif source == "external_data":
                # Leer todas las fuentes externas para este evento
                cache_key = f"event.{self.context.event_id}.external_data.*"
                external_data = await self.context.state_cache.get_many(cache_key)
                collected_state["external_data"] = external_data
            
            elif source == "risk_state":
                cache_key = f"strategy.{self.context.strategy_id}.risk_state"
                risk_state = await self.context.state_cache.get(cache_key)
                collected_state["risk_state"] = risk_state
        
        # Guardar estado recopilado en el contexto
        self.context.collected_state = collected_state
        
        return SuccessResult()
```

#### `core/strategy_engine/nodes/edge_and_risk_check.py`

```python
class EdgeAndRiskCheckNode(GraphNode):
    """
    Nodo que evalúa condiciones (edge) y riesgo.
    
    Evalúa múltiples condiciones con lógica AND/OR.
    """
    
    async def execute(self) -> ConditionalResult:
        conditions = self.config.get("conditions", [])
        logic = self.config.get("logic", "AND")  # "AND" o "OR"
        
        results = []
        
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")
            
            # Resolver valor del campo desde el estado recopilado
            field_value = self._resolve_field(field)
            
            # Evaluar condición
            condition_result = self._evaluate_condition(field_value, operator, value)
            results.append(condition_result)
        
        # Aplicar lógica
        if logic == "AND":
            final_result = all(results)
        else:  # OR
            final_result = any(results)
        
        return ConditionalResult(final_result, {"conditions": results})
    
    def _resolve_field(self, field_path: str) -> Any:
        """Resuelve un campo desde el estado recopilado."""
        # Ejemplo: "event_state.state" -> context.collected_state["event_state"]["state"]
        parts = field_path.split(".")
        value = self.context.collected_state
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        
        return value
    
    def _evaluate_condition(self, field_value: Any, operator: str, expected_value: Any) -> bool:
        """Evalúa una condición."""
        if operator == "==":
            return field_value == expected_value
        elif operator == "!=":
            return field_value != expected_value
        elif operator == ">":
            return field_value > expected_value
        elif operator == ">=":
            return field_value >= expected_value
        elif operator == "<":
            return field_value < expected_value
        elif operator == "<=":
            return field_value <= expected_value
        elif operator == "in":
            return field_value in expected_value
        elif operator == "not_in":
            return field_value not in expected_value
        else:
            raise ValueError(f"Unknown operator: {operator}")
```

#### `core/strategy_engine/nodes/emit_execution_intent.py`

```python
class EmitExecutionIntentNode(GraphNode):
    """
    Nodo que emite un Execution Intent.
    
    Este es el output del Decision Graph.
    """
    
    async def execute(self) -> ExecutionIntentResult:
        side = self.config.get("side", "BUY")
        outcome = self.config.get("outcome", "YES")
        
        # Obtener precio y tamaño del contexto (calculados por nodos anteriores)
        price = self.context.get("calculated_price")
        size = self.context.get("calculated_size")
        
        if not price or not size:
            raise ValueError("Price and size must be calculated before emitting intent")
        
        intent = ExecutionIntent(
            strategy_id=self.context.strategy_id,
            event_id=self.context.event_id,
            side=side,
            outcome=outcome,
            target_price=price,
            size=size,
            size_usdc=size * price,
            reason=self.config.get("reason", "Strategy decision"),
            context=self.context.collected_state,
            trace_id=self.context.trace_id,
            status="PENDING"
        )
        
        return ExecutionIntentResult(intent)
```

### 2.4. State Cache Service

#### `core/strategy_engine/state_cache_service.py`

```python
class StateCacheService:
    """
    Servicio para gestionar State Cache.
    
    Support Graphs escriben aquí.
    Decision Graph lee desde aquí.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._memory_cache: Dict[str, Tuple[Any, datetime]] = {}  # cache_key -> (value, expires_at)
    
    async def get(self, cache_key: str) -> Optional[Any]:
        """Obtiene un valor del cache."""
        # Primero verificar memoria
        if cache_key in self._memory_cache:
            value, expires_at = self._memory_cache[cache_key]
            if expires_at is None or datetime.utcnow() < expires_at:
                return value
            else:
                del self._memory_cache[cache_key]
        
        # Luego verificar DB
        cache_entry = self.db.query(StateCache).filter(
            StateCache.cache_key == cache_key
        ).first()
        
        if cache_entry:
            if cache_entry.expires_at is None or datetime.utcnow() < cache_entry.expires_at:
                # Actualizar memoria
                self._memory_cache[cache_key] = (cache_entry.cache_value, cache_entry.expires_at)
                return cache_entry.cache_value
        
        return None
    
    async def set(
        self,
        cache_key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        strategy_id: Optional[UUID] = None,
        event_id: Optional[UUID] = None
    ):
        """Establece un valor en el cache."""
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        
        # Actualizar memoria
        self._memory_cache[cache_key] = (value, expires_at)
        
        # Actualizar DB
        cache_entry = self.db.query(StateCache).filter(
            StateCache.cache_key == cache_key
        ).first()
        
        if cache_entry:
            cache_entry.cache_value = value
            cache_entry.expires_at = expires_at
            cache_entry.updated_at = datetime.utcnow()
        else:
            cache_entry = StateCache(
                cache_key=cache_key,
                cache_value=value,
                expires_at=expires_at,
                strategy_id=strategy_id,
                event_id=event_id
            )
            self.db.add(cache_entry)
        
        self.db.commit()
    
    async def get_many(self, pattern: str) -> Dict[str, Any]:
        """Obtiene múltiples valores usando un patrón."""
        # Implementar búsqueda por patrón
        pass
```

### 2.5. Strategy Engine (Orquestador Principal)

#### `core/strategy_engine/strategy_engine.py`

```python
class StrategyEngine:
    """
    Strategy Engine - Orquestador principal.
    
    Coordina Control Loop, Graph Runtime, State Cache.
    """
    
    def __init__(self):
        self.state_cache_service = None  # Se inicializa con DB
        self.graph_runtime = None
        self.control_loop = None
    
    def initialize(self, db: Session):
        """Inicializa el engine con una sesión de DB."""
        self.state_cache_service = StateCacheService(db)
        self.graph_runtime = GraphRuntime(self.state_cache_service)
        self.control_loop = ControlLoop(self)
    
    async def execute_decision_graph(
        self,
        strategy: Strategy,
        event: Event,
        db: Session
    ) -> List[ExecutionIntent]:
        """
        Ejecuta el Decision Graph para una estrategia y evento.
        
        Hot path - debe ser rápido.
        """
        trace_id = uuid4()
        
        # Crear contexto
        context = GraphExecutionContext(
            strategy_id=strategy.id,
            event_id=event.id,
            market_id=event.market_id,
            trace_id=trace_id,
            state_cache=self.state_cache_service
        )
        
        # Ejecutar grafo
        result = await self.graph_runtime.execute_graph(
            graph=strategy.decision_graph,
            context=context,
            path_type="hot"
        )
        
        # Guardar ejecución en DB
        execution = GraphExecution(
            strategy_id=strategy.id,
            graph_type="decision",
            event_id=event.id,
            status="completed" if result.success else "failed",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_ms=int(result.duration_ms),
            result={"intents_count": len(result.intents)},
            trace_id=trace_id,
            node_executions=result.execution_trace
        )
        db.add(execution)
        
        # Guardar intents en DB
        for intent in result.intents:
            intent.graph_execution_id = execution.id
            db.add(intent)
        
        db.commit()
        
        return result.intents
    
    async def execute_support_graph(
        self,
        strategy: Strategy,
        support_graph: Dict[str, Any],
        event: Event,
        db: Session
    ):
        """
        Ejecuta un Support Graph.
        
        Cold path - puede tardar, no bloquea.
        """
        trace_id = uuid4()
        graph_name = support_graph.get("name", "unnamed")
        
        context = GraphExecutionContext(
            strategy_id=strategy.id,
            event_id=event.id,
            market_id=event.market_id,
            trace_id=trace_id,
            state_cache=self.state_cache_service
        )
        
        try:
            result = await self.graph_runtime.execute_graph(
                graph=support_graph,
                context=context,
                path_type="cold"
            )
            
            execution = GraphExecution(
                strategy_id=strategy.id,
                graph_type="support",
                graph_name=graph_name,
                event_id=event.id,
                status="completed" if result.success else "failed",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_ms=int(result.duration_ms),
                result=result.to_dict(),
                trace_id=trace_id,
                node_executions=result.execution_trace
            )
        except Exception as e:
            execution = GraphExecution(
                strategy_id=strategy.id,
                graph_type="support",
                graph_name=graph_name,
                event_id=event.id,
                status="failed",
                started_at=datetime.utcnow(),
                error_message=str(e),
                trace_id=trace_id
            )
        
        db.add(execution)
        db.commit()
```

---

## FASE 3: Backend - APIs REST

### 3.1. API de Estrategias

#### `api/strategies.py`

Similar a la versión anterior, pero adaptado para grafos:

```python
@router.post("")
async def create_strategy(
    strategy_data: StrategyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Crea una nueva estrategia con Decision Graph."""
    # Validar Decision Graph
    validate_decision_graph(strategy_data.decision_graph)
    
    # Validar Support Graphs
    for support_graph in strategy_data.support_graphs or []:
        validate_support_graph(support_graph)
    
    strategy = Strategy(
        name=strategy_data.name,
        description=strategy_data.description,
        decision_graph=strategy_data.decision_graph,
        support_graphs=strategy_data.support_graphs or [],
        control_loop_config=strategy_data.control_loop_config or {},
        risk_config=strategy_data.risk_config or {},
        created_by=current_user.id,
        tags=strategy_data.tags,
        is_active=False
    )
    db.add(strategy)
    db.commit()
    return strategy_to_dict(strategy)

@router.get("/{strategy_id}/graph")
async def get_strategy_graph(
    strategy_id: UUID,
    graph_type: str = Query("decision"),  # "decision" o "support"
    graph_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene el grafo de una estrategia."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(404, "Strategy not found")
    
    if graph_type == "decision":
        return {"graph": strategy.decision_graph}
    elif graph_type == "support":
        if graph_name:
            support_graph = next(
                (g for g in strategy.support_graphs if g.get("name") == graph_name),
                None
            )
            if not support_graph:
                raise HTTPException(404, "Support graph not found")
            return {"graph": support_graph}
        else:
            return {"graphs": strategy.support_graphs}
    else:
        raise HTTPException(400, "Invalid graph_type")

@router.put("/{strategy_id}/graph")
async def update_strategy_graph(
    strategy_id: UUID,
    graph_type: str = Query("decision"),
    graph_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Actualiza el grafo de una estrategia."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(404, "Strategy not found")
    
    if strategy.is_active:
        raise HTTPException(400, "Cannot update graph of active strategy")
    
    # Validar grafo
    if graph_type == "decision":
        validate_decision_graph(graph_data)
        strategy.decision_graph = graph_data
    elif graph_type == "support":
        validate_support_graph(graph_data)
        # Actualizar o agregar support graph
        # ... lógica de actualización
    
    strategy.version += 1
    db.commit()
    return strategy_to_dict(strategy)
```

### 3.2. API de Nodos de Grafo

#### `api/graph_nodes.py`

```python
router = APIRouter(prefix="/graph-nodes", tags=["graph-nodes"])

@router.get("")
async def list_graph_nodes(
    category: Optional[str] = Query(None),
    path_type: Optional[str] = Query(None),  # "hot" o "cold"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todos los nodos de grafo disponibles."""
    query = db.query(GraphNodeDefinition)
    
    if category:
        query = query.filter(GraphNodeDefinition.category == category)
    if path_type:
        query = query.filter(GraphNodeDefinition.path_type == path_type)
    
    nodes = query.all()
    return [node_to_dict(n) for n in nodes]

@router.get("/{node_type}")
async def get_graph_node(
    node_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene la definición de un nodo específico."""
    node = db.query(GraphNodeDefinition).filter(
        GraphNodeDefinition.node_type == node_type
    ).first()
    
    if not node:
        raise HTTPException(404, "Node type not found")
    
    return node_to_dict(node, include_schema=True)
```

### 3.3. API de State Cache

#### `api/state_cache.py`

```python
router = APIRouter(prefix="/state-cache", tags=["state-cache"])

@router.get("")
async def get_state_cache(
    strategy_id: Optional[UUID] = Query(None),
    event_id: Optional[UUID] = Query(None),
    pattern: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene valores del State Cache."""
    query = db.query(StateCache)
    
    if strategy_id:
        query = query.filter(StateCache.strategy_id == strategy_id)
    if event_id:
        query = query.filter(StateCache.event_id == event_id)
    if pattern:
        # Implementar búsqueda por patrón
        pass
    
    cache_entries = query.all()
    return [cache_entry_to_dict(e) for e in cache_entries]
```

---

## FASE 4: Frontend - Constructor Visual de Grafos

### 4.1. Biblioteca de Visualización de Grafos

Usar una biblioteca como:
- **React Flow** (recomendado)
- **Cytoscape.js**
- **D3.js**

### 4.2. Componente Principal del Constructor

#### `frontend/components/GraphBuilder/GraphBuilder.tsx`

```typescript
interface GraphBuilderProps {
  graph: DecisionGraph | SupportGraph;
  onGraphChange: (graph: DecisionGraph | SupportGraph) => void;
  pathType: 'hot' | 'cold';
  readOnly?: boolean;
}

export function GraphBuilder({ graph, onGraphChange, pathType, readOnly }: GraphBuilderProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  
  // Cargar definiciones de nodos disponibles
  const { data: nodeDefinitions } = useQuery(['graph-nodes', pathType], () =>
    api.get(`/graph-nodes?path_type=${pathType}`)
  );
  
  // Convertir grafo JSON a nodos/edges de React Flow
  useEffect(() => {
    const { nodes: graphNodes, edges: graphEdges } = graphToReactFlow(graph);
    setNodes(graphNodes);
    setEdges(graphEdges);
  }, [graph]);
  
  // Convertir nodos/edges de React Flow a grafo JSON
  const handleGraphChange = (newNodes: Node[], newEdges: Edge[]) => {
    const newGraph = reactFlowToGraph(newNodes, newEdges, graph.entry_node);
    onGraphChange(newGraph);
  };
  
  return (
    <div className="graph-builder">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onNodeClick={setSelectedNode}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
      >
        <Controls />
        <MiniMap />
        <Background />
      </ReactFlow>
      
      {selectedNode && (
        <NodeConfigPanel
          node={selectedNode}
          nodeDefinition={nodeDefinitions?.find(d => d.node_type === selectedNode.data.type)}
          onConfigChange={(config) => updateNodeConfig(selectedNode.id, config)}
        />
      )}
      
      <NodePalette
        nodeDefinitions={nodeDefinitions}
        onAddNode={(nodeType) => addNodeToGraph(nodeType)}
      />
    </div>
  );
}
```

### 4.3. Página de Creación/Edición de Estrategia

#### `frontend/app/strategies/create/page.tsx`

**Flujo:**
1. **Información Básica**: Nombre, descripción, tags
2. **Decision Graph**: Constructor visual del grafo principal
3. **Support Graphs**: Agregar/editar grafos auxiliares
4. **Control Loop Config**: Configuración de triggers e intervalos
5. **Risk Config**: Límites de riesgo
6. **Eventos**: Seleccionar eventos a observar
7. **Revisión**: Validar y crear

---

## FASE 5: Frontend - Visualización y Métricas

Similar a la versión anterior, pero agregando:
- Visualización de ejecuciones de grafos
- Timeline de ejecuciones de nodos
- Métricas de performance de grafos (latencia por nodo)

---

## FASE 6: Integración con Sistema Existente

### 6.1. Modificar Main Loop

```python
# En main_loop()
strategy_engine = StrategyEngine()
strategy_engine.initialize(db)
await strategy_engine.control_loop.start(db)

# El Control Loop corre en paralelo con el resto del sistema
```

### 6.2. Integrar con Risk Engine

Los Execution Intents generados por el Decision Graph pasan por Risk Engine antes de ejecución.

### 6.3. Support Graphs alimentan State Cache

Los Support Graphs actualizan State Cache, que es leído por el Decision Graph.

---

## Checklist de Validación

- [ ] Strategy es la entidad raíz
- [ ] Event es la unidad de ejecución
- [ ] Decision Graph es stateless y rápido (< 50μs)
- [ ] Support Graphs son asíncronos y no bloquean
- [ ] Decision Graph solo lee State Cache, nunca llama APIs
- [ ] No hay nombres de fuentes externas hardcodeados
- [ ] Los grafos son declarativos (JSON)
- [ ] El frontend permite construir grafos visualmente
- [ ] Las estrategias pueden activarse/desactivarse
- [ ] Se pueden ver métricas y comparar estrategias

---

## Notas Finales

1. **Control Loop es infraestructura fija** - No editable por usuario
2. **Decision Graph es hot path** - Debe ser ultra-rápido
3. **Support Graphs son cold path** - Pueden tardar, usar IA, etc.
4. **State Cache es la interfaz** - Support Graphs escriben, Decision Graph lee
5. **IA solo para generar/validar grafos** - Nunca en hot path
6. **Todo es declarativo** - JSON, no código hardcodeado
