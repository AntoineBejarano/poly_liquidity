# SPEC: Discovery, Universe y Strategy Builder

**Versión:** 1.1  
**Estado:** PR-ready  
**Fuentes:** [MERCADOS_POLYMARKET_FLUJO.md](./MERCADOS_POLYMARKET_FLUJO.md) (AS-IS y evolución), [PLAN_DISCOVERY_UNIVERSE_STRATEGY_BUILDER.md](./PLAN_DISCOVERY_UNIVERSE_STRATEGY_BUILDER.md). Alineado con MERCADOS_POLYMARKET_FLUJO para evitar contradicciones AS-IS/TO-BE.

---

## 0. Executive summary

**Qué existe hoy:** Los markets se obtienen de la API Gamma de Polymarket en `GET /markets` (con paginación y cache in-memory). Los events del Desk salen de la base de datos local, poblada por un Scanner que sí llama a Gamma. El estado “enabled” por market se guarda en `MarketEnabledState`. La estrategia tiene `universe_config` (categories, markets, tags, auto_attach, deny_list) y asignación manual de events vía `StrategyEvent`; el control loop hace auto-attach por categories/markets/tags sin time_filter ni límites duros.

**Qué queremos construir:** Una capa **Directory** cache-first (DB/Redis) que sirva categories, tags, markets y events con filtros (incl. ventana temporal y time-to-resolution). La UI y el control loop consumen solo Directory; **nunca** Gamma en la petición del usuario. Universe por estrategia se amplía con `time_filter` y `events[]`; la **precedencia** es obligatoria: enabled global → deny_list → selectores de universe → time_filter. El Strategy Builder en frontend permite explorar y filtrar por categorías, tags, markets, events y tiempo; guardado optimista y diseño sobrio (estilo ChatGPT/Google). Auto-attach usa Directory, aplica enabled global y time_filter, y está acotado por límites (max events/strategy, max attaches/hora) y modo dry-run opcional.

**Qué NO debe hacer nunca el sistema:** La UI no debe llamar a Gamma. Ningún endpoint de “listado para el usuario” debe disparar una request a Gamma en tiempo real. El único componente que habla con Gamma para descubrir datos es el Scanner (o jobs de refresh), que alimenta DB/cache.

**Principios clave:** (1) **Cache-first:** toda lectura de datos de discovery viene de Directory (DB/Redis). (2) **Universe declarativo:** la estrategia define reglas (categories, tags, markets, time_filter), no listas infinitas de events. (3) **Enabled global:** la allowlist operacional (markets habilitados en nuestra DB) prevalece siempre; ningún event de un market no enabled es elegible. (4) **Rate limits:** solo el Scanner/jobs respetan Gamma; la UI no genera carga a Gamma.

---

## 1. Estado actual (AS-IS)

Fuente: [MERCADOS_POLYMARKET_FLUJO.md](./MERCADOS_POLYMARKET_FLUJO.md). Formato por bloque: qué hace hoy → dónde vive (paths) → limitaciones reales.

### 1.1 Discovery de markets (Gamma `/markets`)

- **Qué hace hoy:** El backend expone `GET /markets`. Si no hay cache, llama a Gamma `GET /markets?closed=false&limit=100&offset=N` en varias páginas (hasta un máximo configurable). Aplica filtros en backend: category, search, enabled, tag_id, series_id. La lista agregada se cachea un tiempo (aprox. 60 s). El estado `enabled` por market se resuelve contra nuestra DB (`MarketEnabledState`).
- **Dónde vive:** `backend/app/api/markets.py` (listado y paginación a Gamma), `backend/app/core/api_cache.py` (cache), `backend/app/core/rate_limiter.py` (rate limit antes de llamar Gamma).
- **Limitaciones reales:** La petición del usuario puede provocar llamadas a Gamma si el cache ha expirado. No hay capa “solo DB/Redis”; no hay filtro por ventana temporal (próximos N días). El frontend `/markets` hoy no envía query params y filtra en cliente.

### 1.2 Discovery de events (Scanner + Gamma `/events`)

- **Qué hace hoy:** El Scanner (`app.core.scanner.scanner`) llama a Gamma `/events` y `/markets` (y opcionalmente `/series`) con paginación configurable (`scanner_pagination_limit`, `scanner_max_pages`). Persiste y actualiza en DB: Series, Market, Event, Tag. Los events listados en el Desk **no** vienen de Gamma en esa petición; vienen de la DB.
- **Dónde vive:** `backend/app/core/scanner/scanner.py` (fetch_events, fetch_markets, fetch_series; uso de rate_limiter y api_cache).
- **Limitaciones reales:** Si el Scanner no ha corrido o no cubre ciertos markets/series, el Desk no verá esos events. No hay `last_scanned_at` expuesto. No hay índices por categoría/tag/ventana temporal listos para filtrar; los filtros actuales del listado de events son limitados (market_id, state).

### 1.3 Enabled global (MarketEnabledState)

- **Qué hace hoy:** El estado “este market está habilitado para operar” se guarda en nuestra DB en `MarketEnabledState` (por `polymarket_market_id`). El toggle es `PATCH /markets/{polymarket_market_id}/enable`. Ese estado se usa al filtrar en `GET /markets` (query `enabled=true/false`). No está documentado como “enabled global” ni aplicado de forma centralizada en listado de events ni en auto-attach.
- **Dónde vive:** Modelo y lógica en `backend/app/api/markets.py` (enable/disable), persistencia en DB vía modelo correspondiente a MarketEnabledState.
- **Limitaciones reales:** No hay un único punto que aplique “solo events de markets enabled” en todos los flujos (Desk, auto-attach, Directory). Un event de un market deshabilitado podría en teoría asignarse si la validación no lo comprueba.

### 1.4 Listado de events en Desk

- **Qué hace hoy:** El frontend pide `GET /strategies/{id}/events` (asignados) y `GET /markets/events/list?state=ACTIVE` y `?state=FINISHED`. El backend lee Event y Market de la DB; filtros: `market_id`, `state`. Devuelve hasta 100 eventos (limit fijo, sin offset). El usuario asigna/desasigna vía endpoints de estrategia; se persiste `StrategyEvent`.
- **Dónde vive:** `backend/app/api/markets.py` (`get_events`), `backend/app/api/strategies.py` (endpoints de add/remove event), `frontend/app/strategies/[id]/desk/page.tsx`.
- **Limitaciones reales:** Sin paginación server-side; sin filtros por categoría, tag, próximos N días ni time-to-resolution; sin aplicar “enabled global” en el listado; filtrado adicional en cliente.

### 1.5 Caching actual (in-memory, TTL)

- **Qué hace hoy:** Cache en memoria (`APICache`), no Redis. Keys por tipo de dato (market_list, event_data, etc.); TTL típicos ~30–60 s para listas. Se usa en `GET /markets`, en el Scanner y en otros puntos que llaman a Gamma o a APIs externas.
- **Dónde vive:** `backend/app/core/api_cache.py`; uso en `backend/app/api/markets.py`, `backend/app/core/scanner/scanner.py`, `backend/app/api/polymarket.py`, `backend/app/api/dashboard.py`.
- **Limitaciones reales:** No hay Redis; no hay índices precalculados por category/tag/tiempo; no hay contrato de “stale-ok” ni cabecera de freshness; el cache se pierde al reiniciar el proceso.

### 1.6 Rate limiting Gamma

- **Qué hace hoy:** El backend usa un rate limiter por tipo de endpoint (GAMMA_MARKETS, GAMMA_EVENTS, etc.) con ventana deslizante. Antes de llamar a Gamma se hace `wait_for_capacity(timeout)`; si hay violación se registra y se puede usar cache si existe, o fallar.
- **Dónde vive:** `backend/app/core/rate_limiter.py` (EndpointType, RateLimiter); uso en `backend/app/api/markets.py`, `backend/app/core/scanner/scanner.py`, y otros.
- **Limitaciones reales:** Los límites exactos por endpoint no están documentados en un solo lugar; la UI indirectamente puede provocar muchas llamadas si muchos usuarios refrescan y el cache expira.

---

## 2. Modelo objetivo (TO-BE)

Fuente: [PLAN_DISCOVERY_UNIVERSE_STRATEGY_BUILDER.md](./PLAN_DISCOVERY_UNIVERSE_STRATEGY_BUILDER.md). Sin ambigüedades; solo definición del estado deseado.

### 2.1 Directory (Data Layer)

**Qué es:** Capa de lectura cache-first que expone categories, tags, markets y events para la UI y para el control loop. Es la única fuente de datos de “discovery” que consumen las peticiones de usuario y el auto-attach.

**Qué datos sirve:** Listas/ítems de categories, tags, markets y events con filtros (category, tag, search, enabled, state, next_days, max_time_to_resolution) y paginación. Incluye metadatos de freshness según el contrato siguiente.

**Qué datos NO sirve:** No sirve datos en tiempo real desde Gamma en la petición. No ejecuta llamadas a Gamma. No expone orderbooks ni precios en vivo (eso sigue en su propia capa).

**Contrato formal de respuesta (Directory):** Toda respuesta de listado del Directory debe incluir (en cuerpo o cabeceras estándar) al menos:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `last_scanned_at` | string (ISO8601) o number (epoch) | Timestamp de la última ejecución del Scanner que alimentó estos datos. |
| `freshness` | `"fresh"` \| `"stale"` | Indica si los datos provienen de la fuente preferida (ej. Redis) o de fallback (ej. solo DB). |
| `source` | `"redis"` \| `"db"` | Origen de los datos en esta respuesta. |
| `data_age_seconds` | number, opcional | Segundos desde `last_scanned_at` hasta ahora. Útil para UI. |

Si Redis no está disponible o no está poblado, se sirve desde DB con `freshness: "stale"` y `source: "db"`. La UI puede mostrar “Última actualización: …” y, si stale, un aviso discreto sin bloquear.

**Paginación:** Se recomienda **cursor-based** (ej. `cursor` + `limit`, respuesta con `next_cursor` o `has_more`). **Offset** es aceptable; en ese caso documentar que la consistencia entre páginas no está garantizada si hay escrituras entre solicitudes (el cliente debe asumir posible duplicado o salto). Límites: `limit` por defecto y máximo definidos (ej. default 20, max 100).

**Relación con Scanner:** El Scanner (o un job de refresh dedicado) es el único componente que llama a Gamma para discovery. Escribe en DB y, si se usa Redis, actualiza índices y `last_scanned_at`. El Directory solo lee de DB/Redis.

**Por qué la UI nunca toca Gamma:** Para garantizar baja latencia, respeto a rate limits y que un fallo o lentitud de Gamma no bloquee la experiencia. Toda interacción del usuario con listados de markets/events pasa por el backend, y el backend en esas rutas solo lee del Directory (DB/Redis).

### 2.2 Universe por estrategia

**Qué es:** Conjunto de reglas declarativas que definen qué events son elegibles para una estrategia (para asignación manual y para auto-attach). No es una lista infinita de event_ids; son criterios (categories, tags, markets, opcionalmente events concretos, time_filter) más deny_list y auto_attach.

**Campos exactos:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `categories` | `string[]` | **Filtros (AND):** El event debe estar en al menos una de estas categorías. Vacío = no filtra por categoría. |
| `tags` | `string[]` | **Filtros (AND):** El event debe tener al menos uno de estos tags. Vacío = no filtra por tag. Entre categories y tags: debe cumplir ambos si ambos están no vacíos. |
| `markets` | `string[]` | **Inclusión explícita:** IDs de market (polymarket_market_id) que se consideran permitidos. Unión con el resto de elegibles (ver semántica). Vacío = no añade por market. |
| `events` | `string[]` | **Inclusión explícita:** IDs concretos de events que se consideran elegibles. Unión con el resultado de categories/tags/markets. Vacío = no añade por event. |
| `deny_list` | `string[]` | IDs de market o event **excluidos siempre**. Se aplica después de enabled global y antes de evaluar elegibilidad positiva. |
| `time_filter` | objeto opcional | Ver tabla siguiente. |
| `auto_attach` | `boolean` | Si true, el control loop puede asignar automáticamente nuevos events que cumplan el universe (respetando límites). |

**time_filter (objeto):**

| Subcampo | Tipo | Descripción |
|----------|------|-------------|
| `window` | `"UPCOMING"` \| `"ACTIVE"` \| `"ANY"` | Estado del event. Opcional; si no se envía, no se filtra por estado. |
| `next_days` | `number` | Solo events cuyo start_time o ventana relevante caiga en los próximos N días. Opcional. |
| `max_time_to_resolution_minutes` | `number` | Solo events con time-to-resolution ≤ este valor (minutos). Opcional. Ver definición provisional más abajo. |

**Semántica de selectores:**

- **Enabled global siempre gana.** Ningún event cuyo market no esté en MarketEnabledState.enabled=true es elegible. No es anulable por Universe.
- **deny_list excluye siempre.** Si el market_id o event_id está en deny_list, el event queda fuera. Se aplica tras enabled global.
- **categories y tags = filtros (AND).** Un event debe cumplir: (al menos una category de la lista, si categories no vacío) Y (al menos un tag de la lista, si tags no vacío). Si solo uno está definido, solo se aplica ese.
- **markets[] y events[] = inclusiones explícitas (unión).** Son listas de IDs que se consideran elegibles. El conjunto elegible por “selectores positivos” es: (events que pasan categories/tags) **unión** (markets[] por market_id) **unión** (events[] por event_id). Si categories y tags están vacíos pero markets o events no, solo cuentan las inclusiones explícitas.
- **time_filter** se aplica al conjunto resultante (window, next_days, max_time_to_resolution_minutes).

**time_to_resolution_minutes (definición provisional):** Valor calculado como `(end_time - now)` en minutos cuando `end_time` existe. Si `end_time` (o el timestamp necesario) falta en el event, el filtro `max_time_to_resolution_minutes` **se omite** en backend (no se filtra por ese criterio para ese event). La **UI** no debe mostrar el control o filtro de time-to-resolution cuando los datos no exponen ese campo o cuando la mayoría de ítems no lo tienen; si se muestra, debe degradar de forma elegante (ej. “—” o ocultar la columna).

**Precedencia obligatoria (de mayor a menor):** (1) Enabled global; (2) deny_list; (3) selectores positivos (categories/tags como AND, markets[]/events[] como unión) y time_filter. Resumen para trader: “Enabled global” es lo que activas en Markets; solo esos markets pueden tener events asignados. Por estrategia defines categorías/tags (filtros), markets/events concretos (inclusiones) y ventana de tiempo; deny_list excluye siempre.

---

## 3. Evolución AS-IS → TO-BE (plan por fases)

Cada fase: objetivo, qué cambia respecto a AS-IS, deliverables, riesgos reales, acceptance criteria.

### Phase 0: Observabilidad y baseline

- **Objetivo:** Poder medir freshness y comportamiento actual sin cambiar flujos; base de tests para evolución.
- **Qué cambia respecto a AS-IS:** Se añade telemetría y tests; no se cambia el flujo de datos ni la API pública.
- **Deliverables:** (1) `last_scanned_at` (o equivalente) registrado cuando el Scanner termina y expuesto (log o endpoint mínimo). (2) Tests de integración para `GET /markets` y `GET /markets/events/list` (paginación donde aplique, filtros existentes). (3) Métricas opcionales: latencia de estos endpoints, error rate a Gamma.
- **Riesgos reales:** Ninguno crítico; solo instrumentación.
- **Acceptance criteria:** Tras un run del Scanner hay un valor de “última vez que se escaneó” consultable. Los tests de integración pasan en CI. **Invariante comprobable:** existe al menos un test (integración o e2e) que verifica que las rutas de listado para el usuario (markets, events/list o equivalentes) no realizan llamadas HTTP a Gamma en la request; por ejemplo mockeando el cliente HTTP de Gamma y afirmando cero invocaciones en una petición típica de listado (cuando el sistema esté en modo Directory/TO-BE).

### Phase 1: Directory (DB-first; Redis opcional)

- **Objetivo:** Capa de lectura cache-first: endpoints que sirven categories, tags, markets y events desde DB (y Redis si se implementa), sin llamar a Gamma en la request.
- **Qué cambia respecto a AS-IS:** Nuevos (o refactorizados) endpoints de tipo Directory que solo leen DB/Redis. El Scanner (o job) puede escribir en Redis si se usa; si no, Directory lee solo de DB. `GET /markets` puede migrar a leer del Directory cuando un feature flag esté activo.
- **Deliverables:** (1) Endpoints de lectura: listar categories, tags; listar markets con filtros (category, tag, search, enabled, state, next_days) y limit/offset; listar events con filtros (market_id, state, category, tag, next_days, max_time_to_resolution) y limit/offset. (2) Respuesta o cabecera con indicación de freshness (ej. `last_scanned_at` o `freshness: fresh|stale`). (3) Documentación: “Directory es cache-first; la UI no llama a Gamma.”
- **Riesgos reales:** Redis nuevo puede fallar; debe existir fallback a DB y marcar stale. Primera versión puede ser solo DB sin Redis.
- **Acceptance criteria:** Una petición a un endpoint Directory no genera llamada a Gamma (testeable: mock de Gamma, aserción de cero llamadas). Los filtros y la paginación devuelven resultados coherentes. Las respuestas incluyen el contrato de freshness (last_scanned_at, freshness, source, data_age_seconds). Si solo DB está disponible, se sirve con freshness “stale” y source “db”.

### Phase 2: Universe completo (con time_filter)

- **Objetivo:** Modelo Universe con time_filter y events[]; validación de enabled global en escritura; precedencia documentada y aplicada en backend.
- **Qué cambia respecto a AS-IS:** `UniverseConfig` ampliado con `events[]` y `time_filter` (window, next_days, max_time_to_resolution_minutes). PUT universe valida que no se referencien markets/events no enabled global. Toda lógica que “elige” events para una estrategia aplica: enabled global → deny_list → selectores + time_filter.
- **Deliverables:** (1) Schema `UniverseConfig` actualizado en API y persistido en `universe_config` (JSONB). (2) Validación en PUT: 400 si se incluyen markets o events no enabled. (3) Documentación de precedencia en este SPEC y en código. (4) Directory (o endpoints que alimenten el Builder) aplican enabled global al listar.
- **Riesgos reales:** Cambio de contrato; clients antiguos que no envíen time_filter deben seguir siendo válidos (campos opcionales).
- **Acceptance criteria:** PUT universe con un market_id no enabled devuelve 400. GET universe devuelve time_filter y events[]. Un event de un market no enabled no aparece como elegible en el listado del Directory para asignar a estrategia.

### Phase 3: Strategy Builder UX

- **Objetivo:** Flujo de configuración del universe en la pantalla de estrategia: explorar por categorías/tags, luego markets/events, filtrar por tiempo, validar y guardar. Diseño sobrio, sin ruido visual.
- **Qué cambia respecto a AS-IS:** Nueva experiencia en Desk (o pestaña “Universe”): datos desde Directory; filtros con chips; contadores (#eligible); freshness visible; guardado optimista con rollback.
- **Deliverables:** (1) User flow: entrar a estrategia → explorar universe (categories/tags → markets → events) → aplicar filtros (incl. ventana temporal) → validar resumen → guardar. (2) Componentes: búsqueda con debounce, chips de filtros, lista/tabla con paginación o infinite scroll, panel/drawer de detalle, CTA “Añadir a estrategia”. (3) Estados: loading (skeletons), empty (mensaje claro), stale (aviso de última actualización). (4) Guardado optimista y rollback en error. (5) Principios visuales: neutro, smooth, foco en información (ver sección 4).
- **Riesgos reales:** Complejidad de estado en frontend; posibles regresiones en flujo actual si se reutiliza la misma ruta.
- **Acceptance criteria:** Usuario puede filtrar por categoría, tag y ventana temporal y ver solo events elegibles (y coherentes con enabled global). Los contadores reflejan el resultado de los filtros. Al guardar, el backend persiste universe_config y la próxima carga muestra los valores guardados. Si el guardado falla, la UI revierte y muestra error.

### Phase 4: Auto-attach seguro (límites y dry-run)

- **Objetivo:** Auto-attach en el control loop usando Directory, aplicando enabled global, deny_list, selectores y time_filter; acotado por límites y con opción dry-run.
- **Qué cambia respecto a AS-IS:** `_check_and_auto_attach_events` obtiene candidatos del Directory (no de Gamma), aplica la precedencia completa y time_filter. Se aplican límites: max_events_per_strategy, max_auto_attaches_per_hour. Opción de dry-run (solo log, no crear StrategyEvent). Si Directory/Gamma no disponible, no se hace auto-attach.
- **Deliverables:** (1) Integración en control loop: lectura desde Directory; aplicación de enabled global, deny_list, universe y time_filter. (2) Configuración de límites (global o por estrategia): max_events_per_strategy, max_auto_attaches_per_hour. (3) Dry-run opcional para auto_attach. (4) Logs/métricas: eventos auto-asignados y rechazos por límite. (5) Feature flag para rollout progresivo.
- **Riesgos reales:** Filtros muy amplios pueden generar muchos candidatos; los límites deben ser estrictos por defecto.
- **Acceptance criteria:** Con auto_attach=true, Universe que matchea un event nuevo y límites que lo permitan, tras el tick correspondiente se crea StrategyEvent. Con max_events_per_strategy ya alcanzado, no se asigna más. Con dry-run activo, no se crea StrategyEvent pero se registra en log que se habría asignado. Un event de un market no enabled no se auto-asigna nunca.

---

## 4. UX / Frontend spec (diseño real)

**Inspiración explícita:** Más ChatGPT / Google Search que dashboard crypto. Información clara, acciones obvias, sin gradientes chillones ni decoración de “IA”.

### 4.1 User flow exacto

1. **Entrar a estrategia:** Usuario abre la estrategia (ej. Desk o pestaña “Universe”).
2. **Explorar universe:** Ve listas o pasos: Categories/Tags → Markets → Events. Puede elegir categorías o tags primero para acotar; luego ver markets y events que cumplen.
3. **Filtrar:** Aplica filtros por búsqueda de texto, chips (categoría, tag, “Próximos 7 días”, etc.) y ventana temporal (UPCOMING/ACTIVE, next_days, time-to-resolution si se expone). Los resultados se actualizan; se muestra un contador de elegibles.
4. **Validar:** Ve un resumen de lo que quedará en el universe (o los events seleccionados) antes de guardar.
5. **Guardar:** Clic en guardar; guardado optimista (UI actualiza); si el backend falla, rollback y mensaje de error.

### 4.2 Componentes clave

- **Search input:** Icono de búsqueda, placeholder claro, botón clear. Debounce 200–300 ms.
- **Filter chips:** Cada filtro activo (categoría, tag, “Próximos 7 días”) como chip con opción de quitar (x). Colores neutros.
- **Lista/tabla de events (o markets):** Densidad moderada: una línea por ítem con nombre, market, state, time-to-resolution si aplica. Checkbox o “Añadir” por fila o desde el detalle.
- **Panel/drawer de detalle:** Al hacer clic en un event (o market), panel lateral o drawer con detalles y CTA “Añadir a estrategia”.
- **Resumen antes de guardar:** Lista corta de lo que se va a guardar (o “N events elegibles”) y botón Guardar.
- **Freshness:** Línea discreta: “Datos actualizados a las HH:MM” o “Última sincronización: …”. Si stale: “Datos pueden estar desactualizados” sin bloquear.

### 4.3 Estados (loading, empty, stale)

- **Loading:** Skeletons en la lista; no spinner grande en toda la pantalla. Botones de acción con spinner pequeño si aplica.
- **Empty:** Mensaje claro: “Ningún event coincide con los filtros” o “Habilita markets en la página Mercados”. Sin ilustraciones pesadas; icono simple o texto.
- **Stale:** Indicador de “datos pueden estar desactualizados” (texto o icono pequeño); no modal ni bloqueo.

### 4.4 Micro-interacciones

- Hover suave en filas y botones (cambio de fondo ligero).
- Focus ring discreto (2px, color neutro) para accesibilidad.
- Transiciones 150–200 ms en aparición/desaparición de panels y chips; sin overshoot.
- Skeletons alineados con el layout real de la lista.

### 4.5 Principios visuales

- **Neutral:** Fondo neutro (blanco/off-white o gris muy claro); texto gris oscuro/negro; bordes suaves.
- **Smooth:** Sin gradientes llamativos; sin paletas saturadas; sin “glassmorphism” innecesario.
- **Foco en información:** La jerarquía visual prioriza títulos, filtros y datos; la decoración es mínima.
- **Accesibilidad básica:** Contraste suficiente, focus visible, labels en inputs.

---

## 5. Decisiones explícitas

Lista de decisiones arquitectónicas para evitar debates futuros:

1. **La UI nunca llama a Gamma.** Toda lectura de markets/events para listados y configuración de estrategia pasa por el backend, y el backend en esas rutas solo lee del Directory (DB/Redis).
2. **Enabled global siempre gana.** Ningún event de un market no habilitado en MarketEnabledState es elegible para asignación ni para auto-attach, independientemente del universe de la estrategia.
3. **Universe es declarativo.** Se definen reglas (categories, tags, markets, time_filter, deny_list), no listas abiertas de event_ids como único mecanismo (events[] es opcional para inclusión explícita).
4. **Directory es cache-first.** Los endpoints Directory solo leen de DB/Redis; el Scanner (o jobs) es el único escritor desde Gamma.
5. **Auto-attach siempre limitado.** Límites obligatorios: max_events_per_strategy y max_auto_attaches_per_hour; opción dry-run; si Directory no disponible, no se hace auto-attach.
6. **Precedencia fija:** enabled global → deny_list → universe selectors + time_filter. No configurable.
7. **Stale-ok permitido.** El Directory puede devolver datos desde DB cuando Redis no esté disponible; se marca freshness y la UI puede mostrar aviso sin bloquear.
8. **Phase 1 puede ser DB-only.** Redis es opcional en Phase 1; la interfaz del Directory debe permitir implementación solo con DB.

---

## 6. Open questions (máx. 5)

Solo preguntas que puedan bloquear implementación:

1. **Redis en Phase 1:** ¿Directory debe implementarse desde día 1 con Redis o se acepta DB-only y Redis en una fase posterior?
2. **Definición operativa de enabled global:** ¿Siempre MarketEnabledState.enabled=true por polymarket_market_id o existirá otra capa (ej. allowlist por entorno)?
3. **Límites por defecto y ámbito:** ¿max_events_per_strategy y max_auto_attaches_per_hour son globales o por estrategia? Valores por defecto (ej. 50 y 10).
4. **Estrategia sin universe definido (todo vacío):** ¿Ningún event elegible para auto_attach, o los events ya asignados manualmente siguen válidos y auto_attach simplemente no añade nuevos?
5. **Dónde exponer last_scanned_at:** ¿Solo GET /directory/meta, solo en cuerpo/cabecera de cada respuesta Directory, o ambos?

---

## 7. Checklist final

Criterios ejecutables para considerar el sistema “bien hecho” según esta SPEC:

- [ ] **Invariante “UI nunca llama Gamma”:** Las rutas de listado (Directory, GET markets, GET events/list o equivalentes) no realizan llamadas a Gamma en la request. Comprobable por test: mock del cliente Gamma, petición de listado, aserción de cero invocaciones. Incluido en Phase 0/1 acceptance criteria y en suite de regresión.
- [ ] **Directory:** Existe una capa de lectura que sirve categories, tags, markets y events desde DB (y opcionalmente Redis). Ninguna de esas rutas llama a Gamma. Respuestas cumplen contrato: last_scanned_at, freshness, source, data_age_seconds; paginación (cursor recomendado u offset documentado).
- [ ] **Freshness:** last_scanned_at (o equivalente) expuesto; UI puede mostrar “última actualización” y aviso si freshness=stale.
- [ ] **Universe:** Schema con categories/tags (filtros AND), markets[]/events[] (inclusiones unión), deny_list, time_filter, auto_attach. time_to_resolution: definición provisional aplicada; si faltan timestamps, filtro omitido y UI oculta control.
- [ ] **Precedencia:** enabled global → deny_list → selectores + time_filter en toda elegibilidad (listado, auto-attach).
- [ ] **Validación:** PUT universe rechaza (400) referencias a markets o events no enabled global.
- [ ] **Strategy Builder UX:** Flujo explorar → filtrar → validar → guardar; chips; contadores; freshness visible; guardado optimista con rollback; diseño neutro y smooth.
- [ ] **Auto-attach:** Usa Directory; aplica enabled global, deny_list, universe y time_filter; límites y dry-run; no asigna si Directory no disponible.
- [ ] **Tests:** Integración para Directory y validación universe; test explícito del invariante “no Gamma en listado”.
- [ ] **Documentación:** SPEC y MERCADOS_POLYMARKET_FLUJO alineados; decisiones §5 reflejadas.
- [ ] **Open questions:** Las preguntas de §6 tienen respuesta decidida y reflejada en SPEC o implementación.
