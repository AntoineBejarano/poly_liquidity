# Decision Trace - Guías de Implementación

## Objetivo

Rastrear completamente cada decisión del bot para explicabilidad, manteniendo la tabla eficiente y no sobrecargada.

---

## Estructura de decision_trace

### Campos Principales

- `decision_stage`: Etapa del pipeline (`SCAN`, `EVENT_CONFIRMATION`, `STRATEGY`, `RISK`, `EXECUTION`)
- `input_data`: Datos de entrada **ACOTADOS**
- `output_data`: Datos de salida
- `config_used`: Configuración usada
- `reason`: Razón de la decisión

---

## ⚠️ Regla Crítica: input_data ACOTADO

### ❌ NO Incluir

1. **Orderbooks completos**
   - NO incluir todas las órdenes del orderbook
   - NO incluir historial completo de precios
   - NO incluir datos históricos extensos

2. **Datos redundantes**
   - NO incluir información que ya está en otras tablas (markets, events, etc.)
   - NO incluir datos que se pueden reconstruir desde otras fuentes

3. **Datos binarios o muy grandes**
   - NO incluir imágenes, archivos, etc.

### ✅ SÍ Incluir

1. **Resúmenes y métricas clave:**
   ```json
   {
     "market_id": "uuid",
     "best_ask": 0.98,
     "best_bid": 0.97,
     "spread": 0.01,
     "midpoint": 0.975,
     "liquidity_at_price": 5000.0
   }
   ```

2. **Estados resumidos:**
   ```json
   {
     "event_state": "FINISHED_CONFIRMED",
     "confidence": 0.95,
     "checkers_used": 2,
     "quorum_used": 2,
     "quorum_required": 2
   }
   ```

3. **Hashes de datos grandes:**
   ```json
   {
     "orderbook_hash": "sha256_hash_of_orderbook",
     "market_snapshot_hash": "sha256_hash_of_market_state"
   }
   ```

4. **Métricas clave:**
   ```json
   {
     "exposure_current": 5000.0,
     "exposure_limit": 10000.0,
     "latency_status": "GREEN",
     "runtime_mode": "GREEN"
   }
   ```

---

## Decision Stages

### SCAN
**Cuándo:** Cuando el Scanner evalúa un mercado

**Input data típico:**
```json
{
  "market_id": "uuid",
  "polymarket_id": "string",
  "category": "sports",
  "last_price": 0.98,
  "volume_24h": 100000.0,
  "liquidity": 50000.0,
  "status": "OPEN"
}
```

**Output data típico:**
```json
{
  "decision": "CANDIDATE" | "REJECTED",
  "reason": "meets_criteria" | "price_too_low" | "insufficient_liquidity"
}
```

### EVENT_CONFIRMATION
**Cuándo:** Cuando el EventEngine/StateAggregator determina estado del evento

**Input data típico:**
```json
{
  "event_id": "uuid",
  "checkers_available": 3,
  "checkers_healthy": 2,
  "quorum_base": 2,
  "quorum_effective": 2,
  "checker_results": [
    {
      "checker_name": "espn",
      "state": "FINISHED",
      "confidence": 0.95
    },
    {
      "checker_name": "flashscore",
      "state": "FINISHED",
      "confidence": 0.92
    }
  ]
}
```

**Output data típico:**
```json
{
  "event_state": "FINISHED_CONFIRMED",
  "confidence": 0.935,
  "quorum_used": 2,
  "checkers_used": ["espn", "flashscore"],
  "trading_permitted": true
}
```

### STRATEGY
**Cuándo:** Cuando el Strategy Engine decide crear un OrderIntent

**Input data típico:**
```json
{
  "market_id": "uuid",
  "best_ask": 0.98,
  "best_bid": 0.97,
  "spread": 0.01,
  "event_state": "FINISHED_CONFIRMED",
  "event_confidence": 0.95,
  "current_exposure": 5000.0,
  "exposure_limit": 10000.0,
  "latency_status": "GREEN"
}
```

**Output data típico:**
```json
{
  "order_intent": {
    "market_id": "uuid",
    "side": "BUY",
    "price": 0.979,
    "size": 5000.0,
    "reason": "conditions_met"
  }
}
```

### RISK
**Cuándo:** Cuando el Risk Engine valida un OrderIntent

**Input data típico:**
```json
{
  "order_intent": {
    "market_id": "uuid",
    "price": 0.979,
    "size": 5000.0
  },
  "current_market_exposure": 5000.0,
  "max_market_exposure": 10000.0,
  "current_global_exposure": 50000.0,
  "max_global_exposure": 200000.0,
  "active_markets": 5,
  "max_active_markets": 10
}
```

**Output data típico:**
```json
{
  "decision": "APPROVED" | "REJECTED" | "ADJUSTED",
  "approved_intent": {
    "price": 0.979,
    "size": 5000.0,
    "original_size": 5000.0,
    "adjustments": {}
  },
  "reason": "all_limits_respected" | "exceeds_market_exposure" | "size_adjusted"
}
```

### EXECUTION
**Cuándo:** Cuando el Execution Engine envía una orden

**Input data típico:**
```json
{
  "approved_intent": {
    "market_id": "uuid",
    "price": 0.979,
    "size": 5000.0
  },
  "execution_mode": "LIVE" | "PAPER" | "DRY_RUN",
  "wallet_address": "0x...",
  "nonce": 123
}
```

**Output data típico:**
```json
{
  "order_id": "uuid",
  "polymarket_order_id": "0x...",
  "status": "PENDING" | "FILLED" | "CANCELLED",
  "execution_mode": "LIVE"
}
```

---

## Ejemplo de Timeline en Frontend

Con `decision_stage`, el frontend puede mostrar:

```
Timeline de Decisión (trace_id: abc-123)

[SCAN] 10:00:00.100
  → Mercado evaluado: "Lakers vs Warriors"
  → Decisión: CANDIDATE
  → Razón: meets_criteria

[EVENT_CONFIRMATION] 10:00:00.200
  → Checkers disponibles: 2
  → Quorum usado: 2
  → Decisión: FINISHED_CONFIRMED
  → Confianza: 0.95

[STRATEGY] 10:00:00.300
  → Precio objetivo: 0.979
  → Tamaño: 5000.0
  → Decisión: OrderIntent creado

[RISK] 10:00:00.400
  → Validación: APPROVED
  → Tamaño final: 5000.0
  → Razón: all_limits_respected

[EXECUTION] 10:00:00.500
  → Orden enviada: 0xabc123...
  → Status: PENDING
  → Modo: LIVE
```

---

## Tamaño Estimado de input_data

**Objetivo:** Mantener `input_data` < 2KB por registro

**Estrategia:**
- Usar hashes para datos grandes
- Solo incluir métricas clave
- No incluir arrays extensos
- Comprimir JSON cuando sea posible

**Ejemplo de tamaño típico:**
- SCAN: ~500 bytes
- EVENT_CONFIRMATION: ~800 bytes
- STRATEGY: ~600 bytes
- RISK: ~700 bytes
- EXECUTION: ~500 bytes

**Total por trace completo:** ~3KB (5 etapas)

---

## Validación

La implementación es correcta cuando:

- [ ] `decision_stage` está presente en todos los traces
- [ ] `input_data` NO contiene orderbooks completos
- [ ] `input_data` NO contiene datos históricos extensos
- [ ] `input_data` contiene solo hashes/snapshots relevantes
- [ ] Frontend puede reconstruir timeline completo usando `decision_stage`
- [ ] Tamaño promedio de `input_data` < 2KB
- [ ] Tabla `decision_trace` no crece excesivamente rápido

