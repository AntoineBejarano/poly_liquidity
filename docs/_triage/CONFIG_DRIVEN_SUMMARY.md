# Resumen Ejecutivo: Transformación Config-Driven

## 🎯 Objetivo

Transformar el sistema de código-driven a config-driven, permitiendo que TODOS los parámetros operativos sean configurables desde el frontend sin modificar código.

---

## ⚠️ REQUISITO CRÍTICO: Quorum Dinámico del EventEngine

**ANTES DE EMPEZAR:** El quorum del EventEngine debe ser dinámico y dependiente del número de checkers realmente disponibles y saludables.

### Lógica Actual con Quorum Fijo (A ELIMINAR):

**❌ Violaciones encontradas:**

1. **`backend/app/core/event_engine.py` línea 97:**
   ```python
   if finished_count >= 2:  # ❌ HARDCODEADO
       return ("FINISHED_CONFIRMED", avg_confidence)
   elif finished_count == 1:  # ❌ HARDCODEADO
       return ("FINISHED_UNCONFIRMED", avg_confidence)
   ```

2. **`backend/app/core/event_watch_engine/state_aggregator.py` línea 128:**
   ```python
   if len(high_confidence_finished) >= self.config.min_checkers_for_confirmed:  # ⚠️ No es dinámico
   ```
   - Usa config pero NO considera checkers disponibles/saludables

3. **`backend/app/core/event_watch_engine/models.py` línea 104:**
   ```python
   min_checkers_for_confirmed: int = 2  # ❌ Valor por defecto hardcodeado
   ```

### Refactorización Necesaria:

1. **Crear CheckerHealthService:**
   - Rastrear estado de cada checker (saludable/no saludable)
   - Método `get_healthy_checkers(category: str) -> List[Checker]`

2. **Quorum Dinámico:**
   - **🔴 REGLA CRÍTICA:** Con 0 checkers, NUNCA confirmar FINISHED_CONFIRMED
   - Calcular: `quorum_efectivo = min(quorum_base, checkers_saludables_disponibles)` (solo si hay checkers)
   - Respetar flags: `allow_single_checker`, `allow_zero_checker`
   - `allow_zero_checker = true`: Sistema sigue vivo pero sin trading (event_state = UNKNOWN)
   - `allow_zero_checker = false`: Sistema en estado DEGRADED/PAUSED
   - Incluir en EventState: `quorum_used`, `checkers_available`, `quorum_reason`, `trading_permitted`

3. **Explicabilidad:**
   - Frontend debe mostrar: checkers disponibles, quorum configurado, quorum efectivo usado, razón de decisión

---

---

## 📋 Checklist de Implementación

### 1. Migraciones Necesarias ✅ CREADAS

- [x] **005_improve_system_config.py** - Mejora tabla system_config
- [x] **006_create_checker_config.py** - Crea tabla checker_config
- [x] **007_create_execution_session.py** - Crea tabla execution_session
- [x] **008_create_decision_trace.py** - Crea tabla decision_trace

**Estado:** Migraciones creadas, pendiente ejecución

---

## 2. Código a Refactorizar

### 2.1 Strategy Engine (`backend/app/core/strategy/strategy.py`)

**Parámetros hardcodeados a eliminar:**
- `max_entry_spread = risk_config.target_margin * 20` (línea 175)
- `latency_mode = "GREEN"` (línea 181)
- `aggressive_mode = False` (línea 182) - Ya no se usa pero debe ser configurable
- `min_liquidity_required` - No existe en StrategyConfig
- Multiplicadores: `safety_tick_multiplier_yellow = 2.0`, `safety_tick_multiplier_red = 3.0`
- `yellow_latency_size_factor = 0.5`

**Acciones:**
1. Crear `StrategyConfig` completo en ConfigService
2. Obtener TODOS los parámetros desde DB
3. Agregar logging de decisiones con `decision_trace`
4. Respetar `execution_mode` (no crear órdenes reales en DRY_RUN)

### 2.2 Risk Engine (`backend/app/core/risk_engine/risk_engine.py`)

**Parámetros hardcodeados a eliminar:**
- `min_order_size = 100.0` (línea 51)
- `latency_fail_mode = "strict"` (línea 52)
- `reduce_size_in_yellow = True` (línea 53)
- `yellow_size_factor = 0.5` (línea 54)
- `cancel_on_red = True` (línea 55)
- `exposure_method = "notional"` (línea 56)
- `max_price_swing_pct = 0.05` (línea 57)
- `max_swing_time_seconds = 10.0` (línea 58)
- `min_realistic_spread = 0.001` (línea 59)

**Acciones:**
1. Obtener TODOS los parámetros desde ConfigService
2. Agregar logging de decisiones con `decision_trace`
3. Respetar `execution_mode`

### 2.3 Scanner (`backend/app/core/scanner/scanner.py`)

**Parámetros hardcodeados a eliminar:**
- `min_price_threshold`
- `allowed_categories = ["sports"]`
- `allowed_subcategories = []`
- Filtros de volumen/liquidez

**Acciones:**
1. Crear `ScannerConfig` model
2. Obtener TODOS los parámetros desde ConfigService
3. Agregar logging de decisiones con `decision_trace`

### 2.4 Event Engine (`backend/app/core/event_engine.py`)

**Parámetros hardcodeados a eliminar:**
- `min_checkers_for_confirmed = 2` (hardcodeado en StateAggregator) - **CRÍTICO: DEBE SER DINÁMICO**
- `category = "sports"` (línea 199)
- **❌ CRÍTICO:** Quorum hardcodeado `>= 2` y `>= 1` (líneas 97, 99)

**Acciones:**
1. Crear `EventEngineConfig` model
2. Obtener TODOS los parámetros desde ConfigService
3. **CRÍTICO:** Implementar quorum dinámico basado en checkers saludables
4. Crear `CheckerHealthService` para rastrear estado de checkers
5. Eliminar hardcoded `>= 2` y `>= 1`
6. Agregar logging de decisiones con `decision_trace` incluyendo quorum usado

### 2.5 Execution Engine (`backend/app/core/execution/execution.py`)

**Parámetros hardcodeados a eliminar:**
- `max_poll_attempts = 720`
- `poll_interval_seconds`
- `order_timeout_seconds`
- `retry_on_failure = True`
- `max_retries = 3`

**Acciones:**
1. Obtener TODOS los parámetros desde ConfigService
2. Implementar modos de ejecución:
   - **DRY_RUN**: Solo loggear, no enviar órdenes
   - **PAPER**: Enviar a wallet de paper trading
   - **LIVE**: Enviar órdenes reales
3. Crear `execution_session` al iniciar
4. Agregar logging de decisiones con `decision_trace`

### 2.6 ConfigService (`backend/app/core/config_service.py`)

**Mejoras necesarias:**
1. Implementar hot reload (polling cada 5-10 segundos)
2. Agregar métodos por componente:
   - `get_strategy_config() -> StrategyConfig`
   - `get_risk_config() -> RiskConfig`
   - `get_scanner_config() -> ScannerConfig`
   - `get_event_engine_config() -> EventEngineConfig`
   - `get_execution_config() -> ExecutionConfig`
3. Agregar `get_execution_mode() -> str`
4. Agregar validación según min/max values

---

## 3. Endpoints del Frontend

### 3.1 Configuración

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config` | Obtener toda la configuración agrupada por categoría |
| GET | `/api/config/{category}` | Obtener configuración de una categoría |
| PUT | `/api/config/{key}` | Actualizar un parámetro (requiere confirmation_token si `requires_confirmation = true`) |
| GET | `/api/config/execution-mode` | Obtener modo de ejecución actual |
| PUT | `/api/config/execution-mode` | Cambiar modo de ejecución (requiere confirmation_token para LIVE) |

**⚠️ Protección de Parámetros:**
- Parámetros con `is_readonly = true` no pueden ser modificados
- Parámetros con `requires_confirmation = true` requieren `confirmation_token` en el request

### 3.2 Decision Traces

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/traces` | Listar traces con filtros |
| GET | `/api/traces/{trace_id}` | Obtener trace específico |
| GET | `/api/traces/summary` | Resumen de decisiones |

### 3.3 Execution Sessions

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/sessions` | Listar sesiones |
| GET | `/api/sessions/{session_id}` | Obtener sesión específica |
| POST | `/api/sessions` | Crear nueva sesión |
| PUT | `/api/sessions/{session_id}/status` | Cambiar estado de sesión |

### 3.4 Checker Configuration

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/checkers/{checker_id}/config` | Obtener configuración de checker |
| PUT | `/api/checkers/{checker_id}/config/{key}` | Actualizar configuración |

---

## 4. Información para Explicar Comportamiento del Bot

### 4.1 Decision Traces (Completo)

Cada decisión debe incluir:

1. **Input Data:**
   - Market state (precio, spread, liquidez)
   - Event state (estado, confianza, fuentes)
   - Exposure state (exposición actual, límites)
   - Latency status
   - Runtime mode

2. **Config Used:**
   - TODOS los parámetros de configuración usados
   - Valores específicos de Strategy, Risk, Scanner, etc.
   - Execution mode

3. **Output Data:**
   - Decisión tomada (APPROVED/REJECTED/ADJUSTED)
   - Razón de la decisión
   - Ajustes aplicados (si los hay)
   - Order intent generado (si aplica)

4. **Métricas:**
   - Latency de la decisión
   - Confidence score
   - Timestamp preciso

### 4.2 Estado de Checkers

Para explicar por qué un evento está en cierto estado:

- Checkers activos por categoría
- Último resultado de cada checker
- Confianza de cada checker
- Tiempo desde última ejecución
- Tasa de éxito/fallo
- Configuración específica de cada checker

### 4.3 Estado de Riesgo

Para explicar límites y exposiciones:

- Exposición actual vs límites configurados
- Mercados activos vs máximo permitido
- Órdenes pendientes
- Brechas de límites (si las hay)
- Historial de ajustes de tamaño

### 4.4 Latencia del Sistema

Para explicar decisiones conservadoras:

- Latencia actual (GREEN/YELLOW/RED)
- Latencia histórica (últimas 24h)
- Componentes más lentos
- Impacto en decisiones (multiplicadores aplicados)

### 4.5 Modo de Ejecución

Para explicar comportamiento:

- Modo actual (DRY_RUN/PAPER/LIVE) - **MUY VISIBLE**
- Sesión activa
- Configuración snapshot al inicio de sesión
- Cambios de configuración durante sesión

---

## 5. Priorización de Implementación

### Fase 1: Crítica (Semana 1)
1. ✅ Crear migraciones
2. Mejorar ConfigService con hot reload
3. Refactorizar Strategy y Risk (parámetros más críticos)
4. Implementar execution_mode básico

### Fase 2: Importante (Semana 2)
1. Refactorizar Scanner y Event Engine
2. Refactorizar Execution Engine
3. Implementar decision_trace básico
4. Crear endpoints de configuración

### Fase 3: Completar (Semana 3)
1. Completar decision_trace en todos los componentes
2. Crear endpoints de traces y sessions
3. Frontend: Página de configuración
4. Frontend: Página de decision traces

### Fase 4: Pulir (Semana 4)
1. Frontend: Dashboard mejorado
2. Tests completos
3. Documentación
4. Validación final

---

## 6. Validación Final

El sistema será config-driven cuando:

- [ ] No hay parámetros hardcodeados en Strategy, Risk, Scanner, EventEngine, Execution
- [ ] Todos los parámetros son configurables desde frontend
- [ ] Parámetros críticos están protegidos (`is_readonly` o `requires_confirmation`)
- [ ] ConfigService tiene hot reload funcionando
- [ ] Modos de ejecución (DRY_RUN/PAPER/LIVE) funcionan correctamente
- [ ] Decision traces se generan para todas las decisiones con `decision_stage`
- [ ] `input_data` en decision_trace está ACOTADO (no orderbooks completos)
- [ ] Frontend muestra información completa del comportamiento del bot
- [ ] Frontend muestra timeline usando `decision_stage`
- [ ] No se requiere modificar código para ajustes operativos
- [ ] Migraciones ejecutadas y funcionando
- [ ] Quorum dinámico implementado y funcionando

---

## 📝 Notas Importantes

1. **Execution Mode debe ser MUY visible** en el frontend - es crítico que el usuario sepa si está en LIVE
2. **Decision traces son esenciales** para explicabilidad - cada decisión debe ser rastreable
3. **Hot reload** debe ser eficiente - no bloquear el sistema
4. **Validación** de parámetros debe ser robusta - evitar configuraciones peligrosas
5. **Backward compatibility** - valores por defecto deben ser seguros

