# SPEC: Near Resolution en Live — Control total y hardening para dinero real

**Versión:** 1.1  
**Estado:** Especificación cerrada + plan técnico accionable  
**Objetivo:** Fuente de verdad para Near Resolution en Live; checklist de PR; diseño que haga **imposible por diseño** enviar órdenes reales al CLOB cuando el sistema no esté en modo LIVE o cuando esté pausado.

---

## 0. Resumen ejecutivo

- **Objetivo prioritario:** Operar con dinero real sin sorpresas. Esta SPEC define las reglas para que **no** sea posible enviar escrituras reales al CLOB (create, cancel, amend) salvo cuando `execution_mode == LIVE` y `system_active == true`.
- **Estado actual del sistema (resumen):** Activar en Live persiste la estrategia como activa y suscribe orderbooks; la UI se actualiza. En el diseño actual, el Control Loop carga estrategias activas solo al arranque, por lo que estrategias activadas después no son consideradas hasta reinicio. El camino Execution Graph → PolymarketAdapter invoca al cliente CLOB sin comprobar `execution_mode` ni `system_active` en ese camino, lo que constituye un gap respecto a esta SPEC.
- **Qué exige esta SPEC:** Invariantes de seguridad obligatorios (I1–I6), un único punto de envío (Execution Gateway) que las aplique siempre, recarga de estrategias activas con DoD acotado, y un contrato mínimo de observabilidad. Ningún PR que toque envío de órdenes es aceptable si vulnera las invariantes.
- **Orden de hardening:** Primero cerrar el punto único de envío y las invariantes (Gap 4.4, 4.2, 4.3); después recarga de activas (4.1); luego observabilidad y mejoras no críticas.

---

## 1. Scope de execution_mode (alcance de esta SPEC)

Esta SPEC **solo cubre dos modos de ejecución:**

- **DRY_RUN:** Simulación. Cero escrituras al CLOB. Solo lógica local y respuestas simuladas.
- **LIVE:** Trading real. Escrituras al CLOB permitidas **únicamente** cuando además se cumplan I2, I4, I5, I6.

**Terminología — "escrituras al CLOB":** Cualquier operación de mutación enviada al CLOB de Polymarket, incluyendo (lista no exhaustiva): `create` / `submit` (order), `cancel` (order), `amend` / `update` / `replace` (order). Si en duda, cualquier llamada al CLOB que no sea lectura pura (GET) se trata como escritura.

**Fuera de scope de esta SPEC:**

- **PAPER** y cualquier otro modo distinto de DRY_RUN y LIVE no forman parte del alcance funcional de este documento. La simulación de fills, PnL o performance (paper trading) se tratará en un documento separado en el futuro.

**Regla de seguridad para modos no LIVE:**

- **Cualquier valor de `execution_mode` distinto de LIVE** (incluido PAPER, o cualquier modo futuro no contemplado aquí) **se trata, a efectos de las invariantes de esta SPEC, exactamente como DRY_RUN:** cero escrituras al CLOB. Es decir, `execution_mode != LIVE` ⇒ ninguna llamada de creación, modificación o cancelación de órdenes al CLOB. Solo respuestas simuladas locales y trazabilidad (I5).

De este modo no queda ningún hueco de interpretación: o el sistema está en LIVE y cumple el resto de invariantes, o no se escribe en el CLOB. La definición formal de «orden real» y las invariantes se detallan en §1.1 y §1.2.

---

## 1.1 Definición formal de “orden real”

Para esta SPEC se considera **orden real** toda operación que:

1. **Envía datos al CLOB de Polymarket** mediante una llamada de red (HTTP/WebSocket) que pueda resultar en la creación, modificación o cancelación de una orden o posición en nombre del bot (credenciales de producción).
2. **Tiene efecto económico inmediato o diferido** en la cuenta asociada al bot (ej. POST order, cancel order, o cualquier operación que Polymarket persista como orden activa o fill).

**No** se consideran órdenes reales:

- Respuestas simuladas generadas localmente (sin llamada al CLOB) cuando `execution_mode != LIVE` (p. ej. DRY_RUN o cualquier modo tratado como no-LIVE según §1).
- Logs, métricas o eventos emitidos sin llamada de red al CLOB.
- Lecturas (GET) del orderbook o de estado de órdenes, salvo que la spec de Polymarket las trate como mutaciones; en caso de duda, cualquier escritura (POST/PUT/DELETE) al CLOB se trata como orden real.

Esta definición es la referencia para aplicar I1 e I2: “no enviar orden real” = no realizar ninguna operación que cumpla los puntos 1 y 2 anteriores. Para I1, “no enviar orden real” aplica siempre que `execution_mode != LIVE`.

---

## 1.2 Invariantes de seguridad

Las siguientes reglas son **NO negociables**. Cualquier ruta que pueda resultar en una **escritura** al CLOB (create, cancel, amend) **debe** cumplirlas. Guían toda la arquitectura y son criterio de PR.

| Id | Invariante | Descripción |
|----|------------|-------------|
| **I1** | **Solo LIVE puede escribir en el CLOB** | `execution_mode != LIVE` ⇒ **cero** llamadas al CLOB que muten estado (POST order, cancel, amend). Solo se permite simular (log + respuesta simulado, sin red). Cualquier otro modo (p. ej. PAPER) se trata como no-LIVE: misma regla. |
| **I2** | **Kill-switch: ninguna mutación real con sistema pausado** | Si `system_active == false`, **no** se permite **ninguna** mutación real al CLOB: ni creación ni cancelación ni amend. El kill-switch tiene **prioridad absoluta** sobre cualquier otro estado. Comportamiento aceptable: devolver resultado SIMULATE o SKIP_PAUSED, registrar con I5, no invocar al CLOB. **Tensión con I4:** Cualquier política de "cancelar órdenes abiertas por latency/circuit" (mencionada en I4) solo puede aplicar cuando `system_active == true`. Si el sistema está pausado, I2 prevalece: **cero** mutaciones (incluidas cancelaciones). |
| **I3** | **Un solo punto de envío** | Toda solicitud que pueda resultar en una escritura al CLOB debe pasar por **un único** componente (Execution Gateway) que aplique I1, I2, I4 antes de llamar al cliente. No se admiten atajos que eviten ese punto. |
| **I4** | **Circuit breaker y latencia** | Antes de enviar una orden real, debe comprobarse: (a) trading circuit no abierto, (b) latencia no en estado RED. Si no se cumple, no enviar (y opcionalmente cancelar abiertas según política). |
| **I5** | **Trazabilidad obligatoria** | Toda decisión de “enviar” o “simular” debe quedar registrada con al menos: `trace_id`, `plan_id` (si aplica), `strategy_id`, `execution_mode`, `system_active` en el momento de la decisión. |
| **I6** | **Idempotencia de envío (solo cuando decision = SEND)** | Cuando el Gateway decide **SEND** (es decir, va a invocar al CLOB), debe garantizar **una sola** llamada efectiva al CLOB por identidad de solicitud. **Identidad de solicitud:** (a) `submit_order`: derivada de `idempotency_key`, que debe ser **determinista y estable** (mismo input → misma key); recomendación de composición: hash o concatenación de trace_id, plan_id, leg_id, side, token_id (sin incluir timestamp o random); (b) `cancel_order`: identidad por `platform_order_id` (el ID de la orden a cancelar). **Comportamiento ante solicitudes duplicadas:** retornar el resultado previo de esa identidad (o consultar estado en el CLOB y retornar coherentemente), sin realizar una segunda escritura. Cuando la decisión es **SIMULATE** o **SKIP_*** (no SEND), I6 no exige idempotencia de llamada al CLOB porque no hay llamada; basta trazabilidad determinista (I5). |

**Criterio de PR:** Cualquier cambio que añada o modifique un camino que pueda escribir en el CLOB debe incluir en la descripción la comprobación explícita de I1–I6 y, si aplica, el test de aceptación que lo garantiza.

---

## 2. Estado actual: qué hace y qué no hace

### 2.1 Flujo actual al hacer “Activar” (Live)

- **Frontend:** Llama a `POST /api/strategies/{id}/activate`; errores 4xx se muestran en banner.
- **Backend (activate):** Comprueba existencia y admin; obtiene `asset_ids` de eventos asignados; suscribe orderbooks; marca `is_active=true` y persiste. No arranca procesos nuevos; no garantiza que el Control Loop vea la estrategia de inmediato.

### 2.2 Qué funciona hoy

- API Activar/Desactivar, suscripción orderbooks, persistencia.
- Frontend Live: Activar/Pausar/Detener y banner de errores.
- `execution_mode` en config; Precheck; Decision Graph → Plan; Execution Graph con coordinator; clase Execution (legacy) respeta modo y kill-switch; `/control/pause` y `/control/resume`.

### 2.3 Qué no hace hoy

- El Control Loop no recarga la lista de estrategias activas tras el arranque.
- El camino Execution Graph → PolymarketAdapter no comprueba `execution_mode` ni `system_active`.
- Hay dos caminos distintos que pueden acabar en envío al CLOB; solo uno de ellos aplica las comprobaciones.

---

## 3. Gaps críticos (reforzados)

Para cada gap se define: **problema**, **riesgo**, **solución aceptable**, **Definition of Done**.

### 3.1 Gap 4.1 — Control Loop no recarga estrategias activas

| Campo | Contenido |
|-------|-----------|
| **Problema** | `load_active_strategies(db)` se ejecuta solo en el arranque del Control Loop. La lista `active_strategies` es en memoria y no se vuelve a leer de la DB. |
| **Riesgo** | Estrategias activadas por API después del arranque **nunca** son consideradas por el loop hasta reinicio del proceso. La funcionalidad “Activar desde la UI” queda rota para uso normal. |
| **Solución aceptable** | (A) Recargar estrategias activas desde DB de forma **periódica** (intervalo configurable, ej. cada N segundos o cada M ticks), **o** (B) Actualizar `active_strategies` ante un **evento** “estrategia activada/desactivada” (API publica, loop consume). La solución debe garantizar que en un tiempo acotado (p. ej. &lt; 30 s) toda estrategia recién activada sea considerada. |
| **Definition of Done** | (1) Test: tras activar una estrategia por API con el loop ya corriendo, en un tiempo ≤ T (ej. 30 s) el loop debe haber procesado al menos un tick para esa estrategia (verificable por log o métrica). (2) Test: tras desactivar por API, el loop debe dejar de procesarla en un tiempo acotado. (3) Doc o comentario en código que fije el criterio de “cuándo” se considera una estrategia activa en el loop. **(4) Casos de activación/desactivación rápida:** (4a) Activar y desactivar la misma estrategia en secuencia rápida (ej. &lt; 2 s): el loop no debe procesar ticks para esa estrategia una vez desactivada (no debe quedar “fantasma” activa). (4b) Activar estrategia A, desactivar A, activar A de nuevo dentro del intervalo de refresh: el estado final debe ser “activa” y el loop debe procesarla. (4c) Activar varias estrategias en ráfaga (ej. 3 en &lt; 5 s): todas deben ser consideradas tras el siguiente refresh (o evento) dentro de T. (4d) Desactivar una estrategia mientras tiene planes en cola: el loop debe dejar de generar nuevos trabajos para esa estrategia en un tiempo acotado; el tratamiento de planes ya encolados puede ser “ejecutar hasta fin” o “cancelar según política”, pero debe estar documentado. |

---

### 3.2 Gap 4.2 — Execution Graph (PolymarketAdapter) no respeta execution_mode

| Campo | Contenido |
|-------|-----------|
| **Problema** | El camino ExecutionCoordinatorNode → `trading_platform.submit_order` → PolymarketAdapter llama directamente al cliente de Polymarket sin consultar `execution_mode`. |
| **Riesgo** | **Accidental live trading:** En DRY_RUN el sistema puede enviar órdenes reales por este camino. Pérdida de dinero y violación de invariante I1. |
| **Solución aceptable** | Todo envío que hoy pasa por PolymarketAdapter (o el cliente CLOB) debe pasar antes por una **capa única** (Execution Gateway) que lea `execution_mode`. Si `execution_mode != LIVE`: no llamar al CLOB; devolver resultado simulado (order_id simulado, status SIMULATED) y registrar con I5. Solo si `execution_mode == LIVE` (y se cumple I2, I4) se delega en la llamada real. La comprobación debe estar en el **mismo** punto que I2 (kill-switch) para no tener lógica duplicada. |
| **Definition of Done** | (1) Test: con `execution_mode != LIVE` (p. ej. DRY_RUN) y un plan que llegue al Execution Graph, **cero** llamadas al CLOB (mock o spy del cliente). (2) Test: con `execution_mode=LIVE` y sistema activo, las órdenes sí llegan al CLOB (o mock en entorno controlado). (3) Revisión de código: no existe ningún otro camino que llame al CLOB sin pasar por esta comprobación. |

---

### 3.3 Gap 4.3 — Execution Graph no respeta system_active (kill-switch)

| Campo | Contenido |
|-------|-----------|
| **Problema** | El camino Execution Graph → PolymarketAdapter no comprueba `state.system_active`. |
| **Riesgo** | Con el sistema en pausa (`/control/pause`), el Execution Graph puede seguir enviando órdenes reales. Bypass del kill-switch; violación de I2. |
| **Solución aceptable** | En el **mismo** punto único donde se aplica I1 (execution_mode), comprobar `state.system_active`. Si `system_active == false`, no enviar orden real; registrar evento “order_skipped_system_paused” con I5 y devolver resultado controlado (ej. status PAUSED o SKIPPED). No llamar al CLOB. |
| **Definition of Done** | (1) Test: con `system_active=false` y un plan listo para ejecutar en LIVE, **cero** llamadas al CLOB. (2) Test: tras `/control/resume`, las órdenes sí pueden enviarse (con resto de condiciones OK). (3) Revisión: el mismo punto que aplica I1 aplica I2. |

---

### 3.4 Gap 4.4 — Dos caminos de envío; falta un único punto de control

| Campo | Contenido |
|-------|-----------|
| **Problema** | Existen dos caminos que pueden acabar en envío al CLOB: (A) Intents → Risk Engine → Execution.tick() → firma/envío; (B) Plans → Execution Graph → ExecutionCoordinatorNode → PolymarketAdapter → CLOB. Solo (A) aplica hoy execution_mode y system_active. (B) no. |
| **Riesgo** | Comportamiento inconsistente; riesgo de que futuros caminos añadan envío sin aplicar invariantes; imposible auditar “quién puede enviar” en un solo lugar. |
| **Solución aceptable** | Ver sección 4 (Decisión arquitectónica). Resumen: **Arquitectura objetivo = un único Execution Gateway** por el que pasen todos los envíos; PolymarketAdapter (o el cliente) solo se invoca desde ese gateway tras comprobar I1, I2, I4. |
| **Definition of Done** | (1) No existe ningún camino que llame al cliente CLOB (o a PolymarketAdapter en modo “enviar real”) sin pasar por el gateway. (2) Test de integración: deshabilitar envío en el gateway (ej. forzar execution_mode distinto de LIVE o system_active=false) y verificar que **ningún** camino envía al CLOB. (3) Documentación de arquitectura actualizada con el diagrama del único punto de envío. **(4) Método verificable para ausencia de caminos directos al CLOB:** Regla de CI, lint o grep (o equivalente) que **falle** si el cliente CLOB se invoca desde código que no sea el Execution Gateway. Ejemplo: lista blanca de módulos/archivos que pueden llamar al cliente; cualquier otra llamada al cliente CLOB hace fallar el check. El DoD no se considera cerrado sin esta regla (o equivalente auditable). |

---

## 4. Decisión arquitectónica: un único punto de envío

### 4.1 Arquitectura objetivo

- **Componente único:** “Execution Gateway” (nombre conceptual; puede ser una capa en el adaptador o un servicio dedicado). **Responsabilidad única:** Dado una solicitud de envío de orden (con trace_id, plan_id, strategy_id, y payload de la orden):
  1. Comprobar I1: `execution_mode != LIVE` ⇒ **cero** escrituras al CLOB; devolver resultado simulado (decision=SIMULATE o SKIP_DRY_RUN) y registrar con I5. No invocar al CLOB.
  2. Comprobar I2: `system_active == false` ⇒ **ninguna** mutación real al CLOB (ni create ni cancel ni amend); devolver resultado “pausado” (decision=SKIP_PAUSED) y registrar con I5. No invocar al CLOB.
  3. Comprobar I4: circuit breaker y latencia; si no pasan, no enviar (y según política cancelar abiertas).
  4. Registrar con I5 (trazabilidad), incluyendo source_path e idempotency_key cuando aplique.
  5. **Solo si** se va a tomar decision=SEND: aplicar I6 (idempotencia); luego invocar al cliente Polymarket. Para decision=SIMULATE o SKIP_*, no se invoca al CLOB; I6 no exige idempotencia de llamada (no hay llamada).

- **Quién llama al Gateway:**  
  - El camino **Intents** (Execution legacy): en lugar de llamar directamente al cliente, debe llamar al Gateway.  
  - El camino **Plans** (ExecutionCoordinatorNode → PolymarketAdapter): PolymarketAdapter no debe llamar al cliente; debe llamar al Gateway. Así, tanto intents como plans pasan por el mismo punto.

- **Resultado:** Una sola implementación de I1, I2, I4, I5, I6; ningún camino puede “saltarse” las comprobaciones.

### 4.2 Interface conceptual del Execution Gateway

**Inputs (solicitud de envío):**

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| **trace_id** | Sí | Identificador de trazabilidad de la decisión/orden. |
| **strategy_id** | Sí | Estrategia que origina la orden. |
| **plan_id** | Si aplica | Plan del que forma parte la orden (camino Plans). |
| **leg_id** o equivalente | Si aplica | Identificador del leg dentro del plan (para idempotencia I6). |
| **idempotency_key** | Recomendado (obligatorio para I6 cuando decision=SEND) | Clave única por solicitud; debe ser **determinista y estable** (mismo input → misma key). Recomendación de composición: hash o concatenación de `trace_id`, `plan_id`, `leg_id`, `side`, `token_id` (sin incluir timestamp o random). Usada para I6. |
| **payload** | Sí | Datos de la orden (token_id, side, size/amount, order_type, etc.) necesarios para invocar al CLOB. |
| **operation** | Sí | Tipo: `submit_order` \| `cancel_order` (u otros que se añadan); determina la llamada al CLOB. |

**Outputs (respuesta del Gateway):**

| Campo | Descripción |
|-------|-------------|
| **decision** | `SEND` \| `SIMULATE` \| `SKIP_PAUSED` \| `SKIP_LATENCY` \| `SKIP_CIRCUIT` \| `SKIP_DRY_RUN` (o equivalente). Debe coincidir con lo registrado en I5. |
| **reason_code** | Cuando decision != SEND; código que explica por qué no se envió (ej. `DRY_RUN`, `SYSTEM_PAUSED`, `CIRCUIT_OPEN`, `LATENCY_RED`). Omitido si decision=SEND. |
| **reason_detail** | Opcional; texto adicional para diagnóstico cuando decision != SEND (ej. "circuit opened after 3 consecutive fill failures"). |
| **platform_order_id** | ID devuelto por el CLOB, o ID simulado (ej. `dry_run_&lt;uuid&gt;`) si no se envió. |
| **status** | Estado resultante: `SUBMITTED` \| `SIMULATED` \| `SKIPPED` \| `REJECTED` (ej. por circuito abierto). |
| **error** | Opcional; mensaje o código si la llamada al CLOB falló (solo cuando decision=SEND). |

**Precondiciones que el Gateway comprueba (en orden):** I1 → I2 → I4; luego I5 (registro). **Solo cuando** la decisión será SEND: aplicar I6 (idempotencia de la solicitud) y entonces invocar al CLOB. Cuando la decisión es SIMULATE o SKIP_*, no se invoca al CLOB; I6 no aplica a la llamada (no hay llamada), solo la trazabilidad I5.

### 4.3 Alternativas descartadas

| Alternativa | Descripción | Motivo de descarte |
|-------------|-------------|--------------------|
| **Duplicar comprobaciones en cada camino** | Añadir I1/I2 en PolymarketAdapter y mantenerlas también en Execution. | Doble mantenimiento; riesgo de que un camino se actualice y el otro no; no cumple “un solo punto” (I3). |
| **Solo arreglar el camino Plans** | Hacer que PolymarketAdapter consulte execution_mode y system_active, sin unificar con Execution. | Siguen existiendo dos sitios que “deciden” enviar; más difícil de auditar y de testear que no queden atajos. |
| **Deshabilitar el camino Intents** | Dejar solo Execution Graph como camino de envío. | Cambio funcional grande; puede haber dependencias o escenarios que aún usen intents; no necesario si el Gateway unifica ambos. |
| **Comprobar solo en el cliente CLOB** | Poner la lógica en el wrapper del cliente (ej. PolymarketCLOBWrapper). | El wrapper puede ser invocado desde varios sitios; si alguien llama al cliente “raw” en el futuro, se salta la comprobación. El Gateway como capa explícita de “envío permitido sí/no” es más claro y auditable. |

### 4.4 Justificación

- **Seguridad:** Un solo punto permite revisar en PR que “todo lo que toca CLOB pasa por aquí” y que aquí se aplican siempre I1–I6.
- **Operación:** En incidentes, se puede desactivar envío real en un solo lugar (ej. forzar simulado en el Gateway).
- **Tests:** Un solo mock o spy del Gateway permite verificar “cero envíos reales” en tests de integración sin tener que mockear múltiples rutas.
- **Trazabilidad:** Toda decisión de envío/simulación concentrada en un punto facilita logs y métricas coherentes (I5).

---

## 5. Contrato mínimo de observabilidad

### 5.1 Eventos que deben existir

| Evento | Cuándo | IDs obligatorios | Uso UI / Ops |
|--------|--------|-------------------|--------------|
| **strategy_activated** | Tras activar estrategia por API (éxito). | `strategy_id` | UI: reflejar estado; ops: auditar activaciones. |
| **strategy_deactivated** | Tras desactivar estrategia por API. | `strategy_id` | UI y ops: estado y auditoría. |
| **plan_queued** | Plan marcado `ready_for_execution`. | `plan_id`, `strategy_id`, `event_id`, `trace_id` | UI: “plan en cola”; ops: correlación. |
| **precheck_failed** | Precheck rechaza un plan. | `plan_id`, `trace_id`, `strategy_id`, `reasons[]` | UI: “por qué no se ejecutó”; ops: diagnóstico. |
| **order_decision** | Decisión de enviar o simular (en el Gateway). | `trace_id`, `plan_id` (si aplica), `strategy_id`, `execution_mode`, `system_active`, `decision` (SEND \| SIMULATE \| SKIP_*), **`source_path`** (INTENT \| PLAN), **`idempotency_key`** (cuando aplique, p. ej. submit_order) | Ops: auditoría y compliance; UI: opcional panel “últimas decisiones”. |
| **order_sent** / **order_simulated** | Orden enviada al CLOB o simulada. | `trace_id`, `plan_id` (si aplica), `platform_order_id` (o simulado), `strategy_id` | UI: estado de órdenes; ops: trazabilidad. |
| **order_fill** | Fill recibido (cuando el sistema lo consuma). | `trace_id`, `platform_order_id`, `strategy_id`, `fill_size`, `fill_price` | UI: PnL y posiciones; ops: reconciliación. |
| **system_paused** / **system_resumed** | Cambio de `system_active`. | - | UI y ops: estado del kill-switch. |

### 5.2 IDs que deben acompañar los eventos

- **trace_id:** En toda la cadena plan → precheck → execution → order. Permite correlacionar logs y UI.
- **plan_id:** En eventos de planes (plan_queued, precheck_failed, order_decision, order_sent/simulated).
- **strategy_id:** En todos los eventos de estrategia y órdenes.
- **platform_order_id:** En order_sent y order_fill (o id simulado cuando execution_mode != LIVE).
- **source_path:** En order_decision; valor INTENT o PLAN según el camino que originó la solicitud.
- **idempotency_key:** En order_decision cuando la operación es submit_order (o equivalente); opcional para cancel_order (identidad por platform_order_id).
- **reason_code:** En order_decision cuando decision != SEND; código que indica por qué no se envió (ej. DRY_RUN, SYSTEM_PAUSED, CIRCUIT_OPEN, LATENCY_RED).
- **reason_detail:** Opcional en order_decision; texto adicional para diagnóstico (ej. "circuit opened by consecutive fills failure").

### 5.3 Uso por UI y Ops

- **UI:** Mostrar “Why not trading?” (precheck_failed, reasons); estado de planes (queued / executing / completed); última decisión (order_decision) en modo LIVE; lista de órdenes y fills por estrategia.
- **Ops:** Auditar que cuando `execution_mode != LIVE` solo hay `order_simulated` y nunca llamadas reales al CLOB; correlacionar incidentes con trace_id; comprobar que system_paused implica ausencia de order_sent.

### 5.4 Expectativas de retención

| Dato / Canal | Retención mínima | Notas |
|--------------|------------------|--------|
| **order_decision** (y eventos del Gateway) | 90 días | Auditoría y compliance; deben poder reconstruirse “quién decidió qué y cuándo”. |
| **order_sent / order_simulated / order_fill** | 90 días | Trazabilidad de órdenes y fills; reconciliación con Polymarket. |
| **precheck_failed** (con reasons) | 30 días | Diagnóstico de “why not trading”; no es crítico a largo plazo. |
| **plan_queued**, **strategy_activated/deactivated** | 30 días | Correlación con planes y estado; suficiente para incidentes recientes. |
| **Logs de aplicación** que contengan trace_id, plan_id, strategy_id | Según política de logs (recomendado ≥ 30 días) | Permiten correlacionar eventos con stack y errores. |

Formato y soporte (log estructurado, tabla de eventos, bus) quedan fuera de esta SPEC; solo se fija la **expectativa de retención** para que UI y ops puedan asumir disponibilidad en ese horizonte.

---

## 6. Orden de implementación (hardening)

### 6.1 Prioridad y dependencias

El orden debe **no comprometer seguridad**: primero se cierra el único punto de envío y las invariantes; después se hace visible la recarga de estrategias (que hoy no envía por el bug 4.1, pero cuando se arregle no debe enviar sin comprobaciones).

| Fase | Contenido | Criterio de cierre | Estado |
|------|-----------|--------------------| ------- |
| **F1** | **Execution Gateway (4.4 + 4.2 + 4.3)** | (1) Existe un único punto que aplica I1, I2, I4, I5, I6 antes de llamar al CLOB. (2) Camino Intents y camino Plans pasan por ese punto. (3) Tests DoD de 4.2, 4.3, 4.4 pasan. | ✅ Cerrada |
| **F2** | **Recarga de estrategias activas (4.1)** | (1) Control Loop recarga estrategias activas con periodicidad definida o evento. (2) Tests DoD de 4.1 pasan. | ✅ Cerrada |
| **F3** | **Contrato de observabilidad** | (1) Eventos listados en §5 existen y llevan los IDs indicados. (2) order_decision emitido en el Gateway para cada decisión. | ✅ Cerrada |
| **F4** | **Mejoras no críticas** | Runbooks, límites de riesgo en Execution Graph, reintentos/compensación, etc. | ✅ Cerrada |

> **Nota (2026-02-02):** Todas las fases completadas. Ver `docs/operations/runbook.md` para documentación operativa actualizada.

### 6.2 Qué NO debe hacerse antes de cerrar los puntos críticos

- **No** añadir nuevos caminos que envíen órdenes al CLOB sin pasar por el Gateway (una vez definido).
- **No** hacer “mejoras” en PolymarketAdapter que invoquen al cliente directamente para envío real sin pasar por la comprobación de I1/I2.
- **No** priorizar F2 por delante de F1: si primero se “arregla” la recarga de estrategias sin tener el Gateway, el camino Plans seguiría pudiendo enviar en DRY_RUN o con system_active=false cuando esa estrategia empiece a generar planes.
- **No** considerar cerrada la SPEC sin que los tests de Definition of Done de 4.1–4.4 estén verdes y documentados.

### 6.3 Checklist de PR (resumen)

Para cualquier PR que toque activación, control loop, execution graph o envío de órdenes:

- [ ] ¿Se mantienen las invariantes I1–I6? (Si el PR añade o modifica un camino de envío, ¿pasa por el único punto que aplica I1–I4 e I6?)
- [ ] ¿Hay test o justificación explícita de que no se envían órdenes reales cuando execution_mode != LIVE ni cuando system_active=false?
- [ ] Si afecta al Control Loop: ¿la recarga de estrategias activas sigue definida y testeada?
- [ ] Si afecta al Gateway o al adaptador: ¿los eventos de observabilidad (al menos order_decision) siguen emitidos con los IDs del §5 (incluyendo source_path, reason_code cuando aplique)?
- [ ] ¿Se respeta la invariante de idempotencia I6 cuando decision=SEND (una sola llamada efectiva al CLOB por idempotency_key / platform_order_id)?
- [ ] ¿Existe y funciona la regla de CI/lint/grep que bloquea llamadas directas al cliente CLOB fuera del Execution Gateway (DoD 4.4.4)?

---

## 7. Anti-patterns (rechazo en PR)

Los siguientes patrones **deben rechazarse** en review cuando el PR toque envío de órdenes, Control Loop, Gateway o adaptador:

| Anti-pattern | Descripción | Por qué rechazar |
|--------------|-------------|-------------------|
| **Bypass del Gateway** | Añadir o conservar una ruta que llame al cliente CLOB (o a PolymarketAdapter en modo “enviar real”) sin pasar por el Execution Gateway. | Viola I3; permite saltarse I1, I2, I4, I5, I6. |
| **Comprobar modo solo en un camino** | Aplicar execution_mode o system_active en un solo camino (ej. solo Intents o solo Plans) y dejar el otro sin comprobar. | Comportamiento inconsistente; riesgo de accidental live o bypass del kill-switch. |
| **Reenvío sin idempotencia** | Reintentar el envío de la misma orden (mismo plan_id/leg_id/trace_id) sin clave de idempotencia ni comprobación de estado previo, pudiendo provocar doble envío al CLOB. | Viola I6; riesgo de órdenes duplicadas y pérdida de control. |
| **“Solo en LIVE” como comentario** | Dejar lógica de “no enviar cuando execution_mode != LIVE” o “no enviar si pausado” como comentario o rama opcional sin garantía de que todo camino pase por el Gateway. | No es enforceable; un futuro cambio puede añadir un atajo. |
| **Nuevo cliente CLOB sin Gateway** | Introducir un nuevo cliente o wrapper que hable con el CLOB sin que todas las llamadas de escritura pasen por el Gateway. | Crea un segundo punto de envío; viola I3. |
| **Refresh de estrategias sin acotar ventana** | Implementar recarga de estrategias activas sin garantía de ventana temporal (ej. “en algún momento”) o sin tests de activación/desactivación rápida (DoD 4.1). | No cumple DoD 4.1; comportamiento indefinido en producción. |
| **Eventos sin IDs obligatorios** | Emitir order_decision u otros eventos del §5 sin los IDs obligatorios (trace_id, strategy_id, source_path, idempotency_key cuando aplique, etc.). | Rompe el contrato de observabilidad y la trazabilidad I5. |
| **Relajar invariantes “solo en este caso”** | Añadir excepciones a I1–I6 (ej. “en modo X sí se puede enviar sin comprobar”) sin actualizar esta SPEC y sin aprobación explícita documentada. | Erosiona la fuente de verdad y la seguridad por diseño. |

**Criterio de review:** Si el revisor identifica uno de estos anti-patterns, el PR debe quedar bloqueado hasta que se corrija o se documente una excepción aprobada en la SPEC.

---

## 8. Referencias

- Flujo de activación por modo: `docs/implementation/strategy-activate-flow.md`
- Plan Demo/Simulación/Live: `docs/implementation/PLAN_MODOS_DEMO_SIMULACION_LIVE.md`
- Execution engine y grafo: `docs/architecture/execution-engine.md`
- Order lifecycle: `docs/exchange/order-lifecycle.md`
- Config y execution_mode: `docs/architecture/config-driven.md`

---

**Fin de la SPEC.** Este documento es la **fuente de verdad** para Near Resolution en Live y permite **bloquear PRs** que: (1) envíen órdenes reales al CLOB cuando `execution_mode != LIVE`, (2) se salten el kill-switch (`system_active == false`), (3) introduzcan nuevos caminos de envío sin pasar por el Execution Gateway. Cualquier cambio que relaje las invariantes I1–I6 o introduzca un nuevo camino de envío sin pasar por el Gateway debe ser explícitamente aprobado y documentado como excepción. El documento queda listo para uso como **checklist de PR** y **referencia operativa**.
