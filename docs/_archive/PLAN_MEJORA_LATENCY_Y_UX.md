# Plan de Mejora: Latency Monitor y UX de Spinners

## Problemas Identificados

### 1. Backend: Saturación de API de Polymarket

**Problema:**
- El `LatencyMonitor` hace 2 llamadas HTTP a Polymarket cada vez que expira el cache (5 segundos)
- Si múltiples componentes llaman a `get_latency_metrics()`, se pueden hacer múltiples requests simultáneos
- El `MetricsCollector` llama a `get_latency_metrics()` periódicamente, aumentando la frecuencia
- Esto puede exceder los rate limits de Polymarket y causar errores 429/503

**Evidencia:**
- Warnings en logs: `Error measuring Polymarket Data API latency` y `Error measuring Polymarket Trading API latency`
- Cache TTL de solo 5 segundos es muy agresivo
- No hay rate limiting ni backoff exponencial

### 2. Frontend: Spinners Innecesarios en Actualizaciones

**Problema:**
- Cada página muestra un spinner completo (`LoadingSpinner fullScreen`) en cada actualización de datos
- Esto causa una mala UX porque bloquea la interfaz constantemente
- Los usuarios no pueden ver los datos mientras se actualizan

**Páginas afectadas:**
- `app/values/live/page.tsx`: `setLoading(true)` en cada `fetchData()`
- `app/dashboard/operations/page.tsx`: `setLoading(true)` en cada refresh
- `app/strategies/[id]/live/page.tsx`: `setLoading(true)` en cada refresh
- `app/markets/page.tsx`: Ya tiene lógica parcial para evitar esto, pero puede mejorarse

---

## Soluciones Implementadas

### Fase 1: Optimizar Latency Monitor (Backend) ✅ COMPLETADO

#### 1.1 Redis Client para Cache Distribuido ✅

**Objetivo:** Cache distribuido compartido entre múltiples instancias del backend

**Implementación:**
- ✅ Cliente Redis (`backend/app/core/redis_client.py`) usando Upstash REST API
- ✅ Singleton pattern para conexión compartida
- ✅ Fallback graceful si Redis no está configurado (usa cache en memoria)
- ✅ Métodos: `get`, `set`, `set_nx` (para locks atómicos), `exists`, `ttl`, `get_json`, `set_json`

**Archivo:** `backend/app/core/redis_client.py`

#### 1.2 SWR (Stale-While-Revalidate) Pattern ✅

**Objetivo:** Reducir llamadas a Polymarket API con cache inteligente

**Implementación:**
- ✅ Cache fresco (< 30s): Retorna inmediatamente desde Redis
- ✅ Cache stale (30-60s): Retorna stale value + revalida en background con `asyncio.create_task`
- ✅ Cache expirado (> 60s): Mide sincrónicamente
- ✅ TTLs configurables en `settings.py`

**Archivo:** `backend/app/core/latency_monitor.py` (método `get_latency_metrics`)

#### 1.3 Lock Distribuido (Anti-Thundering Herd) ✅

**Objetivo:** Prevenir múltiples requests simultáneos a Polymarket API

**Implementación:**
- ✅ Lock distribuido en Redis usando `set_nx` (set if not exists)
- ✅ TTL de 10 segundos para el lock (configurable)
- ✅ Si lock existe, retorna cache o None (no espera)
- ✅ Previene thundering herd cuando cache expira

**Archivo:** `backend/app/core/latency_monitor.py` (método `_acquire_lock`)

#### 1.4 Backoff Exponencial Persistido en Redis ✅

**Objetivo:** Reducir carga cuando hay errores 429/503

**Implementación:**
- ✅ Backoff persistido en Redis con clave `latency:backoff:until`
- ✅ Si hay error 429/503, establece backoff de 10 segundos (configurable)
- ✅ Verifica backoff antes de cada medición
- ✅ Se resetea automáticamente después de una medición exitosa

**Archivo:** `backend/app/core/latency_monitor.py` (métodos `_check_backoff`, `_set_backoff`)

#### 1.5 Configuración en Settings ✅

**Objetivo:** Hacer configurable el comportamiento del latency monitor

**Implementación:**
```python
# Redis (Upstash) - Opcional, para cache distribuido
upstash_redis_rest_url: Optional[str] = None
upstash_redis_rest_token: Optional[str] = None

# Latency Monitor Configuration
latency_cache_ttl_seconds: int = 30  # TTL del cache fresco (SWR: retorna inmediatamente)
latency_stale_ttl_seconds: int = 60  # TTL del cache stale (SWR: retorna stale + revalida en background)
latency_lock_ttl_seconds: int = 10  # TTL del lock distribuido (anti-thundering herd)
latency_min_interval_seconds: int = 10  # Intervalo mínimo entre requests al mismo endpoint
latency_backoff_max_seconds: int = 60  # Backoff máximo en segundos
latency_collector_interval_seconds: int = 60  # Intervalo para MetricsCollector

# Latency Thresholds (ms)
latency_backend_green_threshold: int = 100
latency_backend_yellow_threshold: int = 200
latency_polymarket_data_green_threshold: int = 150
latency_polymarket_data_yellow_threshold: int = 300
latency_polymarket_trading_green_threshold: int = 150
latency_polymarket_trading_yellow_threshold: int = 300
latency_execution_green_threshold: int = 250
latency_execution_yellow_threshold: int = 500
```

**Archivo:** `backend/app/settings.py`

**Implementación:**
```python
CACHE_TTL_SECONDS = 30  # Aumentado de 5 a 30 segundos
MIN_INTERVAL_BETWEEN_REQUESTS = 10  # Segundos mínimos entre requests al mismo endpoint

# Agregar tracking de última llamada por endpoint
self._last_data_api_call: Optional[float] = None
self._last_trading_api_call: Optional[float] = None
self._is_measuring_data: bool = False
self._is_measuring_trading: bool = False
self._consecutive_errors_data: int = 0
self._consecutive_errors_trading: int = 0
```

#### 1.2 Implementar Backoff Exponencial

**Objetivo:** Reducir carga cuando hay errores

**Cambios:**
- Si hay error (429, 503, timeout), aumentar el intervalo antes del siguiente intento
- Backoff exponencial: 10s → 20s → 40s → 60s (max)
- Resetear backoff después de 3 llamadas exitosas consecutivas

**Implementación:**
```python
async def _measure_polymarket_data_latency(self) -> Optional[float]:
    now = time.time()
    
    # Rate limiting: no llamar si fue hace menos de MIN_INTERVAL segundos
    if self._last_data_api_call:
        elapsed = now - self._last_data_api_call
        min_interval = self._calculate_backoff_interval(self._consecutive_errors_data)
        if elapsed < min_interval:
            # Retornar valor cacheado si existe
            if self._cached_results and self._cached_results.get("polymarket_data_latency_ms"):
                return self._cached_results["polymarket_data_latency_ms"]
            return None
    
    # Evitar llamadas concurrentes
    if self._is_measuring_data:
        return None
    
    try:
        self._is_measuring_data = True
        self._last_data_api_call = now
        # ... resto del código ...
        self._consecutive_errors_data = 0  # Resetear en éxito
        return latency_ms
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (429, 503):
            self._consecutive_errors_data += 1
            logger.warning(f"Rate limited by Polymarket Data API, backing off...")
        return None
    finally:
        self._is_measuring_data = False
```

#### 1.6 Optimizar MetricsCollector ✅

**Objetivo:** Reducir frecuencia de mediciones desde el collector

**Implementación:**
- ✅ Solo llama a `get_latency_metrics` cada 60 segundos (configurable)
- ✅ Usa `force_refresh=False` siempre desde el collector
- ✅ Tracking con `_last_latency_collection` para evitar llamadas innecesarias

**Archivo:** `backend/app/core/metrics/collector.py` (método `collect_runtime_metrics`)

---

### Fase 2: Mejorar UX de Spinners (Frontend) ✅ COMPLETADO

#### 2.1 Hook useDataLoader con AbortController ✅

**Objetivo:** Manejo robusto de estados de carga con prevención de race conditions

**Implementación:**
- ✅ Hook `useDataLoader` con estados separados:
  - `isInitialLoading`: Solo true en primer fetch
  - `isRefreshing`: True en actualizaciones automáticas
  - `errorCount`: Solo muestra alertas después de 3 errores consecutivos
- ✅ `AbortController` para cancelar requests en curso y prevenir race conditions
- ✅ Mantiene datos anteriores si un refresh falla (no limpia UI)
- ✅ Refresh periódico configurable con `refreshInterval`
- ✅ Callbacks opcionales: `onError`, `onSuccess`

**Archivo:** `frontend/hooks/useDataLoader.ts`

**Características implementadas:**
- ✅ AbortController para cancelar requests anteriores
- ✅ Cleanup automático al desmontar componente
- ✅ Manejo de errores con contador (solo alerta después de 3 fallos)
- ✅ Mantiene datos anteriores en errores de refresh
- ✅ Soporte para `enabled` flag para deshabilitar temporalmente

#### 2.2 Componentes Skeleton para Carga Inicial ✅

**Objetivo:** Placeholders visuales en lugar de spinners bloqueantes

**Implementación:**
- ✅ `Skeleton`: Componente base con variantes (text, circular, rectangular)
- ✅ `CardSkeleton`: Para tarjetas completas
- ✅ `TableSkeleton`: Para tablas con filas y columnas configurables
- ✅ `ListSkeleton`: Para listas de items con avatares

**Archivo:** `frontend/components/ui/Skeleton.tsx`

#### 2.3 Componente RefreshingIndicator ✅

**Objetivo:** Indicador visual sutil para actualizaciones

**Implementación:**
- ✅ Spinner pequeño (12px por defecto) con texto opcional
- ✅ Tamaños configurables (sm, md, lg)
- ✅ Solo visible cuando `isRefreshing` es true
- ✅ No bloquea la UI

**Archivo:** `frontend/components/ui/RefreshingIndicator.tsx`

#### 2.4 Páginas Actualizadas ✅

**Páginas refactorizadas:**

1. ✅ **`app/values/live/page.tsx`**
   - Reemplazado `useEffect` manual con `useDataLoader`
   - Reemplazado `LoadingSpinner fullScreen` con `ListSkeleton`
   - Agregado `RefreshingIndicator` en header
   - Mantiene datos anteriores si hay error en refresh

2. ✅ **`app/dashboard/operations/page.tsx`**
   - Reemplazado `useEffect` manual con `useDataLoader`
   - Reemplazado `LoadingSpinner fullScreen` con `CardSkeleton` y `TableSkeleton`
   - Agregado `RefreshingIndicator` en header
   - Refresh cada 5 segundos

3. ✅ **`app/strategies/[id]/live/page.tsx`**
   - Reemplazado `useEffect` manual con `useDataLoader`
   - Reemplazado `LoadingSpinner fullScreen` con `ListSkeleton`
   - Agregado `RefreshingIndicator` en header (2 ubicaciones: surebet y default)
   - Refresh cada 10 segundos
   - Integrado con `useRealtimeStrategy` para datos en tiempo real

4. ⚠️ **`app/markets/page.tsx`**
   - Ya tiene lógica parcial para evitar spinners
   - **PENDIENTE**: Mejorar para usar `useDataLoader` y componentes Skeleton

#### 2.5 Manejo de Errores Mejorado ✅

**Objetivo:** Mostrar errores sin bloquear la UI

**Implementación:**
- ✅ Si hay error durante refresh, mantiene datos anteriores visibles
- ✅ No muestra spinner en errores de refresh, solo en carga inicial
- ✅ `errorCount` en hook: solo muestra alertas después de 3 errores consecutivos
- ✅ Callback `onError` opcional para manejo personalizado

---

## Orden de Implementación

### Sprint 1: Backend - Latency Monitor ✅ COMPLETADO
1. ✅ Cliente Redis para cache distribuido (`redis_client.py`)
2. ✅ SWR (Stale-While-Revalidate) pattern implementado
3. ✅ Lock distribuido con `set_nx` para prevenir thundering herd
4. ✅ Backoff exponencial persistido en Redis
5. ✅ Configuración completa en `settings.py` (TTLs, thresholds, intervals)
6. ✅ Optimización de MetricsCollector (llama cada 60s)
7. ⚠️ Tests unitarios para Redis y SWR (PENDIENTE)

### Sprint 2: Frontend - UX de Spinners ✅ COMPLETADO
1. ✅ Hook `useDataLoader` con AbortController
2. ✅ Componente `RefreshingIndicator`
3. ✅ Componentes Skeleton (Skeleton, CardSkeleton, TableSkeleton, ListSkeleton)
4. ✅ Actualizado `app/values/live/page.tsx`
5. ✅ Actualizado `app/dashboard/operations/page.tsx`
6. ✅ Actualizado `app/strategies/[id]/live/page.tsx`
7. ⚠️ Mejorar `app/markets/page.tsx` (PENDIENTE - tiene lógica parcial)
8. ⚠️ Tests de componentes (PENDIENTE)

---

## Métricas de Éxito

### Backend ✅ IMPLEMENTADO
- ✅ **Cache distribuido con Redis**: Compartido entre múltiples instancias del backend
- ✅ **SWR Pattern**: Cache fresco retorna inmediatamente, stale se revalida en background
- ✅ **Lock distribuido**: Previene thundering herd cuando múltiples requests llegan simultáneamente
- ✅ **Backoff automático**: Se activa en errores 429/503 y se persiste en Redis
- ✅ **Configuración flexible**: Todos los TTLs y thresholds son configurables
- ⚠️ **Monitoreo**: Falta agregar métricas de tracking (ver sección "Pendientes")

### Frontend ✅ IMPLEMENTADO
- ✅ **Spinner solo en carga inicial**: Reemplazado con Skeletons
- ✅ **Actualizaciones silenciosas**: `RefreshingIndicator` sutil, no bloquea UI
- ✅ **Interacción durante updates**: Usuarios pueden interactuar mientras se actualiza
- ✅ **Feedback visual claro**: `RefreshingIndicator` muestra estado de actualización
- ✅ **Manejo de errores robusto**: Mantiene datos anteriores, solo alerta después de 3 errores
- ✅ **Prevención de race conditions**: AbortController cancela requests anteriores

---

## Consideraciones Adicionales

### Rate Limits de Polymarket
- **Data API**: No documentado oficialmente, pero estimado ~100 req/min
- **Trading API (CLOB)**: Similar, pero más estricto durante alta volatilidad
- **Solución**: Con cache de 30s y rate limiting de 10s, máximo 6 req/min por endpoint = 12 req/min total (dentro de límites)

### Monitoreo ⚠️ PENDIENTE
- ⚠️ Agregar métrica `latency_api_calls_per_minute` para tracking
- ⚠️ Alertar si se exceden 20 llamadas/minuto
- ✅ Loggear cuando se activa backoff (ya implementado con `logger.warning`)
- ⚠️ Tracking de requests concurrentes (ver sección "Mejoras Propuestas")

### Rollback Plan
- Si hay problemas, reducir `CACHE_TTL_SECONDS` a 15 segundos
- Deshabilitar backoff si causa problemas
- Mantener código anterior comentado para rollback rápido

---

## Sincronización de Estados: Múltiples Pestañas

### Arquitectura Actual (Singleton Global)

**Estado Actual:**
- ✅ El `LatencyMonitor` ya es un **Singleton global** compartido por toda la aplicación
- ✅ Se crea una única instancia: `latency_monitor = LatencyMonitor()` (línea 253 de `latency_monitor.py`)
- ✅ Todos los módulos importan la misma instancia: `from app.core.latency_monitor import latency_monitor`
- ✅ El cache (`_cached_results`, `_cache_timestamp`) es **compartido globalmente** entre todas las requests

**Cómo Funciona:**
```python
# backend/app/core/latency_monitor.py
# Instancia única global - compartida por todas las pestañas/sesiones
latency_monitor = LatencyMonitor()

# backend/app/api/metrics.py
@router.get("/latency")
async def get_latency_metrics(...):
    # Todas las requests (de cualquier pestaña) usan la misma instancia
    metrics = await latency_monitor.get_latency_metrics(force_refresh=force_refresh)
    return metrics
```

### Protección Contra Llamadas Concurrentes

**Mecanismo de Lock:**
- ✅ `asyncio.Lock()` previene llamadas concurrentes dentro del mismo proceso
- ✅ Si múltiples pestañas llaman simultáneamente, solo una ejecuta la medición
- ✅ Las demás esperan y reciben el resultado cacheado

**Flujo con Múltiples Pestañas:**
```
Pestaña 1: GET /metrics/latency → Lock adquirido → Mide latencia → Cache actualizado → Retorna
Pestaña 2: GET /metrics/latency → Espera lock → Lock adquirido → Cache válido → Retorna cache
Pestaña 3: GET /metrics/latency → Espera lock → Lock adquirido → Cache válido → Retorna cache
```

**Código Actual:**
```python
async def get_latency_metrics(self, force_refresh: bool = False) -> Dict:
    async with self._lock:  # ← Protección contra concurrencia
        now = time.time()
        
        # Check cache (compartido por todas las pestañas)
        if not force_refresh and self._cached_results and self._cache_timestamp:
            age = now - self._cache_timestamp
            if age < self.CACHE_TTL_SECONDS:
                return self._cached_results  # ← Todas las pestañas reciben el mismo cache
        
        # Solo una request ejecuta esto (las demás esperan)
        # ... medir latencias ...
        
        # Cache actualizado (visible para todas las pestañas)
        self._cached_results = result
        self._cache_timestamp = now
        
        return result
```

### Mejoras Propuestas para Mayor Eficiencia

#### 1. Verificación de Cache Antes del Lock (Optimización)

**Problema Actual:**
- Todas las requests esperan el lock, incluso si el cache es válido
- Esto causa latencia innecesaria cuando múltiples pestañas llaman simultáneamente

**Solución:**
```python
async def get_latency_metrics(self, force_refresh: bool = False) -> Dict:
    # Verificación rápida de cache SIN lock (read-only)
    if not force_refresh and self._cached_results and self._cache_timestamp:
        now = time.time()
        age = now - self._cache_timestamp
        if age < self.CACHE_TTL_SECONDS:
            # Cache válido - retornar inmediatamente sin lock
            return self._cached_results
    
    # Solo adquirir lock si necesitamos actualizar
    async with self._lock:
        # Double-check: otra request pudo haber actualizado mientras esperábamos
        now = time.time()
        if not force_refresh and self._cached_results and self._cache_timestamp:
            age = now - self._cache_timestamp
            if age < self.CACHE_TTL_SECONDS:
                return self._cached_results
        
        # Medir latencias (solo si realmente es necesario)
        # ...
```

**Beneficio:**
- ✅ Múltiples pestañas pueden leer el cache simultáneamente (sin lock)
- ✅ Solo una request adquiere el lock para actualizar
- ✅ Reduce latencia cuando hay muchas pestañas abiertas

#### 2. Tracking de Requests Concurrentes

**Objetivo:** Monitorear cuántas pestañas están llamando simultáneamente

**Implementación:**
```python
self._concurrent_requests: int = 0
self._max_concurrent_requests: int = 0

async def get_latency_metrics(self, force_refresh: bool = False) -> Dict:
    # Verificación rápida de cache (sin lock)
    if not force_refresh and self._cached_results and self._cache_timestamp:
        now = time.time()
        age = now - self._cache_timestamp
        if age < self.CACHE_TTL_SECONDS:
            return self._cached_results
    
    async with self._lock:
        self._concurrent_requests += 1
        self._max_concurrent_requests = max(
            self._max_concurrent_requests, 
            self._concurrent_requests
        )
        
        try:
            # ... medir latencias ...
        finally:
            self._concurrent_requests -= 1
```

**Uso:**
- Métrica `latency_concurrent_requests_max` para monitoreo
- Alertar si hay > 10 requests simultáneas (posible problema de frontend)

#### 3. Documentación en Código

**Agregar docstring explicando el Singleton:**
```python
class LatencyMonitor:
    """
    Monitors latency to backend and Polymarket APIs.
    
    **Singleton Global:**
    - Esta clase es instanciada una sola vez globalmente
    - Todas las requests HTTP (de cualquier pestaña/sesión) comparten la misma instancia
    - El cache es compartido: si una pestaña actualiza el cache, todas las demás lo ven
    - El lock previene mediciones concurrentes a Polymarket API
    
    **Sincronización:**
    - `asyncio.Lock()` garantiza que solo una request mide latencia a la vez
    - Múltiples pestañas pueden leer el cache simultáneamente (read-only)
    - Si el cache expiró, solo la primera request mide, las demás esperan y reciben el resultado
    
    **Eficiencia:**
    - Cache TTL: 30 segundos (configurable)
    - Rate limiting: máximo 1 request por endpoint cada 10 segundos
    - Backoff exponencial en errores 429/503
    """
```

### Garantías de Sincronización

**✅ Garantizado:**
1. **Cache Global Compartido:** Todas las pestañas ven los mismos valores de latencia
2. **Sin Duplicación de Requests:** Solo una request mide latencia a la vez (lock)
3. **Consistencia:** Si una pestaña actualiza el cache, todas las demás lo ven inmediatamente
4. **Eficiencia:** Múltiples pestañas no causan múltiples llamadas a Polymarket API

**⚠️ Consideraciones:**
- Si una pestaña llama con `force_refresh=True`, fuerza una actualización para todas
- El lock puede causar pequeña latencia si muchas pestañas llaman simultáneamente (mitigado con verificación de cache antes del lock)

### Tests de Sincronización

**Test a Implementar:**
```python
@pytest.mark.asyncio
async def test_multiple_concurrent_requests_share_cache():
    """Test que múltiples requests concurrentes comparten el cache."""
    monitor = LatencyMonitor()
    
    # Simular 5 requests simultáneas
    tasks = [
        monitor.get_latency_metrics(force_refresh=False)
        for _ in range(5)
    ]
    results = await asyncio.gather(*tasks)
    
    # Todas deben retornar el mismo resultado (mismo timestamp)
    timestamps = [r["timestamp"] for r in results]
    assert len(set(timestamps)) == 1, "Todas las requests deben compartir el mismo cache"
    
    # Solo debe haber 1 medición real (las demás usan cache)
    # Verificar que solo se llamó a _measure_polymarket_data_latency una vez
```

---

## Resumen: Sincronización de Estados

| Aspecto | Estado Actual | Mejora Propuesta |
|---------|---------------|------------------|
| **Singleton Global** | ✅ Ya implementado | ✅ Mantener |
| **Cache Compartido** | ✅ Ya implementado | ✅ Mantener |
| **Lock para Concurrencia** | ✅ Ya implementado | ✅ Optimizar (verificación antes del lock) |
| **Rate Limiting** | ❌ No implementado | ✅ Agregar |
| **Backoff Exponencial** | ❌ No implementado | ✅ Agregar |
| **Tracking de Concurrencia** | ❌ No implementado | ✅ Agregar para monitoreo |

**Conclusión:** La arquitectura actual ya garantiza que múltiples pestañas comparten el cache. Las mejoras propuestas optimizan la eficiencia y agregan protecciones adicionales contra saturación de API.

---

## Estado de Implementación

### ✅ COMPLETADO

#### Backend
1. ✅ Cliente Redis (`redis_client.py`) con soporte para Upstash REST API
2. ✅ LatencyMonitor refactorizado con SWR pattern
3. ✅ Lock distribuido usando `set_nx` en Redis
4. ✅ Backoff exponencial persistido en Redis
5. ✅ Configuración completa en `settings.py`
6. ✅ MetricsCollector optimizado (llama cada 60s)

#### Frontend
1. ✅ Hook `useDataLoader` con AbortController y manejo robusto de errores
2. ✅ Componente `RefreshingIndicator` para actualizaciones silenciosas
3. ✅ Componentes Skeleton (Skeleton, CardSkeleton, TableSkeleton, ListSkeleton)
4. ✅ Páginas refactorizadas:
   - ✅ `app/values/live/page.tsx`
   - ✅ `app/dashboard/operations/page.tsx`
   - ✅ `app/strategies/[id]/live/page.tsx`

### ⚠️ PENDIENTE

#### Backend - Crítico
1. ⚠️ **Migrar Redis a TCP** (Prioridad Alta):
   - Cambiar de REST API a protocolo nativo Redis
   - Actualizar `redis_client.py` para usar `redis.asyncio`
   - Cambiar variable de entorno a `REDIS_URL`
   - Agregar timeouts estrictos (200ms) y fallback automático

2. ⚠️ **Mitigar Dangling Tasks** (Prioridad Alta):
   - Agregar timeout en `_revalidate_in_background`
   - Tracking de tareas activas para monitoreo
   - Cleanup automático de tareas huérfanas

3. ⚠️ **Mejorar Fallback de Redis** (Prioridad Alta):
   - Timeout muy bajo (200ms) en conexiones Redis
   - Fallback automático a memoria si Redis falla
   - No bloquear hilo principal

#### Backend - Importante
4. ⚠️ Tests unitarios para:
   - Redis client (get, set, set_nx, exists, ttl)
   - SWR pattern (fresh, stale, expired cache)
   - Lock distribuido (thundering herd prevention)
   - Backoff exponencial
   - Fallback graceful

5. ⚠️ Métricas de monitoreo:
   - `latency_api_calls_per_minute`
   - `latency_concurrent_requests_max`
   - `latency_cache_age_seconds` (edad del cache)
   - Alertas si se exceden límites

#### Frontend - Importante
6. ⚠️ **Prevenir Layout Shift** (Prioridad Media):
   - Asegurar que TableSkeleton tenga alturas fijas
   - Medir CLS y ajustar dimensiones
   - Coincidir dimensiones de Skeletons con renderizado final

7. ⚠️ **Mostrar Edad del Dato** (Prioridad Media):
   - Agregar `cache_age_seconds` en respuesta del backend
   - Mostrar visualmente la edad del dato en frontend
   - Validar que umbral de 60s sea aceptable

8. ⚠️ Actualizar `app/markets/page.tsx` para usar `useDataLoader` y Skeletons

9. ⚠️ Tests de componentes:
   - `useDataLoader` hook
   - `RefreshingIndicator` component
   - Skeleton components

### 🔄 MEJORAS FUTURAS (Opcional)

1. **Tracking de Requests Concurrentes**: Agregar contador de requests simultáneas para monitoreo
2. **Optimización de Lock**: Verificación de cache antes del lock (ya implementado en SWR)
3. **Métricas de Performance**: Tracking de latencia de Redis, hit rate del cache, etc.

---

## Próximos Pasos Recomendados

### Fase 3: Mitigación de Riesgos (Prioridad Crítica)

1. **Migración Redis a TCP** (Sprint 3.1):
   - ⚠️ Instalar `redis` o `aioredis` en `requirements.txt`
   - ⚠️ Refactorizar `redis_client.py` para usar TCP
   - ⚠️ Actualizar `settings.py` (cambiar a `REDIS_URL`)
   - ⚠️ Agregar timeouts estrictos (200ms) y fallback automático
   - ⚠️ Tests de conexión y fallback

2. **Mitigar Dangling Tasks** (Sprint 3.2):
   - ⚠️ Agregar timeout en `_revalidate_in_background` (5s)
   - ⚠️ Tracking de tareas activas
   - ⚠️ Cleanup automático de tareas huérfanas
   - ⚠️ Tests de cleanup

3. **Mejorar Fallback de Redis** (Sprint 3.3):
   - ⚠️ Timeout muy bajo (200ms) en todas las operaciones Redis
   - ⚠️ Fallback automático a memoria si Redis falla
   - ⚠️ No bloquear hilo principal
   - ⚠️ Tests de fallback

### Fase 4: Mejoras de UX (Prioridad Media)

4. **Prevenir Layout Shift** (Sprint 4.1):
   - ⚠️ Ajustar TableSkeleton con alturas fijas
   - ⚠️ Medir CLS y validar mejoras
   - ⚠️ Ajustar otros Skeletons si es necesario

5. **Mostrar Edad del Dato** (Sprint 4.2):
   - ⚠️ Agregar `cache_age_seconds` en respuesta del backend
   - ⚠️ Mostrar badge/indicador de edad en frontend
   - ⚠️ Validar umbral de 60s con stakeholders

6. **Completar Refactorización** (Sprint 4.3):
   - ⚠️ Actualizar `app/markets/page.tsx`

### Fase 5: Testing y Monitoreo (Prioridad Media)

7. **Tests Unitarios** (Sprint 5.1):
   - ⚠️ Redis client (get, set, set_nx, exists, ttl, fallback)
   - ⚠️ SWR pattern (fresh, stale, expired cache)
   - ⚠️ Lock distribuido (thundering herd prevention)
   - ⚠️ Backoff exponencial

8. **Tests Frontend** (Sprint 5.2):
   - ⚠️ `useDataLoader` hook
   - ⚠️ `RefreshingIndicator` component
   - ⚠️ Skeleton components

9. **Métricas de Monitoreo** (Sprint 5.3):
   - ⚠️ `latency_api_calls_per_minute`
   - ⚠️ `latency_concurrent_requests_max`
   - ⚠️ `latency_cache_age_seconds`
   - ⚠️ Alertas si se exceden límites

---

## Análisis de Riesgos y Puntos Ciegos

### 1. Riesgo de "Dangling Tasks" (Backend) ⚠️

**Problema:**
Al usar `asyncio.create_task` para la revalidación en background (SWR), existe el riesgo de que las tareas queden "huérfanas" o se acumulen si:
- La API de Polymarket responde muy lento
- El loop de eventos está saturado
- La tarea falla silenciosamente

**Impacto:**
- Acumulación de tareas en memoria
- Consumo excesivo de descriptores de archivos
- Posible degradación de performance

**Mitigación Implementada:**
- ✅ Timeout estricto en mediciones (3.0 segundos)
- ✅ Lock distribuido con TTL (se libera automáticamente)
- ⚠️ **PENDIENTE**: Agregar timeout explícito en `_revalidate_in_background`
- ⚠️ **PENDIENTE**: Tracking de tareas activas para monitoreo

**Código a Mejorar:**
```python
async def _revalidate_in_background(self):
    """Revalidate cache in background (SWR pattern)."""
    try:
        # Agregar timeout total para la revalidación
        result = await asyncio.wait_for(
            self._measure_latencies(),
            timeout=5.0  # Timeout total de 5 segundos
        )
        # ... resto del código ...
    except asyncio.TimeoutError:
        logger.warning("Background revalidation timed out")
    except Exception as e:
        logger.warning(f"Error revalidating cache in background: {e}")
```

### 2. Precisión de la Métrica vs. Frescura ⚠️

**Problema:**
Los datos pueden tener hasta 60 segundos de antigüedad (`latency_stale_ttl_seconds`). En un entorno de trading o arbitraje, una latencia de 150ms medida hace 59 segundos podría no reflejar un pico de congestión actual.

**Impacto:**
- Decisiones de trading basadas en datos obsoletos
- Posible pérdida de oportunidades o ejecución en condiciones subóptimas

**Mitigación Implementada:**
- ✅ Cache fresco (< 30s) para decisiones críticas
- ✅ Cache stale (30-60s) solo para visualización
- ⚠️ **PENDIENTE**: Mostrar "edad" del dato en frontend
- ⚠️ **PENDIENTE**: Validar que umbral de 60s sea aceptable para decisiones operativas

**Mejora Propuesta:**
```typescript
// Frontend: Mostrar edad del dato
interface LatencyMetrics {
  timestamp: string;
  age_seconds?: number;  // Calculado en frontend
  // ...
}

// Backend: Incluir timestamp en respuesta
{
  "timestamp": "2024-01-01T12:00:00Z",
  "cache_age_seconds": 25,  // Edad del cache
  // ...
}
```

### 3. Fallback Graceful de Redis ⚠️

**Problema:**
Si Redis está configurado pero falla (timeout/caída), el cliente podría bloquear el hilo principal esperando una conexión que no llega, ralentizando toda la API.

**Impacto:**
- Degradación de performance si Redis está caído
- Posible timeout de requests HTTP
- Mala experiencia de usuario

**Mitigación Implementada:**
- ✅ Fallback a memoria local si Redis no está configurado
- ⚠️ **PENDIENTE**: Timeout muy bajo en conexiones Redis (200ms)
- ⚠️ **PENDIENTE**: Fallback automático a memoria si Redis falla

**Código a Mejorar:**
```python
async def get(self, key: str) -> Optional[str]:
    """Get value from Redis with fast timeout and fallback."""
    if not self._enabled:
        return None
    
    try:
        client = await self._get_client()
        # Timeout muy bajo para no bloquear
        response = await asyncio.wait_for(
            client.get(url, timeout=0.2),  # 200ms max
            timeout=0.2
        )
        response.raise_for_status()
        return response.json().get("result")
    except (asyncio.TimeoutError, httpx.TimeoutException):
        logger.debug(f"Redis timeout for key '{key}', using fallback")
        return None  # Fallback a memoria local
    except Exception as e:
        logger.warning(f"Redis error for key '{key}': {e}, using fallback")
        return None  # Fallback a memoria local
```

### 4. Layout Shift (Frontend) ⚠️

**Problema:**
Los Skeletons mejoran la UX, pero si no tienen las dimensiones exactas de los datos finales, la página "saltará" cuando los datos carguen, afectando métricas de Cumulative Layout Shift (CLS).

**Impacto:**
- Malas métricas de CLS (Core Web Vitals)
- Experiencia de usuario degradada
- Posible penalización SEO

**Mitigación Implementada:**
- ✅ Skeletons con dimensiones configurables
- ⚠️ **PENDIENTE**: Asegurar que TableSkeleton tenga alturas de fila fijas
- ⚠️ **PENDIENTE**: Medir CLS y ajustar dimensiones

**Mejora Propuesta:**
```typescript
// TableSkeleton con alturas fijas que coincidan con el renderizado final
export function TableSkeleton({ rows = 5, columns = 3 }: { rows?: number; columns?: number }) {
  return (
    <div className="space-y-3">
      {/* Header - altura fija */}
      <div className="flex gap-4 h-10"> {/* h-10 = 40px fijo */}
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={`header-${i}`} variant="text" width="100%" height={40} />
        ))}
      </div>
      {/* Rows - altura fija por fila */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div key={`row-${rowIdx}`} className="flex gap-4 h-12"> {/* h-12 = 48px fijo */}
          {Array.from({ length: columns }).map((_, colIdx) => (
            <Skeleton key={`cell-${rowIdx}-${colIdx}`} variant="text" width="100%" height={48} />
          ))}
        </div>
      ))}
    </div>
  );
}
```

### 5. Límites de Upstash REST API → Migración a TCP ⚠️

**Problema Original:**
Al usar la API REST de Upstash, cada llamada es un request HTTP, lo que añade latencia adicional y puede agotar conexiones si no se usa un pool de clientes HTTP.

**Solución: Migración a Redis TCP**
- Cambiar de REST API a protocolo nativo Redis (RESP)
- Usar librería `redis` o `aioredis` para conexión TCP
- Variable de entorno: `REDIS_URL` (en lugar de `UPSTASH_REDIS_REST_URL` y `UPSTASH_REDIS_REST_TOKEN`)

**Impacto de la Migración:**
- ✅ Latencia reducida (TCP directo vs HTTP)
- ✅ Mejor rendimiento (protocolo binario RESP)
- ✅ Pool de conexiones nativo
- ⚠️ Requiere actualizar cliente Redis

**Mitigación a Implementar:**
- ⚠️ **PENDIENTE**: Migrar `redis_client.py` para usar `redis` o `aioredis`
- ⚠️ **PENDIENTE**: Actualizar `settings.py` para usar `REDIS_URL`
- ⚠️ **PENDIENTE**: Mantener fallback a memoria si Redis falla
- ⚠️ **PENDIENTE**: Monitorear consumo de créditos en Upstash

**Código Propuesto:**
```python
# backend/app/core/redis_client.py (nueva versión con TCP)
import redis.asyncio as redis
from app.settings import settings

class RedisClient:
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._enabled: bool = False
        
        if settings.redis_url:
            self._enabled = True
            self._redis_url = settings.redis_url
            logger.info("Redis client enabled (TCP)")
        else:
            logger.warning("Redis not configured - using in-memory cache only")
    
    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client with connection pool."""
        if self._client is None:
            self._client = await redis.from_url(
                self._redis_url,
                socket_connect_timeout=0.2,  # 200ms timeout
                socket_timeout=0.5,
                retry_on_timeout=True,
                health_check_interval=30
            )
        return self._client
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis with timeout."""
        if not self._enabled:
            return None
        
        try:
            client = await self._get_client()
            return await asyncio.wait_for(
                client.get(key),
                timeout=0.2  # 200ms max
            )
        except (asyncio.TimeoutError, redis.TimeoutError):
            logger.debug(f"Redis timeout for key '{key}', using fallback")
            return None
        except Exception as e:
            logger.warning(f"Redis error for key '{key}': {e}, using fallback")
            return None
```

---

## Notas de Implementación

### Redis (Upstash) - Migración a TCP ⚠️

**Estado Actual:**
- ✅ Implementado con REST API (Upstash REST)
- ⚠️ **PENDIENTE**: Migrar a TCP para mejor rendimiento

**Configuración Actual:**
- Variables de entorno: `UPSTASH_REDIS_REST_URL` y `UPSTASH_REDIS_REST_TOKEN`
- Cliente: `httpx.AsyncClient` para llamadas REST

**Configuración Futura (TCP):**
- Variable de entorno: `REDIS_URL` (ej: `redis://default:password@host:port`)
- Cliente: `redis.asyncio` o `aioredis` para conexión TCP nativa
- Pool de conexiones automático
- Mejor rendimiento y latencia reducida

**Fallback:**
- Si Redis no está configurado: usa cache en memoria local
- Si Redis falla (timeout/error): fallback automático a memoria local

**Claves Redis:**
- `latency:metrics`: Cache de métricas de latencia
- `latency:lock:data`: Lock para Data API
- `latency:lock:trading`: Lock para Trading API
- `latency:backoff:until`: Timestamp de fin de backoff

### SWR Pattern
- **Fresh cache** (< 30s): Retorna inmediatamente desde Redis
- **Stale cache** (30-60s): Retorna stale + `asyncio.create_task` para revalidar en background
- **Expired cache** (> 60s): Mide sincrónicamente y actualiza cache

### Frontend
- **AbortController**: Previene race conditions cancelando requests anteriores
- **Error handling**: Solo muestra alertas después de 3 errores consecutivos
- **Data persistence**: Mantiene datos anteriores si hay error en refresh

