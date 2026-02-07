# Plan: Demo, Simulación y Live funcionando en todos los casos

Objetivo: definir qué debe verse y poder hacerse en cada modo (Demo, Simulación, Live) y hacer que la activación y la página Live funcionen correctamente en los tres.

---

## 0. Resumen ejecutivo y revisión

- **Definición por modo:** Demo offline, Simulación = DRY_RUN con backend real, Live real. Product-correct y alineado con `docs/system-overview.md` y `docs/data-flow.md`.
- **Fases:** A (Demo UX) → B (Simulación) → C (errores Live) → D (docs). Orden sensato; el control loop (activate → planes → precheck → ejecución) queda como en `docs/execution-engine.md` y `docs/order-lifecycle.md`.
- **Riesgo conceptual:** En Demo, `is_active` es solo “control state” para cambiar vistas; no debe interpretarse como “está tradeando”. Banner/copy debe dejar claro que es simulado.
- **Pause vs Stop en Demo:** Deben distinguirse: Pause = `is_active=false` sin tocar `disabled_at`; Stop = `is_active=false` + `disabled_at=now` (y si la UI lo usa, reseteo de contadores mock). Así la semántica de la UI no miente.
- **Simulación (B3):** No es opcional. La UI debe poder **verificar** el `execution_mode` efectivo del backend (DRY_RUN) antes/durante la activación; el backend debe exponerlo en status y/o el modo debe ser input determinista (ver `docs/config-driven.md`). Evita “accidental live trading”.
- **Errores (C1):** Banner con `ApiResponseError` ya implementado para Live/Simulación; si en el futuro Demo llama al backend opcionalmente (híbrido), reutilizar el mismo mecanismo, no `alert()`.

**Veredicto:** Plan coherente con la arquitectura. Dos cambios clave para hacerlo bulletproof: (1) Demo: Stop ≠ Pause usando `disabled_at`; (2) Simulación: B3 como requisito — verificación del mode efectivo del backend.

---

## 1. Definición por modo

### 1.1 Modo Demo

**Objetivo:** Explorar la UI sin backend. El usuario puede “jugar” con Activar/Pausar y ver el mismo layout que en real, con datos de ejemplo o vacíos.

| Área | Qué queremos ver / hacer |
|------|---------------------------|
| **Activar** | Sí se puede hacer. No llama al API. Al hacer click, la UI pasa a mostrar la estrategia como “activa” (estado local: `strategy.is_active = true`). Se muestran los mismos bloques que cuando está activa (métricas, eventos, health) pero con datos **mock o vacíos**. |
| **Pausar / Detener** | Sí. Revierte el estado local a “pausada” (sin llamar API). |
| **Datos en pantalla** | Banner claro “Modo Demo”. Métricas, eventos, checkers, live-status, intents: **mock o listas vacías**. No llamadas al backend. |
| **Botones** | Activar, Pausar, Detener, Configurar, Desk, Métricas, Logs: todos **habilitados** donde tenga sentido (Activar solo si está pausada, Pausar solo si está activa). Ninguno llama al API en Demo. |
| **Estrategia “activa” en Demo** | Tras “Activar” en Demo: header muestra Pausar/Detener, contador de eventos puede ser 0 o mock, KPIs con valores de ejemplo o “—”. **No interpretar como “operando real”**: es estado local para layout; banner/copy “simulado”. |
| **Pausar vs Detener en Demo** | **Pausar:** `is_active=false`, no tocar `disabled_at`. **Detener:** `is_active=false`, `disabled_at=now`; si la UI distingue “Stopped at” o resetea KPIs, debe reflejarse. No opcional si la UI tiene semántica distinta. |

**Modelo Demo (fuente de datos):** Para que Demo sea vendible y no “todo vacío”, conviene fijar una fuente clara: un **StrategyDemoBundle** (1–3 estrategias, 3–5 eventos, sample metrics, sample logs, sample intents). Puede vivir en el frontend como fixture sin backend. Decisión de spec, no obligatorio implementar ya.

### 1.2 Modo Simulación

**Objetivo:** Backend real, estrategia realmente activa, órdenes en DRY_RUN (no se envían órdenes reales).

| Área | Qué queremos ver / hacer |
|------|---------------------------|
| **Activar** | Sí. **Llama al API** `POST /api/strategies/{id}/activate`. El backend marca la estrategia activa y suscribe orderbooks. El modo de ejecución del backend debe ser DRY_RUN (sincronizado al elegir “Simulación” en el selector). |
| **Pausar / Detener** | Sí. Llaman al API. Desactivan la estrategia en backend. |
| **Datos en pantalla** | Banner “Modo Simulación — Datos del backend; órdenes simuladas (DRY_RUN)”. **Datos reales**: live-status, eventos asignados, checkers, métricas, intents, posiciones, todo desde el backend. |
| **Botones** | Activar/Pausar/Detener llaman al API. Configurar, Desk, Métricas, Logs funcionan igual que en Live. |
| **Garantía DRY_RUN** | **Requisito:** La UI debe poder verificar que el backend está realmente en DRY_RUN (p. ej. leyendo `execution_mode` del status). Activate puede imponer mode o el backend lo toma de sesión/tenant de forma determinista. Sin esto hay riesgo de “accidental live trading”. |

### 1.3 Modo Live

**Objetivo:** Todo real: backend real, estrategia activa, órdenes reales (LIVE).

| Área | Qué queremos ver / hacer |
|------|---------------------------|
| **Activar** | Sí. Llama al API. Backend en modo LIVE; al ejecutar planes se envían órdenes reales. |
| **Pausar / Detener** | Sí. Llaman al API. |
| **Datos en pantalla** | Sin banner de Demo/Simulación. Opcional: indicador discreto “LIVE” o “Órdenes reales”. Datos 100% reales del backend. |
| **Botones** | Todos operativos y con llamadas reales al API. |

---

## 2. Estado actual y gaps

### 2.1 Demo

- **Activar:** Hoy el handler hace `if (isDemo) return` y **no** actualiza estado local, así que el botón no tiene efecto visual. **Gap:** permitir “activación simulada” en estado local y mostrar la vista “activa” con datos mock.
- **Pausar/Detener:** También hacen `if (isDemo) return`. **Gap:** en Demo, que reviertan el estado local a “pausada” sin llamar API.
- **Datos:** En Demo ya se cortan muchas llamadas y se muestran listas vacías o mock. **Gap:** cuando el usuario “activa” en Demo, que los bloques (métricas, eventos, health, intents) sigan mostrando mock/vacío de forma coherente (ya en parte está; revisar que no dependan de `strategy.is_active` del backend).
- **live-compact:** Play/Pause/Stop deshabilitados en Demo. **Gap:** igual que en live: en Demo permitir Play (activación local) y Pausar/Stop (reversión local).

### 2.2 Simulación

- **Activar:** Si quitamos el bloqueo por Demo, en Simulación ya se llamaría al API. **Gap:** asegurar que el backend esté en DRY_RUN cuando el usuario tiene elegido Simulación (ya hay sync en DataModeToggle; verificar que no se cambie a LIVE por otro flujo).
- **Datos:** En Simulación no se cortan las llamadas al API; se muestran datos reales. **Gap:** solo revisar que en ninguna ruta se trate Simulación como Demo (no cortar llamadas cuando `isSimulation`).

### 2.3 Live

- **Activar / Pausar / Detener:** Ya llaman al API. Comportamiento correcto.
- **Gap:** Mejorar mensajes de error (403, 400, 404) en el frontend en lugar de solo `alert()`.

---

## 3. Tareas de implementación (orden sugerido)

### Fase A: Demo – Activación y controles “simulados” en Live

| Id | Tarea | Detalle |
|----|--------|---------|
| A1 | Activar en Demo actualiza solo estado local | En `live/page.tsx`, en `handleActivate`: si `isDemo`, no llamar API; hacer `setStrategy(prev => prev ? { ...prev, is_active: true, enabled_at: new Date().toISOString() } : null)`. Así el header mostrará Pausar/Detener y el resto de la página verá estrategia “activa”. |
| A2 | Pausar en Demo revierte estado local | En `handlePause`: si `isDemo`, `setStrategy(prev => prev ? { ...prev, is_active: false, enabled_at: null } : null)` (no tocar `disabled_at`) y return sin API. |
| A3 | Detener en Demo revierte estado local | En `handleStop`: si `isDemo`, `setStrategy(prev => prev ? { ...prev, is_active: false, enabled_at: null, disabled_at: new Date().toISOString() } : null)` y return sin API. Así la UI puede distinguir “pausada” vs “detenida” (ej. “Stopped at”, reseteo KPIs). No opcional si la UI tiene semántica distinta. |
| A4 | Demo: datos coherentes con “activa” | Revisar que en Demo, cuando `strategy?.is_active === true` (estado local), los bloques que dependen de “está activa” (métricas, eventos recientes, health) sigan mostrando mock o vacío sin depender del backend. Ajustar condiciones si hace falta. |
| A5 | live-compact: Play/Pausar/Stop en Demo | En `live-compact/page.tsx`: si `isDemo`, Play pone `setIsActive(true)` sin API; Pausar/Stop ponen `setIsActive(false)` sin API. Quitar `disabled={isDemo}` de esos botones o hacer que en Demo estén habilitados y operen sobre estado local. |

### Fase B: Simulación – Comprobar que todo usa API y DRY_RUN

| Id | Tarea | Detalle |
|----|--------|---------|
| B1 | Activar/Pausar/Stop en Simulación llaman API | Asegurar que en `live/page.tsx` y `live-compact` no se bloquee por `isSimulation` (solo por `isDemo`). En Simulación debe ejecutarse la misma ruta que en Live (llamada API). |
| B2 | Banner y copy en Simulación | Ya existe banner “Modo Simulación” en Live. Revisar que en live-compact también se muestre un indicador cuando `isSimulation`. |
| B3 | Verificar execution_mode efectivo del backend (requisito) | La UI debe poder comprobar que el backend está en DRY_RUN: (1) Backend expone `execution_mode` en status y la UI lo muestra (“Execution mode: DRY_RUN”), o (2) Activate incluye/impone mode, o el backend lo toma de sesión/tenant de forma determinista. No basta el banner; hay que garantizar DRY_RUN end-to-end para evitar accidental live trading. |

### Fase C: Live – Sin cambios de lógica; mejor UX de errores

| Id | Tarea | Detalle |
|----|--------|---------|
| C1 | Errores de activación visibles | En `handleActivate` (y Pausar/Stop), en el `catch`: mostrar un Alert bajo el header con el mensaje del backend (403, 400, 404) — ya implementado con `ApiResponseError` y banner. Si en el futuro Demo llama al backend opcionalmente (híbrido), reutilizar este mismo mecanismo, no `alert()`. |

### Fase D: Documentación y criterios de “listo”

| Id | Tarea | Detalle |
|----|--------|---------|
| D1 | Actualizar strategy-activate-flow.md | Añadir sección “Comportamiento por modo (Demo / Simulación / Live)” resumiendo esta tabla: quién llama API, quién solo estado local, qué banner se muestra. Ubicar el doc cerca de: `docs/execution-engine.md` (control loop, plans, precheck), `docs/order-lifecycle.md` (ejecución de órdenes), `docs/config-driven.md` (modo DRY_RUN/LIVE como input), `docs/quorum.md` (por qué puede estar activa pero no operar). |
| D2 | Checklist de aceptación | Ver sección 6 abajo. Demo: Activar → header Pausar/Detener y bloques activos (mock/vacíos); Pausar/Detener sin requests; Detener marca disabled_at si aplica. Simulación: Activar/Pausar/Detener llaman API, banner Simulación, UI muestra “Execution mode: DRY_RUN” (leído del backend), datos reales. Live: igual que Simulación sin banner; indicador LIVE; errores 400/403/404 en banner (no alert). |

---

## 4. Resumen por modo (tabla de referencia)

| Acción / Visibilidad | Demo | Simulación | Live |
|----------------------|------|------------|------|
| Click **Activar** | Actualiza solo estado local; UI muestra “activa” con datos mock/vacíos | Llama API; backend activa en DRY_RUN | Llama API; backend activa en LIVE |
| Click **Pausar / Detener** | Revierte estado local; no API | Llama API | Llama API |
| Datos (métricas, eventos, health, intents) | Mock o vacíos; sin llamadas backend | Reales (backend) | Reales (backend) |
| Banner | “Modo Demo” | “Modo Simulación — órdenes simuladas (DRY_RUN)” | Ninguno (o “LIVE” discreto) |
| Botones Configurar, Desk, Métricas, Logs | Habilitados; navegación normal (Desk/Config pueden seguir en Demo con datos mock) | Habilitados | Habilitados |

---

## 5. Orden de trabajo sugerido

1. **Fase A (Demo)** – A1 → A2 → A3 → A4 → A5.  
2. **Fase B (Simulación)** – B1, B2 (y B3 por verificación).  
3. **Fase C (Live)** – C1.  
4. **Fase D** – D1, D2.

Cuando A esté hecha, Demo “funciona” en todos los casos (activar/pausar y ver la vista correcta). B y C completan Simulación y Live. D deja el comportamiento documentado y comprobable.

---

## 6. Riesgos y checklist de aceptación

### Riesgos

- **Confusión semántica de is_active:** En el sistema real “active” no implica “trading”. En Demo, usar `is_active` para layout está bien; evitar copy que lo interprete como “operando real”. Solución: banner y etiquetas “simulado”.
- **Inconsistencias live/page vs live-compact:** Si se duplica lógica (A5 vs A1–A3), mantenerla en sync; idealmente extraer acciones de control a un helper común cuando sea posible.
- **Simulación mal configurada:** Si no se garantiza DRY_RUN end-to-end (B3), riesgo de accidental live trading. Debe haber guardrails: UI muestra mode efectivo y/o backend recibe mode de forma determinista.

### Checklist de aceptación (D2)

**Demo**

- [ ] Activar cambia header a Pausar/Detener y aparecen bloques “activos” (aunque vacíos/mock).
- [ ] Pausar vuelve a estado pausado sin recargar ni llamadas.
- [ ] Detener vuelve a pausado y (si aplica) marca `disabled_at` y resetea lo que corresponda en UI.
- [ ] Ninguna acción genera requests (salvo que se decida híbrido).

**Simulación (DRY_RUN)**

- [ ] Activar/Pausar/Detener llaman API y el banner Simulación aparece.
- [ ] La UI muestra “Execution mode: DRY_RUN” (idealmente leído del backend).
- [ ] Se ven datos reales del backend: eventos, health/checkers, intents.

**Live**

- [ ] Igual que Simulación pero sin banner de Demo/Simulación y con indicador LIVE.
- [ ] Errores 400/403/404 aparecen en banner (no en `alert()`).
