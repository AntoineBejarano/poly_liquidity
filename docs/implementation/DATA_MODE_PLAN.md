# Plan por fases: Modo de datos (Demo / Simulación / Real)

## Objetivo

Separar claramente tres fuentes de datos en la aplicación:

1. **Demo** – Datos estáticos/mock para demostración (sin backend o override explícito).
2. **Simulación** – Datos generados por simulaciones de estrategias (backtesting, DRY_RUN, ejecución simulada).
3. **Real** – Datos en vivo del backend (API real, execution_mode PAPER o LIVE).

Se añadirá un **selector de modo de datos** junto al Theme Toggle en el header para activar/desactivar Demo y elegir entre Simulación y Real.

---

## Estado actual (qué hay que cambiar)

### Mezcla actual Demo vs Real

| Ubicación | Comportamiento actual | Qué hacer |
|-----------|------------------------|-----------|
| **Layout header** | Solo ThemeToggle | Añadir DataModeToggle (Demo / Simulación / Real). |
| **Settings Wallets** (`app/settings/wallets/page.tsx`) | Si API falla → `PLACEHOLDER_WALLETS`; si `!isConnected` → badge "Modo Demo". | Respetar modo: Demo = siempre placeholders; Real = solo API; Simulación = N/A aquí. |
| **Settings Checkers** (`app/settings/checkers/page.tsx`) | Si API falla → placeholders; `!isConnected` → "Modo Demo". | Igual: Demo = placeholders; Real = solo API. |
| **Risk** (`app/risk/page.tsx`) | Si API falla → `PLACEHOLDER_CONFIG`; `!isConnected` → "Modo Demo". | Demo = placeholder; Real = solo API. |
| **Settings Config** (`app/settings/config/page.tsx`) | Badge "Demo", mensaje demo cuando backend no conectado. | Mostrar badge según modo; en Real no permitir edición si no hay backend. |
| **Markets** (`app/markets/page.tsx`) | `api.get().catch(() => [])`; badge "Demo Mode" cuando `!isConnected`. | Demo = mock/empty; Real = solo API; mostrar modo en badge. |
| **Decision Traces** (`app/decision-traces/page.tsx`) | Badge "Modo Demo" cuando `!isConnected`; datos siempre de API (no hay fallback mock). | Badge según modo; en Demo opcionalmente mock vacío o mensaje claro. |
| **Desk** (`app/strategies/[id]/desk/page.tsx`) | Si API eventos falla → `mockEvents`; header con "42k/50k", "+3.2%" hardcodeados. | Demo = mock + KPIs demo; Real = API + KPIs de API (cuando existan). |
| **Live** (`app/strategies/[id]/live/page.tsx`) | Muchos `.catch(() => null/[])`; `execution_mode` de backend; risk fallback 5000. | Demo = no llamar API o mock; Simulación = respetar DRY_RUN y datos sim; Real = solo datos reales. |
| **Live-compact** (`app/strategies/[id]/live-compact/page.tsx`) | Mock data fijo (maxCapital 5000, mercados mock). | Demo = mock; Real = datos de API. |
| **SignalAlertsWithLoader** | Siempre `mockAlerts`/`mockValues` (API comentada). | Demo = mock; Real/Sim = llamar API cuando exista. |
| **LiveValuesStreamWithLoader** | Siempre `mockValues`. | Demo = mock; Real/Sim = API. |
| **GlobalSignalHeaderWithLoader** | Siempre `mockGlobalState`. | Demo = mock; Real/Sim = API. |
| **ValuesSnapshotCard** | "Build values snapshot (mock for now)". | Demo = mock; Real = API. |
| **InfrastructureHealthCards** | `api.get().catch(() => null)`. | Según modo: Demo = mock o vacío; Real = API. |
| **OperationalAlertsList** | `api.get().catch(() => null)`. | Igual. |
| **CapitalAllocationTable, PnLBreakdownTable, OpenPositionsTable, LiquidityCard** | `positions` con `.catch(() => [])`. | Demo = [] o mock; Real = API. |
| **StrategyStateDistribution, StrategyStatusTable** | `api.get('/api/strategies')`. | En Demo no llamar o mock; Real = API. |
| **Markets loaders** (CategoriesFilterWithLoader, TagsFilterWithLoader, EventsListWithLoader, SeriesListWithLoader, MarketsListWithLoader, MarketsCountBadge) | `.catch(() => [])`. | Demo = [] o datos demo; Real = API. |
| **StrategyMetricsWithLoader, IntentsTableWithLoader** | `.catch(() => ({ metrics: {}, … }))` etc. | Demo = vacío/mock; Real = API. |

### Backend (referencia)

- **execution_mode** ya existe: `DRY_RUN` (simulación), `PAPER`, `LIVE` (`backend/app/core/config_service.py`, `live_status.py`, `system.py`).
- **Simulación de estrategia**: `POST /api/strategies/{id}/simulate` existe.
- No hay concepto "demo" en backend; demo es solo frontend (mock/placeholders).

---

## Definición de modos

| Modo | Fuente de datos | Cuándo usar |
|------|------------------|-------------|
| **Demo** | Solo datos mock/placeholders en frontend. No llamar APIs de datos (o ignorar resultado y mostrar mock). | Sin backend, presentaciones, onboarding. |
| **Simulación** | Backend con `execution_mode=DRY_RUN` y/o resultados de `simulate`; datos de runs simulados. | Probar estrategias sin riesgo. |
| **Real** | Backend con `execution_mode=PAPER` o `LIVE`; solo APIs reales; sin fallbacks a mock. | Operación normal. |

---

## Fases de implementación

### Fase 0: Contexto y toggle (base)

**Objetivo:** Tener un estado global "modo de datos" y el botón junto al theme.

1. **Contexto React para DataMode**
   - Crear `frontend/contexts/DataModeContext.tsx` (o en `app/providers.tsx`):
     - Valores: `'demo' | 'simulation' | 'real'`.
     - Por defecto: `'real'` si hay backend conectado, si no `'demo'` (o leer de `localStorage` para persistir).
   - Provider en layout raíz (donde está ThemeProvider).

2. **Componente DataModeToggle**
   - Crear `frontend/components/DataModeToggle.tsx`:
     - Dropdown o botones: Demo / Simulación / Real.
     - Iconos distintos (ej. Beaker/Database/Activity).
     - Lee/escribe el contexto (y opcionalmente `localStorage`).
   - Añadir en `Layout.tsx` al lado de `ThemeToggle` en el header (misma fila, a la izquierda del ThemeToggle).

3. **Hook useDataMode**
   - `frontend/hooks/useDataMode.ts`: devuelve `{ dataMode, setDataMode, isDemo, isSimulation, isReal }`.

**Criterio de éxito:** El usuario puede cambiar el modo en el header y el valor persiste en la sesión (y opcionalmente en `localStorage`).

---

### Fase 1: Páginas de Settings y Risk (Demo vs Real)

**Objetivo:** En estas pantallas no hay "simulación"; solo Demo (placeholders) o Real (API).

1. **Wallets** (`app/settings/wallets/page.tsx`)
   - Si `dataMode === 'demo'`: no llamar API (o llamar y ignorar); mostrar `PLACEHOLDER_WALLETS`; badge "Modo Demo".
   - Si `dataMode === 'real'`: llamar API; si falla, mostrar error (no placeholders). Ocultar badge "Modo Demo" cuando modo Real.

2. **Checkers** (`app/settings/checkers/page.tsx`)
   - Misma lógica: Demo = placeholders + badge; Real = solo API + mensaje de error si falla.

3. **Risk** (`app/risk/page.tsx`)
   - Demo = `PLACEHOLDER_CONFIG` + badge; Real = API, sin fallback a placeholder.

4. **Settings Config** (`app/settings/config/page.tsx`)
   - Badge y mensaje según `dataMode`; en Real y backend no conectado, mensaje "Conecta el backend" en lugar de confundir con "Demo".

**Criterio de éxito:** Con modo Demo se ven datos de ejemplo; con modo Real solo datos del backend (o error claro).

---

### Fase 2: Markets, Decision Traces, Desk (Demo vs Real)

**Objetivo:** Separar listados y KPIs demo de reales.

1. **Markets** (`app/markets/page.tsx`)
   - Demo: no llamar `/markets` y `/markets/orderbook-metrics` (o devolver listas vacías/mock desde un helper).
   - Real: llamar API; sin `.catch(() => [])` que oculte error, o mostrar error en UI.
   - Badge "Demo Mode" solo cuando `dataMode === 'demo'`.

2. **Decision Traces** (`app/decision-traces/page.tsx`)
   - Demo: opcionalmente mock vacío o mensaje "No hay datos en modo demo"; badge "Modo Demo".
   - Real: solo API; error visible si falla.

3. **Desk** (`app/strategies/[id]/desk/page.tsx`)
   - Demo: eventos mock (como ahora en catch); KPIs del header "42k / 50k", "+3.2%" pueden quedar como texto demo o venir de constantes.
   - Real: eventos y estrategia de API; KPIs de API cuando existan endpoints (si no, dejar vacío o "—" en lugar de números inventados).

**Criterio de éxito:** En Demo se ve contenido controlado (mock/vacío); en Real solo datos de API o error explícito.

---

### Fase 3: Live y Live-compact (Demo / Simulación / Real)

**Objetivo:** Live es donde confluyen Simulación (DRY_RUN) y Real (PAPER/LIVE).

1. **Live** (`app/strategies/[id]/live/page.tsx`)
   - **Demo:** No llamar (o ignorar) live-status, positions, executions, etc.; mostrar datos mock o vacíos; banner "Modo Demo".
   - **Simulación:** Llamar API; mostrar `execution_mode` (DRY_RUN); datos de live-status/executions que vengan de runs simulados; banner "Modo Simulación".
   - **Real:** Llamar API; mostrar execution_mode PAPER/LIVE; sin fallbacks a mock; si API falla, mostrar error.
   - Eliminar o ajustar `.catch(() => null/[])` para que en Real el error sea visible.
   - Risk/KPIs: en Demo valores mock; en Simulación/Real de API (max_exposure etc. de estrategia está bien; evitar 5000 hardcodeado cuando haya dato real).

2. **Live-compact** (`app/strategies/[id]/live-compact/page.tsx`)
   - Demo: mock como ahora.
   - Real: cargar datos de API (estrategia, eventos, posiciones si existen).

**Criterio de éxito:** En Live, al cambiar modo se ve claramente Demo (mock), Simulación (DRY_RUN + datos sim) o Real (PAPER/LIVE + datos reales).

---

### Fase 4: Values, Signals, Operations, Capital (loaders y mock)

**Objetivo:** Que todos los loaders respeten el modo de datos.

1. **Values / Signals**
   - `SignalAlertsWithLoader.tsx`: Demo = mock actual; Real/Sim = llamar `/values/alerts` y `/values/live` cuando existan (si no, mensaje "No disponible").
   - `LiveValuesStreamWithLoader.tsx`: Demo = mock; Real/Sim = API.
   - `GlobalSignalHeaderWithLoader.tsx`: Demo = mock; Real/Sim = API.
   - `ValuesSnapshotCard.tsx`: Demo = mock; Real = API.

2. **Operations**
   - `InfrastructureHealthCards.tsx`, `OperationalAlertsList.tsx`: Demo = mock o vacío; Real = API; en Real no silenciar errores con `.catch(() => null)` sin mostrar nada.

3. **Capital**
   - `CapitalAllocationTable.tsx`, `PnLBreakdownTable.tsx`, `OpenPositionsTable.tsx`, `LiquidityCard.tsx`: Demo = [] o mock; Real = API; en Real mostrar error si falla.

4. **Strategy tables**
   - `StrategyStateDistribution.tsx`, `StrategyStatusTable.tsx`: Demo = no llamar o mock; Real = API.

**Criterio de éxito:** Ningún componente mezcla mock y real sin mirar `dataMode`; en Real los fallos de API son visibles.

---

### Fase 5: Markets loaders y resto de .catch

**Objetivo:** Que todos los loaders de markets, series, tags y eventos respeten el modo.

1. **Loaders**
   - `CategoriesFilterWithLoader.tsx`, `TagsFilterWithLoader.tsx`, `EventsListWithLoader.tsx`, `SeriesListWithLoader.tsx`, `MarketsListWithLoader.tsx`, `MarketsCountBadge.tsx`:
   - Demo: no llamar API o devolver []/mock.
   - Real: llamar API; no usar `.catch(() => [])` sin mostrar error en UI.

2. **Strategy loaders**
   - `StrategyMetricsWithLoader.tsx`, `IntentsTableWithLoader.tsx`: Demo = vacío/mock; Real = API; errores visibles en Real.

3. **Revisión global**
   - Buscar en frontend todos los `.catch(() => []|null|{})` en llamadas de datos y decidir por componente: en Real, o bien no hacer catch y dejar que el loader muestre error, o mostrar un mensaje "Error al cargar" en lugar de lista vacía silenciosa.

**Criterio de éxito:** Listados y métricas en Real no muestran vacío silencioso cuando la API ha fallado; en Demo el comportamiento es intencionado (mock/vacío).

---

### Fase 6: Backend opcional (Simulación explícita)

**Objetivo:** Ajustes backend para que "Simulación" tenga sentido como modo de datos en UI.

1. **Endpoints de datos de simulación** (si no existen)
   - Ej.: lecturas de runs de `simulate` o de decision_traces con decision_type SIMULATED.
   - El frontend en modo Simulación podría filtrar o pedir solo datos simulados.

2. **execution_mode y DataMode**
   - Opción A: El modo "Real" en frontend solo muestra datos cuando backend está en PAPER/LIVE; "Simulación" cuando está en DRY_RUN.
   - Opción B: El selector de modo en UI solo controla si el frontend usa mock (Demo) o API (Simulación/Real), y dentro de API el backend ya define DRY_RUN vs PAPER/LIVE por su propia config.
   - Recomendación: Fase 1–5 con opción B; en Fase 6, si se quiere, sincronizar badge "Simulación" con `execution_mode === 'DRY_RUN'` leyendo `/system/config/execution-mode`.

**Criterio de éxito:** Claridad entre "datos que muestra el frontend" (Demo vs API) y "modo de ejecución del backend" (DRY_RUN / PAPER / LIVE); documentado en este plan.

---

## Orden recomendado y dependencias

- **Fase 0** es obligatoria primero (contexto + toggle).
- **Fases 1, 2, 3** pueden hacerse en paralelo por persona/rama una vez exista el contexto; cada una toca un conjunto de páginas distinto.
- **Fase 4** y **Fase 5** son limpieza sistemática de loaders y `.catch`; conviene después de 1–3.
- **Fase 6** es opcional y puede hacerse al final.

---

## Checklist por fase (resumen)

- [ ] **Fase 0:** DataModeContext, DataModeToggle en header, useDataMode.
- [ ] **Fase 1:** Wallets, Checkers, Risk, Settings Config usan dataMode (Demo vs Real).
- [ ] **Fase 2:** Markets, Decision Traces, Desk usan dataMode.
- [ ] **Fase 3:** Live y Live-compact usan dataMode (Demo / Simulación / Real).
- [ ] **Fase 4:** Values, Signals, Operations, Capital loaders usan dataMode.
- [ ] **Fase 5:** Markets loaders, Strategy loaders y revisión de .catch en Real.
- [ ] **Fase 6:** (Opcional) Backend/execution_mode y modo Simulación en UI.

---

## Archivos a crear/modificar (referencia rápida)

| Acción | Ruta |
|--------|------|
| Crear | `frontend/contexts/DataModeContext.tsx` (o en providers) |
| Crear | `frontend/hooks/useDataMode.ts` |
| Crear | `frontend/components/DataModeToggle.tsx` |
| Modificar | `frontend/components/Layout.tsx` (añadir DataModeToggle) |
| Modificar | `frontend/app/providers.tsx` (DataModeProvider si no va en Layout) |
| Modificar | Todas las páginas y loaders listados en "Estado actual" según la fase correspondiente |

Este documento es el plan maestro; cada fase puede tener su propio ticket o PR con checklist detallado de archivos y tests.
