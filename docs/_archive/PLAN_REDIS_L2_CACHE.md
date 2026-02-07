# Plan: Redis L2 cache institucional (SWR + singleflight)

**Versión:** 1.0  
**Objetivo:** Implementar Redis como L2 cache para discovery y metadatos, con Stale-While-Revalidate (SWR), singleflight anti-stampede, canonicalización de queries y fallback limpio. Redis **no** es decision-critical.

**Contexto (ya implementado):**
- `/markets` gamma-first (array + headers), merge enabled, two-phase paging, orderbook-metrics con partials, circuit breaker, rate limit.
- `CacheProvider` con `InMemoryCacheProvider` e inyección en `markets.py` (o equivalente).
- Parte 7 frontend: page size 25, no polling 30s, visibility refetch throttled, metrics solo visibles.

**Referencias:**
- [PLAN_MEJORA_MARKETS_PAGE.md](./PLAN_MEJORA_MARKETS_PAGE.md)
- `backend/app/core/cache_provider.py`, `backend/app/api/markets.py`

---

# 0) Reglas duras

| Regla | Descripción |
|-------|-------------|
| Contrato inalterado | `/markets` devuelve **array** y headers (X-Limit, X-Offset, X-Has-More, etc.). Nada de envelope en body. |
| Fuente de verdad | DB sigue siendo fuente de verdad para **MarketEnabledState** y universos. Redis solo discovery/UI. |
| Fallback obligatorio | Si Redis falla: degradar a L1 in-memory y/o fetch Gamma (respetando breaker); **nunca** bloquear el request. |
| Sin regresiones UX | No reintroducir polling agresivo ni "load all". Mantener Parte 7 (paginación, refetch por visibilidad). |

---

# 1) Infra / Config: Redis toggle, timeouts, observabilidad

## Objetivo

Configuración runtime para Redis L2: toggle, URL, timeouts, prefijo y cliente con timeouts estrictos, reconexión razonable y sin retries agresivos. Logging y métricas para hit/miss, errores y lock contention.

## Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 1.1 | CACHE_PROVIDER | MUST | Añadir `CACHE_PROVIDER=memory|redis` (default `memory` si no configurado). Si `memory`, usar solo `InMemoryCacheProvider`; si `redis`, usar `RedisCacheProvider` (L2) con fallback a memory si Redis no disponible. |
| 1.2 | REDIS_* | MUST | Variables: `REDIS_URL` (o host/port separados), `REDIS_TLS=true` si aplica, `REDIS_TIMEOUT_MS` (50–150 ms), `REDIS_KEY_PREFIX` (ej. `poly:`). Documentar en `.env.example`. |
| 1.3 | Cliente Redis | MUST | Cliente con timeouts estrictos por operación, reconexión razonable, **no** retries agresivos (evitar tormentas). Reutilizar/adaptar `backend/app/core/redis_client.py` si existe. |
| 1.4 | Logging | MUST | Log: cache hit/miss/stale-served, redis errors/timeouts, lock contention (singleflight), gamma fetch count por request. Estructurado (JSON o campos fijos) para agregación. |
| 1.5 | Arranque | MUST | Con `CACHE_PROVIDER=redis` y Redis no disponible: app arranca igual, usa fallback a memory y loguea **warnings** (no fallar startup). |

## Acceptance

- App arranca con `CACHE_PROVIDER=redis`; si Redis no está disponible, sigue funcionando (fallback a memory) y loguea warnings.
- Timeouts de Redis respetados; no bloqueos en request path.

---

# 2) CacheProvider: RedisCacheProvider + SWR

## Objetivo

Implementar `RedisCacheProvider` con formato SWR en Redis y **API interna explícita** para que el endpoint sepa si debe disparar refresh, setear headers (X-Cache: stale, etc.) o evitar doble-refresh. La interfaz pública puede mantener `get()` para compatibilidad; la lógica de decisión usa **get_with_meta()**.

## 2.1 Formato de value en Redis (SWR)

Guardar en Redis un JSON con:

- `payload`: respuesta cacheada (lista markets, tags, series, etc.).
- `fetched_at_ms`: timestamp absoluto (ms) de cuándo se obtuvo.
- `soft_expiry_ms`: timestamp absoluto (ms) hasta cuándo se considera FRESH.
- `hard_expiry_ms`: timestamp absoluto (ms) hasta cuándo se puede servir STALE.

**Redis TTL:** usar **segundos relativos**: `hard_ttl_seconds = (hard_expiry_ms - now_ms) / 1000` al escribir, o equivalente (ej. `stale_grace_seconds` fijo). Así se evita confusión ms vs seconds y absoluto vs relativo: dentro del payload todo en ms absolutos; en Redis, SETEX con TTL en segundos.

## 2.2 API interna: get_with_meta() (P0 — decisión explícita)

Para que el endpoint decida sin ambigüedad:

- **Nueva API:** `get_with_meta(key) -> Optional[CacheHit]`, donde:
  - `CacheHit` es un dataclass/tipo con: `payload`, `status` (literal `"fresh"` | `"stale"`), `fetched_at_ms`, `soft_expiry_ms`, `hard_expiry_ms`.
  - Si no existe key o `now >= hard_expiry_ms` → devolver `None` (miss).
  - Si `now < soft_expiry_ms` → devolver `CacheHit(..., status="fresh")`.
  - Si `soft_expiry_ms <= now < hard_expiry_ms` → devolver `CacheHit(..., status="stale")`.

El **endpoint** (p. ej. GET /markets) usa `get_with_meta()` y según `status`:
- **fresh** → devolver payload, setear X-Cache: hit, no disparar refresh.
- **stale** → devolver payload, setear X-Cache: stale; intentar adquirir lock y, si se adquiere, hacer **refresh síncrono** en ese request (ver sección 3); si no se adquiere, solo servir stale.
- **miss** → seguir flujo miss (breaker, fetch Gamma, etc.).

Así se evita cascada de refreshes y el endpoint tiene control total sobre headers y singleflight.

## 2.3 Semántica set()

- `soft_ttl_seconds` configurable por tipo de dato (markets vs tags/series).
- `hard_ttl_seconds = soft_ttl_seconds + stale_grace_seconds` (ej. +30s o +60s).
- Calcular `soft_expiry_ms = now_ms + soft_ttl_seconds * 1000`, `hard_expiry_ms = now_ms + hard_ttl_seconds * 1000`.
- Escribir en Redis el JSON: `payload`, `fetched_at_ms`, `soft_expiry_ms`, `hard_expiry_ms`.
- Redis `SETEX` con TTL = `hard_ttl_seconds` (segundos relativos).

## 2.4 Coherencia L1 / L2 (P1)

- **L1** guarda el **mismo envelope SWR** que L2: al menos `payload`, `fetched_at_ms`, `soft_expiry_ms`, `hard_expiry_ms` (o equivalente para comparar freshness).
- **En L2 hit** (fresh o stale) → **siempre poblar L1** con ese valor, para que lecturas posteriores en la misma instancia puedan usar L1 sin desvío por relojes distintos.
- Así se evitan estados inconsistentes (L1 “fresh” y L2 “stale” por clocks) y el debug es predecible.

## Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 2.1 | RedisCacheProvider class | MUST | Implementar clase con `get_with_meta(key) -> Optional[CacheHit]` (payload, status, fetched_at_ms, soft_expiry_ms, hard_expiry_ms) y `set(key, value, ttl_seconds)`, opcional `delete(key)`. Opcionalmente mantener `get(key) -> Optional[Any]` como conveniencia (devuelve payload si hit). |
| 2.2 | get_with_meta() SWR | MUST | Si existe y `now < soft_expiry_ms` → CacheHit(status="fresh"); si `soft_expiry_ms <= now < hard_expiry_ms` → CacheHit(status="stale"); si `now >= hard_expiry_ms` o no existe → None. |
| 2.3 | set() SWR | MUST | Recibir soft_ttl_seconds; hard_ttl_seconds = soft + stale_grace. Guardar JSON con payload, fetched_at_ms, soft_expiry_ms, hard_expiry_ms (absolutos en ms). Redis SETEX con TTL = hard_ttl_seconds (relativo, segundos). |
| 2.4 | L1/L2 coherency | MUST | L1 almacena mismo envelope SWR (payload + expiries). En cualquier L2 hit (fresh o stale), popular L1 con ese valor. |
| 2.5 | Unit tests provider | MUST | Tests: fresh hit, stale hit, hard-expired → miss, redis down → None (graceful). |

## Acceptance

- Unit tests del provider: fresh hit, stale hit, hard-expired → miss, redis down → None sin excepción.
- Endpoint puede decidir refresh y headers usando solo `get_with_meta()`.

---

# 3) Singleflight / Anti-stampede (MUST)

## Objetivo

Un solo refresco a Gamma (o fuente) por key cuando muchas requests coinciden tras soft-expiry. El **refresh es síncrono** en el request que adquiere el lock; el resto sirve stale (no hay “background” a menos que se añada un worker explícito más adelante).

## Mecánica

- Lock por key en Redis: `lock:{key}` con `SET NX PX <ms>`.
- **Lock TTL (P0):** El timeout overall de Gamma es ~5 s. Si el lock PX fuera 3–5 s, podría expirar antes de que termine el refresh → dos refreshers y doble llamada a Gamma (riesgo 429). **Definir:** `lock_px_ms = gamma_overall_timeout_ms + margen` (ej. **8–10 s**). NICE: extensión de lock (renovar PX cada X ms mientras se refresca) para refreshes muy lentos.
- Solo el request que **adquiere** el lock hace el refresh a Gamma **síncronamente** (dentro del mismo request); al terminar, set cache (L1+L2) y liberar lock (DELETE).
- Los demás requests: si tienen **stale** disponible → servir stale inmediato; si no hay stale → según diseño (esperar poco al lock holder o ir a Gamma con breaker; idealmente evitar muchas llamadas).

## Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 3.1 | Lock Redis | MUST | Lock `lock:{key}` SET NX PX con **8–10 s** (gamma_overall_timeout + margen). Liberar (DELETE) al terminar refresh. NICE: lock extension (renovar PX) si el refresh tarda más. |
| 3.2 | Refresh síncrono | MUST | El request que adquiere el lock ejecuta el refresh **síncronamente** (fetch Gamma, set cache, liberar lock). No asumir “background”; si en el futuro se quiere worker en background, definirlo como NICE aparte. |
| 3.3 | Integrar en flujo | MUST | Endpoint con get_with_meta: si status=stale o miss, intentar adquirir lock; si se adquiere → fetch, set, liberar; si no → devolver stale si existe, si no flujo miss (breaker / Gamma). |
| 3.4 | Test concurrencia | MUST | ~20 requests simultáneas a la misma key tras soft-expiry → **1 solo** refresh a Gamma, resto sirve stale. |

## Acceptance

- 20 requests simultáneas al mismo key tras soft-expiry ⇒ 1 solo refresh a Gamma, resto sirve stale.
- Lock no expira antes de que el refresh típico termine (PX ≥ 8–10 s).

---

# 4) Canonical Query Normalization (MUST) para keys de /markets

## Objetivo

Una única función que normalice los query params de /markets para producir un string canónico y estable, y de ahí un hash (ej. SHA256) para la key de cache. Mismas queries con distinto orden en arrays ⇒ misma key.

## Función `canonicalize_markets_query(params)`

- Aplicar **defaults** (limit, offset, order, ascending, closed, …).
- Normalizar **booleans** (true/false, 1/0 → string consistente).
- **Dedupe + sort** en arrays: `id[]`, `slug[]`, `clob_token_ids[]`.
- Eliminar params vacíos/null.
- Normalizar rangos min/max (liquidity_num_min/max, volume_num_min/max, start_date_min/max, end_date_min/max).
- Producir string canónico **determinístico** (ej. query string ordenado) y luego **hash** (SHA256).
- **No** incluir headers transitorios ni campos derivados; solo params que afectan la respuesta Gamma.

Key final: `{REDIS_KEY_PREFIX}gamma:markets:q:{sha256(canonical)}`.

## Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 4.1 | canonicalize_markets_query | MUST | Implementar en módulo compartido (ej. `core/cache_keys.py` o dentro de `markets.py`). Input: dict/params; output: string canónico (o hash directo). |
| 4.2 | Integrar en markets | MUST | Sustituir o complementar `_build_gamma_cache_key` con key derivada de `canonicalize_markets_query` + prefijo. Mantener compatibilidad con L1 si la key antigua se sigue usando en memoria durante transición. |
| 4.3 | Tests canonical | MUST | Tests: mismas queries con orden distinto en arrays ⇒ mismo hash/key. Params con defaults aplicados ⇒ mismo key que request explícito con esos defaults. |

## Acceptance

- Mismas queries con orden distinto en arrays ⇒ mismo key.
- Params equivalentes (incl. defaults) ⇒ mismo key.

---

# 5) Qué cachear (L2) y TTL policies

## 5.1 GET /markets (Gamma proxy) — buckets deterministas (P0)

- **Key:** `gamma:markets:q:{hash(canonical)}` (con prefijo global).
- **Valor:** Respuesta raw de Gamma (lista) en formato SWR.

**Reglas de bucket (deterministas, testeables):**

| Bucket | Condición | soft_ttl | hard_ttl |
|--------|-----------|----------|----------|
| **search** | Parámetro `search` existe (cualquier valor). | No cachear en v1 (ver 5.3). | — |
| **narrow** | `id[]` o `slug[]` presentes con length ≤ 20, **o** `clob_token_ids[]` con length ≤ 20. | 300 s | soft + 60 s |
| **broad** | Resto: no hay arrays de ítems específicos; filtros “comunes” (tag_id, closed, order, ascending, limit, offset, etc.). | 90 s | soft + 60 s |

- **search:** en v1 **no cachear** (evita cardinalidad y entropía). Si en el futuro se cachea, usar heurística explícita (ej. 5.3 alternativa).

## 5.2 GET /tags y GET /series

- **Keys:** `gamma:tags:all`, `gamma:series:all` (con prefijo) **solo si los endpoints no aceptan params** (listado completo sin limit/offset/search). Si los endpoints tienen params (limit, offset, búsqueda), o se aplica **canonicalization** análoga a markets y la key incluye el hash, o se fija “solo llamamos al endpoint unfiltered” y se cachea una sola key. Especificar en implementación cuál es el contrato actual de /tags y /series.
- **soft_ttl:** 1–6 h (ej. 3600 s).
- **hard_ttl:** soft + 10–30 min (ej. +600 s).

## 5.3 Search y cardinalidad (P2)

- **v1:** **No cachear** requests que incluyan el parámetro `search`. Así se evita definir “entropía” y se controla cardinalidad.
- Alternativa documentada (si más adelante se cachea search): no cachear si `len(search) > 64` o si >30 % de caracteres no alfanuméricos; o TTL ≤ 30 s.

## Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 5.1 | TTL markets por bucket | MUST | Aplicar soft/hard según bucket (broad 90s + 60s stale, narrow 300s + 60s, search no cachear en v1). |
| 5.2 | TTL tags/series | MUST | Cachear con soft 1–6 h, hard = soft + 10–30 min. Especificar si endpoints son no-param (keys `*:all`) o con params (canonicalization). |
| 5.3 | Search v1 | MUST | Si existe param `search` → no cachear en v1. Documentar alternativa (longitud/entropía) para futuro. |

## Acceptance

- Buckets deterministas: mismas params ⇒ mismo bucket y TTL.
- Redis no crece por search en v1 (no cachear search).

---

# 6) Integración en endpoints existentes

## 6.1 GET /markets

Flujo final (usando **get_with_meta** para decisión explícita):

1. Construir **canonical key** (canonicalize_markets_query + hash).
2. Intentar **L1** con get_with_meta (si el provider expone L1 igual); luego **L2 Redis** con get_with_meta.
3. Si **fresh hit** (status=fresh) → devolver payload, merge enabled en runtime, headers X-Cache: hit; **no** disparar refresh.
4. Si **stale hit** (status=stale) → devolver payload, merge enabled, headers X-Cache: stale; intentar adquirir lock; **si se adquiere**, hacer refresh **síncrono** en este request (fetch Gamma, set L1+L2, liberar lock); si no se adquiere, solo servir stale.
5. Si **miss** (get_with_meta → None):
   - Si breaker **OPEN** → **solo si existía una key (teníamos stale en algún momento)** devolver ese stale; si no había key, **503** sin llamar a Gamma. (P1: “stale only if key existed”; evita UX random.)
   - Si breaker **CLOSED** → fetch Gamma, set cache (L1+L2), devolver.
   - NICE: “last-known-good” global para query broad por defecto (evitar 503 en homepage cuando breaker abre y no hay key); decisión de producto.

**Importante:** Merge **enabled** se hace siempre en runtime (DB); no cachear enabled en la key.

## 6.2 GET /tags y GET /series

- Si los endpoints **no tienen params** (solo devuelven listado completo): keys `gamma:tags:all`, `gamma:series:all`; cache first (L2), SWR + singleflight, TTL largo.
- Si **tienen params** (limit, offset, search): aplicar **canonicalization** análoga a markets y key con hash, o fijar que solo se llama al endpoint unfiltered y se cachea una sola key. Especificar en implementación.
- En miss o stale: fetch fuente, set cache, devolver.

## 6.3 gamma_supported_order_fields

- Si existe cache in-memory hoy, extender a Redis para coherencia multi-pod.
- Key: `gamma:supported_order_fields` (con prefijo).
- TTL: 1–6 h.

## Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 6.1 | Flujo /markets | MUST | Integrar en `get_markets`: key canónica; L1/L2 vía get_with_meta; según status (fresh/stale/miss) devolver payload, setear X-Cache, y en stale/miss singleflight (refresh síncrono si lock); breaker OPEN → stale solo si key existía, si no 503. Merge enabled en runtime. |
| 6.2 | Flujo /tags, /series | MUST | Cache first L2, SWR + singleflight, TTL largo. |
| 6.3 | supported_order_fields | NICE | Cachear en Redis con TTL 1–6 h para coherencia multi-pod. |

## Acceptance

- GET /markets con Redis: miss → fetch Gamma → set cache; fresh hit sin llamar Gamma; stale hit servido + 1 refresh síncrono (el request que tiene el lock).
- Breaker OPEN: se sirve stale **solo si la key existía** (había valor cacheado); si no existía key → 503.
- Merge enabled no depende del cache key.

---

# 7) Circuit breaker global (Redis-backed)

## Objetivo

Estado del circuit breaker compartido entre pods vía Redis: contador de fallos/429 por ventana, estado OPEN con TTL, transiciones logueadas. Cuando OPEN, /markets sirve stale **solo si la key existía** (había valor cacheado); si no → 503 rápido.

## Mecánica

- Contador de fallos/429 por ventana (ej. 60 s) en Redis.
- Estado OPEN con TTL (ej. 60 s) en Redis.
- Transiciones (OPEN/CLOSED) logueadas.
- Con 2 pods: si uno abre el breaker, el otro lo respeta leyendo estado desde Redis.

## Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 7.1 | Breaker state en Redis | MUST | Guardar en Redis: contador fallos por ventana, estado OPEN con TTL. Leer antes de llamar a Gamma. |
| 7.2 | Transiciones | MUST | Al abrir/cerrar: escribir en Redis y loguear. |
| 7.3 | /markets con breaker OPEN | MUST | Si OPEN: servir stale **solo si la key existía** (había valor en cache); si no existía key → 503 sin llamar Gamma. |

## Acceptance

- Con 2 pods, si uno abre el breaker, el otro también lo respeta (estado en Redis).

---

# 8) Observabilidad + headers

## Headers opcionales (NICE)

Para depurar sin cambiar contrato:

- `X-Cache`: hit | miss | stale
- `X-Cache-Provider`: memory | redis
- `X-Cache-Key`: valor corto. **Solo enviar si `DEBUG_CACHE_HEADERS=true`**; en prod **nunca** por defecto (evitar filtrado de información útil para atacantes / replay). (P1)
- `X-Cache-Age`: segundos desde fetched_at
- `X-Cache-Refresh`: 0 | 1 (si esta request disparó refresh)

## Log estructurado

Incluir: key hash, bucket TTL, fresh/stale, redis latency, gamma latency, breaker state.

## Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 8.1 | Headers | NICE | Añadir headers anteriores en GET /markets (y opcionalmente /tags, /series). X-Cache-Key solo si DEBUG_CACHE_HEADERS=true; nunca en prod por defecto. |
| 8.2 | Log | MUST | Log estructurado (key hash, bucket, fresh/stale, redis_latency_ms, gamma_latency_ms, breaker_state). |

---

# 9) Tests

## Unit

- Canonicalización: mismas queries ⇒ mismo hash; defaults aplicados.
- RedisCacheProvider: fresh hit, stale hit, hard-expired → miss, redis down → None.
- Lock: adquisición y liberación; no doble refresh para misma key.

## Integration

- GET /markets con Redis:
  - miss → fetch Gamma → set cache.
  - fresh hit.
  - stale hit servido + singleflight refresh.
  - redis down → fallback (L1 o Gamma con breaker).
  - breaker open → sirve stale o 503 sin Gamma.
- Load-ish (si hay harness): ~20 concurrentes misma key → 1 llamada Gamma.

## Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 9.1 | Unit | MUST | Tests para canonicalize, RedisCacheProvider SWR, lock. |
| 9.2 | Integration | MUST | Tests /markets con Redis: miss, fresh, stale, redis down, breaker open. |
| 9.3 | Concurrencia | NICE | 20 requests simultáneas misma key → 1 Gamma call. |

---

# 10) Rollout seguro

## Config y feature flag

- `CACHE_PROVIDER=memory|redis` (ya en sección 1).
- NICE: “shadow mode” — leer Redis y medir hit-rate pero no usar resultado para servir (solo métricas).

## Dashboards mínimos

- Hit-rate (hit / miss / stale).
- Gamma QPS.
- Redis latency (p50, p99).
- Breaker open rate.

## Runbook

- **Redis down:** fallback a memory; verificar logs y que no hay bloqueos.
- **Gamma 429 spike:** breaker abre; servir stale o 503; revisar límites y TTLs.
- **Stampede suspected:** revisar singleflight y lock contention en logs; ajustar PX del lock si hace falta.

## Tareas

| # | Tarea | Tipo | Instrucción |
|---|-------|------|-------------|
| 10.1 | Shadow mode | NICE | Modo en que se lee Redis y se registra hit-rate pero la respuesta se obtiene como si fuera miss. |
| 10.2 | Dashboards | NICE | Hit-rate, Gamma QPS, redis latency, breaker open rate. |
| 10.3 | Runbook | MUST | Documentar: Redis down, Gamma 429 spike, Stampede suspected. |

---

# Dependencias y orden sugerido

```
1) Infra/Config
    → 2) RedisCacheProvider + SWR
        → 3) Singleflight
            → 4) Canonicalization
                → 5) TTL policies
                    → 6) Integración endpoints
                        → 7) Breaker Redis-backed
8) Observabilidad (paralelo desde 6)
9) Tests (por fases)
10) Rollout (al final)
```

- 4 y 5 pueden solaparse. 6 depende de 2, 3, 4, 5. 7 puede hacerse en paralelo con 6 una vez Redis está en uso.

---

# Deliverable final

- **PR** con: RedisCacheProvider + SWR + get_with_meta, canonicalize_markets_query, singleflight (lock 8–10 s, refresh síncrono), integración GET /markets (y opcional /tags, /series), circuit breaker Redis-backed, tests (unit + integration), docs actualizadas (`docs/api/markets.md` y este plan).

---

# Referencia rápida: variables de entorno

| Variable | Default | Uso |
|----------|---------|-----|
| `CACHE_PROVIDER` | `memory` | `memory` \| `redis` |
| `REDIS_URL` | — | URL Redis (TCP) |
| `REDIS_TLS` | — | `true` si TLS |
| `REDIS_TIMEOUT_MS` | 50–150 | Timeout por operación (ms) |
| `REDIS_KEY_PREFIX` | `poly:` | Prefijo keys (evitar colisiones) |
| `DEBUG_CACHE_HEADERS` | `false` | Si `true`, incluir X-Cache-Key en respuestas; **nunca en prod** por defecto. |
