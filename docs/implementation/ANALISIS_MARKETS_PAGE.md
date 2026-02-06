# Análisis: Página /markets

**Objetivo:** Documentar el estado actual de la página `/markets`, identificar gaps (filtros, paginación, spread/liquidez/impact, botón Add to Universe) y proponer vías de trabajo.

**Última revisión:** Feb 2025

---

## 1. Estado actual

### 1.1 Componentes implicados

| Componente | Ruta / ubicación | Función |
|------------|------------------|---------|
| Página principal | `frontend/app/markets/page.tsx` | Tabla de markets, filtros, métricas, botón Add to Universe |
| API get markets | `backend/app/api/markets.py` → `GET /markets` | Devuelve markets desde Gamma API + estado enabled de DB |
| API orderbook metrics | `backend/app/api/markets.py` → `GET /markets/orderbook-metrics` | Devuelve spread, depth, impact por token_id |
| State Cache | `backend/app/core/strategy_engine/state_cache_service.py` | Fuente de `pm.orderbook.{asset_id}` para métricas |
| Orderbook engine | `backend/app/core/orderbook/` | Publica a State Cache solo para tokens suscritos (estrategias activas) |

### 1.2 Flujo de datos actual

```
Gamma API (markets) → get_markets() → Frontend
                    ↓
         MarketEnabledState (DB) → enabled por market

State Cache (pm.orderbook.*) ← Orderbook WS (solo tokens suscritos)
                    ↓
         get_markets_orderbook_metrics() → Frontend
```

---

## 2. Problemas identificados

### 2.1 Filtros insuficientes

| Aspecto | Estado actual | Gap |
|---------|---------------|-----|
| **Categoría** | Dropdown en frontend, filtrado en cliente | Backend soporta `?category=` pero el frontend no lo pasa; se cargan todos los markets y se filtra en cliente |
| **Series** | No existe en `/markets` | Backend soporta `?series_id=`; no hay UI |
| **Tags** | No existe en `/markets` | Backend soporta `?tag_id=`; no hay UI |
| **Búsqueda** | Input "Buscar markets...", filtrado en cliente | Backend soporta `?search=`; no se usa |
| **Enabled** | No hay filtro por activo/inactivo | Backend soporta `?enabled=`; no hay UI |

**Impacto:** Se cargan hasta 500 markets (5 páginas × 100) en una sola petición, se filtran en cliente. Con muchos markets, la carga y el filtrado son pesados.

### 2.2 Paginación

| Aspecto | Estado actual | Gap |
|---------|---------------|-----|
| **Backend** | `GET /markets` sin `limit` ni `offset`; devuelve todos los markets fetcheados (hasta 5×100) | No hay paginación server-side |
| **Frontend** | Tabla muestra todos los `filteredMarkets` | No hay paginación ni infinite scroll |

**Impacto:** Con 500 markets, la tabla es muy larga y lenta.

### 2.3 Spread, liquidez e impact no calculados (o vacíos)

| Métrica | Fuente | Por qué aparece N/A |
|---------|--------|---------------------|
| **Spread** | `orderbookMetrics[yesTokenId].spread_bps` | 1) Frontend no tiene `yesTokenId` porque el backend no devuelve `clobTokenIds` en `get_markets`. 2) State Cache solo tiene datos para tokens suscritos (estrategias activas) |
| **Liquidez** | `orderbookMetrics[yesTokenId].depth_usdc_at_50bps` | Mismo motivo |
| **Impact** | `orderbookMetrics[yesTokenId].impact_bps_for_usdc_1000` | Mismo motivo |

**Causas raíz:**

1. **Backend `get_markets` no incluye `clobTokenIds` ni `polymarket_payload`**  
   La Gamma API sí devuelve `clobTokenIds` en cada market, pero el endpoint construye el resultado sin incluirlos:
   ```python
   result.append({
       "market_id": polymarket_id,
       "name": ...,
       "tags": tags,
       # falta: polymarket_payload o clobTokenIds
   })
   ```
   El frontend usa `market.polymarket_payload?.clobTokenIds` → siempre `{}` → `getClobTokenIds()` no devuelve YES/NO → `yesTokenId` es `undefined` → no hay match con `orderbookMetrics`.

2. **State Cache solo tiene orderbook para tokens suscritos**  
   `pm.orderbook.{asset_id}` se llena desde el Orderbook WebSocket cuando una estrategia activa suscribe a esos `asset_id`. En `/markets` se listan muchos más markets que los que tienen estrategias activas, así que la mayoría no tienen orderbook en cache.

### 2.4 Botón "Add to Universe" no funciona

| Aspecto | Estado actual | Gap |
|---------|---------------|-----|
| **Código** | `// TODO: Add to universe` — sin lógica | El botón no hace nada |
| **Significado** | "Añadir market al universo de una estrategia" | El universo es por estrategia (`PUT /api/strategies/{id}/universe` con `markets: [polymarket_id, ...]`) |
| **Contexto** | `/markets` no tiene estrategia seleccionada | Falta flujo: elegir estrategia → añadir market |

**Opciones de diseño:**

- **A)** Modal/dropdown para elegir estrategia → `PUT /strategies/{id}/universe` añadiendo el `polymarket_id` al array `markets`.
- **B)** "Add to Universe" como "Enable market" — redundante con el toggle Enabled que ya existe.
- **C)** Añadir market al universo de la última estrategia vista o de una estrategia por defecto (menos claro para el usuario).

---

## 3. Inventario por capa

### 3.1 Backend

| Endpoint / módulo | Soporta | No soporta / no expone |
|-------------------|---------|-------------------------|
| `GET /markets` | category, search, enabled, series_id, tag_id (query params) | `polymarket_payload`, `clobTokenIds` en respuesta; limit/offset |
| `GET /markets/orderbook-metrics` | spread_bps, depth_usdc_at_50bps, impact_bps_for_usdc_1000 por token_id | Datos solo para markets con orderbook en State Cache (tokens suscritos) |
| `PATCH /markets/{id}/enable` | Activar/desactivar market | — |
| `PUT /api/strategies/{id}/universe` | Actualizar universe con `markets: [polymarket_id, ...]` | — |

### 3.2 Frontend

| Componente | Implementado | Pendiente |
|------------|--------------|-----------|
| Tabla markets | Sí | — |
| Filtro categoría (client-side) | Sí | Pasar filtros al backend |
| Filtros series, tags, enabled | No | Añadir UI y lógica |
| Paginación | No | Añadir (server o client) |
| Columnas spread/liquidity/impact | Sí (UI) | Datos reales (dependen de backend) |
| Token IDs (YES/NO) | Sí (UI) | Datos (requiere `clobTokenIds` en respuesta) |
| Botón Add to Universe | Sí (UI) | Lógica y flujo |

### 3.3 Fuentes de datos

| Dato | Fuente | Disponibilidad en /markets |
|------|--------|----------------------------|
| Markets (nombre, categoría, tags) | Gamma API | ✅ |
| Estado enabled | DB (MarketEnabledState) | ✅ |
| clobTokenIds | Gamma API (en raw market) | ❌ No se pasa al frontend |
| spread_bps, depth, impact | State Cache (`pm.orderbook.*`) | ❌ Solo para tokens suscritos |

---

## 4. Vías de trabajo

### 4.1 Quick wins (corto plazo)

1. **Incluir `clobTokenIds` en `get_markets`**  
   - Añadir `polymarket_payload` (o al menos `clobTokenIds`) en el objeto de cada market.  
   - Con eso el frontend tendrá token IDs y podrá mostrar métricas para los markets que sí tengan orderbook en cache.

2. **Pasar filtros al backend**  
   - Usar `?category=`, `?search=`, `?enabled=`, `?series_id=`, `?tag_id=` en la petición a `/markets`.  
   - Reduce payload y mejora consistencia con el backend.

3. **Implementar "Add to Universe" con selector de estrategia**  
   - Modal/dropdown: elegir estrategia → `PUT /strategies/{id}/universe` con `markets: [...existing, polymarket_id]`.  
   - Requiere `GET /api/strategies` (o lista de estrategias) para el selector.

### 4.2 Mejoras medias

4. **Paginación server-side**  
   - Añadir `limit` y `offset` (o `cursor`) a `GET /markets`.  
   - Frontend: paginación o infinite scroll.

5. **Filtros UI completos**  
   - Añadir filtros por series, tags y enabled en la página.

### 4.3 Mejoras mayores (spread/liquidity/impact para todos los markets)

6. **Orderbook para discovery**  
   El State Cache solo tiene orderbook para tokens suscritos. Para mostrar métricas en todos los markets habría que:
   - **Opción A:** Endpoint que calcule métricas on-demand vía CLOB API para un token (coste y rate limits).
   - **Opción B:** Job/service que suscriba a un conjunto amplio de tokens (discovery) y publique en cache (complejidad alta).
   - **Opción C:** Mostrar métricas solo para markets con datos en cache y dejar claro en UI ("Solo para markets con estrategias activas" o similar).

---

## 5. Checklist de implementación sugerido

| # | Tarea | Prioridad | Dependencias |
|---|-------|-----------|--------------|
| 1 | Incluir `clobTokenIds` (o `polymarket_payload`) en respuesta de `GET /markets` | Alta | Ninguna |
| 2 | Pasar filtros (category, search, enabled, etc.) desde frontend a backend | Media | Ninguna |
| 3 | Add to Universe: modal selector de estrategia + PUT universe | Alta | Lista de estrategias |
| 4 | Paginación: limit/offset en backend + UI en frontend | Media | — |
| 5 | Filtros UI: series, tags, enabled | Baja | Backend ya soporta |
| 6 | Decisión y diseño para métricas orderbook en discovery | Media | Análisis de rate limits CLOB |

---

## 6. Archivos relevantes para cambios

| Cambio | Archivos |
|--------|----------|
| Añadir clobTokenIds a get_markets | `backend/app/api/markets.py` (result.append) |
| Filtros en frontend | `frontend/app/markets/page.tsx` (fetch params, Select/Input) |
| Add to Universe | `frontend/app/markets/page.tsx` (onClick, modal), posible `frontend/components/strategies/StrategySelector.tsx` |
| Paginación backend | `backend/app/api/markets.py` (Query limit, offset) |
| Paginación frontend | `frontend/app/markets/page.tsx` (estado página, botones/scroll) |
| Orderbook metrics (si se cambia enfoque) | `backend/app/api/markets.py`, `backend/app/core/orderbook/`, CLOB API |

---

## 7. Relación con otros planes

- **Directory (PLAN_DISCOVERY_UNIVERSE_STRATEGY_BUILDER):** La página `/markets` puede migrar a leer del Directory cuando exista (cache-first, filtros, paginación).
- **Orderbook Engine:** Las métricas de spread/depth/impact dependen de cómo se publique el orderbook y qué tokens se suscriban.
- **Strategy Universe:** El botón "Add to Universe" actualiza `universe_config.markets` vía `PUT /api/strategies/{id}/universe`.
