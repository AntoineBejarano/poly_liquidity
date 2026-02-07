# Flujo al activar una estrategia (y cuándo no te deja)

## Resumen

Al pulsar **Activar** en una estrategia (p. ej. Near Resolution), el frontend llama al backend. El backend **sí puede rechazar** la petición en unos pocos casos; el **precheck** (orderbook, precio, impacto, TTL) **no** se ejecuta en el momento de activar, sino más tarde, cuando ya está activa y el control loop intenta ejecutar un plan.

---

## 1. Qué pasa cuando le das a Activar

### Frontend (`live/page.tsx`)

- **Modo Demo:** al hacer click en Activar, **no** se llama al API. Se actualiza solo el estado local: `setStrategy(prev => ({ ...prev, is_active: true, enabled_at: now }))`. La UI pasa a mostrar la estrategia como activa (Pausar/Detener visibles, datos mock o vacíos). Pausar y Detener en Demo también solo revierten el estado local (sin API).
- **Modo Simulación / Live:** se comprueba que haya estrategia cargada y que no haya petición en curso (`isActivating`). En Simulación, si el backend está en modo LIVE, no se llama al API y se muestra un mensaje en banner pidiendo elegir "Simulación" en el selector. Si no, se llama a `POST /api/strategies/{strategy_id}/activate`. Si la respuesta es correcta, se actualiza el estado con la estrategia devuelta por el backend. Si hay error (403, 400, 404), se muestra un **banner de error** bajo el header con el mensaje del backend (no `alert()`).
- El botón **Activar** se muestra cuando `strategy.is_active === false`. En Demo el click sí tiene efecto (activación simulada en estado local).

### Backend (`POST /api/strategies/{strategy_id}/activate`)

1. **Comprueba** que la estrategia exista y que el usuario sea **admin** (`get_admin_user`). Si no, responde 404 o 403 y **no activa**.
2. **Comprueba** que la estrategia no esté ya activa. Si ya está activa, responde **400** y **no activa**.
3. Obtiene los `asset_ids` (token IDs de Polymarket) de los **eventos asignados** a la estrategia (`StrategyEvent` + `event.polymarket_payload.clobTokenIds` o del market).
4. **Suscribe** la estrategia a los orderbooks de esos `asset_ids` (para que el control loop pueda usar datos de libro).
5. Marca la estrategia como activa en DB: `is_active = True`, `enabled_at = now`, `disabled_at = None`.
6. Responde 200 con la estrategia actualizada.

La activación **no falla** si la estrategia tiene **cero eventos** asignados: en ese caso `asset_ids` queda vacío, se loguea un warning y la estrategia se marca activa igual. Tampoco se hace en este endpoint ninguna validación de “near resolution listo” (umbrales, liquidez, etc.).

---

## 2. Casos en que NO te deja activar (se bloquea)

### En el frontend (no llega request)

| Condición | Efecto |
|-----------|--------|
| **Modo Demo** | No se llama al API; se actualiza solo estado local (estrategia “activa” en UI con datos mock/vacíos). |
| **Estrategia ya activa** | El header muestra Pausar/Detener en lugar de Activar; no hay botón Activar. |
| **Mientras “Activando…”** | `isActivating === true` deshabilita el botón y evita doble click. |

### En el backend (respuesta 4xx)

| Caso | Código | Mensaje / detalle |
|------|--------|-------------------|
| **Estrategia no encontrada** | **404** | `Strategy not found` |
| **Usuario no admin** | **403** | `Admin access required` (el endpoint usa `get_admin_user`) |
| **Estrategia ya activa** | **400** | `Strategy is already active` |

No hay en el backend comprobaciones de:

- Que tenga eventos asignados.
- Que los eventos tengan `clobTokenIds` o orderbook.
- Que la configuración sea “válida” para Near Resolution (price_min/max, liquidez, etc.).

Eso significa: **sí te deja activar** una estrategia Near Resolution sin eventos o sin mercados listos; lo que puede “fallar” después es la **generación o ejecución** de planes (control loop + precheck).

---

## 3. Near Resolution: qué pasa después de activar

Una vez la estrategia está **activa**:

1. El **control loop** la ve como activa y, para cada evento asignado, puede generar **planes de ejecución** (ExecutionPlan) según la lógica del grafo (triggers, liquidez near resolution, etc.).
2. Antes de ejecutar un plan, el nodo **Precheck** valida:
   - **TTL del plan**: que no haya expirado.
   - **Frescura del orderbook** (staleness).
   - **Drift del precio** (target vs best ask/bid).
   - **Impacto de mercado** (impact_bps).

Si el **precheck falla**, ese plan no se ejecuta (no se envía orden), se registra el fallo y se puede emitir `precheck_failed` por WebSocket. La estrategia **sigue activa**; solo ese plan concreto se rechaza.

Por tanto:

- **Activar** no depende de precheck ni de “near resolution listo”.
- **Ejecutar una orden** sí depende de que exista un plan y de que el precheck pase.

Si no asignas eventos o los eventos no tienen orderbook/asset_ids, la estrategia se activa pero no habrá suscripción a orderbooks ni planes que ejecutar hasta que asignes eventos con datos válidos.

---

## 4. Resumen rápido (Near Resolution)

- **Demo:** Activar/Pausar/Detener solo cambian estado local; no se llama al API. La UI muestra la estrategia activa o pausada con datos mock o vacíos.
- **Simulación / Live:** Activar llama al API. Te deja activar siempre que la estrategia exista, no esté ya activa y seas admin. No se exige tener eventos asignados ni “readiness”.
- **No te deja activar en backend** (4xx): 404 estrategia no encontrada, 403 no admin, 400 ya activa.
- El **precheck** (orderbook, precio, impacto, TTL) **no** bloquea la activación; solo bloquea la **ejecución** de un plan concreto cuando la estrategia ya está activa.

---

## 5. Comportamiento por modo (Demo / Simulación / Live)

| Acción o visibilidad | Demo | Simulación | Live |
|----------------------|------|------------|------|
| Click **Activar** | Solo estado local; UI muestra “activa” con datos mock/vacíos | Llama API; backend activa (DRY_RUN) | Llama API; backend activa (LIVE) |
| Click **Pausar / Detener** | Solo estado local; no API | Llama API | Llama API |
| Datos (métricas, eventos, health, intents) | Mock o vacíos; sin llamadas backend | Reales (backend) | Reales (backend) |
| Banner | “Modo Demo” | “Modo Simulación — órdenes simuladas (DRY_RUN)” | Ninguno (o indicador “LIVE” discreto) |
| Botones Configurar, Desk, Métricas, Logs | Habilitados (navegación normal) | Habilitados | Habilitados |

---

## 6. Docs relacionados

- **Control loop, planes, precheck:** [architecture/execution-engine.md](../architecture/execution-engine.md).
- **Ciclo de órdenes (envío, fills, cancelación):** [exchange/order-lifecycle.md](../exchange/order-lifecycle.md).
- **Modo DRY_RUN/LIVE como input determinista:** [architecture/config-driven.md](../architecture/config-driven.md).
- **Por qué puede estar activa pero no operar (quorum, readiness):** [architecture/quorum.md](../architecture/quorum.md).
