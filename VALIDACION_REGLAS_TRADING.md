# Validación de Reglas de Trading - Backend

## Análisis de Cumplimiento de Reglas Estrictas

### Regla 1: SOLO crear órdenes cuando `event_state == FINISHED_CONFIRMED`

**Especificación:** El sistema SOLO puede crear órdenes cuando `event_state == FINISHED_CONFIRMED`, determinado exclusivamente por el EventEngine con quorum de ≥2 checkers independientes y confidence >= min_feed_confidence.

#### ✅ EventEngine - Correcto
- **Archivo:** `backend/app/core/event_engine.py`
- **Línea 97:** `if finished_count >= 2: return ("FINISHED_CONFIRMED", avg_confidence)`
- **Línea 88-90:** Verifica que cada checker tenga `r.state == "FINISHED" and r.confidence >= min_confidence`
- **Línea 85:** `min_confidence = config_service.get("min_feed_confidence", 0.8)`
- **Estado:** ✅ Correcto - Requiere ≥2 checkers con confidence >= min_feed_confidence

#### ✅ Strategy Engine - Corregido
- **Archivo:** `backend/app/core/strategy/strategy.py`
- **Línea 203:** Ahora solo permite `FINISHED_CONFIRMED` (corregido)
- **Líneas 210-221:** Eliminado código que permitía `FINISHED_UNCONFIRMED` (corregido)
- **Líneas 334-339:** Eliminado código de ajuste de tamaño para `FINISHED_UNCONFIRMED` (corregido)
- **Estado:** ✅ Correcto - Solo permite crear órdenes cuando `event_state == FINISHED_CONFIRMED`

#### ✅ Risk Engine - Corregido
- **Archivo:** `backend/app/core/risk_engine/risk_engine.py`
- **Línea 259:** Ahora rechaza todas las órdenes que no sean `FINISHED_CONFIRMED` (corregido)
- **Líneas 260-262:** Eliminado código que permitía `FINISHED_UNCONFIRMED` con alta confianza (corregido)
- **Estado:** ✅ Correcto - Solo aprueba órdenes cuando `event_state == FINISHED_CONFIRMED`

---

### Regla 2: Strategy y Risk NO deben depender de watchers ni resultados raw de checkers

**Especificación:** Strategy y Risk NO deben depender de watchers ni de resultados raw de checkers.

#### ✅ Strategy Engine - Correcto
- **Archivo:** `backend/app/core/strategy/strategy.py`
- **Línea 482:** Usa `self._create_event_state_from_internal(market_id)` que obtiene desde `state.events[market_id]`
- **Línea 443-455:** `_create_event_state_from_internal()` solo accede a `state.events`, no a watchers ni checkers raw
- **Estado:** ✅ Correcto - No accede directamente a watchers ni resultados raw de checkers

#### ✅ Risk Engine - Correcto
- **Archivo:** `backend/app/core/risk_engine/risk_engine.py`
- **Línea 253-256:** Obtiene `event_state` desde `state.events[intent.market_id]`
- **Estado:** ✅ Correcto - No accede directamente a watchers ni resultados raw de checkers

---

### Regla 3: Precio objetivo: `min(best_ask - safety_tick, 1.0 - target_margin)`

**Especificación:** El precio objetivo debe calcularse como `min(best_ask - safety_tick, 1.0 - target_margin)` y nunca cruzar el spread.

#### ✅ Strategy Engine - Correcto
- **Archivo:** `backend/app/core/strategy/strategy.py`
- **Línea 280:** `safe_price = best_ask - effective_safety_tick`
- **Línea 281:** `max_price = 1.0 - config.target_edge` (donde `target_edge` es `target_margin`)
- **Línea 283:** `target_price = min(safe_price, max_price)`
- **Línea 286:** `target_price = max(target_price, best_bid)` - Asegura que no cruce el spread (no está por debajo del best_bid)
- **Estado:** ✅ Correcto - Implementa la fórmula exacta y protege contra cruzar el spread

---

### Regla 4: Tamaño de orden: mínimo entre límites de riesgo, liquidez real y tamaño máximo

**Especificación:** El tamaño de la orden debe ser el mínimo entre límites de riesgo, liquidez real y tamaño máximo por orden.

#### ✅ Strategy Engine - Correcto
- **Archivo:** `backend/app/core/strategy/strategy.py`
- **Línea 335-340:** 
  ```python
  base_size = min(
      size_from_capacity,      # Límite de exposición por mercado
      size_from_liquidity,     # Liquidez real del orderbook
      max_single,              # Tamaño máximo por orden
      size_from_global         # Límite de exposición global
  )
  ```
- **Estado:** ✅ Correcto - Toma el mínimo de todos los límites relevantes

---

### Regla 5: Latencia RED - No generar órdenes

**Especificación:** Si la latencia del sistema está en estado RED, no se deben generar órdenes bajo ningún concepto.

#### ✅ Strategy Engine - Correcto
- **Archivo:** `backend/app/core/strategy/strategy.py`
- **Línea 249:** `if runtime_mode == RuntimeMode.RED or latency_status == LatencyStatus.RED: return False`
- **Línea 310:** `if latency_status == LatencyStatus.RED: return 0.0` (en `_calculate_size`)
- **Estado:** ✅ Correcto - Rechaza entradas y retorna tamaño 0 cuando latencia es RED

#### ✅ Risk Engine - Correcto
- **Archivo:** `backend/app/core/risk_engine/risk_engine.py`
- **Línea 514:** `if runtime_mode == RuntimeMode.RED or latency_status == LatencyStatus.RED: return approved` (lista vacía)
- **Línea 195:** `if runtime_mode == RuntimeMode.RED or latency_status == LatencyStatus.RED: return (False, "latency_too_high", None)`
- **Estado:** ✅ Correcto - Rechaza todas las órdenes cuando latencia es RED

#### ✅ Execution Engine - Correcto
- **Archivo:** `backend/app/core/execution/execution.py`
- **Línea 1055:** `if latency_status == LatencyStatus.RED: await self._cancel_all_open_orders(reason="latency_red")`
- **Estado:** ✅ Correcto - Cancela órdenes abiertas cuando latencia es RED

---

### Regla 6: ExecutionEngine debe usar WalletService.get_active_wallet()

**Especificación:** El ExecutionEngine debe usar exclusivamente `WalletService.get_active_wallet()` y cancelar órdenes en pausas, cambios de wallet o resolución del market.

#### ✅ Execution Engine - Correcto
- **Archivo:** `backend/app/core/execution/execution.py`
- **Línea 1042:** `wallet = await wallet_service.get_active_wallet()`
- **Línea 1043-1045:** Verifica que wallet esté disponible antes de ejecutar
- **Línea 1048-1050:** Cancela órdenes si `state.system_active == False`
- **Estado:** ✅ Correcto - Usa exclusivamente `WalletService.get_active_wallet()`

#### ⚠️ Cancelación en cambios de wallet o resolución - Riesgoso
- **Archivo:** `backend/app/core/execution/execution.py`
- **Problema:** No se encontró código explícito que cancele órdenes cuando:
  - Cambia el wallet activo
  - El mercado se resuelve
- **Recomendación:** Implementar listeners para estos eventos y cancelar órdenes pendientes

---

## Resumen de Validación

### ✅ Correcto (4/6 reglas completamente cumplidas)
1. ✅ Strategy y Risk NO dependen de watchers ni checkers raw
2. ✅ Precio objetivo calculado correctamente: `min(best_ask - safety_tick, 1.0 - target_margin)`
3. ✅ Tamaño de orden: mínimo entre límites de riesgo, liquidez y tamaño máximo
4. ✅ Latencia RED: No se generan órdenes (Strategy, Risk, Execution)

### ✅ Corregido (2 violaciones críticas corregidas)
1. ✅ **Strategy Engine - CORREGIDO**
   - **Archivo:** `backend/app/core/strategy/strategy.py`
   - **Líneas corregidas:** 203-221
   - **Cambio aplicado:** Ahora solo permite `FINISHED_CONFIRMED`, eliminado código que permitía `FINISHED_UNCONFIRMED` con `aggressive_mode`
   - **Estado:** ✅ Cumple con la regla estricta

2. ✅ **Risk Engine - CORREGIDO**
   - **Archivo:** `backend/app/core/risk_engine/risk_engine.py`
   - **Líneas corregidas:** 259-264
   - **Cambio aplicado:** Ahora rechaza todas las órdenes que no sean `FINISHED_CONFIRMED`, eliminado código que permitía `FINISHED_UNCONFIRMED` con alta confianza
   - **Estado:** ✅ Cumple con la regla estricta

### ⚠️ Riesgoso (1 área de mejora)
1. ⚠️ **Cancelación de órdenes en cambios de wallet o resolución de mercado**
   - **Archivo:** `backend/app/core/execution/execution.py`
   - **Problema:** No se encontró código explícito que cancele órdenes cuando cambia el wallet activo o el mercado se resuelve
   - **Recomendación:** Implementar listeners para estos eventos

---

## Correcciones Aplicadas

### ✅ Corrección Crítica 1: Strategy Engine - COMPLETADA
**Archivo:** `backend/app/core/strategy/strategy.py`
**Línea 203:** Cambiado de:
```python
if event_state.event_status not in ["FINISHED_CONFIRMED", "FINISHED_UNCONFIRMED"]:
```
A:
```python
if event_state.event_status != "FINISHED_CONFIRMED":
```

**Líneas 209-221:** Eliminado código de modo agresivo para FINISHED_UNCONFIRMED
**Líneas 334-339:** Eliminado código de ajuste de tamaño para FINISHED_UNCONFIRMED

### ✅ Corrección Crítica 2: Risk Engine - COMPLETADA
**Archivo:** `backend/app/core/risk_engine/risk_engine.py`
**Línea 259:** Cambiado de:
```python
if event_state.state != "FINISHED_CONFIRMED":
    if event_state.state == "FINISHED_UNCONFIRMED":
        if event_state.confidence < 0.85:
            return (False, "event_not_confirmed")
    else:
        return (False, "event_not_finished")
```
A:
```python
if event_state.state != "FINISHED_CONFIRMED":
    return (False, "event_not_finished")
```

### Mejora Recomendada: Cancelación en cambios de wallet/resolución
Implementar listeners en `Execution` que:
1. Escuchen cambios de wallet activo desde `WalletService`
2. Escuchen resolución de mercados desde `Market` model
3. Cancelen todas las órdenes pendientes del wallet anterior o del mercado resuelto

