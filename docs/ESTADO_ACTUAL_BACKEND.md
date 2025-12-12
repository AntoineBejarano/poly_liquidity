# Estado Actual del Backend

**PolyLiquidity Desk – Documentación del Estado Actual del Código**

**Fecha:** Diciembre 2024  
**Fase:** FASE 0 - Preparación y Testing Infrastructure

---

## Resumen Ejecutivo

Este documento describe el estado actual del backend de PolyLiquidity Desk, identificando qué funciona, qué falta, y las dependencias entre módulos. Este análisis es fundamental para la refactorización fase por fase según el plan en `docs/PLAN_REFACTORIZACION.md`.

---

## 1. Módulos Implementados

### 1.1. Scanner Engine (`backend/app/core/scanner.py`)

**Estado:** ✅ Implementado (básico)

**Funcionalidad:**
- ✅ Búsqueda de mercados desde Polymarket API (placeholder)
- ✅ Filtrado básico de mercados (binary, OPEN, precio mínimo)
- ✅ Caching y rate limiting integrado
- ✅ Actualización de estado en memoria y DB
- ✅ Creación automática de eventos para nuevos mercados

**Limitaciones:**
- ❌ API de Polymarket no está completamente implementada (placeholder)
- ❌ Filtrado avanzado según especificación no implementado
- ❌ Normalización y enriquecimiento de datos limitado
- ❌ Logging estructurado con trace_id no implementado

**Dependencias:**
- `app.core.state` - Estado global
- `app.core.config_service` - Configuración
- `app.core.rate_limiter` - Rate limiting
- `app.core.api_cache` - Caching
- `app.models.market` - Modelo de mercado
- `app.models.event` - Modelo de evento

**Tests:** ✅ Tests unitarios creados (`tests/unit/test_scanner.py`)

---

### 1.2. Strategy Engine (`backend/app/core/strategy.py`)

**Estado:** ✅ Implementado (básico)

**Funcionalidad:**
- ✅ Cálculo de target price con ajustes de latencia
- ✅ Cálculo de order size con límites de exposición
- ✅ Ajustes por latencia (GREEN/YELLOW/RED)
- ✅ Generación de OrderIntents
- ✅ Condiciones de activación básicas

**Limitaciones:**
- ❌ Heurísticas adicionales para sports no implementadas
- ❌ Razones detalladas para no entrar no implementadas
- ❌ Logging estructurado con trace_id no implementado
- ❌ Modelos de datos según especificación incompletos

**Dependencias:**
- `app.core.state` - Estado global
- `app.core.config_service` - Configuración
- `app.core.latency_monitor` - Monitoreo de latencia

**Tests:** ✅ Tests unitarios creados (`tests/unit/test_strategy.py`)

---

### 1.3. Risk Engine (`backend/app/core/risk_engine.py`)

**Estado:** ✅ Implementado (básico)

**Funcionalidad:**
- ✅ Validación de límites de exposición por mercado
- ✅ Validación de límites de exposición global
- ✅ Validación de límites de mercados activos
- ✅ Fail-safe por latencia RED (rechaza todos los intents)
- ✅ Actualización de estado de exposición

**Limitaciones:**
- ❌ No implementa las 8 reglas de riesgo detalladas según especificación
- ❌ Ajustes de tamaño no completamente implementados
- ❌ 3 fail-safes según especificación no implementados
- ❌ Logging estructurado no implementado

**Dependencias:**
- `app.core.state` - Estado global
- `app.core.config_service` - Configuración
- `app.core.strategy` - OrderIntent
- `app.core.latency_monitor` - Monitoreo de latencia
- `app.models.exposure` - Modelo de exposición

**Tests:** ✅ Tests unitarios creados (`tests/unit/test_risk_engine.py`)

---

### 1.4. Execution Engine (`backend/app/core/execution.py`)

**Estado:** ✅ Implementado (básico)

**Funcionalidad:**
- ✅ Firma de órdenes (placeholder EIP-712)
- ✅ Envío a Polymarket API (placeholder)
- ✅ Creación de órdenes en DB
- ✅ Actualización de estado de órdenes
- ✅ Manejo de fills (placeholder)
- ✅ Rate limiting integrado
- ✅ Medición de latencia de ejecución

**Limitaciones:**
- ❌ Firma EIP-712 completa no implementada (placeholder)
- ❌ API de Polymarket no está completamente implementada
- ❌ Order Lifecycle Manager no implementado según especificación
- ❌ Fill monitoring no completamente implementado
- ❌ Signatures & Traceability no implementado
- ❌ Nonce Manager no implementado
- ❌ Logging estructurado no implementado

**Dependencias:**
- `app.core.state` - Estado global
- `app.core.wallet` - Wallet Service
- `app.core.risk_engine` - ApprovedOrderIntent
- `app.core.rate_limiter` - Rate limiting
- `app.core.latency_monitor` - Monitoreo de latencia
- `app.models.order` - Modelo de orden
- `app.models.trade` - Modelo de trade
- `app.models.position` - Modelo de posición

**Tests:** ✅ Tests unitarios creados (`tests/unit/test_execution.py`)

---

### 1.5. Wallet Service (`backend/app/core/wallet.py`)

**Estado:** ✅ Implementado (básico)

**Funcionalidad:**
- ✅ Cifrado/descifrado de private keys (Fernet)
- ✅ Cache en memoria de wallet activa
- ✅ Activación de wallet
- ✅ Garantía de solo una wallet activa
- ✅ Invalidación de cache

**Limitaciones:**
- ❌ Rotación en runtime sin reinicio no completamente implementada
- ❌ Cancelación de órdenes al cambiar wallet no implementada
- ❌ Integración con Execution Engine para cancelación no implementada
- ❌ Logging estructurado no implementado

**Dependencias:**
- `app.models.wallet` - Modelo de wallet
- `cryptography.fernet` - Cifrado

**Tests:** ✅ Tests unitarios creados (`tests/unit/test_wallet_service.py`)

---

### 1.6. Event Engine (`backend/app/core/event_engine.py`)

**Estado:** ✅ Implementado (básico)

**Funcionalidad:**
- ✅ Gestión básica de eventos
- ✅ Integración con Checker System

**Limitaciones:**
- ❌ No cumple con especificación de Event Watch Engine
- ❌ Quorum rules no implementadas
- ❌ Coordinator, Lifecycle Manager, State Aggregator no implementados
- ❌ Necesita refactorización completa según especificación

**Dependencias:**
- `app.core.checkers` - Checker System
- `app.models.event` - Modelo de evento

**Tests:** ❌ Tests no creados (necesita refactorización primero)

---

### 1.7. Checker System (`backend/app/core/checkers/`)

**Estado:** ✅ Implementado (básico)

**Funcionalidad:**
- ✅ BaseChecker abstracto
- ✅ CheckerRegistry
- ✅ Implementaciones: Sports Checker, Crypto Checker, Mock Checker
- ✅ SecretService básico

**Limitaciones:**
- ❌ No cumple completamente con especificación
- ❌ Circuit breaker por checker no implementado
- ❌ Error normalization no completamente implementado
- ❌ Timeouts y retries no completamente implementados

**Dependencias:**
- `app.models.checker_config` - Configuración de checkers
- `app.models.secret` - Secretos

**Tests:** ❌ Tests no creados (necesita refactorización primero)

---

### 1.8. Metrics (`backend/app/core/metrics.py`)

**Estado:** ❌ Placeholder (no implementado)

**Funcionalidad:**
- ❌ Solo tiene método `tick()` vacío

**Limitaciones:**
- ❌ No implementado según especificación
- ❌ Necesita implementación completa

**Dependencias:**
- Ninguna (nuevo módulo)

**Tests:** ❌ Tests no creados (necesita implementación primero)

---

### 1.9. Latency Monitor (`backend/app/core/latency_monitor.py`)

**Estado:** ✅ Implementado

**Funcionalidad:**
- ✅ Monitoreo de latencia de API
- ✅ Monitoreo de latencia de ejecución
- ✅ Cálculo de LatencyStatus (GREEN/YELLOW/RED)
- ✅ Thresholds configurables

**Dependencias:**
- Ninguna (módulo independiente)

**Tests:** ❌ Tests no creados (debería crearse)

---

### 1.10. Live Watchers (`backend/app/core/live_watchers.py`)

**Estado:** ✅ Implementado (básico)

**Funcionalidad:**
- ✅ Watchers básicos para eventos

**Limitaciones:**
- ❌ No cumple con especificación de Event Watch Engine
- ❌ Necesita refactorización completa según especificación

**Dependencias:**
- `app.core.checkers` - Checker System

**Tests:** ❌ Tests no creados (necesita refactorización primero)

---

### 1.11. Rate Limiter (`backend/app/core/rate_limiter.py`)

**Estado:** ✅ Implementado

**Funcionalidad:**
- ✅ Rate limiting por tipo de endpoint (DATA_API, TRADING_ORDER)
- ✅ Límites configurables
- ✅ Tracking de violaciones

**Dependencias:**
- Ninguna (módulo independiente)

**Tests:** ❌ Tests no creados (debería crearse)

---

### 1.12. API Cache (`backend/app/core/api_cache.py`)

**Estado:** ✅ Implementado

**Funcionalidad:**
- ✅ Caching en memoria con TTL
- ✅ Limpieza automática de entradas expiradas

**Dependencias:**
- Ninguna (módulo independiente)

**Tests:** ❌ Tests no creados (debería crearse)

---

## 2. Módulos que Necesitan Crearse

### 2.1. Event Mapping Layer

**Estado:** ❌ No existe

**Ubicación esperada:** `backend/app/core/event_mapping_layer/`

**Funcionalidad requerida:**
- Clasificación de eventos (Sports, Politics, Crypto, Finance, Weather)
- Sports Mapper (MVP) con heurísticas
- Confidence scoring
- Caching e idempotencia

**Dependencias:**
- Scanner Engine → Event Mapping Layer → Event Watch Engine

**Prioridad:** 🔴 Alta (crítico para el flujo)

---

### 2.2. Event Watch Engine

**Estado:** ❌ No existe (existe `live_watchers.py` pero no cumple especificación)

**Ubicación esperada:** `backend/app/core/event_watch_engine/`

**Funcionalidad requerida:**
- Coordinator
- Lifecycle Manager
- Checker Runner
- State Aggregator
- Quorum rules
- Update frequencies
- Termination conditions

**Dependencias:**
- Event Mapping Layer → Event Watch Engine
- Checker System → Event Watch Engine
- Event Watch Engine → Strategy Engine

**Prioridad:** 🔴 Alta (crítico para el flujo)

---

### 2.3. Runtime Supervisor

**Estado:** ❌ No existe

**Ubicación esperada:** `backend/app/core/runtime_supervisor/`

**Funcionalidad requerida:**
- Runtime Mode (GREEN/YELLOW/RED)
- Cálculo de latencia global
- Circuit Breakers (Trading, Checker, API)
- Fail-Safes (FS1, FS2, FS3)
- Integración con Metrics

**Dependencias:**
- Metrics & Observability → Runtime Supervisor
- Runtime Supervisor → Risk Engine, Strategy Engine, Execution Engine

**Prioridad:** 🔴 Alta (crítico para seguridad)

---

### 2.4. Metrics & Observability Layer

**Estado:** ❌ No existe (existe `metrics.py` pero es placeholder)

**Ubicación esperada:** `backend/app/core/metrics/`

**Funcionalidad requerida:**
- Metric Collectors (Samplers, Event Hooks)
- Metric Store (memoria + persistente)
- Alerting System
- Prometheus Exporter

**Dependencias:**
- Todos los módulos → Metrics & Observability
- Metrics & Observability → Runtime Supervisor

**Prioridad:** 🟡 Media (necesario para observabilidad)

---

### 2.5. Historical Replay

**Estado:** ❌ No existe

**Ubicación esperada:** `backend/app/core/historical_replay/`

**Funcionalidad requerida:**
- Event Store (SQLite + JSONL)
- Replay Engine
- Strategy Comparator

**Dependencias:**
- Todos los módulos → Historical Replay (logging)
- Historical Replay → API endpoints

**Prioridad:** 🟢 Baja (nice to have)

---

### 2.6. Signatures & Traceability

**Estado:** ❌ No existe (parcialmente en Execution Engine)

**Ubicación esperada:** `backend/app/core/signatures/`

**Funcionalidad requerida:**
- Trazabilidad completa con trace_id
- Almacenamiento de payloads
- OrderStateHistory

**Dependencias:**
- Execution Engine → Signatures & Traceability

**Prioridad:** 🟡 Media (necesario para auditoría)

---

## 3. Dependencias entre Módulos

### 3.1. Flujo Principal

```
Scanner → Event Mapping → Event Watch Engine → Strategy → Risk → Execution
```

**Estado actual:**
- ✅ Scanner existe (básico)
- ❌ Event Mapping no existe
- ⚠️ Event Watch Engine existe parcialmente (`event_engine.py`, `live_watchers.py`)
- ✅ Strategy existe (básico)
- ✅ Risk existe (básico)
- ✅ Execution existe (básico)

---

### 3.2. Módulos de Soporte

```
Metrics → Runtime Supervisor → Risk/Strategy/Execution
Wallet Service → Execution
Checker System → Event Watch Engine
Rate Limiter → Scanner/Execution
API Cache → Scanner
```

**Estado actual:**
- ❌ Metrics no existe (placeholder)
- ❌ Runtime Supervisor no existe
- ✅ Wallet Service existe (básico)
- ✅ Checker System existe (básico)
- ✅ Rate Limiter existe
- ✅ API Cache existe

---

## 4. Tests

### 4.1. Tests Creados

- ✅ `tests/unit/test_scanner.py` - Tests para Scanner
- ✅ `tests/unit/test_strategy.py` - Tests para Strategy
- ✅ `tests/unit/test_risk_engine.py` - Tests para Risk Engine
- ✅ `tests/unit/test_execution.py` - Tests para Execution
- ✅ `tests/unit/test_wallet_service.py` - Tests para Wallet Service
- ✅ `tests/integration/test_main_loop.py` - Tests de integración para main loop

### 4.2. Tests Faltantes

- ❌ Tests para Event Engine
- ❌ Tests para Checker System
- ❌ Tests para Latency Monitor
- ❌ Tests para Rate Limiter
- ❌ Tests para API Cache
- ❌ Tests para Config Service
- ❌ Tests para State Management

### 4.3. Cobertura Actual

**Estimación:** ~40-50% (basado en módulos con tests)

**Objetivo FASE 0:** > 60% para código crítico

---

## 5. Configuración y CI/CD

### 5.1. Configuración de Tests

- ✅ `pytest.ini` configurado
- ✅ `conftest.py` con fixtures comunes
- ✅ Estructura de directorios creada

### 5.2. CI/CD

- ✅ GitHub Actions configurado (`.github/workflows/backend-tests.yml`)
- ✅ Tests ejecutados en cada push/PR
- ✅ Coverage report generado

---

## 6. Próximos Pasos (FASE 1)

Según el plan de refactorización, la siguiente fase es:

**FASE 1: Wallet Service**

**Tareas:**
1. Revisar implementación actual
2. Mejorar según especificación en `docs/services/wallet_service.md`
3. Crear tests unitarios (ya creados, mejorar si es necesario)
4. Integrar con Execution Engine

---

## 7. Notas Importantes

1. **Código Existente:** Mucho código ya existe y puede reutilizarse. No reescribir desde cero.

2. **Placeholders:** Varios módulos tienen placeholders (especialmente APIs de Polymarket). Estos deben implementarse según especificación.

3. **Dependencias:** Respetar el orden de fases según dependencias entre módulos.

4. **Testing:** Cada fase debe pasar tests antes de continuar.

5. **Especificaciones:** Cada módulo tiene su especificación en `docs/services/`. Seguirla estrictamente.

---

## 8. Referencias

- **Plan de Refactorización:** `docs/PLAN_REFACTORIZACION.md`
- **Especificaciones de Servicios:** `docs/services/*.md`
- **Arquitectura General:** `docs/overall.md`
- **Código Actual:** `backend/app/core/` y `backend/app/api/`

---

**Este documento debe actualizarse después de cada fase de refactorización.**

