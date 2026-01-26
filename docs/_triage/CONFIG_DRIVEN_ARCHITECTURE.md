# Arquitectura Config-Driven - Diseño Completo

## Objetivo

Transformar el sistema de código-driven a config-driven, permitiendo que TODOS los parámetros operativos sean configurables desde el frontend sin necesidad de modificar código.

---

## ⚠️ REQUISITO CRÍTICO: Quorum Dinámico del EventEngine

**ANTES DE EMPEZAR:** El quorum del EventEngine debe ser dinámico y dependiente del número de checkers realmente disponibles y saludables.

### Requisitos del Quorum Dinámico:

1. **Detección en Tiempo Real:**
   - El sistema debe detectar cuántos checkers están activos y saludables en tiempo real
   - Un checker se considera "saludable" si:
     - Está habilitado (`enabled = true`)
     - Ha respondido exitosamente en las últimas N ejecuciones (configurable)
     - Su latencia está dentro de límites aceptables
     - No está en estado de error persistente

2. **Cálculo del Quorum Efectivo:**
   - El quorum requerido debe calcularse como función de:
     - `quorum_configurado`: Valor base configurado (ej. 2)
     - `checkers_disponibles`: Número real de checkers saludables disponibles
     - `allow_single_checker`: Flag que permite quorum de 1 si solo hay 1 checker disponible
     - `allow_zero_checker`: Flag que permite operar sin checkers (modo degradado)
   
   **Fórmula:**
   ```
   Si checkers_disponibles = 0:
       Si allow_zero_checker = true:
           ⇒ EVENT_STATE = UNKNOWN
           ⇒ NO TRADING (sistema sigue vivo pero sin entradas)
           ⇒ Produce decision_traces
       Si allow_zero_checker = false:
           ⇒ Sistema en estado DEGRADED/PAUSED
           ⇒ No evaluar mercados
   
   Si checkers_disponibles = 1:
       Si allow_single_checker = true:
           quorum_efectivo = 1
       Si allow_single_checker = false:
           quorum_efectivo = min(quorum_base, checkers_disponibles)  # Puede ser 1 si quorum_base es 1
   
   Si checkers_disponibles >= 2:
       quorum_efectivo = min(quorum_configurado, checkers_disponibles)
   ```
   
   **🔴 REGLA CRÍTICA:**
   - Con 0 checkers, el sistema **NUNCA** debe emitir `FINISHED_CONFIRMED`
   - `allow_zero_checker = true` NO significa "confirmar sin checkers"
   - `allow_zero_checker = true` significa: "permitir que el sistema siga vivo, pero sin entradas"

3. **Explicabilidad en Frontend:**
   - El frontend debe mostrar claramente:
     - **Checkers disponibles:** Lista de checkers activos y saludables
     - **Quorum configurado:** Valor base configurado
     - **Quorum efectivo:** Valor real usado en cada decisión
     - **Razón de decisión:** Por qué un evento fue confirmado o no
     - **Checkers usados:** Qué checkers participaron en la decisión
     - **Checkers no disponibles:** Qué checkers están inactivos/fallando

4. **Sin Valores Hardcodeados:**
   - NO se permiten valores hardcodeados como `>= 2` o `>= 1`
   - NO se permite quorum implícito
   - TODO debe ser configurable y explicable

### Lógica Actual con Quorum Fijo (A ELIMINAR):

**❌ Violaciones encontradas:**

1. **`backend/app/core/event_engine.py` línea 97:**
   ```python
   # Quorum rule: >= 2 checkers with FINISHED and confidence >= min
   if finished_count >= 2:  # ❌ HARDCODEADO
       return ("FINISHED_CONFIRMED", avg_confidence)
   elif finished_count == 1:  # ❌ HARDCODEADO
       return ("FINISHED_UNCONFIRMED", avg_confidence)
   ```

2. **`backend/app/core/event_watch_engine/state_aggregator.py` línea 128:**
   ```python
   if len(high_confidence_finished) >= self.config.min_checkers_for_confirmed:  # ⚠️ Usa config pero no es dinámico
   ```
   - Usa `min_checkers_for_confirmed` del config, pero NO considera checkers disponibles
   - NO detecta checkers saludables vs no saludables

3. **`backend/app/core/event_watch_engine/models.py` línea 104:**
   ```python
   min_checkers_for_confirmed: int = 2  # ❌ Valor por defecto hardcodeado
   ```

### Refactorización Necesaria:

1. **Crear servicio de Checker Health:**
   - `CheckerHealthService` que rastrea estado de cada checker
   - Método `get_healthy_checkers(category: str) -> List[Checker]`
   - Método `is_checker_healthy(checker_id: UUID) -> bool`

2. **Modificar StateAggregator:**
   - Calcular quorum efectivo basado en checkers saludables
   - Incluir en EventState: `quorum_used`, `checkers_available`, `checkers_used`
   - Explicar por qué se tomó la decisión

3. **Modificar EventEngine:**
   - Eliminar hardcoded `>= 2` y `>= 1`
   - Usar quorum dinámico calculado
   - Incluir información de quorum en decision_trace

4. **Configuración necesaria:**
   - `quorum_base` (int): Quorum base configurado
   - `allow_single_checker` (bool): Permitir quorum de 1
   - `allow_zero_checker` (bool): Permitir modo degradado
   - `checker_health_window` (int): Ventana de tiempo para considerar saludable
   - `checker_max_failures` (int): Máximo de fallos consecutivos antes de considerar no saludable

---

---

## 1. Análisis de Parámetros Hardcodeados

### 1.1 Strategy Engine

**Archivo:** `backend/app/core/strategy/strategy.py`

**Parámetros hardcodeados encontrados:**
- `max_entry_spread = risk_config.target_margin * 20` (línea 175) - **DEBE SER CONFIGURABLE**
- `latency_mode = "GREEN"` (línea 181) - **DEBE SER CONFIGURABLE**
- `aggressive_mode = False` (línea 182) - **DEBE SER CONFIGURABLE** (aunque ya no se usa FINISHED_UNCONFIRMED)
- `min_liquidity_required` - No está en StrategyConfig pero se usa (línea 532)
- Multiplicadores de safety_tick por latencia (2.0, 3.0) - **DEBEN SER CONFIGURABLES**
- Factor de reducción de tamaño en YELLOW (0.5) - **DEBE SER CONFIGURABLE**

**Parámetros ya configurables (desde RiskConfig):**
- `min_entry_price`
- `safety_tick`
- `target_edge` (target_margin)
- `max_order_size`
- `max_exposure_per_market`
- `max_global_exposure`

### 1.2 Risk Engine

**Archivo:** `backend/app/core/risk_engine/risk_engine.py`

**Parámetros hardcodeados encontrados:**
- `min_order_size = 100.0` (línea 51) - **DEBE SER CONFIGURABLE**
- `latency_fail_mode = "strict"` (línea 52) - **DEBE SER CONFIGURABLE**
- `reduce_size_in_yellow = True` (línea 53) - **DEBE SER CONFIGURABLE**
- `yellow_size_factor = 0.5` (línea 54) - **DEBE SER CONFIGURABLE**
- `cancel_on_red = True` (línea 55) - **DEBE SER CONFIGURABLE**
- `exposure_method = "notional"` (línea 56) - **DEBE SER CONFIGURABLE**
- `max_price_swing_pct = 0.05` (línea 57) - **DEBE SER CONFIGURABLE**
- `max_swing_time_seconds = 10.0` (línea 58) - **DEBE SER CONFIGURABLE**
- `min_realistic_spread = 0.001` (línea 59) - **DEBE SER CONFIGURABLE**
- `confidence threshold para FINISHED_UNCONFIRMED = 0.85` (línea 261) - **DEBE SER CONFIGURABLE** (aunque ya no se usa)

**Parámetros ya configurables:**
- `max_market_exposure`
- `max_global_exposure`
- `max_markets_active`
- `max_order_size`

### 1.3 Scanner

**Archivo:** `backend/app/core/scanner/scanner.py`

**Parámetros hardcodeados encontrados:**
- `min_price_threshold` - **DEBE SER CONFIGURABLE**
- `allowed_categories = ["sports"]` - **DEBE SER CONFIGURABLE**
- `allowed_subcategories = []` - **DEBE SER CONFIGURABLE**
- `scan_interval_seconds` - Ya está en RiskConfig pero debe ser específico de Scanner
- Filtros de mercado (volumen mínimo, liquidez mínima) - **DEBEN SER CONFIGURABLES**

### 1.4 Event Engine

**Archivo:** `backend/app/core/event_engine.py`

**Parámetros hardcodeados encontrados:**
- `min_feed_confidence = 0.8` (línea 85) - Ya está en config_service pero debe ser más explícito
- `min_checkers_for_confirmed = 2` - **DEBE SER CONFIGURABLE Y DINÁMICO**
- `checker_timeout_seconds` - Ya está en RiskConfig pero debe ser específico
- Categoría hardcodeada `category = "sports"` (línea 199) - **DEBE SER CONFIGURABLE**
- **❌ CRÍTICO:** Quorum hardcodeado `>= 2` (línea 97) - **DEBE SER DINÁMICO BASADO EN CHECKERS DISPONIBLES**

**Lógica de quorum fijo a eliminar:**
- Línea 97: `if finished_count >= 2:` - **HARDCODEADO, DEBE SER DINÁMICO**
- Línea 99: `elif finished_count == 1:` - **HARDCODEADO, DEBE SER DINÁMICO**
- No detecta checkers saludables vs no saludables
- No calcula quorum efectivo basado en disponibilidad

### 1.5 Execution Engine

**Archivo:** `backend/app/core/execution/execution.py`

**Parámetros hardcodeados encontrados:**
- `max_poll_attempts = 720` - **DEBE SER CONFIGURABLE**
- `poll_interval_seconds` - **DEBE SER CONFIGURABLE**
- `order_timeout_seconds` - **DEBE SER CONFIGURABLE**
- `retry_on_failure = True` - **DEBE SER CONFIGURABLE**
- `max_retries = 3` - **DEBE SER CONFIGURABLE**

### 1.6 Modos de Ejecución

**NUEVO - Requiere implementación:**
- `execution_mode`: `DRY_RUN` | `PAPER` | `LIVE`
- `dry_run_behavior`: Configuración de cómo se comporta DRY_RUN
- `paper_trading_wallet`: Wallet específica para paper trading

---

## 2. Esquema de Base de Datos

### 2.1 system_config (Mejoras necesarias)

**Tabla existente:** `system_config`

**Campos actuales:**
- `key` (String, unique)
- `value` (Text)
- `value_type` (String: "float", "int", "bool", "string")
- `category` (String: "system", "risk", "scanner", "event_engine")
- `description` (String, nullable)
- `updated_by` (String, FK a users)

**Mejoras necesarias:**
- Agregar `execution_mode` (String: "DRY_RUN", "PAPER", "LIVE")
- Agregar `min_value` y `max_value` para validación
- Agregar `is_readonly` (bool) para parámetros críticos - **Protección contra errores humanos**
- Agregar `requires_confirmation` (bool) - Requiere confirmación antes de cambiar
- Agregar `updated_at` timestamp
- Agregar `validation_rule` (JSON) para validaciones complejas

**⚠️ Parámetros que deben ser protegidos (is_readonly = true o requires_confirmation = true):**
- `allow_zero_checker` - Crítico para seguridad
- `execution_mode = LIVE` - Cambio a LIVE requiere confirmación explícita
- `latency_fail_mode` - Afecta comportamiento de seguridad
- `quorum_base` - Afecta lógica core
- `min_feed_confidence` - Afecta confiabilidad de decisiones

**Nuevos parámetros para quorum dinámico:**
- `quorum_base` (int): Quorum base configurado (default: 2)
- `allow_single_checker` (bool): Permitir quorum de 1 si solo hay 1 checker disponible
- `allow_zero_checker` (bool): **Permitir sistema operativo sin checkers (sin trading)**
  - `true`: Sistema sigue funcionando, evalúa mercados, produce decision_traces, pero **NUNCA confirma FINISHED** y **NUNCA hace trading**
  - `false`: Sistema entra en estado DEGRADED/PAUSED, no evalúa mercados
- `checker_health_window_seconds` (int): Ventana de tiempo para considerar saludable
- `checker_max_failures` (int): Máximo de fallos consecutivos antes de considerar no saludable

**🔴 REGLA CRÍTICA:**
- Con 0 checkers, el sistema **NUNCA** debe emitir `FINISHED_CONFIRMED`
- `allow_zero_checker = true` NO significa "confirmar sin checkers"
- `allow_zero_checker = true` significa: "permitir que el sistema siga vivo, pero sin entradas"

### 2.2 checker_config (NUEVO)

**Tabla nueva:** `checker_config`

```sql
CREATE TABLE checker_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checker_id UUID NOT NULL REFERENCES event_checker(id),
    key VARCHAR(255) NOT NULL,
    value TEXT NOT NULL,
    value_type VARCHAR(50) NOT NULL, -- "float", "int", "bool", "string", "json"
    description TEXT,
    updated_by VARCHAR(255) REFERENCES neon_auth.users_sync(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(checker_id, key)
);
```

**Propósito:** Configuración específica por checker (timeouts, retries, weights, etc.)

### 2.3 execution_session (NUEVO)

**Tabla nueva:** `execution_session`

```sql
CREATE TABLE execution_session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_name VARCHAR(255) NOT NULL,
    execution_mode VARCHAR(50) NOT NULL, -- "DRY_RUN", "PAPER", "LIVE"
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMP,
    started_by VARCHAR(255) REFERENCES neon_auth.users_sync(id),
    config_snapshot JSONB NOT NULL, -- Snapshot de toda la configuración al inicio
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE', -- "ACTIVE", "PAUSED", "STOPPED", "ERROR"
    metadata JSONB, -- Información adicional
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Propósito:** Rastrear sesiones de ejecución con su modo y configuración

### 2.4 decision_trace (NUEVO)

**Tabla nueva:** `decision_trace`

```sql
CREATE TABLE decision_trace (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES execution_session(id),
    trace_id UUID NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    component VARCHAR(100) NOT NULL, -- "scanner", "strategy", "risk", "execution"
    decision_stage VARCHAR(50) NOT NULL, -- "SCAN", "EVENT_CONFIRMATION", "STRATEGY", "RISK", "EXECUTION"
    market_id UUID REFERENCES markets(id),
    event_id UUID REFERENCES events(id),
    decision_type VARCHAR(100) NOT NULL, -- "entry", "reject", "adjust", "cancel"
    decision VARCHAR(50) NOT NULL, -- "APPROVED", "REJECTED", "ADJUSTED", "CANCELLED"
    reason TEXT,
    input_data JSONB NOT NULL, -- ACOTADO: solo hashes/snapshots relevantes, NO orderbooks completos
    output_data JSONB, -- Datos de salida (order_intent, approved_intent, etc.)
    config_used JSONB NOT NULL, -- Configuración usada para esta decisión
    latency_ms FLOAT,
    confidence_score FLOAT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_decision_trace_session ON decision_trace(session_id);
CREATE INDEX idx_decision_trace_trace_id ON decision_trace(trace_id);
CREATE INDEX idx_decision_trace_timestamp ON decision_trace(timestamp);
CREATE INDEX idx_decision_trace_component ON decision_trace(component);
CREATE INDEX idx_decision_trace_stage ON decision_trace(decision_stage);
CREATE INDEX idx_decision_trace_market ON decision_trace(market_id);
```

**Propósito:** Rastrear completamente cada decisión del bot para explicabilidad

**⚠️ Recomendaciones importantes:**

1. **decision_stage:** 
   - Permite reconstruir el pipeline completo
   - Frontend puede mostrar timeline real del flujo de decisión
   - Valores: `SCAN`, `EVENT_CONFIRMATION`, `STRATEGY`, `RISK`, `EXECUTION`

2. **input_data ACOTADO:**
   - **NO incluir orderbooks completos** - solo hashes o snapshots relevantes
   - **NO incluir datos históricos completos** - solo resúmenes
   - **SÍ incluir:** market_id, event_id, precios clave, spreads, estados, métricas resumidas
   - **Ejemplo de input_data:**
     ```json
     {
       "market_id": "uuid",
       "best_ask": 0.98,
       "best_bid": 0.97,
       "spread": 0.01,
       "event_state": "FINISHED_CONFIRMED",
       "confidence": 0.95,
       "exposure_current": 5000.0,
       "exposure_limit": 10000.0,
       "orderbook_hash": "sha256_hash"  // Hash del orderbook, no el orderbook completo
     }
     ```
   - Esto evita que la tabla crezca excesivamente rápido

---

## 3. Migraciones Alembic

### 3.1 Migración 005: Mejorar system_config

**Archivo:** `backend/alembic/versions/005_improve_system_config.py`

**Cambios:**
- Agregar columna `execution_mode`
- Agregar columnas `min_value`, `max_value` (nullable)
- Agregar columna `is_readonly` (bool, default false) - **Protección contra errores humanos**
- Agregar columna `requires_confirmation` (bool, default false) - **Requiere confirmación antes de cambiar**
- Agregar columna `validation_rule` (JSONB, nullable)
- Agregar índices en `category`, `execution_mode`, `is_readonly`

### 3.2 Migración 006: Crear checker_config

**Archivo:** `backend/alembic/versions/006_create_checker_config.py`

**Cambios:**
- Crear tabla `checker_config`
- Agregar índices necesarios

### 3.3 Migración 007: Crear execution_session

**Archivo:** `backend/alembic/versions/007_create_execution_session.py`

**Cambios:**
- Crear tabla `execution_session`
- Agregar índices necesarios

### 3.4 Migración 008: Crear decision_trace

**Archivo:** `backend/alembic/versions/008_create_decision_trace.py`

**Cambios:**
- Crear tabla `decision_trace`
- Agregar columna `decision_stage` (VARCHAR(50)) - **Para reconstruir pipeline y timeline**
- Agregar índices necesarios (incluyendo `decision_stage`)
- **Nota importante:** `input_data` debe ser ACOTADO - NO incluir orderbooks completos

---

## 4. Refactorización de Código

### 4.1 ConfigService - Hot Reload

**Archivo:** `backend/app/core/config_service.py`

**Mejoras necesarias:**
1. Implementar hot reload con polling o webhooks
2. Agregar métodos para obtener configuraciones por categoría
3. Agregar validación de valores según min/max
4. Agregar soporte para `execution_mode`
5. Agregar métodos para obtener configuraciones específicas de componentes

**Nuevos métodos:**
```python
def get_strategy_config() -> StrategyConfig
def get_risk_config() -> RiskConfig
def get_scanner_config() -> ScannerConfig
def get_event_engine_config() -> EventEngineConfig
def get_execution_config() -> ExecutionConfig
def get_execution_mode() -> str  # "DRY_RUN" | "PAPER" | "LIVE"
def reload_config(category: Optional[str] = None)
```

### 4.2 Strategy Engine

**Archivo:** `backend/app/core/strategy/strategy.py`

**Cambios:**
1. Eliminar hardcoded values
2. Obtener TODOS los parámetros desde ConfigService
3. Agregar logging de decisiones con decision_trace
4. Respetar execution_mode (no crear órdenes reales en DRY_RUN/PAPER)

**Parámetros a configurar:**
- `max_entry_spread`
- `min_liquidity_required`
- `safety_tick_multiplier_yellow` (default 2.0)
- `safety_tick_multiplier_red` (default 3.0)
- `yellow_latency_size_factor` (default 0.5)

### 4.3 Risk Engine

**Archivo:** `backend/app/core/risk_engine/risk_engine.py`

**Cambios:**
1. Eliminar hardcoded values
2. Obtener TODOS los parámetros desde ConfigService
3. Agregar logging de decisiones con decision_trace
4. Respetar execution_mode

**Parámetros a configurar:**
- `min_order_size`
- `latency_fail_mode`
- `reduce_size_in_yellow`
- `yellow_size_factor`
- `cancel_on_red`
- `exposure_method`
- `max_price_swing_pct`
- `max_swing_time_seconds`
- `min_realistic_spread`

### 4.4 Scanner

**Archivo:** `backend/app/core/scanner/scanner.py`

**Cambios:**
1. Crear ScannerConfig model
2. Obtener TODOS los parámetros desde ConfigService
3. Agregar logging de decisiones con decision_trace

**Parámetros a configurar:**
- `min_price_threshold`
- `allowed_categories` (JSON array)
- `allowed_subcategories` (JSON array)
- `scan_interval_seconds`
- `min_volume_24h`
- `min_liquidity`

### 4.5 Event Engine

**Archivo:** `backend/app/core/event_engine.py`

**Cambios:**
1. Crear EventEngineConfig model
2. Obtener TODOS los parámetros desde ConfigService
3. **CRÍTICO:** Implementar quorum dinámico basado en checkers saludables
4. Crear CheckerHealthService para rastrear estado de checkers
5. Agregar logging de decisiones con decision_trace incluyendo quorum usado

**Parámetros a configurar:**
- `min_feed_confidence`
- `quorum_base` (reemplaza min_checkers_for_confirmed)
- `allow_single_checker`
- `allow_zero_checker`
- `checker_timeout_seconds`
- `checker_health_window_seconds`
- `checker_max_failures`
- `default_category` (ya no hardcodeado)

**Refactorización de quorum:**
- Eliminar hardcoded `>= 2` y `>= 1`
- Calcular quorum efectivo: `min(quorum_base, checkers_saludables_disponibles)`
- Incluir en EventState: `quorum_used`, `checkers_available`, `checkers_used`, `quorum_reason`

### 4.6 Execution Engine

**Archivo:** `backend/app/core/execution/execution.py`

**Cambios:**
1. Obtener TODOS los parámetros desde ConfigService
2. Respetar execution_mode:
   - `DRY_RUN`: Solo loggear, no enviar órdenes
   - `PAPER`: Enviar a wallet de paper trading
   - `LIVE`: Enviar órdenes reales
3. Agregar logging de decisiones con decision_trace
4. Crear execution_session al iniciar

**Parámetros a configurar:**
- `max_poll_attempts`
- `poll_interval_seconds`
- `order_timeout_seconds`
- `retry_on_failure`
- `max_retries`
- `paper_trading_wallet_id`

---

## 5. Endpoints del Frontend

### 5.1 Configuración

**GET** `/api/config`
- Obtener toda la configuración agrupada por categoría
- Respuesta: `{ "strategy": {...}, "risk": {...}, "scanner": {...}, ... }`

**GET** `/api/config/{category}`
- Obtener configuración de una categoría específica
- Ejemplo: `/api/config/strategy`

**PUT** `/api/config/{key}`
- Actualizar un parámetro de configuración
- Body: `{ "value": "...", "value_type": "float", "confirmation_token": "..." }` (si requires_confirmation)
- Validar según min/max si existen
- Verificar `is_readonly` - rechazar si es true
- Verificar `requires_confirmation` - requerir confirmation_token si es true
- Invalidar cache del ConfigService

**GET** `/api/config/execution-mode`
- Obtener modo de ejecución actual

**PUT** `/api/config/execution-mode`
- Cambiar modo de ejecución
- Body: `{ "mode": "DRY_RUN" | "PAPER" | "LIVE", "confirmation_token": "..." }`
- **CRÍTICO:** Cambio a LIVE requiere `confirmation_token` explícito
- Validar que el usuario tenga permisos para LIVE
- Mostrar advertencia clara en frontend antes de confirmar

### 5.2 Decision Traces

**GET** `/api/traces`
- Obtener traces de decisiones
- Query params:
  - `session_id` (UUID, opcional)
  - `component` (string, opcional)
  - `market_id` (UUID, opcional)
  - `start_time` (ISO datetime)
  - `end_time` (ISO datetime)
  - `limit` (int, default 100)
  - `offset` (int, default 0)

**GET** `/api/traces/{trace_id}`
- Obtener un trace específico con todos sus detalles

**GET** `/api/traces/summary`
- Resumen de decisiones por componente
- Agregaciones: totales, aprobados, rechazados, razones más comunes

### 5.3 Execution Sessions

**GET** `/api/sessions`
- Listar sesiones de ejecución
- Query params: `status`, `mode`, `limit`, `offset`

**GET** `/api/sessions/{session_id}`
- Obtener detalles de una sesión

**POST** `/api/sessions`
- Crear nueva sesión
- Body: `{ "session_name": "...", "execution_mode": "DRY_RUN" }`

**PUT** `/api/sessions/{session_id}/status`
- Cambiar estado de sesión
- Body: `{ "status": "PAUSED" | "STOPPED" }`

### 5.4 Checker Configuration

**GET** `/api/checkers/{checker_id}/config`
- Obtener configuración de un checker

**PUT** `/api/checkers/{checker_id}/config/{key}`
- Actualizar configuración de un checker

---

## 6. Información para el Frontend

### 6.1 Dashboard Principal

**Información a mostrar:**
1. **Estado del Sistema:**
   - Modo de ejecución actual (DRY_RUN/PAPER/LIVE) - **MUY VISIBLE**
   - Estado de sesión (ACTIVE/PAUSED/STOPPED)
   - Latencia del sistema (GREEN/YELLOW/RED)
   - Circuit breakers activos

2. **Métricas de Decisión:**
   - Total de decisiones en última hora
   - Tasa de aprobación/rechazo
   - Razones más comunes de rechazo
   - Tiempo promedio de decisión

3. **Estado de Checkers:**
   - Checkers activos por categoría
   - Última ejecución de cada checker
   - Tasa de éxito/fallo
   - Latencia promedio

4. **Riesgo:**
   - Exposición actual vs límites
   - Mercados activos
   - Órdenes pendientes
   - Brechas de límites (si las hay)

### 6.2 Página de Configuración

**Secciones:**
1. **Modo de Ejecución** (muy prominente)
   - Selector: DRY_RUN / PAPER / LIVE
   - Advertencia clara cuando está en LIVE
   - Confirmación requerida para cambiar a LIVE

2. **Strategy Configuration**
   - Todos los parámetros de Strategy
   - Validación en tiempo real
   - Descripción de cada parámetro

3. **Risk Configuration**
   - Todos los parámetros de Risk
   - Visualización de límites actuales vs configurados

4. **Scanner Configuration**
   - Categorías permitidas
   - Filtros de mercado

5. **Event Engine Configuration**
   - Confianza mínima
   - Número mínimo de checkers

6. **Execution Configuration**
   - Timeouts
   - Retries
   - Modo de paper trading

### 6.3 Página de Decision Traces

**Vista de lista:**
- Tabla con: timestamp, componente, mercado, decisión, razón
- Filtros por componente, mercado, decisión
- Búsqueda por trace_id

**Vista de detalle:**
- Input data completo
- Output data completo
- Configuración usada
- Latencia
- Confidence score
- Timeline de la decisión

### 6.4 Página de Checkers

**Información a mostrar:**
- Estado de cada checker (activo/inactivo)
- Última ejecución
- Tasa de éxito
- Latencia promedio
- Configuración específica
- Historial de resultados recientes

---

## 7. Implementación de Modos de Ejecución

### 7.1 DRY_RUN

**Comportamiento:**
- NO envía órdenes a Polymarket
- NO crea órdenes en DB
- SÍ genera decision_traces completos
- SÍ muestra en frontend como si fueran órdenes reales
- Útil para probar lógica sin riesgo

**Implementación:**
- En Execution.tick(), verificar `execution_mode == "DRY_RUN"`
- Si es DRY_RUN, solo loggear y crear decision_trace
- No llamar a Polymarket API

### 7.2 PAPER

**Comportamiento:**
- Envía órdenes a wallet de paper trading
- Crea órdenes en DB marcadas como `paper_trading = true`
- Usa wallet separada configurada en `paper_trading_wallet_id`
- SÍ genera decision_traces
- Útil para probar con dinero simulado

**Implementación:**
- En Execution.tick(), verificar `execution_mode == "PAPER"`
- Obtener wallet desde `paper_trading_wallet_id`
- Enviar órdenes normalmente pero a wallet de paper
- Marcar órdenes como paper_trading

### 7.3 LIVE

**Comportamiento:**
- Envía órdenes reales a Polymarket
- Usa wallet activa real
- Requiere confirmación explícita del usuario
- Todas las órdenes son reales

**Implementación:**
- En Execution.tick(), verificar `execution_mode == "LIVE"`
- Usar wallet activa normal
- Enviar órdenes normalmente

---

## 8. Plan de Implementación

### Fase 1: Base de Datos
1. Crear migraciones Alembic (005-008)
2. Ejecutar migraciones
3. Poblar system_config con valores por defecto

### Fase 2: ConfigService
1. Mejorar ConfigService con hot reload
2. Agregar métodos por componente
3. Agregar soporte para execution_mode

### Fase 3: Refactorización de Componentes
1. Strategy Engine
2. Risk Engine
3. Scanner
4. Event Engine
5. Execution Engine

### Fase 4: Decision Tracing
1. Crear servicio de decision_trace
2. Integrar en todos los componentes
3. Crear endpoints del frontend

### Fase 5: Frontend
1. Página de configuración
2. Página de decision traces
3. Dashboard mejorado
4. Selector de modo de ejecución

### Fase 6: Testing
1. Tests unitarios para configuración
2. Tests de modos de ejecución
3. Tests de decision tracing

---

## 9. Checklist de Validación

- [ ] Todos los parámetros hardcodeados eliminados
- [ ] ConfigService con hot reload funcionando
- [ ] Modos de ejecución implementados y funcionando
- [ ] Decision traces generándose correctamente
- [ ] Frontend puede configurar todos los parámetros
- [ ] Frontend muestra información relevante del bot
- [ ] No se requiere modificar código para ajustes operativos
- [ ] Migraciones ejecutadas correctamente
- [ ] Tests pasando

