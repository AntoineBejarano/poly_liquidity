# Plan: Optimización de Redis para mejorar la velocidad de la app

**Objetivo:** Usar Redis como cache distribuido en las partes no operativas de la app (discovery, markets, events, balance, Polymarket API) para reducir latencia, compartir cache entre instancias y persistir entre reinicios.

**Referencias:**
- Estado actual: [PLAN_DISCOVERY_UNIVERSE_STRATEGY_BUILDER.md](./PLAN_DISCOVERY_UNIVERSE_STRATEGY_BUILDER.md) (auditoría Redis/cache)
- Redis operativo ya implementado: `backend/app/core/latency_monitor.py`, `backend/app/core/redis_client.py`
- Documentación infra: [RAILWAY_DEPLOY.md](../infrastructure/RAILWAY_DEPLOY.md)

---

## 1. Estado actual (lo que ya tenemos)

### 1.1 Redis Client
- **Archivo:** `backend/app/core/redis_client.py`
- **Funcionalidad:** Cliente Redis con TCP nativo (preferido) y REST API (legacy Upstash)
- **Métodos disponibles:** `get`, `set`, `setex`, `delete`, `exists`, `ttl`, `get_json`, `set_json`, `set_nx`
- **Características:** Timeout 500ms por operación, fallback graceful si Redis no configurado, singleton global `redis_client`
- **Configuración:** `redis_url` (TCP), `upstash_redis_rest_url` + `upstash_redis_rest_token` (REST)

### 1.2 APICache (solo in-memory)
- **Archivo:** `backend/app/core/api_cache.py`
- **Funcionalidad:** Cache en memoria con TTL por patrón de clave
- **TTLs por patrón:** market_list 30s, market_detail 10s, orderbook 5s, price 5s, event_data 60s
- **API:** `get`, `set`, `invalidate`, `invalidate_pattern`, `clear`, `cleanup_expired`
- **No usa Redis**

### 1.3 Consumidores de APICache
| Consumidor | Datos cacheados | Patrón de uso |
|------------|-----------------|---------------|
| `api/markets.py` | markets_data (list, events) | get → si miss, fetch Gamma → set |
| `api/polymarket.py` | series, markets, events, outcomes, orderbook, balance | get → si miss, fetch API → set |
| `api/series.py` | series_data, markets_data | get → si miss, fetch Gamma → set |
| `api/dashboard.py` | balance | get → si miss, fetch → set |
| `core/scanner/scanner.py` | series, markets, events (Gamma) | get → si miss, fetch Gamma → set |
| `core/equity_snapshot_service.py` | balance | get → si miss, fetch → set |

### 1.4 LatencyMonitor (ya usa Redis)
- Cache de métricas con SWR
- Locks distribuidos, backoff
- No requiere cambios para este plan

---

## 2. Diseño objetivo

### 2.1 Patrón: Layered Cache (L1 + L2)
- **L1 (memoria):** Mantener como está. Lectura muy rápida, evita round-trip a Redis en hits frecuentes.
- **L2 (Redis):** Cache distribuido. Se consulta si L1 miss. Se escribe en ambos al set.
- **Flujo get:** L1 → si miss, L2 (Redis) → si miss, None (llamante hace fetch)
- **Flujo set:** Escribir en L1 y L2 (Redis)
- **Fallback:** Si Redis no configurado o falla, comportamiento actual (solo L1)

### 2.2 Namespace en Redis
- Prefijo para keys de APICache: `api_cache:` (evitar colisión con `latency:`, etc.)
- Key final: `api_cache:{cache_key}` donde `cache_key` es el mismo que usa APICache hoy
- Los consumidores no cambian las keys que usan; la serialización (JSON) se aplica internamente

### 2.3 TTL
- Usar los mismos TTLs que APICache por patrón (convertir `timedelta` a segundos para Redis)
- Redis `SETEX` con el TTL correspondiente

### 2.4 Serialización
- APICache guarda objetos Python (dicts, lists). Redis guarda strings.
- En L2: serializar con `json.dumps` al escribir, `json.loads` al leer
- Considerar valores no serializables: hoy los consumidores guardan JSON-serializables (respuestas API)

---

## 3. Fases de implementación

### Fase 1: Preparación y configuración

**Objetivo:** Asegurar que la infra y la configuración están listas.

**Tareas:**
1. Verificar que `redis[hiredis]` está en `requirements.txt` (recomendado para TCP más rápido).
2. Añadir en `settings.py` (si no existe):
   - `api_cache_redis_enabled: bool = True` — feature flag para activar L2 Redis en APICache.
   - Opcional: `api_cache_redis_prefix: str = "api_cache:"` — prefijo de keys.
3. Documentar en `.env.example` las variables Redis necesarias para APICache (mismas que LatencyMonitor: `REDIS_URL` o Upstash REST).
4. Crear script o comando para verificar conectividad Redis (ya existe `scripts/test_redis_connection.py`; validar que cubre el uso de APICache).

**Entregables:** Configuración lista, feature flag, documentación de variables.

---

### Fase 2: APICache con Redis L2

**Objetivo:** Integrar Redis como capa L2 en APICache sin romper el contrato actual.

**Tareas:**
1. Modificar `APICache` para que, cuando `api_cache_redis_enabled` y `redis_client._enabled`:
   - En `get`: si L1 miss, consultar `redis_client.get_json(api_cache:{key})`; si hit, popular L1 y retornar.
   - En `set`: además de L1, llamar `redis_client.set_json(api_cache:{key}, value, ttl_seconds)` (fire-and-forget o con timeout corto para no bloquear).
2. Mantener el comportamiento actual cuando Redis no está disponible: solo L1.
3. Respetar los timeouts de `redis_client` (500ms); si Redis falla o hace timeout, continuar solo con L1 (no fallar la request).
4. Asegurar que `value` es JSON-serializable; si no lo es, no escribir en L2 (solo L1) y loguear en debug.
5. El `cleanup_expired` actual solo afecta L1; Redis maneja TTL automáticamente, no requiere cleanup.

**Archivos afectados:** `backend/app/core/api_cache.py`, `backend/app/settings.py`.

**Entregables:** APICache con L2 Redis opcional, tests unitarios que validen get/set con y sin Redis.

---

### Fase 3: Invalidación distribuida

**Objetivo:** Cuando se invalida una clave o un patrón, que Redis también se actualice.

**Tareas:**
1. `invalidate(key)`: además de borrar de L1, llamar `redis_client.delete(api_cache:{key})`.
2. `invalidate_pattern(pattern)`: Redis no soporta delete por patrón de forma atómica. Opciones:
   - **A:** Mantener un set secundario en Redis con las keys del namespace `api_cache` y hacer SCAN+DEL (requiere `SCAN` en redis_client).
   - **B:** Por ahora, solo invalidar L1; documentar que invalidate_pattern no propaga a Redis hasta Phase 2 de Directory (cuando se definan keys más estructuradas).
   - **Recomendación:** B para esta fase; la invalidación por patrón se usa poco y L1 queda limpia; el TTL de Redis limita la staleness.
3. `clear()`: borrar todas las keys del prefijo `api_cache:*`. Si redis_client no tiene `delete_pattern`, iterar con `SCAN` o añadir método `delete_by_prefix` en redis_client.
   - Si no se implementa delete_by_prefix en Fase 3, documentar que `clear()` solo afecta L1.

**Archivos afectados:** `backend/app/core/api_cache.py`, posiblemente `backend/app/core/redis_client.py` (método `delete_by_prefix` o `scan_keys`).

**Entregables:** `invalidate` propaga a Redis; decisión documentada para `invalidate_pattern` y `clear`.

---

### Fase 4: Ajustes de TTL y observabilidad

**Objetivo:** Optimizar TTLs para velocidad vs freshness y añadir observabilidad mínima.

**Tareas:**
1. Revisar TTLs actuales por patrón; considerar aumentarlos ligeramente si Redis permite cache más durable sin impacto en freshness (ej. event_data 60s → 90s si el producto lo permite).
2. Añadir logs de debug opcionales: L1 hit, L2 hit, L2 miss, Redis error (no loguear en cada get por rendimiento; tal vez contador o muestreo).
3. Considerar métrica simple (si hay sistema de métricas): contador de L1 hits, L2 hits, L2 miss.
4. Documentar en el plan o en docs operativas: cómo verificar que Redis está siendo usado (logs, keys `api_cache:*` en Redis).

**Entregables:** TTLs revisados, observabilidad básica, documentación operativa.

---

### Fase 5: Validación y rollout

**Objetivo:** Validar el comportamiento en distintos escenarios y preparar el rollout.

**Tareas:**
1. Tests de integración: con Redis mock o Redis real (docker), validar flujo get/set con L2.
2. Test de fallback: con Redis desconectado, validar que la app funciona igual que antes (solo L1).
3. Test de múltiples instancias: dos procesos backend compartiendo Redis; validar que un set en uno se refleja en get del otro.
4. Actualizar tests existentes que mockean `api_cache` si la interfaz cambia (no debería; la API pública de APICache se mantiene).
5. Rollout: activar `api_cache_redis_enabled=True` en staging primero; monitorear latencia y errores; luego producción.

**Entregables:** Suite de tests actualizada, checklist de rollout, documentación de rollback (desactivar feature flag).

---

## 4. Dependencias y orden

```
Fase 1 (Preparación) 
    → Fase 2 (APICache L2)
        → Fase 3 (Invalidación)
            → Fase 4 (Ajustes)
                → Fase 5 (Validación)
```

- Fase 1 puede ejecutarse en paralelo con diseño de Fase 2.
- Fase 4 puede solaparse con Fase 3 si el mismo desarrollador trabaja en invalidación y TTLs.

---

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Redis lento o indisponible | Fallback a L1; timeouts estrictos; no bloquear la request |
| Keys muy grandes (payloads grandes) | Redis maneja valores grandes; monitorizar memoria; considerar compresión si crece |
| invalidate_pattern costoso | En Fase 3, optar por no propagar a Redis; TTL limita el impacto |
| Serialización de valores no JSON | Validar en set; si falla, solo L1 y log debug |

---

## 6. Criterios de éxito

- Con Redis configurado: reducción de latencia en endpoints que hoy dependen de APICache (markets, series, dashboard, polymarket).
- Cache compartido entre instancias: un reinicio de una instancia no pierde el cache si Redis está poblado.
- Sin Redis o con Redis caído: comportamiento idéntico al actual (solo L1).
- Sin regresiones en tests existentes.

---

## 7. Relación con otros planes

- **Directory (PLAN_DISCOVERY_UNIVERSE_STRATEGY_BUILDER):** Este plan mejora APICache genérico. El Directory cache-first puede usar Redis con índices estructurados en una fase posterior; APICache con Redis L2 es complementario y no lo sustituye.
- **LatencyMonitor:** Ya usa Redis; no requiere cambios. Las keys son distintas (`latency:*` vs `api_cache:*`).
