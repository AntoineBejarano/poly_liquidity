# API Markets — Contrato y uso

Documentación del contrato de la API de markets (proxy Gamma, discovery, Add to Universe).

---

## GET /markets

**Respuesta:** siempre un **array** de objetos market. No hay envelope (sin `{ data: [...] }`). Cada item incluye los campos que devuelve Gamma más los añadidos por el backend.

### Campos añadidos por el backend

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `enabled` | boolean | Merge desde DB (MarketEnabledState). Indica si el market está habilitado para trading en la plataforma. |
| `clob_token_ids` | object | Ver sección siguiente. **No** asumir `list[0]=YES`; usar `selection_hint` y `primary`. |

### clob_token_ids y Token Selection Policy

El backend normaliza `clobTokenIds` de Gamma en un objeto con semántica explícita:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `primary` | string \| null | Token a usar para métricas (orderbook, spread). Siempre presente; puede ser null si no hay token usable. |
| `selection_hint` | string | Uno de: `primary_yes`, `single`, `multi`, `none`. |
| `primary_yes` | string \| null | Solo si Gamma envió dict con clave YES (case-insensitive). |
| `primary_no` | string \| null | Solo si Gamma envió dict con clave NO. |
| `clob_token_ids_all` | string[] \| null | Cuando Gamma envía lista (sin semántica YES/NO). |
| `clob_token_ids_by_key` | object \| null | Cuando Gamma envía dict (claves normalizadas). |

**Token Selection Policy (frontend):**

- `primary_yes` o `single`: usar `primary` para métricas.
- `multi`: mostrar badge "Multi (sampled)"; usar `primary` si existe para métricas muestreadas.
- `none`: mostrar "Token IDs unavailable"; no hay token para métricas.

**Importante:** no inferir YES/NO desde una lista por posición; solo cuando el backend expone `primary_yes` / `primary_no` (Gamma envió un dict con esas keys).

### Query params

**Reenviados a Gamma (proxy):** `limit`, `offset`, `order`, `ascending`, `closed`, `tag_id`.

**Aplicados en backend (filtrado post-Gamma):** `category`, `enabled`, `series_id`, `search`.

| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| limit | int | 50 | Máx 100. Items por página. |
| offset | int | 0 | Offset de paginación. |
| order | string | "createdAt" | Campo de orden (p. ej. createdAt, updatedAt). Si Gamma no soporta el valor, backend puede hacer fallback a createdAt. |
| ascending | bool | false | Orden ascendente. |
| closed | string | "false" | Incluir markets cerrados. |
| tag_id | string | — | Filtrar por tag (Gamma). |
| category | string | — | Filtrar por categoría (client-side). |
| enabled | bool | — | Filtrar por estado enabled (client-side). |
| series_id | string | — | Filtrar por serie (client-side). |
| search | string | — | Búsqueda por nombre (client-side). |

### Ejemplo de request (copy-paste)

```http
GET /markets?limit=50&offset=0&order=createdAt&ascending=false&closed=false
GET /markets?limit=20&offset=40&tag_id=abc123
GET /markets?enabled=true&limit=50
```

### Headers de respuesta

La metadata **no** va en el body; va en cabeceras:

| Header | Descripción |
|--------|-------------|
| X-Limit | Límite aplicado. |
| X-Offset | Offset de la respuesta. |
| X-Has-More | "true" si la última llamada a Gamma devolvió exactamente `limit` items → **probablemente** hay más. Gamma no expone total, sobre todo con filtros. |
| X-Order-Effective | Orden efectivamente usado. |
| X-Gamma-Fetch-Count | Número de chunks pedidos a Gamma en esta request. |
| X-Gamma-Scanned | Número total de items escaneados en Gamma. |
| X-Enabled-Filter-Applied | "true" si se aplicó filtro `enabled`. |
| X-Offset-Mode | "gamma" o "filtered" (cuando hay filtro enabled). |
| X-Partial-Page | "true" si la página se truncó por max_scanned o max_iterations (two-phase). |
| X-Partial-Reason | "max_scanned" o "max_iterations" cuando aplica. |

---

## Precedencia de spread (UI)

Para mostrar spread/depth/impact en la UI, usar este orden:

1. **Gamma spread** no-null (si el backend lo expone en el item).
2. **Gamma bestBid / bestAsk** ambos no-null → calcular spread; si hay inconsistencia con spread, confiar en spread.
3. **State cache** (orderbook-metrics).
4. Mensaje de fallback: "Not subscribed" o "Token IDs unavailable" según política de tokens.

---

## GET /markets/orderbook-metrics

**Query:** `token_ids=id1,id2,...` (máximo 100; dedupe; 400 si excede).

**Response shape estable:**

```json
{
  "found_token_ids_count": 12,
  "missing_token_ids_count": 8,
  "partial": true,
  "timed_out": true,
  "errors": ["timeout"],
  "metrics": {
    "tokenId1": {
      "spread_bps": 50,
      "depth_usdc_at_50bps": 1000,
      "impact_bps_for_usdc_1000": 30
    },
    "tokenId2": null
  }
}
```

- `partial`: true si no se pudieron obtener todas las métricas (timeout, errores).
- `timed_out`: true si se alcanzó el timeout global.
- `errors`: lista de mensajes cortos (p. ej. "timeout").
- `metrics`: un entry por token_id; valor `null` si no hay datos para ese token.

El endpoint tiene timeout estricto (~80ms); **siempre** responde con este shape (nunca falla la request entera; puede devolver partials).

---

## Add to Universe

### POST /api/strategies/{strategy_id}/universe/markets

**Body:** `{ "market_id": "<gamma_market_id>" }`.

**Comportamiento:**

- Añade el market a `universe_config.markets` de la estrategia si no existe.
- **Idempotente:** si ya está en el universo, responde 200 con `added: false`.
- **Fuente de verdad:** la DB es la fuente de verdad del universo por estrategia. Cualquier cache de tipo `strategy:{id}:universe` debe invalidarse al hacer POST.

**Respuesta éxito (200):**

```json
{
  "added": true,
  "universe": { ... }
}
```

o `"added": false` cuando el market ya estaba en el universo.

**Errores:**

- **400** — "Market disabled internally": el market está deshabilitado (MarketEnabledState). No se añade a universo.
- **404** — Estrategia no encontrada.

**Auth:** mismo que PUT universe (p. ej. get_admin_user).

---

## Resumen de contratos

| Contrato | Regla |
|----------|--------|
| GET /markets | Siempre array; metadata en headers. |
| clob_token_ids | `selection_hint` + `primary`; no asumir list[0]=YES. |
| X-Has-More | true solo si última llamada Gamma devolvió exactamente `limit` items. |
| orderbook-metrics | Shape fijo; partials siempre; timeout ~80ms. |
| Add to Universe | Idempotente; 400 si market disabled; DB fuente de verdad; invalidar cache al POST. |
