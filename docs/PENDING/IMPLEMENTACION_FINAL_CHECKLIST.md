# Checklist Final de Implementación - Config-Driven

## ✅ Estado: LISTO PARA IMPLEMENTAR

Toda la documentación está completa y lista. Este checklist resume lo que debe implementarse.

---

## 1. Migraciones ✅ CREADAS

- [x] **005_improve_system_config.py** - Mejora tabla system_config
  - [x] Agregar `execution_mode`
  - [x] Agregar `min_value`, `max_value`
  - [x] Agregar `is_readonly` (protección)
  - [x] Agregar `requires_confirmation` (protección)
  - [x] Agregar `validation_rule`
  - [x] Agregar `updated_at`
  - [x] Índices necesarios

- [x] **006_create_checker_config.py** - Crea tabla checker_config
- [x] **007_create_execution_session.py** - Crea tabla execution_session
- [x] **008_create_decision_trace.py** - Crea tabla decision_trace
  - [x] Agregar `decision_stage` (SCAN, EVENT_CONFIRMATION, STRATEGY, RISK, EXECUTION)
  - [x] Comentario sobre `input_data` ACOTADO
  - [x] Índice en `decision_stage`

**Acción:** Ejecutar `alembic upgrade head`

---

## 2. Protección de Parámetros

### Parámetros que requieren `requires_confirmation = true`:

- [ ] `allow_zero_checker`
- [ ] `execution_mode` (especialmente cambio a LIVE)
- [ ] `latency_fail_mode`
- [ ] `quorum_base`
- [ ] `min_feed_confidence`
- [ ] `max_global_exposure`
- [ ] `max_exposure_per_market`
- [ ] `cancel_on_red`

**Implementación:**
- [ ] Backend valida `confirmation_token` antes de cambiar
- [ ] Frontend muestra diálogo de confirmación
- [ ] Frontend requiere escribir token de confirmación

---

## 3. Quorum Dinámico

### CheckerHealthService

- [ ] Crear `backend/app/core/checkers/health_service.py`
- [ ] Implementar `get_healthy_checkers(category: str) -> List[Checker]`
- [ ] Implementar `is_checker_healthy(checker_id: UUID) -> bool`
- [ ] Rastrear estado de salud (fallos consecutivos, latencia, etc.)

### Refactorización de Quorum

- [ ] Eliminar hardcoded `>= 2` y `>= 1` en EventEngine
- [ ] Eliminar hardcoded `>= 2` y `>= 1` en StateAggregator
- [ ] Calcular quorum efectivo dinámicamente
- [ ] Implementar lógica de `allow_zero_checker` (NUNCA confirmar FINISHED con 0 checkers)
- [ ] Implementar lógica de `allow_single_checker`
- [ ] Incluir en EventState: `quorum_used`, `checkers_available`, `quorum_reason`, `trading_permitted`

---

## 4. ConfigService - Hot Reload

- [ ] Implementar polling cada 5-10 segundos
- [ ] Agregar métodos por componente:
  - [ ] `get_strategy_config() -> StrategyConfig`
  - [ ] `get_risk_config() -> RiskConfig`
  - [ ] `get_scanner_config() -> ScannerConfig`
  - [ ] `get_event_engine_config() -> EventEngineConfig`
  - [ ] `get_execution_config() -> ExecutionConfig`
- [ ] Agregar `get_execution_mode() -> str`
- [ ] Agregar validación según min/max
- [ ] Agregar validación de `is_readonly`
- [ ] Agregar validación de `requires_confirmation`

---

## 5. Refactorización de Componentes

### Strategy Engine

- [ ] Eliminar todos los hardcoded values
- [ ] Obtener TODOS los parámetros desde ConfigService
- [ ] Agregar logging de decisiones con `decision_trace` (stage: STRATEGY)
- [ ] Respetar `execution_mode` (no crear órdenes reales en DRY_RUN)
- [ ] `input_data` ACOTADO (no orderbooks completos)

### Risk Engine

- [ ] Eliminar todos los hardcoded values
- [ ] Obtener TODOS los parámetros desde ConfigService
- [ ] Agregar logging de decisiones con `decision_trace` (stage: RISK)
- [ ] Respetar `execution_mode`
- [ ] `input_data` ACOTADO

### Scanner

- [ ] Crear ScannerConfig model
- [ ] Obtener TODOS los parámetros desde ConfigService
- [ ] Agregar logging de decisiones con `decision_trace` (stage: SCAN)
- [ ] `input_data` ACOTADO

### Event Engine

- [ ] Crear EventEngineConfig model
- [ ] Obtener TODOS los parámetros desde ConfigService
- [ ] Implementar quorum dinámico
- [ ] Agregar logging de decisiones con `decision_trace` (stage: EVENT_CONFIRMATION)
- [ ] `input_data` ACOTADO

### Execution Engine

- [ ] Obtener TODOS los parámetros desde ConfigService
- [ ] Implementar modos de ejecución (DRY_RUN/PAPER/LIVE)
- [ ] Crear execution_session al iniciar
- [ ] Agregar logging de decisiones con `decision_trace` (stage: EXECUTION)
- [ ] `input_data` ACOTADO

---

## 6. Decision Tracing

### Servicio de Decision Trace

- [ ] Crear `backend/app/core/decision_trace/service.py`
- [ ] Método `create_trace()` que valida `input_data` está ACOTADO
- [ ] Método `get_trace_by_id()`
- [ ] Método `get_traces_by_session()`
- [ ] Método `get_timeline_by_trace_id()` - Reconstruir pipeline completo

### Integración en Componentes

- [ ] Scanner crea traces con stage: SCAN
- [ ] EventEngine crea traces con stage: EVENT_CONFIRMATION
- [ ] Strategy crea traces con stage: STRATEGY
- [ ] Risk crea traces con stage: RISK
- [ ] Execution crea traces con stage: EXECUTION
- [ ] Todos usan mismo `trace_id` para rastrear pipeline completo

### Validación de input_data

- [ ] NO incluir orderbooks completos
- [ ] NO incluir datos históricos extensos
- [ ] SÍ incluir hashes/snapshots relevantes
- [ ] Tamaño objetivo: < 2KB por registro

---

## 7. Endpoints del Frontend

### Configuración

- [ ] `GET /api/config` - Obtener toda la configuración
- [ ] `GET /api/config/{category}` - Obtener por categoría
- [ ] `PUT /api/config/{key}` - Actualizar (con validación de protección)
- [ ] `GET /api/config/execution-mode` - Obtener modo actual
- [ ] `PUT /api/config/execution-mode` - Cambiar modo (con confirmación para LIVE)

### Decision Traces

- [ ] `GET /api/traces` - Listar con filtros
- [ ] `GET /api/traces/{trace_id}` - Obtener trace específico
- [ ] `GET /api/traces/{trace_id}/timeline` - Timeline completo del pipeline
- [ ] `GET /api/traces/summary` - Resumen de decisiones

### Execution Sessions

- [ ] `GET /api/sessions` - Listar sesiones
- [ ] `GET /api/sessions/{session_id}` - Obtener sesión
- [ ] `POST /api/sessions` - Crear nueva sesión
- [ ] `PUT /api/sessions/{session_id}/status` - Cambiar estado

### Checker Health

- [ ] `GET /api/checkers/health` - Estado de salud de checkers
- [ ] `GET /api/events/{event_id}/quorum` - Quorum usado en decisión

---

## 8. Frontend

### Página de Configuración

- [ ] Mostrar todos los parámetros agrupados por categoría
- [ ] Indicar parámetros protegidos (readonly o requires_confirmation)
- [ ] Diálogo de confirmación para parámetros críticos
- [ ] Validación en tiempo real
- [ ] Advertencia clara para cambio a LIVE

### Página de Decision Traces

- [ ] Lista de traces con filtros
- [ ] Vista de timeline usando `decision_stage`
- [ ] Vista de detalle con input/output data
- [ ] Búsqueda por trace_id

### Dashboard

- [ ] Estado del sistema (modo de ejecución MUY visible)
- [ ] Métricas de decisión
- [ ] Estado de checkers (disponibles, saludables, quorum)
- [ ] Estado de riesgo

---

## 9. Poblar system_config con Valores Iniciales

- [ ] Crear script de seed data
- [ ] Poblar todos los parámetros con valores por defecto
- [ ] Marcar parámetros críticos con `requires_confirmation = true`
- [ ] Agregar descripciones claras

---

## 10. Testing

- [ ] Tests unitarios para ConfigService
- [ ] Tests de quorum dinámico
- [ ] Tests de modos de ejecución
- [ ] Tests de decision tracing
- [ ] Tests de protección de parámetros
- [ ] Tests de validación de input_data ACOTADO

---

## Priorización

### Fase 1: Base (Semana 1)
1. Ejecutar migraciones
2. Poblar system_config
3. Implementar CheckerHealthService
4. Implementar quorum dinámico
5. Protección de parámetros básica

### Fase 2: Core (Semana 2)
1. Refactorizar Strategy y Risk
2. Refactorizar Scanner y EventEngine
3. Refactorizar Execution
4. Implementar decision_trace básico

### Fase 3: Completar (Semana 3)
1. Completar decision_trace en todos los componentes
2. Crear endpoints del frontend
3. Frontend: Página de configuración
4. Frontend: Página de decision traces

### Fase 4: Pulir (Semana 4)
1. Frontend: Dashboard mejorado
2. Tests completos
3. Validación de input_data ACOTADO
4. Optimización de performance

---

## ✅ Listo para Empezar

Toda la documentación está completa:
- ✅ Migraciones creadas
- ✅ Diseño completo
- ✅ Requisitos claros
- ✅ Protecciones definidas
- ✅ Decision trace diseñado correctamente

**¡Puedes empezar a implementar!**

