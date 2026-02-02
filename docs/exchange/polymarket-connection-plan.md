# Plan de Configuración Completa de Polymarket - PolyLiquidity Desk

**Propósito**: Plan detallado para configurar completamente la conexión con Polymarket, obtener toda la información disponible y testear cada fase, alineado con la arquitectura de PolyLiquidity Desk.

**Audiencia**: Desarrolladores implementando o manteniendo la integración con Polymarket.

**Última actualización**: 2025-01-27

**Convenciones de Nomenclatura**:
- **execution_mode**: El sistema usa internamente `DRY_RUN`, `PAPER`, `LIVE`. `DRY_RUN` es equivalente a `SIMULATION` (alias). En este documento usamos `DRY_RUN` para consistencia con el código interno.
- **Endpoints canónicos**: Ver sección "Endpoints Canónicos" más abajo.

**Estado de Implementación (Estado Real)**: 
- ✅ Fase 0: COMPLETADA (6/6 tests pasando)
- ✅ Fase 1: COMPLETADA (5/5 tests pasando)
- ✅ Fase 2: COMPLETADA (7/7 tests pasando)
- ✅ Fase 2.5: COMPLETADA (8/8 tests pasando)
- ✅ Fase 3: COMPLETADA (9/9 tests pasando)
- ✅ Fase 4: COMPLETADA (8/8 tests pasando)
- ✅ Fase 5: COMPLETADA (8/8 tests pasando)

**Nota**: Este documento contiene tanto el **Plan** (lo que debería existir) como el **Estado Real** (lo que existe hoy). Ver sección "Estado de Implementación Detallado" para detalles.

**Filosofía**: Este es un sistema con circuit breakers y risk engine, no un script. Todas las fases deben respetar protecciones y modos de ejecución.

---

## Resumen Ejecutivo

Este plan organiza la configuración de Polymarket en **6 fases progresivas** (incluyendo Fase 0), cada una con:
- ✅ Tests unitarios
- ✅ Tests de integración
- ✅ Endpoints de API documentados
- ✅ Gates / No-Go criteria
- ✅ Colección de Postman para testing manual

### Fases (Orden de Prioridad)

0. **Fase 0: Modo y Protecciones** - Verificar execution_mode y parámetros protegidos (ANTES de tocar APIs)
1. **Fase 1: Configuración y Autenticación** - Verificar credenciales y conexión básica
2. **Fase 2: Datos Públicos (Gamma API)** - Events, markets, metadata públicos
3. **Fase 2.5: WebSocket MARKET → Orderbook Engine** - WS MARKET channel alimenta State Cache (MVP real)
4. **Fase 3: Datos de Cuenta (CLOB API - Lectura)** - Balance, órdenes, trades del usuario
5. **Fase 4: Operaciones de Trading (CLOB API - Escritura)** - Crear/cancelar órdenes
6. **Fase 5: WebSocket USER** - Actualizaciones de órdenes/trades del usuario

### Principios Clave

1. **Endpoints REST como Facade**: Los endpoints REST sirven datos desde State Cache, no hacen fetch directo a Polymarket cada vez.
2. **Estrategia lee State Cache**: La estrategia (Decision Graph) lee State Cache; los conectores y WS alimentan el cache.
3. **Protecciones antes de Trading**: No se puede tradear sin verificar execution_mode, checkers saludables, y parámetros protegidos.

### Endpoints Canónicos

**IMPORTANTE**: Usar siempre estos endpoints canónicos. Si hay aliases, se documentan aquí.

#### Sistema y Configuración
- `GET /system/config/execution-mode` - Modo de ejecución actual
- `GET /system/config/protected-parameters` - Parámetros protegidos
- `GET /system/config/{key}` - Configuración específica

#### Checkers y Health
- `GET /checkers/health` - Estado de salud de checkers y quorum
- `GET /api/checkers/health` - **ALIAS** (redirige a `/checkers/health`)

#### Risk Engine
- `GET /risk/status` - Estado del Risk Engine y circuit breakers
- `GET /api/risk/status` - **ALIAS** (redirige a `/risk/status`)

#### Polymarket
- `GET /api/polymarket/*` - Todos los endpoints de Polymarket
- `GET /api/polymarket/health` - Health check de Gamma API
- `GET /api/polymarket/websocket/status` - Estado de conexiones WebSocket
- `GET /api/polymarket/orderbook/{asset_id}` - Orderbook desde State Cache

**Nota**: Los routers FastAPI pueden tener prefijos diferentes (`/system`, `/api/polymarket`, etc.). Los endpoints canónicos son los que se usan en producción.

---

## Fase 0: Modo y Protecciones

### Objetivo
Verificar que el sistema está en modo seguro (DRY_RUN/PAPER) y que los parámetros protegidos están correctamente configurados **ANTES** de tocar cualquier API de Polymarket.

**Criterio de Done**: "Puedo correr Fase 1-3 en DRY_RUN/PAPER sin riesgo y sin llaves reales".

**Nota sobre execution_mode**: El sistema usa internamente `DRY_RUN` (equivalente a `SIMULATION`), `PAPER`, y `LIVE`. En este documento usamos `DRY_RUN` para consistencia con el código.

### Tests Requeridos

#### Test 0.1: Verificar Execution Mode
- ✅ `execution_mode` está configurado (DRY_RUN, PAPER, o LIVE)
- ✅ Si es LIVE, requiere confirmación explícita (handshake)
- ✅ En DRY_RUN/PAPER, no se requieren llaves reales
- ✅ `DRY_RUN` es equivalente a `SIMULATION` (alias interno)

#### Test 0.2: Verificar Parámetros Protegidos
- ✅ `allow_zero_checker` está configurado (default: `false`)
- ✅ `quorum_base` está configurado (default: `2`)
- ✅ `execution_mode` no puede cambiarse a LIVE sin confirmation_token
- ✅ Parámetros críticos requieren confirmación

#### Test 0.3: Verificar Checkers Saludables
- ✅ Al menos 1 checker saludable disponible (para Fase 3-4)
- ✅ Si `allow_zero_checker=false` y 0 checkers → sistema en modo DEGRADED
- ✅ Quorum efectivo calculado correctamente

#### Test 0.4: Verificar Risk Engine
- ✅ Risk Engine está activo
- ✅ Circuit breakers configurados
- ✅ Kill switches disponibles

### Gates / No-Go Criteria

**🔴 NO proceder a Fase 1-3 si:**
- `execution_mode = LIVE` sin confirmation_token válido
- `allow_zero_checker = true` sin confirmación explícita
- 0 checkers saludables y `allow_zero_checker = false` (sistema degradado)

**✅ OK proceder con datos públicos + WS MARKET si:**
- `execution_mode = DRY_RUN` o `PAPER`
- Parámetros protegidos tienen valores seguros
- Al menos 1 checker saludable (o `allow_zero_checker = true` con confirmación)

**Permisos según `allow_zero_checker=true`:**
- ✅ **WS MARKET + cache**: Sí permitido (datos públicos, no requiere checkers)
- 🔴 **Endpoints de trading (Fase 4)**: NO permitido si `healthy_checkers == 0` (gate crítico)
- ⚠️ **CLOB lectura (balance/orders/trades)**: Depende de política interna:
  - Si requiere checkers para account → NO permitido con 0 checkers
  - Si solo requiere checkers para trading → Sí permitido (lectura/observabilidad)

**🔴 NO proceder a Fase 4 (Trading) si:**
- `healthy_checkers == 0` (independientemente de `allow_zero_checker`)
- **Razón**: 0 checkers = modo "operational" (lectura/observabilidad), NO trading
- **Gate crítico**: `trading_permitted = (healthy_checkers > 0)`

### Endpoints de API (Canónicos)

```python
GET /system/config/execution-mode
# Obtener modo de ejecución actual

GET /system/config/protected-parameters
# Listar parámetros protegidos y sus valores

GET /checkers/health
# Estado de salud de checkers y quorum efectivo

GET /risk/status
# Estado del Risk Engine y circuit breakers
```

**Nota**: Estos son los endpoints canónicos. Ver sección "Endpoints Canónicos" para más detalles.

### Postman Collection

```json
{
  "name": "Fase 0: Modo y Protecciones",
  "item": [
    {
      "name": "0.1 Verificar Execution Mode",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/system/config/execution-mode"
      }
    },
    {
      "name": "0.2 Verificar Parámetros Protegidos",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/system/config/protected-parameters"
      }
    },
    {
      "name": "0.3 Verificar Checkers",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/checkers/health"
      }
    },
    {
      "name": "0.4 Verificar Risk Engine",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/risk/status"
      }
    }
  ]
}
```

---

## Fase 1: Configuración y Autenticación

### Objetivo
Verificar que las credenciales están correctamente configuradas y que podemos autenticarnos con Polymarket.

### Tests Requeridos

#### Test 1.1: Verificar Variables de Entorno
- ✅ `PRIVATE_KEY` está configurada (opcional en DRY_RUN/PAPER)
- ✅ `FUNDER_ADDRESS` o `POLYMARKET_PROXY_ADDRESS` está configurada (opcional en DRY_RUN/PAPER)
- ✅ `CHAIN_ID` está configurada (default: 137)
- ✅ `RPC_URL` está configurada (opcional pero recomendado)

#### Test 1.2: Inicialización del Cliente
- ✅ Cliente CLOB se inicializa correctamente (o simula en DRY_RUN/SIMULATION)
- ✅ Credenciales API se generan/derivan correctamente (si aplica)
- ✅ Cliente está disponible o simulado según execution_mode

#### Test 1.3: Health Check de APIs
- ✅ Gamma API está disponible (`/api/polymarket/health`)
- ✅ CLOB API está disponible o simulado según execution_mode

### Gates / No-Go Criteria

**🔴 NO proceder a Fase 2 si:**
- Gamma API no responde (status != "ok")
- En modo LIVE, CLOB API no está disponible

**✅ OK proceder si:**
- Gamma API responde correctamente
- En DRY_RUN/PAPER, cliente simulado funciona
- En LIVE, CLOB API autenticado correctamente

### Endpoints de API

```python
GET /api/polymarket/connection/status
# Retorna estado de conexión y configuración

GET /api/polymarket/connection/test-auth
# Prueba autenticación con CLOB API (o simula en DRY_RUN)
```

### Validación Recomendada

- **Modo DRY_RUN/PAPER**: Sin llaves reales, `ok()` + `server_time()` + status interno
- **Modo LIVE**: Autenticación real + balance verificable

---

## Fase 2: Datos Públicos (Gamma API)

### Objetivo
Obtener y verificar acceso a todos los datos públicos de Polymarket: events, markets, metadata.

### Tests Requeridos

#### Test 2.1: Listar Events
- ✅ Obtener lista de events con paginación
- ✅ Filtrar por `closed=false` (solo activos)
- ✅ Verificar estructura de respuesta (id, slug, title, markets, etc.)
- ✅ Verificar caching funciona (5s TTL)

#### Test 2.2: Obtener Event Específico
- ✅ Obtener event por ID
- ✅ Verificar información completa del event
- ✅ Verificar que incluye markets asociados

#### Test 2.3: Obtener Market
- ✅ Obtener market por ID
- ✅ Obtener market por slug
- ✅ Verificar campos: conditionId, clobTokenIds, bestBid, bestAsk, volume24hr

#### Test 2.4: Búsqueda
- ✅ Buscar events/markets por query
- ✅ Verificar resultados de búsqueda

### Gates / No-Go Criteria

**🔴 NO proceder a Fase 2.5 si:**
- Rate limiting falla (429 errors frecuentes)
- Caching no funciona
- Paginación no funciona correctamente

**✅ OK proceder si:**
- Scan estable + caching + paginación funcionando
- Logs estructurados de filtros disponibles

### Endpoints de API (Ya Existen)

```python
GET /api/polymarket/events
GET /api/polymarket/events/{event_id}
GET /api/polymarket/markets/{market_id}
GET /api/polymarket/markets/slug/{slug}
GET /api/polymarket/search?q={query}
GET /api/polymarket/health
```

### Validación Recomendada

- **Scan estable**: Puede obtener 1000+ markets sin errores
- **Caching**: Respuestas cacheadas correctamente (5s TTL)
- **Paginación**: Funciona con offset/limit
- **Logs estructurados**: Filtros y resultados logueados

### Riesgos y Mitigación

**Riesgo A: Rate Limits + Degradación Silenciosa**

- **Qué pasa con 429**: Backoff exponencial, circuit breaker, fallback a cache
- **Qué pasa con 5xx**: Retry con backoff, usar cache stale si disponible
- **Métricas mínimas**: Latencia < 300ms, error rate < 1%, staleness del cache < 10s

---

## Fase 2.5: WebSocket MARKET → Orderbook Engine

### Objetivo
Conectar WS MARKET channel al Orderbook Engine y alimentar State Cache. **Esta es la fuente real/rápida de datos de orderbook y precio**.

**Criterio de Done**: Orderbook Engine consume WS MARKET, publica a State Cache, y Strategy (Decision Graph) lee desde cache.

### Tests Requeridos

#### Test 2.5.1: Conexión WebSocket MARKET Channel
- ✅ Conectar a WebSocket MARKET channel (público, no requiere auth)
- ✅ Suscribirse a un asset_id específico
- ✅ Recibir mensajes de orderbook (snapshot completo)
- ✅ Recibir mensajes de price_change

#### Test 2.5.2: Orderbook Engine Integration
- ✅ Orderbook Engine recibe mensajes WS
- ✅ Parsea payload (bids/asks como strings → floats)
- ✅ Mantiene top-20 bids/asks en memoria
- ✅ Calcula BBO (best bid/ask), spread, midpoint

#### Test 2.5.3: State Cache Publishing
- ✅ Orderbook Engine publica a State Cache con key `pm.orderbook.{asset_id}`
- ✅ Incluye `staleness_ms` en el estado
- ✅ TTL configurado (120s)
- ✅ State Cache actualiza correctamente

#### Test 2.5.4: Strategy Consumption
- ✅ Decision Graph puede leer `orderbook_state` desde State Cache
- ✅ Strategy usa orderbook_state, no `last_price` de REST
- ✅ Verificar que staleness se respeta

#### Test 2.5.5: Orchestrator Ref-Count
- ✅ Suscripción con ref-count funciona (múltiples strategies pueden suscribirse)
- ✅ Auto subscribe/unsubscribe WS cuando ref_count pasa 0↔1
- ✅ No hay memory leaks (ref_count nunca negativo)

### Gates / No-Go Criteria

**🔴 NO proceder a Fase 3 si:**
- Book staleness > 5000ms (5 segundos)
- Ref-count no funciona (memory leaks)
- State Cache no se actualiza
- Strategy no puede leer desde cache

**✅ OK proceder si:**
- Book staleness < 1000ms (1 segundo)
- Ref-count funciona correctamente
- Cache keys por asset_id disponibles
- Strategy lee desde cache exitosamente

### Endpoints de API (Control)

```python
GET /api/polymarket/websocket/status
# Estado de conexiones WebSocket MARKET

GET /api/polymarket/orderbook/{asset_id}
# Obtener orderbook desde State Cache (NO desde Polymarket directo)
# Incluye staleness_ms y metadata

GET /api/polymarket/markets/{market_id}/orderbook
# Facade: sirve desde State Cache, expone staleness
```

### Validación Recomendada

- **Book staleness < X ms**: Configurable (default: 1000ms)
- **Ref-count suscripciones**: Funciona correctamente
- **Cache keys por asset_id**: `pm.orderbook.{asset_id}` disponibles
- **Strategy lee cache**: Decision Graph usa `orderbook_state`, no REST

### Arquitectura

```
WS MARKET Channel → OrderbookWSRouter → OrderbookEngine → State Cache
                                                              ↓
                                                    Decision Graph (Strategy)
```

**IMPORTANTE**: Los endpoints REST tipo `/markets/{id}/orderbook` o `/markets/{id}/price` deben servir desde State Cache (con staleness/lag), NO hacer fetch directo a Polymarket cada vez.

### State Cache: In-Memory First, Redis Optional (Money-First)

**Filosofía**: Para hacer dinero rápido, latencia mínima es crítica.

**Implementación**:
- **Orderbook Engine**: Mantiene top-N en RAM (ultra rápido, sin I/O)
- **State Cache = Interfaz**: Abstracción sobre implementaciones concretas

**Implementaciones**:
1. **`InMemoryStateCache`** (default para latencia mínima):
   - Dict/TTL en memoria del proceso
   - Latencia: < 1ms
   - Uso: Single-process, latencia crítica
   - **Límites críticos (SaaS)**:
     - `max_asset_ids_per_instance`: Límite de asset_ids suscritos (ej: 100)
     - `max_total_levels_cached`: Límite total de niveles (ej: 2000 = 100 assets × 20 levels)
     - **Eviction policy**: LRU por asset_id (si se alcanza límite, evictar menos usado)
     - **Métricas**: RSS y "cache entries" en smoke report
   - **Riesgos en SaaS**:
     - Muchos asset_ids suscritos = RAM crece (mitigado con límites)
     - Deploy reinicia y "pierde estado" (no grave, pero afecta UX - aceptable para datos públicos)
     - Si escalas a 2 instancias, cada una tiene su propio book (inconsistente - aceptable para datos públicos, no para estado de usuario)

2. **`RedisStateCache`** (si se necesita horizontal):
   - Redis para multi-process / multi-instance / persistencia ligera
   - Latencia: 1-5ms (depende de red)
   - Uso: Horizontal scaling, multi-instance
   - **Recomendación**: Migrar a Redis solo cuando haya demanda real de horizontal scaling

**En el smoke report**:
- `cache_backend`: `"memory"` o `"redis"` (string, no union type)
- `cache_write_ms`, `cache_read_ms`: Métricas de latencia del backend
- `cache_entries`: Número de entradas en cache
- `cache_rss_mb`: Memoria RSS usada por cache

**Recomendación Money-First**: Empezar con `InMemoryStateCache` con límites estrictos. Migrar a Redis solo si necesitas horizontal scaling o consistencia multi-instance.

### Contrato Mínimo de Orderbook State

El endpoint `GET /api/polymarket/orderbook/{asset_id}` retorna un `orderbook_state` con el siguiente contrato mínimo (para smoke/observabilidad):

```json
{
  "cache_key": "pm.orderbook.{asset_id}",
  "orderbook": {
    "bids": [
      {"price": 0.48, "size": 30},
      {"price": 0.49, "size": 20}
    ],
    "asks": [
      {"price": 0.52, "size": 25},
      {"price": 0.53, "size": 60}
    ],
    "best_bid_price": 0.49,
    "best_ask_price": 0.52,
    "midpoint": 0.505,
    "staleness_ms": 150,
    "ts_last_update": 1234567890,
    "integrity": {
      "hash": "0x0abcdef1234567890abcdef1234567890abcdef"
    },
    "source": "ws_market"
  }
}
```

**Campos requeridos**:
- `bids`, `asks`: Top-N niveles (top-20 por defecto)
- `best_bid_price`, `best_ask_price`, `midpoint`: Precios calculados
- `staleness_ms`: Tiempo desde última actualización (ms)
- `ts_last_update`: Timestamp de última actualización
- `integrity.hash`: Hash del mensaje WS (si existe)
- `source`: Siempre `"ws_market"` (para que nadie meta REST silentamente)

**Latency Budget por Tramo** (Money-First):

Para hacer dinero rápido, necesitas saber dónde pierdes edge. El `orderbook_state` debe incluir timestamps por tramo:

```json
{
  "orderbook": {
    "ts_ws_exchange": 1234567890000,  // Timestamp del exchange (si existe en msg WS)
    "ts_received_local": 1234567890150,  // Timestamp cuando recibimos el msg localmente
    "ts_published_cache": 1234567890200,  // Timestamp cuando se publicó en cache
    "ts_read_local": 1234567890250,  // Timestamp cuando se leyó en el endpoint
    "latency_breakdown": {
      "ws_last_msg_age_ms": 150,  // Edad del último msg recibido (ahora - ts_received_local)
      "ingest_to_cache_ms": 50,  // Tiempo desde recepción hasta cache write (ts_published_cache - ts_received_local)
      "cache_read_ms": 50,  // Tiempo de lectura en endpoint (ts_read_local - ts_published_cache)
      "end_to_end_ms": 250  // WS timestamp → ahora (ahora - ts_ws_exchange)
    }
  }
}
```

**Por qué**: Esto permite identificar dónde se pierde latencia:
- "WS llega rápido pero publicar tarda" → problema en Orderbook Engine
- "Redis lento" → problema en cache backend
- "WS exchange timestamp muy viejo" → problema en Polymarket

**Por qué**: Este contrato ayuda a que el smoke no dependa de campos "accidentales" y garantiza consistencia.

---

## Fase 3: Datos de Cuenta (CLOB API - Lectura)

### Objetivo
Obtener información de la cuenta del usuario: balance, órdenes abiertas, trades históricos.

### Tests Requeridos

#### Test 3.1: Obtener Balance
- ✅ Obtener balance USDC de la cuenta
- ✅ Verificar formato correcto (decimales: USDC tiene 6 decimales)
- ✅ Verificar que balance >= 0
- ✅ Verificar unidades: `balance_usdc` en USDC (no en wei o unidades menores)

#### Test 3.2: Obtener Órdenes Abiertas
- ✅ Listar todas las órdenes abiertas
- ✅ Filtrar por market/condition_id
- ✅ Filtrar por token_id/asset_id
- ✅ Verificar estructura: id, token_id, price, size, side, status

#### Test 3.3: Obtener Orden Específica
- ✅ Obtener orden por order_id/order_hash
- ✅ Verificar información completa

#### Test 3.4: Obtener Trades
- ✅ Listar trades históricos
- ✅ Filtrar por market, taker, maker
- ✅ Filtrar por rango de tiempo (before/after)
- ✅ Verificar estados: MATCHED, MINED, CONFIRMED, RETRYING, FAILED
- ✅ Verificar state machine: PENDING → SUBMITTED → OPEN → FILLED/CANCELLED

#### Test 3.5: Verificar Order Scoring
- ✅ Verificar si una orden está "scoring" (elegible para recompensas)
- ✅ Verificar múltiples órdenes

### Gates / No-Go Criteria

**✅ OK para lectura/observabilidad (Fase 3) si:**
- Balance correcto + reconcile órdenes/trades funciona
- Al menos 1 checker saludable (o `allow_zero_checker=true` confirmado para modo "operational")
- **Nota**: Fase 3 permite lectura/observabilidad incluso con 0 checkers si `allow_zero_checker=true`

**🔴 NO proceder a Fase 4 (Trading) si:**
- `healthy_checkers == 0` (independientemente de `allow_zero_checker`)
- **Gate crítico**: `trading_permitted = (healthy_checkers > 0)`
- **Razón**: 0 checkers = modo "operational" (solo lectura/observabilidad), NO trading
- Balance incorrecto o no disponible
- No se puede reconciliar órdenes/trades

### Endpoints de API Necesarios

```python
GET /api/polymarket/account/balance
# Obtener balance USDC (desde CLOB API)

GET /api/polymarket/account/orders
# Listar órdenes abiertas (con filtros opcionales)

GET /api/polymarket/account/orders/{order_id}
# Obtener orden específica

GET /api/polymarket/account/trades
# Listar trades históricos (con filtros opcionales)

GET /api/polymarket/account/orders/{order_id}/scoring
# Verificar si orden está scoring
```

### Validación Recomendada

- **Balance correcto**: Unidades correctas (USDC, no wei), decimales correctos (6)
- **Reconcile órdenes/trades**: Estado interno coincide con Polymarket
- **State machine**: Estados de orden/trade correctos (PENDING → SUBMITTED → OPEN → FILLED)

### Riesgos y Mitigación

**Riesgo C: Order Lifecycle y Estados de Trade**

- **State machine esperado**: 
  - Orden: `PENDING` → `SUBMITTED` → `OPEN` → `FILLED` / `CANCELLED` / `FAILED`
  - Trade: `MATCHED` → `MINED` → `CONFIRMED` / `RETRYING` / `FAILED`
- **Reconciliación**: Comparar estado interno con estado de Polymarket periódicamente
- **Orphaned orders**: Detectar y manejar órdenes huérfanas

**Riesgo D: Precisión de Tamaños/Decimales**

- **Unidades**: Validar shares vs USDC, `size_usdc` vs `size`
- **Rounding**: Verificar redondeo correcto (min tick/step si aplica)
- **Consistencia**: `size_usdc` debe ser consistente con `size * price`

---

## Fase 4: Operaciones de Trading (CLOB API - Escritura)

### Objetivo
Realizar operaciones de trading: crear órdenes limit y market, cancelar órdenes.

### Tests Requeridos

#### Test 4.1: Crear Limit Order
- ✅ Crear orden limit BUY
- ✅ Crear orden limit SELL
- ✅ Verificar que orden se crea correctamente
- ✅ Verificar que aparece en órdenes abiertas
- ✅ Verificar prechecks: risk engine, balance, exposure

#### Test 4.2: Crear Market Order
- ✅ Crear market order BUY (FOK)
- ✅ Crear market order SELL (IOC)
- ✅ Verificar ejecución inmediata
- ✅ Verificar prechecks: risk engine, balance, exposure

#### Test 4.3: Cancelar Orden
- ✅ Cancelar orden específica
- ✅ Verificar que orden desaparece de abiertas
- ✅ Verificar estado cambia a CANCELLED

#### Test 4.4: Cancelar Todas las Órdenes
- ✅ Cancelar todas las órdenes abiertas
- ✅ Verificar que todas desaparecen

### Gates / No-Go Criteria

**🔴 NO proceder a producción si:**
- `healthy_checkers == 0` → **Trading NO permitido** (modo "operational" solo)
- `pm.warmup.ready != true` → **Warm-up no completado** (gate adicional)
- Prechecks de risk engine no funcionan
- Cancel policy no está definida
- Rollback seguro no está implementado
- Execution mode no está verificado (no puede ser LIVE sin confirmación)

**✅ OK proceder si:**
- `healthy_checkers > 0` → Trading permitido
- `pm.warmup.ready == true` → Warm-up completado (gate adicional)
- Prechecks + risk engine + cancel policy + rollback seguro funcionan
- Execution mode verificado correctamente

**Nota**: Los gates de trading están sincronizados:
- **Gate 1 (Fase 0/3/4)**: `healthy_checkers > 0` + risk engine + execution_mode
- **Gate 2 (Warm-up)**: `pm.warmup.ready == true`
- Ambos deben cumplirse para trading permitido

### Endpoints de API Necesarios

```python
POST /api/polymarket/trading/orders/limit
# Crear limit order
# Body: {token_id, price, size, side, order_type}
# Prechecks: risk engine, balance, exposure

POST /api/polymarket/trading/orders/market
# Crear market order
# Body: {token_id, amount, side, order_type}
# Prechecks: risk engine, balance, exposure

DELETE /api/polymarket/trading/orders/{order_id}
# Cancelar orden específica

DELETE /api/polymarket/trading/orders
# Cancelar todas las órdenes
```

### Cancel/Replace Philosophy

**Cuándo cancelamos:**
- Orden stale (no actualizada en X tiempo)
- Precio drift > threshold
- Risk engine detecta violación
- Circuit breaker activado (YELLOW/RED)

**Cuándo dejamos resting:**
- Orden reciente y válida
- Precio dentro de rango aceptable
- Risk engine OK
- Sistema en GREEN

**Qué hacemos en YELLOW/RED:**
- **YELLOW**: Cancelar órdenes nuevas, mantener resting
- **RED**: Cancelar todas las órdenes, pausar trading

### Kill Switches Específicos (Money-First)

Para market making, necesitas kills específicos que protejan contra pérdidas por datos stale:

**1. Circuit Breaker "DATA_FEED"**:
- **Trigger**: WS no recibe mensajes en X ms (ej: 5000ms)
- **Acción YELLOW**: Cancelar órdenes nuevas, mantener resting
- **Acción RED**: Cancelar todas las órdenes + pause trading
- **Recovery**: Reconexión automática + resubscribe

**2. Circuit Breaker "CACHE_STALE"**:
- **Trigger**: `staleness_ms > threshold` (ej: 2000ms)
- **Acción YELLOW**: No nuevas órdenes, mantener resting
- **Acción RED**: Cancelar todas las órdenes + pause trading
- **Recovery**: Cache se actualiza + staleness < threshold

**Política ligada a Cancel Policy**:
- **YELLOW**: Cancelar órdenes nuevas, mantener resting
- **RED**: Cancelar todas las órdenes, pausar trading

**Implementación**:
- Estos circuit breakers deben estar integrados con el Risk Engine
- Deben exponerse en `/risk/status` como `circuit_breakers.DATA_FEED` y `circuit_breakers.CACHE_STALE`

### Rate Limit Plan para WebSocket (No Solo REST)

Para REST ya tienes mitigación (429/backoff/cache stale). Para WS necesitas:

**1. Reconnect Backoff con Jitter**:
- Backoff exponencial con jitter aleatorio
- Evita "thundering herd" en reconexión masiva
- Ejemplo: `backoff_ms = min(1000 * 2^attempt + random(0, 1000), 60000)`

**2. Resubscribe Replay con Lista de Asset IDs Activa**:
- Mantener lista de `asset_ids` suscritos en memoria
- En reconexión, resubscribir automáticamente todos los `asset_ids` activos
- Evita pérdida de suscripciones en reconexión

**3. Staleness Breaker**:
- Si no llega book en X segundos (ej: 5s) → breaker YELLOW/RED
- Conectado con Circuit Breaker "DATA_FEED"

**4. Drop Policy para MARKET y USER** (Política Canónica):
- **MARKET**: Si la cola crece, dropear updates intermedios, pero mantener "último snapshot válido"
  - Si cola > threshold, dropear mensajes antiguos, mantener último snapshot
  - Permite latencia mínima para datos públicos
- **USER**: Nunca dropear, bloquear si cola llena (esperar procesamiento)
  - Mensajes críticos (CONFIRMED, FAILED) nunca se dropean
  - Si cola llena, bloquear hasta que haya espacio
  - Garantiza integridad de órdenes/trades del usuario
- **Implementación**: 
  - MARKET: Cola con tamaño máximo, dropear mensajes antiguos si cola llena
  - USER: Cola con tamaño máximo, bloquear si cola llena (no dropear)

### Validación Recomendada

- **Prechecks**: Risk engine, balance, exposure verificados antes de crear orden
- **Risk engine**: Validaciones funcionan correctamente
- **Cancel policy**: Cuándo cancelar vs dejar resting definido
- **Rollback seguro**: Si falla, rollback correcto

---

## Fase 5: WebSocket USER (Órdenes/Trades del Usuario)

### Objetivo
Conectar WS USER channel para recibir actualizaciones en tiempo real de órdenes y trades del usuario.

### Tests Requeridos

#### Test 5.1: Conexión WebSocket USER Channel
- ✅ Conectar a WebSocket USER channel (requiere autenticación)
- ✅ Autenticarse correctamente con API keys
- ✅ Recibir mensajes de trades (MATCHED, MINED, CONFIRMED, RETRYING, FAILED)
- ✅ Recibir mensajes de órdenes (PLACEMENT, UPDATE, CANCELLATION)

#### Test 5.2: Reconexión Automática
- ✅ Verificar reconexión automática en caso de desconexión
- ✅ Verificar que se mantiene la suscripción
- ✅ Verificar que no se pierden mensajes críticos

#### Test 5.3: Backpressure y Drop Policy
- ✅ Política canónica: USER nunca dropear, bloquear si cola llena (esperar procesamiento)
- ✅ Mensajes críticos (CONFIRMED, FAILED) nunca se dropean
- ✅ Si cola llena, bloquear hasta que haya espacio (no dropear)

### Gates / No-Go Criteria

**🔴 NO proceder a producción si:**
- Reconexión no funciona
- Se pierden mensajes críticos
- Backpressure no manejado

**✅ OK proceder si:**
- Fills y órdenes en tiempo real, sin polling
- Reconexión automática funciona
- Backpressure manejado correctamente

### Endpoints de API Necesarios

```python
GET /api/polymarket/websocket/status
# Estado de conexiones WebSocket USER

POST /api/polymarket/websocket/subscribe/user
# Suscribirse a USER channel

POST /api/polymarket/websocket/unsubscribe/market
# Desuscribirse de MARKET channel
# Body: {asset_id, owner_key}

POST /api/polymarket/websocket/unsubscribe/user
# Desuscribirse de USER channel
# Body: {owner_key}
```

### Validación Recomendada

- **Fills y órdenes en tiempo real**: Sin polling, actualizaciones inmediatas
- **Reconexión**: Automática, mantiene suscripción
- **Resubscribe**: Funciona correctamente después de reconexión
- **Backpressure**: Política de drop definida y funcionando
- **Drop policy**: Mensajes críticos nunca se dropean

---

## Checklist de Implementación

**Nota**: Este checklist refleja el **Plan** (lo que debería existir). Para el **Estado Real** (lo que existe hoy), ver sección "Estado de Implementación Detallado".

### Fase 0: Modo y Protecciones
- ✅ DONE: Crear tests para verificación de execution_mode
- ✅ DONE: Crear tests para parámetros protegidos
- ✅ DONE: Crear tests para checkers saludables
- ✅ DONE: Implementar endpoints de verificación
- ✅ DONE: Agregar a colección Postman

### Fase 1: Configuración
- ✅ DONE: Crear tests unitarios para verificación de configuración
- ✅ DONE: Crear tests de integración para autenticación
- ✅ DONE: Implementar endpoints `/api/polymarket/connection/status` y `/test-auth`
- ✅ DONE: Agregar a colección Postman

### Fase 2: Datos Públicos
- ✅ DONE: Crear tests para todos los endpoints de Gamma API
- ✅ DONE: Verificar que todos los endpoints existentes funcionan
- ✅ DONE: Verificar caching y rate limiting
- ✅ DONE: Agregar a colección Postman

### Fase 2.5: WebSocket MARKET → Orderbook Engine
- ✅ DONE: Crear tests para WS MARKET connection
- ✅ DONE: Integrar Orderbook Engine con WS
- ✅ DONE: Implementar State Cache publishing
- ✅ DONE: Verificar Strategy puede leer desde cache
- ✅ DONE: Implementar ref-count orchestrator
- ✅ DONE: Agregar endpoints de control

### Fase 3: Datos de Cuenta
- ✅ DONE: Crear tests para balance, órdenes, trades
- ✅ DONE: Implementar endpoints de cuenta
- ✅ DONE: Verificar precisión de decimales/unidades
- ✅ DONE: Implementar reconcile de órdenes/trades
- ✅ DONE: Agregar a colección Postman

### Fase 4: Trading
- ✅ DONE: Crear tests para crear/cancelar órdenes
- ✅ DONE: Implementar endpoints de trading
- ✅ DONE: Agregar prechecks (risk engine, balance, exposure)
- ✅ DONE: Implementar cancel/replace philosophy
- ✅ DONE: Agregar validaciones de riesgo
- ✅ DONE: Agregar a colección Postman

### Fase 5: WebSocket USER
- ✅ DONE: Crear tests para conexión WebSocket USER
- ✅ DONE: Implementar reconexión automática
- ✅ DONE: Implementar backpressure y drop policy
- ✅ DONE: Crear scripts de prueba para WebSocket
- ✅ DONE: Agregar a colección Postman (endpoints de control)

---

## Estructura de Tests

```
backend/tests/
├── integration/
│   └── polymarket/
│       ├── test_phase0_mode_protections.py
│       ├── test_phase1_config.py
│       ├── test_phase2_public_data.py
│       ├── test_phase2_5_websocket_market.py
│       ├── test_phase3_account_data.py
│       ├── test_phase4_trading.py
│       └── test_phase5_websocket_user.py
└── unit/
    └── polymarket/
        ├── test_client_wrapper.py
        ├── test_gamma_api.py
        ├── test_orderbook_engine.py
        └── test_websocket_client.py
```

---

## Referencias y Documentación Relacionada

### Documentación de PolyLiquidity Desk

- [`polymarket-integration.md`](./polymarket-integration.md) - Integración técnica y WS
- [`order-lifecycle.md`](./order-lifecycle.md) - Lifecycle de órdenes y estados
- [`failure-modes.md`](./failure-modes.md) - Criterios de tests de ejecución
- [`../infrastructure/secrets.md`](../infrastructure/secrets.md) - Variables de entorno y prohibiciones
- [`../risk/policy.md`](../risk/policy.md) - Gates, kill switch, policy, controls
- [`../architecture/config-driven.md`](../architecture/config-driven.md) - Configuración y execution_mode
- [`../implementation/orderbook-engine-implementation-plan.md`](../implementation/orderbook-engine-implementation-plan.md) - Orderbook Engine MVP

### APIs Externas

- [Gamma API Documentation](https://gamma-api.polymarket.com)
- [CLOB API Documentation](https://docs.polymarket.com)
- [py-clob-client GitHub](https://github.com/Polymarket/py-clob-client)

---

## Variables de Entorno Requeridas

```bash
# Fase 0: Modo y Protecciones (REQUERIDAS)
# Configuradas en SystemConfig (DB), no en .env

# Fase 1: Configuración (OPCIONALES en DRY_RUN/PAPER, REQUERIDAS en LIVE)
PRIVATE_KEY=0x...  # Opcional en DRY_RUN/PAPER
FUNDER_ADDRESS=0x...  # Opcional en DRY_RUN/PAPER, O POLYMARKET_PROXY_ADDRESS
CHAIN_ID=137
RPC_URL=https://polygon-rpc.com/

# URLs de API (opcionales, tienen defaults)
POLYMARKET_API_URL=https://api.polymarket.com
POLYMARKET_DATA_API_URL=https://data-api.polymarket.com
POLYMARKET_GAMMA_API_URL=https://gamma-api.polymarket.com
POLYMARKET_TRADING_API_URL=https://clob.polymarket.com
```

---

## Próximos Pasos

1. ✅ Crear este plan (completado)
2. ✅ Implementar Fase 0: Tests y endpoints de modo/protecciones (COMPLETADO)
3. ✅ Implementar Fase 1: Tests y endpoints de configuración (COMPLETADO)
4. ✅ Implementar Fase 2: Tests de datos públicos (COMPLETADO)
5. ✅ Implementar Fase 2.5: WS MARKET → Orderbook Engine (COMPLETADO)
6. ✅ Implementar Fase 3: Tests y endpoints de cuenta (COMPLETADO)
7. ✅ Implementar Fase 4: Tests y endpoints de trading (COMPLETADO)
8. ✅ Implementar Fase 5: Tests y control de WebSocket USER (COMPLETADO)
9. ⏳ Crear tests de smoke INTERNAL y EXTERNAL (ver sección "Tests Reales (Smoke Tests)")
10. ⏳ Implementar endpoints operativos (warmup, smoke, scenario runner)
11. ⏳ Crear colección Postman completa
12. ⏳ Documentar resultados y casos de uso

---

## Notas de Arquitectura

### Endpoints REST como Facade

**Regla explícita**: Los endpoints REST no deben convertirse en "otra vía" para que estrategia pegue a Polymarket. La estrategia debe leer State Cache; los conectores y WS alimentan el cache.

**Implementación práctica**:
- `/markets/{id}/orderbook` → Sirve desde State Cache (`pm.orderbook.{asset_id}`)
- `/markets/{id}/price` → Sirve desde State Cache (calculado desde orderbook)
- Exponer `staleness_ms` y `lag` en respuestas
- Si cache está stale, opcionalmente hacer fetch directo (pero loguear como fallback)

### Orderbook Engine como Fuente de Verdad

- **WS MARKET** → Orderbook Engine → State Cache
- **Decision Graph** lee desde State Cache (no REST)
- **Endpoints REST** sirven desde State Cache (facade)

Esto evita que "precio" o "orderbook" sean endpoints REST "inventados" cuando la fuente real/rápida debe ser WS + cache.

---

## Estado de Implementación Detallado

**Última actualización**: 2025-01-27

### Resumen por Fase

| Fase | Estado | Tests | Endpoints | Notas |
|------|--------|-------|-----------|-------|
| **Fase 0: Modo y Protecciones** | ✅ COMPLETADA | 6/6 ✅ | 4/4 ✅ | Todos los tests pasan. Endpoints públicos funcionando. |
| **Fase 1: Configuración y Autenticación** | ✅ COMPLETADA | 5/5 ✅ | 2/2 ✅ | Cliente CLOB inicializado correctamente. Health checks funcionando. |
| **Fase 2: Datos Públicos (Gamma API)** | ✅ COMPLETADA | 7/7 ✅ | 6/6 ✅ | Rate limiting corregido (GAMMA_EVENTS, GAMMA_MARKETS, GAMMA_SEARCH). Cache TTL corregido (timedelta). |
| **Fase 2.5: WebSocket MARKET** | ✅ COMPLETADA | 8/8 ✅ | 4/4 ✅ | Parser actualizado (hash, bids/asks, buys/sells). Endpoints de control funcionando. Ref-count implementado. Manejo de errores robusto. |
| **Fase 3: Datos de Cuenta (CLOB)** | ✅ COMPLETADA | 9/9 ✅ | 5/5 ✅ | Todos los tests pasan (incluyendo casos sin órdenes). Manejo correcto de órdenes inexistentes. |
| **Fase 4: Operaciones de Trading** | ✅ COMPLETADA | 8/8 ✅ | 4/4 ✅ | Validaciones Pydantic implementadas. Execution mode respetado (DRY_RUN simula correctamente). |
| **Fase 5: WebSocket USER** | ✅ COMPLETADA | 8/8 ✅ | 3/3 ✅ | Endpoints de control implementados. Manejo de autenticación y derivación de API keys. Manejo robusto de errores (websocket-client no instalado). |

**Total**: 51 tests pasando, 0 skipped, 28 endpoints implementados

**Nota sobre Smoke Tests**:
- **Smoke INTERNAL**: ✅ Ejecuta en CI (0 skipped)
- **Smoke EXTERNAL**: ⚠️ NO ejecuta en CI (marcado con `@pytest.mark.skipif(CI)`), solo manual/staging

### Correcciones Realizadas

#### Fase 2 (Gamma API)
- ✅ **Rate Limiting**: Corregido uso de `EndpointType` (GAMMA_EVENTS, GAMMA_MARKETS, GAMMA_SEARCH en lugar de DATA_API)
- ✅ **Cliente HTTP**: Migrado a context managers (`async with`) para mejor manejo de recursos
- ✅ **Cache TTL**: Corregido de `int` a `timedelta` para `api_cache.set()`

#### Fase 3 (Account Data)
- ✅ **Tests sin órdenes**: Modificados para no saltarse, prueban con order_id inválido y verifican 404/503
- ✅ **get_order_scoring**: Mejorado manejo de órdenes inexistentes (verifica existencia antes de scoring)

#### Fase 4 (Trading)
- ✅ **Validaciones Pydantic**: Implementadas con `field_validator` para `token_id`, `price`, `size`, `amount`
- ✅ **Execution Mode**: Verificación de `DRY_RUN` antes de crear órdenes (simula sin credenciales)
- ✅ **Manejo de Errores**: `ValidationError` retorna 422, `ValueError` retorna 400 (no 500)

### Próximos Pasos

1. **Tests Reales (Smoke Tests)** - Crear tests de smoke INTERNAL y EXTERNAL ahora que todas las fases están completadas (ver sección al final del documento)

### Notas Técnicas

- **Formato de order_id**: String hexadecimal (hash) de 66 caracteres (`0x` + 64 hex)
- **Manejo de órdenes inexistentes**: 
  - `get_order()` retorna `None` → endpoint retorna 404
  - `is_order_scoring()` puede retornar `False` incluso si orden no existe → endpoint verifica existencia primero
  - `cancel()` retorna `{"canceled": [], "not_canceled": {order_id: reason}}` → endpoint maneja correctamente
- **Formato de mensajes WS MARKET**: 
  - Parser soporta `bids/asks` y `buys/sells`
  - Campo `hash` opcional incluido en `integrity` del OrderbookState
  - Precios y tamaños vienen como strings (`.48` → `0.48`)

---

## Tests Reales (Smoke Tests)

### Objetivo

Una vez completadas todas las fases, crear tests de smoke para verificar que el sistema funciona correctamente tanto internamente como con datos reales de Polymarket.

### Interfaz Operativa (Postman-friendly)

**Endpoint único para smoke tests**:

```python
GET /api/polymarket/smoke?mode=internal|external&asset_id={asset_id}
```

**Respuesta**:

```json
{
  "status": "PASS" | "FAIL",
  "mode": "internal" | "external",
  "checks": [
    {
      "name": "execution_mode",
      "status": "PASS" | "FAIL" | "SKIP",
      "details": "...",
      "timestamp_ms": 1234567890
    },
    {
      "name": "ws_market_connected",
      "status": "PASS" | "FAIL",
      "details": {
        "connected": true,
        "last_msg_age_ms": 150,
        "cache_staleness_ms": 200
      }
    }
  ],
  "observability": {
    "ws_connected": true,
    "last_msg_age_ms": 150,
    "cache_staleness_ms": 200,
    "ref_count": 2,
    "rss_mb": 125.5
  },
  "recommendation": "System ready for trading" | "Fix: ...",
  "timestamp": "2025-01-27T23:00:00Z"
}
```

**Por qué**: Postman hace 1 request y detecta "no conecta / no llegan datos / cache stale" sin mirar logs.

**Implementación**: Ver sección "System Smoke Endpoint" más abajo.

### A) Smoke "INTERNAL" (Determinista, CI)

**Propósito**: Verificar que el pipeline interno funciona correctamente sin depender de servicios externos.

**Características**:
- ✅ Determinista (siempre pasa en CI)
- ✅ No toca Polymarket real
- ✅ Inyecta mensaje WS de ejemplo (fixture) en el pipeline
- ✅ Verifica que el mensaje acaba en State Cache
- ✅ **Ejecuta en CI**: Siempre corre en cada CI/CD run

**Sirve para detectar**:
- Router roto
- Publisher roto
- Cache roto
- Schema roto
- Parser roto

**Contract Test de Schemas WS** (incluido en Smoke INTERNAL):
- ✅ Parser acepta `bids/asks` y `buys/sells`
- ✅ Parser maneja `hash` opcional
- ✅ Parser maneja strings tipo `".48"` → `0.48`
- ✅ Reduce regresiones cuando Polymarket cambia campos

**Implementación**:

```python
# backend/tests/integration/polymarket/test_smoke_internal.py
def test_smoke_internal_websocket_pipeline():
    """
    Smoke test INTERNAL: Verifica que el pipeline WS → Orderbook → Cache funciona.
    
    No requiere conexión real a Polymarket.
    """
    # 1. Crear mensaje WS de ejemplo (fixture)
    book_msg = {
        "event_type": "book",
        "asset_id": "0x1234567890123456789012345678901234567890",
        "market": "0xbd31dc8a...",
        "bids": [
            {"price": ".48", "size": "30"},
            {"price": ".49", "size": "20"}
        ],
        "asks": [
            {"price": ".52", "size": "25"},
            {"price": ".53", "size": "60"}
        ],
        "timestamp": "123456789000",
        "hash": "0x0abcdef1234567890abcdef1234567890abcdef"
    }
    
    # 2. Inyectar mensaje en el pipeline
    from app.core.orderbook.service import get_orderbook_service
    service = get_orderbook_service()
    await service._handle_ws_book_update_async(book_msg)
    
    # 3. Verificar que está en State Cache
    from app.core.strategy_engine.state_cache_service import StateCacheService
    from app.database import SessionLocal
    
    db = SessionLocal()
    cache_service = StateCacheService(db)
    cache_key = f"pm.orderbook.{book_msg['asset_id']}"
    
    orderbook_state = await cache_service.get(cache_key)
    
    assert orderbook_state is not None, "Orderbook debe estar en cache"
    assert orderbook_state["best_bid_price"] == 0.49, "Best bid debe ser correcto"
    assert orderbook_state["best_ask_price"] == 0.52, "Best ask debe ser correcto"
    assert len(orderbook_state["bids"]) == 2, "Debe tener 2 bids"
    assert len(orderbook_state["asks"]) == 2, "Debe tener 2 asks"
    
    db.close()
```

### B) Smoke "EXTERNAL" (Con Polymarket Real, Staging/Producción)

**Propósito**: Verificar que el sistema funciona correctamente con datos reales de Polymarket.

**Características**:
- ⚠️ Requiere conexión real a Polymarket
- ⚠️ **NO ejecuta en CI** (marcado con `@pytest.mark.skipif(CI)`)
- ⚠️ Solo para staging/producción o ejecución manual

**Implementación**:
- **Tests en pytest** (`test_smoke_external.py`): Usan `TestClient(app)` (sin servidor real, pero ejecutan el endpoint completo)
- **Uso manual/staging**: Puede llamarse directamente al endpoint `/api/polymarket/smoke?mode=external` en un servidor real (staging/producción)
- ✅ Hace suscripción real a 1-3 asset_ids
- ✅ Timeout budget claro (connect_timeout_s, data_timeout_s, max_total_s)
- ✅ Limpieza/teardown automático (unsubscribe al final)
- ✅ Idempotencia (subscribe múltiple con mismo owner_key es OK)
- ✅ Selección robusta de asset_id (intenta 2-3 candidatos antes de fallar)
- ✅ Devuelve PASS/FAIL con diagnóstico claro

**Separación de "Pipeline Health" vs "Trading Readiness"**:

El smoke EXTERNAL tiene dos modos de operación:

1. **`mode=external`** (Pipeline Health):
   - Valida dataflow real (WS + cache) aunque `trading_permitted=false`
   - Útil para: "¿conecta WS?", "¿llegan datos?", "¿se publica en cache?"
   - `status = PASS` si el pipeline funciona
   - `trading_ready = false` si `healthy_checkers == 0` (pero pipeline OK)

2. **`mode=external_trade_ready`** (Trading Readiness):
   - Valida lo anterior + `trading_permitted=true` + risk green
   - Útil para: "¿está listo para trading?"
   - `status = PASS` solo si pipeline funciona Y trading permitido
   - `trading_ready = true` solo si `healthy_checkers > 0` y risk engine UP

**En el smoke report**:
- `status = PASS` si el pipeline funciona (independientemente de trading)
- `trading_ready = true/false` indica si trading está permitido
- `recommendation` incluye: "operational ok, trading disabled (0 checkers)" si aplica

**Timeout Budget**:
- `connect_timeout_s = 10` - Tiempo máximo para conectar WS
- `data_timeout_s = 30` - Tiempo máximo para recibir datos
- `max_total_s = 45` - Tiempo total máximo del smoke
- Resultado indica si falló por "no connect" vs "no data"

**Limpieza/Teardown**:
- Al final del smoke: `unsubscribe` del asset_id con `owner_key=smoke:{request_id}`
- **Regla única**: Siempre `owner_key=f"smoke:{request_id}"` en external modes (nunca `smoke_test` fijo)
- Auto-expire `owner_key=smoke:*` después de TTL (ej: 5 minutos)
- Janitor periódico que limpia suscripciones huérfanas
- **Importante**: No acumular suscripciones y RAM

**Selección de asset_id robusta**:
- Auto-descubrir desde Gamma API
- Escoger market activo con liquidez mínima (si hay métrica disponible)
- Si no hay, intentar 2-3 candidatos antes de fallar (reduce flakiness por markets "muertos")

**Checks Mínimos (Core - Si falla cualquiera, no sirve seguir)**:

1. **execution_mode + handshake LIVE** (de Fase 0)
   - ✅ `execution_mode` configurado correctamente
   - ✅ Si es LIVE, handshake verificado

2. **checkers_health + quorum efectivo**
   - ✅ Al menos 1 checker saludable (o `allow_zero_checker=true` confirmado)
   - ✅ Quorum efectivo calculado correctamente
   - ✅ **Trading permitido**: `trading_permitted = (healthy_checkers > 0)`
   - 🔴 **Gate crítico**: Si `healthy_checkers == 0`, `trading_permitted = false` (modo "operational" solo)

3. **risk_engine_status**
   - ✅ Risk Engine UP
   - ✅ Circuit breakers configurados

4. **gamma_health**
   - ✅ Gamma API UP y respondiendo

5. **WS MARKET pipeline** (lo más importante)
   - ✅ `ws_market_connected`: WebSocket MARKET conectado
   - ✅ `subscribed(asset_id)`: Asset ID suscrito (ref-count > 0)
   - ✅ `cache_key_present(pm.orderbook.{asset_id})`: Cache key existe
   - ✅ `staleness_ms < threshold`: Staleness aceptable (< 1000ms)
   - ✅ `book_has_bids_asks`: Orderbook tiene bids y asks

**Checks Opcionales (Cuenta)**:

6. **clob_auth_ok** (solo en LIVE / staging)
   - ✅ CLOB API autenticado correctamente

7. **balance_read_ok**
   - ✅ Balance se puede leer correctamente

**Implementación**:

```python
# backend/tests/integration/polymarket/test_smoke_external.py
import pytest
import time
from fastapi.testclient import TestClient
from app.main import app

# ⚠️ NO ejecutar en CI (marcado con pytest.mark.skipif)
@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Smoke EXTERNAL requiere conexión real a Polymarket"
)
class TestSmokeExternal:
    """Smoke tests con datos reales de Polymarket."""
    
    def test_smoke_external_full_pipeline(self):
        """
        Smoke test EXTERNAL: Verifica pipeline completo con datos reales.
        
        ⚠️ Requiere:
        - websocket-client instalado
        - Conexión a internet
        - Asset IDs reales de Polymarket
        """
        client = TestClient(app)
        
        # Nota: Este test usa TestClient (sin servidor real, pero ejecuta el endpoint completo).
        # El endpoint hace conexiones reales a Polymarket.
        # También puede llamarse directamente al endpoint /api/polymarket/smoke?mode=external
        # en un servidor real (staging/producción).
        
        # Nota: Este test puede ejecutarse con mode="external" (pipeline health)
        # o mode="external_trade_ready" (trading readiness)
        # Por defecto, usamos mode="external" para validar dataflow
        import os
        mode = os.getenv("SMOKE_MODE", "external")
        
        # ============================================================
        # CHECKS CORE (si falla cualquiera, FAIL inmediato)
        # ============================================================
        
        # 1. execution_mode + handshake LIVE
        mode_response = client.get("/system/config/execution-mode")
        assert mode_response.status_code == 200
        execution_mode = mode_response.json()["execution_mode"]
        assert execution_mode in ["DRY_RUN", "PAPER", "LIVE"]  # DRY_RUN = SIMULATION (alias)
        
        if execution_mode == "LIVE":
            # Verificar handshake
            protected_response = client.get("/system/config/protected-parameters")
            assert protected_response.status_code == 200
            # Verificar que LIVE requiere confirmación
        
        # 2. checkers_health + quorum efectivo
        checkers_response = client.get("/checkers/health")
        assert checkers_response.status_code == 200
        checkers_data = checkers_response.json()
        
        healthy_count = sum(1 for c in checkers_data.get("checkers", {}).values() if c.get("healthy", False))
        
        # Gate crítico: Trading NO permitido si healthy_checkers == 0
        trading_permitted = healthy_count > 0
        
        # Separación: Pipeline health vs Trading readiness
        # En mode=external (pipeline health): NO hacer assert de trading_permitted
        # En mode=external_trade_ready: SÍ hacer assert de trading_permitted
        if mode == "external_trade_ready" and not trading_permitted:
            assert False, \
                f"Trading NO permitido: healthy_checkers={healthy_count}. Modo 'operational' (lectura/observabilidad) solo."
        # En mode=external, solo registramos trading_permitted pero no fallamos
        
        quorum_effective = checkers_data.get("quorum_effective", 0)
        assert quorum_effective > 0, "Quorum efectivo debe ser > 0"
        
        # 3. risk_engine_status
        risk_response = client.get("/risk/status")
        assert risk_response.status_code == 200
        risk_data = risk_response.json()
        assert risk_data.get("status") == "UP", "Risk Engine debe estar UP"
        
        # 4. gamma_health
        gamma_response = client.get("/api/polymarket/health")
        assert gamma_response.status_code == 200
        gamma_data = gamma_response.json()
        assert gamma_data.get("status") == "ok", "Gamma API debe estar UP"
        
        # 5. WS MARKET pipeline (LO MÁS IMPORTANTE)
        # 5.1. Obtener asset_id real desde Gamma API (selección robusta)
        # Intentar 2-3 candidatos antes de fallar (reduce flakiness)
        events_response = client.get("/api/polymarket/events?closed=false&limit=3")
        assert events_response.status_code == 200
        events = events_response.json()
        assert len(events) > 0, "Debe haber al menos 1 event activo"
        
        asset_id = None
        for event in events[:3]:  # Intentar hasta 3 candidatos
            try:
                market_id = event["markets"][0]["id"]
                market_response = client.get(f"/api/polymarket/markets/{market_id}")
                if market_response.status_code == 200:
                    market_data = market_response.json()
                    # Escoger outcome con liquidez (si hay métrica disponible)
                    # Por ahora, escoger el primer outcome
                    asset_id = market_data["outcomes"][0]["token_id"]
                    break
            except (KeyError, IndexError):
                continue
        
        assert asset_id is not None, "No se pudo obtener asset_id válido de los primeros 3 eventos"
        
        # 5.2. Suscribirse a asset_id real (idempotente)
        # Regla única: Siempre usar request_id único para evitar colisiones
        import uuid
        request_id = str(uuid.uuid4())
        owner_key = f"smoke:{request_id}"
        
        subscribe_response = client.post(
            "/api/polymarket/websocket/subscribe/market",
            json={"asset_id": asset_id, "owner_key": owner_key}
        )
        assert subscribe_response.status_code == 200
        
        # Verificar idempotencia: suscribirse de nuevo debe ser OK
        subscribe_response_2 = client.post(
            "/api/polymarket/websocket/subscribe/market",
            json={"asset_id": asset_id, "owner_key": owner_key}
        )
        # Puede retornar 200 (subscribed) o 200 (already_connected), ambos OK
        assert subscribe_response_2.status_code == 200
        
        # 5.3. Verificar conexión WS
        ws_status_response = client.get("/api/polymarket/websocket/status")
        assert ws_status_response.status_code == 200
        ws_status = ws_status_response.json()
        
        # 5.3.1. ws_market_connected
        assert ws_status["market_channel"]["connected"] == True, \
            "WebSocket MARKET debe estar conectado"
        
        # 5.3.2. subscribed(asset_id) - ref_count > 0
        ref_count = ws_status["orderbook"]["ref_count"]
        assert asset_id in ref_count, f"Asset ID {asset_id} debe estar suscrito"
        assert ref_count[asset_id] > 0, "Ref-count debe ser > 0"
        
        # 5.4. Esperar hasta X segundos (con timeout) a que llegue book
        # Timeout budget claro
        connect_timeout_s = 10  # Tiempo máximo para conectar WS
        data_timeout_s = 30     # Tiempo máximo para recibir datos
        max_total_s = 45        # Tiempo total máximo del smoke
        check_interval = 2
        
        # Verificar que no excedemos max_total_s
        smoke_start_time = time.time()
        
        # Verificar conexión primero
        start_time = time.time()
        ws_connected = False
        while time.time() - start_time < connect_timeout_s:
            # Verificar timeout total
            if time.time() - smoke_start_time > max_total_s:
                raise AssertionError(f"Smoke excedió tiempo total máximo de {max_total_s}s")
            ws_status_check = client.get("/api/polymarket/websocket/status")
            if ws_status_check.status_code == 200:
                ws_data = ws_status_check.json()
                if ws_data.get("market_channel", {}).get("connected", False):
                    ws_connected = True
                    break
            time.sleep(1)
        
        assert ws_connected, f"WS no conectó después de {connect_timeout_s}s"
        
        # Esperar datos
        start_time = time.time()
        orderbook_data = None
        while time.time() - start_time < data_timeout_s:
            # Verificar timeout total
            if time.time() - smoke_start_time > max_total_s:
                raise AssertionError(f"Smoke excedió tiempo total máximo de {max_total_s}s")
            # Verificar timeout total
            if time.time() - smoke_start_time > max_total_s:
                raise AssertionError(f"Smoke excedió tiempo total máximo de {max_total_s}s")
            orderbook_response = client.get(f"/api/polymarket/orderbook/{asset_id}")
            
            if orderbook_response.status_code == 200:
                orderbook_data = orderbook_response.json()
                
                # 5.4.1. cache_key_present
                assert orderbook_data["cache_key"] == f"pm.orderbook.{asset_id}", \
                    "Cache key debe ser correcta"
                
                # 5.4.2. staleness_ms < threshold
                staleness_ms = orderbook_data["orderbook"]["staleness_ms"]
                assert staleness_ms < 5000, \
                    f"Staleness debe ser < 5000ms, obtuvo {staleness_ms}ms"
                
                # 5.4.3. book_has_bids_asks
                book = orderbook_data["orderbook"]
                assert len(book["bids"]) > 0, "Orderbook debe tener bids"
                assert len(book["asks"]) > 0, "Orderbook debe tener asks"
                assert book["best_bid_price"] is not None, "Debe tener best_bid_price"
                assert book["best_ask_price"] is not None, "Debe tener best_ask_price"
                
                # ✅ PASS: Todos los checks pasaron
                break
            
            time.sleep(check_interval)
        
        # Si llegamos aquí sin datos, FAIL con diagnóstico claro
        if orderbook_data is None:
            # Diagnóstico: "no connect" vs "no data"
            if not ws_connected:
                raise AssertionError(f"WS no conectó después de {connect_timeout_s}s (no connect)")
            else:
                raise AssertionError(f"Orderbook no llegó después de {data_timeout_s}s (no data)")
        
        # ============================================================
        # LIMPIEZA / TEARDOWN
        # ============================================================
        
        # Desuscribirse al final para no acumular suscripciones
        unsubscribe_response = client.post(
            "/api/polymarket/websocket/unsubscribe/market",
            json={"asset_id": asset_id, "owner_key": owner_key}
        )
        # No fallar si unsubscribe falla, pero loguear
        if unsubscribe_response.status_code != 200:
            logger.warning(f"Failed to unsubscribe asset_id={asset_id} with owner_key={owner_key} in smoke test teardown")
        
        # ============================================================
        # CHECKS OPCIONALES (Cuenta)
        # ============================================================
        
        if execution_mode in ["LIVE", "PAPER"]:
            # 6. clob_auth_ok (solo en LIVE / staging)
            auth_response = client.get("/api/polymarket/connection/test-auth")
            assert auth_response.status_code == 200
            auth_data = auth_response.json()
            assert auth_data.get("authenticated") == True, \
                "CLOB API debe estar autenticado"
            
            # 7. balance_read_ok
            balance_response = client.get("/api/polymarket/account/balance")
            assert balance_response.status_code == 200
            balance_data = balance_response.json()
            assert "balance_usdc" in balance_data, "Debe poder leer balance"
```

### Estructura de Tests

```
backend/tests/integration/polymarket/
├── test_phase0_mode_protections.py
├── test_phase1_config.py
├── test_phase2_public_data.py
├── test_phase2_5_websocket_orderbook.py
├── test_phase3_account_data.py
├── test_phase4_trading.py
├── test_phase5_websocket_user.py
├── test_smoke_internal.py      # ← NUEVO: Smoke INTERNAL (CI)
└── test_smoke_external.py      # ← NUEVO: Smoke EXTERNAL (staging/prod)
```

### Cuándo Ejecutar

- **Smoke INTERNAL**: En cada CI/CD run (siempre)
- **Smoke EXTERNAL**: Solo en staging/producción, antes de deploy o periódicamente

### Gates / No-Go Criteria

**🔴 NO deployar a producción si:**
- Smoke INTERNAL falla (pipeline roto)
- Smoke EXTERNAL falla (no hay datos reales)
- Cualquier check core falla

**✅ OK deployar si:**
- Smoke INTERNAL pasa (en CI)
- Smoke EXTERNAL pasa (en staging, antes de deploy)
- Todos los checks core pasan
- `trading_permitted = true` (healthy_checkers > 0)

---

## System Smoke Endpoint (Interfaz Operativa)

### Objetivo

Proporcionar un endpoint único, Postman-friendly, que ejecute smoke tests y retorne un reporte estructurado.

### Endpoint

```python
GET /api/polymarket/smoke?mode=internal|external|external_trade_ready&asset_id={asset_id}
```

**Parámetros**:
- `mode` (requerido): 
  - `internal`: Smoke interno (sin side effects persistentes)
  - `external`: Pipeline health (valida dataflow aunque trading disabled)
  - `external_trade_ready`: Trading readiness (valida dataflow + trading permitido)
- `asset_id` (opcional): Para `mode=external` o `external_trade_ready`, asset_id específico. Si no se proporciona, se auto-descubre.

**Política de Side Effects**:
- **`mode=internal`**: No side effects persistentes (no toca WS real)
- **`mode=external` o `external_trade_ready`**: 
  - **Regla única**: Siempre `owner_key=f"smoke:{request_id}"` (nunca `smoke_test` fijo)
  - Siempre cleanup al final (unsubscribe)
  - Si el proceso muere antes del cleanup: auto-expire (TTL de `owner_key` o TTL de refcount), o un "janitor" que limpia periódicamente
  - **Importante**: Evita leaks en WS y RAM

**Idempotencia y Concurrencia**:
- Si 2 operadores llaman smoke a la vez: `owner_key=smoke:{request_id}` único por request
- Si llamas 10 veces, no debería multiplicar suscripciones "sin control" (cada request tiene su propio `request_id`)
- **Recomendado**: Usar `request_id` único (UUID) para evitar colisiones

### Respuesta

```json
{
  "status": "PASS",
  "mode": "external",
  "trading_ready": false,
  "timestamp": "2025-01-27T23:00:00Z",
  "failure_reason": null,
  "timeouts": {
    "connect_timeout_s": 10,
    "data_timeout_s": 30,
    "total_timeout_s": 45
  },
  "checks": [
    {
      "name": "execution_mode",
      "status": "PASS",
      "details": {
        "execution_mode": "DRY_RUN",
        "is_safe": true
      },
      "timestamp_ms": 1234567890
    },
    {
      "name": "checkers_health",
      "status": "PASS",
      "details": {
        "healthy_checkers": 2,
        "quorum_effective": 2,
        "trading_permitted": true
      }
    },
    {
      "name": "ws_market_connected",
      "status": "PASS",
      "details": {
        "connected": true,
        "subscribed_asset_ids": ["0x123..."],
        "ref_count": 1
      }
    },
    {
      "name": "cache_staleness",
      "status": "PASS",
      "details": {
        "staleness_ms": 150,
        "threshold_ms": 1000
      }
    }
  ],
  "observability": {
    "ws_connected": true,
    "last_msg_age_ms": 150,
    "cache_staleness_ms": 200,
    "ref_count": 2,
    "subscriptions_count": 1,
    "hot_cache_markets": ["0x123..."],
    "process_uptime_s": 3600,
    "rss_mb": 125.5,
    "cache_backend": "memory",
    "cache_write_ms": 0.5,
    "cache_read_ms": 0.3,
    "latency_breakdown": {
      "ws_last_msg_age_ms": 150,
      "ingest_to_cache_ms": 50,
      "cache_read_ms": 50,
      "end_to_end_ms": 250
    }
  },
  "recommendation": "System ready for trading" | "Operational ok, trading disabled (0 checkers)" | "Fix: WS not connected"
}
```

**Campos clave**:
- `status`: PASS si pipeline funciona (independientemente de trading)
- `trading_ready`: true solo si `healthy_checkers > 0` y risk engine UP
- `failure_reason`: Código de razón del fallo (ver tabla abajo)
- `timeouts`: Budget de tiempo usado
- `observability`: Métricas adicionales para debugging

**Failure Reasons y Qué Mirar en Logs**:
- `NO_CONNECT`: WS no conectó → logs: websocket connect/ssl/dns
- `NO_DATA`: Subscribe OK pero no messages → asset_id muerto o WS desconectado
- `CACHE_STALE`: Cache no se actualiza → publisher/router logs
- `GAMMA_DOWN`: Gamma API no responde → gamma client + rate limiter logs
- `RISK_DOWN`: Risk Engine no está UP → risk engine logs
- `NO_CHECKERS`: 0 checkers saludables → checkers health logs
- `AUTH_FAIL`: CLOB autenticación falló → CLOB client logs

### Especificación (Pseudo-steps)

**Contrato Request/Response**:

1. **Request**:
   - `GET /api/polymarket/smoke?mode={mode}&asset_id={asset_id}`
   - `mode`: `internal` | `external` | `external_trade_ready`
   - `asset_id`: Opcional (auto-descubre si no se proporciona)

2. **Pseudo-steps** (no código real, solo especificación):
   - **Step 1**: Verificar `execution_mode` (GET `/system/config/execution-mode`)
   - **Step 2**: Verificar `checkers_health` (GET `/checkers/health`)
     - Calcular `trading_permitted = (healthy_checkers > 0)`
     - Si `mode=external_trade_ready` y `trading_permitted=false` → `status=FAIL`, `failure_reason=NO_CHECKERS`
   - **Step 3**: Verificar `risk_engine_status` (GET `/risk/status`)
   - **Step 4**: Verificar `gamma_health` (GET `/api/polymarket/health`)
   - **Step 5** (solo `mode=external` o `external_trade_ready`):
     - Auto-descubrir `asset_id` si no se proporciona (GET `/api/polymarket/events?closed=false&limit=3`)
     - Suscribirse a WS MARKET con `owner_key=smoke:{request_id}` (POST `/api/polymarket/websocket/subscribe/market`)
     - Esperar hasta `data_timeout_s` a que llegue orderbook (con timeout total `max_total_s`)
     - Verificar `cache_staleness_ms < threshold`
     - **Cleanup**: Unsubscribe con `owner_key=smoke:{request_id}` (POST `/api/polymarket/websocket/unsubscribe/market`)
   - **Step 6**: Calcular `status`, `trading_ready`, `failure_reason`, `recommendation`

3. **Response**: Ver formato JSON arriba

**Notas de Implementación**:
- **Regla única**: Siempre usar `owner_key=f"smoke:{request_id}"` donde `request_id` es UUID único
- Auto-expire suscripciones con `owner_key=smoke:*` después de TTL (ej: 5 minutos)
- Janitor periódico que limpia suscripciones huérfanas

### Failure-Modes Smoke (Mini)

**Incluido en Smoke INTERNAL**:

```python
def test_failure_modes_smoke():
    """
    Smoke interno que simula:
    - WS disconnect → reconexión → resubscribe
    - Verifica que el estado vuelve a actualizarse
    """
    # 1. Conectar y suscribirse
    # 2. Simular disconnect
    # 3. Verificar reconexión automática
    # 4. Verificar resubscribe
    # 5. Verificar que datos vuelven a actualizarse
```

---

## Cobertura Adicional

### Contract Test de Schemas WS

**Incluido en Smoke INTERNAL**:

```python
def test_ws_schema_contract():
    """
    Valida que el parser acepta:
    - bids/asks y buys/sells
    - hash opcional
    - strings tipo ".48"
    """
    # Test con bids/asks
    msg1 = {"bids": [{"price": ".48", "size": "30"}], "asks": [...]}
    # Test con buys/sells
    msg2 = {"buys": [{"price": ".48", "size": "30"}], "sells": [...]}
    # Test con hash
    msg3 = {"bids": [...], "hash": "0x123..."}
    # Test sin hash
    msg4 = {"bids": [...]}
    
    # Verificar que todos se parsean correctamente
```

### Observabilidad Mínima en Smoke Report

El endpoint `/api/polymarket/smoke` incluye en `observability`:
- `ws_connected`: Estado de conexión WS
- `last_msg_age_ms`: Edad del último mensaje recibido
- `cache_staleness_ms`: Staleness del cache
- `ref_count`: Referencias activas
- `rss_mb`: Memoria RSS del proceso (opcional)

**Por qué**: Acelera debugging sin necesidad de mirar logs.

---

## Warm-up / Priming (Fase Operativa)

### Objetivo

Para market making, no empiezas a tradear con books fríos. El warm-up es un paso operativo previo al trading.

### Proceso de Warm-up

**Pasos**:
1. Suscribirse a N mercados objetivo durante X segundos (ej: 30s)
2. Confirmar:
   - Orderbooks poblados (todos los asset_ids tienen datos)
   - Staleness estable (`staleness_ms < threshold` para todos)
   - Memory dentro de límites (RSS < threshold)
   - Reconexión OK (simular disconnect → reconexión automática)

**Endpoint**:

```python
POST /api/polymarket/warmup
# Body: {asset_ids: ["0x123...", "0x456..."], duration_s: 30}
# Retorna: {
#   "status": "ready" | "not_ready",
#   "orderbooks_populated": 3/3,
#   "staleness_ok": true,
#   "failed_asset_ids": [
#     {"asset_id": "0x789...", "reason": "NO_DATA"},
#     {"asset_id": "0xabc...", "reason": "STALE"}
#   ]
# }
```

**Gates**:
- ✅ Todos los orderbooks poblados
- ✅ Staleness estable (< threshold)
- ✅ Memory dentro de límites
- ✅ Reconexión OK

**Warm-up Flag**:
- Warm-up debe setear un flag: `pm.warmup.ready=true` con TTL corto (ej: 60s)
- Risk Engine usa este flag como gate: "no warmup → no trading"
- Si warmup falla, `pm.warmup.ready=false` y trading bloqueado

**Razones de Fallo**:
- `NO_DATA`: No llegaron datos en `duration_s`
- `STALE`: Staleness > threshold
- `SPREAD_BAD`: Spread muy amplio (si aplica)

**No es una "fase nueva"**: Es un modo operativo previo al trading, ejecutado antes de activar estrategias.

---

## E2E Trading Safe Test (DRY_RUN/PAPER)

### Objetivo

Para ganar dinero, necesitas estar seguro de que el flujo completo funciona: Strategy genera intención → order placer → ack → reconcile → cancel/replace.

### Smoke Interno: "Strategy Tick Produces Order Intent"

**En DRY_RUN/PAPER**:

```python
def test_e2e_trading_safe():
    """
    E2E trading safe test: Verifica flujo completo sin riesgo.
    
    En DRY_RUN:
    - Strategy genera intención de orden
    - Crea orden simulada
    - Aparece en "open orders" internas
    - Cancel funciona
    - Lifecycle consistente
    """
    # 1. Strategy tick produce order intent
    intent = strategy.generate_intent(market_data)
    assert intent is not None
    
    # 2. Order placer crea orden (simulada en DRY_RUN)
    order = order_placer.create_order(intent)
    assert order.status == "PENDING"
    
    # 3. Aparece en "open orders" internas
    open_orders = get_open_orders()
    assert order.id in [o.id for o in open_orders]
    
    # 4. Cancel funciona
    cancel_result = cancel_order(order.id)
    assert cancel_result["canceled"] == [order.id]
    
    # 5. Lifecycle consistente
    assert order.status == "CANCELLED"
    assert order.id not in [o.id for o in get_open_orders()]
```

**Por qué**: Esto es "paper reality". Si falla aquí, en LIVE vas ciego.

**Verificaciones Críticas**:
- ✅ Intent → order created → ack simulated → order visible → cancel → reconcile
- ✅ No toca CLOB real en DRY_RUN (todo simulado)
- ✅ Lifecycle consistente (PENDING → SUBMITTED → OPEN → CANCELLED)

**Implementación**:
- Test incluido en Smoke INTERNAL
- Ejecuta en DRY_RUN/PAPER (no requiere credenciales reales)
- Verifica flujo completo sin riesgo

---

## Scenario Runner (Postman-friendly)

### Objetivo

Para operar rápido, conviene tener "macros" que ejecuten secuencias comunes.

### Endpoint

```python
GET /api/polymarket/scenario/run?name={scenario_name}&market={market_id}
```

**Scenarios disponibles**:

1. **`mm_bootstrap`** (Market Making Bootstrap):
   - Subscribe a market
   - Wait data (hasta 10s)
   - Place tiny order (solo en PAPER)
   - Cancel
   - Verify reconcile

2. **`warmup_check`** (Warm-up Check):
   - Subscribe a N markets
   - Wait data
   - Verify staleness
   - Verify memory

3. **`kill_switch_test`** (Kill Switch Test):
   - Simular WS disconnect
   - Verify circuit breaker activa
   - Verify órdenes canceladas
   - Verify reconexión

**Respuesta**:

```json
{
  "scenario": "mm_bootstrap",
  "status": "PASS" | "FAIL",
  "steps": [
    {"name": "subscribe", "status": "PASS", "duration_ms": 100},
    {"name": "wait_data", "status": "PASS", "duration_ms": 2000},
    {"name": "place_order", "status": "PASS", "duration_ms": 500},
    {"name": "cancel", "status": "PASS", "duration_ms": 300},
    {"name": "reconcile", "status": "PASS", "duration_ms": 200}
  ],
  "total_duration_ms": 3100
}
```

**Por qué**: No necesitas framework complejo. Un "macro" de 20s que ejecuta secuencias comunes.

**Seguridad (V1 - Internal-Only)**:
- **Bandera de habilitación**: Variable de entorno `SCENARIO_RUNNER_ENABLED=false` (default, deshabilitado en prod)
  - **Archivo**: `backend/app/settings.py`
  - **Campo**: `scenario_runner_enabled: bool = False`
  - **Mapeo**: `SCENARIO_RUNNER_ENABLED` (env var) → `scenario_runner_enabled` (campo) - mapeo automático de pydantic-settings
- **Internal-only**: Solo habilitado en staging/internal con `SCENARIO_RUNNER_ENABLED=true`
- **Sin auth/roles en V1**: Si es internal-only, el rate limit real es "quién tiene acceso a la red"
- **V2 (futuro)**: Si se expone a usuarios o internet, entonces añadir auth/roles y rate limiting

**Implementación**:
- Endpoint simple que ejecuta secuencia predefinida
- Retorna reporte paso a paso
- Útil para Postman y operaciones rápidas
- Verifica `settings.scenario_runner_enabled` antes de ejecutar (retorna **503** si está deshabilitado)
