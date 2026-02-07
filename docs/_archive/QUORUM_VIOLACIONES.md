# Violaciones de Quorum Hardcodeado - Análisis Completo

## Resumen

Se encontraron **3 violaciones críticas** donde el quorum está hardcodeado o no es dinámico basado en checkers disponibles y saludables.

---

## ❌ Violación 1: EventEngine - Quorum Hardcodeado

**Archivo:** `backend/app/core/event_engine.py`  
**Líneas:** 96-100

**Código actual:**
```python
# Quorum rule: >= 2 checkers with FINISHED and confidence >= min
if finished_count >= 2:  # ❌ HARDCODEADO
    return ("FINISHED_CONFIRMED", avg_confidence)
elif finished_count == 1:  # ❌ HARDCODEADO
    return ("FINISHED_UNCONFIRMED", avg_confidence)
else:
    return ("LIVE", avg_confidence)
```

**Problemas:**
1. Quorum fijo de `>= 2` - no considera checkers disponibles
2. No detecta si hay checkers no saludables
3. No es configurable desde frontend
4. No es explicable - no se puede saber por qué se tomó la decisión
5. No respeta flags `allow_single_checker` o `allow_zero_checker`

**Impacto:** CRÍTICO - El sistema no puede adaptarse cuando hay menos checkers disponibles

---

## ⚠️ Violación 2: StateAggregator - Quorum No Dinámico

**Archivo:** `backend/app/core/event_watch_engine/state_aggregator.py`  
**Líneas:** 127-130

**Código actual:**
```python
# FINISHED_CONFIRMED: 2+ checkers con alta confianza dicen FINISHED
if len(high_confidence_finished) >= self.config.min_checkers_for_confirmed:  # ⚠️ No es dinámico
    confidence = self._calculate_weighted_confidence(high_confidence_finished)
    return EventStateType.FINISHED_CONFIRMED, confidence
```

**Problemas:**
1. Usa `min_checkers_for_confirmed` del config, pero NO considera checkers disponibles
2. No detecta checkers saludables vs no saludables
3. No calcula quorum efectivo basado en disponibilidad real
4. No incluye información de quorum en EventState para explicabilidad

**Impacto:** ALTO - Aunque usa config, no es dinámico basado en checkers reales

---

## ❌ Violación 3: WatchEngineConfig - Valor Por Defecto Hardcodeado

**Archivo:** `backend/app/core/event_watch_engine/models.py`  
**Línea:** 104

**Código actual:**
```python
class WatchEngineConfig(BaseModel):
    # ...
    # Reglas de quorum
    min_checkers_for_confirmed: int = 2  # ❌ Valor por defecto hardcodeado
    min_confidence_threshold: float = 0.8
```

**Problemas:**
1. Valor por defecto hardcodeado de `2`
2. No hay flags para `allow_single_checker` o `allow_zero_checker`
3. No hay parámetros para salud de checkers (`checker_health_window_seconds`, `checker_max_failures`)

**Impacto:** MEDIO - Aunque es configurable, falta funcionalidad para quorum dinámico

---

## ❌ Violación 4: Lógica Implícita de Quorum

**Archivo:** `backend/app/core/event_watch_engine/state_aggregator.py`  
**Líneas:** 135-141

**Código actual:**
```python
if len(high_confidence_finished) == 1:  # ⚠️ Lógica implícita
    confidence = high_confidence_finished[0].confidence
    return EventStateType.FINISHED_UNCONFIRMED, confidence
elif len(finished_all) >= 2:  # ⚠️ Lógica implícita
    # 2+ checkers dicen FINISHED pero con confianza < threshold
    confidence = self._calculate_weighted_confidence(finished_all)
    return EventStateType.FINISHED_UNCONFIRMED, confidence
```

**Problemas:**
1. Lógica implícita de `== 1` y `>= 2` sin considerar checkers disponibles
2. No explica por qué se tomó la decisión
3. No respeta flags de configuración

**Impacto:** MEDIO - Lógica no explicable

---

## Solución Requerida

### 1. Crear CheckerHealthService

**Nuevo archivo:** `backend/app/core/checkers/health_service.py`

**Responsabilidades:**
- Rastrear estado de salud de cada checker
- Detectar checkers disponibles y saludables
- Calcular métricas de salud (fallos consecutivos, latencia, etc.)

### 2. Modificar EventEngine

**Cambios:**
- Eliminar hardcoded `>= 2` y `>= 1`
- Obtener checkers saludables disponibles
- Calcular quorum efectivo dinámicamente
- Incluir información de quorum en respuesta

### 3. Modificar StateAggregator

**Cambios:**
- Agregar parámetro `healthy_checkers: List[Checker]`
- Calcular quorum efectivo antes de comparar
- Incluir en EventState: `quorum_used`, `checkers_available`, `checkers_used`, `quorum_reason`

### 4. Actualizar WatchEngineConfig

**Agregar:**
- `quorum_base: int = 2` (reemplaza `min_checkers_for_confirmed`)
- `allow_single_checker: bool = False` - Permitir quorum de 1
- `allow_zero_checker: bool = False` - **Permitir sistema operativo sin checkers (sin trading)**
- `checker_health_window_seconds: int = 300` - Ventana de tiempo para considerar saludable
- `checker_max_failures: int = 3` - Máximo de fallos consecutivos

**🔴 Semántica de `allow_zero_checker`:**
- `true`: Sistema sigue funcionando, evalúa mercados, produce decision_traces, pero **NUNCA confirma FINISHED** y **NUNCA hace trading**
- `false`: Sistema entra en estado DEGRADED/PAUSED, no evalúa mercados

### 5. Agregar a system_config

**Nuevos parámetros:**
- `quorum_base` (int, category: "event_engine")
- `allow_single_checker` (bool, category: "event_engine")
- `allow_zero_checker` (bool, category: "event_engine")
- `checker_health_window_seconds` (int, category: "event_engine")
- `checker_max_failures` (int, category: "event_engine")

### 6. Endpoints del Frontend

**GET** `/api/checkers/health`
- Estado de salud de todos los checkers
- Checkers disponibles vs no disponibles
- Quorum efectivo actual

**GET** `/api/events/{event_id}/quorum`
- Quorum usado en última decisión
- Checkers que participaron
- Razón de la decisión

---

## Checklist de Validación

- [ ] No hay valores hardcodeados `>= 2` o `>= 1` en EventEngine
- [ ] No hay valores hardcodeados `>= 2` o `>= 1` en StateAggregator
- [ ] Se detecta en tiempo real checkers saludables
- [ ] Quorum efectivo se calcula basado en checkers disponibles
- [ ] Flags `allow_single_checker` y `allow_zero_checker` funcionan
- [ ] Frontend muestra checkers disponibles
- [ ] Frontend muestra quorum configurado
- [ ] Frontend muestra quorum efectivo usado
- [ ] Frontend explica por qué un evento fue confirmado o no
- [ ] Decision traces incluyen información completa de quorum
- [ ] CheckerHealthService implementado y funcionando

---

## Prioridad

**CRÍTICA** - Debe implementarse ANTES de la refactorización config-driven, ya que afecta la lógica core del EventEngine.

