# Requisitos: Quorum Dinámico del EventEngine

## Objetivo

El quorum del EventEngine debe ser dinámico y dependiente del número de checkers realmente disponibles y saludables, no un valor fijo hardcodeado.

---

## Requisitos Obligatorios

### 1. Detección de Checkers Disponibles y Saludables

El sistema debe detectar en tiempo real:

- **Checkers activos:** Checkers con `enabled = true` en la base de datos
- **Checkers saludables:** Checkers que cumplen:
  - Han respondido exitosamente en las últimas N ejecuciones (configurable)
  - Su latencia está dentro de límites aceptables
  - No están en estado de error persistente
  - No han excedido `checker_max_failures` consecutivos

**Implementación:**
- Crear `CheckerHealthService` que rastrea estado de cada checker
- Mantener historial de últimas ejecuciones por checker
- Calcular salud basado en ventana de tiempo configurable

### 2. Cálculo del Quorum Efectivo

El quorum requerido debe calcularse como función de:

**Parámetros de configuración:**
- `quorum_base` (int): Quorum base configurado (ej. 2)
- `allow_single_checker` (bool): Permitir quorum de 1 si solo hay 1 checker disponible
- `allow_zero_checker` (bool): **Permitir que el sistema siga funcionando sin checkers, pero SIN confirmar FINISHED y SIN trading**

**🔴 Semántica Correcta de `allow_zero_checker`:**
- `allow_zero_checker = true`: 
  - Sistema sigue evaluando mercados
  - Produce decision_traces
  - **NUNCA entra (NO TRADING)**
  - **NUNCA confirma FINISHED_CONFIRMED**
  - Event state = UNKNOWN
  
- `allow_zero_checker = false`:
  - Sistema se pone en estado DEGRADED/PAUSED
  - No evalúa mercados
  - No produce decision_traces

**Fórmula:**
```python
checkers_saludables = get_healthy_checkers(category)
checkers_disponibles = len(checkers_saludables)

# 🔴 REGLA CRÍTICA: Con 0 checkers, NUNCA confirmar FINISHED
if checkers_disponibles == 0:
    if allow_zero_checker:
        # Sistema sigue vivo pero sin trading
        event_state = "UNKNOWN"
        quorum_efectivo = None  # No hay quorum posible
        trading_permitido = False
        # Sistema produce decision_traces pero NO entra
    else:
        # Sistema en estado DEGRADED/PAUSED
        event_state = "UNKNOWN"
        quorum_efectivo = None
        trading_permitido = False
        # Sistema NO evalúa mercados
        system_status = "DEGRADED"
elif checkers_disponibles == 1:
    if allow_single_checker:
        quorum_efectivo = 1
    else:
        quorum_efectivo = min(quorum_base, checkers_disponibles)  # Puede ser 1 si quorum_base es 1
else:
    quorum_efectivo = min(quorum_base, checkers_disponibles)
```

**Ejemplos:**
- `quorum_base = 2`, `checkers_disponibles = 3` → `quorum_efectivo = 2`, `FINISHED_CONFIRMED` posible
- `quorum_base = 2`, `checkers_disponibles = 1`, `allow_single_checker = true` → `quorum_efectivo = 1`, `FINISHED_UNCONFIRMED` posible
- `quorum_base = 2`, `checkers_disponibles = 1`, `allow_single_checker = false` → `quorum_efectivo = 1` (pero con advertencia)
- `quorum_base = 2`, `checkers_disponibles = 0`, `allow_zero_checker = true` → `event_state = UNKNOWN`, `NO TRADING`, sistema sigue vivo
- `quorum_base = 2`, `checkers_disponibles = 0`, `allow_zero_checker = false` → `event_state = UNKNOWN`, `NO TRADING`, sistema en `DEGRADED`

### 3. Explicabilidad en Frontend

El frontend debe mostrar claramente:

#### Dashboard Principal:
- **Checkers disponibles:** Lista de checkers activos y saludables por categoría
- **Checkers no disponibles:** Lista de checkers inactivos o no saludables
- **Quorum configurado:** Valor de `quorum_base`
- **Quorum efectivo actual:** Valor calculado basado en checkers disponibles

#### Página de Eventos:
- **Quorum usado en decisión:** Quorum efectivo usado para cada decisión
- **Checkers usados:** Qué checkers participaron en la decisión
- **Razón de decisión:** Explicación clara de por qué un evento fue confirmado o no
  - Ejemplo: "Confirmado: 2 de 2 checkers disponibles (quorum requerido: 2)"
  - Ejemplo: "No confirmado: Solo 1 de 2 checkers disponibles (quorum requerido: 2, allow_single_checker: false)"

#### Página de Checkers:
- Estado de salud de cada checker
- Última ejecución exitosa
- Número de fallos consecutivos
- Latencia promedio
- Si está considerado "saludable" o no

### 4. Sin Valores Hardcodeados

**NO se permiten:**
- Valores hardcodeados como `>= 2` o `>= 1`
- Quorum implícito
- Lógica que no sea explicable desde el frontend

**DEBE ser:**
- Todo configurable desde frontend
- Todo explicable en decision_trace
- Todo visible en el frontend

---

## Código Actual con Violaciones

### ❌ Violación 1: EventEngine (`backend/app/core/event_engine.py`)

**Línea 97-100:**
```python
# Quorum rule: >= 2 checkers with FINISHED and confidence >= min
if finished_count >= 2:  # ❌ HARDCODEADO
    return ("FINISHED_CONFIRMED", avg_confidence)
elif finished_count == 1:  # ❌ HARDCODEADO
    return ("FINISHED_UNCONFIRMED", avg_confidence)
```

**Problemas:**
- Quorum fijo de 2, no considera checkers disponibles
- No detecta si hay checkers no saludables
- No es configurable
- No es explicable

**Solución:**
```python
# Obtener checkers saludables disponibles
healthy_checkers = checker_health_service.get_healthy_checkers(category)
available_count = len(healthy_checkers)

# 🔴 REGLA CRÍTICA: Con 0 checkers, NUNCA confirmar FINISHED
if available_count == 0:
    if config.allow_zero_checker:
        # Sistema sigue vivo pero sin trading
        return ("UNKNOWN", 0.0, {
            "reason": "no_checkers_available_allow_zero",
            "quorum_required": config.quorum_base,
            "checkers_available": 0,
            "trading_permitted": False,
            "system_status": "OPERATIONAL_NO_TRADING"
        })
    else:
        # Sistema en estado DEGRADED
        return ("UNKNOWN", 0.0, {
            "reason": "no_checkers_available_system_degraded",
            "quorum_required": config.quorum_base,
            "checkers_available": 0,
            "trading_permitted": False,
            "system_status": "DEGRADED"
        })

# Calcular quorum efectivo (solo si hay checkers disponibles)
quorum_effective = calculate_effective_quorum(
    quorum_base=config.quorum_base,
    available_checkers=available_count,
    allow_single_checker=config.allow_single_checker
)

# Aplicar quorum dinámico
if finished_count >= quorum_effective:
    return ("FINISHED_CONFIRMED", avg_confidence, {
        "quorum_used": quorum_effective,
        "quorum_required": config.quorum_base,
        "checkers_available": available_count,
        "checkers_used": finished_count
    })
```

### ❌ Violación 2: StateAggregator (`backend/app/core/event_watch_engine/state_aggregator.py`)

**Línea 128:**
```python
if len(high_confidence_finished) >= self.config.min_checkers_for_confirmed:  # ⚠️ No es dinámico
```

**Problemas:**
- Usa `min_checkers_for_confirmed` del config, pero NO considera checkers disponibles
- No detecta checkers saludables vs no saludables
- No calcula quorum efectivo

**Solución:**
- Pasar lista de checkers saludables disponibles al método
- Calcular quorum efectivo antes de comparar
- Incluir información de quorum en EventState

### ❌ Violación 3: WatchEngineConfig (`backend/app/core/event_watch_engine/models.py`)

**Línea 104:**
```python
min_checkers_for_confirmed: int = 2  # ❌ Valor por defecto hardcodeado
```

**Problemas:**
- Valor por defecto hardcodeado
- No hay flags para `allow_single_checker` o `allow_zero_checker`

**Solución:**
- Cambiar a `quorum_base: int = 2`
- Agregar `allow_single_checker: bool = False`
- Agregar `allow_zero_checker: bool = False`
- Agregar `checker_health_window_seconds: int = 300`
- Agregar `checker_max_failures: int = 3`

---

## Implementación Requerida

### 1. Crear CheckerHealthService

**Archivo:** `backend/app/core/checkers/health_service.py`

```python
class CheckerHealthService:
    def get_healthy_checkers(self, category: str) -> List[Checker]:
        """Obtiene checkers saludables para una categoría."""
        
    def is_checker_healthy(self, checker_id: UUID) -> bool:
        """Verifica si un checker está saludable."""
        
    def record_checker_result(self, checker_id: UUID, success: bool, latency_ms: float):
        """Registra resultado de ejecución de checker."""
```

### 2. Modificar StateAggregator

**Agregar:**
- Parámetro `healthy_checkers: List[Checker]` al método `aggregate()`
- Cálculo de quorum efectivo
- Incluir en EventState: `quorum_used`, `checkers_available`, `checkers_used`, `quorum_reason`

### 3. Modificar EventEngine

**Eliminar:**
- Hardcoded `>= 2` y `>= 1`
- Lógica fija de quorum

**Agregar:**
- Uso de CheckerHealthService
- Cálculo de quorum efectivo
- Información de quorum en decision_trace

### 4. Agregar a system_config

**Nuevos parámetros:**
- `quorum_base` (int, default: 2) - Quorum base configurado
- `allow_single_checker` (bool, default: false) - Permitir quorum de 1
- `allow_zero_checker` (bool, default: false) - **Permitir sistema operativo sin checkers (sin trading)**
- `checker_health_window_seconds` (int, default: 300) - Ventana de tiempo para considerar saludable
- `checker_max_failures` (int, default: 3) - Máximo de fallos consecutivos

**🔴 Descripción de `allow_zero_checker` en DB:**
```
"Permite que el sistema siga funcionando cuando no hay checkers disponibles. 
El sistema evaluará mercados y producirá decision_traces, pero NUNCA confirmará 
FINISHED_CONFIRMED y NUNCA realizará trading. Si es false, el sistema entrará 
en estado DEGRADED y no evaluará mercados."
```

### 5. Endpoints del Frontend

**GET** `/api/checkers/health`
- Estado de salud de todos los checkers
- Checkers disponibles vs no disponibles
- Quorum efectivo actual

**GET** `/api/events/{event_id}/quorum`
- Quorum usado en última decisión
- Checkers que participaron
- Razón de la decisión

---

## Validación

El quorum será dinámico cuando:

- [ ] No hay valores hardcodeados `>= 2` o `>= 1`
- [ ] Se detecta en tiempo real checkers saludables
- [ ] Quorum efectivo se calcula basado en checkers disponibles
- [ ] Flags `allow_single_checker` y `allow_zero_checker` funcionan
- [ ] Frontend muestra checkers disponibles, quorum configurado, quorum efectivo
- [ ] Frontend explica por qué un evento fue confirmado o no
- [ ] Decision traces incluyen información completa de quorum

