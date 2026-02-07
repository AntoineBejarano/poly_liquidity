# Plan de Implementación: Orderbook Engine para Near-Resolution LP

**Versión**: 1.1 (Revisado con feedback)  
**Fecha**: 2025-01-XX  
**Objetivo**: Implementar sistema completo de Near-Resolution Liquidity Provider basado en orderbooks de Polymarket

---

## 🔄 Cambios Importantes (v1.1)

### Mejoras Aplicadas

1. **✅ Snapshot-only (no delta)**: Simplificado a `update_from_snapshot()` - evita 80% de bugs de coherencia
2. **✅ BUY-side clarificado**: Todos los cálculos depth/impact marcados como "BUY side only" con warnings
3. **✅ Tick size / price rounding**: Función `round_price_to_tick()` añadida
4. **✅ Time since finished**: Reemplazado `max_time_to_resolution` por `min/max_seconds_since_finished`
5. **✅ Ref-count mejorado**: Usa `owners: Dict[str, Set[str]]` para evitar leaks y double-subscribe
6. **✅ Retención/agregación**: Plan de cleanup y rollups para evitar DB pesada
7. **✅ Simulación 2 modos**: Conservative (best level) y Realistic (barre topN)
8. **✅ Tests corregidos**: Depth@50bps y impact con tolerancias correctas
9. **✅ State Cache API**: Sección completa con ejemplos de uso

### Parser Exacto Incluido

- Payload WS: `{"bids": [{"price": ".48", "size": "30"}], ...}` (strings)
- Parser: `float(level["price"])`, `int(timestamp_str)`
- Sin fricción: Listo para implementar

---

## 📋 Índice

1. [Objetivo de Producto](#objetivo-de-producto)
2. [Principios e Invariantes](#principios-e-invariantes)
3. [Estado Actual vs Target](#estado-actual-vs-target)
4. [Plan por Fases](#plan-por-fases)
5. [Frontend: Design System y Arquitectura](#frontend-design-system-y-arquitectura)
6. [Contratos de Datos](#contratos-de-datos)
7. [Tests Unitarios por Fase](#tests-unitarios-por-fase)
8. [Criterios de Aceptación](#criterios-de-aceptación)

---

## Objetivo de Producto

### Flujo Final SaaS

1. **Conecta cuenta (wallet)**
   - Usuario conecta wallet de Polymarket
   - Sistema valida permisos y allowances

2. **Ve mercados (sincronizados desde Polymarket) + filtros**
   - Catálogo de markets desde Polymarket API
   - Filtros por categoría, series, tags
   - Búsqueda por nombre

3. **Selecciona universo (allow/deny por markets/categories/tags, auto_attach)**
   - Selección granular por strategy
   - Auto-attach de nuevos events
   - Deny list para exclusiones

4. **Configura Near-Resolution (knobs)**
   - Condiciones de entrada (spread, depth, impact, staleness)
   - Sizing (capacity-aware)
   - Execution (mode, ttl, drift limits)

5. **Botón Simular → reporte "hubieras ganado X"**
   - Paper-forward simulation
   - Fill model basado en orderbook
   - Reporte de PnL estimado

6. **Botón Play Live → suscribe orderbooks, ejecuta, dashboard PnL + exposición + trazas**
   - Suscripción automática a asset_ids
   - Ejecución con prechecks
   - Dashboard en tiempo real

---

## Principios e Invariantes

### Para Cursor (Reglas No Negociables)

1. **Decision Graph no llama APIs**
   - Solo lee State Cache
   - No hace requests HTTP/WS directamente

2. **Support Graphs/Watchers sí llaman WS/REST**
   - Actualizan State Cache
   - Son la única fuente de datos externos

3. **ExecutionPlan inmutable**
   - Una vez creado, no se modifica
   - Si necesita cambios, crear nuevo plan

4. **Execution Graph no modifica el plan**
   - Lee el plan y ejecuta
   - No altera el plan original

5. **Risk Engine siempre aprueba/rechaza**
   - No hay estados intermedios
   - Decisión binaria: APPROVED o REJECTED

6. **Compensación solo reduce exposición**
   - No aumenta exposición
   - Solo revierte o cancela

---

## Estado Actual vs Target

### ✅ Ya Existe

- **WS MARKET**: `on_book_update` / `on_price_change` en Strategy Engine
- **WS USER**: `on_trade` / `on_order_update` en Execution Engine
- **MarketState**: `best_bid/ask/last_price/spread` y `orderbook_snapshot` dict
- **Event/Market**: `polymarket_payload` contiene `clobTokenIds`
- **Strategy template**: `liquidity_near_end` + compiler + graphs + support graph external confirmation

### ❌ Falta

- **Orderbook Engine "first class"**: estado normalizado + métricas derivadas
- **Orquestación shared por asset_id**: ref-count para suscripciones
- **Feature extraction + persistencia**: para rentabilidad/capacidad/competencia
- **Strategy Near-Resolution**: debe usar orderbook metrics (no `last_price`)
- **Sizing "capacity-aware"**: bank máximo útil
- **Simulation Engine**: fill model basado en book
- **UI endpoints**: para Simulate/Play & reportes

---

## Plan por Fases

### PHASE 1: Orderbook Engine Core

**Objetivo**: Crear motor de orderbook que consume WS y publica a State Cache

**Entregables**:

1. **Estructura de módulo**
   ```
   backend/app/core/orderbook/
     __init__.py
     models.py
     book.py
     features.py
     publisher.py
     orchestrator.py
     ws_router.py
   ```

2. **Parser WS book** (payload exacto)
   - Input: `{"bids": [{"price": ".48", "size": "30"}], "asks": [...], "timestamp": "123456789000"}`
   - Output: `OrderbookLevel` objects (price/size floats, ts_ms int)

3. **OrderbookBook** (in-memory top-N)
   - Mantener top-20 bids (desc) y asks (asc)
   - `update_from_snapshot(bids, asks, ts_ms)` - **SNAPSHOT ONLY** (no delta)
   - ⚠️ **IMPORTANTE**: WS book event es snapshot del top-of-book, no delta
   - Lógica: **reemplazar completamente** y truncar a top-N
   - `compute_bbo()`
   - **NO implementar `apply_delta()` por ahora** (evita 80% de bugs de coherencia)
   - **Simplificación**: Snapshot es más simple, estable y suficiente para MVP

4. **Features calculator** (BUY-side only para Near-Resolution)
   - `spread_bps`, `mid`
   - `depth_usdc_at_Xbps_buy()` (25/50/100) - **BUY side only** (asks)
   - `impact_bps_for_usdc_buy()` (100/500/1000/5000) - **BUY side only** (asks)
   - `concentration_top3_pct_buy()` - **BUY side only** (asks)
   - `update_rate_hz` (rolling window 10s)
   - ⚠️ **NOTA**: Near-Resolution típicamente BUY YES, pero si un día operas NO/SELL, necesitarás funciones `_sell()` separadas

5. **Publisher a State Cache**
   - Key: `pm.orderbook.{asset_id}`
   - TTL: 120s
   - Incluir `staleness_ms`

6. **Orchestrator con ref-count mejorado**
   - `subscribe(asset_id, owner_key)`
   - `unsubscribe(asset_id, owner_key)`
   - **Estructura interna**:
     ```python
     owners: Dict[str, Set[str]] = {}  # asset_id -> set of owner_keys
     ref_count: Dict[str, int] = {}    # asset_id -> count (derivado de len(owners))
     ```
   - **Regla**: `ref_count[asset_id] = len(owners[asset_id])` (nunca negativo)
   - **Validaciones**:
     - Double-subscribe del mismo owner → ignorar (idempotente)
     - Unsubscribe sin subscribe previo → error/warning
   - Auto subscribe/unsubscribe WS cuando ref_count pasa 0↔1

7. **Wire WS callback**
   - Reemplazar `_handle_websocket_book_update` en Strategy
   - Llamar `orchestrator.ingest_book_msg(book_msg)`
   - Mantener compatibilidad temporal con MarketState

**Tests Unitarios**:
- ✅ Parser WS payload (strings → floats)
- ✅ OrderbookBook sorting + truncation
- ✅ Features depth@bps (BUY side)
- ✅ Features impact_bps (BUY side)
- ✅ Orchestrator ref-count lifecycle
- ✅ State Cache publishing

**Criterios de Aceptación**:
- [ ] En runtime aparecen keys `pm.orderbook.*` en State Cache
- [ ] `staleness_ms` se actualiza correctamente
- [ ] Ref-count funciona: 0→1 subscribe, 1→0 unsubscribe
- [ ] No hay memory leaks (ref-count nunca negativo)
- [ ] WS se suscribe/desuscribe correctamente

---

### PHASE 2: Feature Store (Persistencia)

**Objetivo**: Persistir micro-features en DB para análisis histórico

**Entregables**:

1. **Migración DB**
   ```sql
   CREATE TABLE market_micro_features (
     id UUID PRIMARY KEY,
     ts_ms BIGINT NOT NULL,
     market_condition_id VARCHAR NOT NULL,
     asset_id VARCHAR NOT NULL,
     best_bid_price FLOAT,
     best_bid_size FLOAT,
     best_ask_price FLOAT,
     best_ask_size FLOAT,
     spread_bps FLOAT,
     depth_usdc_at_25bps FLOAT,
     depth_usdc_at_50bps FLOAT,
     depth_usdc_at_100bps FLOAT,
     impact_bps_for_usdc_100 FLOAT,
     impact_bps_for_usdc_500 FLOAT,
     impact_bps_for_usdc_1000 FLOAT,
     impact_bps_for_usdc_5000 FLOAT,
     concentration_top3_pct FLOAT,
     update_rate_hz FLOAT,
     replenishment_score FLOAT,
     created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE INDEX idx_micro_features_ts ON market_micro_features(ts_ms DESC);
   CREATE INDEX idx_micro_features_asset ON market_micro_features(asset_id, ts_ms DESC);
   CREATE INDEX idx_micro_features_market ON market_micro_features(market_condition_id, ts_ms DESC);
   ```

2. **Persistence module**
   - `persistence.py` con batch insert
   - Buffer en memoria (100 registros o 10s)
   - Batch insert cada 10s o 100 registros

3. **Frecuencia adaptativa**
   - Default: cada 10-30s
   - Si evento `FINISHED_UNRESOLVED`: cada 1-2s (opcional v1.1)

4. **Retención y agregación** (crítico para escalabilidad)
   - **Retención**: Eliminar registros > 30 días (o configurable)
   - **Agregación opcional**: Rollups por minuto para datos > 7 días
   - **Cron job**: `cleanup_old_features()` ejecutar diariamente
   - **Índices**: Particionado lógico por `ts_ms` (rangos de tiempo)
   - **Sin retención**: DB crecerá rápidamente (1-2 semanas = DB pesada)

**Tests Unitarios**:
- ✅ Batch insert (100 registros)
- ✅ Time-based flush (10s)
- ✅ Índices funcionan para queries

**Criterios de Aceptación**:
- [ ] Features se persisten sin bloquear loop principal
- [ ] Queries históricas funcionan (por asset_id, por market, por rango de tiempo)
- [ ] No hay pérdida de datos en crash (buffer se flusha periódicamente)

---

### PHASE 3: Market Catalog / Token IDs

**Objetivo**: Asegurar que markets tienen `clobTokenIds` accesibles

**Entregables**:

1. **Sync job refuerzo**
   - Asegurar que `sync_polymarket_markets()` guarda `clobTokenIds`
   - Validar formato: `{"YES": "token_id", "NO": "token_id"}`

2. **API endpoint actualizado**
   - `GET /api/markets` incluye `outcomes` y `clobTokenIds`
   - Formato:
     ```json
     {
       "market_id": "...",
       "outcomes": [
         {"outcome": "YES", "token_id": "..."},
         {"outcome": "NO", "token_id": "..."}
       ]
     }
     ```

3. **UI selection**
   - Mostrar outcomes disponibles
   - Permitir seleccionar markets y ver tokens

**Tests Unitarios**:
- ✅ Sync guarda `clobTokenIds` correctamente
- ✅ API retorna formato esperado
- ✅ Parsing de `clobTokenIds` (dict y list formats)

**Criterios de Aceptación**:
- [ ] Todos los markets tienen `clobTokenIds` en `polymarket_payload`
- [ ] API expone tokens en formato consumible
- [ ] UI puede mostrar y seleccionar markets con tokens

---

### PHASE 4: Universe por Strategy (SaaS)

**Objetivo**: Selección de universo por estrategia (no global)

**Entregables**:

1. **Modelo StrategyUniverse**
   ```python
   class StrategyUniverse(BaseModel):
       strategy_id: UUID
       categories: List[str] = []
       markets: List[UUID] = []  # Market IDs internos
       events: List[UUID] = []   # Event IDs internos
       deny_markets: List[UUID] = []
       auto_attach: bool = True
       max_tracked_markets: int = 10
   ```

2. **Migración DB**
   ```sql
   CREATE TABLE strategy_universes (
     id UUID PRIMARY KEY,
     strategy_id UUID NOT NULL REFERENCES strategies(id),
     categories JSONB DEFAULT '[]',
     markets JSONB DEFAULT '[]',
     events JSONB DEFAULT '[]',
     deny_markets JSONB DEFAULT '[]',
     auto_attach BOOLEAN DEFAULT true,
     max_tracked_markets INT DEFAULT 10,
     created_at TIMESTAMP DEFAULT NOW(),
     updated_at TIMESTAMP DEFAULT NOW()
   );
   ```

3. **API endpoints**
   - `GET /api/strategies/{id}/universe`
   - `PUT /api/strategies/{id}/universe`

4. **Resolución a asset_ids**
   - Función: `resolve_universe_to_asset_ids(strategy_id) -> Set[str]`
   - Lógica:
     - Obtener markets/events según selection
     - Leer `clobTokenIds` de cada market/event
     - Producir set de asset_ids (YES/NO según estrategia)
     - Filtrar deny_markets

5. **Lifecycle hooks**
   - On strategy activate: `subscribe_all_assets(strategy_id)`
   - On strategy pause/stop: `unsubscribe_all_assets(strategy_id)`

**Tests Unitarios**:
- ✅ Resolución categories → markets → events → asset_ids
- ✅ Deny list funciona
- ✅ Auto-attach de nuevos events
- ✅ Subscribe/unsubscribe lifecycle

**Criterios de Aceptación**:
- [ ] Cada strategy tiene su propio universo
- [ ] Al activar strategy, se suscriben solo sus asset_ids
- [ ] Al pausar, se desuscriben todos
- [ ] Ref-count se mantiene correcto (no leaks)

---

### PHASE 5: Strategy Near-Resolution Upgrade

**Objetivo**: Actualizar estrategia para usar OrderbookState

**Entregables**:

1. **Template config extension**
   - Añadir campos en `LIQUIDITY_NEAR_END_CONFIG`:
     ```python
     {
         "key": "max_book_staleness_ms",
         "label": "Máximo staleness del orderbook (ms)",
         "type": "number",
         "default": 2000,
         "min": 100,
         "max": 10000
     },
     {
         "key": "max_spread_bps",
         "label": "Spread máximo (bps)",
         "type": "number",
         "default": 200,
         "min": 0,
         "max": 1000
     },
     {
         "key": "min_depth_usdc_at_50bps",
         "label": "Liquidez mínima a 50bps (USDC)",
         "type": "number",
         "default": 2000,
         "min": 0,
         "max": 100000
     },
     {
         "key": "max_impact_bps",
         "label": "Impacto máximo permitido (bps)",
         "type": "number",
         "default": 50,
         "min": 0,
         "max": 500
     },
     {
         "key": "order_mode",
         "label": "Modo de orden",
         "type": "select",
         "options": ["IOC", "POST_ONLY"],
         "default": "IOC"
     },
     {
         "key": "capacity_sizing_enabled",
         "label": "Sizing capacity-aware",
         "type": "boolean",
         "default": true
     },
     {
         "key": "tick_size",
         "label": "Tick size mínimo (precio)",
         "type": "number",
         "default": 0.001,
         "min": 0.0001,
         "max": 0.01,
         "step": 0.0001,
         "description": "Paso mínimo de precio (se refinará desde market data)"
     },
     {
         "key": "min_seconds_since_finished",
         "label": "Mínimo segundos desde que terminó el evento",
         "type": "number",
         "default": 60,
         "min": 0,
         "max": 3600,
         "description": "Buffer anti-falsos positivos (esperar confirmación)"
     },
     {
         "key": "max_seconds_since_finished",
         "label": "Máximo segundos desde que terminó el evento",
         "type": "number",
         "default": 1800,
         "min": 0,
         "max": 7200,
         "description": "No entrar tarde (liquidez muerta)"
     }
     ```

2. **Compiler update**
   - Modificar `compile_liquidity_near_end()` para:
     - Leer `OrderbookState` del cache (key: `pm.orderbook.{asset_id}`)
     - Añadir condiciones de entrada basadas en orderbook
     - Usar `CalculateSize` capacity-aware

3. **Decision Graph changes**
   - `collect_state` node: añadir `orderbook_state` source
   - `check_event_finished` node: añadir condiciones:
     - `event_state.state == "FINISHED_CONFIRMED"`
     - `time_since_finished >= min_seconds_since_finished`
     - `time_since_finished <= max_seconds_since_finished`
     - `orderbook_state.staleness_ms <= max_book_staleness_ms`
     - `orderbook_state.spread_bps <= max_spread_bps`
     - `orderbook_state.depth_usdc_at_50bps >= min_depth_usdc_at_50bps`
     - `orderbook_state.impact_bps_for_usdc_{bucket} <= max_impact_bps`

4. **CalculateSize node (capacity-aware)**
   - Inputs: `target_usdc`, `orderbook_state`, `risk_state`, `tick_size`
   - Compute:
     ```python
     cap_by_depth = orderbook_state.depth_usdc_at_50bps
     cap_by_impact = find_max_usdc_such_that_impact_le_max(
         orderbook_state.impact_vector,
         max_impact_bps
     )
     cap_usdc = min(cap_by_depth, cap_by_impact)
     final_usdc = min(target_usdc, cap_usdc, risk_remaining)
     
     # Price calculation
     if order_mode == "IOC":
         price = orderbook_state.best_ask_price
     elif order_mode == "POST_ONLY":
         if improve_ticks > 0:
             price = round_price_to_tick(
                 orderbook_state.best_bid_price + (tick_size * improve_ticks),
                 tick_size
             )
         else:
             price = round_price_to_tick(orderbook_state.best_bid_price, tick_size)
     
     # Round price to tick
     price = round_price_to_tick(price, tick_size)
     
     shares = final_usdc / price
     ```
   - **Función helper**: `round_price_to_tick(price, tick_size) -> float`
   - Output: `{price, shares, final_usdc, expected_bbo, ts_ms}`

5. **BuildPlan node**
   - Incluir `asset_id` explícito
   - Incluir `expected_bbo` y `ts_ms` para prechecks

**Tests Unitarios**:
- ✅ Template config parsing
- ✅ Compiler genera graph con orderbook conditions
- ✅ CalculateSize capacity-aware (tests con books sintéticos)
- ✅ Size se reduce cuando max_impact es bajo
- ✅ Size se reduce cuando depth es bajo

**Criterios de Aceptación**:
- [ ] UI guarda nuevos knobs
- [ ] Compiler produce graph con orderbook conditions
- [ ] Plans solo se generan si depth/impact/spread OK
- [ ] Size se capea correctamente por capacity

---

### PHASE 6: Execution Prechecks

**Objetivo**: Validar freshness/drift/impact antes de ejecutar

**Entregables**:

1. **Precheck node en Execution Graph**
   ```python
   class PrecheckNode(GraphNode):
       def execute(self, context):
           plan = context.get("plan")
           orderbook_state = state_cache.get(f"pm.orderbook.{plan.asset_id}")
           
           # Staleness check
           if orderbook_state.staleness_ms > plan.max_book_staleness_ms:
               return {"status": "FAIL_PRECHECK", "reason": "stale_book"}
           
           # Drift check
           if plan.order_mode == "IOC":
               drift = compute_drift(orderbook_state.best_ask, plan.expected_best_ask)
           else:
               drift = compute_drift(orderbook_state.best_bid, plan.expected_best_bid)
           
           if drift > plan.drift_bps_limit:
               return {"status": "FAIL_PRECHECK", "reason": "drift_too_high"}
           
           # Impact check
           impact = compute_impact(orderbook_state, plan.final_usdc)
           if impact > plan.max_impact_bps:
               return {"status": "FAIL_PRECHECK", "reason": "impact_too_high"}
           
           # TTL check
           if now_ms - plan.ts_ms > plan.ttl_ms:
               return {"status": "FAIL_PRECHECK", "reason": "ttl_expired"}
           
           return {"status": "OK"}
   ```

2. **Execution Graph update**
   - Añadir `precheck` node antes de `execution_coordinator`
   - Si precheck falla: marcar plan como `FAIL_PRECHECK` y terminar

3. **Trazas**
   - Incluir razón de fallo en `decision_trace`
   - Métricas: `plans_failed_precheck_total{reason}`

**Tests Unitarios**:
- ✅ Precheck bloquea por staleness
- ✅ Precheck bloquea por drift
- ✅ Precheck bloquea por impact
- ✅ Precheck bloquea por TTL
- ✅ Precheck pasa cuando todo OK

**Criterios de Aceptación**:
- [ ] No ejecuta órdenes con book stale
- [ ] No ejecuta órdenes con drift alto
- [ ] No ejecuta órdenes con impact alto
- [ ] Trazas incluyen razón de fallo

---

### PHASE 7: Simulation Engine

**Objetivo**: Paper-forward simulation con fill model

**Entregables**:

1. **Modelos DB**
   ```sql
   CREATE TABLE simulation_runs (
     id UUID PRIMARY KEY,
     strategy_id UUID NOT NULL REFERENCES strategies(id),
     duration_minutes INT NOT NULL,
     initial_capital_usdc FLOAT NOT NULL,
     mode VARCHAR NOT NULL, -- 'paper_forward'
     pnl_total FLOAT,
     trades_count INT,
     fill_rate FLOAT,
     avg_edge_bps FLOAT,
     max_exposure_usdc FLOAT,
     started_at TIMESTAMP,
     completed_at TIMESTAMP,
     created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE TABLE simulation_fills (
     id UUID PRIMARY KEY,
     simulation_run_id UUID NOT NULL REFERENCES simulation_runs(id),
     plan_id UUID,
     asset_id VARCHAR,
     side VARCHAR,
     fill_price FLOAT,
     fill_shares FLOAT,
     fill_usdc FLOAT,
     fill_ts_ms BIGINT,
     created_at TIMESTAMP DEFAULT NOW()
   );
   ```

2. **SimExecutionEngine**
   ```python
   class SimExecutionEngine:
       def __init__(self, strategy_id, duration_minutes, initial_capital):
           self.strategy_id = strategy_id
           self.duration_minutes = duration_minutes
           self.capital = initial_capital
           self.plans = []
           self.fills = []
       
       async def run(self):
           # Ejecutar Decision Graph en modo SIMULATE
           # Para cada plan generado:
           #   - Aplicar fill model
           #   - Registrar fill si aplica
           #   - Actualizar capital
           pass
       
       def apply_fill_model(self, plan, orderbook_state):
           if plan.order_mode == "IOC":
               return self._fill_ioc(plan, orderbook_state)
           else:
               return self._fill_post_only(plan, orderbook_state)
       
       def _fill_ioc(self, plan, orderbook_state, mode="conservative"):
           """
           Fill model IOC.
           
           Args:
               mode: "conservative" (solo best level) o "realistic" (barre topN)
           """
           if mode == "conservative":
               # Solo best level
               if plan.price >= orderbook_state.best_ask_price and orderbook_state.best_ask_size > 0:
                   fill_shares = min(plan.shares, orderbook_state.best_ask_size)
                   fill_price = orderbook_state.best_ask_price
                   return Fill(price=fill_price, shares=fill_shares, usdc=fill_price * fill_shares)
           else:
               # Realistic: barre topN asks (igual que impact sim)
               remaining_usdc = plan.final_usdc
               filled_shares = 0
               spent_usdc = 0
               fills = []
               
               for level in orderbook_state.asks:
                   if remaining_usdc <= 0:
                       break
                   if plan.price < level.price:
                       break  # No podemos comprar más caro
                   
                   level_usdc = level.size * level.price
                   take_usdc = min(remaining_usdc, level_usdc)
                   take_shares = take_usdc / level.price
                   
                   filled_shares += take_shares
                   spent_usdc += take_usdc
                   remaining_usdc -= take_usdc
                   fills.append((level.price, take_shares))
               
               if filled_shares > 0:
                   avg_price = spent_usdc / filled_shares
                   return Fill(price=avg_price, shares=filled_shares, usdc=spent_usdc)
           return None
       
       def _fill_post_only(self, plan, orderbook_state, stream):
           # Observar stream hasta TTL
           # Si best_ask <= plan.price: fill
           # Si TTL expira: cancel
           pass
   ```

3. **Endpoint**
   ```python
   @router.post("/strategies/{strategy_id}/simulate")
   async def simulate_strategy(
       strategy_id: UUID,
       duration_minutes: int = 60,
       initial_capital_usdc: float = 5000.0,
       fill_mode: str = "conservative",  # "conservative" | "realistic"
       db: Session = Depends(get_db)
   ):
       engine = SimExecutionEngine(
           strategy_id, 
           duration_minutes, 
           initial_capital_usdc,
           fill_mode=fill_mode
       )
       result = await engine.run()
       return result
   ```

4. **UI**
   - Botón "Simular" en strategy page
   - Selector de fill mode: "Conservative" / "Realistic"
   - Panel de resultados:
     - PnL total
     - Trades count
     - Fill rate
     - Avg edge
     - Max exposure
     - Chart de PnL over time
     - Comparación conservative vs realistic (opcional)

**Tests Unitarios**:
- ✅ Fill model IOC (fill inmediato)
- ✅ Fill model POST_ONLY (fill después de TTL)
- ✅ Fill model POST_ONLY (cancel si no fill)
- ✅ PnL calculation (near-resolution: 1.0 - entry_price)
- ✅ Capital tracking

**Criterios de Aceptación**:
- [ ] Usuario puede simular strategy
- [ ] Fill model es conservador y realista
- [ ] Reporte muestra PnL y métricas
- [ ] Simulation runs se guardan en DB

---

### PHASE 8: Frontend - Terminal Style UI

**Objetivo**: Frontend production-ready con diseño compacto tipo trading terminal

**Estrategia**: Reutilizar 80%+ del frontend existente, solo ajustar design tokens y añadir variantes compactas.

**Entregables**:

#### FE-PR1: Design System Compacto (Base)

**Objetivo**: Establecer base compacta sin romper componentes existentes

**Archivos a Modificar**:

1. **`frontend/app/globals.css`**
   - Ajustar tipografía base a `13px` (text-[13px])
   - Headings compactos: h1=16px, h2=14px, h3=13px
   - Mantener clases existentes para compatibilidad

2. **`frontend/components/ui/button.tsx`**
   - Añadir sizes: `compact` (h-8 px-3 text-[13px]) y `compact-sm` (h-7 px-2 text-[13px])
   - Mantener sizes existentes (`default`, `sm`, `lg`, `icon`)

3. **`frontend/components/ui/input.tsx`**
   - Cambiar default a `h-8 text-[13px]`
   - Mantener compatibilidad con className override

4. **`frontend/components/ui/table.tsx`**
   - Reducir paddings: `px-3 py-1.5` en TableCell
   - Font-size: `text-[13px]`
   - Preparar sticky header (TableHeader con `sticky top-0 bg-card z-10`)
   - Row height: `h-9` explícito

5. **`frontend/components/ui/card.tsx`**
   - ⚠️ **NO cambiar padding por defecto** (evitar regressions)
   - Mantener `p-6` por defecto
   - Si se necesita compacto, usar className override o crear nuevo componente `Panel`

6. **Nuevo componente: `frontend/components/ui/panel.tsx`**
   - Similar a Card pero con `p-3` por defecto
   - Para uso en terminal compacto

**Cambios Específicos**:

```tsx
// button.tsx - Añadir sizes
size: {
  default: "h-10 px-4 py-2",
  sm: "h-9 rounded-md px-3",
  compact: "h-8 px-3 text-[13px]",      // ⭐ NUEVO
  compact-sm: "h-7 px-2 text-[13px]",   // ⭐ NUEVO
  lg: "h-11 rounded-md px-8",
  icon: "h-10 w-10",
}

// input.tsx - Cambiar default
className={cn(
  "flex h-8 w-full rounded-md border border-input bg-background px-3 py-1.5 text-[13px] ring-offset-background ...",
  className
)}

// table.tsx - Reducir paddings y font
const TableHead = ... className={cn("h-9 px-3 text-left align-middle text-[13px] font-medium ...")}
const TableCell = ... className={cn("px-3 py-1.5 align-middle text-[13px] [&:has([role=checkbox])]:pr-0", className)}
const TableHeader = ... className={cn("sticky top-0 bg-card z-10 [&_tr]:border-b", className)} // ⭐ Sticky

// globals.css - Tipografía compacta
.text-h1 { font-size: 1rem; line-height: 1.25rem; }      /* 16px */
.text-h2 { font-size: 0.875rem; line-height: 1.125rem; }  /* 14px */
.text-h3 { font-size: 0.8125rem; line-height: 1rem; }     /* 13px */
.text-body { font-size: 0.8125rem; line-height: 1.25rem; } /* 13px base */
```

**Checklist de Verificación Visual**:
- [ ] Buttons con `size="compact"` miden 32px de altura (h-8)
- [ ] Buttons con `size="compact-sm"` miden 28px de altura (h-7)
- [ ] Inputs miden 32px de altura (h-8) y texto 13px
- [ ] Table cells tienen padding horizontal 12px (px-3) y vertical 6px (py-1.5)
- [ ] Table rows miden 36px de altura (h-9)
- [ ] Table header es sticky y se mantiene al hacer scroll
- [ ] Texto base en páginas es 13px (verificar en navegador DevTools)
- [ ] Headings h1=16px, h2=14px, h3=13px
- [ ] Cards mantienen `p-6` (no regresión)
- [ ] Panel nuevo tiene `p-3` cuando se use

**Archivos Modificados** (lista exacta):
1. `frontend/app/globals.css`
2. `frontend/components/ui/button.tsx`
3. `frontend/components/ui/input.tsx`
4. `frontend/components/ui/table.tsx`
5. `frontend/components/ui/panel.tsx` (nuevo)

**Tests**:
- ✅ Button sizes compact y compact-sm renderizan correctamente
- ✅ Input default es h-8 text-[13px]
- ✅ Table cells tienen padding reducido
- ✅ Table header es sticky
- ✅ Cards no tienen regresión (mantienen p-6)

**Criterios de Aceptación**:
- [ ] Design tokens compactos aplicados
- [ ] No hay regresiones visuales en componentes existentes
- [ ] Nuevas variantes funcionan correctamente
- [ ] Sticky header funciona en tablas

---

#### FE-PR2: Layout Compacto

**Entregables**:
1. Compactar Layout principal (`px-3 py-2` en lugar de `p-6`)
2. Compactar Sidebar (`p-3`, `gap-2`, `text-[13px]`)
3. Topbar compacto con search y acciones (`h-10`)

**Archivos a Modificar**:
1. `frontend/components/Layout.tsx`
2. `frontend/components/Sidebar.tsx`

---

#### FE-PR3: Markets Page "Terminal Style"

**Entregables**:
1. Tabla densa con todas las columnas especificadas
2. Filtros compactos en topbar
3. SidePanel con detalles
4. Multi-select + bulk actions

**Archivos a Modificar**:
1. `frontend/app/markets/page.tsx`
2. `frontend/components/markets/MarketsListWithLoader.tsx`
3. Nuevo: `frontend/components/ui/side-panel.tsx`

---

#### FE-PR4: Strategy Builder Compacto

**Entregables**:
1. Layout 3 columnas (Universe | Knobs | Summary)
2. Form compacto con accordion
3. Validaciones live
4. Summary panel

**Archivos a Modificar**:
1. `frontend/app/strategies/new/page.tsx`
2. `frontend/app/strategies/[id]/edit/page.tsx` (si existe)
3. `frontend/components/StrategyConfigForm.tsx`

---

#### FE-PR5: Live Terminal

**Entregables**:
1. Topbar con status + capital + acciones
2. Split 70/30: tabla + panel derecho
3. Tabla con métricas de orderbook
4. Panel derecho: health + precheck failures + recent orders

**Archivos a Modificar**:
1. `frontend/app/strategies/[id]/live/page.tsx`
2. Nuevo: `frontend/components/ui/kpi-bar.tsx`
3. Nuevo: `frontend/components/ui/status-pill.tsx`
4. Nuevo: `frontend/components/ui/metric-chip.tsx`

---

#### FE-PR6: Simulation UI

**Entregables**:
1. Modal/página de simulación
2. Inputs compactos
3. Reportes y KPIs

**Archivos a Modificar**:
1. Nuevo: `frontend/app/strategies/[id]/simulate/page.tsx` o modal
2. Integración con endpoint `/strategies/{id}/simulate`

---

#### FE-PR7: Componentes Nuevos Compactos

**Entregables**:
1. `DenseTable` con virtualización
2. `KPIBar`
3. `StatusPill`
4. `MetricChip`
5. `InlineForm`
6. `ConfirmModal`
7. `SidePanel`

**Archivos Nuevos**:
1. `frontend/components/ui/dense-table.tsx`
2. `frontend/components/ui/kpi-bar.tsx`
3. `frontend/components/ui/status-pill.tsx`
4. `frontend/components/ui/metric-chip.tsx`
5. `frontend/components/ui/inline-form.tsx`
6. `frontend/components/ui/side-panel.tsx`

---

#### FE-PR8: Eliminar "Colorines" (Paleta Monocromática)

**Entregables**:
1. Paleta monocromática en `globals.css`
2. Charts en escala de grises
3. Revisar y reemplazar colores hardcoded

**Archivos a Modificar**:
1. `frontend/app/globals.css` (colores charts y status)
2. Revisar todos los componentes con `bg-*-500` hardcoded

**Tests Unitarios**:
- ✅ Componentes base renderizan con tokens correctos
- ✅ Tablas virtualizadas con muchos rows
- ✅ Validaciones de formulario
- ✅ Integración con endpoints

**Criterios de Aceptación**:
- [ ] UI es compacta y densa (tipo trading terminal)
- [ ] Todas las acciones son keyboard-friendly
- [ ] Performance: tablas con 1000+ rows sin lag
- [ ] Responsive en desktop (mínimo 1280px)
- [ ] Design tokens aplicados consistentemente
- [ ] No hay regresiones visuales
- [ ] Paleta monocromática (sin colorines)

---

## Frontend: Design System y Arquitectura

### 📋 Análisis del Frontend Existente

**Documento completo**: Ver `docs/implementation/frontend-compact-terminal-analysis.md`

#### ✅ Lo que YA tenemos y podemos REUTILIZAR

1. **Infraestructura Base** (100% reutilizable):
   - ✅ Next.js 14 App Router
   - ✅ shadcn/ui (Button, Card, Input, Table, etc.)
   - ✅ Tailwind CSS con design tokens
   - ✅ TypeScript completo
   - ✅ Layout + Sidebar funcional
   - ✅ CommandPalette existente
   - ✅ ThemeToggle (dark mode)
   - ✅ Skeleton loading implementado

2. **Componentes UI Base** (reutilizables con ajustes):
   - ✅ `Button` - Añadir variante `compact` (h-8, h-7)
   - ✅ `Card` - Ajustar padding a `p-3`, `rounded-xl`
   - ✅ `Input` - Ajustar altura a `h-8`
   - ✅ `Table` - Ajustar rows a `h-9`, cells a `px-3`
   - ✅ `Badge`, `Select`, `Dropdown` - Reutilizables

3. **Páginas Existentes** (estructura reutilizable):
   - ✅ `/markets` - Compactar y convertir a tabla densa
   - ✅ `/strategies/[id]/live` - Reorganizar a split 70/30
   - ✅ `/strategies/new` - Rebuild compacto 3 columnas
   - ✅ Layout base - Reutilizable

4. **Hooks y Utilidades** (100% reutilizables):
   - ✅ `useBackendConnection`
   - ✅ `useComponentDataLoader`
   - ✅ `useRealtimeStrategy`
   - ✅ `lib/api.ts`

#### 🔧 Cambios Necesarios (sin reescribir)

**Principio**: Ajustar, no reescribir. Añadir variantes compactas manteniendo compatibilidad.

1. **Design Tokens Compactos**:
   - Tipografía: `text-[13px]` base (en lugar de 14px)
   - Spacing: `px-3 py-2`, `gap-2` (en lugar de `p-6`, `gap-4`)
   - Inputs: `h-8` (en lugar de `h-10`)
   - Buttons: `h-8` primary, `h-7` secondary (añadir variantes)
   - Tables: `h-9` rows, `px-3` cells (en lugar de `h-12`, `px-4`)

2. **Layout Compacto**:
   - Main container: `px-3 py-2` (en lugar de `p-6`)
   - Sidebar: `p-3`, `gap-2`, `text-[13px]` (reducir padding/gap)
   - Topbar: `h-10` con search y acciones (en lugar de `h-14` solo theme toggle)

3. **Eliminar "Colorines"**:
   - Paleta monocromática (grises + acentos sutiles)
   - Charts en escala de grises
   - Status colors apagados (no vibrantes)

**Ver análisis completo en**: 
- `docs/implementation/frontend-compact-terminal-analysis.md` - Análisis del frontend existente
- `docs/implementation/frontend-field-naming-guide.md` - Guía de nombres simples en UI

---

### Dirección de Diseño

**Principios**:
- **Alta densidad informativa**: Más tabla, menos cards enormes
- **1 layout, 3 vistas**: Markets, Strategy Builder, Live/Sim
- **Acciones primarias siempre visibles**: Play/Pause/Simulate/Stop arriba a la derecha
- **Keyboard-friendly**: Search con `/`, navegar con flechas, `Enter` para aplicar
- **Sin "padding de marketing"**: `px-3 py-2` como base, `gap-2`

### Design Tokens (Tailwind)

```css
/* Base */
font-size: 13px;
line-height: 1.25rem (20px);

/* Headings */
h1: text-base (16px)
h2: text-sm (14px)
h3: text-[13px]

/* Inputs */
height: 2rem (32px)
padding: px-3 py-1.5
font-size: text-[13px]

/* Buttons */
Primary: h-8 px-3 text-[13px]
Secondary: h-7 px-2 text-[13px]

/* Cards */
padding: p-3
rounded: rounded-xl
shadow: shadow-sm
border: border bg-background

/* Spacing */
Containers: px-3 py-2
Grids: gap-2
Forms: space-y-2

/* Tables */
Row height: h-9
Hover: bg-muted/50 (sutil)
```

### Information Architecture

#### A) `/markets` - Catálogo

**Objetivo**: Filtrar, inspeccionar, y "añadir al universo" rápido

**Layout**:
```
┌─────────────────────────────────────────────────────────┐
│ Topbar: [Search /] [Category▼] [Series▼] [Tags▼] [...] │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Markets Table (full width)                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Market | Status | YES Token | NO Token | Spread │   │
│  │ ...    | ...    | ...       | ...      | ...    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                           │
│  [Panel Derecho - Collapsible]                          │
│  ┌─────────────────┐                                     │
│  │ Market Details  │                                     │
│  │ Outcomes        │                                     │
│  │ Token IDs       │                                     │
│  │ [Add to Universe]                                    │
│  └─────────────────┘                                     │
└─────────────────────────────────────────────────────────┘
```

**Tabla Columns** (compacta, nombres simples):
- **Market**: Question + chips tags
- **Status**: "Tradable" / "Resolved" + end_time
- **YES Token**: Truncado con copy button (tooltip: "Token ID para outcome YES")
- **NO Token**: Truncado con copy button (tooltip: "Token ID para outcome NO")
- **Spread**: "150 bps" (si orderbook suscrito, tooltip: "Diferencia entre mejor bid y ask")
- **Liquidity**: "$2.5k" (en lugar de Depth@50, tooltip: "Liquidez disponible a 50bps")
- **Impact**: "30 bps" (en lugar de Impact@1000, tooltip: "Impacto al ejecutar $1000")
- **Actions**: "Add to Universe" (dropdown strategy, tooltip: "Añadir este market al universo de la estrategia")

**UX Clave**:
- Hover row → preview en panel derecho
- Multi-select + "Add selected to strategy universe"
- Keyboard: `/` focus search, `↑↓` navegar, `Enter` seleccionar

#### B) `/strategies/new` y `/strategies/{id}/edit` - Builder

**Objetivo**: Configurar Near-Resolution en 2-3 minutos, sin scroll infinito

**Estructura 3 Columnas**:
```
┌──────────────┬──────────────────┬──────────────┐
│ Universe     │ Knobs            │ Summary      │
│ (izquierda)  │ (centro)         │ (derecha)    │
│              │                  │              │
│ Categories   │ [Orderbook]      │ "Lo que va   │
│ Markets      │ [Timing]         │  a hacer"    │
│ Events       │ [Sizing]        │              │
│ Deny         │ [Execution]      │ Validaciones │
│ Auto-attach  │                  │ Warnings     │
└──────────────┴──────────────────┴──────────────┘
```

**Knobs en Grupos** (accordion compacto):

**Principio**: Nombres simples y amigables en UI, con tooltips/modales explicativos. Nombres técnicos solo en backend.

1. **Orderbook Constraints**:
   - **"Book Freshness"** (label) → `max_book_staleness_ms` (backend)
     - Tooltip: "Tiempo máximo que puede pasar sin actualizarse el orderbook (ms). Si es muy alto, los precios pueden estar desactualizados."
   - **"Max Spread"** (label) → `max_spread_bps` (backend)
     - Tooltip: "Diferencia máxima entre mejor bid y ask (en basis points). Spread alto = menos liquidez."
   - **"Min Liquidity"** (label) → `min_depth_usdc_at_50bps` (backend)
     - Tooltip: "Liquidez mínima disponible a 50bps del mejor precio (USDC). Asegura que hay suficiente volumen para tu orden."
   - **"Max Price Impact"** (label) → `max_impact_bps` (backend)
     - Tooltip: "Impacto máximo en precio al ejecutar tu orden (basis points). Impacto alto = tu orden mueve el mercado."

2. **Timing**:
   - **"Wait After Finish"** (label) → `min_seconds_since_finished` (backend)
     - Tooltip: "Segundos mínimos a esperar después de que termine el evento. Evita falsos positivos antes de confirmación."
   - **"Max Time After Finish"** (label) → `max_seconds_since_finished` (backend)
     - Tooltip: "Segundos máximos después de que termine el evento. Evita entrar cuando la liquidez ya se agotó."

3. **Sizing**:
   - **"Order Size"** (label) → `order_usdc` (backend)
     - Tooltip: "Tamaño de orden en USDC (fijo o rango)."
   - **"Smart Sizing"** (label) → `capacity_sizing_enabled` (backend)
     - Tooltip: "Ajusta automáticamente el tamaño según la liquidez disponible. Evita órdenes demasiado grandes que muevan el mercado."

4. **Execution**:
   - **"Order Type"** (label) → `order_mode` (backend)
     - Options: "Market" (IOC) / "Limit" (POST_ONLY)
     - Tooltip: "Market = ejecuta inmediatamente. Limit = espera a que alguien tome tu precio."
   - **"Order Timeout"** (label) → `ttl_ms` (backend)
     - Tooltip: "Tiempo máximo que la orden puede estar pendiente (ms). Si expira, se cancela."
   - **"Price Drift Limit"** (label) → `drift_bps_limit` (backend)
     - Tooltip: "Cambio máximo permitido en precio desde que se creó el plan (basis points). Si el precio cambia mucho, no ejecuta."
   - **"Price Step"** (label) → `tick_size` (backend)
     - Tooltip: "Paso mínimo de precio permitido (ej: 0.001). Los precios se redondean a este paso."
   - **"Improve Price By"** (label) → `improve_ticks` (backend, solo si POST_ONLY)
     - Tooltip: "Mejora el precio en X pasos respecto al mejor bid. Aumenta probabilidad de ejecución."

**Validaciones Live** (con mensajes simples):
- Si POST_ONLY y `improve_ticks=0` → ⚠️ warning "Tu precio iguala el mejor bid. Podría no ejecutarse."
- Si `max_impact` muy bajo → ⚠️ warning "Impacto máximo muy bajo. El tamaño de orden será pequeño."
- Si `min_depth` alto → ⚠️ warning "Liquidez mínima muy alta. Pocos mercados cumplirán este requisito."

#### C) `/strategies/{id}/live` - Terminal

**Objetivo**: Operar y confiar

**Topbar**:
```
┌─────────────────────────────────────────────────────────┐
│ [Status: ACTIVE] Capital: $2.5k/$5k | Exposure: $1.2k  │
│ [Simulate] [Play] [Pause] [Stop] [Kill Switch]         │
└─────────────────────────────────────────────────────────┘
```

**Main Split**:
```
┌──────────────────────────────────┬─────────────────────┐
│ Markets/Events Table (70%)       │ Right Panel (30%)   │
│                                   │                     │
│ Event | Phase | Confirmed | BBO  │ Orderbook Health    │
│ ...   | ...   | ...       | ...  │ WS: ✅ Connected    │
│                                   │ Staleness p95: 1.2s │
│                                   │ Update rate: 5.3 Hz │
│                                   │                     │
│                                   │ Precheck Failures   │
│                                   │ stale_book: 2       │
│                                   │ drift_too_high: 1   │
│                                   │                     │
│                                   │ Recent Orders       │
│                                   │ #12345 FILLED       │
│                                   │ #12346 PENDING      │
└──────────────────────────────────┴─────────────────────┘
```

**Markets/Events Table Columns** (nombres simples):
- **Event**: Name (compact)
- **Status**: "In Play" / "Finished" / "Resolved" (en lugar de IN_PLAY/FINISHED_UNRESOLVED/RESOLVED)
- **Confirmed**: ✅/❌ + confidence % (tooltip: "Confirmado por fuente externa")
- **Best Price**: "0.50 / 0.52" (en lugar de BBO, tooltip: "Mejor bid / mejor ask")
- **Spread**: "150 bps" (con color: green < 100, yellow < 200, red >= 200)
  - Tooltip: "Diferencia entre mejor bid y ask. Spread bajo = más liquidez."
- **Liquidity**: "$2.5k" (en lugar de Depth@50, tooltip: "Liquidez disponible a 50bps del mejor precio")
- **Impact**: "30 bps" (en lugar de Impact@1000, tooltip: "Impacto en precio al ejecutar $1000")
- **Freshness**: "1.2s" (en lugar de Staleness, tooltip: "Tiempo desde última actualización del orderbook")
  - Con color: green < 1s, yellow < 2s, red >= 2s
- **Last Action**: "Plan Created" / "Precheck Failed" / "Filled" (en lugar de nombres técnicos)
  - Tooltip al hover: razón detallada
- **PnL**: "$234.56" (si aplica)

**Right Panel Widgets** (nombres simples):
1. **Orderbook Health**:
   - "Connected" / "Disconnected" (en lugar de WS connected status)
   - "Freshness p95: 1.2s" (en lugar de Staleness p95, tooltip: "95% de los orderbooks se actualizan en menos de este tiempo")
   - "Update Rate: 5.3 Hz" (tooltip: "Frecuencia de actualizaciones por segundo")

2. **Precheck Failures** (en lugar de "Precheck Failures Breakdown"):
   - "Book Stale: 2" (en lugar de stale_book, tooltip: "Órdenes rechazadas porque el orderbook estaba desactualizado")
   - "Price Changed: 1" (en lugar de drift_too_high, tooltip: "Órdenes rechazadas porque el precio cambió demasiado")
   - "Impact Too High: 0" (en lugar de impact_too_high, tooltip: "Órdenes rechazadas porque el impacto sería muy alto")
   - "Timeout: 0" (en lugar de ttl_expired, tooltip: "Órdenes rechazadas porque expiró el tiempo límite")

3. **Recent Orders** (en lugar de "Recent Orders List"):
   - Order ID (truncado), Status ("Filled" / "Pending" / "Failed"), Price, Size, Time
   - Tooltip al hover: detalles completos

#### D) Simulación: Modal o `/strategies/{id}/simulate`

**Inputs Compactos** (nombres simples):
- **"Duration"** → `duration_minutes` (select: "15 min" / "30 min" / "60 min")
  - Tooltip: "Tiempo de simulación"
- **"Initial Capital"** → `initial_capital` (input number, label: "$")
  - Tooltip: "Capital inicial para la simulación"
- **"Fill Model"** → `fill_mode` (select: "Conservative" / "Realistic")
  - Tooltip: "Conservative = solo mejor nivel. Realistic = barre varios niveles (más realista)"

**Output** (nombres simples):
- **KPI Row**: 
  - "PnL: $234.56" (tooltip: "Profit and Loss total")
  - "Fill Rate: 87%" (tooltip: "Porcentaje de órdenes ejecutadas")
  - "Trades: 12" (tooltip: "Número de trades ejecutados")
  - "Avg Edge: 2.3%" (tooltip: "Ventaja promedio por trade")
  - "Max Exposure: $2.5k" (tooltip: "Exposición máxima simultánea")
- **Tabs**:
  - "Summary" (overview con KPIs)
  - "Fills" (table detallada de ejecuciones)
  - "Top Markets" (en lugar de "Markets ranking", ranking de mejores performers)

### Componentes Core

#### Topbar Component
```tsx
<Topbar>
  <Search placeholder="Search /" />
  <Filters>
    <CategoryFilter />
    <SeriesFilter />
    <TagsFilter />
  </Filters>
  <Actions>
    <Button variant="primary">Play</Button>
    <Button variant="secondary">Pause</Button>
  </Actions>
</Topbar>
```

#### DenseTable Component
```tsx
<DenseTable
  data={markets}
  columns={columns}
  virtualized={true}  // Si > 100 rows
  onRowHover={(row) => setPreview(row)}
  rowHeight={36}  // h-9
/>
```

#### SidePanel Component
```tsx
<SidePanel
  open={isOpen}
  onClose={() => setIsOpen(false)}
  position="right"
  width="w-80"
>
  {preview && <MarketDetails market={preview} />}
</SidePanel>
```

#### KPIBar Component
```tsx
<KPIBar>
  <KPI label="PnL" value="$234.56" trend="up" />
  <KPI label="Fill Rate" value="87%" />
  <KPI label="Trades" value="12" />
  <KPI label="Avg Edge" value="2.3%" />
  <KPI label="Max Exposure" value="$2.5k" />
</KPIBar>
```

#### StatusPill Component
```tsx
<StatusPill status="active" />  // green
<StatusPill status="paused" />  // yellow
<StatusPill status="error" />    // red
```

#### MetricChip Component (con tooltip)
```tsx
// frontend/components/ui/metric-chip.tsx
'use client';

import { InfoTooltip } from './info-tooltip';

interface MetricChipProps {
  label: string;
  value: string;
  color?: 'green' | 'yellow' | 'red' | 'neutral';
  tooltip?: string;
}

export function MetricChip({ label, value, color = 'neutral', tooltip }: MetricChipProps) {
  const colorStyles = {
    green: 'text-green-600 dark:text-green-400',
    yellow: 'text-yellow-600 dark:text-yellow-400',
    red: 'text-red-600 dark:text-red-400',
    neutral: 'text-foreground',
  };
  
  return (
    <div className="flex items-center gap-1.5 px-2 py-1 rounded border bg-card">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      {tooltip && <InfoTooltip content={tooltip} />}
      <span className={`text-[13px] font-medium ${colorStyles[color]}`}>{value}</span>
    </div>
  );
}

// Uso:
<MetricChip
  label="Spread"
  value="150 bps"
  color="yellow"
  tooltip="Diferencia entre mejor bid y ask. Spread bajo = más liquidez."
/>
<MetricChip
  label="Freshness"
  value="1.2s"
  color="green"
  tooltip="Tiempo desde última actualización del orderbook. Fresco = datos actualizados."
/>
```

#### InlineForm Component (con tooltip integrado)
```tsx
// frontend/components/ui/inline-form.tsx
'use client';

import { Label } from './label';
import { InfoTooltip } from './info-tooltip';

interface InlineFormProps {
  label: string;
  tooltip?: string;
  tooltipTitle?: string;
  input: React.ReactNode;
  error?: string;
}

export function InlineForm({ label, tooltip, tooltipTitle, input, error }: InlineFormProps) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1">
        <Label className="text-[13px]">{label}</Label>
        {tooltip && <InfoTooltip content={tooltip} title={tooltipTitle} />}
      </div>
      {input}
      {error && <p className="text-[11px] text-destructive">{error}</p>}
    </div>
  );
}

// Uso:
<InlineForm
  label="Book Freshness"
  tooltip="Tiempo máximo que puede pasar sin actualizarse el orderbook (ms). Si es muy alto, los precios pueden estar desactualizados."
  tooltipTitle="¿Qué es Book Freshness?"
  input={<Input type="number" defaultValue={2000} className="h-8" placeholder="ms" />}
/>
```

#### ConfirmModal Component
```tsx
<ConfirmModal
  open={showStop}
  title="Stop Strategy?"
  message="This will cancel all pending orders."
  onConfirm={handleStop}
  onCancel={() => setShowStop(false)}
  variant="destructive"
/>
```

### Estilo Compacto (Tailwind Guidelines)

**Evitar**:
- `p-6`, `p-8` (demasiado padding)
- `text-xl`, `text-2xl` (demasiado grande)
- `gap-4`, `gap-6` (demasiado espacio)
- Cards enormes con "hero sections"

**Usar**:
- Contenedores: `px-3 py-2`
- Grids: `gap-2`
- Forms: `space-y-2`
- Inputs: `h-8 text-[13px]`
- Buttons: `h-8 px-3 text-[13px]` (primary), `h-7 px-2 text-[13px]` (secondary)
- Cards: `p-3 rounded-xl shadow-sm border bg-background`
- Tables: `h-9` row height, hover `bg-muted/50`

### Frontend Tickets (Cursor-Ready)

#### FE-PR1: Design System Compacto (Base) - IMPLEMENTAR PRIMERO

**Objetivo**: Establecer base compacta sin romper componentes existentes

**Estrategia**: Ajustar design tokens y añadir variantes, NO cambiar defaults de componentes existentes.

**Archivos a Modificar**:

1. **`frontend/app/globals.css`**
   ```css
   /* Tipografía compacta */
   .text-h1 {
     font-size: 1rem;        /* 16px - compacto */
     line-height: 1.25rem;    /* 20px */
     font-weight: 600;
   }
   
   .text-h2 {
     font-size: 0.875rem;    /* 14px */
     line-height: 1.125rem;   /* 18px */
     font-weight: 600;
   }
   
   .text-h3 {
     font-size: 0.8125rem;   /* 13px */
     line-height: 1rem;      /* 16px */
     font-weight: 600;
   }
   
   .text-body {
     font-size: 0.8125rem;   /* 13px - base */
     line-height: 1.25rem;    /* 20px */
   }
   
   .text-caption {
     font-size: 0.75rem;      /* 12px */
     line-height: 1rem;       /* 16px */
   }
   ```

2. **`frontend/components/ui/button.tsx`**
   ```tsx
   size: {
     default: "h-10 px-4 py-2",        // Mantener
     sm: "h-9 rounded-md px-3",        // Mantener
     compact: "h-8 px-3 text-[13px]",  // ⭐ NUEVO
     compact-sm: "h-7 px-2 text-[13px]", // ⭐ NUEVO
     lg: "h-11 rounded-md px-8",       // Mantener
     icon: "h-10 w-10",                // Mantener
   }
   ```

3. **`frontend/components/ui/input.tsx`**
   ```tsx
   className={cn(
     "flex h-8 w-full rounded-md border border-input bg-background px-3 py-1.5 text-[13px] ring-offset-background ...",
     className
   )}
   ```

4. **`frontend/components/ui/table.tsx`**
   ```tsx
   const TableHeader = ... className={cn("sticky top-0 bg-card z-10 [&_tr]:border-b", className)}
   const TableHead = ... className={cn("h-9 px-3 text-left align-middle text-[13px] font-medium ...")}
   const TableCell = ... className={cn("px-3 py-1.5 align-middle text-[13px] [&:has([role=checkbox])]:pr-0", className)}
   const TableRow = ... className={cn("border-b transition-colors hover:bg-muted/50 h-9", className)}
   ```

5. **`frontend/components/ui/card.tsx`**
   - ⚠️ **NO cambiar** - Mantener `p-6` por defecto para evitar regresiones

6. **Nuevo: `frontend/components/ui/panel.tsx`**
   ```tsx
   const Panel = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
     ({ className, ...props }, ref) => (
       <div
         ref={ref}
         className={cn(
           "rounded-xl border bg-card text-card-foreground shadow-sm p-3", // p-3 compacto
           className
         )}
         {...props}
       />
     )
   )
   ```

**Checklist de Verificación Visual** (Manual):
- [ ] **Buttons**: `size="compact"` mide exactamente 32px altura (h-8)
- [ ] **Buttons**: `size="compact-sm"` mide exactamente 28px altura (h-7)
- [ ] **Inputs**: Todos miden 32px altura (h-8) y texto 13px
- [ ] **Table cells**: Padding horizontal 12px (px-3), vertical 6px (py-1.5)
- [ ] **Table rows**: Altura 36px (h-9)
- [ ] **Table header**: Es sticky y se mantiene visible al hacer scroll
- [ ] **Texto base**: 13px en todas las páginas (verificar con DevTools)
- [ ] **Headings**: h1=16px, h2=14px, h3=13px
- [ ] **Cards**: Mantienen `p-6` (verificar que no hay regresión)
- [ ] **Panel nuevo**: Tiene `p-3` cuando se use

**Lista de Archivos Modificados**:
1. ✅ `frontend/app/globals.css` - Tipografía compacta
2. ✅ `frontend/components/ui/button.tsx` - Añadir sizes compact
3. ✅ `frontend/components/ui/input.tsx` - Default h-8 text-[13px]
4. ✅ `frontend/components/ui/table.tsx` - Padding reducido + sticky header
5. ✅ `frontend/components/ui/panel.tsx` - Nuevo componente (p-3)

**Tests**:
- ✅ Button sizes compact y compact-sm renderizan correctamente
- ✅ Input default es h-8 text-[13px]
- ✅ Table cells tienen padding reducido (px-3 py-1.5)
- ✅ Table header es sticky
- ✅ Cards mantienen p-6 (no regresión)

**Criterios de Aceptación**:
- [ ] Design tokens compactos aplicados
- [ ] No hay regresiones visuales en componentes existentes
- [ ] Nuevas variantes funcionan correctamente
- [ ] Sticky header funciona en tablas
- [ ] Checklist visual completado

---

#### FE-PR2: Layout Compacto

**Entregables**:
1. Compactar Layout principal (`px-3 py-2` en lugar de `p-6`)
2. Compactar Sidebar (`p-3`, `gap-2`, `text-[13px]`)
3. Topbar compacto con search y acciones (`h-10`)

**Archivos a Modificar**:
1. `frontend/components/Layout.tsx`
2. `frontend/components/Sidebar.tsx`

**Cambios Específicos**:
```tsx
// Layout.tsx
<main className="flex-1 overflow-y-auto">
  <div className="min-h-full px-3 py-2 max-w-[1920px] mx-auto w-full"> {/* px-3 py-2 */}
    <DynamicBreadcrumbs />
    {children}
  </div>
</main>

<header className="h-10 border-b border-border bg-card flex items-center justify-between px-3 flex-shrink-0"> {/* h-10, px-3 */}
  {/* Search + Actions */}
</header>

// Sidebar.tsx
<aside className="w-64 bg-card h-screen flex flex-col border-r border-border flex-shrink-0">
  <div className="p-3 border-b border-border flex-shrink-0"> {/* p-3 */}
    {/* Logo */}
  </div>
  <nav className="flex-1 p-3 overflow-y-auto space-y-1"> {/* p-3, space-y-1 */}
    {/* Nav items con gap-2, text-[13px] */}
  </nav>
</aside>
```

**Checklist de Verificación Visual**:
- [ ] Layout principal tiene padding reducido (px-3 py-2)
- [ ] Sidebar tiene padding reducido (p-3)
- [ ] Topbar mide 40px altura (h-10)
- [ ] Nav items en sidebar usan text-[13px]
- [ ] Espaciado entre items es gap-2

---

#### FE-PR3: Markets Page "Terminal Style"

**Entregables**:
1. Tabla densa con columns especificadas
2. Filtros compactos en topbar
3. SidePanel con detalles de market
4. Acción "Add to Strategy Universe" (si endpoint existe)
5. Multi-select + bulk actions

**Archivos a Modificar**:
1. `frontend/app/markets/page.tsx`
2. `frontend/components/markets/MarketsListWithLoader.tsx`
3. Nuevo: `frontend/components/ui/side-panel.tsx`

**Cambios Específicos**:
- Usar `Table` con nuevos paddings compactos
- Filtros con `Input` h-8 y `Button` size="compact"
- SidePanel colapsable a la derecha
- Tabla con sticky header

**Tests**:
- ✅ Tabla renderiza 1000+ markets sin lag
- ✅ Filtros funcionan correctamente
- ✅ Hover row muestra preview
- ✅ Copy token ID funciona

**Criterios de Aceptación**:
- [ ] Tabla densa y performante
- [ ] Filtros en línea (no dropdowns enormes)
- [ ] Panel lateral colapsable
- [ ] Keyboard navigation funciona

---

#### FE-PR4: Strategy Builder Compacto (Near-Resolution)

**Entregables**:
1. Layout 3 columnas (Universe | Knobs | Summary)
2. Form compacto con secciones (accordion)
3. Universe editor (allow/deny/auto_attach)
4. Summary panel con validaciones live
5. Warnings dinámicos según configuración
6. **Nombres simples en UI** (no técnicos)
7. **Tooltips/Modales explicativos** para cada campo

**Archivos a Modificar**:
1. `frontend/app/strategies/new/page.tsx`
2. `frontend/app/strategies/[id]/edit/page.tsx` (si existe)
3. `frontend/components/StrategyConfigForm.tsx`

**Estructura** (con nombres simples y tooltips):
```tsx
<div className="flex gap-2 h-full">
  {/* Universe (25%) */}
  <div className="w-[25%] border-r p-3 space-y-2">
    <h3 className="text-sm font-semibold">
      Universe
      <InfoIcon 
        className="ml-1 h-3 w-3 text-muted-foreground cursor-help" 
        onClick={() => setShowUniverseTooltip(true)}
      />
    </h3>
    {showUniverseTooltip && (
      <Tooltip>
        Selecciona qué markets/events operará esta estrategia. 
        Puedes incluir por categoría, series, o markets específicos.
      </Tooltip>
    )}
    {/* Categories, Markets, Events, Deny, Auto-attach */}
  </div>
  
  {/* Knobs (50%) */}
  <div className="flex-1 p-3 space-y-2">
    <Accordion type="multiple" className="space-y-2">
      <AccordionItem value="orderbook" className="border rounded-lg">
        <AccordionTrigger className="px-3 py-2 text-sm">
          Orderbook Constraints
          <InfoIcon 
            className="ml-1 h-3 w-3 text-muted-foreground cursor-help" 
            onClick={(e) => { e.stopPropagation(); setShowOrderbookTooltip(true); }}
          />
        </AccordionTrigger>
        {showOrderbookTooltip && (
          <Tooltip>
            Condiciones que debe cumplir el orderbook para entrar en un trade. 
            Aseguran que hay suficiente liquidez y que los precios están actualizados.
          </Tooltip>
        )}
        <AccordionContent className="px-3 pb-3 space-y-2">
          <InlineForm 
            label="Book Freshness" 
            tooltip="Tiempo máximo sin actualizarse (ms). Si es muy alto, precios desactualizados."
            input={<Input type="number" defaultValue={2000} className="h-8" placeholder="ms" />} 
          />
          <InlineForm 
            label="Max Spread" 
            tooltip="Diferencia máxima entre bid y ask (bps). Spread alto = menos liquidez."
            input={<Input type="number" defaultValue={200} className="h-8" placeholder="bps" />} 
          />
          <InlineForm 
            label="Min Liquidity" 
            tooltip="Liquidez mínima a 50bps del mejor precio (USDC)."
            input={<Input type="number" defaultValue={2000} className="h-8" placeholder="USDC" />} 
          />
          <InlineForm 
            label="Max Price Impact" 
            tooltip="Impacto máximo en precio al ejecutar (bps). Impacto alto = mueve el mercado."
            input={<Input type="number" defaultValue={50} className="h-8" placeholder="bps" />} 
          />
        </AccordionContent>
      </AccordionItem>
      {/* ... más secciones con tooltips similares ... */}
    </Accordion>
  </div>
  
  {/* Summary (25%) */}
  <div className="w-[25%] border-l p-3 space-y-2">
    <h3 className="text-sm font-semibold">Summary</h3>
    {/* Validaciones y warnings con mensajes simples */}
  </div>
</div>
```

**Componente Tooltip/InfoIcon**:
```tsx
// Nuevo: frontend/components/ui/info-tooltip.tsx
export function InfoTooltip({ content, children }: { content: string; children?: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <InfoIcon 
        className="h-3 w-3 text-muted-foreground cursor-help inline-block ml-1" 
        onClick={() => setOpen(true)}
      />
      {open && (
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Información</DialogTitle>
            </DialogHeader>
            <p className="text-sm">{content}</p>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
```

**Mapeo Nombres UI → Backend**:
```tsx
const FIELD_MAPPING = {
  // UI Label → Backend Key
  "Book Freshness": "max_book_staleness_ms",
  "Max Spread": "max_spread_bps",
  "Min Liquidity": "min_depth_usdc_at_50bps",
  "Max Price Impact": "max_impact_bps",
  "Wait After Finish": "min_seconds_since_finished",
  "Max Time After Finish": "max_seconds_since_finished",
  "Order Size": "order_usdc",
  "Smart Sizing": "capacity_sizing_enabled",
  "Order Type": "order_mode",
  "Order Timeout": "ttl_ms",
  "Price Drift Limit": "drift_bps_limit",
  "Price Step": "tick_size",
  "Improve Price By": "improve_ticks",
};
```

**Tests**:
- ✅ Validaciones se actualizan en tiempo real
- ✅ Warnings aparecen cuando corresponde
- ✅ Form guarda correctamente
- ✅ Summary refleja configuración
- ✅ Tooltips se muestran correctamente
- ✅ Mapeo UI → Backend funciona

**Criterios de Aceptación**:
- [ ] Form completo en 2-3 minutos
- [ ] Sin scroll infinito
- [ ] Validaciones claras y útiles
- [ ] Summary actualiza en tiempo real
- [ ] **Todos los campos tienen nombres simples (no técnicos)**
- [ ] **Todos los campos tienen tooltips/modales explicativos**
- [ ] **Usuario no técnico puede entender qué hace cada campo**

---

#### FE-PR5: Live Terminal

**Entregables**:
1. Topbar con status, capital, exposure, acciones
2. Main split: tabla (70%) + panel derecho (30%)
3. Markets/Events table con métricas de orderbook
4. Panel derecho: health + precheck failures + recent orders
5. Play/Pause/Stop wiring con endpoints

**Archivos a Modificar**:
1. `frontend/app/strategies/[id]/live/page.tsx`
2. Nuevo: `frontend/components/ui/kpi-bar.tsx`
3. Nuevo: `frontend/components/ui/status-pill.tsx`
4. Nuevo: `frontend/components/ui/metric-chip.tsx`

**Estructura**:
```tsx
<div className="flex flex-col h-full">
  {/* Topbar compacto */}
  <div className="flex items-center justify-between px-3 py-2 border-b bg-card">
    <div className="flex items-center gap-3">
      <StatusPill status={strategy.is_active ? 'active' : 'paused'} />
      <span className="text-[13px]">Capital: ${capitalUsed}/${maxCapital}</span>
      <span className="text-[13px]">Exposure: ${exposure}</span>
    </div>
    <div className="flex items-center gap-2">
      <Button size="compact" onClick={handleSimulate}>Simulate</Button>
      <Button size="compact" onClick={handlePlay}>Play</Button>
      <Button size="compact" onClick={handlePause}>Pause</Button>
      <Button size="compact-sm" variant="destructive" onClick={handleStop}>Stop</Button>
    </div>
  </div>
  
  {/* Main split */}
  <div className="flex flex-1 overflow-hidden">
    {/* Tabla izquierda (70%) */}
    <div className="flex-[0.7] overflow-auto border-r">
      <Table>
        <TableHeader className="sticky top-0 bg-card z-10">
          {/* Columns */}
        </TableHeader>
        <TableBody>
          {/* Rows con h-9 */}
        </TableBody>
      </Table>
    </div>
    
    {/* Panel derecho (30%) */}
    <div className="flex-[0.3] overflow-auto p-3 space-y-2">
      <Panel>
        <CardHeader className="p-3 pb-2">
          <CardTitle className="text-sm">Orderbook Health</CardTitle>
        </CardHeader>
        {/* Health metrics */}
      </Panel>
    </div>
  </div>
</div>
```

**Tests**:
- ✅ Tabla actualiza en tiempo real
- ✅ Métricas se colorean correctamente
- ✅ Acciones funcionan (play/pause/stop)
- ✅ Panel derecho muestra datos correctos

**Criterios de Aceptación**:
- [ ] Dashboard operacional completo
- [ ] Métricas en tiempo real
- [ ] Acciones primarias siempre visibles
- [ ] Performance: updates sin lag

---

#### FE-PR6: Simulation UI

**Entregables**:
1. Modal/página de simulación
2. Inputs compactos (duration, capital, fill_mode)
3. Endpoint call a `/strategies/{id}/simulate`
4. Render KPI row
5. Tabs: Summary, Fills, Markets ranking

**Archivos a Modificar**:
1. Nuevo: `frontend/app/strategies/[id]/simulate/page.tsx` o modal
2. Integración con endpoint `/strategies/{id}/simulate`

**Estructura**:
```tsx
<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <DialogContent className="max-w-4xl">
    <DialogHeader>
      <DialogTitle>Simulate Strategy</DialogTitle>
    </DialogHeader>
    <div className="space-y-3">
      <InlineForm label="Duration" input={<Select><SelectItem>15 min</SelectItem>...</Select>} />
      <InlineForm label="Initial Capital" input={<Input type="number" />} />
      <InlineForm label="Fill Mode" input={<Select><SelectItem>Conservative</SelectItem>...</Select>} />
      <Button size="compact" onClick={handleSimulate}>Run Simulation</Button>
    </div>
    {results && (
      <>
        <KPIBar kpis={[...]} />
        <Tabs>
          <TabsList>
            <TabsTrigger>Summary</TabsTrigger>
            <TabsTrigger>Fills</TabsTrigger>
            <TabsTrigger>Markets</TabsTrigger>
          </TabsList>
        </Tabs>
      </>
    )}
  </DialogContent>
</Dialog>
```

**Tests**:
- ✅ Modal abre y cierra correctamente
- ✅ Simulación ejecuta y muestra resultados
- ✅ Tabs funcionan
- ✅ Tabla de fills renderiza correctamente

**Criterios de Aceptación**:
- [ ] Usuario puede simular strategy
- [ ] Resultados se muestran claramente
- [ ] KPIs son legibles
- [ ] Fills table es útil

---

#### FE-PR7: Componentes Nuevos Compactos

**Entregables**:
1. `DenseTable` con virtualización
2. `KPIBar`
3. `StatusPill`
4. `MetricChip` (con tooltip)
5. `InlineForm` (con tooltip)
6. `ConfirmModal`
7. `SidePanel`
8. **`InfoTooltip`** (nuevo, para explicaciones)

**Archivos Nuevos**:
1. `frontend/components/ui/dense-table.tsx`
2. `frontend/components/ui/kpi-bar.tsx`
3. `frontend/components/ui/status-pill.tsx`
4. `frontend/components/ui/metric-chip.tsx` (con prop `tooltip`)
5. `frontend/components/ui/inline-form.tsx` (con prop `tooltip`)
6. `frontend/components/ui/side-panel.tsx`
7. `frontend/components/ui/info-tooltip.tsx` (nuevo)

**Ver sección "Componentes Core" más abajo para implementación detallada**

**Principio de Nombres Simples**:
- ✅ **UI**: "Book Freshness", "Max Spread", "Min Liquidity"
- ❌ **UI**: "max_book_staleness_ms", "max_spread_bps", "min_depth_usdc_at_50bps"
- ✅ **Backend**: Mantener nombres técnicos (`max_book_staleness_ms`)
- ✅ **Mapeo**: Función que convierte UI labels → backend keys

---

#### FE-PR8: Eliminar "Colorines" (Paleta Monocromática)

**Entregables**:
1. Paleta monocromática en `globals.css`
2. Charts en escala de grises
3. Revisar y reemplazar colores hardcoded

**Archivos a Modificar**:
1. `frontend/app/globals.css` (colores charts y status)
2. Revisar componentes con `bg-*-500` hardcoded:
   - `frontend/components/Sidebar.tsx`
   - `frontend/components/markets/MarketCard.tsx`
   - Todos los componentes con colores vibrantes

**Cambios Específicos**:
```css
/* globals.css - Paleta monocromática */
:root {
  --primary: 217 20% 50%;        /* Gris azulado neutro */
  --chart-1: 0 0% 40%;           /* Gris oscuro */
  --chart-2: 0 0% 50%;           /* Gris medio */
  --chart-3: 0 0% 60%;           /* Gris claro */
  --chart-4: 0 0% 70%;           /* Gris más claro */
  --chart-5: 0 0% 80%;           /* Gris muy claro */
  --success: 142 20% 40%;        /* Verde apagado */
  --warning: 45 20% 40%;         /* Amarillo apagado */
  --error: 0 20% 40%;            /* Rojo apagado */
}
```

**Checklist de Verificación Visual**:
- [ ] No hay colores vibrantes (verde brillante, rojo brillante, etc.)
- [ ] Charts usan escala de grises
- [ ] Status colors son sutiles (apagados)
- [ ] Paleta general es monocromática

---

### Detalles "Premium"

**3 detalles que cambian la percepción**:

1. **Skeleton Loading**:
   - En tablas: mostrar skeleton rows en lugar de spinner
   - En cards: skeleton del contenido
   - Ejemplo: `<Skeleton className="h-9 w-full" />` para table rows

2. **Empty States Útiles**:
   - "No markets selected → go to Universe"
   - "No strategies active → create one"
   - Con acciones directas (botones)

3. **Micro-interacciones**:
   - Hover sutil: `transition-colors duration-150`
   - Copy feedback: toast minimalista (1-2s)
   - Loading states: skeleton en lugar de spinners
   - Transiciones suaves: `transition-all duration-200`

---

## Contratos de Datos

### OrderbookLevel

```python
class OrderbookLevel(BaseModel):
    price: float      # 0.01 - 0.99
    size: float       # shares (CLOB size)
```

### OrderbookState (State Cache)

**Key**: `pm.orderbook.{asset_id}`

```python
class OrderbookState(BaseModel):
    asset_id: str
    ts_ms: int
    
    # BBO
    best_bid_price: float | None
    best_bid_size: float | None
    best_ask_price: float | None
    best_ask_size: float | None
    
    # Spread/Mid
    spread_bps: float | None
    mid: float | None
    
    # Top N levels
    bids: list[OrderbookLevel]  # top 20, desc price
    asks: list[OrderbookLevel]  # top 20, asc price
    
    # Depth metrics (BUY side only - asks)
    depth_usdc_at_25bps: float  # ⚠️ BUY side only
    depth_usdc_at_50bps: float  # ⚠️ BUY side only
    depth_usdc_at_100bps: float  # ⚠️ BUY side only
    
    # Impact metrics (BUY side only - asks)
    impact_bps_for_usdc_100: float  # ⚠️ BUY side only
    impact_bps_for_usdc_500: float  # ⚠️ BUY side only
    impact_bps_for_usdc_1000: float  # ⚠️ BUY side only
    impact_bps_for_usdc_5000: float  # ⚠️ BUY side only
    
    # Competition proxies
    concentration_top3_pct: float  # ⚠️ BUY side only (asks)
    update_rate_hz: float
    replenishment_score: float
    
    # Health
    staleness_ms: int
    integrity: dict  # {resync_count, last_snapshot_ts_ms, parse_errors}
```

**⚠️ NOTA IMPORTANTE**: Todos los cálculos de depth/impact/concentration son **BUY-side only** (asks). Si un día operas SELL/NO, necesitarás campos separados o funciones `_sell()`.

### Payload WS Book (Input)

```python
{
  "event_type": "book",
  "asset_id": "65818619657568813474341868652308942079804919287380422192892211131408793125422",
  "market": "0xbd31dc8a20211944f6b70f31557f1001557b59905b7738480ca09bd4532f84af",
  "bids": [
    {"price": ".48", "size": "30"},  # ⚠️ STRINGS
    {"price": ".49", "size": "20"}
  ],
  "asks": [
    {"price": ".52", "size": "25"},  # ⚠️ STRINGS
    {"price": ".53", "size": "60"}
  ],
  "timestamp": "123456789000",  # ⚠️ STRING (ms)
  "hash": "0x0...."
}
```

### Parser Exacto

```python
def parse_ws_book_payload(book_msg: Dict[str, Any]) -> tuple[list[OrderbookLevel], list[OrderbookLevel], int]:
    """Parse WS book payload to OrderbookLevel lists and timestamp."""
    bids_raw = book_msg.get("bids", [])
    asks_raw = book_msg.get("asks", [])
    timestamp_str = book_msg.get("timestamp", "0")
    
    bids = []
    for level in bids_raw:
        try:
            price = float(level["price"])  # ".48" -> 0.48
            size = float(level["size"])    # "30" -> 30.0
            if price > 0 and size >= 0:
                bids.append(OrderbookLevel(price=price, size=size))
        except (ValueError, KeyError):
            continue
    
    asks = []
    for level in asks_raw:
        try:
            price = float(level["price"])
            size = float(level["size"])
            if price > 0 and size >= 0:
                asks.append(OrderbookLevel(price=price, size=size))
        except (ValueError, KeyError):
            continue
    
    ts_ms = int(timestamp_str)
    
    # Sort: bids desc, asks asc
    bids.sort(key=lambda x: x.price, reverse=True)
    asks.sort(key=lambda x: x.price)
    
    # Truncate to top 20
    bids = bids[:20]
    asks = asks[:20]
    
    return bids, asks, ts_ms
```

---

## Tests Unitarios por Fase

### PHASE 1 Tests

```python
# tests/unit/test_orderbook_parser.py
def test_parse_ws_book_payload_strings():
    """Test parsing WS payload with string prices/sizes."""
    payload = {
        "event_type": "book",
        "asset_id": "123",
        "market": "0xabc",
        "bids": [{"price": ".48", "size": "30"}],
        "asks": [{"price": ".52", "size": "25"}],
        "timestamp": "123456789000"
    }
    bids, asks, ts_ms = parse_ws_book_payload(payload)
    assert len(bids) == 1
    assert bids[0].price == 0.48
    assert bids[0].size == 30.0
    assert ts_ms == 123456789000

def test_orderbook_book_sorting():
    """Test OrderbookBook sorts correctly."""
    book = OrderbookBook(top_n=20)
    bids = [
        OrderbookLevel(price=0.50, size=10),
        OrderbookLevel(price=0.48, size=20),
        OrderbookLevel(price=0.49, size=15)
    ]
    asks = [
        OrderbookLevel(price=0.52, size=25),
        OrderbookLevel(price=0.54, size=30),
        OrderbookLevel(price=0.53, size=20)
    ]
    book.update_from_snapshot(bids, asks, ts_ms=1000)
    assert book.compute_bbo()[0] == 0.50  # best bid (highest)
    assert book.compute_bbo()[1] == 0.52  # best ask (lowest)

def test_orderbook_book_truncation():
    """Test OrderbookBook truncates to top_n."""
    book = OrderbookBook(top_n=3)
    bids = [OrderbookLevel(price=0.50 - i*0.01, size=10) for i in range(10)]
    asks = [OrderbookLevel(price=0.52 + i*0.01, size=10) for i in range(10)]
    book.update_from_snapshot(bids, asks, ts_ms=1000)
    assert len(book.bids) == 3
    assert len(book.asks) == 3

def test_features_depth_at_bps():
    """Test depth calculation at X bps."""
    asks = [
        OrderbookLevel(price=0.50, size=100),  # 50 USDC
        OrderbookLevel(price=0.51, size=100),  # 51 USDC
        OrderbookLevel(price=0.52, size=100),  # 52 USDC
    ]
    best_ask = 0.50
    depth_50bps = compute_depth_usdc_at_bps_buy(asks, best_ask, 50)
    # 50bps = 0.5% = 0.50 * 1.005 = 0.5025
    # Only first level (0.50) is within 50bps (0.51 > 0.5025)
    assert depth_50bps == 50.0  # Solo el primer nivel
    
    # Test con 300bps para incluir 0.51
    depth_300bps = compute_depth_usdc_at_bps_buy(asks, best_ask, 300)
    # 300bps = 3% = 0.50 * 1.03 = 0.515
    # Incluye 0.50 y 0.51 (0.52 > 0.515)
    assert depth_300bps == 101.0  # 50 + 51

def test_features_impact_bps():
    """Test impact calculation for USDC size."""
    asks = [
        OrderbookLevel(price=0.50, size=100),  # 50 USDC
        OrderbookLevel(price=0.51, size=100),  # 51 USDC
    ]
    best_ask = 0.50
    impact = compute_impact_bps_for_usdc_buy(asks, best_ask, 75.0)
    # Spend 75 USDC: 50 at 0.50 (100 shares) + 25 at 0.51 (49.02 shares)
    # Total shares = 149.02
    # Avg price = 75 / 149.02 = 0.5034
    # Impact = (0.5034 - 0.50) / 0.50 * 10000 = 68 bps
    assert abs(impact - 68) < 2  # Tolerancia más amplia por rounding

def test_orchestrator_ref_count():
    """Test orchestrator ref-count lifecycle con owners set."""
    orchestrator = OrderbookOrchestrator()
    asset_id = "123"
    
    # First subscribe
    orchestrator.subscribe(asset_id, "strategy_1")
    assert asset_id in orchestrator.owners
    assert "strategy_1" in orchestrator.owners[asset_id]
    assert orchestrator.ref_count[asset_id] == 1
    assert len(orchestrator.owners[asset_id]) == orchestrator.ref_count[asset_id]
    
    # Double-subscribe same owner (idempotente)
    orchestrator.subscribe(asset_id, "strategy_1")
    assert orchestrator.ref_count[asset_id] == 1  # No cambia
    
    # Second subscribe (different owner)
    orchestrator.subscribe(asset_id, "strategy_2")
    assert orchestrator.ref_count[asset_id] == 2
    assert len(orchestrator.owners[asset_id]) == 2
    
    # First unsubscribe
    orchestrator.unsubscribe(asset_id, "strategy_1")
    assert orchestrator.ref_count[asset_id] == 1
    assert "strategy_1" not in orchestrator.owners[asset_id]
    assert "strategy_2" in orchestrator.owners[asset_id]
    
    # Second unsubscribe
    orchestrator.unsubscribe(asset_id, "strategy_2")
    assert orchestrator.ref_count[asset_id] == 0
    assert asset_id not in orchestrator.owners
    
    # Unsubscribe sin subscribe previo (debe manejar gracefully)
    orchestrator.unsubscribe(asset_id, "strategy_3")  # No debe crashear
```

### PHASE 2 Tests

```python
# tests/unit/test_orderbook_persistence.py
def test_batch_insert():
    """Test batch insert of features."""
    features = [create_test_feature() for _ in range(100)]
    persistence.batch_insert(features)
    # Verify all inserted
    assert db.query(MarketMicroFeature).count() == 100

def test_time_based_flush():
    """Test time-based flush of buffer."""
    # Add features slowly
    for i in range(5):
        persistence.add_feature(create_test_feature())
        time.sleep(0.1)
    # Wait for flush (10s)
    time.sleep(11)
    # Verify flushed
    assert persistence.buffer_size() == 0
```

### PHASE 4 Tests

```python
# tests/unit/test_universe_resolution.py
def test_resolve_universe_to_asset_ids():
    """Test universe resolution to asset_ids."""
    strategy = create_strategy()
    universe = StrategyUniverse(
        strategy_id=strategy.id,
        categories=["sports"],
        markets=[market1.id, market2.id]
    )
    asset_ids = resolve_universe_to_asset_ids(strategy.id)
    # Should include YES tokens from market1 and market2
    assert len(asset_ids) > 0
    assert all(isinstance(aid, str) for aid in asset_ids)

def test_universe_deny_list():
    """Test deny list filtering."""
    universe = StrategyUniverse(
        strategy_id=strategy.id,
        markets=[market1.id, market2.id],
        deny_markets=[market2.id]
    )
    asset_ids = resolve_universe_to_asset_ids(strategy.id)
    # Should NOT include market2 tokens
    assert market2_yes_token not in asset_ids
```

### PHASE 5 Tests

```python
# tests/unit/test_capacity_sizing.py
def test_capacity_sizing_by_depth():
    """Test size capping by depth."""
    orderbook_state = OrderbookState(
        depth_usdc_at_50bps=2000.0,
        impact_bps_for_usdc_1000=30.0
    )
    target_usdc = 5000.0
    max_impact_bps = 50.0
    
    final_usdc = calculate_capacity_aware_size(
        target_usdc, orderbook_state, max_impact_bps
    )
    # Should be capped by depth (2000)
    assert final_usdc == 2000.0

def test_capacity_sizing_by_impact():
    """Test size capping by impact."""
    orderbook_state = OrderbookState(
        depth_usdc_at_50bps=10000.0,
        impact_bps_for_usdc_1000=60.0,  # > max_impact
        impact_bps_for_usdc_500=40.0
    )
    target_usdc = 5000.0
    max_impact_bps = 50.0
    
    final_usdc = calculate_capacity_aware_size(
        target_usdc, orderbook_state, max_impact_bps
    )
    # Should be capped by impact (500)
    assert final_usdc == 500.0
```

### PHASE 6 Tests

```python
# tests/unit/test_execution_prechecks.py
def test_precheck_staleness():
    """Test precheck blocks stale books."""
    plan = ExecutionPlan(
        asset_id="123",
        max_book_staleness_ms=2000
    )
    orderbook_state = OrderbookState(
        asset_id="123",
        staleness_ms=5000  # Too stale
    )
    result = precheck_execution(plan, orderbook_state)
    assert result["status"] == "FAIL_PRECHECK"
    assert result["reason"] == "stale_book"

def test_precheck_drift():
    """Test precheck blocks high drift."""
    plan = ExecutionPlan(
        asset_id="123",
        order_mode="IOC",
        expected_best_ask=0.50,
        drift_bps_limit=20
    )
    orderbook_state = OrderbookState(
        asset_id="123",
        best_ask_price=0.52  # 4% drift = 400 bps
    )
    result = precheck_execution(plan, orderbook_state)
    assert result["status"] == "FAIL_PRECHECK"
    assert result["reason"] == "drift_too_high"
```

### PHASE 7 Tests

```python
# tests/unit/test_simulation_engine.py
def test_fill_model_ioc_conservative():
    """Test IOC fill model (conservative mode - solo best level)."""
    plan = ExecutionPlan(
        order_mode="IOC",
        side="BUY",
        price=0.52,
        shares=100
    )
    orderbook_state = OrderbookState(
        best_ask_price=0.50,
        best_ask_size=50
    )
    fill = apply_fill_model_ioc(plan, orderbook_state, mode="conservative")
    assert fill is not None
    assert fill.fill_price == 0.50
    assert fill.fill_shares == 50  # Limited by best_ask_size

def test_fill_model_ioc_realistic():
    """Test IOC fill model (realistic mode - barre topN)."""
    plan = ExecutionPlan(
        order_mode="IOC",
        side="BUY",
        price=0.52,
        final_usdc=75.0
    )
    orderbook_state = OrderbookState(
        best_ask_price=0.50,
        best_ask_size=50,
        asks=[
            OrderbookLevel(price=0.50, size=100),  # 50 USDC
            OrderbookLevel(price=0.51, size=100),  # 51 USDC
        ]
    )
    fill = apply_fill_model_ioc(plan, orderbook_state, mode="realistic")
    assert fill is not None
    # Debe barrer: 50 USDC a 0.50 + 25 USDC a 0.51
    assert fill.fill_shares > 0
    assert fill.fill_price >= 0.50
    assert fill.fill_price <= 0.51

def test_fill_model_post_only():
    """Test POST_ONLY fill model."""
    plan = ExecutionPlan(
        order_mode="POST_ONLY",
        side="BUY",
        price=0.51,
        ttl_ms=5000
    )
    # Simulate stream: best_ask drops to 0.51
    orderbook_state = OrderbookState(best_ask_price=0.51)
    fill = apply_fill_model_post_only(plan, orderbook_state, stream=[orderbook_state])
    assert fill is not None
    assert fill.fill_price == 0.51
```

---

## Criterios de Aceptación Global

### Funcionalidad

- [ ] Orderbook Engine mantiene top-20 levels por asset_id
- [ ] Features se calculan correctamente (depth, impact, concentration)
- [ ] State Cache contiene `pm.orderbook.{asset_id}` con staleness
- [ ] Universe por strategy funciona (subscribe/unsubscribe)
- [ ] Strategy Near-Resolution usa OrderbookState (no last_price)
- [ ] Sizing es capacity-aware (capped por depth/impact)
- [ ] Execution prechecks bloquean órdenes inválidas
- [ ] Simulation produce reportes de PnL

### Performance

- [ ] Orderbook updates no bloquean loop principal
- [ ] State Cache TTL es apropiado (120s)
- [ ] Persistence no bloquea (batch insert)
- [ ] WS suscripciones se gestionan eficientemente (ref-count)

### Observabilidad

- [ ] Métricas: `orderbook_staleness_ms_p95`, `plans_failed_precheck_total`
- [ ] Trazas incluyen: `asset_id`, `best_bid/ask`, `spread_bps`, `depth_50`, `impact_bps`
- [ ] Alertas: staleness > 5s, WS disconnect loop

### Tests

- [ ] Cobertura > 80% en módulos nuevos
- [ ] Tests unitarios pasan
- [ ] Tests de integración pasan
- [ ] Acceptance tests pasan

### Frontend

- [ ] UI es compacta y densa (tipo trading terminal)
- [ ] Todas las acciones son keyboard-friendly
- [ ] Performance: tablas con 1000+ rows sin lag
- [ ] Responsive en desktop (mínimo 1280px)
- [ ] Design tokens aplicados consistentemente
- [ ] Componentes base reutilizables
- [ ] Skeleton loading en lugar de spinners
- [ ] Empty states útiles con acciones

---

## Instrucción Final para Cursor

**Copiar/Pegar este prompt completo:**

```
Implementar Orderbook Engine shared para Polymarket usando WS MARKET existente. El payload book trae bids/asks como lista de dicts con price y size STRINGS (ej ".48", "30") y timestamp string ms. Parsear y mantener top-20 por asset_id, compute BBO/spread/mid, depth_usdc_at_25/50/100bps (BUY side), impact_bps para USDC sizes [100,500,1000,5000] (BUY), concentration_top3_pct, update_rate_hz y replenishment_score. Publicar a State Cache como pm.orderbook.{asset_id} con staleness_ms. Persistir micro-features en DB. Implementar Universe por strategy para seleccionar markets/categories/tags y suscribirse a asset_ids (clobTokenIds) con ref-count. Actualizar estrategia liquidity_near_end para usar OrderbookState en Decision Graph (no last_price), con knobs de staleness/spread/depth/impact y sizing capacity-aware, y Execution prechecks drift/impact/freshness/ttl. Añadir modo Simulate (paper-forward) con SimExecutionEngine y reporte PnL basado en fills modelados por book.

Frontend: Implementar UI compacta tipo trading terminal con diseño "unicornio" (alta densidad informativa, sin padding inútil). Design tokens: text-[13px], h-8 inputs/buttons, px-3 py-2 spacing, gap-2 grids. Páginas: /markets (catálogo con tabla densa), /strategies/new|edit (builder 3 columnas), /strategies/{id}/live (terminal operacional), /strategies/{id}/simulate (simulación). Componentes: DenseTable (virtualized), KPIBar, StatusPill, MetricChip, InlineForm, ConfirmModal. Keyboard-friendly: search con /, navegar con flechas. Skeleton loading, empty states útiles, micro-interacciones sutiles.

Seguir el plan detallado en docs/implementation/orderbook-engine-implementation-plan.md fase por fase (PHASE 1-8), con tests unitarios por cada fase y criterios de aceptación claros.
```

---

## State Cache API

### Ubicación y Uso

**Archivo**: `backend/app/core/strategy_engine/state_cache_service.py`

**Clase**: `StateCacheService`

### API Principal

```python
# Obtener instancia (desde GraphRuntime context)
state_cache: StateCacheService = context.state_cache

# Escribir (Support Graphs)
await state_cache.set(
    cache_key="pm.orderbook.{asset_id}",
    value=orderbook_state_dict,  # Se serializa a JSONB automáticamente
    ttl_seconds=120,
    strategy_id=strategy_id,  # Opcional
    event_id=event_id  # Opcional
)

# Leer (Decision Graph)
orderbook_state_dict = await state_cache.get("pm.orderbook.{asset_id}")

# Leer múltiples (patrón)
all_orderbooks = await state_cache.get_many("pm.orderbook.*")
```

### Namespacing

**Convención de claves**:
- `pm.orderbook.{asset_id}` - Orderbook state
- `event.{event_id}.market_state` - Market state
- `event.{event_id}.external_confirmation` - External confirmation
- `strategy.{strategy_id}.risk_state` - Risk state

### Serialización

- **Valores**: Cualquier objeto serializable a JSON
- **DB**: Almacenado como `JSONB` en PostgreSQL
- **Memoria**: Objeto Python nativo (deserializado)
- **TTL**: Se respeta en memoria y DB

### Ejemplo de Uso en OrderbookPublisher

```python
class OrderbookPublisher:
    def __init__(self, state_cache_service: StateCacheService):
        self.state_cache = state_cache_service
    
    async def publish(self, asset_id: str, orderbook_state: OrderbookState):
        cache_key = f"pm.orderbook.{asset_id}"
        await self.state_cache.set(
            cache_key=cache_key,
            value=orderbook_state.dict(),  # Pydantic model → dict
            ttl_seconds=120
        )
```

---

## Notas de Implementación

### Parser WS Book (Crítico)

El payload viene con **strings**, no floats:
- `"price": ".48"` → `float(".48")` = `0.48`
- `"size": "30"` → `float("30")` = `30.0`
- `"timestamp": "123456789000"` → `int("123456789000")` = `123456789000`

### Depth Calculation (BUY Side Only)

⚠️ **IMPORTANTE**: Funciones `depth_usdc_at_Xbps_buy()` son **BUY-side only** (asks).

Para Near-Resolution (típicamente BUY):
- Referencia: `best_ask_price`
- Límite: `best_ask * (1 + Xbps/10000)`
- Depth: Suma de `size * price` para asks con `price <= límite`

**Nota**: Si un día operas SELL/NO, necesitarás funciones `_sell()` separadas con bids.

### Impact Calculation (BUY Side Only)

⚠️ **IMPORTANTE**: Función `impact_bps_for_usdc_buy()` es **BUY-side only** (asks).

Simular barrido de asks:
1. Empezar con `best_ask`
2. Consumir niveles hasta gastar B USDC
3. Calcular `avg_price = total_usdc / total_shares`
4. `impact_bps = (avg_price - best_ask) / best_ask * 10000`

**Nota**: Si no hay suficiente depth para gastar B, retornar `inf` o valor muy alto (1e9).

### Ref-Count Lifecycle (Mejorado)

**Estructura interna**:
```python
owners: Dict[str, Set[str]] = {}  # asset_id -> set of owner_keys
ref_count: Dict[str, int] = {}    # asset_id -> count (derivado)
```

**Reglas**:
- `ref_count[asset_id] = len(owners[asset_id])` (siempre derivado, nunca manual)
- `subscribe(asset_id, owner)` → añadir a `owners[asset_id]` (idempotente)
- `unsubscribe(asset_id, owner)` → remover de `owners[asset_id]` (validar existencia)
- Si `ref_count` pasa 0→1: suscribir WS
- Si `ref_count` pasa 1→0: desuscribir WS
- **Nunca dejar ref_count negativo** (validar antes de decrementar)
- **Double-subscribe mismo owner**: ignorar (idempotente)

### Compatibilidad Temporal

Durante transición:
- Mantener `MarketState.best_bid/best_ask` poblado desde `OrderbookState`
- No romper código existente que lee `MarketState`
- Gradualmente migrar a `OrderbookState` directo

### Tick Size / Price Rounding

**Función helper**:
```python
def round_price_to_tick(price: float, tick_size: float) -> float:
    """Redondea precio al tick más cercano."""
    return round(price / tick_size) * tick_size
```

**Uso**:
- Aplicar después de calcular precio objetivo
- Default `tick_size=0.001` si no está disponible en market data
- Refinar cuando tengas `tick_size` real desde Polymarket

### Time Since Finished (vs max_time_to_resolution)

**Cambio importante**:
- ❌ `max_time_to_resolution_minutes` (no se puede conocer bien)
- ✅ `min_seconds_since_finished` (buffer anti-falsos)
- ✅ `max_seconds_since_finished` (evitar liquidez muerta)

**Cálculo**:
```python
time_since_finished = (now - event.finished_at).total_seconds()
if time_since_finished < min_seconds_since_finished:
    return False  # Muy reciente, esperar confirmación
if time_since_finished > max_seconds_since_finished:
    return False  # Muy tarde, liquidez muerta
```

### Simulación: 2 Modos de Fill

**Modo conservador** (default):
- Solo best level
- Más seguro, menos realista

**Modo realista**:
- Barre topN asks (igual que impact sim)
- Más vendible, se parece más a producción
- Configurable en UI: "Fill model: Conservative / Realistic"

---

## Próximos Pasos

1. **Revisar plan con equipo**
2. **Priorizar fases** (PHASE 1 es crítica)
3. **Asignar recursos**
4. **Ejecutar fase por fase**
5. **Validar criterios de aceptación**
6. **Deploy incremental**

---

**Fin del Plan**

