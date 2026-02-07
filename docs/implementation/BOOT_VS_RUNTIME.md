# Boot vs Runtime: ciclo de vida del backend (política v2)

**Política institucional v2.0**: No existe CLOB global ni system wallet. Cualquier operación/lectura que requiera CLOB auth exige `user_id` + wallet en BD. FAIL CLOSED.

Este documento describe qué se inicializa en **arranque (boot)** y qué se hace **en runtime (lazy / on-demand)** para cumplir esa política.

---

## 1. Inventario de arranque

### 1.1 Eventos FastAPI (lifespan)

| Paso | Archivo | Acción |
|------|---------|--------|
| 1 | `app/main.py` `lifespan()` | `config_service.load_from_db()` |
| 2 | `app/main.py` | `config_service.start_hot_reload()` |
| 3 | `app/main.py` | `state.risk_config = config_service.get_risk_config()` |
| 4 | `app/main.py` | `state.load_from_db(db)` |
| 5 | `app/main.py` | `metrics_service.start()` |
| 6 | `app/main.py` | Redis ping (si `CACHE_PROVIDER=redis`), `main_loop()`, `cache_cleanup_loop()`, `equity_snapshot_service.start_periodic_snapshots()`, `strategy_engine.initialize(db, ...)`, `strategy_engine.control_loop.start(db)` |
| 7 | `app/main.py` | Startup completado |

### 1.2 Singletons / instancias creadas al import o al primer uso

| Dónde | Qué | CLOB/WS USER |
|-------|-----|----------------|
| `app/core/config_service.py` | `config_service` (singleton) | No; solo config/DB |
| `app/core/state.py` | `state` (StateManager) | No; solo estructuras en memoria |
| `app/core/execution/polymarket_websocket.py` | `get_websocket_manager()` → `PolymarketWebSocketManager()` | No; el manager no abre USER hasta `connect_user_channel()` (solo desde API con user+wallet) |
| `app/core/execution/polymarket_client_wrapper.py` | `get_polymarket_client()` | Lanza; no hay cliente global. Solo `get_polymarket_client_for_user(user_id)` crea cliente (runtime) |
| `app/core/equity_snapshot_service.py` | `equity_snapshot_service` | No en boot; `take_snapshot()` solo llama CLOB si `_snapshot_user_id` está definido (nunca en boot) |
| `app/main.py` (imports) | `scanner`, `event_mapping_layer`, `event_watch_coordinator`, `event_engine`, `risk_engine`, `strategy_engine` o `strategy`, `execution`, `metrics`, `runtime_supervisor`, `event_store`, `live_control_store` | No CLOB en construcción; Execution._setup_websocket() no abre USER |

### 1.3 Módulos que al importar crean clientes/threads

| Módulo | Comportamiento |
|--------|----------------|
| `app.core.execution.execution` | `Execution()` llama `_setup_websocket()`: obtiene `get_websocket_manager()` pero no llama `connect_user_channel()`; deja `_use_websocket = False`. |
| `app.core.strategy_engine.strategy_engine` | Solo se instancia si `use_graph_strategies`; no crea CLOB. |
| `app.core.orderbook.service` | `OrderbookService` usa `get_websocket_manager()` y conecta MARKET solo on-demand al suscribir asset_id (no en boot). |
| `app.core.strategy.strategy` | Strategy (legacy) configura callbacks del WS manager; no abre USER. |

### 1.4 Loops y tareas en background (iniciados en lifespan)

| Tarea | Archivo | Qué hace en el primer tick / ciclo |
|-------|---------|------------------------------------|
| `main_loop()` | `app/main.py` | Tick de execution, risk, metrics, runtime_supervisor; execution.tick() solo usa CLOB vía `get_polymarket_client_for_user(execution_user_id)` si hay intent con user_id; si no hay wallet → intent FAILED. |
| `cache_cleanup_loop()` | `app/main.py` | Limpieza de caches; no CLOB. |
| `equity_snapshot_service._snapshot_loop()` | `app/core/equity_snapshot_service.py` | `take_snapshot()`: sin `_snapshot_user_id` no llama CLOB (base_equity=0). |
| `strategy_engine.control_loop.start(db, app=app)` | `app/core/strategy_engine/control_loop.py` | No carga estrategias al arranque; en cada tick solo hace refresh si `app.state.control_loop_refresh_requested` (lo marca la API cuando un usuario logeado lista o activa/desactiva estrategias). La ejecución real usa `execution_user_id` + wallet (runtime). |

### 1.5 WebSocket USER

- **Inicialización en startup**: no. `connect_user_channel()` solo se invoca desde la API cuando hay user_id + wallet configurada.
- **Dónde se abre**: `app/core/execution/polymarket_websocket.py` `PolymarketWebSocketManager.connect_user_channel()`; llamada desde `app/api/polymarket.py` (o similar) al suscribir canal USER, tras comprobar wallet.

---

## 2. Clasificación

### A) Safe-at-boot (infra, DB, Redis, caches públicos, metadata)

- Config load from DB y hot reload (`config_service`)
- State load from DB (`state.load_from_db`) — solo modelos/estado en memoria
- Risk config en state
- Métricas (`metrics_service.start()`)
- Redis ping y flag `cache_redis_available`
- Creación de tareas: `main_loop`, `cache_cleanup_loop`, `equity_snapshot_service.start_periodic_snapshots()`, `strategy_engine.initialize()`, `control_loop.start(db)`
- `strategy_engine.initialize()`: StateCacheService, GraphRuntime, ControlLoop, TriggerEvaluator — sin CLOB
- Estrategias activas: no se cargan en boot; se cargan en el primer refresh cuando un usuario logeado ha pedido listado o activado/desactivado (flag `control_loop_refresh_requested` en app.state)
- Singleton `get_websocket_manager()`: crea solo el gestor; no abre canal USER
- Caches públicos (Gamma, discovery, etc.): se usan en runtime; no exigen CLOB en boot

### B) Must-be-runtime (lazy / on-demand)

- Cualquier llamada que use **CLOB auth**: balance, órdenes, trades, place, cancel.
- **WS USER**: solo al invocar `connect_user_channel()` con credenciales de un user (tras comprobar wallet en BD).
- **Cliente CLOB**: solo vía `get_polymarket_client_for_user(user_id)` cuando hay wallet para ese user.
- **Equity snapshot con balance**: solo si se configura `_snapshot_user_id` (opcional; no en boot).
- **Execution engine**: en cada tick, intents con `execution_user_id` resuelven wallet; si falta → intent en estado FAILED + log, sin crash.
- **Estrategias “enabled”**: el control loop puede arrancar y listar estrategias activas; la ejecución de trading se hace cuando hay execution_user_id + wallet; si no hay wallet → MISCONFIGURED/FAILED (FAIL CLOSED).

---

## 3. Resumen de garantías

- El backend **puede arrancar sin** `PRIVATE_KEY`/`FUNDER` en env y sin wallets en BD.
- No existe `get_polymarket_client()` global; solo `get_polymarket_client_for_user(user_id)`.
- WS USER **nunca** se abre en startup; solo cuando hay user_id + wallet y se pide explícitamente (p. ej. subscribe user).
- Carga de estrategias en boot: **solo metadata** (DB); no se inicializa PolymarketAdapter con CLOB en startup.
- Si en env existen `PRIVATE_KEY`/`FUNDER`, se **ignoran** (opcional: log de aviso); no se usan como fallback global.
- Cualquier operación wallet-data sin wallet configurada para el usuario → 4xx (FAIL CLOSED) y logs estructurados cuando una estrategia/intento falla por missing wallet.

---

## 4. Referencias

- `PLAN_WALLET_SCOPE_REFACTOR.md`: alcance del refactor de wallet por usuario.
- `app/main.py`: `lifespan()`, tareas en background.
- `app/core/execution/execution.py`: `_setup_websocket()`, tick con `get_polymarket_client_for_user`.
- `app/core/execution/polymarket_websocket.py`: `get_websocket_manager()`, `connect_user_channel()`.
- `app/core/execution/polymarket_client_wrapper.py`: `get_polymarket_client_for_user()`, `get_polymarket_client()` (lanza).
- `app/core/equity_snapshot_service.py`: `take_snapshot()`, `_snapshot_user_id`.
- `app/core/strategy_engine/control_loop.py`: `start()`, `load_active_strategies()`.

---

## 5) Auditoría y hardening (ciclo de vida)

### Garantías verificadas

- **Boot**: No se crea cliente CLOB; no se llama `get_polymarket_client_for_user`; no se abre WS USER (`connect_user_channel`). Si en env hay `PRIVATE_KEY`/`FUNDER`, se loguea warning y no se usan.
- **PolymarketCLOBWrapper**: `_initialize_client()` (path legacy con PRIVATE_KEY/FUNDER) **lanza RuntimeError** y no se ejecuta; solo `_initialize_client_for_user(user_id)` con wallet desde BD.
- **Execution**: `_resolve_wallet_for_intent()` sin `strategy_id` devuelve `(None, None)` (FAIL CLOSED). Con strategy pero sin wallet activa para ese usuario → `(None, user_id)`. En `tick()`, intent sin wallet o sin `user_id_for_clob` → log estructurado (`intent_failed_missing_wallet`), skip, loop continúa sin crash.
- **Rutas wallet-data**: balance, orders, trades, place, cancel, WS USER subscribe, connection status, test-auth usan `_require_clob_client` → 409 `WALLET_NOT_CONFIGURED` si el usuario no tiene wallet. Dashboard puede devolver equity 0 cuando no hay wallet (no bloquea).
- **OrderbookService**: solo se instancia vía `get_orderbook_service()` en runtime (API/control_loop); no en boot. Usa WS MARKET on-demand, no USER.

### Frontend alineado con v2

- El frontend no asume CLOB global ni wallet de sistema; las wallets son por usuario en Ajustes → Wallets.
- Cuando el backend devuelve **409 WALLET_NOT_CONFIGURED** (p. ej. GET /api/polymarket/balance), el frontend muestra mensaje claro y enlace a configurar wallet. Ver `FRONTEND_WALLET_POLICY_V2.md`.
