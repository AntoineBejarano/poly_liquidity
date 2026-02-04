# Operations Runbook

**Purpose**: Operational procedures and real-time monitoring guide for the Live Control system.

**Audience**: Operations team, engineers monitoring the system, on-call engineers.

**Where this is used**: Live Control dashboard, real-time monitoring, operational procedures.

**Last updated**: 2026-02-02

---

## Execution Gateway y Modos de Ejecución

### Invariantes de Seguridad

El sistema aplica **6 invariantes críticas** antes de cualquier escritura al CLOB:

| Invariante | Descripción | Qué ocurre si falla |
|------------|-------------|---------------------|
| **I1** | Solo `execution_mode=LIVE` puede escribir al CLOB | → Orden simulada (dry_run_*) |
| **I2** | Kill-switch (`system_active=false`) bloquea todas las mutaciones | → Orden rechazada |
| **I3** | Único punto de envío (Execution Gateway) | Garantizado por arquitectura |
| **I4** | Circuit breaker y latencia | → Orden rechazada si circuit abierto o latencia RED |
| **I5** | Trazabilidad obligatoria | → Evento `order_decision` con IDs |
| **I6** | Idempotencia por `idempotency_key` | → Devuelve resultado cacheado |

### Modos de Ejecución

| Modo | Comportamiento | Uso |
|------|----------------|-----|
| `DEMO` | Frontend-only, sin llamadas API | Demos y pruebas UI |
| `DRY_RUN` | Backend real, órdenes simuladas | Validación de lógica |
| `LIVE` | Backend real, órdenes al CLOB | Producción |

**Verificar modo actual:**
```bash
curl -s http://localhost:8000/api/values/status | jq '.execution_mode'
```

### Eventos de Observabilidad

Los siguientes eventos se emiten y pueden consultarse en logs/métricas:

| Evento | Cuándo | IDs incluidos |
|--------|--------|---------------|
| `strategy_activated` | Estrategia activada | strategy_id |
| `strategy_deactivated` | Estrategia desactivada | strategy_id |
| `plan_queued` | Plan marcado `ready_for_execution` | plan_id, strategy_id, event_id, trace_id |
| `precheck_failed` | Precheck rechaza plan | plan_id, strategy_id, reasons[] |
| `order_decision` | Gateway decide enviar/simular | trace_id, plan_id, strategy_id, decision, source_path |
| `order_sent` | Orden enviada al CLOB | trace_id, platform_order_id |
| `order_simulated` | Orden simulada (no LIVE) | trace_id, reason |
| `system_paused` | Kill-switch activado | - |
| `system_resumed` | Kill-switch desactivado | - |

### Procedimientos de Kill-Switch

**Pausar sistema (emergencia):**
```bash
curl -X POST http://localhost:8000/control/pause -H "Authorization: Bearer $TOKEN"
```

**Reanudar sistema:**
```bash
curl -X POST http://localhost:8000/control/resume -H "Authorization: Bearer $TOKEN"
```

**Verificar estado:**
```bash
curl -s http://localhost:8000/api/values/status | jq '.system_active'
```

---

## Overview

The **Live Control** system provides a **real-time view** of bot behavior:

1. **What events** the system is monitoring
2. **What markets** are associated with each event
3. **LIVE/FINISHED states** according to checkers
4. **Watcher states** (active, stopped, error)
5. **Strategy signals** (intents generated)
6. **Risk Engine decisions** (approvals/rejections)
7. **Orders sent, fills, and executions**
8. **System latency and health checks**

**Live Control is the primary tool for:**
- ✅ **Operating the bot** in real-time
- ✅ **Monitoring system behavior**
- ✅ **Debugging live events** when something fails
- ✅ **Identifying failures** before they cause problems
- ✅ **Validating system decisions**
- ✅ **Auditing the system** for compliance

**Live Control is not optional:**  
> It's the bot's mission control tool.

---

## Live Control API

### REST Endpoints

#### `GET /live/events`

**Returns all events currently monitored:**

```json
[
  {
    "event_id": "sports:nba:401585236",
    "event_type": "sports",
    "status": "LIVE",
    "confidence": 0.94,
    "watcher_status": "active",
    "markets": ["pm123", "pm555"],
    "last_update": "2025-01-25T20:15:30.123Z"
  }
]
```

#### `GET /live/markets`

**Returns all markets with current state:**

```json
[
  {
    "market_id": "pm123",
    "question": "Will the Lakers win?",
    "best_yes_price": 0.98,
    "best_no_price": 0.02,
    "event_state": "FINISHED_CONFIRMED",
    "strategy_signals": ["intent_created"],
    "orders": ["order_xyz"]
  }
]
```

#### `GET /live/system`

**Returns system health status:**

```json
{
  "runtime_mode": "GREEN",
  "latency_status": "GREEN",
  "active_watchers": 45,
  "active_markets": 12,
  "open_orders": 3,
  "global_exposure": 15000.0,
  "last_tick_duration_ms": 42
}
```

### Server-Sent Events (SSE)

**Subscribe to real-time updates:**

```javascript
const eventSource = new EventSource('/live/stream');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle update: event_state_changed, order_filled, etc.
};
```

**Event Types:**
- `event_state_changed` - Event state updated
- `intent_created` - Strategy created intent
- `intent_approved` - Risk approved intent
- `order_sent` - Order sent to Polymarket
- `order_filled` - Order filled
- `system_mode_changed` - Runtime mode changed

---

## Monitoring Procedures

### Daily Operations

1. **Check System Health**
   - Verify `runtime_mode == GREEN`
   - Check latency is acceptable
   - Verify no circuit breakers open

2. **Monitor Active Events**
   - Review active watchers
   - Check event states
   - Verify checker results

3. **Review Orders**
   - Check open orders
   - Monitor fills
   - Verify execution latency

4. **Check Exposure**
   - Verify global exposure within limits
   - Check per-market exposure
   - Review active markets count

### Incident Response

**If `runtime_mode == RED`:**

1. **Immediate Actions:**
   - Check kill switch status
   - Review recent errors
   - Check circuit breaker states

2. **Investigation:**
   - Query event logs for recent errors
   - Check latency metrics
   - Review checker failures

3. **Recovery:**
   - Fix underlying issue
   - Clear circuit breakers if appropriate
   - Resume trading gradually

**If orders not filling:**

1. **Check Order Status:**
   - Verify orders in Polymarket
   - Check order prices vs market
   - Review execution latency

2. **Check Market State:**
   - Verify market still open
   - Check liquidity
   - Review price movements

3. **Check System State:**
   - Verify no system pauses
   - Check risk limits
   - Review exposure

---

## Dashboard Views

### Events View

- List of all monitored events
- Current state (LIVE/FINISHED)
- Confidence levels
- Associated markets
- Watcher status

### Markets View

- All active markets
- Current prices
- Event states
- Strategy signals
- Open orders

### System View

- Runtime mode
- Latency metrics
- Circuit breaker states
- Exposure metrics
- Health checks

### Orders View

- All orders (open, filled, cancelled)
- Execution details
- Fill history
- Latency metrics

---

## Alerting

### Critical Alerts

- `runtime_mode == RED`
- Circuit breaker opened
- Exposure limit exceeded
- High error rate
- Latency spike

### Warning Alerts

- `runtime_mode == YELLOW`
- Latency elevated
- Checker failures
- Low confidence events

### Notification Channels

- Slack webhook
- Discord webhook
- Email
- SMS (for critical)

---

## Reintentos y Compensación

### Retry de Legs Fallidos

El nodo `RetryLegNode` permite reintentar legs fallidos con backoff exponencial:

**Configuración en Execution Graph:**
```json
{
  "node_type": "retry_leg",
  "config": {
    "leg_id": "{{failed_leg_id}}",
    "plan_id": "{{plan.id}}",
    "max_retries": 3,
    "retry_delay_ms": 1000,
    "backoff_multiplier": 2.0
  }
}
```

**Comportamiento:**
- Máximo 3 reintentos por defecto
- Delay inicial de 1 segundo
- Backoff exponencial: 1s → 2s → 4s

### Compensación de Planes Fallidos

El nodo `CompensatePlanNode` compensa (revierte) órdenes de un plan fallido:

**Estrategias de compensación:**

| Estrategia | Descripción |
|------------|-------------|
| `reverse_all` | Revierte todas las órdenes ejecutadas |
| `cancel_all` | Cancela todas las órdenes pendientes |
| `partial` | Solo compensa legs específicos |

**Configuración:**
```json
{
  "node_type": "compensate_plan",
  "config": {
    "plan_id": "{{plan.id}}",
    "compensation_strategy": "reverse_all"
  }
}
```

**Invariante:** La compensación solo puede **reducir exposición**, nunca aumentarla.

---

## Límites de Riesgo

### Precheck Automático

Antes de ejecutar cualquier plan, el sistema verifica:

1. **Position limits**: Exposición máxima por mercado
2. **Price drift**: Desviación entre precio target y precio actual
3. **Market impact**: Impacto estimado en el orderbook

**Si algún check falla:** El plan se rechaza y se emite `precheck_failed` con las razones.

### Verificar Límites Actuales

```bash
# Ver risk_config de una estrategia
curl -s http://localhost:8000/api/strategies/{id} | jq '.risk_config'
```

### Configuración de Límites

En la estrategia:
```json
{
  "risk_config": {
    "max_position_size": 1000,
    "max_exposure_usd": 5000,
    "drift_bps_limit": 50,
    "max_impact_bps": 100
  }
}
```

---

## Related Documentation

- [`../infrastructure/monitoring.md`](../infrastructure/monitoring.md) - Metrics collection
- [`../risk/kill-switch.md`](../risk/kill-switch.md) - Kill switch procedures
- [`incident-response.md`](incident-response.md) - Incident response
- [`troubleshooting.md`](troubleshooting.md) - Troubleshooting guide
- [`../implementation/LIVE_NEAR_RESOLUTION_ESTADO_Y_GAPS.md`](../implementation/LIVE_NEAR_RESOLUTION_ESTADO_Y_GAPS.md) - Invariantes y SPEC




