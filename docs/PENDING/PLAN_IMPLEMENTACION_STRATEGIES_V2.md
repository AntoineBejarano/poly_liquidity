# Plan de Implementación V2 - Sistema de Estrategias Basado en Grafos

**Basado en**: `BACKEND_ARCHITECTURE_STRATEGIES.md`  
**Fecha**: 2025-12-20  
**Versión**: 2.0

---

## 🎯 Objetivo

Implementar el sistema completo de estrategias basado en grafos con:
- ✅ Execution Plans (inmutables)
- ✅ Execution Graphs (multi-leg, reintentos, compensación)
- ✅ Strategy Triggers (watchers explícitos)
- ✅ Operational Configuration & Invariants
- ✅ Reutilizando lo que ya existe

---

## 📊 Estado Actual (Qué Ya Existe)

### ✅ **Ya Implementado** (Reutilizar)

1. **Modelos Base**:
   - ✅ `Strategy` (`backend/app/models/strategy.py`)
   - ✅ `GraphNodeDefinition` (`backend/app/models/graph_node_definition.py`)
   - ✅ `GraphExecution` (`backend/app/models/graph_execution.py`)
   - ✅ `ExecutionIntent` (`backend/app/models/execution_intent.py`)
   - ✅ `StrategyEvent` (asignación eventos)

2. **Core Engine**:
   - ✅ `StrategyEngine` (`backend/app/core/strategy_engine/strategy_engine.py`)
   - ✅ `ControlLoop` (`backend/app/core/strategy_engine/control_loop.py`)
   - ✅ `GraphRuntime` (`backend/app/core/strategy_engine/graph_runtime.py`)
   - ✅ `StateCacheService` (`backend/app/core/strategy_engine/state_cache_service.py`)

3. **Nodos Básicos**:
   - ✅ `collect_state`
   - ✅ `edge_and_risk_check`
   - ✅ `calculate_order_size`
   - ✅ `emit_execution_intent` (⚠️ **DEPRECAR** - usar `build_plan` + `emit_plan_intent`)
   - ✅ `noop`
   - ✅ `fetch_external_source`
   - ✅ `update_state_cache`
   - ✅ `log`

4. **APIs**:
   - ✅ `/api/strategies` (básico)
   - ✅ `/api/graph-nodes`

### ❌ **Falta Implementar** (Nuevo)

1. **Execution Plans**:
   - ❌ Modelo `ExecutionPlan` (DB)
   - ❌ Modelo `PlanLeg` (JSONB en ExecutionPlan)
   - ❌ Nodo `build_plan`
   - ❌ Nodo `emit_plan_intent`

2. **Execution Graphs**:
   - ❌ Campo `execution_graph` en `Strategy`
   - ❌ Nodo `execution_coordinator`
   - ❌ Nodo `retry_leg`
   - ❌ Nodo `compensate_plan`
   - ❌ Nodo `derive_plan` (follow-up plans)
   - ❌ Método `execute_execution_graph()` en `StrategyEngine`

3. **Strategy Triggers**:
   - ❌ Campo `triggers` en `Strategy`
   - ❌ Evaluación de triggers en `ControlLoop`
   - ❌ Tipos de triggers: `near_end`, `edge_detected`, `state_change`, `timer`

4. **Operational Configuration**:
   - ❌ `risk_config` a nivel `ExecutionPlan`
   - ❌ Invariantes verificadas en runtime
   - ❌ Observability config
   - ❌ Versioning rules

5. **Refactorizaciones**:
   - ⚠️ Cambiar `calculate_order_size` para que retorne datos (no intents)
   - ⚠️ Deprecar `emit_execution_intent` en Decision Graph
   - ⚠️ Actualizar `ControlLoop` para evaluar triggers
   - ⚠️ Actualizar `StrategyEngine` para manejar Execution Plans

---

## 🗺️ Plan de Implementación por Fases

### **FASE 1: Execution Plans - Modelo y Base de Datos** (2-3 días)

**Objetivo**: Crear el modelo de ExecutionPlan en DB y estructura base.

#### 1.1. Modelo ExecutionPlan

- [ ] Crear `backend/app/models/execution_plan.py`:
  ```python
  class ExecutionPlan(BaseModel):
      __tablename__ = "execution_plans"
      
      strategy_id = Column(UUID, ForeignKey("strategies.id"), nullable=False, index=True)
      event_id = Column(UUID, ForeignKey("events.id"), nullable=False, index=True)
      
      # Plan inmutable (JSONB)
      legs = Column(JSONB, nullable=False)  # List[PlanLeg]
      ttl_ms = Column(Integer, nullable=False)
      
      # Estado
      status = Column(String, nullable=False, index=True)  # PLAN_BUILT | ABORTED | EXECUTING | COMPLETED | FAILED
      
      # Risk config
      risk_config = Column(JSONB, nullable=False, default={})
      
      # Trazabilidad
      trace_id = Column(UUID, nullable=True, index=True)
      decision_graph_execution_id = Column(UUID, ForeignKey("graph_executions.id"), nullable=True)
      execution_graph_execution_id = Column(UUID, ForeignKey("graph_executions.id"), nullable=True)
      
      # Timestamps
      created_at = Column(DateTime, nullable=False, server_default=func.now())
      expires_at = Column(DateTime, nullable=True)  # Calculado: created_at + ttl_ms
      # IMPORTANTE: expires_at es INMUTABLE. No se recalcula, no se actualiza, no se extiende.
      # TTL es parte de la inmutabilidad semántica del plan.
      
      # Estado de ejecución (para observabilidad)
      ready_for_execution = Column(Boolean, nullable=False, default=False, index=True)
      queued_at = Column(DateTime, nullable=True)  # Timestamp cuando se marcó como listo
      
      # Relationships
      strategy = relationship("Strategy", back_populates="execution_plans")
      event = relationship("Event")
  ```

- [ ] Añadir relación en `Strategy`:
  ```python
  execution_plans = relationship("ExecutionPlan", back_populates="strategy", cascade="all, delete-orphan")
  ```

- [ ] Crear migración Alembic:
  - [ ] `backend/alembic/versions/XXX_create_execution_plans.py`
  - [ ] Ejecutar: `alembic upgrade head`

#### 1.2. Modelo PlanLeg (Pydantic para validación)

- [ ] Crear `backend/app/core/strategy_engine/models.py` (si no existe):
  ```python
  from pydantic import BaseModel
  from decimal import Decimal
  from typing import Dict, Any
  
  class PlanLeg(BaseModel):
      leg_id: str
      side: str  # "BUY" | "SELL"
      outcome: str  # "YES" | "NO" | "UP" | "DOWN"
      target_price: Decimal
      size: Decimal
      size_usdc: Decimal
      status: str = "PENDING"  # PENDING | EXECUTING | FILLED | PARTIAL | FAILED | CANCELLED
      filled_size: Decimal = Decimal("0")
      filled_size_usdc: Decimal = Decimal("0")
      reason: str
      metadata: Dict[str, Any] = {}
  ```

#### 1.3. Validación de Invariantes

- [ ] Crear `backend/app/core/strategy_engine/invariants.py`:
  ```python
  def validate_plan_immutability(plan: ExecutionPlan) -> None:
      """Verifica que el plan no se modifique después de PLAN_BUILT."""
      if plan.status != "PLAN_BUILT":
          raise ValueError(f"Cannot modify plan in status {plan.status}")
  
  def validate_plan_state_transition(old_status: str, new_status: str) -> None:
      """Verifica transiciones de estado válidas."""
      valid_transitions = {
          "PLAN_BUILT": ["EXECUTING", "ABORTED"],
          "EXECUTING": ["COMPLETED", "FAILED", "ABORTED"],
          "COMPLETED": [],
          "FAILED": [],
          "ABORTED": []
      }
      if new_status not in valid_transitions.get(old_status, []):
          raise ValueError(f"Invalid transition: {old_status} -> {new_status}")
  ```

**Resultado**: ExecutionPlan en DB, validación de invariantes básica.

---

### **FASE 2: Nodos de Decision Graph - build_plan y emit_plan_intent** (2-3 días)

**Objetivo**: Implementar nodos que construyen ExecutionPlans.

#### 2.1. Nodo build_plan

- [ ] Crear `backend/app/core/strategy_engine/nodes/build_plan.py`:
  ```python
  from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult
  from app.models.execution_plan import ExecutionPlan
  from app.core.strategy_engine.models import PlanLeg
  
  class BuildPlanNode(GraphNode):
      async def execute(self) -> 'PlanResult':
          # Validar config
          legs_data = self.config.get("legs", [])
          ttl_ms = self.config.get("ttl_ms", 30000)
          
          # Construir PlanLegs
          legs = [PlanLeg(**leg_data) for leg_data in legs_data]
          
          # Crear ExecutionPlan en DB
          plan = ExecutionPlan(
              strategy_id=self.context.strategy_id,
              event_id=self.context.event_id,
              legs=[leg.dict() for leg in legs],  # Serializar a JSONB
              ttl_ms=ttl_ms,
              status="PLAN_BUILT",
              risk_config=self.config.get("risk_config", {}),
              trace_id=self.context.trace_id,
              decision_graph_execution_id=self.context.graph_execution_id
          )
          
          # Guardar en DB (usar self.context.db)
          self.context.db.add(plan)
          self.context.db.flush()
          
          return PlanResult(plan_id=plan.id)
  ```

- [ ] Añadir `PlanResult` a `base.py`:
  ```python
  class PlanResult(NodeResult):
      def __init__(self, plan_id: UUID):
          self.plan_id = plan_id
  ```

- [ ] Registrar nodo en `GraphRuntime`:
  ```python
  self.node_registry["build_plan"] = BuildPlanNode
  ```

#### 2.2. Nodo emit_plan_intent

- [ ] Crear `backend/app/core/strategy_engine/nodes/emit_plan_intent.py`:
  ```python
  from datetime import datetime
  from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult
  from app.models.execution_plan import ExecutionPlan
  
  class EmitPlanIntentNode(GraphNode):
      async def execute(self) -> SuccessResult:
          plan_id = self.config.get("plan_id")
          if not plan_id:
              raise ValueError("plan_id required")
          
          # Marcar plan como listo para ejecución (huella mínima para observabilidad)
          plan = self.context.db.query(ExecutionPlan).filter(ExecutionPlan.id == plan_id).first()
          if plan:
              plan.ready_for_execution = True
              plan.queued_at = datetime.utcnow()
              self.context.db.flush()
              # Esto permite:
              # - Observabilidad: saber cuándo se marcó como listo
              # - Debugging: rastrear race conditions
              # - Métricas: tiempo entre PLAN_BUILT y EXECUTING
          
          return SuccessResult()
  ```

- [ ] Registrar nodo en `GraphRuntime`

#### 2.3. Actualizar seed de nodos

- [ ] Actualizar `backend/scripts/seed_graph_node_definitions.py`:
  - [ ] Añadir definición de `build_plan`
  - [ ] Añadir definición de `emit_plan_intent`
  - [ ] Marcar `emit_execution_intent` como deprecated (añadir flag)

**Resultado**: Decision Graph puede construir ExecutionPlans.

---

### **FASE 3: Refactorizar calculate_order_size** (1 día)

**Objetivo**: Cambiar `calculate_order_size` para que retorne datos, no intents.

#### 3.1. Actualizar Nodo

- [ ] Modificar `backend/app/core/strategy_engine/nodes/calculate_order_size.py`:
  ```python
  # ANTES: Retornaba ExecutionIntentResult
  # AHORA: Retornar CalculationResult con datos
  
  class CalculationResult(NodeResult):
      def __init__(self, size: Decimal, price: Decimal, size_usdc: Decimal):
          self.size = size
          self.price = price
          self.size_usdc = size_usdc
  ```

- [ ] Actualizar lógica del nodo para retornar `CalculationResult`

#### 3.2. Actualizar GraphRuntime

- [ ] Modificar `GraphRuntime._result_to_dict()` para incluir `CalculationResult`

**Resultado**: `calculate_order_size` retorna datos, no intents.

---

### **FASE 4: Strategy Triggers** (2-3 días)

**Objetivo**: Implementar triggers explícitos para activar Decision Graph.

#### 4.1. Añadir campo triggers a Strategy

- [ ] Modificar `backend/app/models/strategy.py`:
  ```python
  triggers = Column(JSONB, nullable=False, default=[])  # List[Trigger]
  ```

- [ ] Crear migración Alembic para añadir columna

#### 4.2. Evaluador de Triggers

- [ ] Crear `backend/app/core/strategy_engine/trigger_evaluator.py`:
  ```python
  class TriggerEvaluator:
      def evaluate(self, trigger: Dict, strategy: Strategy, event: Event, state_cache: StateCacheService) -> bool:
          trigger_type = trigger.get("type")
          
          if trigger_type == "always":
              return True
          elif trigger_type == "near_end":
              return self._evaluate_near_end(trigger, event)
          elif trigger_type == "edge_detected":
              return self._evaluate_edge_detected(trigger, state_cache)
          elif trigger_type == "state_change":
              return self._evaluate_state_change(trigger, event)
          elif trigger_type == "timer":
              return self._evaluate_timer(trigger)
          else:
              return False
      
      def _evaluate_near_end(self, trigger: Dict, event: Event) -> bool:
          # Implementar lógica de near_end
          pass
      
      # ... otros métodos ...
  ```

#### 4.3. Integrar en ControlLoop

- [ ] Modificar `backend/app/core/strategy_engine/control_loop.py`:
  ```python
  async def tick(self, db: Session):
      for strategy_id, strategy in self.active_strategies.items():
          # Obtener eventos asignados
          strategy_events = db.query(StrategyEvent).filter(...).all()
          
          for strategy_event in strategy_events:
              event = strategy_event.event
              
              # NUEVO: Evaluar triggers
              if not self._evaluate_triggers(strategy, event):
                  continue  # Skip si no hay trigger match
              
              # Ejecutar Decision Graph solo si trigger match
              intents = await self.strategy_engine.execute_decision_graph(...)
  ```

- [ ] Implementar `_evaluate_triggers()` usando `TriggerEvaluator`

#### 4.4. Cooldown y Rate Limiting

- [ ] Implementar tracking de cooldown por trigger
- [ ] Implementar rate limiting (max_fires_per_event, max_fires_per_hour)

**Resultado**: Decision Graph solo se ejecuta cuando triggers match.

---

### **FASE 5: Execution Graphs - Nodos y Runtime** (4-5 días)

**Objetivo**: Implementar Execution Graphs para ejecutar planes.

#### 5.1. Añadir execution_graph a Strategy

- [ ] Modificar `backend/app/models/strategy.py`:
  ```python
  execution_graph = Column(JSONB, nullable=True)  # Grafo para ejecutar planes
  ```

- [ ] Crear migración Alembic

#### 5.2. Nodo execution_coordinator

- [ ] Crear `backend/app/core/strategy_engine/nodes/execution_coordinator.py`:
  ```python
  class ExecutionCoordinatorNode(GraphNode):
      async def execute(self) -> ExecutionResult:
          plan_id = self.config.get("plan_id")
          execution_mode = self.config.get("execution_mode", "sequential")
          
          # Obtener plan de DB con lock (SELECT FOR UPDATE)
          # CRÍTICO: Usar transacción con lock para evitar race conditions
          # cuando múltiples Execution Graphs intentan ejecutar el mismo plan
          plan = self.context.db.query(ExecutionPlan).filter(
              ExecutionPlan.id == plan_id
          ).with_for_update().first()
          
          # Validar invariantes
          validate_plan_immutability(plan)
          
          # Cambiar estado a EXECUTING (dentro de la transacción)
          validate_plan_state_transition(plan.status, "EXECUTING")
          plan.status = "EXECUTING"
          # NOTA: Todo esto debe estar en una transacción DB explícita
          # para garantizar atomicidad del cambio de estado
          
          # Ejecutar legs según modo
          if execution_mode == "sequential":
              result = await self._execute_sequential(plan)
          elif execution_mode == "parallel":
              result = await self._execute_parallel(plan)
          elif execution_mode == "atomic":
              result = await self._execute_atomic(plan)
          
          return ExecutionResult(plan_id=plan_id, legs_status=result)
  ```

- [ ] Implementar `_execute_sequential()`, `_execute_parallel()`, `_execute_atomic()`
- [ ] Integrar con Execution Engine existente

#### 5.3. Nodo retry_leg

- [ ] Crear `backend/app/core/strategy_engine/nodes/retry_leg.py`
- [ ] Implementar lógica de reintento con backoff

#### 5.4. Nodo compensate_plan

- [ ] Crear `backend/app/core/strategy_engine/nodes/compensate_plan.py`
- [ ] Implementar compensación (revertir órdenes ejecutadas)

#### 5.5. Nodo derive_plan

- [ ] Crear `backend/app/core/strategy_engine/nodes/derive_plan.py`
- [ ] Implementar creación de follow-up plan para remanente

#### 5.6. Método execute_execution_graph en StrategyEngine

- [ ] Añadir a `backend/app/core/strategy_engine/strategy_engine.py`:
  ```python
  async def execute_execution_graph(
      self,
      strategy: Strategy,
      plan: ExecutionPlan,
      event: Event,
      db: Session
  ) -> None:
      """Ejecuta Execution Graph para un plan."""
      # Similar a execute_decision_graph pero para execution_graph
  ```

#### 5.7. Integrar en ControlLoop

- [ ] Modificar `ControlLoop` para detectar planes con `status=PLAN_BUILT`
- [ ] Ejecutar Execution Graph para esos planes

**Resultado**: Execution Graphs funcionando, planes se ejecutan.

---

### **FASE 6: Risk Configuration y Invariantes** (2-3 días)

**Objetivo**: Implementar risk config a nivel plan y verificación de invariantes.

#### 6.1. Risk Config en ExecutionPlan

- [ ] Ya añadido en FASE 1, pero implementar validación:
  - [ ] `max_slippage`
  - [ ] `max_fill_delay_ms`
  - [ ] `max_partial_fill_ratio`
  - [ ] `abort_on_price_move`
  - [ ] `price_validation`
  - [ ] `liquidity_validation`

#### 6.2. Verificación de Invariantes en Runtime

- [ ] Añadir verificaciones en `execution_coordinator`:
  - [ ] Verificar inmutabilidad del plan
  - [ ] Verificar transiciones de estado
  - [ ] Verificar TTL (abortar si expirado)
  - [ ] Verificar que Execution Graph no lee APIs para decisiones

#### 6.3. Validación de Price/Liquidity

- [ ] Implementar validación de precio antes de ejecutar leg
- [ ] Implementar validación de liquidez antes de ejecutar leg
- [ ] Abortar si no se cumplen condiciones

**Resultado**: Risk config funcionando, invariantes verificadas.

---

### **FASE 7: Observability y Versioning** (2 días)

**Objetivo**: Configuración de observabilidad y reglas de versionado.

#### 7.1. Observability Config

- [ ] Añadir `observability_config` a `Strategy`
- [ ] Implementar emisión de métricas (usar sistema existente si hay)
- [ ] Implementar emisión de eventos
- [ ] Configuración de logging por nodo

#### 7.2. Versioning

- [ ] Documentar reglas de versionado en código
- [ ] Implementar pinning de versiones de nodos en Strategy
- [ ] Registrar versiones usadas en ExecutionPlan

**Resultado**: Observabilidad configurada, versionado funcionando.

---

### **FASE 8: Actualizar APIs** (2-3 días)

**Objetivo**: Añadir endpoints para Execution Plans y actualizar existentes.

#### 8.1. API Execution Plans

- [ ] Añadir a `backend/app/api/strategies.py`:
  - [ ] `GET /strategies/{id}/plans` - Lista planes
  - [ ] `GET /strategies/{id}/plans/{plan_id}` - Detalle plan
  - [ ] `POST /strategies/{id}/plans/{plan_id}/abort` - Abortar plan

#### 8.2. Actualizar API Strategy

- [ ] Añadir `execution_graph` a creación/actualización
- [ ] Añadir `triggers` a creación/actualización
- [ ] Añadir `observability_config` a creación/actualización

#### 8.3. Validación

- [ ] Validar que `execution_graph` tiene estructura correcta
- [ ] Validar que `triggers` tienen estructura correcta

**Resultado**: APIs completas para Execution Plans.

---

### **FASE 9: Testing y Validación** (3-4 días)

**Objetivo**: Tests completos y validación end-to-end.

#### 9.1. Tests Unitarios

- [ ] Tests de `build_plan` node
- [ ] Tests de `execution_coordinator` node
- [ ] Tests de `TriggerEvaluator`
- [ ] Tests de invariantes
- [ ] Tests de risk config

#### 9.2. Tests de Integración

- [ ] Test completo: Decision Graph → ExecutionPlan → Execution Graph
- [ ] Test de surebet multi-leg
- [ ] Test de near-end con follow-up plan
- [ ] Test de triggers (near_end, edge_detected)
- [ ] **Test crítico: Atomic surebet aborta si una cuota se mueve**
  - [ ] Crear surebet con 2 legs (modo atomic)
  - [ ] Simular que leg_1 se ejecuta exitosamente
  - [ ] Simular que precio de leg_2 se mueve > max_slippage antes de ejecutar
  - [ ] Verificar que plan se marca como FAILED
  - [ ] Verificar que leg_1 se compensa (revertido)
  - [ ] **Este test ahorra dinero en producción** - es el más importante para surebets

#### 9.3. Tests E2E

- [ ] Crear estrategia desde API
- [ ] Activar estrategia
- [ ] Verificar que genera planes
- [ ] Verificar que ejecuta planes
- [ ] Verificar métricas

**Resultado**: Sistema probado y validado.

---

### **FASE 10: Deprecación y Limpieza** (1-2 días)

**Objetivo**: Deprecar código antiguo y limpiar.

#### 10.1. Deprecar emit_execution_intent en Decision Graph

- [ ] Añadir warning si se usa `emit_execution_intent` en Decision Graph
- [ ] Documentar que debe usarse `build_plan` + `emit_plan_intent`
- [ ] Mantener `emit_execution_intent` para Execution Graph (si es necesario)

#### 10.2. Actualizar Documentación

- [ ] Actualizar ejemplos en código
- [ ] Actualizar README si existe
- [ ] Marcar código legacy como deprecated

**Resultado**: Código limpio, documentación actualizada.

---

## 📋 Checklist de Reutilización

### ✅ **Reutilizar Sin Cambios**

- [x] `Strategy` model (añadir campos nuevos)
- [x] `GraphNodeDefinition` model
- [x] `GraphExecution` model
- [x] `StateCacheService` (ya funciona)
- [x] `GraphRuntime` (añadir nuevos nodos)
- [x] Nodos básicos: `collect_state`, `edge_and_risk_check`, `noop`, `fetch_external_source`, `update_state_cache`, `log`
- [x] APIs básicas de strategies y graph-nodes

### ⚠️ **Refactorizar**

- [ ] `calculate_order_size` - Cambiar para retornar datos
- [ ] `emit_execution_intent` - Deprecar en Decision Graph
- [ ] `ControlLoop` - Añadir evaluación de triggers
- [ ] `StrategyEngine` - Añadir `execute_execution_graph()`
- [ ] `Strategy` model - Añadir campos: `execution_graph`, `triggers`, `observability_config`

### ❌ **Borrar/Deprecar**

- [ ] `emit_execution_intent` en Decision Graph (deprecar, no borrar todavía)
- [ ] Código legacy de estrategias (si existe y no se usa)

---

## ⏱️ Estimación de Tiempo

| Fase | Tiempo | Prioridad |
|------|--------|-----------|
| FASE 1: Execution Plans DB | 2-3 días | 🔴 Crítica |
| FASE 2: build_plan + emit_plan_intent | 2-3 días | 🔴 Crítica |
| FASE 3: Refactor calculate_order_size | 1 día | 🔴 Crítica |
| FASE 4: Strategy Triggers | 2-3 días | 🟡 Alta |
| FASE 5: Execution Graphs | 4-5 días | 🔴 Crítica |
| FASE 6: Risk Config + Invariantes | 2-3 días | 🟡 Alta |
| FASE 7: Observability + Versioning | 2 días | 🟢 Media |
| FASE 8: APIs | 2-3 días | 🟡 Alta |
| FASE 9: Testing | 3-4 días | 🔴 Crítica |
| FASE 10: Deprecación | 1-2 días | 🟢 Media |

**Total**: ~21-29 días (~1 mes)

---

## 🚀 Orden de Ejecución Recomendado

```
FASE 1 (Execution Plans DB)
    ↓
FASE 2 (build_plan + emit_plan_intent)
    ↓
FASE 3 (Refactor calculate_order_size)
    ↓
FASE 4 (Strategy Triggers) ─┐
    ↓                        │ (Pueden ir en paralelo)
FASE 5 (Execution Graphs) ─┤
    ↓                        │
FASE 6 (Risk + Invariantes) ┘
    ↓
FASE 7 (Observability)
    ↓
FASE 8 (APIs)
    ↓
FASE 9 (Testing)
    ↓
FASE 10 (Deprecación)
```

---

## ✅ Checklist de Inicio

Antes de empezar:

- [ ] Revisar `BACKEND_ARCHITECTURE_STRATEGIES.md`
- [ ] Verificar que código existente funciona
- [ ] Backup de base de datos
- [ ] Entorno de desarrollo configurado
- [ ] Tests existentes pasan

**¿Listo?** → Comenzar con **FASE 1**.

---

## 📝 Notas Importantes

1. **No romper compatibilidad**: Mantener `emit_execution_intent` funcionando durante transición
2. **Feature flags**: Considerar feature flag para activar Execution Plans gradualmente
3. **Migración de datos**: Si hay ExecutionIntents existentes, considerar migración a ExecutionPlans
4. **Testing incremental**: Probar después de cada fase
5. **Documentación**: Actualizar docs mientras se implementa

---

**Última actualización**: 2025-12-20

