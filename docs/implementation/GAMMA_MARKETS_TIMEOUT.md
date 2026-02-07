# Error "Gamma markets temporarily unavailable: gamma timeout"

## Qué significa

El backend obtiene la lista de **markets** (plantillas de mercados) desde la **API externa de Polymarket (Gamma)**: `https://gamma-api.polymarket.com`.  
Cuando esa API no responde dentro del tiempo configurado, el backend devuelve **503** con el mensaje:

```text
Gamma markets temporarily unavailable: gamma timeout
```

El frontend suele mostrarlo como **"Error al cargar markets"**.

## Causas habituales

1. **Gamma API lenta o caída** – Servicio externo de Polymarket sobrecargado o no disponible.
2. **Red o firewall** – El servidor donde corre el backend no puede alcanzar `gamma-api.polymarket.com` o la conexión se corta.
3. **Timeouts muy bajos** – Por defecto el backend usa 1s connect, 4s read, 5s total; si Gamma tarda más, se produce el timeout.

## Qué hace el backend

- **GET /markets** hace una o varias peticiones a `{POLYMARKET_GAMMA_API_URL}/markets`.
- Timeouts por defecto (configurables vía env):
  - `GAMMA_CONNECT_TIMEOUT` = 1 s (conexión TCP).
  - `GAMMA_READ_TIMEOUT` = 4 s (lectura del cuerpo).
  - `GAMMA_OVERALL_TIMEOUT` = 5 s (máximo total por request).
- Si se supera cualquiera de ellos → `httpx.TimeoutException` → se registra fallo en el **circuit breaker** y se responde **503** con el mensaje anterior.
- Si el circuit breaker está **abierto** (varios fallos seguidos), se responde 503 sin llamar a Gamma hasta que pase el periodo de recuperación (p. ej. 60 s).

## Qué hacer cuando levantes el backend

1. **Comprobar conectividad a Gamma** (desde la máquina del backend):
   ```bash
   curl -s -o /dev/null -w "%{http_code}" "https://gamma-api.polymarket.com/markets?limit=1"
   ```
   Debería devolver `200`. Si falla o tarda mucho, el problema es red o Gamma.

2. **Si Gamma suele responder lento** (pero al final responde), aumenta los timeouts en `.env`:
   ```env
   GAMMA_CONNECT_TIMEOUT=3
   GAMMA_READ_TIMEOUT=10
   GAMMA_OVERALL_TIMEOUT=15
   ```
   Reinicia el backend después de cambiar `.env`.

3. **Cache** – Si usas Redis (`CACHE_PROVIDER=redis`), las respuestas de Gamma se cachean; tras el primer éxito, las peticiones siguientes pueden servirse desde cache y no depender tanto de Gamma en cada request.

4. **Logs** – En los logs del backend verás líneas como:
   - `Gamma timeout for markets: ...` cuando hay timeout.
   - `Gamma markets circuit breaker OPEN, returning 503` cuando el breaker está abierto.

## Resumen

| Mensaje / Comportamiento | Significado |
|--------------------------|-------------|
| `gamma timeout` | La petición a Gamma superó el tiempo límite (connect/read/overall). |
| `circuit breaker open` | Demasiados fallos seguidos; el backend deja de llamar a Gamma un tiempo. |
| `gamma_429` | Gamma devolvió rate limit (429). |
| `gamma_5xx` | Gamma devolvió error de servidor (5xx). |

El error es **esperable** cuando Gamma está caído o muy lento. Ajustar timeouts y usar cache (Redis) mejora la resiliencia cuando vuelvas a levantar el backend.
