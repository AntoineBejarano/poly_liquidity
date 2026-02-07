# Plan: Discovery, Universe y Strategy Builder

**Objetivo:** En la pantalla de una estrategia, el usuario puede explorar y filtrar dinámicamente por categorías/tags, markets, events y ventana temporal (UPCOMING/ACTIVE, próximos X días, time-to-resolution). Todo cache-first y de baja latencia; enabled global operativo; Universe por Strategy declarativo con auto-attach opcional; respeto a rate limits Gamma vía scanner/refresh jobs.

**Referencia de flujo actual:** [MERCADOS_POLYMARKET_FLUJO.md](./MERCADOS_POLYMARKET_FLUJO.md).

---

## 1. Auditoría del estado actual

### A. Discovery & data sources

| Aspecto | What it does today | Files/Paths | Gaps vs target |
|--------|---------------------|-------------|-----------------|
| **Llamadas a Gamma** | `GET /markets` (paginado hasta ~500), `GET /events`, `GET /series`. Scanner usa `/events`, `/markets`, `/series` con paginación configurable. | `backend/app/api/markets.py` (list_markets), `backend/app/core/scanner/scanner.py` (fetch_events, fetch_markets, fetch_series) | No hay un “Directory” unificado cache-first; cada endpoint decide si cache o Gamma. |
| **Paginación** | Markets: varias páginas (limit 100, offset N, max páginas configurable). Events en scanner: acumulación por páginas. `GET /markets/events/list` devuelve **limit 100** fijo, sin offset. | `backend/app/api/markets.py` (loop offset), `backend/app/core/scanner/scanner.py` (scanner_pagination_limit, scanner_max_pages), `backend/app/api/markets.py` get_events (`.limit(100)`) | Events list sin paginación server-side; sin “max pages” explícito en API para el cliente. |
| **Persistencia DB** | Event, Market, Tag, Series; StrategyEvent (strategy_id, event_id); MarketEnabledState (polymarket_market_id, enabled). | `backend/app/models/` (event, market, strategy_event, strategy con universe_config JSONB), migración `2026_01_28_1500-add_universe_config_to_strategies.py` | Falta modelo/índice explícito para “enabled global” (hoy es MarketEnabledState por market). Time-to-resolution no persistido como campo. |
| **Redis/cache** | Cache en memoria (`APICache`), no Redis. Keys por tipo (market_list, event_data, etc.). TTL ~30–60 s para listas. | `backend/app/core/api_cache.py`, uso en `markets.py`, `scanner.py`, `polymarket.py`, `dashboard.py` | No Redis; no índices por categoría/tag/ventana temporal listos para filtrar; no `last_scanned_at` expuesto. |
| **Listar markets** | `GET /markets` con query: category, search, enabled, tag_id, series_id. Filtros aplicados en backend sobre lista obtenida de Gamma (+ cache). | `backend/app/api/markets.py` | Falta filtro por ventana temporal (próximos X días); enabled es por nuestra DB. |
| **Listar events** | `GET /markets/events/list?market_id=&state=`. Lee Event+Market de DB. state=UPCOMING\|ACTIVE\|FINISHED. limit 100. | `backend/app/api/markets.py` get_events | Sin paginación; sin filtros por categoría/tag/tiempo (next N days, time-to-resolution); sin “enabled global” aplicado en el listado. |
| **Asignar/desasignar events** | POST/DELETE para añadir/quitar event a estrategia. Persiste StrategyEvent. | `backend/app/api/strategies.py` (add/remove event endpoints) | OK; falta validar que el event esté en “enabled global”. |
| **Toggle enabled market** | `PATCH /markets/{polymarket_market_id}/enable`. Actualiza MarketEnabledState. | `backend/app/api/markets.py` | OK; falta concepto “enabled global” documentado y aplicado en todos los listados. |

### B. Strategy assignment

| Aspecto | What it does today | Files/Paths | Gaps vs target |
|--------|---------------------|-------------|-----------------|
| **Relación Strategy↔Event** | `StrategyEvent(strategy_id, event_id)` con timestamps. | `backend/app/models/strategy_event.py`, `backend/app/models/strategy.py` (relationship strategy_events) | OK. |
| **Universe** | `Strategy.universe_config` (JSONB): categories, markets, tags, auto_attach, deny_list. Sin events[] ni time_filter. | `backend/app/models/strategy.py` (universe_config), `backend/app/api/strategies.py` (UniverseConfig Pydantic, GET/PUT universe) | Falta events[], time_filter (UPCOMING/ACTIVE, next X days, max_time_to_resolution_minutes). Precedencia enabled global > deny_list > universe no documentada ni aplicada de forma centralizada. |
| **Auto-attach** | Cada ~100 ticks del control loop se llama `_check_and_auto_attach_events`: estrategias con auto_attach=True; filtra Event por universe (categories, markets, tags); crea StrategyEvent si no existe. | `backend/app/core/strategy_engine/control_loop.py` (_check_and_auto_attach_events, uso de universe_config) | No usa time_filter; no hay límite max events/strategy ni rate de attaches/hora; no se comprueba “enabled global” de forma explícita antes de asignar. |

### C. Latency & rate limiting

| Aspecto | What it does today | Files/Paths | Gaps vs target |
|--------|---------------------|-------------|-----------------|
| **Rate limiter** | Sliding window por EndpointType (GAMMA_*, CLOB_*, DATA_API, etc.). wait_for_capacity(timeout), record_violation. | `backend/app/core/rate_limiter.py` (EndpointType, RateLimiter), uso en markets.py, scanner.py, execution, polymarket_adapter | OK; falta documentar límites exactos por endpoint en un solo sitio. |
| **Caching para Gamma** | api_cache.get/set con TTL (market_list ~30s, event_data ~60s). Cache key por parámetros. | `backend/app/core/api_cache.py`, `backend/app/api/markets.py`, `backend/app/core/scanner/scanner.py` | In-memory solo; no Redis; no “Directory” pre-indexado. |
| **Fallback 429/timeout** | Si wait_for_capacity False se usa cache si existe; si no, se devuelve error. record_violation bloquea alternativa. | Mismo uso en markets y scanner | No hay fallback “stale-ok” explícito (devolver último conocido con aviso). |

### D. Frontend

| Aspecto | What it does today | Files/Paths | Gaps vs target |
|--------|---------------------|-------------|-----------------|
| **Pantalla asignar events** | Desk de estrategia: lista de eventos (ACTIVE/FINISHED), asignados vs disponibles; añadir/quitar. | `frontend/app/strategies/[id]/desk/page.tsx` | No hay exploración por categorías/tags/markets primero; no filtros temporales ni time-to-resolution. |
| **Datos** | `GET /strategies/{id}/events`, `GET /markets/events/list?state=ACTIVE` y `?state=FINISHED`. Filtrado adicional en cliente. | `frontend/app/strategies/[id]/desk/page.tsx`, `frontend/lib/api.ts` | Sin filtros server-side por categoría/tag/ventana; sin paginación/infinite scroll. |
| **Diseño** | Componentes UI (shadcn-style), Tailwind, formularios. | `frontend/components/`, `frontend/app/`, tailwind.config.ts | Falta flujo por pasos (Categories → Markets → Events), chips de filtros, freshness, diseño minimalista tipo ChatGPT/Google. |

---

## 2. Target design

### A. Data layer (Directory)

- **Directory API** (cache-first): capa de lectura que sirve categories, tags, markets, events desde **Redis + DB**, nunca llamando a Gamma en la petición del usuario.
- **Scanner/refresh job** (existente o ampliado) alimenta:
  - Redis: índices por category, tag, market_id, state, y si se quiere por ventana temporal (bucket por día o time-to-resolution).
  - Campos necesarios para filtros temporales: en Event (o en índice) `start_time`, `end_time`, y/o `time_to_resolution_minutes` (calculado), `state`.
- **last_scanned_at** guardado y expuesto (ej. en GET /directory/meta o en cabecera) para que la UI muestre “freshness”.
- Endpoints de lectura ej.:  
  `GET /directory/categories`, `GET /directory/tags`,  
  `GET /directory/markets?category=&tag=&search=&enabled=&state=&next_days=&limit=&offset=`,  
  `GET /directory/events?market_id=&state=&category=&tag=&next_days=&max_time_to_resolution=&limit=&offset=`.  
  Todos leen de Redis/DB; si Redis está vacío, se puede leer solo de DB y marcar “stale”.

### B. Universe per strategy (schema conceptual)

- **Selectores:**  
  `categories[]`, `tags[]`, `markets[]` (polymarket_market_id), `events[]` (opcional, IDs concretos), `deny_list[]` (market/event IDs excluidos), `auto_attach` (bool).
- **time_filter (objeto):**  
  - `window`: `UPCOMING` | `ACTIVE` | `ANY`  
  - `next_days`: número (próximos N días desde ahora)  
  - `max_time_to_resolution_minutes`: número (solo events con time-to-resolution ≤ este valor)  
  (Todos opcionales; si no se envían, sin filtro temporal.)
- **Precedencia:**  
  1) **Enabled global:** si el market no está en la allowlist operacional (enabled), el event no es elegible.  
  2) **deny_list:** si el market/event está en deny_list, excluido.  
  3) **Selectores positivos:** categories/tags/markets/events y time_filter definen el conjunto elegible. (Intersección de lo que cumple cada uno si está presente.)
- **Persistencia:** `universe_config` JSONB actual con estos campos añadidos/ajustados; sin cambios de modelo relacional estrictamente necesarios si se mantiene flexible.

### C. Control loop integration

- Si `auto_attach=true`, en el tick correspondiente:
  - Obtener candidatos del **Directory** (no Gamma) aplicando Universe (categories, tags, markets, time_filter, deny_list) y **enabled global**.
  - Para cada event elegible que aún no tenga StrategyEvent: crear StrategyEvent y, si aplica, suscribir orderbooks.
- **Límites operativos:**  
  - `max_events_per_strategy` (ej. 50).  
  - `max_auto_attaches_per_hour` por estrategia (ej. 10).  
  - Kill-condition: si Gamma o Directory no disponible, no hacer auto-attach (solo observar ya asignados).

---

## 3. Plan de implementación (fase por fase)

### Phase 0 — Baseline & metrics

- **Deliverables:** Telemetría de freshness (last_scanned_at), nº de events elegibles por estrategia, latencia p95 de endpoints Directory (cuando existan), error rate a Gamma; tests de integración mínimos para GET /markets y GET /markets/events/list (paginación y filtros).
- **Files/Modules:** `backend/app/api/markets.py`, `backend/app/core/scanner/scanner.py`, nuevo módulo opcional `backend/app/core/observability/directory_metrics.py`, tests en `backend/tests/integration/`.
- **Risks:** Ninguno crítico; solo añadir métricas y tests.
- **Validation:** Dashboard o log con last_scanned_at; tests pasan.
- **Rollout:** Deploy sin cambio de comportamiento; feature flags no necesarios.

---

### Phase 1 — Directory cache

- **Deliverables:**  
  - Índices en Redis (o seguir in-memory primero con misma interfaz) para markets/events con campos de filtro (category, tag, state, enabled, timestamps).  
  - Endpoints de lectura: listar categories/tags desde DB/Redis; listar markets y events con filtros (category, tag, search, enabled, state, next_days, max_time_to_resolution) y paginación (limit/offset).  
  - Toda lectura desde Redis/DB; scanner (o job) es quien escribe en Redis.
- **Files/Modules:** Nuevo `backend/app/api/directory.py` o rutas bajo `markets.py`; `backend/app/core/directory/` (service + cache keys); `backend/app/core/scanner/scanner.py` (escribir a Redis después de Gamma). Config Redis en `backend/app/core/config.py` si se introduce Redis.
- **Risks:** Redis nuevo puede fallar; tener fallback a DB y marcar “stale”.
- **Validation:** GET /directory/events con filtros devuelve solo datos de Redis/DB; nunca llama a Gamma en la request; paginación funciona.
- **Rollout:** Feature flag “use_directory” para leer de Directory; si off, comportamiento actual.

---

### Phase 2 — Universe model & API

- **Deliverables:**  
  - Schema `UniverseConfig` ampliado con events[], time_filter (window, next_days, max_time_to_resolution_minutes).  
  - Validación en PUT: no permitir referenciar markets/events que no estén enabled global.  
  - GET/PUT universe existentes actualizados; documentación de precedencia (enabled global > deny_list > selectors).
- **Files/Modules:** `backend/app/api/strategies.py` (UniverseConfig, validación), `backend/app/models/strategy.py` (sin cambio de columna si JSONB ya soporta estructura).
- **Risks:** Cambio de contrato; compatibilidad con clients que no envíen time_filter.
- **Validation:** PUT con market_id disabled global devuelve 400; GET devuelve time_filter.
- **Rollout:** Backward compatible (time_filter opcional); comunicar cambio a frontend.

---

### Phase 3 — Frontend Strategy Builder (UX smooth)

- **Deliverables:**  
  - UI por pasos: Categories/Tags → Markets → Events → Summary.  
  - Instant search con debounce, skeleton loading, infinite scroll.  
  - Chips de filtros activos, contadores (#eligible).  
  - “Freshness: last updated at …” desde Directory meta.  
  - Guardado optimista con rollback en error.  
  - Diseño minimalista: fondo neutro, bordes suaves, tipografía simple, sin gradientes saturados.
- **Files/Modules:** `frontend/app/strategies/[id]/desk/page.tsx` (o nueva ruta `/strategies/[id]/universe`), nuevos componentes en `frontend/components/strategy/` (DirectoryFilters, EventList, UniverseSummary, etc.), `frontend/lib/api.ts` (llamadas a Directory y universe).
- **Risks:** Complejidad de estado en frontend; muchos filtros pueden confundir.
- **Validation:** Usuario puede filtrar por categoría/tag/tiempo y ver solo eligible; contadores coherentes; guardado persiste en backend.
- **Rollout:** Nueva ruta o tab “Universe” en Desk; redirección opcional desde flujo antiguo.

---

### Phase 4 — Auto-attach & ops safety

- **Deliverables:**  
  - Auto-attach en control loop usando Directory (no Gamma) y aplicando time_filter y enabled global.  
  - Límites: max_events_per_strategy, max_auto_attaches_per_hour; kill-condition si Directory/Gamma no disponible.  
  - Logs y métricas de auto-attach (cuántos por estrategia, rechazos por límite).
- **Files/Modules:** `backend/app/core/strategy_engine/control_loop.py` (_check_and_auto_attach_events), config en `control_loop_config` o global.
- **Risks:** Auto-attach masivo si filtros mal configurados; mitigar con límites estrictos por defecto.
- **Validation:** Con auto_attach=true y Universe que matchea 1 event nuevo, tras un tick se crea StrategyEvent; con límite 0 no se crea.
- **Rollout:** Feature flag “auto_attach_v2”; rollout progresivo por estrategia.

---

## 4. UI/UX spec (mini design spec)

- **Layout:** 2 paneles: izquierda filtros (Categories, Tags, Markets, ventana temporal), derecha lista de events (o tabs: Markets | Events). Resumen y “Add to strategy” visible (barra fija o drawer).
- **Componentes:**  
  - Search input con icono de búsqueda y botón clear.  
  - Filter chips (categoría, tag, “Próximos 7 días”, etc.) con opción de quitar.  
  - Tabla o lista de items (densidad moderada: una línea por event con nombre, market, state, time-to-resolution).  
  - Drawer o side panel para detalle de event/market; CTA “Add to strategy”.  
  - Empty states: “No events match filters” / “Enable markets in Markets page” con ilustración o icono simple.
- **Micro-interactions:**  
  - Hover suave (cambio de fondo ligero), focus ring discreto (2px, color neutro).  
  - Transitions 150–200 ms, sin overshoot.  
  - Skeletons en lista mientras carga; spinners pequeños en botones de acción.
- **Guidelines:**  
  - Grid 8pt (espaciado 8, 16, 24).  
  - Colores neutros, no saturados (grises, blanco/off-white).  
  - Accesibilidad básica: contraste, focus visible, labels en inputs.

---

## 5. Open questions (máx. 8)

1. **Redis vs in-memory para Phase 1:** ¿Se exige Redis desde día 1 para Directory o se puede mantener in-memory con la misma API y migrar a Redis en una fase posterior?
2. **Cálculo de time-to-resolution:** ¿Se calcula en scanner (y se persiste en Event o en índice) o en tiempo de lectura (GET) a partir de end_time?
3. **Enabled global:** ¿Es exactamente el conjunto de markets con MarketEnabledState.enabled=true, o habrá otra capa (ej. allowlist por entorno)?
4. **Límite máximo de events por estrategia:** ¿Valor por defecto (ej. 50) y dónde se configura (por estrategia vs global)?
5. **Paginación en GET /markets/events/list:** ¿Limit por defecto (ej. 20) y max (ej. 100) y offset/cursor; o solo limit/offset?
6. **Idioma de la UI:** ¿Solo español, solo inglés, o i18n desde el inicio para Strategy Builder?
7. **Estrategias sin Universe definido:** ¿Se consideran “todas los events asignados manualmente” o “ninguno elegible para auto_attach”?
8. **Métricas de freshness:** ¿Dónde se exponen (endpoint dedicado /directory/meta, cabecera HTTP, o ambos)?

---

## 6. Checklist final

- [ ] Phase 0: Métricas de freshness y tests de integración en marcha.
- [ ] Phase 1: Directory cache (Redis o in-memory) con índices y endpoints de lectura con filtros y paginación; cero llamadas a Gamma en requests de usuario.
- [ ] Phase 2: UniverseConfig ampliado con time_filter y events[]; validación enabled global en PUT; documentación de precedencia.
- [ ] Phase 3: Frontend por pasos (Categories → Markets → Events), filtros con chips, contadores, freshness, guardado optimista, diseño minimalista.
- [ ] Phase 4: Auto-attach usando Directory con time_filter y enabled global; límites max_events y max_attaches/hora; feature flag y rollout progresivo.
- [ ] Documentación: Precedencia enabled global > deny_list > universe; rate limits Gamma y uso del scanner; actualización de MERCADOS_POLYMARKET_FLUJO si cambian flujos.
- [ ] Open questions resueltas y reflejadas en implementación.
