# Guía de Nombres Simples en Frontend

**Principio**: El frontend debe usar nombres simples y amigables. Los nombres técnicos solo existen en el backend.

---

## Mapeo UI → Backend

### Orderbook Constraints

| UI Label (Simple) | Backend Key (Técnico) | Tooltip |
|-------------------|----------------------|---------|
| **Book Freshness** | `max_book_staleness_ms` | "Tiempo máximo que puede pasar sin actualizarse el orderbook (ms). Si es muy alto, los precios pueden estar desactualizados." |
| **Max Spread** | `max_spread_bps` | "Diferencia máxima entre mejor bid y ask (en basis points). Spread alto = menos liquidez." |
| **Min Liquidity** | `min_depth_usdc_at_50bps` | "Liquidez mínima disponible a 50bps del mejor precio (USDC). Asegura que hay suficiente volumen para tu orden." |
| **Max Price Impact** | `max_impact_bps` | "Impacto máximo en precio al ejecutar tu orden (basis points). Impacto alto = tu orden mueve el mercado." |

### Timing

| UI Label (Simple) | Backend Key (Técnico) | Tooltip |
|-------------------|----------------------|---------|
| **Wait After Finish** | `min_seconds_since_finished` | "Segundos mínimos a esperar después de que termine el evento. Evita falsos positivos antes de confirmación." |
| **Max Time After Finish** | `max_seconds_since_finished` | "Segundos máximos después de que termine el evento. Evita entrar cuando la liquidez ya se agotó." |

### Sizing

| UI Label (Simple) | Backend Key (Técnico) | Tooltip |
|-------------------|----------------------|---------|
| **Order Size** | `order_usdc` | "Tamaño de orden en USDC (fijo o rango)." |
| **Smart Sizing** | `capacity_sizing_enabled` | "Ajusta automáticamente el tamaño según la liquidez disponible. Evita órdenes demasiado grandes que muevan el mercado." |

### Execution

| UI Label (Simple) | Backend Key (Técnico) | Tooltip |
|-------------------|----------------------|---------|
| **Order Type** | `order_mode` | "Market = ejecuta inmediatamente. Limit = espera a que alguien tome tu precio." |
| **Order Timeout** | `ttl_ms` | "Tiempo máximo que la orden puede estar pendiente (ms). Si expira, se cancela." |
| **Price Drift Limit** | `drift_bps_limit` | "Cambio máximo permitido en precio desde que se creó el plan (basis points). Si el precio cambia mucho, no ejecuta." |
| **Price Step** | `tick_size` | "Paso mínimo de precio permitido (ej: 0.001). Los precios se redondean a este paso." |
| **Improve Price By** | `improve_ticks` | "Mejora el precio en X pasos respecto al mejor bid. Aumenta probabilidad de ejecución." |

---

## Nombres en Tablas

### Markets/Events Table

| UI Column (Simple) | Backend Field | Tooltip |
|-------------------|---------------|---------|
| **Status** | `state` | "Estado del evento: In Play, Finished, Resolved" |
| **Best Price** | `best_bid_price / best_ask_price` | "Mejor bid / mejor ask disponible" |
| **Spread** | `spread_bps` | "Diferencia entre mejor bid y ask. Spread bajo = más liquidez." |
| **Liquidity** | `depth_usdc_at_50bps` | "Liquidez disponible a 50bps del mejor precio" |
| **Impact** | `impact_bps_for_usdc_1000` | "Impacto en precio al ejecutar $1000" |
| **Freshness** | `staleness_ms` | "Tiempo desde última actualización del orderbook. Fresco = datos actualizados." |
| **Last Action** | `last_action` | "Última acción realizada: Plan Created, Precheck Failed, Filled" |

### Precheck Failures

| UI Label (Simple) | Backend Reason | Tooltip |
|-------------------|----------------|---------|
| **Book Stale** | `stale_book` | "Órdenes rechazadas porque el orderbook estaba desactualizado" |
| **Price Changed** | `drift_too_high` | "Órdenes rechazadas porque el precio cambió demasiado" |
| **Impact Too High** | `impact_too_high` | "Órdenes rechazadas porque el impacto sería muy alto" |
| **Timeout** | `ttl_expired` | "Órdenes rechazadas porque expiró el tiempo límite" |

---

## Implementación

### Función de Mapeo

```tsx
// frontend/lib/field-mapping.ts
export const UI_TO_BACKEND_MAP: Record<string, string> = {
  "Book Freshness": "max_book_staleness_ms",
  "Max Spread": "max_spread_bps",
  "Min Liquidity": "min_depth_usdc_at_50bps",
  "Max Price Impact": "max_impact_bps",
  "Wait After Finish": "min_seconds_since_finished",
  "Max Time After Finish": "max_seconds_since_finished",
  "Order Size": "order_usdc",
  "Smart Sizing": "capacity_sizing_enabled",
  "Order Type": "order_mode",
  "Order Timeout": "ttl_ms",
  "Price Drift Limit": "drift_bps_limit",
  "Price Step": "tick_size",
  "Improve Price By": "improve_ticks",
};

export const BACKEND_TO_UI_MAP: Record<string, string> = Object.fromEntries(
  Object.entries(UI_TO_BACKEND_MAP).map(([ui, backend]) => [backend, ui])
);

export function uiLabelToBackendKey(uiLabel: string): string {
  return UI_TO_BACKEND_MAP[uiLabel] || uiLabel;
}

export function backendKeyToUiLabel(backendKey: string): string {
  return BACKEND_TO_UI_MAP[backendKey] || backendKey;
}
```

### Uso en Form

```tsx
// Al guardar
const formData = {
  [uiLabelToBackendKey("Book Freshness")]: formValues["Book Freshness"],
  [uiLabelToBackendKey("Max Spread")]: formValues["Max Spread"],
  // ...
};

// Al cargar
const displayValues = {
  "Book Freshness": formData.max_book_staleness_ms,
  "Max Spread": formData.max_spread_bps,
  // ...
};
```

---

## Checklist de Verificación

- [ ] Todos los campos tienen nombres simples (no técnicos)
- [ ] Todos los campos tienen tooltips explicativos
- [ ] Las tablas usan nombres simples en columnas
- [ ] Los mensajes de error/warning son comprensibles
- [ ] El mapeo UI → Backend funciona correctamente
- [ ] Usuario no técnico puede entender qué hace cada campo

---

**Fin de la Guía**



