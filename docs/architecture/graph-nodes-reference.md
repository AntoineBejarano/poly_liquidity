# Graph Nodes Reference

**Purpose**: Complete reference of all available graph nodes in the Strategy Engine, organized by graph type (Decision, Support, Execution).

**Audience**: Strategy developers, traders configuring strategies, engineers implementing new nodes.

**Where this is used**: Strategy design, node selection, graph configuration.

**Last updated**: 2025-01-XX

---

## System Architecture Overview

### Complete Module Flow

```mermaid
graph TD
    A[Scanner Engine] --> B[Event Mapping Layer]
    B --> C[Checker System]
    C --> D[Event Watch Engine]
    D --> E[Orderbook Engine]
    E --> F[State Cache]
    
    F --> G[Strategy Engine]
    G --> H[Decision Graph]
    G --> I[Support Graph]
    G --> J[Execution Graph]
    
    H --> K[Execution Plan]
    K --> J
    J --> L[Risk Engine]
    L --> M[Execution Engine]
    M --> N[Polymarket]
    
    O[Runtime Supervisor] --> A
    O --> C
    O --> M
    
    P[Metrics & Observability] --> Q[Live Control]
    M --> P
    G --> P
    L --> P
    
    style H fill:#e1f5ff
    style I fill:#fff4e1
    style J fill:#ffe1f5
    style F fill:#e1ffe1
```

### Graph Types Architecture

```mermaid
graph LR
    subgraph "Control Loop"
        CL[Control Loop<br/>Fixed Infrastructure]
    end
    
    subgraph "Strategy Engine"
        SE[Strategy Engine<br/>Orchestrator]
        SC[State Cache<br/>Read/Write]
    end
    
    subgraph "Decision Graph<br/>Hot Path < 50μs"
        DG[Decision Graph]
        DG --> CS[collect_state]
        CS --> EC[edge_and_risk_check]
        EC --> COS[calculate_order_size]
        COS --> BP[build_plan]
        BP --> EPI[emit_plan_intent]
    end
    
    subgraph "Support Graph<br/>Cold Path Async"
        SG[Support Graph]
        SG --> FES[fetch_external_source]
        FES --> USC[update_state_cache]
        USC --> LOG[log]
    end
    
    subgraph "Execution Graph<br/>Cold Path Async"
        EG[Execution Graph]
        EG --> EXC[execution_coordinator]
        EXC --> RL[retry_leg]
        RL --> CP[compensate_plan]
    end
    
    CL --> SE
    SE --> DG
    SE --> SG
    SE --> EG
    DG --> SC
    SG --> SC
    EG --> SC
    
    style DG fill:#e1f5ff
    style SG fill:#fff4e1
    style EG fill:#ffe1f5
    style SC fill:#e1ffe1
```

---

## Node Types by Graph

### Decision Graph Nodes (Hot Path)

**Purpose**: Fast decision-making (< 50μs), only reads State Cache, builds Execution Plans.

**Restrictions**: 
- ❌ Cannot call APIs
- ❌ Cannot modify State Cache
- ✅ Only reads State Cache
- ✅ Can build Execution Plans

```mermaid
graph TD
    START[Decision Graph Entry] --> CS[collect_state]
    CS --> EC1[edge_and_risk_check]
    EC1 -->|true| CI[calculate_indicators]
    EC1 -->|false| IDLE[idle]
    CI --> EC2[edge_and_risk_check]
    EC2 -->|true| COS[calculate_order_size]
    EC2 -->|false| IDLE
    COS --> BP[build_plan]
    BP --> EPI[emit_plan_intent]
    EPI --> END[End]
    IDLE --> END
    
    style CS fill:#e1f5ff
    style EC1 fill:#e1f5ff
    style EC2 fill:#e1f5ff
    style CI fill:#e1f5ff
    style COS fill:#e1f5ff
    style BP fill:#e1f5ff
    style EPI fill:#e1f5ff
```

### Support Graph Nodes (Cold Path)

**Purpose**: Update State Cache with external data, can call APIs, async execution.

**Restrictions**:
- ✅ Can call APIs
- ✅ Can modify State Cache
- ✅ Can take as long as needed

```mermaid
graph TD
    START[Support Graph Trigger] --> FES[fetch_external_source]
    FES -->|success| USC[update_state_cache]
    FES -->|error| LOG[log]
    USC --> LOG
    LOG --> END[End]
    
    style FES fill:#fff4e1
    style USC fill:#fff4e1
    style LOG fill:#fff4e1
```

### Execution Graph Nodes (Cold Path)

**Purpose**: Execute Execution Plans, handle retries, compensation, order lifecycle.

**Restrictions**:
- ✅ Can read State Cache
- ✅ Can call trading APIs
- ❌ Cannot modify Execution Plan after PLAN_BUILT
- ✅ Can update leg status

```mermaid
graph TD
    START[Execution Plan Ready] --> EXC[execution_coordinator]
    EXC -->|leg success| NEXT{More Legs?}
    EXC -->|leg failed| RL[retry_leg]
    RL -->|retry success| NEXT
    RL -->|retry failed| CP[compensate_plan]
    NEXT -->|yes| EXC
    NEXT -->|no| END[End]
    CP --> END
    
    style EXC fill:#ffe1f5
    style RL fill:#ffe1f5
    style CP fill:#ffe1f5
```

---

## Complete Node Catalog

### Decision Graph Nodes

| Node Type | Description | Config Parameters | Path |
|-----------|-------------|-------------------|------|
| `collect_state` | Recopila estado del State Cache (solo lectura) | `sources: List[str]` - ["market_state", "event_state", "external_data", "risk_state", "orderbook_state"] | `backend/app/core/strategy_engine/nodes/collect_state.py` |
| `edge_and_risk_check` | Evalúa condiciones con lógica AND/OR | `conditions: List[Dict]` - [{field, operator, value}], `logic: str` - "AND"\|"OR" | `backend/app/core/strategy_engine/nodes/edge_and_risk_check.py` |
| `calculate_order_size` | Calcula tamaño de orden con restricciones | `method: str` - "fixed_range"\|"capacity_aware", `min: Decimal`, `max: Decimal` | `backend/app/core/strategy_engine/nodes/calculate_order_size.py` |
| `calculate_indicators` | Calcula indicadores técnicos avanzados | `indicators: List[str]` - ["confidence_score", "book_imbalance", etc.] | `backend/app/core/strategy_engine/nodes/calculate_indicators.py` |
| `build_plan` | Construye ExecutionPlan inmutable | `legs: List[Dict]`, `ttl_ms: int`, `risk_config: Dict` | `backend/app/core/strategy_engine/nodes/build_plan.py` |
| `emit_plan_intent` | Emite intent de plan para Execution Graph | `plan_id: str` | `backend/app/core/strategy_engine/nodes/emit_plan_intent.py` |
| `emit_execution_intent` | Emite intent de ejecución directa (legacy) | `side: str`, `outcome: str`, `price: Decimal`, `size: Decimal` | `backend/app/core/strategy_engine/nodes/emit_execution_intent.py` |
| `derive_plan` | Deriva plan desde otro plan (multi-leg) | `source_plan_id: str`, `derivation_rules: Dict` | `backend/app/core/strategy_engine/nodes/derive_plan.py` |
| `noop` | No operation (placeholder/end node) | None | `backend/app/core/strategy_engine/nodes/noop.py` |

### Support Graph Nodes

| Node Type | Description | Config Parameters | Path |
|-----------|-------------|-------------------|------|
| `fetch_external_source` | Obtiene datos de fuente externa configurable | `source_id: str`, `endpoint: str`, `params: Dict`, `output_key: str` | `backend/app/core/strategy_engine/nodes/fetch_external_source.py` |
| `update_state_cache` | Actualiza State Cache con nuevos datos | `key: str`, `value_source: str`, `value_path: str`, `ttl_seconds: int` | `backend/app/core/strategy_engine/nodes/update_state_cache.py` |
| `log` | Registra eventos para debugging/auditoría | `level: str`, `message: str`, `data: Dict` | `backend/app/core/strategy_engine/nodes/log.py` |
| `noop` | No operation (placeholder/end node) | None | `backend/app/core/strategy_engine/nodes/noop.py` |

### Execution Graph Nodes

| Node Type | Description | Config Parameters | Path |
|-----------|-------------|-------------------|------|
| `execution_coordinator` | Coordina ejecución de ExecutionPlan | `plan_id: str`, `execution_mode: str` - "sequential"\|"parallel"\|"atomic", `retry_config: Dict` | `backend/app/core/strategy_engine/nodes/execution_coordinator.py` |
| `retry_leg` | Reintenta ejecución de un leg fallido | `leg_id: str`, `max_retries: int`, `backoff_ms: int` | `backend/app/core/strategy_engine/nodes/retry_leg.py` |
| `compensate_plan` | Compensa plan fallido (reduce exposición) | `plan_id: str`, `compensation_mode: str` - "reverse"\|"cancel" | `backend/app/core/strategy_engine/nodes/compensate_plan.py` |
| `noop` | No operation (placeholder/end node) | None | `backend/app/core/strategy_engine/nodes/noop.py` |

---

## Node Execution Flow Example

### Near-Resolution Liquidity Provider Strategy

```mermaid
graph TD
    subgraph "Support Graph: confirm_event_result"
        SG_TRIGGER[Trigger: event_state_change] --> SG_FES[fetch_external_source]
        SG_FES --> SG_USC[update_state_cache]
        SG_USC --> SG_END[End]
    end
    
    subgraph "Decision Graph: evaluate_opportunity"
        DG_TRIGGER[Trigger: timer/event_change] --> DG_CS[collect_state]
        DG_CS --> DG_EC1[edge_and_risk_check<br/>Event finished?]
        DG_EC1 -->|true| DG_EC2[edge_and_risk_check<br/>Price in range?]
        DG_EC1 -->|false| DG_IDLE[idle]
        DG_EC2 -->|true| DG_EC3[edge_and_risk_check<br/>Orderbook OK?]
        DG_EC2 -->|false| DG_IDLE
        DG_EC3 -->|true| DG_COS[calculate_order_size]
        DG_EC3 -->|false| DG_IDLE
        DG_COS --> DG_BP[build_plan]
        DG_BP --> DG_EPI[emit_plan_intent]
        DG_EPI --> DG_END[End]
        DG_IDLE --> DG_END
    end
    
    subgraph "Execution Graph: execute_plan"
        EG_TRIGGER[Plan Ready] --> EG_EXC[execution_coordinator]
        EG_EXC --> EG_SUCCESS{Success?}
        EG_SUCCESS -->|yes| EG_END[End]
        EG_SUCCESS -->|no| EG_RL[retry_leg]
        EG_RL --> EG_RETRY{Retry OK?}
        EG_RETRY -->|yes| EG_END
        EG_RETRY -->|no| EG_CP[compensate_plan]
        EG_CP --> EG_END
    end
    
    SG_USC -.->|Updates State Cache| DG_CS
    DG_EPI -.->|Creates Plan| EG_TRIGGER
    
    style DG_CS fill:#e1f5ff
    style DG_EC1 fill:#e1f5ff
    style DG_EC2 fill:#e1f5ff
    style DG_EC3 fill:#e1f5ff
    style DG_COS fill:#e1f5ff
    style DG_BP fill:#e1f5ff
    style SG_FES fill:#fff4e1
    style SG_USC fill:#fff4e1
    style EG_EXC fill:#ffe1f5
    style EG_RL fill:#ffe1f5
    style EG_CP fill:#ffe1f5
```

---

## State Cache Structure

### Available State Sources

```mermaid
graph LR
    SC[State Cache] --> MS[market_state]
    SC --> ES[event_state]
    SC --> ED[external_data]
    SC --> RS[risk_state]
    SC --> OS[orderbook_state]
    
    MS --> MS1[last_price]
    MS --> MS2[spread_bps]
    MS --> MS3[liquidity]
    
    ES --> ES1[state: FINISHED_CONFIRMED]
    ES --> ES2[confidence]
    ES --> ES3[quorum_used]
    
    ED --> ED1[event_confirmation]
    ED --> ED2[surebet_opportunity]
    ED --> ED3[pinnacle_odds]
    
    RS --> RS1[exposure]
    RS --> RS2[max_exposure]
    RS --> RS3[position_size]
    
    OS --> OS1[spread_bps]
    OS --> OS2[depth_usdc_at_50bps]
    OS --> OS3[impact_bps_for_usdc_1000]
    OS --> OS4[staleness_ms]
    
    style SC fill:#e1ffe1
    style MS fill:#e1f5ff
    style ES fill:#e1f5ff
    style ED fill:#fff4e1
    style RS fill:#ffe1f5
    style OS fill:#e1f5ff
```

---

## Node Configuration Examples

### Decision Graph: collect_state

```json
{
  "type": "collect_state",
  "config": {
    "sources": ["market_state", "event_state", "external_data", "risk_state", "orderbook_state"]
  },
  "next": "check_event_finished"
}
```

### Decision Graph: edge_and_risk_check

```json
{
  "type": "edge_and_risk_check",
  "config": {
    "conditions": [
      {
        "field": "event_state.state",
        "operator": "==",
        "value": "FINISHED_CONFIRMED"
      },
      {
        "field": "market_state.last_price",
        "operator": ">=",
        "value": 0.95
      },
      {
        "field": "orderbook_state.spread_bps",
        "operator": "<=",
        "value": 150
      }
    ],
    "logic": "AND"
  },
  "on_true": "check_price_range",
  "on_false": "idle"
}
```

### Support Graph: fetch_external_source

```json
{
  "type": "fetch_external_source",
  "config": {
    "source_id": "uuid-of-external-source",
    "endpoint": "/api/event/result",
    "params": {
      "event_id": "{{event.id}}"
    },
    "output_key": "event_confirmation"
  },
  "next": "update_cache"
}
```

### Execution Graph: execution_coordinator

```json
{
  "type": "execution_coordinator",
  "config": {
    "plan_id": "{{plan.id}}",
    "execution_mode": "sequential",
    "retry_config": {
      "max_retries": 3,
      "backoff_ms": 1000
    },
    "compensation_enabled": true
  },
  "next": "end"
}
```

---

## Related Documentation

- [`execution-engine.md`](./execution-engine.md) - Execution engine architecture
- [`../strategies/README.md`](../strategies/README.md) - Strategy philosophy
- [`../strategies/templates.md`](../strategies/templates.md) - Strategy templates guide
- [`../strategies/near-resolution-complete-analysis.md`](../strategies/near-resolution-complete-analysis.md) - Complete strategy example

---

## Node Development Guidelines

### Creating New Nodes

1. **Inherit from `GraphNode`** - Base class in `backend/app/core/strategy_engine/nodes/base.py`
2. **Implement `execute()` method** - Returns appropriate `NodeResult` type
3. **Register in `__init__.py`** - Add to exports
4. **Add tests** - Unit tests in `backend/tests/unit/strategy_engine/nodes/`
5. **Document** - Update this file with node description and config

### Node Result Types

- `SuccessResult` - Node completed successfully
- `ConditionalResult` - Boolean result (true/false paths)
- `PlanResult` - Created/modified ExecutionPlan
- `ExecutionResult` - Execution completed
- `FailureResult` - Node failed (with reason)
- `CalculationResult` - Calculated value
- `ExecutionIntentResult` - Legacy execution intent (deprecated)

---

## Quick Reference: Node Selection Guide

**Need to read State Cache?** → `collect_state`

**Need to check conditions?** → `edge_and_risk_check`

**Need to calculate order size?** → `calculate_order_size`

**Need to build execution plan?** → `build_plan`

**Need to fetch external data?** → `fetch_external_source` (Support Graph only)

**Need to update State Cache?** → `update_state_cache` (Support/Execution Graph only)

**Need to execute plan?** → `execution_coordinator` (Execution Graph only)

**Need to retry failed leg?** → `retry_leg` (Execution Graph only)

**Need to compensate failed plan?** → `compensate_plan` (Execution Graph only)

