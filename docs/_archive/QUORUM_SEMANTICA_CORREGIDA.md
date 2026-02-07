# Corrección Semántica: allow_zero_checker

## 🔴 Corrección Conceptual Crítica

### Error Original (PELIGROSO)

```python
Si allow_zero_checker = true y checkers_disponibles = 0:
    quorum_efectivo = 0 (modo degradado, no confirmar FINISHED)
```

**Problema:** Esta semántica puede inducir a un bug conceptual peligroso donde se interprete que con 0 checkers se puede confirmar FINISHED.

---

## ✅ Semántica Correcta

### Regla Crítica

**Con 0 checkers, el sistema NUNCA debe emitir `FINISHED_CONFIRMED`.**

### Semántica de `allow_zero_checker`

#### `allow_zero_checker = true`

**Significa:** Permitir que el sistema siga funcionando sin checkers, pero **SIN confirmar FINISHED** y **SIN trading**.

**Comportamiento:**
- ✅ Sistema sigue evaluando mercados
- ✅ Produce decision_traces
- ✅ Mantiene estado operativo
- ❌ **NUNCA entra (NO TRADING)**
- ❌ **NUNCA confirma FINISHED_CONFIRMED**
- ❌ Event state = `UNKNOWN` (nunca `FINISHED_CONFIRMED`)

**Código:**
```python
if checkers_disponibles == 0:
    if allow_zero_checker:
        event_state = "UNKNOWN"
        trading_permitted = False
        system_status = "OPERATIONAL_NO_TRADING"
        # Sistema produce decision_traces pero NO entra
```

#### `allow_zero_checker = false`

**Significa:** Si no hay checkers, el sistema entra en estado DEGRADED/PAUSED.

**Comportamiento:**
- ❌ Sistema se pone en estado `DEGRADED` / `PAUSED`
- ❌ No evalúa mercados
- ❌ No produce decision_traces
- ❌ No trading

**Código:**
```python
if checkers_disponibles == 0:
    if not allow_zero_checker:
        event_state = "UNKNOWN"
        trading_permitted = False
        system_status = "DEGRADED"
        # Sistema NO evalúa mercados
```

---

## Fórmula Corregida

```python
checkers_saludables = get_healthy_checkers(category)
checkers_disponibles = len(checkers_saludables)

# 🔴 REGLA CRÍTICA: Con 0 checkers, NUNCA confirmar FINISHED
if checkers_disponibles == 0:
    if allow_zero_checker:
        # Sistema sigue vivo pero sin trading
        event_state = "UNKNOWN"
        quorum_efectivo = None  # No hay quorum posible
        trading_permitted = False
        system_status = "OPERATIONAL_NO_TRADING"
        # Sistema produce decision_traces pero NO entra
    else:
        # Sistema en estado DEGRADED/PAUSED
        event_state = "UNKNOWN"
        quorum_efectivo = None
        trading_permitted = False
        system_status = "DEGRADED"
        # Sistema NO evalúa mercados
        # Sistema NO produce decision_traces

elif checkers_disponibles == 1:
    if allow_single_checker:
        quorum_efectivo = 1
        # Puede confirmar FINISHED_UNCONFIRMED
    else:
        quorum_efectivo = min(quorum_base, checkers_disponibles)
        # Puede confirmar FINISHED_UNCONFIRMED si quorum_base es 1

else:  # checkers_disponibles >= 2
    quorum_efectivo = min(quorum_base, checkers_disponibles)
    # Puede confirmar FINISHED_CONFIRMED si finished_count >= quorum_efectivo
```

---

## Ejemplos de Comportamiento

### Ejemplo 1: allow_zero_checker = true, 0 checkers

**Input:**
- `checkers_disponibles = 0`
- `allow_zero_checker = true`
- `quorum_base = 2`

**Output:**
- `event_state = "UNKNOWN"`
- `quorum_efectivo = None`
- `trading_permitted = False`
- `system_status = "OPERATIONAL_NO_TRADING"`
- Sistema evalúa mercados pero NO entra
- Sistema produce decision_traces

### Ejemplo 2: allow_zero_checker = false, 0 checkers

**Input:**
- `checkers_disponibles = 0`
- `allow_zero_checker = false`
- `quorum_base = 2`

**Output:**
- `event_state = "UNKNOWN"`
- `quorum_efectivo = None`
- `trading_permitted = False`
- `system_status = "DEGRADED"`
- Sistema NO evalúa mercados
- Sistema NO produce decision_traces

### Ejemplo 3: allow_single_checker = true, 1 checker

**Input:**
- `checkers_disponibles = 1`
- `allow_single_checker = true`
- `quorum_base = 2`
- `finished_count = 1`

**Output:**
- `quorum_efectivo = 1`
- `event_state = "FINISHED_UNCONFIRMED"` (si el checker dice FINISHED)
- `trading_permitted = True` (pero con tamaño reducido)

### Ejemplo 4: allow_single_checker = false, 1 checker

**Input:**
- `checkers_disponibles = 1`
- `allow_single_checker = false`
- `quorum_base = 2`
- `finished_count = 1`

**Output:**
- `quorum_efectivo = 1` (min(2, 1) = 1)
- `event_state = "FINISHED_UNCONFIRMED"` (pero con advertencia)
- `trading_permitted = True` (pero con tamaño reducido y advertencia)

---

## Validación

La semántica es correcta cuando:

- [ ] Con 0 checkers, NUNCA se emite `FINISHED_CONFIRMED`
- [ ] Con 0 checkers y `allow_zero_checker = true`, sistema sigue funcionando pero sin trading
- [ ] Con 0 checkers y `allow_zero_checker = false`, sistema entra en estado DEGRADED
- [ ] Frontend muestra claramente que no hay trading cuando hay 0 checkers
- [ ] Decision traces explican por qué no se puede confirmar FINISHED
- [ ] No hay ambigüedad sobre el comportamiento con 0 checkers

---

## Impacto en Código

### EventEngine

**Debe verificar:**
```python
if checkers_disponibles == 0:
    # NUNCA confirmar FINISHED_CONFIRMED
    if allow_zero_checker:
        return ("UNKNOWN", 0.0, {
            "trading_permitted": False,
            "system_status": "OPERATIONAL_NO_TRADING"
        })
    else:
        return ("UNKNOWN", 0.0, {
            "trading_permitted": False,
            "system_status": "DEGRADED"
        })
```

### Strategy Engine

**Debe verificar:**
```python
if event_state.trading_permitted == False:
    # NO crear order intents
    return []
```

### Frontend

**Debe mostrar:**
- Estado del sistema: "OPERATIONAL_NO_TRADING" o "DEGRADED"
- Advertencia clara: "No hay checkers disponibles - Trading deshabilitado"
- Razón: "0 checkers disponibles, quorum requerido: 2"

