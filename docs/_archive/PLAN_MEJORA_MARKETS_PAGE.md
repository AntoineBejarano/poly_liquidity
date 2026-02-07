# Plan v2: Mejora completa de la página /markets (Gamma-first)

**Versión:** 2.0  
**Objetivo:** `/markets` listará markets de Gamma/Polymarket de forma correcta, rápida y robusta. Discovery + selección (ver, filtrar, paginar, Add to Universe). Operativa (trading) es aparte y usará WS market channel una vez el market esté en universo.  
**Referencias:** [ANALISIS_MARKETS_PAGE.md](./ANALISIS_MARKETS_PAGE.md), OpenAPI Polymarket Gamma, [PLAN_REDIS_OPTIMIZACION_VELOCIDAD.md](./PLAN_REDIS_OPTIMIZACION_VELOCIDAD.md)

---

# Parte 1: Plan v2 (Ejecutable)

## Reglas duras (no romper)

| Regla | Descripción |
|-------|-------------|
| Contrato array | GET /markets devuelve ARRAY (Gamma-like). Nada de envelope. |
| Metadata headers | X-Limit, X-Offset, X-Has-More, etc. — nunca en body |
| Endpoints | No inventar endpoints que no estén en repo, salvo los explícitos (POST universe/markets, POST orderbook-metrics si se decide) |
| Orderbook WS | NO tocar el engine de suscripción; solo consumir su cache/estado |
| clobTokenIds | NO asumir list[0]=YES. Solo inferir yes/no si viene como dict con keys explícitas (case-insensitive). Lista = tokens sin semántica |
| Separación estrategia | Cada estrategia tiene su universo; operativa distinta de discovery |
| Redis | No decision-critical. Solo discovery y métricas UI; nunca fuente de verdad de decisiones |

---

## Contexto: Discovery vs Operativa

| Capa | Rol | Fuentes de datos |
|------|-----|------------------|
| **Discovery** | /markets: ver, filtrar, paginar, Add to Universe | Gamma API, DB (enabled), cache discovery |
| **Operativa** | Trading real, decisiones, órdenes | WS market channel (book, price_change, best_bid_ask), user channel (auth para órdenes) |

- WS market channel: book/price_change/best_bid_ask. User channel: auth para órdenes/trades.
- **Nota WS:** `best_bid_ask` requiere `custom_feature_enabled: true` al subscribir. Si queremos best_bid_ask en el futuro, hay que setearlo. No implementar ahora; dejar apuntado.
- Sports websocket es broadcast global con ping/pong distinto; no mezclar con CLOB.
- Esta entrega NO toca el WS operativo.

---

## Fase 1: Backend — Proxy Gamma GET /markets

**Objetivo:** Proxy Gamma-compatible que devuelve array, añade campos internos, expone metadata vía headers.

### Tareas (implementables)

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 1.1 | Forward query params | MUST | Aceptar y reenviar a Gamma: limit, offset, order, ascending, id[], slug[], clob_token_ids[], tag_id, closed, liquidity_num_min/max, volume_num_min/max, start_date_min/max, end_date_min/max, y resto de la OpenAPI |
| 1.2 | Defaults | MUST | limit=50 (max 100), offset=0. order default: createdAt desc |
| 1.3 | Order fallback | MUST | Si order=updatedAt y Gamma 4xx → reintentar order=createdAt |
| 1.4 | Cache order válido | NICE | gamma_supported_order_fields en memoria, TTL 1h. Si updatedAt falla, no reintentar en próximas requests |
| 1.5 | Respuesta array | MUST | Devolver array de markets. NO eliminar campos Gamma. Añadir por market: enabled (merge DB), clob_token_ids (ver 1.6) |
| 1.6 | clob_token_ids | MUST | Helper parse_clob_token_ids(raw). Dict case-insensitive YES/NO → primary_yes, primary_no. Lista → clob_token_ids_all sin semántica. Nunca asumir list[0]=YES. **Dentro de clob_token_ids añadir:** `selection_hint` y `primary`. Ver contrato abajo |
**Contrato clob_token_ids.selection_hint + primary (MUST):**

- `primary`: siempre `string | null` — el token "a usar" para métricas según policy
- `selection_hint`: siempre uno de `primary_yes` | `single` | `multi` | `none`
- Si `multi`: `primary` es "primer token" solo si se decide muestrear; el front siempre muestra badge "Multi (sampled)"

| 1.7 | Headers | MUST | X-Limit, X-Offset, **X-Has-More** (true si última llamada Gamma devolvió exactamente limitGamma items → "probablemente" hay más; Gamma no da total, sobre todo con filtros cambiantes), X-Order-Effective, X-Gamma-Fetch-Count, X-Gamma-Scanned. NICE: X-Has-More-Confidence: low\|high |

### Definition of Done

- GET /markets devuelve array; cada item tiene enabled y clob_token_ids (primary_yes/primary_no o clob_token_ids_all)
- Headers presentes y correctos
- Tests: array + clob_token_ids + headers

### Rollback

- Si Gamma cambia contrato: feature flag para desactivar proxy y servir fallback (ej. lista vacía con mensaje) mientras se corrige

### Coste / Riesgo

- Cambio en consumidores que esperan estructura distinta; revisar MarketsListWithLoader, SeriesListWithLoader
- Gamma rate limits: mitigar con circuit breaker (Fase 3)

---

## Fase 2: Backend — Enabled + two-phase paging

**Objetivo:** Merge MarketEnabledState; filtro enabled local; two-phase paging cuando enabled aplica.

### Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 2.1 | Merge enabled | MUST | Tras fetch Gamma, consultar MarketEnabledState y añadir enabled por market |
| 2.2 | Filtro enabled | MUST | Si query enabled=true|false, aplicar tras merge. Gamma no conoce enabled |
| 2.3 | Two-phase paging | NICE | max_iterations=5, max_scanned=500. Fetch chunks, merge, filtrar, acumular hasta limit o cap |
| 2.4 | Headers partial | MUST | X-Partial-Page: true, X-Partial-Reason: max_scanned|max_iterations cuando no se llena la página |
| 2.5 | Headers offset | MUST | X-Enabled-Filter-Applied, X-Offset-Mode (gamma|filtered). Suficiente para v1 |
| 2.6 | UI enabled + paginación | MUST | Si enabled presente: **mantener offset Gamma** pero mostrar en UI "Filtered results (may skip)" + X-Partial-Page y X-Gamma-Scanned. **No construir paginador "filtered" real en v1** (puede confundir). Page number (1,2,3) como NICE futuro |

### Definition of Done

- enabled filter reduce items correctamente
- Con enabled=true y escasez, two-phase funciona y headers indican partial si aplica

### Rollback

- Desactivar two-phase: si enabled presente, devolver primera página Gamma filtrada sin overfetch

### Coste / Riesgo

- 5×100 items por request en peor caso; headers X-Gamma-Scanned permiten observabilidad

---

## Fase 3: Backend — Robustez y rate limits

**Objetivo:** Timeouts, 429/5xx → 503, circuit breaker, rate limit soft.

### Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 3.1 | Timeouts Gamma | MUST | **connect_timeout: 1s**, **read_timeout: 3–5s** (máx), **overall timeout: 5s** por request. 10s acumula requests en discovery; límites bajos evitan backlog. Si circuit breaker abierto → 503 inmediato |
| 3.2 | 429/5xx → 503 | MUST | Si Gamma 429 o 5xx, devolver 503 con mensaje claro. Log. Sin retries internos agresivos |
| 3.3 | Circuit breaker | MUST | Si Gamma 429 repetido (ej. 3 en ventana), responder 503 rápido sin intentar |
| 3.4 | Rate limit | MUST | **O lo hacéis de verdad o no lo llaméis rate limit.** v1: token bucket por IP + ruta, devolver 429 local. Aplicar en /orderbook-metrics (es el que más se spamea). Opción B (solo logs + X-RateLimit-Policy) si no se implementa bloqueo |
| 3.5 | Logs | MUST | Log 429, 5xx, circuit breaker open/close |

### Definition of Done

- 429 Gamma → 503 en <500ms
- Circuit breaker abre tras N fallos; cierra tras TTL

### Rollback

- Aumentar TTL circuit breaker o desactivar temporalmente

### Coste / Riesgo

- Usuarios legítimos pueden ver 503 bajo carga Gamma; documentar y monitorear

---

## Fase 4: Backend — Orderbook-metrics y Add to Universe

**Objetivo:** orderbook-metrics con partials y límites; endpoint Add to Universe idempotente.

### 4.1 Orderbook-metrics

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 4.1 | token_ids CSV | MUST | Query param token_ids=id1,id2. Max 100. Dedupe, ignorar null/empty. 400 si excede |
| 4.2 | POST body | NICE | POST /markets/orderbook-metrics body { token_ids: [...] } mismo límite 100 |
| 4.3 | Response shape estable | MUST | Fijar shape explícito (evitar que frontend adivine). Ver ejemplo abajo |
| 4.4 | Campos partial | MUST | partial: bool, timed_out: bool, errors: string[] (cortos). Siempre responder con partials; nunca fallar toda la request |
| 4.5 | Timeout global | MUST | Hard timeout 50–100ms. Si state cache permite batch-get, usarlo; si no, concurrency 10–20, abort si timeout |
| 4.6 | max_requests_per_min | NICE | Docs + log para evitar abuso |

**Ejemplo response shape orderbook-metrics:**
```json
{
  "found_token_ids_count": 12,
  "missing_token_ids_count": 8,
  "partial": true,
  "timed_out": true,
  "errors": ["timeout"],
  "metrics": {
    "tokenId1": { "spread_bps": 50, "depth_usdc_at_50bps": 1000, "impact_bps_for_usdc_1000": 30 },
    "tokenId2": null
  }
}
```

### 4.2 POST /api/strategies/{id}/universe/markets

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 4.7 | Endpoint | MUST | POST body { market_id: "<gamma_market_id>" } |
| 4.8 | Idempotencia | MUST | Añadir a universe_config.markets si no existe. Devuelve { added: true|false, universe: ... } |
| 4.9 | Validación | MUST | Si market disabled (MarketEnabledState) → 400 "Market disabled internally" |
| 4.10 | Fuente de verdad | MUST | **DB es fuente de verdad del universo por estrategia.** Cache strategy:{id}:universe es read-through y se **invalida al POST** |
| 4.11 | Auth | MUST | get_admin_user (igual que PUT universe) |

### Definition of Done

- orderbook-metrics responde en <100ms con counts; partial si timeout
- POST universe/markets idempotente; 400 si disabled

### Rollback

- Desactivar POST universe/markets; UI usa PUT universe con merge manual

### Coste / Riesgo

- orderbook-metrics no es decision-critical (solo UI); partials aceptables

---

## Fase 5: Frontend — Gamma-first UI

**Objetivo:** Query params Gamma, paginación, filtros por clase, backpressure.

### Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 5.1 | Query params | MUST | Construir limit, offset, order, ascending, tag_id, closed, liquidity_num_min, volume_num_min, enabled |
| 5.2 | Clases filtros | MUST | Gamma-pass-through (limit, offset, tag_id, closed, order...); Local (enabled); Derived (search si existe) |
| 5.3 | Search | MUST | Si search no existe → deshabilitar con tooltip "Search not available". Si existe → debounce 400–600ms |
| 5.4 | Reset offset | MUST | Al cambiar filtros o sort, reset offset=0 siempre |
| 5.5 | Paginación | MUST | Prev/Next; leer X-Has-More, X-Offset, X-Limit, X-Order-Effective |
| 5.6 | X-Partial-Page | MUST | Si X-Partial-Page: true → mostrar "Results truncated" |
| 5.6b | Enabled filter UI | MUST | Si enabled presente → mostrar "Filtered results (may skip)" + usar X-Partial-Page y X-Gamma-Scanned |
| 5.7 | AbortController | MUST | Cancelar requests previas cuando cambian filtros rápido |
| 5.8 | Order estable | MUST | Default order estable; permitir override |

### Definition of Done

- Cambiar filtro/sort → offset=0, refetch; requests previas canceladas
- Paginación funcional; "Results truncated" cuando aplica

### Rollback

- Volver a filtrado client-side temporal si problemas server-side

### Coste / Riesgo

- UX depende de latencia Gamma; debounce y AbortController reducen carga

---

## Fase 5.5: Frontend — Category selector

**Objetivo:** Selector de categoría server-side (Gamma) usando `tag_id`.

### Tareas (MUST)

| # | Tarea | Instrucción |
|---|-------|-------------|
| 5.5.1 | Dropdown Category | Mostrar dropdown "Category" en la barra de filtros |
| 5.5.2 | Cargar opciones | Primero intentar `/directory/tags` (si devuelve categorías top-level); si no, `/tags` |
| 5.5.3 | Al seleccionar categoría | set `tag_id=<id>`, reset `offset=0`, refetch `/markets` |

### Tareas (NICE)

| # | Tarea | Instrucción |
|---|-------|-------------|
| 5.5.4 | "All categories" | Opción "All categories" = `tag_id` vacío |
| 5.5.5 | Persistencia | Persistir selección en localStorage (`markets_selected_tag_id`) |
| 5.5.6 | Contador/label | Mostrar contador o label de la categoría seleccionada |

### Mapping categorías (evitar hardcode peligroso)

**Opción A (recomendada): Tags dinámicos**

- UI lista los tags que devuelve el backend; el usuario elige.
- Ventaja: no se rompe si Gamma cambia nombres/ids.

**Opción B: Shortcuts "top categories" (configurable)**

Si se quieren botones fijos ("Politics", "Sports", "Finance", "Crypto"), hacerlo configurable:

- Ejemplo config (backend o env frontend):
  ```
  NEXT_PUBLIC_MARKETS_TOP_CATEGORIES='[{"label":"Politics","tagSlug":"politics"},{"label":"Sports","tagSlug":"sports"},{"label":"Finance","tagSlug":"finance"},{"label":"Crypto","tagSlug":"crypto"}]'
  ```
- Frontend carga `/tags`, resuelve `tagSlug` → `tag_id`.
- Si un slug no existe, ocultar ese shortcut (no rompe).

### Configuración desde fuera (NICE, recomendado)

Para no tocar código al cambiar categorías y filtros:

| Variable | Descripción |
|----------|-------------|
| `NEXT_PUBLIC_MARKETS_SHOW_TOP_CATEGORIES` | true/false — mostrar botones shortcuts |
| `NEXT_PUBLIC_MARKETS_TOP_CATEGORIES` | JSON con label + tagSlug |
| `NEXT_PUBLIC_MARKETS_DEFAULT_TAG_ID` | tag_id por defecto — **más robusto** que slug (slugs/names pueden cambiar; tag_id suele ser estable) |
| `NEXT_PUBLIC_MARKETS_DEFAULT_TAG_SLUG` | fallback si no se quiere hardcodear IDs — resolver vía /tags |
| `NEXT_PUBLIC_MARKETS_ENABLE_SERIES_FILTER` | true/false — activar/desactivar filtro Series sin code changes |
| `NEXT_PUBLIC_MARKETS_ENABLE_SPORTS_FILTERS` | true/false — si más tarde se usan sports_market_types[]/game_id |

**Backend (si existe GET /config/public):** Devolver `top_categories` ya resueltas a `{label, tag_id}` para que el front no tenga que resolver slugs.

### UI: Category y Series como filtros separados (explícito)

| Filtro | Param | Fuente | Nota |
|--------|-------|--------|------|
| **Category** | tag_id | /directory/tags o /tags | Dropdown "Category" |
| **Series** | series_id | /series (proxy Gamma) | Param real que soporte el proxy; si no existe, dropdown disabled |

Ambos son filtros independientes; el usuario puede combinar Category + Series.

### Nota Sports / League-Series

En Sports a menudo se querrá:
- **Category** = Sports (tag_id)
- **League/Series** (NBA, NFL…) vía `/series` o `game_id`

Encaja con la separación Discovery vs Operativa:
- Discovery: filtros tag/series
- Operativa: WS market channel una vez en universo

---

## Fase 6: Frontend — Token IDs y métricas

**Objetivo:** Token Selection Policy explícita; precedencia spread; mensajes claros.

### Token Selection Policy (MUST)

Frontend debe usar **clob_token_ids.selection_hint** y **clob_token_ids.primary** (backend los añade). No re-implementar la policy.

| selection_hint | Acción |
|----------------|--------|
| primary_yes | Usar primary para métricas |
| single | Usar primary |
| multi | "Multi (sampled)" badge; usar primary si existe para métricas muestreadas |
| none | "Token IDs unavailable" |

### Precedencia spread (MUST)

1. Gamma spread no-null → mostrar
2. Gamma bestBid/bestAsk ambos no-null → calcular; si inconsistentes con spread → confiar en spread
3. State cache orderbookMetrics
4. "Not subscribed" / "Token IDs unavailable"

### Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 6.1 | Política tokens | MUST | Usar clob_token_ids.selection_hint y clob_token_ids.primary del backend; no re-implementar policy |
| 6.2 | Precedencia spread | MUST | Orden estricto: Gamma spread → Gamma bestBid/bestAsk → state cache → fallback |
| 6.3 | Orderbook-metrics eficiente | MUST | Pedir solo primary de items visibles (página actual). GET o POST según cantidad. Leer metrics del response shape estable |
| 6.4 | Mensajes | MUST | "Not subscribed", "Token IDs unavailable", "Multi (sampled)" según caso |

### Definition of Done

- Métricas muestran valores cuando existen; mensajes claros cuando no

### Rollback

- Ocultar columnas spread/depth/impact si fallan; mantener tabla funcional

---

## Fase 7: Frontend — Tags y Series

**Objetivo:** Dropdowns con endpoints existentes; caching; protección listas grandes.

### Backend: soporte para categoría (recomendado)

- `/tags` o `/directory/tags` deben responder con algo utilizable: `id`, `name`, idealmente `slug`.
- Si el repo no da `slug`, el front puede usar `name` pero es más frágil.
- NICE: si hay tags enormes, paginación/typeahead (ver 7.5).

### Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 7.1 | Tags | MUST | Usar /tags o /directory/tags. No inventar. Verificar que response incluye id, name (y slug si existe) |
| 7.2 | Series | MUST | Usar /series (proxy Gamma). No inventar |
| 7.3 | Si no existe | MUST | Dropdown deshabilitado + TODO en código |
| 7.4 | Cache | NICE | Cache L1 (y hook Redis) para /tags y /series, TTL 5–30 min |
| 7.5 | Listas grandes | NICE | Paginación/búsqueda en dropdown; typeahead; o cachear top 500 |

### Definition of Done

- Dropdowns funcionales con endpoints existentes

### Rollback

- Deshabilitar dropdown si endpoint falla

---

## Fase 8: Frontend — Add to Universe

**Objetivo:** Strategy selector; botón idempotente; toasts.

### Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 8.1 | Strategy selector | MUST | Dropdown arriba; GET /api/strategies; persistir markets_selected_strategy_id en localStorage |
| 8.2 | Botón | MUST | Si no estrategia → enfocar selector. Si hay → POST universe/markets |
| 8.3 | Toasts | MUST | "Added" / "Already in universe"; 400 "Market disabled internally"; 404 "Strategy not found" |
| 8.4 | Side panel | MUST | Mismo comportamiento en "Add to Strategy Universe" |

### Definition of Done

- Add to Universe funcional; idempotente; mensajes claros

### Rollback

- Ocultar botón; dejar solo toggle enabled

---

## Fase 9: Tests

### Backend (MUST)

- GET /markets array + enabled + clob_token_ids
- Headers X-Has-More, X-Gamma-Fetch-Count, X-Gamma-Scanned
- Filtros Gamma y enabled
- Two-phase con X-Partial-Page
- orderbook-metrics: token_ids, counts, límite 100 → 400
- POST universe/markets: idempotente, 400 disabled
- parse_clob_token_ids: string, list, dict; no list[0]=YES

### Frontend (NICE)

- Construcción query params
- Reset offset al cambiar filtros
- Token Selection Policy

---

## Fase 10: Documentación

### docs/api/markets.md (MUST)

- Compat contract: array + campos añadidos
- Ejemplos copy-paste con params
- Query params: Gamma vs internos
- clobTokenIds + selection_hint, primary + Token Selection Policy
- Headers (X-Has-More: "probablemente" hay más; documentar matiz)
- Precedencia spread; orderbook-metrics response shape estable
- Add to Universe (DB fuente de verdad; cache invalidar al POST)

---

# Parte 2: Peligros / Footguns (priorizados)

| Prioridad | Peligro | Mitigación |
|-----------|---------|------------|
| P0 | Asumir list[0]=YES en clobTokenIds | Solo inferir yes/no si dict con keys explícitas; lista → clob_token_ids_all sin semántica |
| P0 | X-Has-More con len<limit | has_more=true solo si última llamada Gamma devolvió exactamente limitGamma items ("probablemente" hay más; Gamma no da total) |
| P0 | Order updatedAt no existe en Gamma | Fallback a createdAt; cachear order válido para evitar 2 roundtrips |
| P1 | Páginas duplicadas/saltos al cambiar order | Reset offset=0 al cambiar filtros/sort |
| P1 | Auto-DDOS por UI (typing, toggles) | Debounce, AbortController, rate limit backend |
| P1 | Gamma 429 en cascada | Circuit breaker; 503 rápido sin retries |
| P1 | Timeout Gamma 10s en discovery | Acumula requests; usar connect 1s, read 3–5s, overall 5s |
| P2 | Tabla "miente" con métricas multi-outcome | Token Selection Policy; badge "Multi (sampled)" |
| P2 | orderbook-metrics bloquea request | Hard timeout; responder partials siempre |
| P2 | Tags/Series 10k items en dropdown | Paginación, typeahead, top N |
| P3 | Two-phase muy caro | Caps max_iterations, max_scanned; headers observabilidad |

---

# Parte 3: Decisiones cerradas

| Decisión | Estado |
|----------|--------|
| GET /markets devuelve array | Cerrado |
| Metadata por headers | Cerrado |
| clobTokenIds: no list[0]=YES | Cerrado |
| Token Selection Policy (primary_yes → len=1 → len≥2 → unavailable) | Cerrado |
| Precedencia spread: Gamma spread → bestBid/bestAsk → state cache → fallback | Cerrado |
| X-Has-More: true si última llamada = limitGamma | Cerrado |
| Two-phase con caps (max_iterations, max_scanned) | Cerrado |
| orderbook-metrics: partials siempre, timeout 50–100ms | Cerrado |
| Add to Universe idempotente, 400 si disabled | Cerrado |
| Discovery vs Operativa separados; WS operativo no se toca | Cerrado |
| Redis no decision-critical | Cerrado |
| Timeout Gamma: connect 1s, read 3–5s, overall 5s | Cerrado |
| clob_token_ids: selection_hint + primary (primary siempre string|null; selection_hint primary_yes|single|multi|none; multi → badge) | Cerrado |
| orderbook-metrics: response shape estable (metrics, partial, timed_out, errors) | Cerrado |
| Rate limit: token bucket 429 en /orderbook-metrics v1 | Cerrado |
| enabled + paginación: "Filtered results (may skip)"; no page number en v1 | Cerrado |
| best_bid_ask WS requiere custom_feature_enabled (apuntado) | Cerrado |

---

# Parte 4: Open questions (máx. 10)

1. **Search:** ¿Existe endpoint /search en polymarket que podamos usar para búsqueda server-side, o dejamos search deshabilitado en v1?

2. **POST orderbook-metrics:** ¿Implementamos POST en esta entrega o solo GET con token_ids CSV (y asumimos max 100 ids en URL)?

3. **Rate limit:** v1 recomendado: token bucket en /orderbook-metrics con 429 local. ¿Extender a /markets o solo orderbook-metrics?

4. **Tags/Series paginación:** ¿Los endpoints /tags y /series actuales soportan limit/offset, o hay que añadirlo al proxy?

5. **Circuit breaker TTL:** ¿Cuántos segundos mantener circuit abierto tras 429? (Sugerido: 60s)

6. **gamma_supported_order_fields:** ¿Cache en memoria solo o preparar abstracción para Redis desde ya?

7. **X-Offset-Mode:** ¿Exponer gamma vs filtered en headers, o solo X-Enabled-Filter-Applied para simplificar?

8. **Consumidores legacy:** ¿MarketsListWithLoader y SeriesListWithLoader leen array directo o esperan otra estructura? ¿Hay que migrarlos?

9. **order default:** ¿Preferimos createdAt desc o volumeNum desc como default para /markets discovery? (volumeNum puede ser más útil para usuarios)

10. **max_requests_per_minute orderbook-metrics:** ¿Solo documentar, o implementar rechazo 429 si se excede?

---

# Parte 5: Redis-ready (sin Redis todavía)

## Principio

Introducir abstracción de cache provider (in-memory hoy, Redis mañana) en los puntos donde se consumirá cache. Redis NO es decision-critical; solo discovery y métricas UI.

## Qué NO se cachea (decision-critical)

- MarketEnabledState (DB, fuente de verdad)
- universe_config por estrategia (DB)
- Órdenes, trades, posiciones
- Datos del WS operativo (book en tiempo real para trading)

## Qué se cachea (discovery / métricas UI)

### TTLs

| Tipo | TTL | Comentario |
|------|-----|------------|
| Discovery | 60–180s markets, 300–900s events | Según entidad |
| Metadata | 3600–7200s tags, series | Poco volátil |
| Order fields Gamma | 3600s | gamma_supported_order_fields |
| Circuit breaker | 10–60s | Estado temporal |
| Operativa UI | 1–15s | pm:book, pm:best, pm:metrics — solo para UI, no decisiones |

### Key schema sugerido

```
# Discovery
gamma:markets:q:{hash(params)}     TTL 60–180s
gamma:events:q:{hash(params)}      TTL 300–900s
gamma:tags:all                    TTL 3600–7200s
gamma:series:all                  TTL 3600–7200s
gamma:supported_order_fields      TTL 3600s
gamma:circuit_breaker             TTL 10–60s

# Operativa UI (no decision-critical)
pm:book:{asset_id}                TTL 1–3s
pm:best:{asset_id}                TTL 3–10s
pm:metrics:{asset_id}             TTL 5–15s

# Por estrategia (cache lectura)
strategy:{id}:universe            TTL 30–120s  (read-through; invalidar al POST)
strategy:{id}:subs                TTL 30–60s
```

### Dónde se produce/consume

| Componente | Produce | Consume | Hook para Redis |
|------------|---------|---------|-----------------|
| GET /markets | — | gamma:markets:q:{hash} | Inyectar CacheProvider en markets.py; hoy APICache, mañana Redis |
| GET /tags, /series | — | gamma:tags:all, gamma:series:all | Mismo CacheProvider |
| gamma_supported_order_fields | gamma:supported_order_fields | — | CacheProvider.set/get |
| orderbook-metrics | — | pm:metrics:{asset_id} (hoy state_cache) | Abstracción: StateCacheProvider; hoy state_cache_service, mañana opcional Redis L2 |
| Circuit breaker | gamma:circuit_breaker | — | CacheProvider para estado compartido entre instancias |

### Abstracciones a introducir HOY

1. **CacheProvider (interface):** `get(key) -> value | None`, `set(key, value, ttl_seconds)`, `delete(key)`. Implementación: InMemoryCacheProvider (dict + TTL). Mañana: RedisCacheProvider.

2. **Punto de inyección:** En `markets.py` (y donde se use APICache para Gamma), usar `cache_provider` inyectado. Default: implementación in-memory.

3. **StateCacheProvider:** Ya existe state_cache_service. Mantener interfaz; documentar que pm:book, pm:metrics son consumidos por orderbook-metrics. No cambiar engine WS; solo consumir.

4. **Config:** `CACHE_PROVIDER=memory|redis` (o similar). Hoy solo memory.

### Cache stampede protection (para cuando haya Redis)

Si metes Redis después, lo siguiente que pasará al expirar es **stampede** (muchas requests simultáneas por la misma key).

Añadir al plan (aunque no implementar hoy):

- **Singleflight / lock por key:** `SETNX lock:gamma:markets:q:{hash} 3–5s` — solo uno refresca, los demás esperan o leen stale.
- O **stale-while-revalidate:** servir stale 30s mientras refrescas en background. Si no hay background job, entonces singleflight.

Dejarlo escrito evita que Redis empeore la carga en expiry.

---

# Parte 6: Checklist final de PR por fases

## Fase 1 (Backend Proxy Gamma)

- [x] Helper `parse_clob_token_ids` implementado; tests con string, list, dict; no list[0]=YES
- [x] GET /markets forwardea params a Gamma; defaults limit=50, offset=0, order=createdAt desc
- [x] Order fallback: 4xx updatedAt → createdAt
- [x] Respuesta array con enabled + clob_token_ids (primary_yes/primary_no o clob_token_ids_all)
- [x] Headers: X-Limit, X-Offset, X-Has-More, X-Order-Effective, X-Gamma-Fetch-Count, X-Gamma-Scanned
- [x] Tests unit + integration

## Fase 2 (Enabled + two-phase)

- [x] Merge MarketEnabledState en cada market
- [x] Filtro enabled aplicado post-fetch
- [x] Two-phase: max_iterations=5, max_scanned=500
- [x] X-Partial-Page, X-Partial-Reason cuando no se llena página
- [x] Tests two-phase

## Fase 3 (Robustez)

- [x] Timeout Gamma: connect 1s, read 3–5s, overall 5s
- [x] 429/5xx → 503; log
- [x] Circuit breaker implementado
- [x] Rate limit token bucket en /orderbook-metrics con 429 (o logs si Opción B)
- [x] Cache gamma_supported_order_fields (opcional)

## Fase 4 (Orderbook + Add to Universe)

- [x] GET orderbook-metrics: token_ids CSV, max 100; response shape estable (metrics, partial, timed_out, errors)
- [x] Hard timeout 50–100ms; partials siempre
- [x] POST orderbook-metrics (opcional)
- [x] POST universe/markets: idempotente, 400 si disabled; DB fuente de verdad; invalidar cache strategy:{id}:universe al POST
- [x] Tests

## Fase 5 (Frontend UI)

- [x] Query params construidos y enviados (incl. tag_id para Category)
- [x] Reset offset=0 al cambiar filtros/sort
- [x] AbortController para cancelar requests (useDataLoader)
- [x] Debounce search 400–600ms; param search en GET /markets
- [x] Paginación Prev/Next; X-Partial-Page → "Results truncated"

## Fase 5.5 (Category selector)

- [x] Category (tag_id) y Series (series_id) como filtros separados en UI
- [x] Dropdown Category; cargar desde /directory/tags o /tags
- [x] Al seleccionar: tag_id, reset offset, refetch
- [x] "All categories" (tag_id vacío)
- [x] Persistencia localStorage para tag_id (markets_selected_tag_id)
- [x] Top categories y DEFAULT_TAG_ID vía env (NEXT_PUBLIC_MARKETS_DEFAULT_TAG_ID)

## Fase 6 (Frontend métricas)

- [x] Token Selection Policy implementada (selection_hint + primary)
- [x] Precedencia spread (Gamma → state cache → fallback)
- [x] orderbook-metrics solo para items visibles (primary por página)
- [x] Mensajes "Not subscribed", "Token IDs unavailable", "Multi (sampled)"

## Fase 7 (Tags/Series)

- [x] /tags o /directory/tags con id, name (slug si existe)
- [x] Dropdowns Tags y Series con endpoints existentes (/directory/tags, GET /series)
- [x] Cache L1 en frontend 10 min (opcional)
- [x] Protección listas grandes: filtro typeahead en dropdown si >15 opciones (opcional)

## Fase 8 (Add to Universe)

- [x] Strategy selector GET /api/strategies con persistencia localStorage
- [x] Botón Add to Universe funcional; si no estrategia → enfocar selector
- [x] Toasts según respuesta (Added/Already in universe, 400, 404)
- [x] Side panel mismo flujo

## Fase 9–10 (Tests + Docs)

- [x] Suite tests backend (phase0, phase2, gamma_utils; headers X-Gamma-Fetch-Count, X-Gamma-Scanned)
- [x] docs/api/markets.md creado/actualizado

## Redis-ready (hooks)

- [x] Interface CacheProvider definida
- [x] InMemoryCacheProvider implementado
- [x] Inyección en markets.py (o punto elegido) para gamma:markets cache
- [x] Documentar key schema, TTLs y **cache stampede protection** (singleflight/SWR) para futuro Redis

---

# Parte 7: Vista navegable y polling inteligente (/markets)

**Objetivo:** La página /markets debe ser navegable (una página a la vez, sin “todos de golpe”), consumir menos llamadas y hacer un polling inteligente (solo cuando tenga sentido).

**Problema actual:** Sensación de “todos de golpe”, muchas llamadas (GET /markets + orderbook-metrics cada 30s siempre), lista poco navegable.

---

## Principios

| Principio | Descripción |
|-----------|-------------|
| Una página a la vez | Nunca cargar “todos” los mercados en una sola vista. Siempre limit + offset. |
| Polling solo cuando aporta | No refrescar en background cada 30s siempre; refrescar al volver a la pestaña o manualmente. |
| Menos tokens en orderbook-metrics | Pedir métricas solo para los mercados de la página actual (≈ limit), no más. |
| Paginación clara | Usuario debe ver claramente “página actual” y poder ir Anterior / Siguiente (o página N). |

---

## Fase 7.1: Paginación y tamaño de página (MUST)

| # | Tarea | Instrucción |
|---|-------|-------------|
| 7.1.1 | Tamaño de página por defecto | Reducir `DEFAULT_LIMIT` de 50 a **25** (compromiso UX). Configurable vía `NEXT_PUBLIC_MARKETS_PAGE_SIZE` (default 25). Escape hatch: selector 20/50 en 7.4.1. |
| 7.1.2 | Una sola página en memoria | El estado solo mantiene la página actual (la que devuelve GET /markets con offset/limit). No acumular páginas ni hacer “load more” que concatene. |
| 7.1.3 | UI de paginación | Mantener Prev/Next; mejorar texto: “Página N” o “Resultados 1–20 de esta búsqueda” y “Siguiente” deshabilitado cuando `X-Has-More !== true`. No mostrar “total” si el backend no lo expone (Gamma no da total). |
| 7.1.4 | Reset offset | Al cambiar cualquier filtro (tag_id, series_id, search, order, enabled): `offset = 0` y una sola petición para la nueva página 1. |

**Definition of Done:** Usuario ve 20–25 mercados por vista; Anterior/Siguiente cambian de página sin cargar cientos de ítems.

---

## Fase 7.2: Polling inteligente (MUST)

| # | Tarea | Instrucción |
|---|-------|-------------|
| 7.2.1 | Quitar refresh fijo 30s | Eliminar o desactivar `refreshInterval: 30000` en el `useComponentDataLoader` de la página /markets (o ponerlo en 0). Discovery no necesita actualización cada 30s. |
| 7.2.2 | Refresco al volver a la pestaña | `visibilitychange` → un único `refetch()`. **Debounce:** no más de 1 refetch cada 3–5 s. **Throttle por tiempo:** solo refetch si `lastFetchedAt` hace > 15–30 s (evitar alt-tab spam / flapping en PWAs, devtools). Ver Riesgos 7.2.3. |
| 7.2.3 | Refresco manual | Botón “Actualizar” visible que llame a `refetch()`. **MUST:** indicador “Actualizado hace X s” (“Updated Xs ago”) para que la tabla no parezca “muerta”; deshabilitar botón 5–10 s tras pulsar para evitar spam. |
| 7.2.4 | Sin polling en background | No usar `setInterval` para /markets. Único auto-refresh: al volver a la pestaña (con debounce/throttle). Intervalo largo (2–5 min) solo visible: **detrás de flag** (ej. `NEXT_PUBLIC_MARKETS_BACKGROUND_REFRESH_MIN`) para no reintroducir el problema; NICE. |

**Definition of Done:** No hay peticiones periódicas cada 30s; hay como mucho un refetch al volver a la pestaña y/o al pulsar Actualizar.

---

## Fase 7.3: Orderbook-metrics solo para la página actual (MUST)

| # | Tarea | Instrucción |
|---|-------|-------------|
| 7.3.1 | Tokens solo de la página actual | Enviar a orderbook-metrics **solo** los `primary` (o primary_yes) de `data.markets` de la respuesta actual; sin `slice(0, 100)`. Tope = `list.length` (p. ej. 25). **Request key:** no re-pedir metrics si `metrics_key` no cambió (ver Riesgos 7.1). |
| 7.3.2 | Máximo por request | Backend ya limita (ej. 100). Frontend no debe pedir más de `limit` de la página. **AbortController para metrics:** obligatorio; al cambiar offset/filtros, abortar request de metrics en curso e invalidar UI (mostrar loading/—). Ver Riesgos 7.2. |

**Definition of Done:** Cada carga de página = 1 GET /markets (limit, offset, filtros) + 1 GET /markets/orderbook-metrics con ≤ limit tokens.

---

## Fase 7.4: UX navegable (NICE)

| # | Tarea | Instrucción |
|---|-------|-------------|
| 7.4.1 | Selector de tamaño de página | Escape hatch: dropdown “25 / 50 por página” (o 20/25/50) que actualice `limit` y resetee `offset` a 0. Default vía `NEXT_PUBLIC_MARKETS_PAGE_SIZE`. |
| 7.4.2 | Virtualización | Si en el futuro se sube el limit (p. ej. 50) y se nota lag, considerar virtual scroll (solo renderizar filas visibles). Para limit 20–25 no es prioritario. |
| 7.4.3 | Indicador de carga por página | Al cambiar de página (Prev/Next), mostrar skeleton o indicador en la tabla hasta que llegue la nueva respuesta; no dejar la tabla vacía sin feedback. |

---

## Resumen de llamadas (objetivo)

| Acción | Llamadas |
|--------|----------|
| Carga inicial (p. ej. página 1) | 1× GET /markets (limit=25, offset=0, filtros) + 1× GET /markets/orderbook-metrics (≤25 token_ids) |
| Cambiar de página (Siguiente) | 1× GET /markets (limit=25, offset=25, …) + 1× GET /markets/orderbook-metrics (≤25 token_ids) |
| Cambiar filtro (categoría, series, etc.) | offset=0; 1× GET /markets + 1× orderbook-metrics |
| Volver a la pestaña | 1× refetch (misma página actual) |
| Pulsar “Actualizar” | 1× refetch (misma página actual) |

No hay polling en background cada 30s.

---

## Riesgos y Footguns (Parte 7)

| # | Riesgo | Mitigación concreta (spec-level) |
|---|--------|----------------------------------|
| **7.1** | **Doble-fetch markets + metrics (refetch en cascada)** | Un refetch (visibilidad o botón) dispara GET /markets y luego metrics; si metrics tiene refresh propio o estado intermedio, pueden duplicarse llamadas. **Regla:** “metrics solo se pide cuando existe una respuesta de markets **estable** (misma offset, limit, filtros que la vista) y la pestaña está visible”. **Request key:** `metrics_key = hash(strategy_id + offset + limit + filtros + list(primary_token_ids))`. Si no cambia, no re-pedir metrics. Integrar en el mismo fetch que markets (una “carga” atómica) o comparar key antes de disparar metrics. |
| **7.2** | **Race conditions al cambiar filtros/página rápido** | Respuestas fuera de orden → se pintan métricas de la página anterior en la nueva. **AbortController obligatorio también para metrics** (no solo para markets). Al cambiar offset o filtros: invalidar inmediatamente metrics en UI (mostrar “loading” o “—”) y abortar request de metrics en curso. Descartar respuestas cuyo `offset/limit/filtros` no coincidan con el estado actual de la vista. |
| **7.3** | **visibilitychange spam / flapping** | En algunos entornos (tabs, PWAs, devtools) el evento se dispara varias veces → ráfagas de refetch. **Debounce:** no más de 1 refetch cada 3–5 s. **Throttle por tiempo:** solo refetch si `lastFetchedAt` hace > 15–30 s (evitar “alt-tab spam”). |
| **7.4** | **Tamaño de página 20 vs UX (más clics)** | 20 puede sentirse corto si el usuario explora mucho. **Mitigación:** default **25** (compromiso). Selector de tamaño (7.4.1) como escape hatch desde ya; configurable por env `NEXT_PUBLIC_MARKETS_PAGE_SIZE`. |
| **7.5** | **Metrics “no decision critical” pero “UX critical”** | Sin polling, la tabla puede parecer “muerta” si spreads/depth cambian. **Mitigación:** Mostrar “Actualizado hace X s” (Updated Xs ago) y botón Refresh evidente. Intervalo largo solo con pestaña visible (2–5 min): **detrás de flag** (ej. env) para no reintroducir el problema; NICE. |

---

## Plan de validación (Parte 7)

### Métricas de producto / performance

| Métrica | Antes (referencia) | Después (objetivo) |
|--------|---------------------|--------------------|
| Llamadas por minuto por usuario en /markets y /markets/orderbook-metrics | ~2 calls/min siempre (polling 30 s) × usuarios | ~0 en background; solo “on load / on tab return / on manual” |
| P95 latencia de carga de página | — | Tiempo desde navegación hasta tabla con datos + metrics; medir y no degradar |
| Errores 429/503 en orderbook-metrics | — | Deberían bajar proporcionalmente al reducir llamadas |

### Tests funcionales mínimos

| Caso | Criterio de aceptación |
|------|------------------------|
| Cambiar filtro | offset=0 → **como máximo** 1 llamada GET /markets + 1 llamada orderbook-metrics (sin duplicados en cascada). |
| Next page | 1× GET /markets + 1× orderbook-metrics; no concatenar datos de páginas. |
| Alt-tab (volver a la pestaña) | Máximo 1 refetch (debounced/throttled); no ráfaga. |
| Cambios rápidos (filtro + next + back) | Nunca se pintan métricas “cruzadas” (métricas de página/filtro anterior en la vista actual). AbortController + invalidación de UI. |

---

## Rollback

- Si el refetch por visibility causa problemas: desactivar listener `visibilitychange` y dejar solo el botón “Actualizar”.
- Si limit 25 es demasiado pequeño: subir a 30 o usar selector de página (7.4.1); mantener principio “una página a la vez”.
