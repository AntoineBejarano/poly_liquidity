# Roadmap: Near-Resolution Liquidity Provider - Estado Actual y Pendientes

**Objetivo Final**: Estrategia Near-Resolution completamente funcional con:
- ✅ Control completo de datos de Polymarket (orderbooks, markets, events)
- ✅ Todos los parámetros configurables desde frontend
- ✅ Botón Play que activa la estrategia y funciona end-to-end
- ✅ Dashboard Live con datos actualizándose en tiempo real
- ✅ Ejecución real de órdenes en Polymarket

**Fecha**: 2025-01-28  
**Estado**: 🟢 Endpoints API Completados - En Desarrollo (Fase 5/8)

---

## 📊 Estado Actual del Proyecto

### ✅ Implementado y Funcional

#### Backend - Infraestructura Base
- ✅ **Strategy Engine (Graph-based)**: Sistema completo de Decision/Support/Execution Graphs
- ✅ **Template Compiler**: Compilador de templates a grafos (`liquidity_near_end`)
- ✅ **State Cache Service**: Sistema de caché centralizado
- ✅ **Execution Engine**: Cliente Polymarket con EIP-712 signing
- ✅ **Risk Engine**: Validación de riesgo y límites
- ✅ **Runtime Supervisor**: Circuit breakers y fail-safes
- ✅ **Metrics & Observability**: Sistema de métricas y logging
- ✅ **API REST**: Endpoints básicos para estrategias, markets, positions

#### Backend - Integración Polymarket (✅ COMPLETADA)
- ✅ **Fase 0: Modo y Protecciones** (6/6 tests) - Execution mode, parámetros protegidos, checkers, risk engine
- ✅ **Fase 1: Configuración y Autenticación** (5/5 tests) - Cliente CLOB inicializado, health checks
- ✅ **Fase 2: Datos Públicos (Gamma API)** (7/7 tests) - Events, markets, metadata, búsqueda, caching
- ✅ **Fase 2.5: WebSocket MARKET** (8/8 tests) - Orderbook Engine conectado, State Cache, ref-count
- ✅ **Fase 3: Datos de Cuenta (CLOB)** (9/9 tests) - Balance, órdenes, trades, scoring
- ✅ **Fase 4: Operaciones de Trading** (8/8 tests) - Crear/cancelar órdenes, prechecks, validaciones
- ✅ **Fase 5: WebSocket USER** (8/8 tests) - Actualizaciones en tiempo real de órdenes/trades
- **Total**: 51 tests pasando, 28 endpoints implementados
- **Referencia**: [`docs/exchange/polymarket-connection-plan.md`](exchange/polymarket-connection-plan.md)

#### Backend - Orderbook Engine (✅ COMPLETADO)
- ✅ **Orderbook Models**: `OrderbookLevel`, `OrderbookState` con métricas
- ✅ **OrderbookBook**: In-memory top-N book con snapshot updates
- ✅ **Features Calculator**: Cálculo de spread, depth, impact (BUY-side)
- ✅ **Orchestrator**: Ref-count para suscripciones (completamente funcional)
- ✅ **Publisher**: Publicación a State Cache (`pm.orderbook.{asset_id}`)
- ✅ **WebSocket Integration**: Conectado al Orderbook Engine y funcionando
- ✅ **Endpoints de Control**: `/api/polymarket/websocket/status`, `/api/polymarket/orderbook/{asset_id}`

#### Frontend - UI Base
- ✅ **Design System Compacto**: Componentes UI optimizados para trading terminal
- ✅ **Markets Page**: Lista de markets con filtros (datos reales de Polymarket API)
- ✅ **Strategy Builder**: Formulario para crear estrategia Near-Resolution
- ✅ **Live Dashboard**: Estructura UI completa (`/strategies/[id]/live`)
- ✅ **Simulation Page**: UI para simulación (`/strategies/[id]/simulate`)
- ⚠️ **Datos**: Muchos datos están hardcodeados o mock

#### Frontend - Funcionalidad
- ✅ **Autenticación**: Stack OAuth integrado
- ✅ **API Client**: Cliente REST con manejo de errores
- ✅ **WebSocket Client**: Cliente WebSocket básico (no conectado a datos reales)
- ✅ **Componentes**: StrategyHeader, Metrics, Positions, SystemHealth, etc.

---

## ❌ Pendiente - Crítico para MVP

### ✅ PHASE 1: Integración Orderbook Engine ↔ WebSocket

**Estado**: ✅ **COMPLETADA** - WebSocket MARKET conectado y funcionando

**Completado**:

1. ✅ **WebSocket MARKET channel conectado al Orderbook Engine**
   - Path: `backend/app/core/orderbook/ws_router.py`
   - `OrderbookWSRouter` inicializado en `main.py`
   - Callbacks de WebSocket conectados a `orchestrator.ingest_book_msg()`
   - **Verificado**: Al recibir update de WS, aparece `pm.orderbook.{asset_id}` en State Cache

2. ✅ **Orderbook Engine integrado**
   - Path: `backend/app/core/orderbook/service.py`
   - `OrderbookOrchestrator` con ref-count funcional
   - Endpoints de control implementados
   - **Verificado**: Suscripciones funcionan correctamente

3. ⚠️ **Suscripción automática por Strategy Universe** (Pendiente de integración con Control Loop)
   - Path: `backend/app/core/strategy_engine/control_loop.py`
   - Cuando strategy se activa, suscribir a todos los asset_ids de su universe
   - Cuando strategy se desactiva, desuscribir
   - **Criterio**: Ref-count funciona correctamente (0→1 subscribe, 1→0 unsubscribe)

**Nota**: La infraestructura de Orderbook Engine está completa. Falta integrar con Control Loop para suscripciones automáticas por estrategia.

---

### ✅ PHASE 2: Actualizar Strategy Near-Resolution para usar Orderbook

**Estado**: ✅ **COMPLETADA (backend)** - Template, collect_state y calculate_order_size usan orderbook_state

**Completado**:

1. ✅ **Decision Graph usa OrderbookState**
   - Path: `backend/app/core/strategy_engine/template_compiler.py` (`compile_liquidity_near_end`)
   - Precio: `orderbook_state.best_ask_price` (rango price_min/price_max)
   - Condiciones: `staleness_ms`, `spread_bps`, `depth_usdc_at_50bps`, `impact_bps_for_usdc_1000`
   - Nodo `collect_state` incluye source `"orderbook_state"`

2. ✅ **collect_state node**
   - Path: `backend/app/core/strategy_engine/nodes/collect_state.py`
   - Source `"orderbook_state"`: lee `pm.orderbook.{asset_id}` con `context.metadata["asset_id"]`

3. ✅ **calculate_order_size capacity-aware**
   - Path: `backend/app/core/strategy_engine/nodes/calculate_order_size.py`
   - Método `capacity_aware`: `min(base_size, depth_usdc_at_50bps * capacity_factor)`
   - Precio: `_get_market_price()` prefiere `orderbook_state.best_ask_price` sobre `market_state.last_price`

**Tests**:
- `tests/unit/test_template_compiler.py`: grafo con orderbook_state en sources y condiciones
- `tests/unit/test_nodes.py`: CollectStateNode con orderbook_state y asset_id
- `tests/unit/test_calculate_order_size_node.py`: capacity_aware, _get_market_price desde orderbook

---

### ✅ PHASE 3: Execution Prechecks

**Estado**: ✅ **COMPLETADA** - PrecheckNode creado y integrado en Execution Graph

**Completado**:

1. ✅ **PrecheckNode creado**
   - Path: `backend/app/core/strategy_engine/nodes/precheck.py`
   - Validaciones implementadas:
     - `orderbook_state.staleness_ms <= max_book_staleness_ms`
     - `|current_best_ask/bid - plan.target_price| <= drift_bps_limit`
     - `orderbook_state.impact_bps_for_usdc_1000 <= max_impact_bps`
     - `plan.ttl_ms > elapsed_ms` (TTL no expirado)
   - Retorna `ConditionalResult(condition=True/False, data={failures: [...]})`

2. ✅ **Integrado en Execution Graph**
   - `template_compiler.py`: Ambos compilers generan `execution_graph` con `precheck → coordinate`
   - `strategy_template.py`: Templates actualizados con execution_graph que incluye precheck
   - `graph_runtime.py`: Nodo `precheck` registrado en NODE_REGISTRY

3. ✅ **Métricas de Precheck Failures**
   - Métrica `plans_failed_precheck_total{reason}` se registra automáticamente
   - Razones: `orderbook_stale`, `price_drift`, `market_impact_high`, `plan_ttl_expired`

**Tests**:
- `tests/unit/test_precheck_node.py`: 14 tests cubriendo todas las validaciones y edge cases

---

### ✅ PHASE 4: Endpoints API para Frontend

**Estado**: ✅ **COMPLETADA** - Todos los endpoints implementados

**Completado**:

1. ✅ **POST `/strategies/{id}/activate`** - Activar estrategia
   - Path: `backend/app/api/strategies.py` (línea 329)
   - ✅ Suscribe a orderbooks de universe (asset_ids) al activar
   - ✅ El Control Loop detecta automáticamente estrategias activas desde DB
   - **Verificado**: Al activar, orderbooks se suscriben automáticamente usando OrderbookService

2. ✅ **POST `/strategies/{id}/deactivate`** - Desactivar estrategia
   - Path: `backend/app/api/strategies.py` (línea 359)
   - ✅ Desuscribe de orderbooks al desactivar
   - ✅ Cancela órdenes pendientes asociadas a la estrategia
   - **Verificado**: Al desactivar, se limpian suscripciones y órdenes

3. ✅ **GET `/strategies/{id}/live-status`** - Estado en tiempo real
   - Path: `backend/app/api/strategies.py` (nuevo endpoint)
   - Retorna:
     - Estado de estrategia (active/paused/stopped)
     - Métricas: exposición, PnL, órdenes activas
     - Precheck failures (estructura lista, se puede mejorar con métricas Prometheus)
     - Execution Plans recientes (últimos 20)
     - Orderbook health por asset_id
   - **Criterio**: Frontend puede refrescar estado cada 1-2s ✅

4. ✅ **GET `/strategies/{id}/executions`** - Ejecuciones recientes
   - Path: `backend/app/api/strategies.py` (mejorado)
   - Retorna: Lista de Execution Plans con estado, legs, fills
   - **Criterio**: Dashboard muestra órdenes ejecutadas ✅

5. ✅ **GET `/strategies/{id}/positions`** - Posiciones abiertas
   - Path: `backend/app/api/strategies.py` (nuevo endpoint)
   - Filtra por markets de eventos asignados a la estrategia
   - **Criterio**: Dashboard muestra posiciones reales ✅

6. ✅ **WebSocket `/ws/strategies/{id}`** - Updates en tiempo real
   - Path: `backend/app/api/websocket.py` (nuevo endpoint)
   - Eventos soportados:
     - `plan_created` - Nuevo plan creado (via broadcast_strategy_event)
     - `plan_executing` - Plan en ejecución
     - `plan_filled` - Plan completado
     - `plan_failed` - Plan falló
     - `precheck_failed` - Precheck falló
     - `orderbook_update` - Update de orderbook
     - `metrics_update` - Actualización de métricas
   - **Criterio**: Dashboard se actualiza sin refresh ✅

**Archivos modificados**:
- ✅ `backend/app/api/strategies.py` - Endpoints añadidos/mejorados
- ✅ `backend/app/api/websocket.py` - WebSocket para estrategias implementado

**Nota**: La función `broadcast_strategy_event()` está disponible para que otros módulos envíen eventos a los WebSockets conectados. Falta integrar las llamadas desde Control Loop y Execution Engine.

---

### 🔴 PHASE 5: Frontend - Conectar Datos Reales

**Estado**: ⚠️ UI existe pero datos mock/hardcodeados

**Pendientes**:

1. **Live Dashboard - Datos Reales**
   - Path: `frontend/app/strategies/[id]/live/page.tsx`
   - Conectar a:
     - `GET /strategies/{id}/live-status` (cada 2s)
     - `GET /strategies/{id}/executions` (cada 5s)
     - `GET /strategies/{id}/positions` (cada 5s)
     - WebSocket `/ws/strategies/{id}` (updates en tiempo real)
   - **Criterio**: Dashboard muestra datos reales actualizándose

2. **Botón Play/Pause Funcional**
   - Path: `frontend/app/strategies/[id]/live/page.tsx`
   - Conectar a:
     - `POST /strategies/{id}/activate` → Play
     - `POST /strategies/{id}/deactivate` → Pause
   - Mostrar loading state durante activación
   - **Criterio**: Al hacer click, estrategia se activa/desactiva realmente

3. **Métricas de Orderbook en Markets Page**
   - Path: `frontend/app/markets/page.tsx`
   - Ya implementado parcialmente (`/markets/orderbook-metrics`)
   - Verificar que datos se actualizan cuando Orderbook Engine está activo
   - **Criterio**: Markets muestran spread/depth/impact reales cuando hay datos

4. **Strategy Builder - Todos los Parámetros**
   - Path: `frontend/app/strategies/new/Liquidity/page.tsx`
   - Añadir campos faltantes:
     - `price_min` / `price_max` (actualmente hardcodeados a 0.95/0.98)
     - Todos los parámetros de orderbook (staleness, spread, depth, impact)
   - **Criterio**: Todos los parámetros configurables desde UI

5. **Simulation - Conectar Backend**
   - Path: `frontend/app/strategies/[id]/simulate/page.tsx`
   - Conectar a endpoint de simulación (si existe)
   - Mostrar resultados reales
   - **Criterio**: Simulación funciona con datos reales

**Archivos a modificar**:
- `frontend/app/strategies/[id]/live/page.tsx`
- `frontend/app/strategies/new/Liquidity/page.tsx`
- `frontend/app/strategies/[id]/simulate/page.tsx`
- `frontend/app/markets/page.tsx`

---

### 🟡 PHASE 6: Execution Engine - Completar Integración Polymarket

**Estado**: ⚠️ Cliente existe pero hay TODOs

**Pendientes**:

1. **Completar Execution Coordinator**
   - Path: `backend/app/core/strategy_engine/nodes/execution_coordinator.py`
   - Línea 128: `# TODO: Llamar a compensate_plan node`
   - Línea 282: `# TODO: Llamar a compensate_plan node`
   - Línea 486: `# TODO: Implementar llamada real a execution_engine`
   - **Criterio**: Execution Coordinator ejecuta órdenes reales en Polymarket

2. **Completar Retry Leg**
   - Path: `backend/app/core/strategy_engine/nodes/retry_leg.py`
   - Línea 150: `# TODO: Implementar ejecución real usando execution_engine`
   - **Criterio**: Retry funciona con ejecución real

3. **Completar Compensate Plan**
   - Path: `backend/app/core/strategy_engine/nodes/compensate_plan.py`
   - Línea 137: `# TODO: Implementar compensación real usando execution_engine`
   - **Criterio**: Compensación cancela/revierte órdenes reales

4. **Verificar Trading Platform Integration**
   - Path: `backend/app/core/execution/polymarket_client_wrapper.py`
   - Verificar que todos los métodos necesarios están implementados:
     - `place_order()` - Colocar orden
     - `cancel_order()` - Cancelar orden
     - `get_order_status()` - Estado de orden
     - `get_fills()` - Fills de orden
   - **Criterio**: Todas las operaciones de trading funcionan

**Archivos a modificar**:
- `backend/app/core/strategy_engine/nodes/execution_coordinator.py`
- `backend/app/core/strategy_engine/nodes/retry_leg.py`
- `backend/app/core/strategy_engine/nodes/compensate_plan.py`
- `backend/app/core/execution/polymarket_client_wrapper.py` (verificar)

---

### 🟡 PHASE 7: Universe Management

**Estado**: ⚠️ Estructura existe pero falta implementación completa

**Pendientes**:

1. **Modelo Universe en DB**
   - Path: `backend/app/models/strategy.py` (verificar si existe)
   - Campos:
     - `categories: List[str]` - Categorías permitidas
     - `markets: List[str]` - Markets específicos (polymarket_id)
     - `tags: List[str]` - Tags permitidos
     - `auto_attach: bool` - Auto-attach nuevos events
     - `deny_list: List[str]` - Markets/events excluidos
   - **Criterio**: Universe se guarda en DB y se puede actualizar

2. **API Endpoint para Universe**
   - Path: `backend/app/api/strategies.py`
   - `PUT /strategies/{id}/universe` - Actualizar universe
   - `GET /strategies/{id}/universe` - Obtener universe actual
   - **Criterio**: Frontend puede configurar universe

3. **Auto-attach de Events**
   - Path: `backend/app/core/strategy_engine/control_loop.py`
   - Cuando Scanner descubre nuevo event que cumple universe:
     - Si `auto_attach = true` → asignar automáticamente a strategy
     - Suscribir a orderbooks del event
   - **Criterio**: Nuevos events se asignan automáticamente

4. **Frontend - Universe Selector**
   - Path: `frontend/app/strategies/new/Liquidity/page.tsx`
   - Ya existe parcialmente (selectedCategories, selectedMarkets)
   - Conectar a API para guardar/actualizar
   - **Criterio**: Universe se configura y guarda correctamente

**Archivos a crear/modificar**:
- `backend/app/models/strategy.py` (añadir campos universe)
- `backend/app/api/strategies.py` (endpoints universe)
- `backend/app/core/strategy_engine/control_loop.py` (auto-attach)
- `frontend/app/strategies/new/Liquidity/page.tsx` (conectar API)

---

### 🟡 PHASE 8: Simulation Engine

**Estado**: ❌ No implementado

**Pendientes**:

1. **SimExecutionEngine**
   - Path: `backend/app/core/strategy_engine/simulation_engine.py` (nuevo)
   - Fill models:
     - `conservative`: Solo best level
     - `realistic`: Barre top-N levels según liquidez
   - **Criterio**: Simulación calcula fills basados en orderbook

2. **API Endpoint de Simulación**
   - Path: `backend/app/api/strategies.py`
   - `POST /strategies/{id}/simulate`
   - Parámetros:
     - `duration_seconds: int` - Duración de simulación
     - `capital_usdc: float` - Capital disponible
     - `fill_mode: str` - "conservative" | "realistic"
   - Retornar:
     - `estimated_pnl: float`
     - `orders_executed: int`
     - `fills_breakdown: List[Dict]`
   - **Criterio**: Simulación retorna resultados realistas

3. **Frontend - Conectar Simulación**
   - Path: `frontend/app/strategies/[id]/simulate/page.tsx`
   - Conectar a endpoint de simulación
   - Mostrar resultados con gráficos
   - **Criterio**: Simulación funciona desde UI

**Archivos a crear**:
- `backend/app/core/strategy_engine/simulation_engine.py` (nuevo)
- `backend/app/api/strategies.py` (endpoint simulate)

---

## 📋 Checklist de "Listo"

### Criterios de Aceptación Final

La estrategia Near-Resolution está **lista** cuando:

#### ✅ Backend
- [x] Orderbook Engine conectado a WebSocket y publicando a State Cache ✅ **COMPLETADO**
- [x] Strategy Near-Resolution usa orderbook_state (no last_price) ✅ backend
- [ ] Execution Prechecks funcionan y bloquean planes inválidos
- [ ] Execution Coordinator ejecuta órdenes reales en Polymarket
- [ ] Universe management funciona (auto-attach, suscripciones)
- [ ] Endpoints API completos: activate, deactivate, live-status, executions, positions
- [ ] WebSocket para updates en tiempo real

#### ✅ Frontend
- [ ] Botón Play activa estrategia y funciona end-to-end
- [ ] Botón Pause desactiva estrategia y cancela órdenes
- [ ] Live Dashboard muestra datos reales actualizándose:
  - [ ] Métricas: exposición, PnL, capital usado
  - [ ] Precheck failures con razones
  - [ ] Órdenes recientes (creadas, ejecutándose, filled)
  - [ ] Posiciones abiertas
  - [ ] Eventos asignados con estado
  - [ ] Orderbook health por asset_id
- [ ] Strategy Builder tiene todos los parámetros configurables
- [ ] Markets Page muestra métricas reales de orderbook (cuando disponibles)
- [ ] Simulation funciona con datos reales

#### ✅ Integración End-to-End
- [ ] Flujo completo funciona:
  1. Usuario crea estrategia desde UI
  2. Configura universe (markets/categories/tags)
  3. Configura parámetros (spread, depth, impact, etc.)
  4. Click "Play" → Estrategia se activa
  5. Orderbooks se suscriben automáticamente
  6. Decision Graph evalúa oportunidades
  7. Execution Plans se crean y ejecutan
  8. Órdenes se envían a Polymarket
  9. Dashboard muestra todo en tiempo real
- [ ] Datos se actualizan sin refresh (WebSocket)
- [ ] Errores se manejan gracefully (prechecks, rate limits, etc.)

---

## 🎯 Priorización

### Crítico (MVP) - Hacer Primero

1. ~~**PHASE 1**: Conectar Orderbook Engine a WebSocket~~ ✅ **COMPLETADO**
2. ~~**PHASE 2**: Actualizar Strategy para usar Orderbook~~ ✅ **COMPLETADO (backend)**
3. ~~**PHASE 3**: Execution Prechecks~~ ✅ **COMPLETADO**
4. ~~**PHASE 4**: Endpoints API para Frontend~~ ✅ **COMPLETADO**
5. **PHASE 5**: Frontend - Conectar Datos Reales ⚠️ **BLOQUEANTE** (SIGUIENTE)

### Importante (Completar MVP)

6. **PHASE 6**: Completar Execution Engine TODOs

### Nice to Have (Post-MVP)

7. **PHASE 7**: Universe Management completo
8. **PHASE 8**: Simulation Engine

---

## 📁 Archivos Clave por Fase

### PHASE 1: Orderbook ↔ WebSocket
- `backend/app/main.py`
- `backend/app/core/orderbook/ws_router.py`
- `backend/app/core/strategy_engine/control_loop.py`

### PHASE 2: Strategy Update
- `backend/app/core/strategy_engine/template_compiler.py`
- `backend/app/core/strategy_engine/nodes/collect_state.py`
- `backend/app/core/strategy_engine/nodes/calculate_order_size.py`

### PHASE 3: Prechecks
- `backend/app/core/strategy_engine/nodes/precheck.py` (nuevo)
- `backend/app/core/strategy_engine/template_compiler.py`

### PHASE 4: API Endpoints
- `backend/app/api/strategies.py`
- `backend/app/api/websocket.py` (verificar/crear)

### PHASE 5: Frontend
- `frontend/app/strategies/[id]/live/page.tsx`
- `frontend/app/strategies/new/Liquidity/page.tsx`
- `frontend/app/strategies/[id]/simulate/page.tsx`

### PHASE 6: Execution
- `backend/app/core/strategy_engine/nodes/execution_coordinator.py`
- `backend/app/core/strategy_engine/nodes/retry_leg.py`
- `backend/app/core/strategy_engine/nodes/compensate_plan.py`

---

## 🔗 Referencias

- **Plan Completo**: [`docs/implementation/orderbook-engine-implementation-plan.md`](implementation/orderbook-engine-implementation-plan.md)
- **Graph Nodes**: [`docs/architecture/graph-nodes-reference.md`](architecture/graph-nodes-reference.md)
- **Strategy Philosophy**: [`docs/strategies/README.md`](strategies/README.md)
- **Execution Engine**: [`docs/architecture/execution-engine.md`](architecture/execution-engine.md)

---

## 📝 Notas de Implementación

### Orden Recomendado de Trabajo

1. **Semana 1**: PHASE 1 + PHASE 2
   - Conectar Orderbook Engine
   - Actualizar Strategy para usar orderbook
   - Verificar que Decision Graph lee orderbook_state

2. **Semana 2**: PHASE 4 + PHASE 5 (Frontend básico)
   - Endpoints API
   - Conectar frontend a datos reales
   - Botón Play/Pause funcional

3. **Semana 3**: PHASE 3 + PHASE 6
   - Prechecks
   - Completar Execution TODOs
   - Verificar ejecución end-to-end

4. **Semana 4**: PHASE 7 + PHASE 8 (opcional)
   - Universe management
   - Simulation engine

### Testing por Fase

Cada fase debe tener:
- ✅ Tests unitarios
- ✅ Tests de integración (si aplica)
- ✅ Verificación manual en frontend
- ✅ Criterios de aceptación cumplidos

---

**Última actualización**: 2025-01-28

---

## 🎉 Logros Recientes

### 2025-01-28: Integración Completa con Polymarket ✅

**Todas las fases de integración con Polymarket están completadas y funcionando:**

- ✅ **51 tests pasando** (Fases 0-5)
- ✅ **28 endpoints implementados** y funcionando
- ✅ **WebSocket MARKET** conectado y alimentando Orderbook Engine
- ✅ **WebSocket USER** para actualizaciones en tiempo real
- ✅ **Trading operations** (crear/cancelar órdenes) funcionando
- ✅ **Datos de cuenta** (balance, órdenes, trades) accesibles
- ✅ **Protecciones y modo seguro** implementados y verificados

**Referencia completa**: [`docs/exchange/polymarket-connection-plan.md`](exchange/polymarket-connection-plan.md)

### 2025-01-28: PHASE 2 Near-Resolution (Orderbook) ✅

**Strategy Near-Resolution actualizada para usar orderbook en backend:**

- ✅ **Template compiler**: Decision Graph usa `orderbook_state.best_ask_price` y condiciones (staleness, spread, depth, impact)
- ✅ **CollectStateNode**: source `orderbook_state` lee `pm.orderbook.{asset_id}` desde State Cache
- ✅ **CalculateOrderSizeNode**: método `capacity_aware` y precio desde orderbook; tests unitarios añadidos
- ✅ **Tests**: `test_template_compiler.py`, `test_nodes.py` (orderbook_state), `test_calculate_order_size_node.py` (capacity_aware)

### 2025-01-28: PHASE 3 Execution Prechecks ✅

**PrecheckNode creado e integrado en Execution Graph:**

- ✅ **PrecheckNode**: Valida staleness, price drift, market impact y plan TTL antes de ejecutar
- ✅ **Execution Graph**: Templates y compiler generan `precheck → coordinate` flow
- ✅ **Métricas**: `plans_failed_precheck_total{reason}` registrada automáticamente
- ✅ **Tests**: `test_precheck_node.py` con 14 tests cubriendo todas las validaciones

### 2025-01-28: PHASE 4 Endpoints API para Frontend ✅

**Todos los endpoints API necesarios para el frontend implementados:**

- ✅ **activate/deactivate mejorados**: Suscriben/desuscriben orderbooks y cancelan órdenes
- ✅ **GET /strategies/{id}/live-status**: Estado en tiempo real con métricas y orderbook health
- ✅ **GET /strategies/{id}/executions**: Execution Plans con estado y legs
- ✅ **GET /strategies/{id}/positions**: Posiciones filtradas por estrategia
- ✅ **WebSocket /ws/strategies/{id}**: Updates en tiempo real con StrategyConnectionManager
- ✅ **Función helper**: `_get_asset_ids_from_strategy()` para obtener asset_ids de eventos asignados

