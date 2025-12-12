# Plan de Refactorización del Backend

**PolyLiquidity Desk – Plan de Migración Fase por Fase**

**Versión 1.0 - Guía de Implementación**

---

## Objetivo

Refactorizar el backend existente para alinearlo con la arquitectura documentada en `docs/services/`, manteniendo y mejorando el código existente.

**Principio clave:** Cada fase debe pasar todos los tests unitarios antes de continuar a la siguiente fase.

---

## Estado Actual del Backend

### Código Existente que se Puede Reutilizar

- ✅ `backend/app/core/scanner.py` - Scanner básico implementado
- ✅ `backend/app/core/event_engine.py` - Event Engine básico
- ✅ `backend/app/core/strategy.py` - Strategy básico
- ✅ `backend/app/core/risk_engine.py` - Risk Engine básico
- ✅ `backend/app/core/execution.py` - Execution básico
- ✅ `backend/app/core/metrics.py` - Placeholder (necesita implementación)
- ✅ `backend/app/core/latency_monitor.py` - Latency Monitor implementado
- ✅ `backend/app/core/live_watchers.py` - Live Watchers implementado
- ✅ `backend/app/core/wallet.py` - Wallet Service básico
- ✅ `backend/app/core/checkers/` - Sistema de checkers implementado
- ✅ `backend/app/core/rate_limiter.py` - Rate Limiter implementado
- ✅ `backend/app/core/state.py` - State management
- ✅ `backend/app/core/config_service.py` - Config Service
- ✅ `backend/app/api/` - Endpoints API básicos

### Código que Necesita Crearse

- ❌ `backend/app/core/event_mapping_layer/` - Event Mapping Layer (nuevo)
- ❌ `backend/app/core/event_watch_engine/` - Event Watch Engine (refactorizar desde live_watchers)
- ❌ `backend/app/core/runtime_supervisor/` - Runtime Supervisor (nuevo)
- ❌ `backend/app/core/metrics/` - Metrics & Observability (refactorizar desde metrics.py)
- ❌ `backend/app/core/historical_replay/` - Historical Replay (nuevo)
- ❌ Tests unitarios para todos los módulos

---

## Fases de Refactorización

### FASE 0: Preparación y Testing Infrastructure

**Objetivo:** Establecer infraestructura de testing y validar el estado actual.

**Tareas:**

1. **Configurar pytest y estructura de tests:**
   ```bash
   # Crear estructura
   backend/tests/
   ├── __init__.py
   ├── conftest.py
   ├── unit/
   │   ├── __init__.py
   │   ├── test_scanner.py
   │   ├── test_strategy.py
   │   ├── test_risk_engine.py
   │   └── ...
   └── integration/
       ├── __init__.py
       └── test_main_loop.py
   ```

2. **Crear tests básicos para código existente:**
   - Tests para Scanner (mocks de Polymarket API)
   - Tests para Strategy (validar cálculos)
   - Tests para Risk Engine (validar reglas)
   - Tests para Execution (mocks de Polymarket Trading API)
   - Tests para Wallet Service (validar cifrado/descifrado)

3. **Configurar CI/CD básico:**
   - GitHub Actions o similar
   - Ejecutar tests en cada commit

4. **Documentar estado actual:**
   - Listar qué funciona
   - Listar qué falta
   - Identificar dependencias entre módulos

**Criterio de Éxito:**
- ✅ Todos los tests existentes pasan
- ✅ Cobertura de tests > 60% para código crítico
- ✅ CI/CD configurado y funcionando

**Referencias:**
- No hay documentación específica, pero se debe seguir best practices de testing en Python

---

### FASE 1: Wallet Service

**Objetivo:** Refactorizar Wallet Service según especificación completa.

**Documentación de Referencia:**
- 📖 `docs/services/wallet_service.md` - Especificación completa del Wallet Service

**Tareas:**

1. **Revisar implementación actual:**
   - `backend/app/core/wallet.py`
   - Validar que cumple con especificación

2. **Mejorar según especificación:**
   - ✅ Cache en memoria con invalidación
   - ✅ Cifrado seguro (AES-256-GCM)
   - ✅ Rotación en runtime sin reinicio
   - ✅ Garantía de solo una wallet activa
   - ✅ Cancelación de órdenes al cambiar wallet

3. **Crear tests unitarios:**
   - Test de cifrado/descifrado
   - Test de activación de wallet
   - Test de cache
   - Test de rotación
   - Test de cancelación de órdenes

4. **Integrar con Execution Engine:**
   - Asegurar que Execution usa WalletService
   - Validar que falla gracefully si no hay wallet activa

**Criterio de Éxito:**
- ✅ Todos los tests unitarios pasan
- ✅ Wallet Service cumple con especificación en `docs/services/wallet_service.md`
- ✅ Integración con Execution Engine funciona
- ✅ Tests de integración pasan

**Archivos a Modificar/Crear:**
- `backend/app/core/wallet.py` (refactorizar)
- `backend/app/api/wallets.py` (mejorar endpoints)
- `backend/tests/unit/test_wallet_service.py` (nuevo)

---

### FASE 2: Metrics & Observability Layer

**Objetivo:** Implementar Metrics & Observability Layer completo.

**Documentación de Referencia:**
- 📖 `docs/services/metrics_observabilitiy.md` - Especificación completa del Metrics & Observability Layer

**Tareas:**

1. **Revisar implementación actual:**
   - `backend/app/core/metrics.py` (placeholder)
   - `backend/app/core/latency_monitor.py` (ya implementado)

2. **Crear estructura de Metrics:**
   ```
   backend/app/core/metrics/
   ├── __init__.py
   ├── collector.py          # Metric Collector
   ├── sampler.py            # Metric Sampler
   ├── store.py              # Metric Store
   ├── alerting.py           # Alerting System
   └── prometheus_exporter.py # Prometheus Exporter
   ```

3. **Implementar según especificación:**
   - ✅ Metric Samplers (periódicos)
   - ✅ Event Hooks (de módulos)
   - ✅ Metric Store (memoria + persistente)
   - ✅ Alerting System (Slack, Discord, Email)
   - ✅ Prometheus Exporter

4. **Integrar con módulos existentes:**
   - Scanner → emite métricas
   - Strategy → emite métricas
   - Risk → emite métricas
   - Execution → emite métricas

5. **Crear tests unitarios:**
   - Test de recolección de métricas
   - Test de almacenamiento
   - Test de alertas
   - Test de Prometheus exporter

6. **Mejorar API endpoints:**
   - `backend/app/api/metrics.py` (expandir)
   - Endpoint SSE streaming
   - Endpoint Prometheus

**Criterio de Éxito:**
- ✅ Todos los tests unitarios pasan
- ✅ Metrics & Observability cumple con especificación en `docs/services/metrics_observabilitiy.md`
- ✅ Métricas se recolectan de todos los módulos
- ✅ Alertas funcionan
- ✅ Prometheus exporter funciona

**Archivos a Modificar/Crear:**
- `backend/app/core/metrics/` (nuevo directorio)
- `backend/app/core/metrics.py` (refactorizar o eliminar)
- `backend/app/api/metrics.py` (expandir)
- `backend/tests/unit/test_metrics.py` (nuevo)

---

### FASE 3: Runtime Supervisor

**Objetivo:** Implementar Runtime Supervisor completo.

**Documentación de Referencia:**
- 📖 `docs/services/runtime_supervisor.md` - Especificación completa del Runtime Supervisor

**Tareas:**

1. **Crear estructura de Runtime Supervisor:**
   ```
   backend/app/core/runtime_supervisor/
   ├── __init__.py
   ├── supervisor.py         # Runtime Supervisor principal
   ├── circuit_breaker.py   # Circuit Breaker base
   └── fail_safes/
       ├── __init__.py
       ├── trading_fail_safe.py
       ├── checker_fail_safe.py
       └── anomaly_detector.py
   ```

2. **Implementar según especificación:**
   - ✅ Runtime Mode (GREEN/YELLOW/RED)
   - ✅ Cálculo de latencia global
   - ✅ Circuit Breakers (Trading, Checker, API)
   - ✅ Fail-Safes (FS1, FS2, FS3)
   - ✅ Integración con Metrics

3. **Integrar con módulos existentes:**
   - Risk Engine → consulta runtime_mode
   - Strategy Engine → consulta runtime_mode
   - Execution Engine → consulta circuit breakers
   - Metrics → alimenta Runtime Supervisor

4. **Crear tests unitarios:**
   - Test de cálculo de Runtime Mode
   - Test de Circuit Breakers
   - Test de Fail-Safes
   - Test de integración con módulos

5. **Integrar en main loop:**
   - Runtime Supervisor tick en main loop
   - Ajustar modo según métricas

**Criterio de Éxito:**
- ✅ Todos los tests unitarios pasan
- ✅ Runtime Supervisor cumple con especificación en `docs/services/runtime_supervisor.md`
- ✅ Integración con módulos funciona
- ✅ Circuit breakers funcionan
- ✅ Fail-safes se activan correctamente

**Archivos a Modificar/Crear:**
- `backend/app/core/runtime_supervisor/` (nuevo directorio)
- `backend/app/main.py` (integrar Runtime Supervisor)
- `backend/tests/unit/test_runtime_supervisor.py` (nuevo)

---

### FASE 4: Scanner Engine

**Objetivo:** Refactorizar Scanner Engine según especificación completa.

**Documentación de Referencia:**
- 📖 `docs/services/scanner.md` - Especificación completa del Scanner Engine

**Tareas:**

1. **Revisar implementación actual:**
   - `backend/app/core/scanner.py`
   - Validar que cumple con especificación

2. **Mejorar según especificación:**
   - ✅ Filtrado avanzado (estructural, categoría, precio, temporal)
   - ✅ Normalización y enriquecimiento de datos
   - ✅ Caching y rate limiting mejorados
   - ✅ Logging estructurado con trace_id
   - ✅ Manejo de errores robusto

3. **Crear modelos de datos:**
   - `CandidateMarket` (según especificación)
   - `EventMetadata` (según especificación)

4. **Crear tests unitarios:**
   - Test de filtrado de mercados
   - Test de normalización
   - Test de caching
   - Test de rate limiting
   - Test de manejo de errores

5. **Integrar con Event Mapping Layer:**
   - Scanner → Event Mapping Layer (preparar para Fase 5)

**Criterio de Éxito:**
- ✅ Todos los tests unitarios pasan
- ✅ Scanner Engine cumple con especificación en `docs/services/scanner.md`
- ✅ Filtrado funciona correctamente
- ✅ Caching y rate limiting funcionan
- ✅ Logging estructurado funciona

**Archivos a Modificar/Crear:**
- `backend/app/core/scanner.py` (refactorizar)
- `backend/tests/unit/test_scanner.py` (nuevo o mejorar)

---

### FASE 5: Event Mapping Layer

**Objetivo:** Implementar Event Mapping Layer completo (nuevo módulo crítico).

**Documentación de Referencia:**
- 📖 `docs/services/event_mapping_layer.md` - Especificación completa del Event Mapping Layer

**Tareas:**

1. **Crear estructura de Event Mapping Layer:**
   ```
   backend/app/core/event_mapping_layer/
   ├── __init__.py
   ├── mapper.py             # Mapper principal
   ├── classifiers/
   │   ├── __init__.py
   │   ├── sports_classifier.py
   │   ├── politics_classifier.py
   │   └── ...
   └── mappers/
       ├── __init__.py
       ├── sports_mapper.py  # MVP
       ├── politics_mapper.py
       └── ...
   ```

2. **Implementar según especificación:**
   - ✅ Clasificación de eventos (Sports, Politics, Crypto, Finance, Weather)
   - ✅ Sports Mapper (MVP) con heurísticas
   - ✅ Confidence scoring
   - ✅ Caching e idempotencia
   - ✅ Logging estructurado

3. **Integrar con Scanner:**
   - Scanner → Event Mapping Layer → Event Watch Engine

4. **Crear tests unitarios:**
   - Test de clasificación
   - Test de Sports Mapper (MVP)
   - Test de confidence scoring
   - Test de caching

5. **Crear modelos de datos:**
   - `EventDescriptor` (según especificación)

**Criterio de Éxito:**
- ✅ Todos los tests unitarios pasan
- ✅ Event Mapping Layer cumple con especificación en `docs/services/event_mapping_layer.md`
- ✅ Sports Mapper funciona (MVP)
- ✅ Integración con Scanner funciona
- ✅ Confidence scoring funciona

**Archivos a Modificar/Crear:**
- `backend/app/core/event_mapping_layer/` (nuevo directorio)
- `backend/app/main.py` (integrar Event Mapping Layer)
- `backend/tests/unit/test_event_mapping_layer.py` (nuevo)

---

### FASE 6: Checker System

**Objetivo:** Refactorizar Checker System según especificación completa.

**Documentación de Referencia:**
- 📖 `docs/services/checker_system.md` - Especificación completa del Checker System

**Tareas:**

1. **Revisar implementación actual:**
   - `backend/app/core/checkers/`
   - Validar que cumple con especificación

2. **Mejorar según especificación:**
   - ✅ BaseChecker mejorado
   - ✅ CheckerRegistry mejorado
   - ✅ CheckerResult según especificación
   - ✅ SecretService mejorado
   - ✅ Timeouts y retries
   - ✅ Error normalization
   - ✅ Circuit breaker por checker

3. **Implementar checkers según especificación:**
   - Sports Checker (ESPN, Flashscore)
   - Politics Checker (placeholder)
   - Crypto Checker (mejorar)
   - Finance Checker (placeholder)
   - Weather Checker (placeholder)

4. **Crear tests unitarios:**
   - Test de BaseChecker
   - Test de CheckerRegistry
   - Test de cada checker
   - Test de timeouts y retries
   - Test de circuit breaker

5. **Integrar con Event Watch Engine:**
   - Checker System → Event Watch Engine

**Criterio de Éxito:**
- ✅ Todos los tests unitarios pasan
- ✅ Checker System cumple con especificación en `docs/services/checker_system.md`
- ✅ Todos los checkers funcionan
- ✅ Circuit breakers funcionan
- ✅ Integración con Event Watch Engine funciona

**Archivos a Modificar/Crear:**
- `backend/app/core/checkers/base.py` (mejorar)
- `backend/app/core/checkers/registry.py` (mejorar)
- `backend/app/core/checkers/implementations/` (mejorar)
- `backend/tests/unit/test_checker_system.py` (nuevo)

---

### FASE 7: Event Watch Engine

**Objetivo:** Refactorizar Event Watch Engine desde live_watchers según especificación completa.

**Documentación de Referencia:**
- 📖 `docs/services/event_watch_engine.md` - Especificación completa del Event Watch Engine

**Tareas:**

1. **Revisar implementación actual:**
   - `backend/app/core/live_watchers.py`
   - Validar qué se puede reutilizar

2. **Crear estructura de Event Watch Engine:**
   ```
   backend/app/core/event_watch_engine/
   ├── __init__.py
   ├── coordinator.py        # Coordinator
   ├── lifecycle_manager.py  # Lifecycle Manager
   ├── checker_runner.py     # Checker Runner
   ├── state_aggregator.py   # State Aggregator
   └── watcher.py            # Watcher individual
   ```

3. **Implementar según especificación:**
   - ✅ Coordinator (gestión de watchers)
   - ✅ Lifecycle Manager (ciclo de vida)
   - ✅ Checker Runner (ejecución de checkers)
   - ✅ State Aggregator (agregación de estados)
   - ✅ Quorum rules
   - ✅ Update frequencies
   - ✅ Termination conditions

4. **Migrar desde live_watchers:**
   - Adaptar código existente
   - Mejorar según especificación

5. **Crear tests unitarios:**
   - Test de Coordinator
   - Test de Lifecycle Manager
   - Test de Checker Runner
   - Test de State Aggregator
   - Test de quorum rules

6. **Integrar con módulos:**
   - Event Mapping Layer → Event Watch Engine
   - Checker System → Event Watch Engine
   - Event Watch Engine → Strategy Engine

**Criterio de Éxito:**
- ✅ Todos los tests unitarios pasan
- ✅ Event Watch Engine cumple con especificación en `docs/services/event_watch_engine.md`
- ✅ Watchers funcionan en paralelo
- ✅ Quorum rules funcionan
- ✅ Integración con módulos funciona

**Archivos a Modificar/Crear:**
- `backend/app/core/event_watch_engine/` (nuevo directorio)
- `backend/app/core/live_watchers.py` (migrar o eliminar)
- `backend/app/main.py` (integrar Event Watch Engine)
- `backend/tests/unit/test_event_watch_engine.py` (nuevo)

---

### FASE 8: Strategy Engine

**Objetivo:** Refactorizar Strategy Engine según especificación completa.

**Documentación de Referencia:**
- 📖 `docs/services/strategy.md` - Especificación completa del Strategy Engine

**Tareas:**

1. **Revisar implementación actual:**
   - `backend/app/core/strategy.py`
   - Validar que cumple con especificación

2. **Mejorar según especificación:**
   - ✅ Condiciones de activación
   - ✅ Cálculo de target price (con ajustes de latencia)
   - ✅ Cálculo de order size (con ajustes de latencia y exposición)
   - ✅ Heurísticas adicionales para sports
   - ✅ Razones para no entrar
   - ✅ Logging estructurado con trace_id

3. **Crear modelos de datos:**
   - `MarketState` (según especificación)
   - `EventState` (según especificación)
   - `StrategyConfig` (según especificación)
   - `OrderIntent` (mejorar)

4. **Crear tests unitarios:**
   - Test de condiciones de activación
   - Test de cálculo de target price
   - Test de cálculo de order size
   - Test de heurísticas
   - Test de razones para no entrar

5. **Integrar con módulos:**
   - Event Watch Engine → Strategy Engine
   - Strategy Engine → Risk Engine

**Criterio de Éxito:**
- ✅ Todos los tests unitarios pasan
- ✅ Strategy Engine cumple con especificación en `docs/services/strategy.md`
- ✅ Cálculos de precio y tamaño funcionan
- ✅ Ajustes por latencia funcionan
- ✅ Integración con módulos funciona

**Archivos a Modificar/Crear:**
- `backend/app/core/strategy.py` (refactorizar)
- `backend/tests/unit/test_strategy.py` (nuevo o mejorar)

---

### FASE 9: Risk Engine

**Objetivo:** Refactorizar Risk Engine según especificación completa.

**Documentación de Referencia:**
- 📖 `docs/services/risk_engine.md` - Especificación completa del Risk Engine

**Tareas:**

1. **Revisar implementación actual:**
   - `backend/app/core/risk_engine.py`
   - Validar que cumple con especificación

2. **Mejorar según especificación:**
   - ✅ 8 reglas de riesgo detalladas
   - ✅ Ajustes de tamaño
   - ✅ Gestión de estado de exposición
   - ✅ Logging estructurado
   - ✅ 3 fail-safes (Red Latency, Disproportionate Exposure, Misaligned Watch Engine)

3. **Crear modelos de datos:**
   - `ExposureState` (según especificación)
   - `RuntimeState` (según especificación)
   - `RiskConfig` (mejorar)

4. **Crear tests unitarios:**
   - Test de cada regla de riesgo
   - Test de ajustes de tamaño
   - Test de gestión de exposición
   - Test de fail-safes

5. **Integrar con módulos:**
   - Strategy Engine → Risk Engine
   - Risk Engine → Execution Engine
   - Runtime Supervisor → Risk Engine

**Criterio de Éxito:**
- ✅ Todos los tests unitarios pasan
- ✅ Risk Engine cumple con especificación en `docs/services/risk_engine.md`
- ✅ Todas las reglas de riesgo funcionan
- ✅ Fail-safes funcionan
- ✅ Integración con módulos funciona

**Archivos a Modificar/Crear:**
- `backend/app/core/risk_engine.py` (refactorizar)
- `backend/tests/unit/test_risk_engine.py` (nuevo o mejorar)

---

### FASE 10: Execution Engine

**Objetivo:** Refactorizar Execution Engine según especificación completa.

**Documentación de Referencia:**
- 📖 `docs/services/execution.md` - Especificación completa del Execution Engine
- 📖 `docs/services/signatures_trazability.md` - Especificación de Signatures & Traceability

**Tareas:**

1. **Revisar implementación actual:**
   - `backend/app/core/execution.py`
   - Validar que cumple con especificación

2. **Mejorar según especificación:**
   - ✅ Flujo completo de ejecución
   - ✅ Generación de payload
   - ✅ Firma EIP-712 completa
   - ✅ Envío a Polymarket API (con rate limiting)
   - ✅ Order Lifecycle Manager (estados, state machine)
   - ✅ Fill monitoring
   - ✅ Order cancellation
   - ✅ Security (Nonce Manager, Retry Logic, Circuit Breaker)
   - ✅ Logging estructurado con trace_id

3. **Integrar Signatures & Traceability:**
   - Implementar según `docs/services/signatures_trazability.md`
   - Trazabilidad completa con trace_id
   - Almacenamiento de payloads

4. **Crear modelos de datos:**
   - `SignedOrder` (según especificación)
   - `ExecutionRecord` (según especificación)
   - `OrderStateHistory` (según especificación)

5. **Crear tests unitarios:**
   - Test de generación de payload
   - Test de firma EIP-712
   - Test de envío a Polymarket
   - Test de Order Lifecycle Manager
   - Test de fill monitoring
   - Test de trazabilidad

6. **Integrar con módulos:**
   - Risk Engine → Execution Engine
   - Execution Engine → Wallet Service
   - Execution Engine → Polymarket API

**Criterio de Éxito:**
- ✅ Todos los tests unitarios pasan
- ✅ Execution Engine cumple con especificación en `docs/services/execution.md`
- ✅ Signatures & Traceability cumple con especificación en `docs/services/signatures_trazability.md`
- ✅ Firma EIP-712 funciona
- ✅ Order lifecycle funciona
- ✅ Trazabilidad completa funciona

**Archivos a Modificar/Crear:**
- `backend/app/core/execution.py` (refactorizar)
- `backend/app/core/signatures/` (nuevo directorio para Signatures & Traceability)
- `backend/tests/unit/test_execution.py` (nuevo o mejorar)

---

### FASE 11: Historical Replay

**Objetivo:** Implementar Historical Replay completo (nuevo módulo).

**Documentación de Referencia:**
- 📖 `docs/services/historical_replay.md` - Especificación completa del Historical Replay

**Tareas:**

1. **Crear estructura de Historical Replay:**
   ```
   backend/app/core/historical_replay/
   ├── __init__.py
   ├── event_store.py          # Event Store
   ├── replay_engine.py        # Replay Engine
   └── strategy_comparator.py  # Strategy Comparator
   ```

2. **Implementar según especificación:**
   - ✅ Event Store (SQLite + JSONL)
   - ✅ Replay Engine (replay, rewind, step-by-step)
   - ✅ Strategy Comparator (A/B testing)

3. **Integrar con módulos:**
   - Todos los módulos → Event Store (logging)
   - Historical Replay → API endpoints

4. **Crear tests unitarios:**
   - Test de Event Store
   - Test de Replay Engine
   - Test de Strategy Comparator

5. **Crear API endpoints:**
   - `backend/app/api/history.py` (expandir)
   - Endpoints para replay, rewind, compare

**Criterio de Éxito:**
- ✅ Todos los tests unitarios pasan
- ✅ Historical Replay cumple con especificación en `docs/services/historical_replay.md`
- ✅ Event Store funciona
- ✅ Replay Engine funciona
- ✅ Strategy Comparator funciona

**Archivos a Modificar/Crear:**
- `backend/app/core/historical_replay/` (nuevo directorio)
- `backend/app/api/history.py` (expandir)
- `backend/tests/unit/test_historical_replay.py` (nuevo)

---

### FASE 12: Live Control

**Objetivo:** Refactorizar Live Control según especificación completa.

**Documentación de Referencia:**
- 📖 `docs/services/livecontrol.md` - Especificación completa del Live Control

**Tareas:**

1. **Revisar implementación actual:**
   - `backend/app/api/live.py`
   - `frontend/app/livecontrol/page.tsx`
   - Validar que cumple con especificación

2. **Mejorar backend según especificación:**
   - ✅ Live Control API Layer (endpoints REST + SSE)
   - ✅ Live Control State Store (in-memory)
   - ✅ Event Bus para eventos de módulos
   - ✅ SSE streaming mejorado

3. **Mejorar frontend según especificación:**
   - ✅ Vista de eventos activos
   - ✅ Vista de mercados activos
   - ✅ Vista de watchers
   - ✅ Stream de decisiones
   - ✅ Estado global del sistema

4. **Integrar con módulos:**
   - Todos los módulos → Event Bus → Live Control

5. **Crear tests unitarios:**
   - Test de Live Control API
   - Test de Event Bus
   - Test de SSE streaming

**Criterio de Éxito:**
- ✅ Todos los tests unitarios pasan
- ✅ Live Control cumple con especificación en `docs/services/livecontrol.md`
- ✅ Backend funciona correctamente
- ✅ Frontend funciona correctamente
- ✅ Integración con módulos funciona

**Archivos a Modificar/Crear:**
- `backend/app/core/live_control/` (nuevo directorio)
- `backend/app/api/live.py` (refactorizar)
- `frontend/app/livecontrol/page.tsx` (mejorar)
- `backend/tests/unit/test_live_control.py` (nuevo)

---

### FASE 13: Integración y Main Loop

**Objetivo:** Integrar todos los módulos en el main loop según arquitectura.

**Documentación de Referencia:**
- 📖 `docs/overall.md` - Arquitectura general
- 📖 `docs/algoritmo_backend.md` - Algoritmo del backend

**Tareas:**

1. **Refactorizar main loop:**
   - `backend/app/main.py`
   - Integrar todos los módulos según flujo:
     ```
     Scanner → Event Mapping → Event Watch Engine → Strategy → Risk → Execution → Metrics → Runtime Supervisor
     ```

2. **Integrar Event Bus:**
   - Todos los módulos emiten eventos
   - Live Control y Historical Replay consumen eventos

3. **Mejorar manejo de errores:**
   - Error handling robusto
   - Recovery automático
   - Logging estructurado

4. **Crear tests de integración:**
   - Test de main loop completo
   - Test de flujo end-to-end
   - Test de manejo de errores

5. **Optimizar performance:**
   - Profiling del main loop
   - Optimización de bottlenecks
   - Validar latencias

**Criterio de Éxito:**
- ✅ Todos los tests de integración pasan
- ✅ Main loop funciona según arquitectura
- ✅ Todos los módulos integrados correctamente
- ✅ Performance aceptable (< 1 segundo por tick)
- ✅ Manejo de errores robusto

**Archivos a Modificar/Crear:**
- `backend/app/main.py` (refactorizar)
- `backend/tests/integration/test_main_loop.py` (nuevo)

---

### FASE 14: Testing Completo y Validación

**Objetivo:** Asegurar que todo funciona correctamente con tests completos.

**Tareas:**

1. **Tests unitarios completos:**
   - Cobertura > 80% para código crítico
   - Todos los módulos tienen tests
   - Tests de edge cases

2. **Tests de integración completos:**
   - Flujo completo end-to-end
   - Integración entre módulos
   - Tests de performance

3. **Tests de sistema:**
   - Tests con datos reales (mocks)
   - Tests de carga
   - Tests de recuperación de errores

4. **Validación contra especificaciones:**
   - Validar que cada módulo cumple con su especificación
   - Validar que la arquitectura es correcta
   - Validar que el flujo es correcto

5. **Documentación:**
   - Actualizar README
   - Documentar cambios
   - Guía de deployment

**Criterio de Éxito:**
- ✅ Cobertura de tests > 80%
- ✅ Todos los tests pasan
- ✅ Validación contra especificaciones completa
- ✅ Documentación actualizada

---

## Orden de Ejecución Recomendado

**Fases que deben ejecutarse en orden:**

1. **FASE 0** - Preparación (base para todo)
2. **FASE 1** - Wallet Service (necesario para Execution)
3. **FASE 2** - Metrics & Observability (base para Runtime Supervisor)
4. **FASE 3** - Runtime Supervisor (necesario para seguridad)
5. **FASE 4** - Scanner (base del flujo)
6. **FASE 5** - Event Mapping Layer (crítico, nuevo)
7. **FASE 6** - Checker System (necesario para Event Watch Engine)
8. **FASE 7** - Event Watch Engine (necesario para Strategy)
9. **FASE 8** - Strategy Engine (necesario para Risk)
10. **FASE 9** - Risk Engine (necesario para Execution)
11. **FASE 10** - Execution Engine (depende de todo lo anterior)
12. **FASE 11** - Historical Replay (puede hacerse en paralelo con FASE 12)
13. **FASE 12** - Live Control (puede hacerse en paralelo con FASE 11)
14. **FASE 13** - Integración (integra todo)
15. **FASE 14** - Testing Completo (valida todo)

---

## Principios de Refactorización

### 1. Mantener Funcionalidad Existente

- ✅ No romper código que funciona
- ✅ Migrar gradualmente
- ✅ Mantener compatibilidad durante transición

### 2. Seguir Especificaciones

- ✅ Cada fase debe cumplir con su especificación en `docs/services/`
- ✅ Validar contra especificación antes de marcar como completa

### 3. Testing Continuo

- ✅ Tests unitarios para cada módulo
- ✅ Tests de integración para flujos
- ✅ No avanzar sin tests pasando

### 4. Logging y Trazabilidad

- ✅ Logging estructurado con trace_id
- ✅ Trazabilidad completa
- ✅ Facilita debugging

### 5. Documentación

- ✅ Documentar cambios
- ✅ Actualizar README
- ✅ Comentar código complejo

---

## Checklist por Fase

Para cada fase, verificar:

- [ ] Código implementado según especificación
- [ ] Tests unitarios creados y pasando
- [ ] Tests de integración creados y pasando
- [ ] Logging estructurado implementado
- [ ] Manejo de errores robusto
- [ ] Documentación actualizada
- [ ] Integración con módulos anteriores funciona
- [ ] Performance aceptable
- [ ] Código revisado y limpio

---

## Notas Importantes

1. **Código Existente:** Mucho código ya existe y puede reutilizarse. Revisar antes de reescribir.

2. **Dependencias:** Algunas fases dependen de otras. Respetar el orden.

3. **Testing:** Cada fase debe pasar tests antes de continuar. No saltar esta validación.

4. **Especificaciones:** Cada fase tiene su especificación en `docs/services/`. Seguirla estrictamente.

5. **Iteración:** Es normal iterar en fases. Mejorar gradualmente.

---

## Recursos

- **Documentación General:** `docs/overall.md`
- **Algoritmo Backend:** `docs/algoritmo_backend.md`
- **Especificaciones de Servicios:** `docs/services/*.md`
- **Código Actual:** `backend/app/core/` y `backend/app/api/`

---

**Este plan es una guía. Ajustar según necesidades y descubrimientos durante la implementación.**

