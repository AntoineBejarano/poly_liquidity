# Runbook: Cache L2 Redis y GET /markets

**Plan:** [PLAN_REDIS_L2_CACHE.md](./PLAN_REDIS_L2_CACHE.md) — Sección 10.3.

Escenarios de operación y remediación cuando Redis, Gamma o el singleflight se degradan.

---

## 1. Redis caído o no disponible

### Síntomas

- Logs de arranque: `CACHE_PROVIDER=redis pero Redis no está disponible. Usando fallback a memory.`
- En runtime: `Gamma breaker ... (Redis): ...` o errores de timeout/connection en operaciones Redis.
- Headers `X-Cache-Provider` siguen en `redis` si el fallback no reconfigura el provider; en práctica el código usa **fallback a memory** si Redis falla al iniciar o en uso (el provider puede degradar a L1).

### Comportamiento esperado

- **Arranque:** Con `CACHE_PROVIDER=redis` y Redis inaccesible, la app arranca igual; usa cache en memoria y loguea **warnings** (no falla el startup).
- **Runtime:** Si el cliente Redis deja de responder (timeout, conexión cerrada), las operaciones de cache pueden devolver miss/error; el endpoint **no debe bloquear** el request: se degrada a miss y se llama a Gamma (respetando circuit breaker y rate limit).

### Acciones

1. **Verificar logs:** Buscar `Redis no está disponible`, `redis_latency_ms`, timeouts en el cliente Redis.
2. **Comprobar conectividad:** `REDIS_URL`, red/firewall, estado del servicio Redis (Upstash u otro).
3. **No bloquear tráfico:** La app debe seguir respondiendo (fallback a memory o fetch a Gamma). Si hay bloqueos, revisar timeouts en `redis_timeout_ms` (50–150 ms recomendado).
4. **Opcional:** Cambiar a `CACHE_PROVIDER=memory` para no intentar Redis hasta resolver la incidencia.
5. **Tras recuperar Redis:** Reinicio o reconexión del cliente; siguiente request con cache puede volver a usar L2 con normalidad.

---

## 2. Pico de Gamma 429 (rate limit)

### Síntomas

- Logs: `Gamma 429 rate limit exceeded for markets`, `circuit breaker OPEN`.
- Respuestas **503** en GET /markets cuando no hay entrada en cache (miss) y el circuit breaker está abierto.
- Headers `X-Gamma-Fetch-Count` en 0 cuando hay 503 por breaker.

### Comportamiento esperado

- Tras **3** fallos (429 o 5xx) en la ventana (60 s), el circuit breaker se **abre** (60 s de cooldown).
- **Si hay key en cache (aunque sea stale):** Se sirve ese valor (200), no se llama a Gamma.
- **Si no hay key (miss):** Se devuelve **503** sin llamar a Gamma para evitar más 429.

### Acciones

1. **Confirmar en logs:** `Gamma markets circuit breaker OPEN`, `failure_count=3`, `breaker_state=open`.
2. **Revisar límites y TTL:**
   - TTL de cache (broad 90 s + 60 s stale, narrow 300 s + 60 s) para reducir frecuencia de refrescos.
   - Lock singleflight (8–10 s) para evitar doble refresh por la misma key.
3. **No aumentar tráfico a Gamma** hasta que el breaker vuelva a cerrar (tras cooldown o tras éxito).
4. **Opcional:** Aumentar ligeramente `redis_lock_ttl_seconds` si los refreshes son muy justos en tiempo.
5. **Si el proveedor Gamma tiene cuotas mayores:** Ajustar uso (menos clientes, más cache) o contactar con el proveedor.

---

## 3. Posible stampede (muchas peticiones misma key)

### Síntomas

- Muchas peticiones simultáneas a la misma query (ej. GET /markets con mismos params) tras expiración soft.
- Logs: múltiples refreshes a Gamma para la misma key, o muchas llamadas a Gamma en poco tiempo.
- Posible 429 si el singleflight no está limitando bien.

### Comportamiento esperado

- **Singleflight:** Una sola request adquiere el lock (`lock:{key}`) y hace el refresh a Gamma; el resto sirve **stale** (o espera brevemente y luego sirve stale).
- Lock TTL **8–10 s** (≥ tiempo típico de Gamma) para que no expire antes de terminar el refresh.

### Acciones

1. **Revisar logs estructurados (Fase 8):** `cache_status=stale`, `redis_latency_ms`, `gamma_latency_ms`, `X-Cache-Refresh=1` — cuántas requests disparan refresh.
2. **Lock contention:** Si en logs aparece mucha contención (muchos intentos de lock para la misma key), el diseño es “uno refresha, resto sirve stale”; confirmar que solo **una** request por ventana hace refresh para esa key.
3. **Ajustar PX del lock:** Si el refresh a Gamma tarda más de 8–10 s a veces, valorar aumentar `redis_lock_ttl_seconds` (o implementar extensión de lock si está previsto).
4. **Cardinalidad:** Evitar cachear búsquedas (param `search`) en v1 para no multiplicar keys; revisar que los buckets (broad/narrow) siguen siendo deterministas.

---

## Referencia rápida

| Escenario        | Comportamiento esperado                    | Acción principal                          |
|------------------|--------------------------------------------|-------------------------------------------|
| Redis down       | Fallback memory / miss; no bloquear        | Revisar REDIS_*, timeouts, opcional memory |
| Gamma 429 spike   | Breaker OPEN → stale o 503 sin Gamma      | Revisar TTLs, límites, cooldown           |
| Stampede suspected| 1 refresh por key, resto stale            | Revisar singleflight, PX lock, logs        |

Variables relevantes: `CACHE_PROVIDER`, `REDIS_URL`, `REDIS_TIMEOUT_MS`, `REDIS_KEY_PREFIX`, `redis_lock_ttl_seconds`. Log estructurado: `markets_cache key_hash=... bucket=... cache_status=... redis_latency_ms=... gamma_latency_ms=... breaker_state=...`.
