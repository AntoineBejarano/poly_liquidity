# Strategy Page Layout Contract

**Purpose:** Cross-layout consistency and shared mental model across Tipster, Liquidity, and Surebet strategy pages.

**Scope:** UI only. No backend changes.

---

## 1. Fixed Zones (Canonical Order)

All strategy Live pages use the same **zone sequence**. Zones are structural slots; content varies by layout type.

| # | Zone | Description | Always visible |
|---|------|-------------|----------------|
| 0 | **Alert Banner Stack** | Max 2 banners visible; overflow collapsed into "N más" | When non-empty |
| 1 | **Header** | Strategy name, status badge, Pause/Stop/Activate, Config, Desk, Métricas, Logs | Yes |
| 2 | **Context Strip** | Modo, eventos asignados, badge tipo, última actualización | Yes |
| 3 | **KPI Strip** | PnL, exposición, intentos (InfoTooltip), tasa acierto, última acción | Yes |
| 4 | **Core Panel** | Contenido type-specific (ver taxonomía) | Yes |
| 4.5 | **Confirmación Externa** | Solo cuando hay checkers configurados; colocado tras Core | Condicional |
| 5 | **Execution Feed** | Tabla de ejecuciones (compacta, densa) | Yes |
| 6 | **Risk** | Monitor de riesgo, límites, alertas | Yes |
| 7 | **Activity Log** | Entradas de actividad reciente | Yes |

**Zone 0 rules:** Máximo 2 banners visibles. Si hay más, mostrar los 2 más severos y un control "N alertas más" que expande. Severidad: Error > Warning > Info.

**Invariant:** Zonas 1–3 y 5–7 en el mismo orden. Zona 4 (Core Panel) es la única variable. Zona 4.5 solo cuando Confirmación Externa está configurada.

---

## 2. Panel Taxonomy

### Base (all layouts)

| Panel | Zone | Descripción |
|-------|------|-------------|
| Header | 1 | StrategyHeaderWithLoader |
| Context Strip | 2 | Modo, eventos, badge tipo, hora actualización |
| KPI Strip | 3 | LiveKPIStrip |
| Execution Feed | 5 | IntentsTableWithLoader |
| Risk | 6 | RiskMonitor |
| Activity Log | 7 | ActivityLog |

### Type-specific (Core Panel, Zone 4)

| Layout | Contenido Core Panel |
|--------|----------------------|
| **Tipster** | Pipeline de Tips — resumen pendientes/ejecutados + enlace a página Tips |
| **Liquidity** | Monitor de Señales (indicadores orderbook) |
| **Surebet** | Estado Venues, Snapshot Arbitraje, Pipeline Ejecución, Exposición Abierta — apilados en Zone 4 |

### Core-adjacent (Zone 4.5)

| Panel | Condición | Descripción |
|-------|-----------|-------------|
| Confirmación Externa | Cuando hay checkers configurados | Estado de checkers; va tras Core Panel, antes de Execution Feed |

### Advanced (opcionales, cross-linked)

| Panel | Layouts | Cuándo | Destino cross-link |
|-------|---------|--------|--------------------|
| Tips (página completa) | Tipster | "Ver todos" en Pipeline Tips | `/strategies/[id]/tips` |
| Pipeline de Eventos | Liquidity | Extiende Core | Inline |
| Posiciones | Liquidity, Surebet | Cuando existen | Inline o Desk |
| Salud Orderbook | Liquidity | Cuando hay datos | Inline |
| Capital Limits | Surebet | Siempre en Surebet | Inline |
| Profit Metrics | Surebet | Cuando existe | Inline |
| Risk Alerts | Surebet | Cuando existen | Inline |
| Event-Level Controls | Surebet | Siempre en Surebet | Inline |
| Config | Todos | Header "Configurar" | `/strategies/[id]` |
| Desk | Todos | Header "Desk" | `/strategies/[id]/desk` |
| Métricas (histórico) | Todos | Header "Métricas" | `/strategies/[id]/live#metrics` |
| Logs | Todos | Header "Logs" | `/strategies/[id]/live#logs` |

---

## 3. Layout Type → Panels Mapping

| Panel | Tipster | Liquidity | Surebet |
|-------|:-------:|:---------:|:-------:|
| **Base** | | | |
| Header | ✓ | ✓ | ✓ |
| Context Strip | ✓ | ✓ | ✓ |
| KPI Strip | ✓ | ✓ | ✓ |
| Execution Feed | ✓ | ✓ | ✓ |
| Risk | ✓ | ✓ | ✓ |
| Activity Log | ✓ | ✓ | ✓ |
| **Type-specific (Zone 4)** | | | |
| Pipeline de Tips | ✓ | — | — |
| Monitor de Señales | — | ✓ | — |
| Estado Venues / Arbitraje / etc. | — | — | ✓ |
| **Core-adjacent (Zone 4.5)** | | | |
| Confirmación Externa | ✓* | ✓* | — |
| **Advanced** | | | |
| Pipeline de Eventos | — | ✓ | — |
| Posiciones | — | ✓ | ✓ |
| Salud Orderbook | — | ✓* | — |
| Capital Limits / Profit / Alerts | — | — | ✓ |
| Tips (página completa) | link | — | — |

\* Condicional: cuando hay datos o checkers configurados.

---

## 4. Cross-Links a Paneles Omitidos

Si un panel **no** se muestra en el layout actual, el usuario debe alcanzarlo en ≤2 clics.

| Desde | Panel omitido | Cross-link | Clics |
|-------|---------------|------------|-------|
| Live Tipster | Tips (completo) | "Ver todos" en Pipeline de Tips | 1 |
| Cualquier Live | Config | Header "Configurar" | 1 |
| Cualquier Live | Desk | Header "Desk" | 1 |
| Cualquier Live | Métricas | Header "Métricas" → `#metrics` | 1 |
| Cualquier Live | Logs | Header "Logs" → `#logs` | 1 |
| Config Tipster | Dashboard Tips | Botón "Tips" en header estrategia | 1 |
| Liquidity (sin eventos) | Asignar eventos | Context Strip → Desk o Universe | 1–2 |
| Surebet | — | Todos los paneles inline | 0 |

**Regla:** Todo panel avanzado existente para un tipo de layout debe ser alcanzable desde Live vía Header o Core Panel en ≤2 clics.

---

## 5. Empty vs Disabled vs Degraded

| Estado | Definición | CTA | Ejemplo |
|--------|------------|-----|---------|
| **Empty** | Datos obtenidos correctamente; no hay ítems. | CTA primario si la acción es posible (ej. "Asignar en Desk"). Secundario si relevante. | "No hay tips aún." + "Ver Tips" / "Configurar canales" |
| **Disabled** | Fetch falló o bloqueado (sin conexión, no autorizado). | Sin CTA hasta que retry funcione. Mostrar skeleton o "—". | Skeleton en KPI Strip cuando live-status no responde |
| **Degraded** | Datos parciales o condición que limita operación. | CTA hacia recuperación (ej. link a Settings, reintentar). Ver sección 11. | "Telegram: Desconectado" + badge |

**Regla CTA:** Empty → CTA cuando el usuario puede actuar. Disabled → ningún CTA (solo reintento implícito). Degraded → CTA explícito hacia resolución.

**Copy por panel (Empty):**

| Panel | Copy | CTA |
|-------|------|-----|
| Pipeline de Tips | "No hay tips. Aparecen cuando el listener reciba mensajes." | "Ver Tips" / "Configurar canales" |
| Execution Feed | "No hay ejecuciones aún." | — |
| Monitor de Señales | Badge "Desconectado" | — |
| Pipeline de Eventos | "No hay eventos activos en el pipeline." | "Asignar en Desk" / "Configurar Universe" |
| Posiciones | "No hay posiciones abiertas." | — |
| Context Strip (sin eventos) | "Eventos asignados: Ninguno." | "Desk" + "Universe" |

---

## 6. Nomenclatura (español institucional)

Todo el texto visible en español. Sin mezcla ES/EN salvo términos de producto establecidos.

| Concepto | Etiqueta canónica | InfoTooltip |
|----------|-------------------|-------------|
| Nombre estrategia | [Nombre] | — |
| Estado | En ejecución / Pausado / Detenido | — |
| Modo | Modo: Real / Papel / Simulación | — |
| Eventos | Eventos asignados: N / Ninguno | — |
| PnL | PnL | — |
| Exposición | Exposición | — |
| Intentos | Intentos | Sí: "Solicitudes de ejecución emitidas por el grafo de decisión" |
| Tasa acierto | Tasa acierto | — |
| Última acción | Última acción (o Δt) | — |
| Pipeline Tips | Pipeline de Tips | — |
| Señales | Monitor de Señales | — |
| Ejecuciones | Feed de Ejecución | — |
| Riesgo | Monitor de Riesgo | — |
| Logs | Logs de Actividad | — |

---

## 7. Acceptance Criteria

### AC1: Entender en &lt;10 s
- [ ] Nombre, estado y badge tipo visibles de inmediato.
- [ ] Context Strip muestra modo y eventos de un vistazo.
- [ ] KPI Strip muestra PnL, exposición, intentos sin scroll.
- [ ] Etiqueta Core Panel identifica layout (Pipeline de Tips / Monitor de Señales / bloques Surebet).

### AC2: Llegar a panel omitido en ≤2 clics
- [ ] Desde Live, Config, Desk, Métricas, Logs a 1 clic vía Header.
- [ ] "Ver todos" en Pipeline Tips llega a página Tips en 1 clic.
- [ ] Empty state "Asignar en Desk" llega a Desk en 1 clic.
- [ ] Ningún panel requiere &gt;2 clics desde Live o sus empty states.

### AC3: Consistencia mental
- [ ] Mismo orden de zonas en Tipster, Liquidity, Surebet.
- [ ] Badge tipo siempre visible en Context Strip.
- [ ] Controles Header idénticos en todos los layouts.

---

## 8. Implementation Checklist (Future)

- [ ] Implementar Zone 0 (Alert Banner Stack): máx 2 banners + collapse "N alertas más".
- [ ] Mover Confirmación Externa a Zone 4.5 cuando checkers configurados.
- [ ] Unificar layout Surebet con mismo orden de zonas.
- [ ] Añadir badge "Surebet" a Context Strip Surebet.
- [ ] Añadir LiveKPIStrip a Surebet.
- [ ] Implementar umbrales staleness: KPI &gt;5 min, Tips &gt;30 s, Execution Feed &gt;15 s.
- [ ] Unificar nomenclatura a español; añadir InfoTooltip a "Intentos".

---

## 9. Above-the-Fold (Viewport 1440×900)

Sin scroll, debe verse:

| Zona | Requerido above-fold | Notas |
|------|----------------------|-------|
| 0 (Alertas) | Si hay alertas, máx 2 visibles | |
| Header | Completo | Nombre, estado, controles |
| Context Strip | Completo | Modo, eventos, badge tipo, última actualización |
| KPI Strip | Completo | Todas las métricas en una fila |
| Core Panel | Título + primera sección | Ej. "Pipeline de Tips" + 1 fila o resumen |
| 4.5 (Confirmación Externa) | Si configurado | |
| Execution Feed | Título + ≥3 filas (o copy empty) | Estructura de tabla evidente |
| Risk | Título sección | "Monitor de Riesgo"; contenido puede estar abajo |
| Activity Log | Puede estar abajo | — |

**Invariante:** Identidad (nombre, estado, tipo), contexto (modo, eventos), KPIs e inicio de Core + Execution Feed visibles sin scroll. Risk y Activity Log pueden requerir un scroll.

---

## 10. Semántica de Paneles

Recursos (nombres lógicos; rutas concretas según implementación).

| Panel | Recurso | Cadencia refresco | Umbral staleness | Indicador staleness | Empty | Disabled |
|-------|---------|-------------------|------------------|---------------------|-------|----------|
| Header | `strategy` | Carga, tras acciones | — | — | N/A | Skeleton |
| Context Strip | `execution-mode`, `strategy-events` | Carga, 60s | — | — | "Ninguno" eventos | — |
| KPI Strip | `live-status` | 2–5 s | **&gt;5 min** | "Hace N min" en Δt; si &gt;5 min, tint muted | Ceros | Skeleton |
| Pipeline de Tips | `tip-intents/summary` | 5 s | **&gt;30 s** | Si último fetch &gt;30 s: badge "Datos desactualizados" | "No hay tips" | Skeleton |
| Monitor de Señales | WebSocket `decision_trace` | Tiempo real | — | Badge "Desconectado" si WS caído | Sin indicadores | Badge |
| Execution Feed | `executions` | 5–10 s (+ WS si hay) | **&gt;15 s** | Si último fetch &gt;15 s: indicador discreto (ej. punto ámbar) | "No hay ejecuciones aún" | Skeleton |
| Pipeline de Eventos | `event-pipeline` | 2–5 s | — | — | "No hay eventos activos" | — |
| Risk | `live-status`, `risk_config` | 2–5 s | — | — | (Siempre exposición) | — |
| Activity Log | `strategy-logs` | 10 s | — | — | Lista vacía | — |
| Confirmación Externa | `checkers` | 10 s | Latencia por checker | Per-checker | "No hay checkers configurados" | — |
| Salud Orderbook | `live-status.orderbook_health` | 2–5 s | Por asset | `staleness_ms` | "No Data" | — |
| Estado Venues (Surebet) | `venue-health` | 2–5 s | Por venue | Por venue | — | — |

**Empty vs Disabled vs Degraded:** Ver sección 5. Resumen: Empty = datos ok, sin ítems → CTA si aplica. Disabled = fetch falló → skeleton, sin CTA. Degraded = condición que limita → badge/banner + CTA a resolución.

---

## 11. Estados Degradados / Seguridad

Banners y badges para fallos o degradación. Mostrar en Zone 0 (Alert Banner Stack) o inline; sin jerga nueva (InfoTooltip si término técnico inevitable).

| Condición | Ubicación | Tratamiento | InfoTooltip |
|-----------|-----------|-------------|-------------|
| Checkers ausentes | Panel Confirmación Externa | "No hay checkers configurados para esta estrategia." | — |
| Quorum no alcanzado | Zone 0 | "Confirmación externa insuficiente: menos checkers de los requeridos." | Sí si se usa "quorum" |
| Fuente externa caída | Core Panel o badge inline | "Telegram: Desconectado" / "PS3838: Sin respuesta" | — |
| Venue de ejecución caída | Zone 0 | "Polymarket CLOB no disponible. Órdenes en cola." | — |
| Cache desactualizado | Inline en panel afectado | "Datos hace N min" o por asset | — |
| Wallet no configurada | Zone 0 o alerta sobre Risk | "No hay wallet Polymarket configurada." + link Settings | — |
| Estrategia activa sin eventos | Context Strip | "La estrategia está activa pero no tiene mercados asignados." (ámbar) | — |
| Modo Demo / Simulación | Zone 0 | "Modo Demo" / "Modo Simulación" | — |

**Niveles de severidad:**

| Nivel | Uso | Estilo |
|-------|-----|--------|
| Info | Demo, simulación | Banner ámbar/gris |
| Warning | Sin eventos, cache stale, quorum en riesgo | Texto o badge ámbar |
| Error | Venue caída, fuente caída, wallet faltante | Banner o badge rojo/destructive |

**Regla:** Estado degradado visible en above-fold (Zone 0, Context Strip o inicio Core Panel) cuando bloquea o limita ejecución.
