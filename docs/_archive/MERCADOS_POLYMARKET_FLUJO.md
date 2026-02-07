# Flujo de mercados y eventos desde Polymarket

## Resumen

- **Markets (plantillas)** se leen de la **API Gamma de Polymarket** (`https://gamma-api.polymarket.com`).
- **Events (instancias tradeables)** en la app vienen de **nuestra base de datos**, que el **Scanner** rellena usando la misma API.
- El estado **enabled** de cada market se guarda solo en nuestra DB (`MarketEnabledState`).

---

## 1. Dónde se lee Polymarket

| Qué | Dónde | Cómo |
|-----|--------|------|
| **Listado de markets (configurar mercados)** | Backend `GET /markets` | Llama a Gamma `GET /markets?closed=false&limit=...&offset=...`. Tras un cambio reciente, se hace **paginación** (varias páginas) para poder devolver más de 100 markets. Los filtros (`category`, `search`, `tag_id`, `series_id`, `enabled`) se aplican **en el backend** sobre esa lista. |
| **Eventos para asignar a estrategia (Desk)** | Backend `GET /markets/events/list` | **No** llama a Polymarket en esa petición. Lee **Event** y **Market** de **nuestra base de datos**. Esos datos los ha escrito antes el **Scanner**. |
| **Scanner (poblado de DB)** | `app.core.scanner.scanner` | Llama a Gamma: **Events** (`/events`) y **Markets** (`/markets`) con paginación (varias páginas), y opcionalmente **Series** (`/series`). Crea/actualiza **Series**, **Market**, **Event** y **Tag** en nuestra DB. |

---

## 2. Flujo por pantalla

### Pantalla “Markets” (`/markets`)

1. Frontend llama a `GET /markets` (opcionalmente con query `category`, `search`, etc.).
2. Backend:
   - Si no hay cache, pide a Gamma varias páginas de markets (`/markets?closed=false&limit=100&offset=0`, luego `offset=100`, etc., hasta un máximo de páginas).
   - Guarda en cache la lista agregada (TTL ~60 s).
   - Lee de nuestra DB el estado `enabled` por `polymarket_market_id`.
   - Aplica filtros (category, search, tag_id, series_id, enabled) sobre la lista.
   - Devuelve la lista filtrada.
3. Frontend muestra la tabla y aplica además filtros en cliente (búsqueda por nombre, categoría) sobre lo que ya recibió.
4. Al activar/desactivar un market, el frontend llama `PATCH /markets/{polymarket_market_id}/enable` y solo se actualiza `MarketEnabledState` en nuestra DB.

Resultado: **Sí se lee de Polymarket** para listar mercados. Con paginación en backend se pueden ver muchos más de 100. **Filtrar** se puede por categoría, búsqueda, tag, series y enabled; los filtros de categoría y búsqueda tienen efecto en backend si se pasan por query.

### Pantalla “Desk” de una estrategia (asignar eventos)

1. Frontend pide eventos asignados: `GET /strategies/{id}/events`.
2. Frontend pide lista de eventos: `GET /markets/events/list?state=ACTIVE` y `GET /markets/events/list?state=FINISHED`.
3. **Esos eventos vienen de nuestra DB**, no de Polymarket en tiempo real. La DB se rellena cuando corre el **Scanner** (events descubiertos vía Gamma y persistidos como **Event** + **Market**).
4. El usuario asigna/desasigna eventos; el backend actualiza **StrategyEvent**.

Resultado: Para “configurar” qué eventos usa la estrategia, **no** se lee Polymarket en esa petición; se usa lo que ya está en DB. Si no hay muchos eventos en DB, hay que asegurarse de que el **Scanner** esté corriendo y que tenga configurado descubrir suficientes markets/events (p. ej. series o filtros que incluyan los mercados que te interesan).

---

## 3. Filtros disponibles

### Backend `GET /markets`

- **category**: solo markets con `category` igual al valor.
- **search**: solo markets cuyo nombre/pregunta contenga el texto (case-insensitive).
- **enabled**: `true` / `false` según estado en nuestra DB.
- **series_id**: solo markets de esa series (Polymarket).
- **tag_id**: solo markets que tengan ese tag.

Todos se aplican **en el servidor** sobre la lista de markets obtenida de Gamma (y cache).

### Frontend `/markets`

- Hoy la página llama `GET /markets` **sin** query params (category, search, etc.), así que recibe todos los markets que devuelve el backend (varios cientos tras la paginación) y filtra en cliente por **nombre** y **categoría**. Si quieres filtrar en servidor (menos datos por red), se puede cambiar el frontend para llamar p. ej. `GET /markets?category=crypto&search=btc`.

### Backend `GET /markets/events/list`

- **market_id**: solo eventos de ese market (interno).
- **state**: `UPCOMING`, `ACTIVE` o `FINISHED`.

---

## 4. Límites y cache

- **Gamma API**: rate limits por endpoint (p. ej. 125 req/10s para markets). El backend usa `rate_limiter` y, al pedir varias páginas, puede tardar unos segundos la primera vez.
- **Cache**: la lista agregada de markets se cachea ~60 s; así no se vuelve a pedir a Gamma en cada petición.
- **Scanner**: usa su propia paginación y configuración (`scanner_pagination_limit`, `scanner_max_pages`) para descubrir markets/events y escribir en DB.

---

## 5. Evolución

El estado objetivo (TO-BE) está definido en [DISCOVERY_UNIVERSE_STRATEGY_BUILDER_SPEC.md](./DISCOVERY_UNIVERSE_STRATEGY_BUILDER_SPEC.md): capa **Directory** cache-first (solo DB/Redis en la request; nunca Gamma), **Universe** por estrategia con time_filter y precedencia enabled global → deny_list → selectores. La evolución por fases (observabilidad, Directory, Universe completo, Strategy Builder UX, auto-attach seguro) se describe en la sección 3 de ese SPEC.

---

## 6. Enabled global vs Universe

- **Enabled global:** Allowlist operacional. Son los markets que un operador ha habilitado en la pantalla Markets; se persiste en `MarketEnabledState`. Solo los events de esos markets pueden ser asignados a estrategias o considerados por auto-attach.
- **Universe:** Reglas declarativas por estrategia (categories, tags, markets, events, deny_list, time_filter). Acotan *qué* events, dentro de los que ya pasan enabled global, son elegibles para esa estrategia.
- **Precedencia:** Enabled global siempre gana. Un market no habilitado no puede incluirse vía Universe. Detalle en [DISCOVERY_UNIVERSE_STRATEGY_BUILDER_SPEC.md](./DISCOVERY_UNIVERSE_STRATEGY_BUILDER_SPEC.md) §2.2.

---

## 7. Resumen rápido

| Pregunta | Respuesta |
|----------|-----------|
| ¿Se leen markets de Polymarket? | **Sí.** En `GET /markets` se llama a la API Gamma con paginación. |
| ¿Se leen “todos”? | **Varios cientos/miles**, según límite de páginas configurado en backend (no solo 100). |
| ¿Se puede filtrar? | **Sí.** Por categoría, búsqueda, tag, series y enabled en backend; en frontend además por nombre y categoría. |
| ¿De dónde salen los eventos del Desk? | De **nuestra base de datos**, poblada por el **Scanner** (que sí usa Polymarket). |
| ¿Activando un market en `/markets` se empieza a tradear? | No. Solo se guarda `enabled` en DB; el Scanner y la estrategia usan eso para descubrir/considerar eventos de ese market. |

Si no ves un market o categoría: comprueba que el backend esté pidiendo suficientes páginas a Gamma y que los filtros (category, search) no lo estén excluyendo. Si no ves eventos en el Desk, comprueba que el Scanner haya corrido y que los markets cuyos eventos quieres estén habilitados o sean descubiertos por el Scanner.

---

*Documento AS-IS. Para modelo objetivo y evolución, ver [DISCOVERY_UNIVERSE_STRATEGY_BUILDER_SPEC.md](./DISCOVERY_UNIVERSE_STRATEGY_BUILDER_SPEC.md).*
