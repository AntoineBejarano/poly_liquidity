# Discovery (Gamma-first) vs Wallet (CLOB auth)

Este documento deja claro la separación entre **datos públicos de discovery** y **datos privados por wallet**, y qué endpoints usar en cada caso.

**Referencia externa**: [Polymarket – Fetching Market Data](https://docs.polymarket.com/quickstart/fetching-data), [Gamma API (events, markets, tags, series)](https://docs.polymarket.com/developers/gamma-markets-api/overview). Base URL Gamma: `https://gamma-api.polymarket.com`. Discovery no requiere API key ni auth.

## Políticas

### A) DISCOVERY (público, sin cuenta)

- **Gamma-first**: Toda la data pública de discovery (markets, tags, series) viene de **Gamma** (o del proxy backend a Gamma).
- **NO requiere** cuenta ni wallet.
- La DB legacy (Directory/Scanner) puede existir pero **NO** es fuente de verdad para el UI de discovery.

### B) WALLET-SCOPE (privado, con cuenta)

- No existe CLOB global ni system wallet.
- Todo lo que requiera CLOB auth (balance, orders, trades, place, cancel, WS USER) exige **user_id + wallet en BD**.
- **FAIL CLOSED**: API devuelve 4xx con `{ "error": "WALLET_NOT_CONFIGURED" }`; el engine marca intent FAILED y loguea.

---

## Endpoints: market-data público vs wallet-data privado

### Market-data público (Gamma-first, auth opcional)

| Endpoint | Descripción |
|----------|-------------|
| **GET /markets** | Lista de markets (proxy Gamma). Auth **opcional**: sin token devuelve Gamma; con token hace merge de `enabled` desde DB. Paginación limit/offset, headers X-Has-More, X-Cache, etc. |
| **GET /series** | Lista de series (proxy Gamma). Auth **opcional**. |
| **GET /markets/orderbook-metrics** | Métricas de orderbook por token_ids. Auth **opcional** (discovery sin login). |
| **GET /api/polymarket/tags** | Tags/categorías desde Gamma. **Sin auth**. Cache 1h en backend. |
| **GET /api/polymarket/events** | Eventos (proxy Gamma). **Sin auth**. |
| **GET /api/polymarket/health** | Health Gamma. No toca CLOB. |

Para discovery el frontend puede llamar **sin token**; el backend usa `get_current_user_optional` en /markets y /series y no exige wallet.

### Wallet-data privado (requiere auth + wallet)

| Endpoint | Descripción |
|----------|-------------|
| **GET /api/polymarket/balance** | Balance USDC de la wallet del usuario. |
| **GET /api/polymarket/account/balance** | Idem. |
| **Orders / trades / place / cancel** | CLOB API; requieren wallet configurada. |
| **WebSocket USER channel** | Datos de usuario; requieren wallet. |

Si el usuario no tiene wallet configurada en BD, estos endpoints devuelven **409** con detalle tipo `WALLET_NOT_CONFIGURED`.

### Directory legacy (DB-only, interno)

| Endpoint | Descripción |
|----------|-------------|
| **GET /directory/tags** | Tags desde **DB** (tabla Tag). Poblado por Scanner. No es fuente de verdad para discovery. |
| **GET /directory/categories** | Categorías desde DB. |
| **GET /directory/markets** | Markets desde DB. |
| **GET /directory/events** | Events desde DB. |
| **GET /directory/meta** | Meta de freshness del Scanner. |

- **No** usarlos como dependencia para el UI de discovery (pueden estar vacíos si el Scanner no ha corrido).
- Pueden seguir usándose para flujos internos/admin; documentados como "internal directory cache".

---

## Frontend /markets (discovery)

### Jerarquía Polymarket (orden de filtros en la UI)

1. **Series** (nivel superior): colección/tema (ej. "US Elections 2024", "Champions League"). No se tradea; agrupa Events → Markets. Filtro principal en el dropdown.
2. **Events**: hecho concreto (ej. "Will Trump win 2024?"). Pertenece a una serie; contiene uno o varios markets. La tabla lista **markets** (lo tradeable).
3. **Markets**: contrato binario YES/NO; es lo único que tiene orderbook, precio, volumen y trading.
4. **Tags (etiquetas)**: no son categorías jerárquicas. Son etiquetas muchos-a-muchos (Politics, Crypto, Sports). Segundo dropdown, opcional.

En la UI: orden de filtros = **Serie (colección)** → **Etiquetas** → búsqueda → tabla de **Markets**.

### Endpoints y comportamiento

- **Series (dropdown)**: **GET /series** (Gamma, auth opcional). Primero en la barra de filtros.
- **Etiquetas (dropdown)**: **GET /api/polymarket/tags** (Gamma, sin auth). Fallback: derivar desde GET /markets. No usar "categoría" en la UI; son etiquetas.
- **Tabla de markets**: **GET /markets** con limit/offset y filtros (series_id, tag_id, search). Sin login; "Ver todos" o elegir serie/etiqueta/búsqueda.
- **Orderbook metrics**: **GET /markets/orderbook-metrics** (auth opcional).
- La página no exige usuario ni wallet. Componentes reutilizables usan los mismos endpoints públicos.

---

## Resumen rápido

| Tipo | Ejemplos | Auth | Fuente |
|------|----------|------|--------|
| Market-data público | /markets, /series, /api/polymarket/tags, /markets/orderbook-metrics | Opcional (sin token = Gamma only) | Gamma (proxy backend) |
| Wallet-data privado | /api/polymarket/balance, orders, WS USER | Sí + wallet en BD | CLOB / State Cache |
| Directory legacy | /directory/* | Sí (get_current_user) | DB (Scanner) |

Gamma-first aplica **solo** al discovery público. El directorio legacy no bloquea el UI de discovery.
