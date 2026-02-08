# Plan: Polymarket-style Discovery & Market-First UX

Refactorizar la búsqueda de mercados para replicar la UX de Polymarket (crypto, politics, sports) con URLs legibles, filtrado server-side cuando sea posible y Add to Universe.

---

## 1. Definición y reglas

### Visión

- **Market-first**: la UI lista mercados tradeables directamente, no events como contenedor principal.
- **URL-driven**: el estado de la vista se deriva completamente de la URL.
- **Gamma-first**: no usar DB para discovery; fuente = Gamma API.
- **Fail-closed**: si los datos faltan o son inconsistentes, ocultar el market.

### Criterios de inclusión (tradeable, fail-closed)

**Market** (todos obligatorios):

- `market.active === true`
- `market.acceptingOrders === true`
- `market.archived !== true`
- `market.closed !== true` ← importante para evitar ruido histórico

**Event**:

- `event.archived !== true` ← evita mostrar basura
- (opcional) `event.active === true` si sirve como gating adicional

**TTR** (cuando aplique):

- `timeToResolution <= timeBucket`

Estos criterios limpian muchísimo ruido de datos históricos / raros.

---

## 2. Estructura de URLs

| Ruta | Significado | Ejemplo |
|------|-------------|---------|
| `/[domain]/[timeBucket]` | Crypto/politics con max TTR | `/crypto/15M`, `/politics/1D` |
| `/sports/[league]/games` | Liga → partidos | `/sports/nfl/games` |
| `/sports/live` | Partidos en vivo | `/sports/live` |

**Regla**: las URLs usan siempre **slugs**. Nunca `tag_id` numérico en la ruta.

---

## 3. DomainRegistry y LeagueRegistry (config)

**Regla de jerarquía URL**:

- `/{domain}/{timeBucket}` → contexto **crypto/politics/general** (ej. `/crypto/15M`)
- `/sports/{league}/games` → contexto **sports** (ej. `/sports/nfl/games`)
- `/sports/live` → contexto **sports live**

No mezclar leagues como top-level. NFL/NBA son **league slugs**, no domain slugs.

### DOMAIN_REGISTRY (dominios raíz: crypto, politics, general)

```ts
// frontend: lib/discovery/domain-registry.ts
interface DomainEntry {
  domainSlug: string;      // Lo que va en la URL (/crypto, /politics)
  gammaTagSlug: string;    // Lo que se manda a Gamma (tag_slug)
  gammaTagId?: string;     // Fallback si Gamma requiere id
  category: 'crypto' | 'politics' | 'general';
  supportsTimeBucket: boolean;  // true para crypto/politics
}

const DOMAIN_REGISTRY: DomainEntry[] = [
  { domainSlug: 'crypto', gammaTagSlug: 'crypto', gammaTagId: '21', category: 'crypto', supportsTimeBucket: true },
  { domainSlug: 'politics', gammaTagSlug: 'politics', category: 'politics', supportsTimeBucket: true },
  { domainSlug: 'general', gammaTagSlug: '', category: 'general', supportsTimeBucket: false },
];
```

### LEAGUE_REGISTRY (ligas dentro de /sports/)

```ts
interface LeagueEntry {
  leagueSlug: string;      // Lo que va en la URL (/sports/nfl/...)
  gammaTagSlug: string;    // Lo que se manda a Gamma (tag_slug)
  gammaTagId?: string;     // Fallback
}

const LEAGUE_REGISTRY: LeagueEntry[] = [
  { leagueSlug: 'nfl', gammaTagSlug: 'nfl', gammaTagId: '...' },
  { leagueSlug: 'nba', gammaTagSlug: 'nba' },
  { leagueSlug: 'ncaab', gammaTagSlug: 'ncaab' },
  { leagueSlug: 'nhl', gammaTagSlug: 'nhl' },
  { leagueSlug: 'ufc', gammaTagSlug: 'ufc' },
  // ...
];
```

- **URL usa slug** (`/crypto`, `/sports/nfl/games`).
- **Backend** resuelve slug → parámetros Gamma; preferir siempre `tag_slug`.
- **Fallback** a `tag_id` solo si Gamma no soporta `tag_slug` en un endpoint concreto.

---

## 4. TimeBucket = max TTR

### Estrategia (server-first + fail-closed)

1. **Backend/proxy**: filtrar por `endDate` o `end_date_max` si Gamma lo soporta, para limitar el volumen de datos.
2. **Client-side**: re-validar `timeToResolution <= timeBucket` (fail-closed).

Si no filtramos en backend, se traen demasiados events y la UI es ruidosa y lenta.

### Mapeo timeBucket → minutos

| timeBucket | Max minutos |
|------------|-------------|
| 5M | 5 |
| 15M | 15 |
| 1H | 60 |
| 1D | 1440 |

### Verificación Gamma (filtro por fecha)

Probar en la API de Gamma:

```bash
# ¿Gamma acepta end_date_max o similar?
GET /events?closed=false&tag_slug=crypto&end_date_max=2026-02-08T00:00:00Z&limit=25

# ¿Existe endDate como query param?
GET /events?closed=false&tag_slug=crypto&endDate=...&limit=25

# ¿Hay un rango start/end?
GET /events?closed=false&tag_slug=crypto&start_date=...&end_date=...&limit=25
```

Si Gamma no expone filtro por fecha, el proxy puede:

- Calcular `end_date_max = now + timeBucket_minutes` y pasarlo si existe param equivalente.
- O devolver más datos y documentar que el filtrado TTR es solo client-side hasta que Gamma lo soporte.

---

## 5. Endpoint Discovery (tradeable-markets)

**Nombre**: `GET /api/polymarket/discovery`

**Respuesta**: lista plana de mercados tradeables, cada uno con metadata mínima del event.

```ts
interface DiscoveryMarket {
  market_id: string;
  polymarket_id: string;
  question: string;
  clob_token_ids: { primary_yes?: string; primary_no?: string; primary?: string };
  active: boolean;
  acceptingOrders: boolean;
  archived: boolean;
  closed: boolean;
  liquidity?: number;
  volume24hr?: number;
  // metadata del event (para contexto)
  event_id: string;
  event_title: string;
  event_end_date: string;
  event_archived: boolean;
  event_tags: { slug: string; label: string }[];
  series_slug?: string;
  time_to_resolution_minutes?: number;
}
```

**Query params**:

- `tag_slug` (slug del dominio o liga)
- `closed` = false
- `end_date_max` o equivalente (si Gamma lo soporta)
- `limit`, `offset` — ver **Overfetch** abajo
- `live` (opcional, ver sección 7)

**Lógica**:

- Obtener events desde Gamma con `tag_slug`, `closed=false` y fecha si existe.
- Filtrar events: `event.archived !== true` (y opcional `event.active === true`).
- Aplanar: por cada event → sus markets.
- Filtrar markets: `active && acceptingOrders && !archived && !closed`.
- Ordenar con **ranking compuesto** (sección 5.1).
- Incluir metadata mínima del event en cada market.

### 5.1 Paginación + Overfetch

Para evitar pantallas vacías cuando el filtro TTR (client-side) elimina muchos ítems:

1. **Proxy**: pedir `limit=100` o `limit=200` al proxy.
2. **Filtrar**: aplicar criterios tradeable + TTR (client-side).
3. **Devolver a UI**: solo `limit=50` (o lo que la UI muestre por página).
4. **Auto-fetch**: si quedan pocos tras filtrar, pedir la siguiente página automáticamente.

Ejemplo: proxy devuelve 100, filtro deja 12 → UI muestra 12 y dispara fetch de offset+100 para intentar llenar la vista.

### 5.2 Ordenación: ranking compuesto

No solo "sort by X". Lo relevante en Polymarket suele ser: tradeables con liquidez/volumen reciente primero, luego cercanía a resolución (según vista).

**Fórmula de score**:

```
score = (w1 * volume24hr) + (w2 * liquidity) + (w3 * recencyBoost) - (w4 * timeToResolutionPenalty)
```

- `volume24hr`, `liquidity`: normalizados (p.ej. log1p para atenuar outliers).
- `recencyBoost`: bonus por actividad reciente.
- `timeToResolutionPenalty`: penalización si TTR es muy alto (para vistas cortas) o muy bajo (ya casi cerrado).

**Alternativa sin score** (orden explícito):

1. `volume24hr` desc
2. `liquidity` desc
3. `timeToResolution` asc (lo que cierra antes, primero)

---

## 6. Search (q=)

### Estrategia en 2 fases

1. **Candidatos por URL**: dominio + timeBucket + closed=false (params del discovery).
2. **Búsqueda local**: sobre el conjunto reducido de candidatos.

### Campos indexados (Fuse / BM25)

- `event.title`
- `market.question`
- slugs (`event.slug`, `market.slug`)
- tags (labels, slugs)
- series (`series.title`, `series.slug`)
- **Tokens normalizados**: sin acentos, sin guiones, sin mayúsculas (ej. "Will BTC hit 100k?" → "will btc hit 100k")

### Normalización y precisión percibida

- **Normalización**: lowercasing, trim, eliminar acentos, colapsar guiones/underscores.
- **Sinónimos** (mejora grande de precisión percibida):

| Query | Expansión |
|-------|-----------|
| btc | bitcoin |
| eth | ethereum |
| nfl | football |
| nba | basketball |
| psg | paris saint germain |
| trump | donald trump |
| ... | (configurable) |

- **Boosting** (ejemplo):
  - `market.question`: 1.2
  - `event.title`: 1.0
  - tags/slugs: 0.8
- **Threshold**: score mínimo para considerar match (p.ej. 0.3 en Fuse).

### Flujo

1. Usuario introduce `q=btc` en la barra de búsqueda.
2. Fetch: `GET /api/polymarket/discovery?tag_slug=crypto&closed=false&limit=100` (o el conjunto ya cargado).
3. Indexar en memoria con Fuse/BM25.
4. Buscar `q` sobre candidatos.
5. Renderizar solo los matches que pasen el threshold.

---

## 7. Sports Live

**Importante**: `live` no es un `tag_slug` en Gamma. Es un estado/heurística.

### Definición de "live"

- `now >= startDate - tolerance_start` y `now <= endDate + tolerance_end`.
- En deportes, `endDate` muchas veces no coincide con el fin real; hay delays.
- Siempre `market.acceptingOrders === true`.

### Heurística con tolerancias (configurable por liga)

```ts
// Config: tolerancias en minutos
const LIVE_TOLERANCES = {
  default: { startMinutes: 15, endMinutes: 4 * 60 },  // -15min inicio, +4h fin
  nfl: { startMinutes: 15, endMinutes: 4 * 60 },
  nba: { startMinutes: 15, endMinutes: 3 * 60 },
  // ...
};

function isLiveEvent(event: GammaEvent, league?: string): boolean {
  const now = Date.now();
  const cfg = LIVE_TOLERANCES[league ?? 'default'] ?? LIVE_TOLERANCES.default;
  const start = new Date(event.startDate).getTime() - cfg.startMinutes * 60 * 1000;
  const end = new Date(event.endDate).getTime() + cfg.endMinutes * 60 * 1000;
  return now >= start && now <= end;
}
```

Y para cada market del event: `market.acceptingOrders === true`.

### Backend

- Si Gamma tiene algo como `?live=true` o `?in_play=true`, usarlo.
- Si no, el proxy `/discovery` puede:
  - Recibir `live=true` (y opcional `league` para tolerancias).
  - Traer events (p.ej. `tag_slug=sports`) y filtrar server-side con la heurística + `acceptingOrders`.

---

## 8. Verificación Gamma (checklist)

### Filtros por tag

```bash
GET /events?closed=false&tag_slug=nfl&limit=25
GET /events?closed=false&tag_slug=crypto&limit=25
GET /events?closed=false&tag_slug=politics&limit=25
```

### Filtros por fecha

```bash
GET /events?closed=false&tag_slug=crypto&end_date_max=2026-02-08T00:00:00Z&limit=25
GET /events?closed=false&tag_slug=crypto&endDate=...&limit=25
GET /events?closed=false&tag_slug=crypto&start_date=...&end_date=...&limit=25
```

### Live

```bash
# ¿Existe parámetro live/in_play?
GET /events?closed=false&tag_slug=sports&live=true&limit=25
GET /events?closed=false&tag_slug=sports&in_play=true&limit=25
```

### Ordenación

```bash
# ¿Soporta order por liquidez/volumen?
GET /events?closed=false&tag_slug=crypto&order=liquidity&limit=25
GET /events?closed=false&tag_slug=crypto&order=volume24hr&limit=25
```

---

## 9. Implementación por fases

### Fase 1: DomainRegistry + LeagueRegistry + proxy

- [ ] Crear `domain-registry.ts` (DOMAIN_REGISTRY: crypto, politics, general).
- [ ] Crear `league-registry.ts` (LEAGUE_REGISTRY: nfl, nba, ncaab, nhl, ufc, ...).
- [ ] Extender proxy `/api/polymarket/events` con `tag_slug` y params de fecha (si Gamma los soporta).
- [ ] Ejecutar checklist de verificación Gamma y documentar hallazgos.

### Fase 2: Endpoint Discovery

- [ ] Implementar `GET /api/polymarket/discovery`.
- [ ] Aplanar events → markets tradeables.
- [ ] Filtrar: `active`, `acceptingOrders`, `!archived`, `!closed`, `event.archived !== true`.
- [ ] Ordenar con ranking compuesto (o volume24hr desc, liquidity desc, timeToResolution asc).
- [ ] Paginación + overfetch (limit 100/200 al proxy, devolver 50 a UI, auto-fetch si quedan pocos).
- [ ] Incluir metadata mínima de event en cada market.

### Fase 3: Routing y páginas

- [ ] `app/markets/[domain]/[timeBucket]/page.tsx` (crypto, politics).
- [ ] `app/sports/[league]/games/page.tsx` (nfl, nba, etc.).
- [ ] `app/sports/live/page.tsx`.
- [ ] UI derivada 100% de la URL.

### Fase 4: Filtrado TTR

- [ ] Pasar `end_date_max` (o equivalente) al proxy si Gamma lo soporta.
- [ ] Re-validación client-side `timeToResolution <= timeBucket` (fail-closed).

### Fase 5: Search (q=)

- [ ] Integrar Fuse/BM25 en frontend.
- [ ] Tokens normalizados + sinónimos (btc↔bitcoin, eth↔ethereum, nfl↔football, psg↔paris saint germain, etc.).
- [ ] Definir campos, boosting y threshold.
- [ ] Barra de búsqueda sobre candidatos ya cargados.

### Fase 6: Sports Live

- [ ] Heurística con tolerancias: `now >= startDate - 15min` y `now <= endDate + 4h` (configurable por liga).
- [ ] Siempre `acceptingOrders === true`.
- [ ] Usar param Gamma `live`/`in_play` si existe.
- [ ] Página `/sports/live` funcionando.

### Fase 7: Add to Universe

- [ ] Mantener flujo actual POST `universe/markets` desde la nueva UI.
- [ ] Confirmación antes de añadir.

---

## 10. Archivos relevantes

| Archivo | Cambios |
|---------|---------|
| `frontend/lib/discovery/domain-registry.ts` | Nuevo: DOMAIN_REGISTRY (crypto, politics, general) |
| `frontend/lib/discovery/league-registry.ts` | Nuevo: LEAGUE_REGISTRY (nfl, nba, ...) |
| `frontend/lib/discovery/discovery-client.ts` | Cliente para /discovery |
| `frontend/app/markets/[domain]/[timeBucket]/page.tsx` | Nueva ruta crypto/politics |
| `frontend/app/sports/[league]/games/page.tsx` | Nueva ruta sports |
| `frontend/app/sports/live/page.tsx` | Nueva ruta live |
| `backend/app/api/polymarket.py` | Endpoint /discovery, params tag_slug, end_date_max, live |
| `docs/implementation/PLAN_POLYMARKET_STYLE_DISCOVERY.md` | Este plan |

---

## 11. Referencias

- Polymarket: [crypto/15M](https://polymarket.com/crypto/15M), [sports/nfl/games](https://polymarket.com/sports/nfl/games), [sports/live](https://polymarket.com/sports/live)
- Gamma API: [List events](https://docs.polymarket.com/api-reference/events/list-events)
- Gamma API: [Fetching Markets](https://docs.polymarket.com/developers/gamma-markets-api/fetch-markets-guide)
