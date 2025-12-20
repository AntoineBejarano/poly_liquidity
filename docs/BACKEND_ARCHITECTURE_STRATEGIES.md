# Arquitectura del Backend - Sistema de Estrategias Basado en Grafos

**Fecha**: 2025-12-20  
**Versión**: 1.0

---

## 📋 Índice

1. [Visión General](#visión-general)
2. [Arquitectura por Capas](#arquitectura-por-capas)
3. [Modelo de Datos](#modelo-de-datos)
4. [Execution Plans](#execution-plans) ⭐ **NUEVO**
5. [Execution Graphs](#execution-graphs) ⭐ **NUEVO**
6. [Strategy Triggers](#strategy-triggers) ⭐ **NUEVO**
7. [Operational Configuration & Invariants](#operational-configuration--invariants) 🔒 **CRÍTICO**
8. [Sistema de Nodos](#sistema-de-nodos)
9. [Flujo de Ejecución](#flujo-de-ejecución)
10. [Cómo Crear una Estrategia](#cómo-crear-una-estrategia)
11. [APIs Disponibles](#apis-disponibles)
12. [Ejemplos Prácticos](#ejemplos-prácticos)

---

## 🎯 Visión General

El backend está diseñado con una **arquitectura basada en grafos declarativos** donde:

- **Las estrategias NO son código hardcodeado**, son **grafos JSON** que se ejecutan en runtime
- **Cada estrategia es un proceso vivo** (long-lived) que ejecuta un Control Loop
- **Decision Graph (hot path)**: Se ejecuta rápido (< 50μs), solo lee State Cache, nunca llama APIs. **Decide** si hay oportunidad y **construye un Plan**.
- **Execution Plans**: Entidades inmutables que representan un plan de ejecución (1 leg para near-end, N legs para surebet)
- **Execution Graphs (cold path)**: Ejecutan planes de forma asíncrona, manejan reintentos, compensación, atomicidad parcial
- **Support Graphs (cold path)**: Se ejecutan asíncronamente, pueden usar APIs, IA, tardar lo necesario. Actualizan State Cache.
- **State Cache**: Servicio centralizado que almacena estado (market_state, event_state, external_data, risk_state)
- **Strategy Triggers**: Condiciones explícitas que determinan cuándo activar el Decision Graph (no "evaluar siempre")

### Principios Fundamentales

1. ✅ **Strategy es la entidad raíz** - No markets o events
2. ✅ **Event es la unidad de ejecución atómica** - No el market
3. ✅ **Las estrategias NO llaman APIs directamente** - Solo leen State Cache
4. ✅ **Fuentes de datos externas son configurables** - Desde DB/frontend
5. ✅ **No hay nombres hardcodeados** - Todo es configurable
6. ✅ **Solo el venue de ejecución está fijo** - Polymarket
7. ✅ **Estrategias declarativas** - JSON, no código Python
8. ✅ **Plan explícito e inmutable** - ExecutionPlan separa decisión de ejecución
9. ✅ **Execution Graph para operar** - Maneja multi-leg, reintentos, compensación
10. ✅ **Triggers explícitos** - No "evaluar siempre", solo cuando se cumplen condiciones

---

## 🏗️ Arquitectura por Capas

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTROL LOOP                             │
│  (Infraestructura fija - NO editable por usuario)           │
│  - Itera sobre estrategias activas                          │
│  - Evalúa Strategy Triggers (watchers explícitos)           │
│  - Dispara Decision Graph solo si trigger match             │
│  - Ejecuta Execution Graphs para planes listos              │
│  - Ejecuta Support Graphs según triggers                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  STRATEGY ENGINE                            │
│  - Orquesta ejecución de grafos                            │
│  - Coordina Graph Runtime + State Cache                    │
│  - Gestiona Execution Plans (inmutables)                   │
│  - Coordina Execution Graphs (multi-leg, reintentos)      │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
┌──────────────────┐              ┌──────────────────┐
│  GRAPH RUNTIME   │              │  STATE CACHE     │
│  - Ejecuta nodos │              │  - market_state  │
│  - Hot/Cold path │              │  - event_state   │
│  - Secuencial    │              │  - external_data │
└──────────────────┘              │  - risk_state    │
                                  └──────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              EXECUTION PLAN STORE                          │
│  - Almacena planes inmutables                              │
│  - Estados: PLAN_BUILT | EXECUTING | COMPLETED | FAILED   │
└─────────────────────────────────────────────────────────────┘
```

### Componentes Principales

#### 1. **Control Loop** (`app/core/strategy_engine/control_loop.py`)
- **Propósito**: Infraestructura fija que mantiene las estrategias vivas
- **NO es editable** por el usuario
- **Funciones**:
  - Carga estrategias activas desde DB
  - Itera sobre eventos asignados a cada estrategia
  - Dispara ejecución del Decision Graph cuando hay triggers
  - Ejecuta Support Graphs de forma asíncrona
  - Tick cada 100ms

#### 2. **Strategy Engine** (`app/core/strategy_engine/strategy_engine.py`)
- **Propósito**: Orquestador principal
- **Funciones**:
  - Ejecuta Decision Graph (hot path) - **Decide y construye Plan**
  - Ejecuta Execution Graphs (cold path) - **Ejecuta planes**
  - Ejecuta Support Graphs (cold path) - **Actualiza estado**
  - Guarda ejecuciones en DB (GraphExecution)
  - Gestiona Execution Plans (creación, actualización de estado)

#### 3. **Graph Runtime** (`app/core/strategy_engine/graph_runtime.py`)
- **Propósito**: Ejecuta grafos nodo por nodo
- **Funciones**:
  - Registra tipos de nodos disponibles
  - Ejecuta grafo de forma secuencial
  - Maneja transiciones (next, on_true, on_false)
  - Retorna intents generados

#### 4. **State Cache Service** (`app/core/strategy_engine/state_cache_service.py`)
- **Propósito**: Almacena estado compartido
- **Estructura**:
  - `market_state.{market_id}` - Estado del mercado
  - `event_state.{event_id}` - Estado del evento
  - `external_data.{source_id}` - Datos externos
  - `risk_state.{strategy_id}` - Estado de riesgo

---

## 📦 Execution Plans

### Concepto Clave

**ExecutionPlan** es una entidad **inmutable** que representa un plan de ejecución completo. Separa la **decisión** (Decision Graph) de la **ejecución** (Execution Graph).

### ¿Por qué Execution Plans?

1. **Para Surebets multi-leg**: Necesitas ejecutar múltiples órdenes de forma coordinada
2. **Para Near-End iterativo**: Necesitas reintentar y ajustar
3. **Para compensación**: Si una parte falla, necesitas deshacer
4. **Para atomicidad parcial**: Algunos legs pueden completarse, otros no

### Modelo de Datos

```python
class ExecutionPlan(BaseModel):
    """Plan de ejecución inmutable."""
    
    __tablename__ = "execution_plans"
    
    # Relación con estrategia y evento
    strategy_id = Column(UUID, ForeignKey("strategies.id"), nullable=False, index=True)
    event_id = Column(UUID, ForeignKey("events.id"), nullable=False, index=True)
    
    # Plan inmutable (no se modifica después de creado)
    legs: List[PlanLeg]  # 1 para near-end, N para surebet
    ttl_ms: int  # Tiempo de vida del plan
    created_at: datetime
    
    # Estado del plan
    status: str  # "PLAN_BUILT" | "ABORTED" | "EXECUTING" | "COMPLETED" | "FAILED"
    
    # Trazabilidad
    trace_id: UUID
    decision_graph_execution_id: UUID  # FK a GraphExecution
    execution_graph_execution_id: Optional[UUID]  # FK a GraphExecution (si se ejecuta)


class PlanLeg(BaseModel):
    """Un leg del plan (una orden a ejecutar)."""
    
    leg_id: str  # Identificador único del leg dentro del plan
    side: str  # "BUY" | "SELL"
    outcome: str  # "YES" | "NO" | "UP" | "DOWN"
    target_price: Decimal
    size: Decimal  # En shares
    size_usdc: Decimal  # En USDC
    
    # Estado del leg
    status: str  # "PENDING" | "EXECUTING" | "FILLED" | "PARTIAL" | "FAILED" | "CANCELLED"
    filled_size: Decimal = 0
    filled_size_usdc: Decimal = 0
    
    # Metadata
    reason: str  # Razón de este leg
    metadata: Dict[str, Any] = {}  # Contexto adicional
```

### Estructura de un Plan

```json
{
  "id": "uuid",
  "strategy_id": "uuid",
  "event_id": "uuid",
  "legs": [
    {
      "leg_id": "leg_1",
      "side": "BUY",
      "outcome": "YES",
      "target_price": 0.95,
      "size": 1000,
      "size_usdc": 950,
      "status": "PENDING",
      "reason": "Surebet leg 1"
    },
    {
      "leg_id": "leg_2",
      "side": "BUY",
      "outcome": "NO",
      "target_price": 0.05,
      "size": 1000,
      "size_usdc": 50,
      "status": "PENDING",
      "reason": "Surebet leg 2"
    }
  ],
  "ttl_ms": 30000,
  "status": "PLAN_BUILT",
  "created_at": "2025-12-20T10:00:00Z"
}
```

### Estados del Plan

| Estado | Descripción |
|--------|-------------|
| `PLAN_BUILT` | Plan creado, listo para ejecutar |
| `ABORTED` | Plan cancelado antes de ejecutar |
| `EXECUTING` | Plan en ejecución (al menos un leg activo) |
| `COMPLETED` | Todos los legs completados exitosamente |
| `FAILED` | Plan falló (no se pudo completar) |

### Estados de un Leg

| Estado | Descripción |
|--------|-------------|
| `PENDING` | Leg pendiente de ejecutar |
| `EXECUTING` | Leg en proceso de ejecución |
| `FILLED` | Leg completamente ejecutado |
| `PARTIAL` | Leg parcialmente ejecutado |
| `FAILED` | Leg falló |
| `CANCELLED` | Leg cancelado |

---

## ⚙️ Execution Graphs

### Concepto Clave

**Execution Graph** es un nuevo tipo de grafo (además de Decision Graph y Support Graph) que **ejecuta un ExecutionPlan**.

### Características

- **Cold path**: Puede tardar, usar APIs, reintentar
- **Con estado**: Mantiene estado de ejecución del plan
- **Maneja errores**: Reintentos, compensación, atomicidad parcial
- **Multi-leg**: Coordina ejecución de múltiples legs

### Tipos de Grafos

| Tipo | Path | Propósito | Ejemplo |
|------|------|-----------|---------|
| **Decision Graph** | Hot | Decide si hay oportunidad, construye Plan | `collect_state → check → build_plan` |
| **Execution Graph** | Cold | Ejecuta un Plan | `execution_coordinator → retry → compensate` |
| **Support Graph** | Cold | Actualiza State Cache | `fetch_external_source → update_state_cache` |

### Nodos Específicos de Execution Graph

#### `execution_coordinator` (NUEVO)

**Propósito**: Coordina la ejecución de un ExecutionPlan.

**Configuración**:
```json
{
  "type": "object",
  "properties": {
    "plan_id": {
      "type": "string",
      "format": "uuid",
      "description": "ID del ExecutionPlan a ejecutar"
    },
    "execution_mode": {
      "type": "string",
      "enum": ["sequential", "parallel", "atomic"],
      "default": "sequential",
      "description": "Cómo ejecutar los legs"
    },
    "retry_config": {
      "type": "object",
      "properties": {
        "max_retries": {"type": "integer", "default": 3},
        "retry_delay_ms": {"type": "integer", "default": 1000}
      }
    },
    "compensation_enabled": {
      "type": "boolean",
      "default": false,
      "description": "Si true, deshace legs si el plan falla"
    }
  },
  "required": ["plan_id"]
}
```

**Resultado**: `ExecutionResult` con estado de cada leg.

#### `retry_leg` (NUEVO)

**Propósito**: Reintenta un leg que falló.

**Configuración**:
```json
{
  "type": "object",
  "properties": {
    "leg_id": {"type": "string"},
    "max_retries": {"type": "integer", "default": 3},
    "backoff_ms": {"type": "integer", "default": 1000}
  },
  "required": ["leg_id"]
}
```

#### `compensate_plan` (NUEVO)

**Propósito**: Compensa (deshace) legs ejecutados si el plan falla.

**Configuración**:
```json
{
  "type": "object",
  "properties": {
    "plan_id": {"type": "string", "format": "uuid"},
    "compensation_strategy": {
      "type": "string",
      "enum": ["reverse_all", "reverse_failed", "none"],
      "default": "reverse_all"
    }
  },
  "required": ["plan_id"]
}
```

### Ejemplo de Execution Graph

```json
{
  "name": "execute_surebet_plan",
  "entry_node": "coordinate",
  "nodes": {
    "coordinate": {
      "type": "execution_coordinator",
      "config": {
        "plan_id": "{{plan.id}}",
        "execution_mode": "parallel",
        "retry_config": {
          "max_retries": 3,
          "retry_delay_ms": 1000
        },
        "compensation_enabled": true
      },
      "on_success": "check_completion",
      "on_failure": "compensate"
    },
    "check_completion": {
      "type": "check_plan_status",
      "config": {
        "plan_id": "{{plan.id}}"
      },
      "on_true": "end",
      "on_false": "retry_failed"
    },
    "retry_failed": {
      "type": "retry_leg",
      "config": {
        "leg_id": "{{failed_leg_id}}",
        "max_retries": 2
      },
      "on_success": "check_completion",
      "on_failure": "compensate"
    },
    "compensate": {
      "type": "compensate_plan",
      "config": {
        "plan_id": "{{plan.id}}",
        "compensation_strategy": "reverse_all"
      },
      "next": "end"
    },
    "end": {
      "type": "noop"
    }
  }
}
```

---

## 🎯 Strategy Triggers

### Concepto Clave

**Strategy Triggers** son condiciones explícitas que determinan **cuándo** ejecutar el Decision Graph. No se evalúa "siempre", solo cuando se cumplen las condiciones.

### ¿Por qué Triggers?

1. **Eficiencia**: No ejecutar Decision Graph innecesariamente
2. **Near-End**: Solo activar cuando `time_to_resolution` está en rango
3. **Surebet**: Solo activar cuando hay edge detectado
4. **Control explícito**: El usuario define cuándo evaluar

### Estructura de un Trigger

```json
{
  "type": "near_end",
  "conditions": {
    "time_to_resolution_lte": "20m",
    "time_to_resolution_gte": "5m"
  }
}
```

### Tipos de Triggers

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `always` | Siempre ejecutar (comportamiento actual) | `{"type": "always"}` |
| `near_end` | Solo cuando está cerca del final | `{"type": "near_end", "conditions": {"time_to_resolution_lte": "20m"}}` |
| `edge_detected` | Solo cuando hay edge | `{"type": "edge_detected", "conditions": {"min_edge": 0.05}}` |
| `state_change` | Solo cuando cambia estado | `{"type": "state_change", "conditions": {"field": "event_state.state", "values": ["ACTIVE"]}}` |
| `timer` | Cada X segundos | `{"type": "timer", "interval_seconds": 30}` |

### Configuración en Strategy

```python
class Strategy(BaseModel):
    # ... campos existentes ...
    
    # Strategy Triggers (NUEVO)
    triggers: JSONB = []  # Lista de triggers
    
    # Ejemplo:
    # [
    #   {
    #     "type": "near_end",
    #     "conditions": {
    #       "time_to_resolution_lte": "20m",
    #       "time_to_resolution_gte": "5m"
    #     }
    #   },
    #   {
    #     "type": "edge_detected",
    #     "conditions": {
    #       "min_edge": 0.05,
    #       "source": "external_data.pinnacle_odds"
    #     }
    #   }
    # ]
```

### Evaluación de Triggers en Control Loop

El Control Loop ahora:

1. **Evalúa triggers** antes de ejecutar Decision Graph
2. **Solo ejecuta** si al menos un trigger match
3. **No itera innecesariamente** sobre eventos que no cumplen condiciones

---

## 💾 Modelo de Datos

### Strategy (`app/models/strategy.py`)

```python
class Strategy(BaseModel):
    # Identificación
    name: str
    description: Optional[str]
    
    # Estado (proceso vivo)
    is_active: bool = False
    enabled_at: Optional[datetime]
    disabled_at: Optional[datetime]
    
    # Decision Graph (hot path) - JSON declarativo
    decision_graph: JSONB  # Grafo principal
    
    # Support Graphs (cold path) - Array de grafos
    support_graphs: JSONB = []  # Lista de grafos auxiliares
    
    # Execution Graph (cold path) - NUEVO
    execution_graph: Optional[JSONB] = None  # Grafo para ejecutar planes
    
    # Strategy Triggers (NUEVO)
    triggers: JSONB = []  # Condiciones para activar Decision Graph
    
    # Configuración
    control_loop_config: JSONB = {}  # Intervalo, triggers, etc.
    risk_config: JSONB = {}  # max_exposure, max_order_size, etc.
    
    # Metadata
    created_by: Optional[str]
    tags: Optional[List[str]]
    version: int = 1
```

### GraphNodeDefinition (`app/models/graph_node_definition.py`)

```python
class GraphNodeDefinition(BaseModel):
    # Identificación
    node_type: str  # "collect_state", "edge_and_risk_check", etc.
    name: str
    description: Optional[str]
    
    # Categoría
    category: str  # "state", "condition", "calculation", "action", "io"
    path_type: str  # "hot" (Decision Graph) o "cold" (Support Graph)
    
    # Schema de configuración (JSON Schema)
    config_schema: JSONB  # Valida config del nodo
    
    # Metadata
    is_builtin: bool = True
    version: Optional[str]
    icon: Optional[str]  # Para UI
```

---

## 🔒 Operational Configuration & Invariants

### Propósito

Esta sección define **qué puede pasar** y, más importante, **qué NUNCA puede pasar**. Esto protege el sistema de bugs y de configuraciones incorrectas (incluyendo LLM "creativo").

---

### 1️⃣ Execution Invariants (CRÍTICO)

Los **Execution Invariants** son reglas que **NUNCA** pueden violarse. Son verificadas en runtime y previenen errores costosos.

#### Invariantes Fundamentales

1. **An ExecutionPlan is immutable after creation.**
   - Una vez creado con estado `PLAN_BUILT`, el plan NO puede modificarse
   - No se pueden cambiar: legs, sizes, prices, TTL
   - Solo se puede cambiar el estado del plan (transiciones permitidas)

2. **No node may modify a plan after PLAN_BUILT.**
   - ❌ Prohibido: cambiar `leg.size`
   - ❌ Prohibido: cambiar `leg.target_price`
   - ❌ Prohibido: añadir/eliminar legs
   - ❌ Prohibido: modificar `plan.ttl_ms`
   - ✅ Permitido: actualizar `leg.status` (PENDING → EXECUTING → FILLED)

3. **Plan state transitions are strictly enforced.**
   ```
   PLAN_BUILT → EXECUTING → COMPLETED | FAILED | ABORTED
                    ↓
                 ABORTED (desde cualquier estado)
   ```
   - No se puede volver a un estado anterior
   - No se puede saltar estados
   - `ABORTED` puede ocurrir desde cualquier estado

4. **Execution TTL is enforced strictly.**
   - Si `plan.ttl_ms` expira, el plan DEBE ser abortado automáticamente
   - No se pueden ejecutar legs de un plan expirado
   - Los legs en ejecución se cancelan si el plan expira

5. **Execution Graph nodes may not read external data for decision-making.**
   - Los nodos de Execution Graph pueden leer State Cache
   - ❌ Prohibido: llamar APIs externas para decidir si ejecutar
   - ✅ Permitido: llamar APIs para ejecutar (polymarket trading API)
   - ✅ Permitido: leer State Cache actualizado por Support Graphs

6. **Compensation may only reduce exposure, never increase it.**
   - La compensación solo puede:
     - ✅ Revertir órdenes ejecutadas (reducir exposición)
     - ✅ Cancelar órdenes pendientes
   - ❌ Prohibido: crear nuevas órdenes durante compensación
   - ❌ Prohibido: aumentar el tamaño de órdenes existentes

7. **Hot path nodes may not modify State Cache.**
   - Decision Graph (hot path) solo puede LEER State Cache
   - ❌ Prohibido: `update_state_cache` en Decision Graph
   - ✅ Permitido: `update_state_cache` en Support Graphs y Execution Graphs

8. **A follow-up plan may be created; the original plan remains immutable.**
   - Si un plan tiene partial fills, se puede crear un plan nuevo (follow-up) para el remanente
   - ❌ Prohibido: Modificar el plan original
   - ✅ Permitido: Crear nuevo plan con `derive_plan` (nodo `derive_plan`)
   - El plan original mantiene su estado y no se modifica

#### Verificación de Invariantes

Los invariantes se verifican en:
- **Creación de Plan**: Al crear `ExecutionPlan`, se valida inmutabilidad
- **Transiciones de Estado**: Cada cambio de estado verifica reglas de transición
- **Ejecución de Nodos**: Cada nodo verifica que no viola invariantes
- **Compensación**: Se verifica que solo reduce exposición

---

### 2️⃣ Risk Configuration at Plan Level

Además de `risk_config` a nivel Strategy, cada `ExecutionPlan` tiene configuración de riesgo específica.

#### Campos de Risk en ExecutionPlan

```python
class ExecutionPlan(BaseModel):
    # ... campos existentes ...
    
    # Risk Configuration (NUEVO)
    risk_config: Dict[str, Any] = {
        "max_slippage": Decimal("0.01"),  # 1% máximo slippage permitido
        "max_fill_delay_ms": 5000,  # Máximo tiempo esperando fill
        "max_partial_fill_ratio": Decimal("0.2"),  # 20% máximo partial fill aceptable
        "abort_on_price_move": True,  # Abortar si precio se mueve > max_slippage
        "min_liquidity_required": Decimal("1000"),  # Liquidez mínima requerida
        "price_validation": {
            "max_price_drift": Decimal("0.01"),  # 1% drift máximo
            "abort_on_drift": True
        }
    }
```

#### Reglas de Risk a Nivel Plan

**Partial Fill Acceptance**:
- Si `filled_size / target_size >= (1 - max_partial_fill_ratio)` → ✅ Aceptable
- Si `filled_size / target_size < (1 - max_partial_fill_ratio)` → ❌ Abortar plan

**Price Movement**:
- Si `current_price` se mueve > `max_slippage` desde `target_price` → ❌ Abortar leg
- Si `abort_on_price_move = true` → Abortar inmediatamente
- Si `abort_on_price_move = false` → Continuar pero registrar warning

**Fill Delay**:
- Si un leg está en estado `EXECUTING` por > `max_fill_delay_ms` → ❌ Abortar leg
- Esto previene órdenes "colgadas" indefinidamente

**Liquidity Validation**:
- Antes de ejecutar leg, verificar que `market_state.liquidity >= min_liquidity_required`
- Si no hay suficiente liquidez → ❌ Abortar plan

#### Ejemplo de Configuración

```json
{
  "risk_config": {
    "max_slippage": 0.01,
    "max_fill_delay_ms": 5000,
    "max_partial_fill_ratio": 0.2,
    "abort_on_price_move": true,
    "min_liquidity_required": 1000,
    "price_validation": {
      "max_price_drift": 0.01,
      "abort_on_drift": true
    }
  }
}
```

---

### 3️⃣ Execution Coordinator Runtime Configuration

El `execution_coordinator` necesita configuración detallada para manejar casos edge en producción.

#### Configuración Completa

```json
{
  "type": "execution_coordinator",
  "config": {
    "plan_id": "{{plan.id}}",
    "execution_mode": "parallel",  // "sequential" | "parallel" | "atomic"
    
    // Execution Mode Definitions:
    // - sequential: Ejecuta legs en orden; aborta según política de riesgo
    // - parallel: Envía legs en paralelo; tolera fills en distintos tiempos
    // - atomic: Si no se completan TODOS los legs dentro del budget/TTL,
    //           se compensa según strategy y se marca FAILED (crítico para surebets)
    
    // Retry Configuration
    "retry_config": {
      "max_retries": 3,
      "retry_delay_ms": 1000,
      "backoff_strategy": "exponential"
    },
    
    // Price Validation (NUEVO)
    "price_validation": {
      "max_price_drift": 0.01,  // 1% drift máximo
      "abort_on_drift": true,    // Abortar si precio se mueve
      "check_on_retry": true     // Re-validar precio en cada retry
    },
    
    // Liquidity Validation (NUEVO)
    "liquidity_validation": {
      "min_remaining_liquidity": 500,  // Liquidez mínima requerida
      "abort_if_below": true,         // Abortar si liquidez baja
      "check_before_each_leg": true    // Verificar antes de cada leg
    },
    
    // Time Budgets (NUEVO)
    "time_budget_ms": 15000,      // Tiempo total máximo para el plan
    "order_ttl_ms": 3000,         // TTL de cada orden individual
    "leg_timeout_ms": 5000,       // Timeout por leg
    
    // Compensation
    "compensation_enabled": true,
    "compensation_strategy": "reverse_all",
    
    // Partial Fill Handling (NUEVO)
    "partial_fill_handling": {
      "accept_partial": true,
      "min_fill_ratio": 0.8,      // Aceptar si >= 80% filled
      "retry_for_remaining": true // Reintentar para completar
    }
  }
}
```

#### Preguntas Clave Respondidas

**"¿Cuánto me espero?"**
- `time_budget_ms`: Tiempo total máximo para ejecutar el plan
- `leg_timeout_ms`: Timeout por leg individual
- Si se excede → Abortar plan

**"¿Qué pasa si el libro cambia?"**
- `price_validation.max_price_drift`: Si precio se mueve > drift → Abortar
- `liquidity_validation.min_remaining_liquidity`: Si liquidez baja → Abortar

**"¿Cuándo abandono?"**
- Si `time_budget_ms` expirado → Abandonar
- Si `price_drift > max_price_drift` y `abort_on_drift = true` → Abandonar
- Si `liquidity < min_remaining_liquidity` y `abort_if_below = true` → Abandonar

**"¿Qué hago con partial fills?"**
- Si `accept_partial = true` y `filled_ratio >= min_fill_ratio` → ✅ Aceptar
- Si `retry_for_remaining = true` → Reintentar para completar
- Si no se cumple → ❌ Abortar leg

---

### 4️⃣ Advanced Trigger Configuration

Los triggers básicos necesitan configuración avanzada para evitar loops y spam en producción.

#### Configuración Avanzada de Triggers

```json
{
  "triggers": [
    {
      "type": "near_end",
      "conditions": {
        "time_to_resolution_lte": "20m",
        "time_to_resolution_gte": "5m"
      },
      
      // Cooldown (NUEVO)
      "cooldown_seconds": 60,  // No disparar más de una vez cada 60s
      
      // Rate Limiting (NUEVO)
      "max_fires_per_event": 3,  // Máximo 3 planes por evento
      "max_fires_per_hour": 10,   // Máximo 10 planes por hora (global)
      
      // Uniqueness (NUEVO)
      "once_per_plan": true,  // Solo un plan activo por evento a la vez
      "cancel_previous_plan": false,  // Si true, cancela plan anterior
      
      // Priority (NUEVO)
      "priority": "high",  // "low" | "normal" | "high" | "urgent"
      
      // Debounce (NUEVO)
      "debounce_ms": 2000  // Esperar 2s antes de disparar (evita spam)
    },
    {
      "type": "edge_detected",
      "conditions": {
        "min_edge": 0.05
      },
      "cooldown_seconds": 30,
      "max_fires_per_event": 1,  // Solo un surebet por evento
      "once_per_plan": true,
      "priority": "urgent"
    }
  ]
}
```

#### Reglas de Triggers Avanzados

**Cooldown**:
- Después de disparar un trigger, esperar `cooldown_seconds` antes de poder disparar de nuevo
- Previene loops rápidos

**Rate Limiting**:
- `max_fires_per_event`: Máximo número de planes que puede generar este trigger para un evento
- `max_fires_per_hour`: Límite global por hora (previene spam)

**Uniqueness**:
- `once_per_plan`: Si hay un plan activo para este evento, no crear otro
- `cancel_previous_plan`: Si `true`, cancela el plan anterior antes de crear uno nuevo

**Priority**:
- Determina orden de ejecución si hay múltiples triggers match
- `urgent` > `high` > `normal` > `low`

**Debounce**:
- Esperar `debounce_ms` antes de disparar
- Útil para evitar spam cuando condiciones cambian rápidamente

#### Ejemplo: Near-End con Protecciones

```json
{
  "triggers": [
    {
      "type": "near_end",
      "conditions": {
        "time_to_resolution_lte": "20m",
        "time_to_resolution_gte": "5m"
      },
      "cooldown_seconds": 60,
      "max_fires_per_event": 3,
      "once_per_plan": true,
      "priority": "high",
      "debounce_ms": 2000
    }
  ]
}
```

**Comportamiento**:
- Solo dispara cuando está entre 5-20 min del final
- Máximo 3 planes por evento
- Solo un plan activo a la vez
- Espera 2s antes de disparar (debounce)
- No dispara más de una vez cada 60s (cooldown)

---

### 5️⃣ Observability Configuration

Configuración declarativa de qué observar y cómo loggear.

#### Observability Config a Nivel Strategy

```json
{
  "observability_config": {
    // Metrics
    "emit_metrics": true,
    "metrics_interval_seconds": 10,
    
    // Events
    "emit_events": true,
    "event_types": ["plan_created", "plan_completed", "plan_failed", "leg_executed"],
    
    // Logging
    "log_level": "INFO",  // "DEBUG" | "INFO" | "WARNING" | "ERROR"
    "log_format": "json",  // "json" | "text"
    
    // Alerts
    "alerts": {
      "on_plan_failure": true,
      "on_compensation": true,
      "on_partial_fill": true,
      "on_price_drift": true,
      "on_liquidity_low": true,
      "on_ttl_expired": true
    },
    
    // Tracing
    "enable_tracing": true,
    "trace_sampling_rate": 1.0,  // 0.0 - 1.0
    
    // Performance
    "record_durations": true,
    "record_node_inputs": false,  // Cuidado: puede ser voluminoso
    "record_node_outputs": true
  }
}
```

#### Observability Config por Nodo

```json
{
  "type": "execution_coordinator",
  "config": {
    "plan_id": "{{plan.id}}",
    // ... otras configs ...
  },
  "observability": {
    "record_duration": true,
    "record_inputs": false,  // No registrar inputs (pueden ser grandes)
    "record_outputs": true,  // Registrar outputs (estado del plan)
    "log_level": "INFO",
    "emit_events": ["leg_started", "leg_completed", "leg_failed"]
  }
}
```

#### Métricas Emitidas

**Strategy Level**:
- `strategy.plans.created` - Planes creados
- `strategy.plans.completed` - Planes completados
- `strategy.plans.failed` - Planes fallidos
- `strategy.plans.aborted` - Planes abortados
- `strategy.legs.executed` - Legs ejecutados
- `strategy.legs.failed` - Legs fallidos
- `strategy.compensations.triggered` - Compensaciones ejecutadas

**Plan Level**:
- `plan.duration_ms` - Duración total del plan
- `plan.legs.count` - Número de legs
- `plan.legs.completed` - Legs completados
- `plan.legs.failed` - Legs fallidos
- `plan.slippage` - Slippage promedio
- `plan.price_drift` - Drift de precio máximo

**Leg Level**:
- `leg.duration_ms` - Duración del leg
- `leg.fill_ratio` - Ratio de fill (filled / target)
- `leg.slippage` - Slippage del leg
- `leg.retry_count` - Número de reintentos

#### Eventos Emitidos

```json
{
  "event_type": "plan_created",
  "strategy_id": "uuid",
  "plan_id": "uuid",
  "event_id": "uuid",
  "legs_count": 2,
  "timestamp": "2025-12-20T10:00:00Z"
}

{
  "event_type": "leg_executed",
  "strategy_id": "uuid",
  "plan_id": "uuid",
  "leg_id": "leg_1",
  "status": "FILLED",
  "fill_ratio": 1.0,
  "slippage": 0.002,
  "timestamp": "2025-12-20T10:00:05Z"
}

{
  "event_type": "plan_failed",
  "strategy_id": "uuid",
  "plan_id": "uuid",
  "reason": "price_drift_exceeded",
  "failed_legs": ["leg_2"],
  "timestamp": "2025-12-20T10:00:10Z"
}
```

---

### 6️⃣ Versioning & Compatibility

Reglas claras de versionado para evitar romper estrategias existentes.

#### Versioning Rules

1. **GraphNodeDefinitions are versioned independently.**
   - Cada nodo tiene `version: str` (ej: "1.0.0", "1.1.0", "2.0.0")
   - Cambios menores: "1.0.0" → "1.1.0" (backward compatible)
   - Cambios mayores: "1.0.0" → "2.0.0" (backward incompatible)

2. **Strategies pin node versions.**
   - Al crear/actualizar estrategia, se registran versiones de nodos usados
   - Ejemplo: `{"collect_state": "1.0.0", "build_plan": "1.2.0"}`
   - La estrategia siempre usa esas versiones, incluso si hay versiones nuevas

3. **ExecutionPlans record node versions used.**
   - Al crear un plan, se guardan las versiones de nodos que lo crearon
   - Esto permite debugging y auditoría
   - Ejemplo: `{"decision_graph_nodes": {"collect_state": "1.0.0", "build_plan": "1.2.0"}}`

4. **Backward incompatible node changes require new version.**
   - Si cambias `config_schema` de forma incompatible → nueva versión mayor
   - Si cambias comportamiento de forma incompatible → nueva versión mayor
   - Cambios compatibles → nueva versión menor o patch

#### Ejemplo de Versionado

```json
{
  "strategy": {
    "id": "uuid",
    "name": "My Strategy",
    "version": 1,
    "node_versions": {
      "collect_state": "1.0.0",
      "edge_and_risk_check": "1.1.0",
      "build_plan": "1.2.0",
      "execution_coordinator": "2.0.0"
    }
  },
  "execution_plan": {
    "id": "uuid",
    "node_versions_used": {
      "decision_graph": {
        "collect_state": "1.0.0",
        "edge_and_risk_check": "1.1.0",
        "build_plan": "1.2.0"
      }
    }
  }
}
```

#### Compatibilidad

**Backward Compatible Changes** (nueva versión menor):
- ✅ Añadir campos opcionales a `config_schema`
- ✅ Añadir nuevos valores a `enum`
- ✅ Cambiar comportamiento interno sin cambiar interfaz
- ✅ Mejoras de performance

**Backward Incompatible Changes** (nueva versión mayor):
- ❌ Eliminar campos de `config_schema`
- ❌ Cambiar tipo de campo
- ❌ Cambiar valores requeridos
- ❌ Cambiar comportamiento de forma que rompe expectativas

#### Migración de Versiones

```json
{
  "migration_strategy": "pin_versions",  // "pin_versions" | "auto_upgrade" | "manual"
  "auto_upgrade_rules": {
    "allow_minor_upgrades": true,  // 1.0.0 → 1.1.0 OK
    "allow_patch_upgrades": true,   // 1.0.0 → 1.0.1 OK
    "require_manual_major": true    // 1.0.0 → 2.0.0 requiere manual
  }
}
```

---

## 🔧 Sistema de Nodos

### Estructura de un Nodo

Cada nodo tiene:
- **Tipo único** (`node_type`): Identificador del nodo
- **Configuración** (`config`): Parámetros específicos del nodo
- **Transiciones**: `next`, `on_true`, `on_false`, `on_success`, `on_failure`

### Tipos de Nodos Disponibles

#### **Hot Path (Decision Graph)** - Solo lectura, rápido

| Nodo | Tipo | Categoría | Descripción |
|------|------|-----------|-------------|
| `collect_state` | `state` | Hot | Recopila estado del State Cache |
| `edge_and_risk_check` | `condition` | Hot | Evalúa condiciones y verifica riesgo |
| `calculate_order_size` | `calculation` | Hot | Calcula tamaño de orden (retorna datos, NO genera intent) |
| `build_plan` | `action` | Hot | Construye ExecutionPlan (NUEVO) |
| `emit_plan_intent` | `action` | Hot | Emite señal de que hay plan listo (NUEVO) |
| `noop` | `action` | Hot | No hace nada (fin del grafo) |

#### **Cold Path (Support Graphs)** - Pueden usar APIs, IA

| Nodo | Tipo | Categoría | Descripción |
|------|------|-----------|-------------|
| `fetch_external_source` | `io` | Cold | Obtiene datos de fuente externa (API) |
| `update_state_cache` | `state` | Cold | Actualiza State Cache |
| `log` | `io` | Cold | Registra mensaje en logs |
| `execution_coordinator` | `action` | Cold | Coordina ejecución de ExecutionPlan (NUEVO - Execution Graph) |
| `retry_leg` | `action` | Cold | Reintenta un leg que falló (NUEVO - Execution Graph) |
| `compensate_plan` | `action` | Cold | Compensa (deshace) legs ejecutados (NUEVO - Execution Graph) |
| `derive_plan` | `action` | Cold | Crea plan follow-up para remanente (NUEVO - Execution Graph) |

### Categorías de Nodos

1. **`state`**: Lee o escribe estado
2. **`condition`**: Evalúa condiciones booleanas
3. **`calculation`**: Realiza cálculos
4. **`action`**: Ejecuta acciones (emitir intent, etc.)
5. **`io`**: Input/Output (APIs, logs)

---

## 🔄 Flujo de Ejecución

### Ciclo de Vida de una Estrategia (Modelo Actualizado)

```
1. Strategy creada (is_active = False)
   ↓
2. Usuario asigna eventos a la estrategia (StrategyEvent)
   ↓
3. Usuario activa estrategia (is_active = True)
   ↓
4. Control Loop detecta estrategia activa
   ↓
5. Para cada evento asignado:
   ├─ Evalúa Strategy Triggers (watchers explícitos)
   │  └─ Si NO match → skip (no ejecutar Decision Graph)
   │
   ├─ Si trigger match → Ejecuta Decision Graph (hot path)
   │  ├─ collect_state → lee State Cache
   │  ├─ edge_and_risk_check → evalúa condiciones
   │  ├─ calculate_order_size → calcula tamaño (retorna datos)
   │  ├─ build_plan → construye ExecutionPlan (inmutable)
   │  └─ emit_plan_intent → señala que hay plan listo
   │
   ├─ Si hay plan listo → Ejecuta Execution Graph (cold path, async)
   │  ├─ execution_coordinator → ejecuta legs del plan
   │  ├─ retry_leg → reintenta si falla
   │  └─ compensate_plan → compensa si falla todo
   │
   └─ Ejecuta Support Graphs (cold path, async)
      ├─ fetch_external_source → llama API
      ├─ update_state_cache → actualiza cache
      └─ log → registra logs
   ↓
6. Execution Plans con estado EXECUTING pasan por Risk Engine
   ↓
7. Plans aprobados se ejecutan en Execution Engine
```

### Ejecución del Decision Graph (Modelo Actualizado)

**ANTES** (modelo antiguo - NO usar):
```python
# ❌ ANTIGUO: calculate_order_size genera intent directamente
calculate_size → emit_execution_intent  # ❌ DEPRECATED
```

**AHORA** (modelo nuevo):
```python
# ✅ NUEVO: calculate_order_size retorna datos, build_plan construye plan
graph = {
    "entry_node": "observe",
    "nodes": {
        "observe": {
            "type": "collect_state",
            "config": {"sources": ["market_state", "event_state"]},
            "next": "evaluate"
        },
        "evaluate": {
            "type": "edge_and_risk_check",
            "config": {
                "conditions": [
                    {"field": "event_state.state", "operator": "==", "value": "ACTIVE"},
                    {"field": "market_state.last_price", "operator": ">=", "value": 0.95}
                ],
                "logic": "AND"
            },
            "on_true": "calculate_size",
            "on_false": "idle"
        },
        "calculate_size": {
            "type": "calculate_order_size",
            "config": {"method": "fixed_range", "min": 100, "max": 5000},
            "next": "build_plan"  # ✅ Retorna datos, NO genera intent
        },
        "build_plan": {
            "type": "build_plan",
            "config": {
                "legs": [
                    {
                        "side": "BUY",
                        "outcome": "YES",
                        "size": "{{calculate_size.size}}",
                        "target_price": "{{market_state.last_price}}",
                        "reason": "Edge detected"
                    }
                ],
                "ttl_ms": 30000
            },
            "next": "emit_plan_intent"
        },
        "emit_plan_intent": {
            "type": "emit_plan_intent",
            "config": {
                "plan_id": "{{build_plan.plan_id}}"
            },
            "next": "idle"
        },
        "idle": {
            "type": "noop"
        }
    }
}
```

**Flujo de ejecución**:
1. Empieza en `observe` (entry_node)
2. `collect_state` → lee State Cache
3. `edge_and_risk_check` → evalúa condiciones
   - Si `True` → va a `calculate_size`
   - Si `False` → va a `idle` (termina)
4. `calculate_order_size` → **retorna datos** (size, price), NO genera intent
5. `build_plan` → **construye ExecutionPlan** (inmutable)
6. `emit_plan_intent` → **señala que hay plan listo** (no ejecuta)
7. `idle` → termina

**Luego** (fuera del Decision Graph):
- Execution Graph detecta plan listo
- `execution_coordinator` ejecuta el plan

---

## 📝 Cómo Crear una Estrategia

### Paso 1: Obtener Nodos Disponibles

```bash
GET /api/graph-nodes?path_type=hot
```

Retorna lista de nodos disponibles para Decision Graph.

### Paso 2: Diseñar el Decision Graph

**Estructura mínima**:
```json
{
  "entry_node": "nombre_del_nodo_inicial",
  "nodes": {
    "nombre_del_nodo_inicial": {
      "type": "tipo_de_nodo",
      "config": { /* configuración */ },
      "next": "siguiente_nodo"  // o "on_true"/"on_false"
    }
  }
}
```

**Ejemplo completo**:
```json
{
  "entry_node": "observe",
  "nodes": {
    "observe": {
      "type": "collect_state",
      "config": {
        "sources": ["market_state", "event_state", "risk_state"]
      },
      "next": "check_conditions"
    },
    "check_conditions": {
      "type": "edge_and_risk_check",
      "config": {
        "conditions": [
          {
            "field": "event_state.state",
            "operator": "==",
            "value": "ACTIVE"
          },
          {
            "field": "market_state.last_price",
            "operator": ">=",
            "value": 0.95
          },
          {
            "field": "risk_state.exposure",
            "operator": "<",
            "value": 10000
          }
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
      "next": "build_plan"
    },
    "build_plan": {
      "type": "build_plan",
      "config": {
        "legs": [
          {
            "leg_id": "leg_1",
            "side": "BUY",
            "outcome": "YES",
            "target_price": "{{market_state.last_price}}",
            "size": "{{calculate_size.size}}",
            "reason": "High probability edge detected"
          }
        ],
        "ttl_ms": 30000
      },
      "next": "emit_plan"
    },
    "emit_plan": {
      "type": "emit_plan_intent",
      "config": {
        "plan_id": "{{build_plan.plan_id}}"
      },
      "next": "idle"
    },
    "idle": {
      "type": "noop"
    }
  }
}
```

### Paso 3: Crear la Estrategia

```bash
POST /api/strategies
Content-Type: application/json

{
  "name": "Mi Estrategia de Surebet",
  "description": "Estrategia que detecta oportunidades de arbitraje",
  "decision_graph": { /* grafo del paso 2 */ },
  "support_graphs": [],
  "control_loop_config": {
    "min_interval_seconds": 5
  },
  "risk_config": {
    "max_exposure": 10000,
    "max_order_size": 5000
  },
  "tags": ["surebet", "arbitrage"]
}
```

### Paso 4: Asignar Eventos a la Estrategia

```bash
POST /api/strategies/{strategy_id}/events
Content-Type: application/json

{
  "event_ids": ["uuid-1", "uuid-2", "uuid-3"]
}
```

### Paso 5: Activar la Estrategia

```bash
POST /api/strategies/{strategy_id}/activate
```

---

## 🔌 APIs Disponibles

### Estrategias

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/strategies` | GET | Lista todas las estrategias |
| `/api/strategies` | POST | Crea una nueva estrategia |
| `/api/strategies/{id}` | GET | Obtiene una estrategia |
| `/api/strategies/{id}` | PUT | Actualiza una estrategia |
| `/api/strategies/{id}/activate` | POST | Activa una estrategia |
| `/api/strategies/{id}/deactivate` | POST | Desactiva una estrategia |
| `/api/strategies/{id}/graph` | GET | Obtiene el grafo (decision o support) |
| `/api/strategies/{id}/graph` | PUT | Actualiza el grafo |
| `/api/strategies/{id}/events` | GET | Obtiene eventos asignados |
| `/api/strategies/{id}/events` | POST | Asigna eventos a la estrategia |
| `/api/strategies/{id}/intents` | GET | Obtiene intents generados |
| `/api/strategies/{id}/metrics` | GET | Obtiene métricas de la estrategia |
| `/api/strategies/{id}/executions` | GET | Obtiene ejecuciones del grafo |

### Nodos de Grafo

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/graph-nodes` | GET | Lista todos los nodos disponibles |
| `/api/graph-nodes?path_type=hot` | GET | Nodos para Decision Graph |
| `/api/graph-nodes?path_type=cold` | GET | Nodos para Support Graphs |
| `/api/graph-nodes?category=condition` | GET | Filtra por categoría |
| `/api/graph-nodes/{node_type}` | GET | Obtiene definición de un nodo |
| `/api/graph-nodes/categories/list` | GET | Lista todas las categorías |

---

## 📚 Ejemplos Prácticos

### Ejemplo 1: Surebet Multi-Leg (Modelo Actualizado)

**Objetivo**: Detectar surebet con 2 legs y ejecutarlos coordinadamente.

#### Decision Graph (hot path) - Decide y construye Plan

```json
{
  "entry_node": "collect",
  "nodes": {
    "collect": {
      "type": "collect_state",
      "config": {
        "sources": ["market_state", "external_data"]
      },
      "next": "check_surebet"
    },
    "check_surebet": {
      "type": "edge_and_risk_check",
      "config": {
        "conditions": [
          {
            "field": "external_data.surebet_detected",
            "operator": "==",
            "value": true
          },
          {
            "field": "external_data.total_edge",
            "operator": ">",
            "value": 0.05
          }
        ],
        "logic": "AND"
      },
      "on_true": "calculate_legs",
      "on_false": "idle"
    },
    "calculate_legs": {
      "type": "calculate_order_size",
      "config": {
        "method": "kelly",
        "edge": "{{external_data.total_edge}}"
      },
      "next": "build_plan"
    },
    "build_plan": {
      "type": "build_plan",
      "config": {
        "legs": [
          {
            "leg_id": "leg_yes",
            "side": "BUY",
            "outcome": "YES",
            "target_price": "{{market_state.yes_price}}",
            "size": "{{calculate_legs.size_yes}}",
            "reason": "Surebet leg 1"
          },
          {
            "leg_id": "leg_no",
            "side": "BUY",
            "outcome": "NO",
            "target_price": "{{market_state.no_price}}",
            "size": "{{calculate_legs.size_no}}",
            "reason": "Surebet leg 2"
          }
        ],
        "ttl_ms": 30000
      },
      "next": "emit_plan"
    },
    "emit_plan": {
      "type": "emit_plan_intent",
      "config": {
        "plan_id": "{{build_plan.plan_id}}"
      },
      "next": "idle"
    },
    "idle": {
      "type": "noop"
    }
  }
}
```

#### Execution Graph (cold path) - Ejecuta el Plan

```json
{
  "name": "execute_surebet_plan",
  "entry_node": "coordinate",
  "nodes": {
    "coordinate": {
      "type": "execution_coordinator",
      "config": {
        "plan_id": "{{plan.id}}",
        "execution_mode": "parallel",
        "retry_config": {
          "max_retries": 3,
          "retry_delay_ms": 1000
        },
        "compensation_enabled": true
      },
      "on_success": "check_completion",
      "on_failure": "compensate"
    },
    "check_completion": {
      "type": "check_plan_status",
      "config": {
        "plan_id": "{{plan.id}}"
      },
      "on_true": "end",
      "on_false": "retry_failed"
    },
    "retry_failed": {
      "type": "retry_leg",
      "config": {
        "leg_id": "{{failed_leg_id}}",
        "max_retries": 2
      },
      "on_success": "check_completion",
      "on_failure": "compensate"
    },
    "compensate": {
      "type": "compensate_plan",
      "config": {
        "plan_id": "{{plan.id}}",
        "compensation_strategy": "reverse_all"
      },
      "next": "end"
    },
    "end": {
      "type": "noop"
    }
  }
}
```

#### Strategy Configuration

```json
{
  "name": "Surebet Multi-Leg Strategy",
  "triggers": [
    {
      "type": "edge_detected",
      "conditions": {
        "min_edge": 0.05,
        "source": "external_data.surebet_detected"
      }
    }
  ],
  "decision_graph": { /* Decision Graph arriba */ },
  "execution_graph": { /* Execution Graph arriba */ }
}
```

### Ejemplo 2: Liquidity Near-End (Modelo Actualizado)

**Objetivo**: Activar solo cuando está cerca del final (5-20 min) y ejecutar iterativamente.

#### Decision Graph (hot path)

```json
{
  "entry_node": "collect",
  "nodes": {
    "collect": {
      "type": "collect_state",
      "config": {
        "sources": ["event_state", "market_state"]
      },
      "next": "check_liquidity"
    },
    "check_liquidity": {
      "type": "edge_and_risk_check",
      "config": {
        "conditions": [
          {
            "field": "market_state.liquidity",
            "operator": ">",
            "value": 10000
          },
          {
            "field": "market_state.spread",
            "operator": "<",
            "value": 0.02
          }
        ],
        "logic": "AND"
      },
      "on_true": "calculate",
      "on_false": "idle"
    },
    "calculate": {
      "type": "calculate_order_size",
      "config": {
        "method": "fixed_range",
        "min": 100,
        "max": 1000
      },
      "next": "build_plan"
    },
    "build_plan": {
      "type": "build_plan",
      "config": {
        "legs": [
          {
            "leg_id": "leg_1",
            "side": "BUY",
            "outcome": "YES",
            "target_price": "{{market_state.last_price}}",
            "size": "{{calculate.size}}",
            "reason": "Near-end liquidity play"
          }
        ],
        "ttl_ms": 60000
      },
      "next": "emit_plan"
    },
    "emit_plan": {
      "type": "emit_plan_intent",
      "config": {
        "plan_id": "{{build_plan.plan_id}}"
      },
      "next": "idle"
    },
    "idle": {
      "type": "noop"
    }
  }
}
```

#### Execution Graph (cold path) - Con reintentos iterativos

```json
{
  "name": "execute_near_end_plan",
  "entry_node": "coordinate",
  "nodes": {
    "coordinate": {
      "type": "execution_coordinator",
      "config": {
        "plan_id": "{{plan.id}}",
        "execution_mode": "sequential",
        "retry_config": {
          "max_retries": 5,
          "retry_delay_ms": 2000
        },
        "compensation_enabled": false
      },
      "on_success": "check_partial",
      "on_failure": "retry"
    },
    "check_partial": {
      "type": "check_plan_status",
      "config": {
        "plan_id": "{{plan.id}}",
        "check_partial": true
      },
      "on_true": "derive_followup",
      "on_false": "end"
    },
    "derive_followup": {
      "type": "derive_plan",
      "config": {
        "base_plan_id": "{{plan.id}}",
        "strategy": "fill_remaining",
        "ttl_ms": 30000
      },
      "next": "coordinate"
    },
    "retry": {
      "type": "retry_leg",
      "config": {
        "leg_id": "leg_1",
        "max_retries": 3
      },
      "on_success": "end",
      "on_failure": "end"
    },
    "end": {
      "type": "noop"
    }
  }
}
```

#### Strategy Configuration

```json
{
  "name": "Liquidity Near-End Strategy",
  "triggers": [
    {
      "type": "near_end",
      "conditions": {
        "time_to_resolution_lte": "20m",
        "time_to_resolution_gte": "5m"
      }
    }
  ],
  "decision_graph": { /* Decision Graph arriba */ },
  "execution_graph": { /* Execution Graph arriba */ }
}
```

### Ejemplo 3: Estrategia con Support Graph (Actualización de Estado)

**Decision Graph** (hot path) - Lee estado actualizado:
```json
{
  "entry_node": "collect",
  "nodes": {
    "collect": {
      "type": "collect_state",
      "config": {"sources": ["market_state", "external_data"]},
      "next": "check"
    },
    "check": {
      "type": "edge_and_risk_check",
      "config": {
        "conditions": [
          {"field": "external_data.confirmed", "operator": "==", "value": true}
        ]
      },
      "on_true": "build_plan",
      "on_false": "idle"
    },
    "build_plan": {
      "type": "build_plan",
      "config": {
        "legs": [
          {
            "leg_id": "leg_1",
            "side": "BUY",
            "outcome": "YES",
            "target_price": "{{market_state.last_price}}",
            "size": 1000,
            "reason": "External confirmation received"
          }
        ],
        "ttl_ms": 30000
      },
      "next": "emit_plan"
    },
    "emit_plan": {
      "type": "emit_plan_intent",
      "config": {"plan_id": "{{build_plan.plan_id}}"},
      "next": "idle"
    },
    "idle": {"type": "noop"}
  }
}
```

**Support Graph** (cold path) - Actualiza external_data:
```json
{
  "name": "fetch_external_confirmation",
  "trigger": {
    "type": "timer",
    "interval_seconds": 30
  },
  "entry_node": "fetch",
  "nodes": {
    "fetch": {
      "type": "fetch_external_source",
      "config": {
        "source_id": "uuid-of-external-source",
        "endpoint": "/api/confirm",
        "params": {"event_id": "{{event.id}}"}
      },
      "next": "update"
    },
    "update": {
      "type": "update_state_cache",
      "config": {
        "key": "external_data.confirmed",
        "value": "{{fetch_result}}"
      },
      "next": "end"
    },
    "end": {
      "type": "noop"
    }
  }
}
```

---

## 🎨 Estructura de un Nodo

### Configuración de Nodos

Cada nodo tiene un `config_schema` (JSON Schema) que define qué parámetros acepta.

### Schemas de Nodos Nuevos

#### `build_plan` (Hot Path - Decision Graph)

**Propósito**: Construye un ExecutionPlan inmutable a partir de datos calculados.

**Config Schema**:
```json
{
  "type": "object",
  "properties": {
    "legs": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "leg_id": {
            "type": "string",
            "description": "Identificador único del leg dentro del plan"
          },
          "side": {
            "type": "string",
            "enum": ["BUY", "SELL"],
            "description": "Lado de la orden"
          },
          "outcome": {
            "type": "string",
            "enum": ["YES", "NO", "UP", "DOWN"],
            "description": "Outcome de la orden"
          },
          "target_price": {
            "type": "number",
            "description": "Precio objetivo (puede usar {{variables}} del contexto)"
          },
          "size": {
            "type": "number",
            "description": "Tamaño en shares (puede usar {{variables}} del contexto)"
          },
          "size_usdc": {
            "type": "number",
            "description": "Tamaño en USDC (opcional, se calcula si no se proporciona)"
          },
          "reason": {
            "type": "string",
            "description": "Razón de este leg"
          },
          "metadata": {
            "type": "object",
            "description": "Metadata adicional del leg"
          }
        },
        "required": ["leg_id", "side", "outcome", "target_price", "size"]
      },
      "minItems": 1,
      "description": "Lista de legs del plan"
    },
    "ttl_ms": {
      "type": "integer",
      "default": 30000,
      "description": "Tiempo de vida del plan en milisegundos"
    },
    "metadata": {
      "type": "object",
      "description": "Metadata adicional del plan"
    }
  },
  "required": ["legs"]
}
```

**Resultado**: `PlanResult` con `plan_id` (UUID del ExecutionPlan creado).

**Ejemplo de uso**:
```json
{
  "type": "build_plan",
  "config": {
    "legs": [
      {
        "leg_id": "leg_1",
        "side": "BUY",
        "outcome": "YES",
        "target_price": "{{market_state.last_price}}",
        "size": "{{calculate_order_size.size}}",
        "reason": "Edge detected"
      }
    ],
    "ttl_ms": 30000
  }
}
```

#### `emit_plan_intent` (Hot Path - Decision Graph)

**Propósito**: Señala que hay un ExecutionPlan listo para ejecutar. No ejecuta, solo notifica.

**Config Schema**:
```json
{
  "type": "object",
  "properties": {
    "plan_id": {
      "type": "string",
      "format": "uuid",
      "description": "ID del ExecutionPlan (viene de build_plan)"
    },
    "priority": {
      "type": "string",
      "enum": ["low", "normal", "high", "urgent"],
      "default": "normal",
      "description": "Prioridad del plan"
    }
  },
  "required": ["plan_id"]
}
```

**Resultado**: `SuccessResult` - Plan marcado como listo para ejecución.

#### `execution_coordinator` (Cold Path - Execution Graph)

**Propósito**: Coordina la ejecución de un ExecutionPlan, ejecutando sus legs según el modo configurado.

**Config Schema**:
```json
{
  "type": "object",
  "properties": {
    "plan_id": {
      "type": "string",
      "format": "uuid",
      "description": "ID del ExecutionPlan a ejecutar"
    },
    "execution_mode": {
      "type": "string",
      "enum": ["sequential", "parallel", "atomic"],
      "default": "sequential",
      "description": "Modo de ejecución: sequential (uno por uno), parallel (todos a la vez), atomic (todo o nada)"
    },
    "retry_config": {
      "type": "object",
      "properties": {
        "max_retries": {
          "type": "integer",
          "default": 3,
          "minimum": 0,
          "description": "Máximo número de reintentos por leg"
        },
        "retry_delay_ms": {
          "type": "integer",
          "default": 1000,
          "minimum": 0,
          "description": "Delay entre reintentos en milisegundos"
        },
        "backoff_strategy": {
          "type": "string",
          "enum": ["fixed", "exponential", "linear"],
          "default": "fixed",
          "description": "Estrategia de backoff para reintentos"
        }
      }
    },
    "compensation_enabled": {
      "type": "boolean",
      "default": false,
      "description": "Si true, activa compensación automática si el plan falla"
    },
    "timeout_ms": {
      "type": "integer",
      "description": "Timeout total del plan en milisegundos"
    }
  },
  "required": ["plan_id"]
}
```

**Resultado**: `ExecutionResult` con estado de cada leg y estado general del plan.

**Ejemplo de uso**:
```json
{
  "type": "execution_coordinator",
  "config": {
    "plan_id": "{{plan.id}}",
    "execution_mode": "parallel",
    "retry_config": {
      "max_retries": 3,
      "retry_delay_ms": 1000,
      "backoff_strategy": "exponential"
    },
    "compensation_enabled": true,
    "timeout_ms": 30000
  }
}
```

#### `retry_leg` (Cold Path - Execution Graph)

**Propósito**: Reintenta un leg específico que falló.

**Config Schema**:
```json
{
  "type": "object",
  "properties": {
    "plan_id": {
      "type": "string",
      "format": "uuid",
      "description": "ID del ExecutionPlan"
    },
    "leg_id": {
      "type": "string",
      "description": "ID del leg a reintentar"
    },
    "max_retries": {
      "type": "integer",
      "default": 3,
      "minimum": 0
    },
    "backoff_ms": {
      "type": "integer",
      "default": 1000,
      "minimum": 0
    },
    "adjust_price": {
      "type": "boolean",
      "default": false,
      "description": "Si true, ajusta el precio según market_state actual"
    }
  },
  "required": ["plan_id", "leg_id"]
}
```

#### `compensate_plan` (Cold Path - Execution Graph)

**Propósito**: Compensa (deshace) legs ejecutados si el plan falla.

**Config Schema**:
```json
{
  "type": "object",
  "properties": {
    "plan_id": {
      "type": "string",
      "format": "uuid",
      "description": "ID del ExecutionPlan a compensar"
    },
    "compensation_strategy": {
      "type": "string",
      "enum": ["reverse_all", "reverse_failed", "reverse_partial", "none"],
      "default": "reverse_all",
      "description": "Estrategia de compensación"
    },
    "timeout_ms": {
      "type": "integer",
      "description": "Timeout para operaciones de compensación"
    }
  },
  "required": ["plan_id"]
}
```

**Estrategias de compensación**:
- `reverse_all`: Revierte todos los legs ejecutados
- `reverse_failed`: Solo revierte legs que fallaron
- `reverse_partial`: Solo revierte legs parcialmente ejecutados
- `none`: No compensa

### Schemas de Nodos Existentes (Actualizados)

#### `edge_and_risk_check`:
```json
{
  "type": "object",
  "properties": {
    "conditions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "field": {"type": "string"},
          "operator": {
            "type": "string",
            "enum": ["==", "!=", ">", ">=", "<", "<=", "in", "not_in"]
          },
          "value": {}
        },
        "required": ["field", "operator", "value"]
      }
    },
    "logic": {
      "type": "string",
      "enum": ["AND", "OR"],
      "default": "AND"
    }
  },
  "required": ["conditions"]
}
```

### Transiciones entre Nodos

Un nodo puede tener:
- **`next`**: Siguiente nodo siempre
- **`on_true`**: Si condición es True (para ConditionalResult)
- **`on_false`**: Si condición es False (para ConditionalResult)
- **`on_success`**: Si operación exitosa (para SuccessResult)
- **`on_failure`**: Si operación falla (para FailureResult)

---

## 🔍 Acceso a Estado en Nodos

Los nodos acceden al estado a través del `GraphExecutionContext`:

```python
# En un nodo
state = context.state_cache.get("market_state.{market_id}")
event_state = context.state_cache.get("event_state.{event_id}")
external_data = context.state_cache.get("external_data.{source_id}")
risk_state = context.state_cache.get("risk_state.{strategy_id}")
```

**Campos disponibles**:
- `context.strategy_id` - ID de la estrategia
- `context.event_id` - ID del evento actual
- `context.market_id` - ID del mercado
- `context.trace_id` - ID de traza de ejecución
- `context.state_cache` - Servicio de State Cache

---

## 📊 Ejecución y Trazabilidad

### GraphExecution

Cada ejecución de un grafo se guarda en `graph_executions`:

```python
{
  "id": "uuid",
  "strategy_id": "uuid",
  "graph_type": "decision" | "support",
  "event_id": "uuid",
  "status": "completed" | "failed",
  "started_at": "datetime",
  "completed_at": "datetime",
  "duration_ms": 12.5,
  "result": {"intents_count": 1},
  "error_message": null,
  "trace_id": "uuid",
  "node_executions": [
    {
      "node_id": "observe",
      "node_type": "collect_state",
      "duration_ms": 0.5,
      "result_type": "SuccessResult"
    },
    {
      "node_id": "check",
      "node_type": "edge_and_risk_check",
      "duration_ms": 0.3,
      "result_type": "ConditionalResult",
      "result": {"condition": true}
    }
  ]
}
```

### ExecutionIntent

> **⚠️ Nota Importante**: `ExecutionIntent` **NO es la unidad de ejecución**. `ExecutionPlans` son la unidad de ejecución. `ExecutionIntent` puede usarse como evento interno ("plan ready") o para cola/scheduling, pero la ejecución real se hace a través de `ExecutionPlan`.

Cada intent generado se guarda en `execution_intents` (legacy/compatibilidad):

```python
{
  "id": "uuid",
  "strategy_id": "uuid",
  "event_id": "uuid",
  "side": "BUY" | "SELL",
  "outcome": "YES" | "NO" | "UP" | "DOWN",
  "target_price": 0.95,
  "size": 1000,
  "size_usdc": 950,
  "reason": "Edge detected",
  "status": "PENDING" | "APPROVED" | "REJECTED" | "EXECUTED",
  "trace_id": "uuid",
  "graph_execution_id": "uuid"
}
```

---

## 🚀 Cómo Empezar

### 1. Verificar Nodos Disponibles

```bash
curl http://localhost:8000/api/graph-nodes?path_type=hot
```

### 2. Crear Estrategia de Prueba

```bash
curl -X POST http://localhost:8000/api/strategies \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Test Strategy",
    "description": "Estrategia de prueba",
    "decision_graph": {
      "entry_node": "collect",
      "nodes": {
        "collect": {
          "type": "collect_state",
          "config": {"sources": ["market_state"]},
          "next": "idle"
        },
        "idle": {"type": "noop"}
      }
    },
    "risk_config": {"max_exposure": 1000}
  }'
```

### 3. Activar Estrategia

```bash
curl -X POST http://localhost:8000/api/strategies/{strategy_id}/activate \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Ver Ejecuciones

```bash
curl http://localhost:8000/api/strategies/{strategy_id}/executions \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📖 Referencias

- **Modelos**: `backend/app/models/strategy.py`, `backend/app/models/graph_node_definition.py`
- **Engine**: `backend/app/core/strategy_engine/`
- **APIs**: `backend/app/api/strategies.py`, `backend/app/api/graph_nodes.py`
- **Scripts**: `backend/scripts/seed_graph_node_definitions.py`

---

## ✅ Checklist para Crear una Estrategia

- [ ] Diseñar Decision Graph (hot path)
- [ ] Validar que todos los nodos existen (`/api/graph-nodes`)
- [ ] Validar estructura del grafo (entry_node, nodes)
- [ ] Configurar `risk_config` (max_exposure, max_order_size)
- [ ] Configurar `control_loop_config` (opcional)
- [ ] Crear estrategia (`POST /api/strategies`)
- [ ] Asignar eventos (`POST /api/strategies/{id}/events`)
- [ ] Activar estrategia (`POST /api/strategies/{id}/activate`)
- [ ] Monitorear ejecuciones (`GET /api/strategies/{id}/executions`)
- [ ] Ver intents generados (`GET /api/strategies/{id}/intents`)

---

---

## 🔄 Resumen de Cambios (Modelo Actualizado)

### ✅ Lo que NO cambia (arquitectura base)

- ✅ Estrategias como grafos declarativos JSON
- ✅ Control Loop fijo y no editable
- ✅ Decision Graph hot / Support Graph cold
- ✅ State Cache como única fuente de lectura
- ✅ Nodos tipados, versionables, con schema
- ✅ No APIs desde el hot path

### 🆕 Lo que se añade (sin romper nada)

1. **Execution Plans**: Planes inmutables que separan decisión de ejecución
2. **Execution Graphs**: Nuevo tipo de grafo para ejecutar planes
3. **Strategy Triggers**: Watchers explícitos (no "evaluar siempre")
4. **Operational Configuration & Invariants** 🔒 **CRÍTICO**:
   - Execution Invariants (7 reglas fundamentales)
   - Risk Configuration a nivel Plan
   - Execution Coordinator runtime knobs
   - Advanced Trigger Configuration (cooldown, rate limiting)
   - Observability Configuration declarativa
   - Versioning & Compatibility rules
5. **Nodos nuevos**:
   - `build_plan` - Construye ExecutionPlan
   - `emit_plan_intent` - Señala que hay plan listo
   - `execution_coordinator` - Coordina ejecución de plan
   - `retry_leg` - Reintenta leg fallido
   - `compensate_plan` - Compensa plan fallido

### 🔧 Ajustes a nodos existentes

- **`calculate_order_size`**: 
  - ❌ ANTES: Generaba intent directamente
  - ✅ AHORA: Retorna datos (size, price) para `build_plan`

- **`emit_execution_intent`**:
  - ❌ ANTES: Se usaba en Decision Graph
  - ✅ AHORA: Se usa en Execution Graph (si es necesario)

---

**Última actualización**: 2025-12-20  
**Versión**: 2.1 (Modelo con Execution Plans, Execution Graphs + Operational Configuration & Invariants)

