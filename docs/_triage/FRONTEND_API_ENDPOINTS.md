# Endpoints de Gamma API para Frontend

Este documento describe los endpoints de Gamma API que son útiles para la configuración del bot desde el frontend.

## Base URL

```
https://gamma-api.polymarket.com
```

## Endpoints Principales

### 1. Listar Eventos (con Paginación)

**GET** `/events`

Obtiene lista de eventos con sus mercados asociados. Retorna un array directo de eventos.

**Parámetros de Query:**
- `order` (string): Orden de resultados (`id`)
- `ascending` (boolean): Orden ascendente (`false` = más nuevos primero)
- `closed` (boolean): Incluir cerrados (`false` = solo activos)
- `limit` (number): Resultados por página (default: 50, max: 100)
- `offset` (number): Offset para paginación

**Ejemplo:**
```bash
curl "https://gamma-api.polymarket.com/events?order=id&ascending=false&closed=false&limit=100&offset=0"
```

**Respuesta:**
```json
[
  {
    "id": "event-id",
    "slug": "event-slug",
    "title": "Event Title",
    "markets": [...],
    "active": true,
    "closed": false,
    "volume24hr": 123,
    "liquidity": 123
  }
]
```

### 2. Obtener Evento por ID

**GET** `/events/{id}`

Obtiene un evento específico con todos sus detalles y mercados.

**Ejemplo:**
```bash
curl "https://gamma-api.polymarket.com/events/{event-id}"
```

**Respuesta:**
```json
{
  "id": "event-id",
  "slug": "event-slug",
  "title": "Event Title",
  "description": "...",
  "startDate": "2023-11-07T05:31:56Z",
  "endDate": "2023-11-07T05:31:56Z",
  "active": true,
  "closed": false,
  "markets": [...],
  ...
}
```

### 3. Obtener Mercado por ID

**GET** `/markets/{id}`

Obtiene un mercado específico con información completa.

**Campos Importantes:**
- `id` - ID del mercado
- `conditionId` - ID de condición (para WebSocket/CLOB)
- `slug` - Slug del mercado
- `question` - Pregunta del mercado
- `outcomes` - Array de outcomes
- `bestBid` / `bestAsk` - Mejores precios
- `volume24hr` - Volumen de 24h
- `clobTokenIds` - IDs de tokens para CLOB
- `enableOrderBook` - Si orderbook está habilitado

**Ejemplo:**
```bash
curl "https://gamma-api.polymarket.com/markets/{market-id}"
```

**Respuesta:**
```json
{
  "id": "market-id",
  "question": "Will X happen?",
  "conditionId": "condition-id",
  "slug": "market-slug",
  "outcomes": [...],
  "bestBid": 0.45,
  "bestAsk": 0.55,
  "volume24hr": 12345,
  "liquidity": 50000,
  "active": true,
  "closed": false,
  "clobTokenIds": "...",
  "enableOrderBook": true,
  ...
}
```

### 4. Obtener Mercado por Slug

**GET** `/markets/slug/{slug}`

Útil para obtener un mercado desde su URL de Polymarket.

**Ejemplo:**
```bash
# URL: https://polymarket.com/event/fed-decision-in-october
# Slug: fed-decision-in-october

curl "https://gamma-api.polymarket.com/markets/slug/fed-decision-in-october"
```

### 5. Búsqueda Pública

**GET** `/public-search`

Busca eventos, mercados, tags y perfiles. Muy útil para el frontend.

**Parámetros de Query:**
- `q` (string): Término de búsqueda
- `limit` (number): Resultados por página
- `offset` (number): Offset para paginación

**Ejemplo:**
```bash
curl "https://gamma-api.polymarket.com/public-search?q=bitcoin&limit=20&offset=0"
```

**Respuesta:**
```json
{
  "events": [...],
  "markets": [...],
  "tags": [...],
  "profiles": [...],
  "pagination": {
    "hasMore": true,
    "totalResults": 123
  }
}
```

## Casos de Uso para Frontend

### 1. Selector de Mercados

El frontend puede usar `/public-search` o `/events` para permitir al usuario:
- Buscar mercados por término
- Filtrar por categoría/tags
- Ver información básica (precio, volumen, liquidez)

### 2. Configuración de Bot

Cuando el usuario selecciona un mercado, el frontend puede:
1. Obtener detalles completos con `/markets/{id}` o `/markets/slug/{slug}`
2. Extraer `conditionId` y `clobTokenIds` para configuración
3. Mostrar información relevante: `bestBid`, `bestAsk`, `volume24hr`, etc.

### 3. Validación de Mercados

El frontend puede validar que un mercado es válido antes de configurar el bot:
- Verificar `active: true` y `closed: false`
- Verificar `enableOrderBook: true`
- Verificar que tiene `clobTokenIds`

### 4. Monitoring/Dashboard

El frontend puede usar estos endpoints para:
- Mostrar lista de mercados activos
- Actualizar precios periódicamente (`bestBid`, `bestAsk`)
- Mostrar volumen y liquidez en tiempo real

## Integración con Backend

### Opción 1: Frontend llama directamente a Gamma API

**Ventajas:**
- Más rápido (sin pasar por backend)
- Menos carga en backend

**Desventajas:**
- CORS puede ser un problema
- Credenciales deben estar en frontend (si requiere autenticación)

### Opción 2: Backend actúa como Proxy

Crear endpoints en nuestro backend que llamen a Gamma API:

```python
# backend/app/api/polymarket.py

@router.get("/markets/{market_id}")
async def get_market(market_id: str):
    """Obtiene mercado desde Gamma API."""
    client = httpx.AsyncClient()
    response = await client.get(
        f"{settings.polymarket_gamma_api_url}/markets/{market_id}"
    )
    return response.json()

@router.get("/markets/slug/{slug}")
async def get_market_by_slug(slug: str):
    """Obtiene mercado por slug desde Gamma API."""
    client = httpx.AsyncClient()
    response = await client.get(
        f"{settings.polymarket_gamma_api_url}/markets/slug/{slug}"
    )
    return response.json()

@router.get("/search")
async def search(q: str, limit: int = 20, offset: int = 0):
    """Búsqueda pública de mercados."""
    client = httpx.AsyncClient()
    response = await client.get(
        f"{settings.polymarket_gamma_api_url}/public-search",
        params={"q": q, "limit": limit, "offset": offset}
    )
    return response.json()
```

**Ventajas:**
- Control de rate limiting
- Cache centralizado
- Manejo de errores consistente
- No problemas de CORS

**Desventajas:**
- Más latencia (una llamada extra)
- Más carga en backend

## Recomendación

Para la configuración inicial del bot, recomiendo:
1. **Backend como Proxy** para búsqueda y validación de mercados
2. **Cache agresivo** en backend (5-30 segundos) para reducir llamadas
3. **Rate limiting** para proteger la API de Gamma

Esto permite:
- Validación centralizada de mercados
- Cache compartido entre usuarios
- Mejor control sobre uso de API

