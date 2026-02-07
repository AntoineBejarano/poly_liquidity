# Plan: Refactor Wallet Scope — Política institucional estricta (sin CLOB global)

**Versión:** 2.0  
**Objetivo:** Eliminar por completo el concepto de wallet global y system wallet. Cualquier operación o lectura que requiera CLOB auth exige `user_id` + wallet en BD. FAIL CLOSED en todo el sistema.

**Política (NO NEGOCIABLE):**

1. **No existe wallet global ni "system wallet".**  
   - No hay CLOB global inicializado desde PRIVATE_KEY/FUNDER.  
   - No existe `ENABLE_SYSTEM_WALLET_TRADING` ni path "system".  
   - **Aclaración:** Aunque existan PRIVATE_KEY/FUNDER en .env por legacy, el backend **NO los usará en ningún path**. Si están presentes se ignoran (opcional: validar y loguear warning). No hay fallback escondido.

2. **FAIL CLOSED.**  
   - Cualquier operación o lectura que requiera CLOB auth (balance, orders, trades, place/cancel, WS USER) **requiere** `user_id` + wallet en BD.  
   - Si falta `user_id` o wallet: **API → 4xx**; **Execution engine → marcar intent FAILED**, loguear y continuar (no crash loop).

3. **Lectura sin wallet solo para APIs públicas sin auth.**  
   - `/markets`, `/tags`, `/series` (Gamma proxy) pueden ser públicos y no usan wallet.  
   - No hay "balance global", "orders global" ni "health del CLOB" que requiera auth sin user.

4. **WS USER channel.**  
   - Solo se abre con `user_id` y wallet del usuario.  
   - No existe WS USER "global".

---

# 0) Reglas duras (no violar)

| Regla | Descripción |
|-------|-------------|
| No CLOB global | No existe `get_polymarket_client()` que devuelva un cliente inicializado con PRIVATE_KEY/FUNDER. La única forma de obtener un cliente CLOB es `get_polymarket_client_for_user(user_id)`. |
| No system wallet | Eliminado scope "system", flag ENABLE_SYSTEM_WALLET_TRADING y cualquier path que use "wallet global". |
| CLOB auth = user + wallet | Balance, orders, trades, place/cancel, WS USER: siempre `user_id` + wallet en BD. Si falta → API 4xx o intent FAILED. |
| Lectura pública sin wallet | Solo market-data público: Gamma (/markets, /tags, /series). No "readonly global" para balance. Wallet-data (balance, orders) siempre con user. |
| WS USER solo con user | Nunca abrir canal USER sin `user_id` y wallet del usuario. |
| No TODOs con "global" | No dejar "TODO: use global wallet" ni equivalente; eliminar o fallar explícito. |

---

# 0.1) Política única: missing wallet / user_id

| Contexto | Comportamiento |
|----------|----------------|
| **Execution engine (tick / intents)** | Missing wallet o user_id → intent **FAILED**, log estructurado, continuar (no crash loop). |
| **API / acción manual** | Missing wallet o user → request **FALLA** con 4xx y mensaje claro (p. ej. "User wallet not configured"). |

---

# 0.2) WebSocket USER channel

- **El canal WS USER solo se abre si hay `user_id` y wallet del usuario.**  
- Si no hay `user_id`, no abrir canal USER y loguear.  
- No existe WS USER "global".

---

# 1) API de cliente CLOB (única forma)

- **Única función expuesta para obtener cliente CLOB:**  
  `get_polymarket_client_for_user(user_id: str) -> PolymarketCLOBWrapper`

- **Eliminado / no disponible:**  
  - `get_polymarket_client()` (global).  
  - `get_polymarket_client_system()`.  
  - `get_polymarket_client_readonly()` que devolvía el global.  

- No existe "public client" sin firma para CLOB (el SDK CLOB requiere auth para todo lo que no sea market-data público; market-data público se sirve vía Gamma, no CLOB).

---

# 2) Lectura sin wallet (solo público)

- **Gamma (market-data público):** `/markets`, `/tags`, `/series` — sin auth de CLOB, sin wallet. Siguen funcionando igual.  
- **Wallet-data (balance, orders, trades, health CLOB):** requieren auth y `user_id`; se usa `get_polymarket_client_for_user(current_user.id)`. Si el usuario no tiene wallet configurada → 4xx "User wallet not configured".

## 2.1) Health en dos capas (sin CLOB auth en health público)

- **GET /health (o /live):** Salud del backend + DB + Redis + Gamma. **No toca CLOB auth.** Público (o con auth de sesión si aplica), sin wallet. Sirve para saber si el sistema está vivo.
- **GET /api/polymarket/.../auth-health (o equivalente):** “¿Puedo hablar con CLOB con TU wallet?”. Requiere auth + wallet del usuario. Es wallet-data, no health genérico.
- Si en `api/polymarket.py` existe un endpoint de “health” o “connection/status” que antes era global: o se **elimina**, o se **convierte en auth-health** y exige user (y se documenta como tal). El health que usen load balancers / monitoreo **no** debe depender de CLOB con wallet.

## 2.2) Equity snapshot / jobs: exigen user_id, no hay modo global

- **Regla:** En `core/equity_snapshot_service.py`, la API exige `user_id`; los callers deben pasar `user_id`. No existe modo global.
- Si el snapshot era un job periódico “global”, queda roto hasta que se adopte una de estas opciones:

| Opción | Descripción |
|--------|--------------|
| **A** | Equity snapshot se calcula **por usuario** (requiere `user_id`) y solo cuando el usuario lo solicita / está autenticado (p. ej. desde dashboard o un endpoint explícito). |
| **B** | Existe un **scheduler** que recorre usuarios con opt-in y calcula snapshot por cada `user_id` (solo si el usuario tiene wallet). |
| **C** | Se **elimina** equity snapshot si no es core para el producto. |

- Decisión de producto: elegir A, B o C y documentarla aquí o en el código. Sin una de ellas, el job “global” no debe asumir que hay un balance único.

---

# 3) Inventario de cambios por archivo

| Archivo | Cambio |
|---------|--------|
| **polymarket_client_wrapper.py** | Eliminar/deprecar `get_polymarket_client()` (o hacer que lance si se llama). Mantener solo `get_polymarket_client_for_user(user_id)`. Constructor sin `from_user_id` no debe inicializar cliente con settings.private_key. |
| **api/polymarket.py** | Balance, orders, trades, create/cancel: exigir auth + `get_polymarket_client_for_user(current_user.id)`. Si no hay wallet del usuario → 4xx "User wallet not configured". Eliminar cualquier uso de cliente global. |
| **execution.py** | Si no hay `user_id_for_clob` → no usar cliente global; marcar intent FAILED, log, continuar. WebSocket USER: solo inicializar si hay user_id (y cliente de ese user). |
| **execution/gateway.py** | No llamar a `get_polymarket_client()`. Exigir siempre `clob_delegate` inyectado (resuelto por usuario). Si no hay delegate → error (en engine: fail intent; en API: 4xx). |
| **execution_engine/platforms/polymarket_adapter.py** | Resolver `user_id` desde estrategia: **usar `strategy.execution_user_id`** (o regla documentada en §3.1). Si falta user_id → error. CLOB solo vía `get_polymarket_client_for_user(user_id)`. |
| **api/strategies.py** | Cancelaciones al desactivar: usar **`strategy.execution_user_id`** (ver §3.1) y `get_polymarket_client_for_user(user_id)`. Si no hay wallet → 4xx o skip con log según contexto. |
| **api/dashboard.py** | Balance: solo del usuario autenticado (`get_polymarket_client_for_user(current_user.id)`). Si no hay wallet → 4xx o no mostrar balance. Eliminar "balance global". |
| **core/equity_snapshot_service.py** | Balance/equity: solo con user_id y wallet. **API exige user_id; los callers deben pasar user_id; no existe modo global.** Ver §2.2 para opciones (A/B/C). |
| **core/wallet.py** | Eliminar fallback a ENV (PRIVATE_KEY/FUNDER) en `get_active_wallet`. Cuando `user_id` es None: solo BD (o devolver None). No devolver wallet "desde .env". |
| **api/live_status.py** | Actualizar docstrings: no mencionar "PRIVATE_KEY/FUNDER en .env"; solo wallet en BD. cancel_all_orders (si se implementa): con user. |
| **settings / .env.example** | No añadir ENABLE_SYSTEM_WALLET_TRADING. **PRIVATE_KEY/FUNDER: legacy, no usados por el backend. Si están, se ignoran. No deben ser necesarios.** |

### 3.1) Estrategias: quién firma (execution_user_id)

- En un setup institucional, una estrategia puede tener: **created_by** (quién la creó), **owner** (quién la opera), **wallet_owner / execution_user_id** (quién firma órdenes). Usar solo `created_by` como wallet owner puede operar con la wallet equivocada.
- **Regla:** Definir un campo o derivación única para “quién firma órdenes”: **`strategy.execution_user_id`** (o reutilizar el que ya exista en el modelo).
- Si ese campo **no existe aún en BD:**  
  - Regla explícita: **por ahora `execution_user_id = created_by`**.  
  - Esto se documenta como **limitación**: será migrado cuando exista el campo (p. ej. columna `execution_user_id` o lógica de delegación).  
- En el plan y en código no debe leerse “created_by siempre es correcto”; debe leerse “usamos execution_user_id; por ahora equivale a created_by”.

---

# 4) Seguridad y comportamiento

- Ningún path puede colocar o cancelar órdenes sin user wallet.  
- Quitar PRIVATE_KEY/FUNDER del .env no debe romper nada salvo features que se eliminan o que fallan con error claro ("User wallet not configured" o equivalente).  
- Lectura de markets (Gamma) sigue funcionando sin auth de CLOB.  
- Rutas legacy "sin auth" que tocaban CLOB deben fallar CLOSED con error explícito.

---

# 5) Observabilidad

- En cualquier operación de trading: loguear `user_id`, `strategy_id`, `intent_id`, `market_id`, `side`, `size`.  
- Añadir logs cuando se bloquea una acción por "missing wallet" (API 4xx o intent FAILED).

---

# 6) Tests mínimos

1. **Sin PRIVATE_KEY/FUNDER:**  
   - `/markets` (Gamma) funciona.  
   - Endpoints de trading (balance, orders, create/cancel) fallan 4xx si no hay wallet del usuario.  
   - Trading con user wallet en BD funciona.

2. **Execution engine:**  
   - Intent sin user_id → FAILED, no crashea, no llama a CLOB.

3. **WS USER:**  
   - No abre sin user_id (y sin wallet del usuario).

---

# 7) Entregable

- Plan actualizado (este documento).  
- PR con cambios en código: eliminación de cliente global, solo `get_polymarket_client_for_user`, guards y 4xx/FAILED según política.  
- Compatibilidad de `/markets` y discovery (Gamma) mantenida.  
- Features legacy que dependían de wallet global: rotas explícitamente con error claro (no silencio).

---

# 8) Lista de referencias a eliminar o cambiar

## get_polymarket_client() (global)

- `polymarket_client_wrapper.py`: definición → eliminar o hacer que lance.  
- `execution.py`: init WebSocket USER y tick (else branch) → usar solo cliente por user o no abrir WS / marcar FAILED.  
- `execution/gateway.py`: `_get_clob()` → no llamar global; exigir delegate.  
- `execution_engine/platforms/polymarket_adapter.py`: init → obtener user_id y usar `get_polymarket_client_for_user`.  
- `api/polymarket.py`: todos los usos → `get_polymarket_client_for_user(current_user.id)` + 4xx si no wallet.  
- `api/strategies.py`: deactivate cancel → `get_polymarket_client_for_user(strategy.execution_user_id)` (por ahora = created_by, ver §3.1).  
- `api/dashboard.py`: balance → `get_polymarket_client_for_user(current_user.id)` o 4xx.  
- `core/equity_snapshot_service.py`: balance → con user_id y `get_polymarket_client_for_user`.

## PRIVATE_KEY / FUNDER (settings)

- `polymarket_client_wrapper.py`: init sin `from_user_id` → no usar `settings.private_key` / `settings.funder_address` para crear cliente (o eliminar ese path).  
- `wallet.py`: `get_active_wallet(user_id=None)` → no devolver wallet desde ENV; solo BD o None.  
- `api/polymarket.py`: mensajes de error y status → no mencionar "PRIVATE_KEY and FUNDER_ADDRESS"; usar "User wallet not configured".  
- `.env.example`: no ENABLE_SYSTEM_WALLET_TRADING. **PRIVATE_KEY/FUNDER: legacy, no usados por el backend. Si están, se ignoran. No deben ser necesarios.**

---

# 9) Estado de implementación (refactor aplicado)

- **polymarket_client_wrapper.py:** `get_polymarket_client()` lanza RuntimeError; solo `get_polymarket_client_for_user(user_id)` disponible. Wrapper con `_user_id`.
- **execution.py:** Intent sin `user_id_for_clob` → FAILED, log, continue. WS USER no usa cliente global.
- **gateway.py:** `_get_clob()` exige `clob_delegate`; sin delegate lanza. `get_execution_gateway(clob_delegate)` devuelve instancia con delegate cuando se pasa.
- **polymarket_adapter.py:** `config["user_id"]` obligatorio para CLOB; gateway con `clob_delegate=self._client_wrapper`.
- **strategy_engine.py:** Crea `PolymarketAdapter(config={"user_id": strategy.created_by})`. *Limitación (§3.1): por ahora no existe `execution_user_id` en modelo; se usa `created_by` hasta migración.*
- **api/polymarket.py:** Dependency `_require_clob_client` (auth + wallet); balance/orders/trades/place/cancel/orderbook/price/connection/status/test-auth/WS subscribe user usan cliente por usuario; 4xx "User wallet not configured" si falta wallet.
- **api/strategies.py:** Deactivate: cancel pending con `get_polymarket_client_for_user(strategy.created_by)`; si no wallet, skip con log. *Cuando exista `execution_user_id` en modelo, usar ese (§3.1).*
- **api/dashboard.py:** Balance con `get_polymarket_client_for_user(current_user.id)` y cache por usuario.
- **equity_snapshot_service.py:** Balance solo si `_snapshot_user_id`; sin user_id no se llama CLOB.
- **wallet.py:** `get_active_wallet(user_id=None)` retorna None; sin fallback ENV.
- **.env.example:** PRIVATE_KEY/FUNDER documentados como legacy; no ENABLE_SYSTEM_WALLET_TRADING.

---

# 10) Boot vs Runtime

Qué se inicializa en arranque y qué se hace en runtime (lazy / on-demand) está documentado en:

- **`BOOT_VS_RUNTIME.md`**: inventario de startup (lifespan, singletons, loops), clasificación Safe-at-boot vs Must-be-runtime, y garantías (arranque sin PRIVATE_KEY/FUNDER, sin WS USER ni CLOB en boot).
