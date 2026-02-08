# Plan de implantación: estrategia Near-Resolution Liquidity Provider

**Objetivo del documento:** Fuente de verdad técnica para producción: arquitectura de estado L1/L2, datos, ejecución, riesgo, operación en vivo y UX trader. El Decision Graph es hot path y no depende de roundtrips a Redis; Redis es L2 (shared backing) para UI, observabilidad y recovery.

**Audiencia:** Ingeniería, auditoría técnica, operaciones, trading desk.

**Última actualización:** 2026-02.

**Convenciones:**  
- **Ya existe:** componente o contrato implementado en el código actual.  
- **A implementar / Propuesta:** decisión o diseño pendiente de implementación.

---

## 1. Objetivo de la estrategia (edge + cuándo existe)

### 1.1 Edge explotado

- **Latencia de resolución:** Polymarket cierra mercados con retraso respecto al fin del evento en el mundo real.
- **Ventana temporal:** Entre el momento en que el evento ya ha terminado (y una fuente externa lo confirma) y el cierre oficial del mercado.
- **Liquidez de cashout:** Usuarios quieren salir antes de la resolución; la estrategia ofrece liquidez comprando (típicamente BUY YES) a precios por debajo de 1.00, minimizando adverse selection al operar solo cuando el resultado está confirmado.
- **Riesgo limitado:** El resultado del evento ya está decidido; el riesgo principal es retraso o error de resolución, no el resultado del evento.

### 1.2 Cuándo existe la oportunidad

- El **evento real** ha terminado (p. ej. partido finalizado, resultado conocido).
- Una **fuente externa** confirma el resultado con un nivel de confianza aceptable.
- El **estado del evento** en el sistema es "finalizado confirmado" (p. ej. `event_state.state == "FINISHED_CONFIRMED"`).
- El **precio en el orderbook** (best ask para BUY YES) está dentro del rango configurado (p. ej. 0.95–0.98).
- El **orderbook** cumple condiciones de frescura (staleness), spread, depth e impact.
- Los **límites de riesgo** (exposure, tamaño) no se exceden.

La estrategia **no** hace market making genérico: opera solo en esta ventana near-resolution.

---

## 2. Arquitectura de estado: L1 in-memory + L2 Redis

### 2.1 Definición formal

- **L1 (in-memory, hot):** Caché en memoria del proceso del backend donde viven todos los datos de estado que el **Decision Graph** necesita para decidir en el hot path. El Decision Graph **no** hace roundtrips a Redis ni a red; solo lee L1. Latencia mínima y predecible.
- **L2 (Redis, shared backing):** Almacén compartido que recibe **copias** del estado publicado desde L1 (o desde los mismos producers que escriben L1). Sirve para: frontend/UI (snapshots y deltas), otros servicios, métricas/observabilidad, y **recovery / warm start** (al arrancar o tras fallo, se puede hidratar L1 desde L2 si L2 tiene datos recientes). Redis **no** es la lectura crítica del Decision Graph.

### 2.2 Qué datos viven en L1 (y por qué)

Todo lo que el Decision Graph lee en el hot path debe estar en L1:

| Dato en L1 | Descripción | Producer que escribe L1 |
|-------------|-------------|--------------------------|
| **orderbook_state** | Por asset_id: best bid/ask, sizes, spread_bps, depth a X bps, impact, staleness_ms, last_update_ts, **version** (sequence por escritura). | OrderbookService: recibe WS MARKET (Polymarket), calcula métricas, escribe en L1; cada escritura incrementa version. |
| **event_state** | Por event_id: state, confidence, quorum_used, last_updated_ts, **version**, source, health. | Event Watch / Checkers con regla de quorum (único escritor). **A implementar** si no está centralizado. |
| **external_data** | Confirmación externa por event_id (confirmed, result, confidence, timestamp, source, **version**, health). | Support Graph: fetch_external_source (cold path) escribe en L1 tras llamar API externa. |
| **market_state** | Por event_id: total_liquidity, last_price (indicativo; ver §6.2), metadata, **version**, health. | Agregador: Gamma (discovery, API pública) + métricas de orderbook; escribe L1. **A implementar** como único escritor. |
| **risk_state** | Por strategy_id: exposure, max_exposure, position_size, límites, **version** si aplica. | Risk Engine (o servicio de configuración) actualiza L1 cuando aplica. |
| **Concurrency locks** | Clave conceptual: `lock:decision:{strategy_id}:{event_id}`. Evita que dos hilos/coroutines ejecuten el Decision Graph para el mismo par a la vez. TTL corto (p. ej. 2–5 s). | Control Loop adquiere antes de ejecutar Decision Graph; libera al salir del flujo. |
| **Dedup markers** | Clave conceptual: `dedup:intent:{strategy_id}:{event_id}:{side}:{outcome}:{price_band}`. Marca que ya se emitió un intent equivalente en una ventana reciente; evita idempotencia duplicada. TTL distinto al lock (p. ej. 10–30 s). | Control Loop / intent emitter escribe tras emitir; comprueba antes de pasar a Risk/Execution. |

El Decision Graph (nodo collect_state y condiciones) lee **únicamente** de L1. Si una clave crítica falta en L1 o está STALE, no se opera (NO TRADE). Locks y dedup son conceptos separados: lock para concurrencia, dedup para idempotencia (ver §9).

### 2.3 Qué datos viven en L2 (Redis)

L2 no es la fuente de lectura del Decision Graph. L2 se usa para:

| Uso de L2 | Descripción |
|-----------|-------------|
| **Snapshots para frontend** | El terminal de trading puede solicitar al conectar un snapshot del estado (orderbook por asset_id, event_state, exposure, system_status) desde Redis; así el frontend no depende de que el proceso que tiene L1 le sirva directamente en el primer frame. |
| **Métricas / observabilidad** | Publicación de estado agregado o muestras para dashboards, alertas y monitoreo (staleness, health, latencia). |
| **Recovery / warm start (solo UI)** | Tras reinicio, L1 está vacío. L2→L1 se usa **solo para hidratar la UI** (snapshot para frontend desde Redis). **Trading queda bloqueado** hasta que se cumplan las condiciones de **TRADING_READY** (ver abajo). No se emiten intents LIVE ni se pasa a Execution usando solo datos cargados desde L2; el hot path de decisión depende exclusivamente de datos escritos en L1 por producers en vivo. |

**Estado operativo TRADING_READY (TradingDisabledUntilLive):** el sistema mantiene un estado interno **TRADING_READY** (o equivalente “TradingDisabledUntilLive” = true hasta que esté listo). Al **boot**, TRADING_READY = **false**. Se vuelve **true** solo cuando se cumplen todas las condiciones que apliquen:

- WS MARKET conectado y orderbook **fresh** (staleness dentro del umbral configurado para al menos los asset_id de interés).
- Quorum / checkers **healthy** (event_state con health=OK donde la estrategia lo requiera).
- external_data **fresh** (si la estrategia requiere confirmación externa, last_updated_ts dentro del umbral).
- **health=OK** en los State Objects críticos usados por la estrategia (orderbook_state, event_state, external_data, market_state según configuración).

Mientras **TRADING_READY = false**, el Control Loop puede evaluar triggers, ejecutar el Decision Graph en modo “solo lectura” y emitir **decision_tick** (para que el trader vea por qué no se opera), pero **no** puede emitir intents LIVE ni pasar a Execution. Es una condición operacional explícita, no una API nueva.
| **Locks / dedup en Redis (opcional)** | Copia de locks (concurrencia) y/o dedup markers (idempotencia) en Redis con TTL para que otros procesos o recuperación respeten las mismas reglas. |

La **publicación L1 → L2** se hace con throttling y coalescing (p. ej. no cada tick de orderbook; ventanas de 100–250 ms) para no saturar Redis ni el canal hacia UI.

### 2.4 Qué vive en DB (solo config e histórico)

La base de datos (PostgreSQL) almacena **solo**:

- Configuración persistente: estrategias, eventos asignados, External Data Sources, system_config, risk_config.
- Wallets (encriptadas) y asociación usuario/wallet.
- Histórico: ExecutionIntent, ExecutionPlan, decision_trace, órdenes y trades guardados.

La DB **no** es fuente de estado en tiempo real para el Decision Graph. El hot path no lee la DB para orderbook, event_state ni external_data; eso vive en L1.

### 2.5 Resumen L1 vs L2 vs DB

| Capa | Rol | Decision Graph lo lee |
|------|-----|------------------------|
| **L1 (in-memory)** | Estado vivo para decisión (hot path). | **Sí** — única fuente en el hot path. |
| **L2 (Redis)** | Snapshots para UI, observabilidad, recovery. | **No** — sin roundtrips a Redis en el Decision Graph. |
| **DB** | Config e histórico. | **No** para estado de mercado/evento/orderbook; sí para config de estrategia/evento ya cargada por el runtime. |

---

## 3. Frescura y coherencia del estado

### 3.1 Contrato mínimo de un State Object

Cualquier objeto de estado (orderbook_state, event_state, market_state, external_data, risk_state) que se use para decisión debe cumplir un contrato mínimo de frescura y trazabilidad. Campos recomendados (propuesta):

| Campo | Descripción |
|-------|-------------|
| **last_updated_ts** | Timestamp (epoch ms o ISO8601) de la última actualización. |
| **staleness_ms** | Tiempo transcurrido en ms desde last_updated_ts hasta “ahora” en el momento de la lectura (o se calcula en lectura). |
| **version / sequence** | Número monótono por clave (p. ej. por asset_id o event_id) que se incrementa en cada escritura. Permite ordenar updates y verificar que el snapshot de collect_state es coherente: todas las piezas leídas pertenecen a la misma “generación” de datos. Cada State Object en L1 debe llevar su **version** (o sequence). |
| **source** | Origen del dato (ej. "ws_market", "event_watch", "support_graph", "risk_engine"). |
| **health** | Estado de salud del dato: **OK** (válido y fresco), **STALE** (staleness por encima de umbral), **DEGRADED** (parcial o dudoso). |

**Uso de version/sequence para coherencia de snapshot:** el nodo **collect_state** debe capturar, en un único paso (o con barrera de lectura), todos los State Objects necesarios para ese (strategy_id, event_id) y registrar un **read_ts** (timestamp de la lectura) junto con las **versions** de cada objeto leído (orderbook_state.version, event_state.version, etc.). La evaluación posterior del Decision Graph usa solo esos valores capturados; no vuelve a leer L1 a mitad del grafo. Así se garantiza que las condiciones (precio, staleness, event_state, external_data) se evalúan sobre un snapshot coherente: mismo read_ts y conjunto de versions. **Las version son por dominio** (orderbook, event, external, risk): cada clave tiene su propia sequence. El snapshot es coherente porque se toma en un **mismo read_ts** y se registra el **set de versions** leído; **no** se requiere que las versions sean iguales entre dominios (no pueden serlo, son dominios distintos). Si en un tick posterior se detecta que alguna version cambió respecto a la usada en el último intent para ese par, puede usarse como señal de “datos nuevos” para considerar re-evaluación (opcional). En resumen: **collect_state captura read_ts + versions**; el grafo opera sobre esa captura atómica.

### 3.2 Umbrales recomendados (defaults “desk-friendly”) de staleness y TTL por tipo de dato

Valores por defecto sugeridos para operar “top del mercado”; cada entorno puede endurecer. Para evitar que ops relaje demasiado los umbrales, se define **default recomendado** y **límite máximo permitido** (no superar el máximo en configuración). Si staleness excede el umbral de decisión, el State Object se considera no válido para operar (NO TRADE).

| Tipo de dato | TTL en L1 / L2 (retención) | Default recomendado (staleness máx. decisión) | Límite máximo permitido | Notas |
|--------------|----------------------------|-----------------------------------------------|--------------------------|-------|
| **orderbook_state** | Retención en L1: hasta nuevo tick. TTL L2: 120 s. | **1000 ms** (max_book_staleness_ms). Libro fresco para evitar slippage y gaps de liquidez en el minuto final. | **1500 ms** (hard stop). No configurar por encima: 2 s de libro viejo es demasiado si el mercado se mueve rápido. | Near-resolution no exige microsegundos, pero 2 s puede ocultar movimientos o liquidez cambiante. |
| **external_data** (confirmación) | TTL en L1/L2: 3600 s. | **120 s** (2 min) a **180 s** (3 min). Para trading activo, bajar respecto a 5 min si la fuente es muy confiable. | **300 s** (5 min). Por encima, exigir reconfirmación. | 5 min solo si la fuente es muy confiable; para desk, 2–3 min es más seguro. |
| **event_state** | TTL en L1: 300 s; en L2 según publicación. | **30 s** a **60 s**. Si event_state no se ha actualizado, no confiar en FINISHED_CONFIRMED. | **60 s**. | El Event Watch debe refrescar con frecuencia. |
| **market_state** | TTL en L1: 120 s; en L2 según publicación. | **10 s** a **30 s**. 60 s puede ocultar cambios de liquidez o metadata. | **60 s**. | Agregador debe mantener market_state alineado con orderbook y Gamma. |

Estos umbrales se aplican en las reglas de decisión: si `staleness_ms > umbral` o `health == STALE`, el dato no se usa para abrir posición. La configuración no debe superar el **límite máximo permitido**.

### 3.3 Reglas de decisión

- **Si staleness excede umbral configurado** (según tabla §3.2 por tipo: orderbook, external_data, event_state, market_state) → **NO TRADE**. El Decision Graph debe tratar el dato como no válido para abrir posición.
- **Si falta alguna clave crítica** en L1 para el evento/estrategia (p. ej. orderbook_state para el asset_id, event_state, external_data cuando la estrategia requiere confirmación) → **NO TRADE**. No se emite intent.
- **Snapshot coherente:** el Decision Graph opera sobre la captura atómica de collect_state (read_ts + versions). No se relee L1 a mitad de la evaluación; así se evita que un producer actualice L1 entre condiciones y se garantiza coherencia.

### 3.4 Health y NO TRADE

- Si cualquier State Object necesario tiene **health != OK** (STALE o DEGRADED), la decisión debe ser no operar (idle o equivalente).
- Los motivos de NO TRADE (falta de wallet, staleness, clave faltante, health DEGRADED) deben ser **observables** en el trader terminal (logs de decisión, intent_emitted con razón “skipped” o risk_decision rejected con motivo), para que el operador sepa por qué no se tradó.

---

## 4. Orderbook público vs ejecución privada

### 4.1 WebSocket MARKET (público)

- **Qué es:** canal público de Polymarket con updates de orderbook por asset_id.
- **Quién lo consume:** backend (OrderbookService). Ref-count por estrategia/evento; al asignar eventos a una estrategia activa se suscriben los asset_id; al desasignar/desactivar se desuscriben.
- **Dónde se escribe:** **L1 primero** (orderbook_state por asset_id). Luego, publicación a L2 (Redis) con throttling para UI.
- **Uso:** el Decision Graph lee **solo** desde L1 (best bid/ask, spread, depth, impact, staleness). No usa fills ni órdenes propias como input de decisión.

### 4.2 WebSocket USER (privado por wallet)

- **Qué es:** canal por usuario/wallet en Polymarket con órdenes y fills de ese usuario.
- **Quién lo consume:** Execution Engine, asociado al usuario/wallet de la estrategia. **No existe CLOB global:** toda operación de trading (place order, estado de órdenes, fills) requiere wallet/usuario. El cliente CLOB y el USER WebSocket son por usuario/wallet.
- **Dónde se usa:** Execution Engine recibe fills/updates en tiempo real; pueden exponerse al frontend vía streaming (ver §13). El Decision Graph **no** usa fills ni estado de órdenes como input.

---

## 5. Flujo runtime: Control Loop, producers → L1, L1→L2, Decision Graph lee L1

### 5.1 Activación (API — ya existe)

- Usuario activa la estrategia (p. ej. "Play"). Frontend llama p. ej. `PATCH /api/strategies/{id}` con `is_active: true`.
- Backend persiste `is_active=true`. La estrategia queda activa para el Control Loop.

### 5.2 Data producers → actualizan L1 primero

Los siguientes componentes escriben **en L1** (no en Redis en el camino crítico):

1. **OrderbookService (WS MARKET):** recibe mensajes de orderbook por asset_id, calcula métricas (spread, depth, impact, staleness) y actualiza L1 `orderbook_state` por asset_id. Opcionalmente, con throttling, publica a L2 para UI.
2. **Event Watch / Checkers / Quorum:** determinan el estado del evento (p. ej. FINISHED_CONFIRMED) y escriben L1 `event.{event_id}.event_state`. Único escritor (propuesta §6).
3. **Support Graph (fetch external):** cuando se dispara (cold path), llama a la API externa, obtiene confirmación y escribe L1 `event.{event_id}.external_data.*` (o clave de confirmación). No escribe Redis en el camino crítico; L2 se puede rellenar después desde L1.
4. **Aggregator (market_state):** combina Gamma (discovery, API pública) y métricas de orderbook ya en L1, escribe L1 `event.{event_id}.market_state` (propuesta §6).
5. **Risk Engine (si aplica):** cuando actualiza exposición o límites, escribe L1 `strategy.{strategy_id}.risk_state`.

Ningún producer debe depender de Redis para que el Decision Graph funcione; Redis es destino de publicación para UI y recovery.

### 5.3 Publicación L1 → Redis (L2)

- Tras actualizar L1, un mecanismo de **publicación** (asíncrono, con throttling y coalescing) escribe en Redis las mismas claves o agregados para:
  - **Frontend:** snapshot al conectar y deltas en vivo (ver §13).
  - **Observabilidad:** métricas, health.
  - **Recovery:** warm start leyendo L2.
- **Throttle típico para orderbook:** 100–250 ms por asset_id (no cada tick). Coalescing: un solo update por ventana con el último estado o delta.
- No se exige que el Decision Graph espere a que L2 esté actualizado; el hot path solo depende de L1.

### 5.4 Control Loop (paso a paso)

1. **Refresh de estrategias activas** desde DB.
2. Por cada estrategia activa: eventos asignados (`StrategyEvent`).
3. Por cada evento: comprobar si debe observarse (timing, estado UPCOMING/ACTIVE).
4. **TRADING_READY (compuerta):** si el estado operativo **TRADING_READY** es false (p. ej. tras boot o warm start), no emitir intents LIVE ni pasar a Execution. Sí se puede evaluar triggers, ejecutar el Decision Graph en “solo lectura” y emitir **decision_tick** para que el trader vea el estado. Cuando TRADING_READY = true, continuar.
5. **Wallet readiness (compuerta):** antes de evaluar triggers que puedan generar intents live, comprobar si existe wallet configurada para el usuario dueño de la estrategia (o la wallet asociada).
   - **Si no hay wallet:** no generar intents que vayan a Risk/Execution (**fail closed**). Sí seguir observando, actualizando L1 (y publicando a L2), y **registrando en logs/traces y exponiendo en UI** que “no se emiten intents por falta de wallet”. Las decisiones y motivos deben ser visibles en el trader terminal.
   - **Si hay wallet:** continuar con evaluación de triggers y Decision Graph.
6. **Evaluación de triggers:** TriggerEvaluator lee **L1** (event_state, market_state, external_data) y determina si al menos un trigger se cumple. Triggers preferiblemente **event-driven** (reaccionar a cambios de L1 cuando los producers actualizan), no solo timer; si el diseño actual es por tick, los datos leídos en cada tick deben ser el snapshot L1 coherente.
7. **Concurrency lock:** antes de ejecutar el Decision Graph para (strategy_id, event_id), adquirir **lock de concurrencia** en L1 (clave conceptual `lock:decision:{strategy_id}:{event_id}`) con TTL corto (p. ej. 2–5 s). Si no se adquiere, otro flujo ya está evaluando ese par; no ejecutar Decision Graph en este tick. Al salir del flujo (tras ejecutar el grafo o tras fallo), liberar el lock. Evita ejecuciones paralelas del mismo par.
8. **Dedup marker (idempotencia):** antes de pasar intents a Risk/Execution, comprobar si existe **marcador de dedup** para (strategy_id, event_id, side, outcome, price_band) en L1 (clave conceptual `dedup:intent:...`). Si existe (intent equivalente ya emitido en la ventana reciente), no enviar de nuevo. Tras emitir y pasar a Risk/Execution, escribir el marcador con TTL mayor (p. ej. 10–30 s). TTL del dedup es distinto al del lock: el lock es corto (solo duración del grafo); el dedup es más largo para evitar repetir la misma operación lógica en triggers consecutivos.
9. Si trigger se cumple, lock adquirido y dedup no presente: ejecutar **Decision Graph leyendo solo L1** (snapshot coherente). Resultado: intents o planes.
10. Si intents directos (template Near-Resolution actual): pasar intents a Risk Engine; approved intents a Execution Engine (que usa CLOB por usuario/wallet). El Execution Engine aplica **pre-trade/preflight check** antes de enviar (ver §8.1).
11. Support Graphs (cold path) según triggers; pueden llamar APIs y escribir **L1** (y luego L2 si aplica).
12. Planes listos: si hay planes con `ready_for_execution=True` y `status=PLAN_BUILT`, ejecutar Execution Graph.
13. **Execution Engine:** usa cliente CLOB y WebSocket USER **por usuario/wallet**; no existe CLOB global.

### 5.5 Flujo concreto Near-Resolution (template `liquidity_near_end`)

- Decision Graph: **collect_state desde L1** → check_event_finished → check_price_range → (opcional) check_liquidity → calculate_size → emit_intent → idle.
- Salida: intents; se persisten en DB y se pasan a Risk y luego a Execution (con wallet readiness ya comprobada y lock/dedup evitando doble envío).
- Support Graph: fetch_external_source escribe confirmación en **L1** (y se publica a L2 para UI).
- Execution: Execution Engine obtiene cliente CLOB por usuario/wallet, firma EIP-712, envía al CLOB; WebSocket USER recibe fills.

---

## 6. Escritores únicos: event_state y market_state (L1)

### 6.1 event_state

- **Clave en L1:** `event.{event_id}.event_state`.
- **Contenido:** state (FINISHED_CONFIRMED, ACTIVE, etc.), confidence, quorum_used, last_updated_ts, y campos que el Decision Graph use. Debe cumplir contrato de State Object (§3).
- **Propuesta (a implementar):** un único escritor: **Event Watch / Checker** con regla de quorum. Escribe en **L1**; la publicación a L2 (Redis) puede hacerse por el mismo mecanismo L1→L2 (throttle/coalesce). El Decision Graph solo lee L1.

### 6.2 market_state

- **Clave en L1:** `event.{event_id}.market_state`.
- **Contenido:** total_liquidity, **last_price** (ver abajo), metadata. Cumple contrato de State Object (§3).
- **Significado de market_state.last_price:** es un precio **derivado o indicativo** (p. ej. último mid del orderbook, último trade conocido, o dato de Gamma si aplica). **No** es la fuente de verdad para condiciones de entrada de trading. Las **condiciones de entrada** (rango de precio, spread, depth, impact) deben basarse en **orderbook_state**: best bid / best ask (p. ej. `orderbook_state.best_ask_price` para BUY YES), spread_bps, depth_usdc_at_50bps, impact_bps_for_usdc_1000. Usar orderbook_state evita operar con un “last price” retrasado o no representativo del libro actual; el trader y el Decision Graph deben decidir con el top-of-book real. `market_state.last_price` puede usarse para UI, métricas o condiciones secundarias (p. ej. liquidez mínima), pero **no** como único criterio de precio para entrar.
- **Propuesta (a implementar):** un único escritor: **aggregator** que combina Gamma (API pública de discovery) + métricas de orderbook ya en L1, y escribe **L1** `event.{event_id}.market_state`. Discovery sigue siendo Gamma; no se inventan endpoints nuevos. Publicación a L2 para UI/recovery como el resto.

---

## 7. Lógica de decisión (alto nivel)

1. **Collect state:** leer de **L1** (no Redis): market_state, event_state, external_data, risk_state, orderbook_state (con `context.metadata.asset_id` para el asset_id del evento). Snapshot coherente (misma ventana/versión).
2. **Comprobar health y staleness:** si algún State Object tiene health != OK o staleness por encima de umbral → NO TRADE (idle); registrar motivo para UI.
3. **Evento finalizado y confirmado:** event_state.state == "FINISHED_CONFIRMED", external_data.event_confirmation.confirmed == true, sin ambigüedad si está configurado.
4. **Riesgo:** risk_state.exposure < max_exposure (y demás límites).
5. **Precio y orderbook:** las condiciones de entrada de precio deben basarse en **orderbook_state**, no en market_state.last_price: **orderbook_state.best_ask_price** (para BUY YES) en [price_min, price_max], orderbook_state.staleness_ms, spread_bps, depth_usdc_at_50bps, impact_bps_for_usdc_1000 dentro de límites. Ver §6.2: last_price en market_state es indicativo; la decisión de trading usa best bid/ask del libro.
6. **Liquidez (opcional):** market_state.total_liquidity >= min_liquidity (market_state sí puede usarse para liquidez agregada).
7. **Tamaño:** calcular (p. ej. fixed_range); emitir intent (BUY YES, precio, tamaño, razón). El Control Loop pasa a Risk y luego a Execution (wallet ya comprobada, lock/dedup aplicado).

El Decision Graph no llama APIs; solo lee L1 (hot path).

---

## 8. Lógica de ejecución (órdenes, monitoreo, cancelación)

- **Colocación:** intents aprobados por Risk; Execution Engine obtiene cliente CLOB **por usuario/wallet**, aplica **pre-trade/preflight check** (§8.1), firma EIP-712, envía al CLOB. Trazabilidad: trace_id, decision_trace.
- **Monitoreo:** WebSocket USER (por wallet) para fills/estado de órdenes; fallback polling si USER no está disponible. La estrategia (grafos) no monitorea órdenes.
- **Cancelación:** responsabilidad del Execution Engine / Order Lifecycle Manager (TTL, cancelación explícita, compensación).

### 8.1 Pre-trade / preflight check (fail-safe en Execution Engine)

Antes de firmar y enviar cada orden al CLOB, el Execution Engine debe ejecutar un **preflight check** obligatorio (propuesta). Si falla, no se envía la orden y se registra el motivo. Comprueba:

| Comprobación | Descripción |
|--------------|-------------|
| **system_active** | Kill-switch: si `system_active == false`, no enviar. Trading pausado. |
| **execution_mode** | Solo en modo LIVE se envían órdenes reales al CLOB; en DRY_RUN/PAPER no se envía orden real. |
| **Wallet** | Cliente CLOB y wallet válidos para el usuario; si no hay wallet configurada o el cliente no está disponible, no enviar (409 equivalente interno). |
| **Re-check staleness (opcional)** | Opcionalmente, volver a leer de L1 el orderbook_state (o la métrica relevante) para el asset_id de la orden y comprobar que staleness_ms sigue por debajo del umbral. Si el libro se ha vuelto STALE entre la decisión y el envío, se puede abortar o registrar para métricas (trade-off entre latencia y seguridad). |

Este preflight es una **última línea de defensa**; no sustituye las comprobaciones en el Decision Graph ni en Risk, pero evita envíos en condiciones de sistema pausado, modo incorrecto o wallet no disponible.

---

## 9. Locks (concurrencia) vs dedup markers (idempotencia)

Se usan dos mecanismos distintos, con **claves conceptuales y TTLs distintos**:

### 9.1 Lock de concurrencia

- **Objetivo:** evitar que dos ejecuciones del Decision Graph corran a la vez para el mismo (strategy_id, event_id).
- **Clave conceptual:** `lock:decision:{strategy_id}:{event_id}` (en L1; opcionalmente reflejada en Redis).
- **TTL:** corto, p. ej. **2–5 s**. Solo debe cubrir la duración de una ejecución del grafo. Se **libera explícitamente** al salir del flujo (éxito o error).
- **Uso:** antes de ejecutar el Decision Graph, adquirir el lock; si no se puede adquirir, no ejecutar en este tick (otro flujo ya está en curso). Tras ejecutar collect_state → condiciones → emit intent (o idle), liberar el lock.

### 9.2 Marcador de dedup (idempotencia)

- **Objetivo:** no enviar dos intents **equivalentes** (mismo strategy_id, event_id, side, outcome, en la misma banda de precio) en una ventana de tiempo; evita doble envío por triggers consecutivos.
- **Clave conceptual:** `dedup:intent:{strategy_id}:{event_id}:{side}:{outcome}:{price_band}` (price_band puede ser un bucket, p. ej. 0.01). En L1; opcionalmente en Redis.
- **TTL:** más largo que el lock, p. ej. **10–30 s**. Tras emitir un intent y pasarlo a Risk/Execution, se escribe el marcador; mientras exista, no se vuelve a emitir un intent equivalente.
- **Uso:** antes de pasar intents a Risk/Execution, comprobar si existe el marcador; si existe, no enviar (o enviar solo si la estrategia permite “retry” explícito). Tras enviar, escribir el marcador con TTL. El dedup es independiente del lock: el lock protege la ejecución concurrente del grafo; el dedup protege la repetición de la misma operación lógica en el tiempo.

---

## 10. Supuestos críticos y condiciones de seguridad

- **L1 como única lectura del Decision Graph:** el hot path no hace roundtrips a Redis ni a red; solo lee L1. Redis (L2) es para UI, observabilidad y recovery.
- **Sin CLOB global:** toda operación de trading requiere wallet/usuario; cliente CLOB y USER WebSocket son por usuario/wallet.
- **Wallet readiness:** compuerta antes de Risk/Execution; sin wallet no se generan intents live (fail closed); se sigue observando, actualizando L1 y publicando a L2, y **reportando en UI** motivo de no trading.
- **Snapshot coherente:** el Decision Graph opera sobre la captura atómica de collect_state (read_ts + versions de cada State Object); ver §3.1.
- **TRADING_READY:** el sistema mantiene un estado operativo **TRADING_READY**. Mientras sea **false** (p. ej. al boot o tras reinicio, “TradingDisabledUntilLive”), el Control Loop puede evaluar y emitir **decision_tick**, pero **no** puede emitir intents LIVE ni pasar a Execution. TRADING_READY pasa a true solo cuando WS MARKET + orderbook fresh, checkers healthy, external_data fresh si aplica, y health=OK en objetos críticos (ver §2.3).
- **Staleness y health:** si staleness excede umbral o health != OK → NO TRADE; motivos visibles en trader terminal.
- **Execution mode y system_active:** respetar DRY_RUN/PAPER/LIVE y kill-switch (system_active=false); en no-LIVE no se envían órdenes reales.
- **Escritores únicos en L1:** event_state y market_state tienen un único escritor que escribe L1 (propuesta §6).

---

## 11. Riesgos operativos y mitigación

| Riesgo | Mitigación |
|--------|------------|
| Staleness del orderbook | State Object con staleness_ms; condición NO TRADE si > max_book_staleness_ms; L1 actualizado por WS MARKET. |
| Spread / impact excesivos | Límites en condiciones (spread_bps, impact_bps_for_usdc_1000). |
| Exposición excesiva | risk_state en L1 y Risk Engine; rechazo de intents que superen límites. |
| Fuente externa lenta o errónea | Timeout y reintentos en fetch_external_source; no escribir en L1 si no fiable; no ambigüedad. |
| Resolución incorrecta o retrasada | Riesgo inherente; mitigación operativa (tamaño por evento, monitoreo). |
| Wallet no configurada | Fail closed; compuerta Wallet readiness; reportar en UI; no envío de órdenes. |
| Doble envío de intents | Lock/dedup en L1 (y opcionalmente Redis) por (strategy_id, event_id) o por (strategy_id, event_id, side, outcome, price_band) con TTL. |
| L1 vacío tras reinicio | L2→L1 solo para UI (snapshot para frontend). Trading bloqueado hasta que producers en vivo refresquen L1 y health=OK en State Objects críticos. |

---

## 12. Checklist de readiness para producción

- [ ] **L1:** Todos los datos necesarios para el Decision Graph (orderbook_state, event_state, external_data, market_state, risk_state) se escriben en L1 por producers definidos. Decision Graph lee solo L1.
- [ ] **Snapshot coherente:** Collect state lee L1 en una ventana atómica o con versionado coherente.
- [ ] **State Object contract:** last_updated_ts, staleness_ms, version/sequence, source, health en los objetos que participan en decisión; reglas NO TRADE cuando staleness o health lo exijan.
- [ ] **L1→L2:** Publicación desde L1 a Redis (L2) con throttling (p. ej. 100–250 ms para orderbook) y coalescing para UI y recovery.
- [ ] **Escritores únicos:** event_state y market_state con único escritor en L1 (§6).
- [ ] **asset_id:** context.metadata.asset_id (token primary) disponible para collect_state en L1.
- [ ] **Orderbook:** WS MARKET → L1; suscripción/desuscripción por estrategia/evento.
- [ ] **Wallet readiness:** compuerta antes de Risk/Execution; sin wallet no intents live; motivos visibles en UI.
- [ ] **Lock (concurrencia):** clave `lock:decision:{strategy_id}:{event_id}` en L1, TTL 2–5 s; adquirir antes de ejecutar Decision Graph, liberar al salir.
- [ ] **Dedup (idempotencia):** clave `dedup:intent:{strategy_id}:{event_id}:{side}:{outcome}:{price_band}` en L1, TTL 10–30 s; comprobar antes de pasar a Risk/Execution, escribir tras enviar.
- [ ] **Pre-trade/preflight check:** en Execution Engine, comprobar system_active, execution_mode, wallet antes de enviar; opcional re-check staleness.
- [ ] **Execution mode y kill-switch:** DRY_RUN/PAPER sin órdenes reales; system_active respetado.
- [ ] **CLOB por usuario:** flujo 409 WALLET_NOT_CONFIGURED probado; USER WebSocket por wallet.
- [ ] **Warm start / TRADING_READY:** L2→L1 solo para hidratar UI. TRADING_READY = false al boot; pasa a true solo cuando WS MARKET + orderbook fresh, checkers healthy, external_data fresh si aplica, health=OK en objetos críticos. Mientras TRADING_READY = false, no emitir intents LIVE ni pasar a Execution (sí emitir decision_tick).
- [ ] **Métricas y alertas:** L1 health, staleness, L2 publication lag, Decision Graph, Risk, Execution, runtime (§14).

---

## 13. Publicación en vivo a frontend (Trader UX)

### 13.1 ¿WebSocket backend→frontend para terminal live?

**Sí.** Para un terminal de trading en vivo con orderbook, fills, risk y estado del sistema en tiempo real, un canal de streaming backend→frontend (WebSocket) es recomendable: baja latencia, push de eventos sin polling. REST se mantiene para configuración y comandos (activar/desactivar, ajustes); el WebSocket se usa para el feed en vivo.

### 13.2 Contrato de mensajes (propuesta)

Sin inventar endpoints “oficiales”; se describe como **contrato** de mensajes que el backend puede enviar al frontend por el canal de streaming (propuesta):

| Tipo | Descripción | Alcance |
|------|-------------|---------|
| **orderbook_update** | Update de orderbook por asset_id (top-of-book, spread, depth, impact, staleness_ms, last_update_ts). Público. | Por asset_id suscrito. |
| **event_state_update** | Cambio de event_state (quorum o external). | Por event_id. |
| **external_data_update** | Cambio de confirmación externa (confirmed, result, confidence, timestamp). | Por event_id. |
| **intent_emitted** | Auditoría: intent generado por Decision Graph (strategy_id, event_id, side, price, size, reason); incluye si fue “skipped” (ej. no wallet, lock, staleness). | Por strategy_id / evento. |
| **risk_decision** | approved / rejected + reason (exposure, límite, etc.). | Por strategy_id. |
| **order_update** | Estado de orden del usuario (open, partial, filled, cancelled, failed, fill_ratio, slippage). **Privado por usuario.** | Canal usuario. |
| **exposure_update** / **position_update** | Cambio de exposición o posición por estrategia/mercado. | Por strategy_id / usuario. |
| **system_status** | Modo: LIVE/PAPER/DRY_RUN; Runtime Supervisor GREEN/YELLOW/RED; kill-switch (system_active); latency; WS health. | Global. |
| **decision_tick** (o equivalente) | **Por qué no se operó en este tick:** **failed_checks** (condiciones que fallaron), **métricas actuales** del snapshot, y para terminal “top”: **expected_edge_bps** (ej. 1 - best_ask para BUY YES, aproximado) y **capacity_usdc** (cuánto se podría comprar sin superar impact X bps, según depth). Así el trader ve: edge, capacidad y motivo de no entrada. | Por strategy_id / event_id. |

Formato de mensaje (propuesta): p. ej. `{ "type": "<tipo>", "ts": "<iso8601>", "payload": { ... } }`. Para **decision_tick**, el payload incluiría al menos: `strategy_id`, `event_id`, `outcome` ("no_trade" | "intent_emitted"), `failed_checks[]`, `snapshot_metrics` (best_ask, best_bid, staleness_ms, event_state.state, exposure, health por State Object). **Bonus terminal:** `expected_edge_bps` (ej. (1 - best_ask)*10000 para BUY YES en bps), `capacity_usdc` (tamaño en USDC que cabría sin superar el impact máximo configurado, derivado de depth/impact).

### 13.3 Snapshot inicial y deltas

- **Snapshot inicial al conectar:** el cliente obtiene el estado actual desde **Redis (L2)** (orderbook por asset_id suscritos, event_state, exposure, órdenes abiertas si aplica, system_status). Así el terminal tiene un frame completo sin depender del proceso que posee L1 en ese instante.
- **Deltas en tiempo real:** los updates en vivo provienen del backend: el backend publica desde **L1 a L2** (con throttle/coalesce) y/o envía por WebSocket los mismos eventos (orderbook_update, event_state_update, etc.) a los clientes suscritos. En la práctica, el feed en vivo puede ser “backend lee L1 y emite por WS” o “backend escribe L2 y el cliente recibe por WS lo que el servidor pushea desde L2”; el contrato es que el cliente recibe snapshot inicial desde L2 y deltas en tiempo real coherentes con el estado publicado por el backend.
- **Throttle:** orderbook 100–250 ms por asset_id.
- **Backpressure:** si el cliente va lento, el servidor puede reducir frecuencia o priorizar system_status, risk_decision, order_update.
- **Reconnection:** tras reconexión, el cliente solicita de nuevo snapshot desde L2 y luego recibe deltas.

### 13.4 Mensaje decision_tick para operar en vivo

Para que el trader pueda **operar en vivo** con visibilidad completa (y acercar el terminal a un “desk real”), el contrato incluye un mensaje de **decision_tick** (o nombre equivalente): cada vez que el Control Loop evalúa un (strategy_id, event_id) y **no** emite intent (o emite y se rechaza), el backend puede enviar por WebSocket un resumen de **por qué no se operó** y con **qué datos se evaluó**. Incluye:

- **failed_checks:** lista de identificadores de condiciones que fallaron (ej. event_state_stale, orderbook_stale, no_wallet, lock_held, dedup_active, price_out_of_range, spread_too_wide, exposure_limit, health_degraded).
- **snapshot_metrics:** métricas actuales del snapshot L1 usado en ese tick (p. ej. orderbook_state.best_ask_price, best_bid_price, staleness_ms, spread_bps; event_state.state; risk_state.exposure; health de cada State Object). Así el trader ve exactamente qué best_ask tenía el libro, qué staleness, y por qué no se cumplió el rango o la frescura.

**Campos adicionales para terminal “top del mercado” (propuesta):**

- **expected_edge_bps:** edge esperado en basis points, aunque sea aproximado. Para BUY YES near-resolution: p. ej. `(1 - best_ask) * 10000` (bps que se capturarían si se compra al best_ask y el mercado resuelve a 1). Permite al trader ver de un vistazo si el edge justifica entrar o si se ha comprimido.
- **capacity_usdc:** cuánto se podría comprar (en USDC) sin superar el impact máximo configurado (p. ej. impact_bps_for_usdc_1000), derivado de depth. Así el trader ve no solo “por qué no entró” sino **cuánto tamaño tendría** si entrara (liquidez disponible en el libro para su impacto aceptable).

Con esto el terminal puede mostrar en un panel de “última decisión”: **edge** (expected_edge_bps), **capacidad** (capacity_usdc) y **motivo de no entrada** (failed_checks + snapshot_metrics). Ejemplo: “No trade: best_ask 0.99 (fuera de rango 0.95–0.98), edge 100 bps, capacity 2.5k USDC, staleness 800 ms”. No se inventan endpoints; es un tipo más en el contrato de mensajes WS (propuesta).

---

## 14. Métricas a monitorear en live

- **L1:** Health de State Objects (OK/STALE/DEGRADED), staleness por asset_id y por event_id, existencia de claves críticas; version/sequence por clave; lock (concurrencia) y dedup (idempotencia) hits y misses.
- **L1→L2:** Lag de publicación (cuánto tarda un update de L1 en reflejarse en Redis); tasa de publicación por tipo.
- **Orderbook (L1):** spread_bps, depth, impact, update_rate_hz; errores de parseo/resync del WS MARKET.
- **Decision Graph:** ejecuciones por estrategia/evento, intents generados, condiciones que fallan (incl. NO TRADE por staleness/health/wallet).
- **Risk Engine:** intents recibidos vs aprobados vs rechazados; motivo de rechazo.
- **Execution Engine:** órdenes enviadas, filled, partial, cancelled; latency de envío; errores CLOB; uso USER vs polling.
- **Runtime:** system_active, execution_mode; Runtime Supervisor (GREEN/YELLOW/RED); circuit breakers.
- **Support Graph:** fetch_external_source (latency, errors, timeouts); escrituras L1 correctas.

---

## 15. Trader View: Top-of-Book + Context

Datos mínimos para una UX “top del mercado” (especificación de datos; no define APIs nuevas):

- **Orderbook (top):** best bid/ask por outcome, sizes en el top (shares/USDC), spread (bps), staleness_ms / last_update_ts, tick size si aplica.
- **Depth/impact:** depth a 25/50/100 bps en USDC, impact para sizes típicos ($500, $1k, $5k), imbalance bid vs ask.
- **Trades/microstructure (si disponible):** last trade price/time, agresor (taker side), prints/min.
- **Ejecución del usuario (privado):** órdenes abiertas por mercado/outcome, estado (open/partial/filled/cancelled/failed), fill ratio, avg fill time, slippage vs target_price, colas/retries.
- **Riesgo/inventory:** exposure por estrategia y por mercado/evento, capital libre vs comprometido, límites (max_global, max_market, max_order), PnL mark-to-market o “expected edge captured” si existe.
- **Estado del evento:** event_state, external confirmation (confidence, timestamp, sources), time since finished / time since last confirmation.

---

## 16. Referencias

- [Análisis completo Near-Resolution](near-resolution-complete-analysis.md) — Flujo de usuario, formularios, APIs de configuración.
- [Referencia de nodos de grafos](../architecture/graph-nodes-reference.md) — Nodos y State Cache.
- [Integración Polymarket](../exchange/polymarket-integration.md) — CLOB y WebSocket.
- [Kill-switch y controles de riesgo](../risk/kill-switch.md) — Circuit breakers y operación segura.
- [Secrets e infraestructura](../infrastructure/secrets.md) — Variables de entorno; Redis si aplica.
