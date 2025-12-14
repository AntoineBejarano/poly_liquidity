# Módulo de Ejecución, Firmas y Trazabilidad

**Versión 1.0 - Especificación Técnica para Implementación**

---

## 1. Propósito del Módulo

El módulo de **Ejecución, Firmas y Trazabilidad** es responsable de:

1. Convertir **OrderIntents** aprobados por el Risk Engine en **órdenes firmadas** válidas para la API de trading de Polymarket
2. Enviar esas órdenes a Polymarket y gestionar su ciclo de vida completo (pendiente, parcial, filled, cancelada, fallida)
3. Garantizar **trazabilidad total** de cada paso:
   - Qué intent generó qué orden
   - Qué firma se utilizó
   - Qué payload exacto se firmó y envió
   - Qué respuesta devolvió Polymarket
   - Cómo evolucionó la orden en el tiempo (histórico completo)

### Importancia Crítica

Este módulo es crítico porque:
- Maneja **claves privadas** (o acceso a ellas)
- Es el punto donde se materializa la exposición real (hasta 200k €+)
- Es la base para cualquier análisis post-mortem si algo sale mal
- Protege el capital mediante validaciones y controles de seguridad

---

## 2. Alcance del Documento

Este documento especifica:

- ✅ Modelo de datos completo para intents, órdenes firmadas y registros de ejecución
- ✅ Flujo detallado de firma EIP-712 (especificación técnica)
- ✅ Recomendaciones de seguridad de claves
- ✅ Modelo de trazabilidad y auditoría
- ✅ Requisitos de logging estructurado y correlación (trace IDs)
- ✅ Manejo de errores y casos excepcionales
- ✅ Estructura de archivos y módulos a implementar

**No incluye:**
- Implementación específica de código Python (se hará después)
- Detalles de la API de Polymarket (se consultará documentación oficial)

---

## 3. Modelo de Datos

### 3.1. OrderIntent

**Origen:** Generado por el **Strategy Engine** y validado por el **Risk Engine**.

**Campos requeridos:**

```python
class OrderIntent:
    intent_id: UUID                    # ID único interno
    trace_id: UUID                     # ID de trazabilidad (generado en Strategy)
    created_at: datetime
    
    # Información del mercado
    polymarket_market_id: str
    market_id: UUID                    # ID interno del mercado
    
    # Parámetros de la orden
    side: str                          # "BUY" o "SELL"
    outcome: str                       # "YES" o "NO"
    price: float                       # Ej: 0.979
    size: float                        # En USDC, ej: 5000.0
    
    # Contexto del evento
    event_status_at_creation: str      # "FINISHED_CONFIRMED", etc.
    espn_event_id: str | None          # Si aplica
    
    # Snapshot de riesgo al momento de creación
    risk_snapshot: dict                # {
                                       #   "exposure_before": float,
                                       #   "exposure_after_expected": float,
                                       #   "global_exposure_before": float,
                                       #   "global_exposure_after_expected": float,
                                       #   "active_markets_before": int,
                                       #   "active_markets_after": int
                                       # }
    
    # Estado de latencia
    latency_bucket: str                # "GREEN", "YELLOW", "RED"
    
    # Estado del intent
    status: str                        # "PENDING_EXECUTION", "EXECUTED", 
                                       # "REJECTED_BY_EXECUTION", "CANCELLED"
```

**Estados del Intent:**
- `PENDING_EXECUTION`: Creado pero aún no procesado por Execution Engine
- `EXECUTED`: Orden firmada y enviada exitosamente
- `REJECTED_BY_EXECUTION`: Rechazado por error en firma o envío
- `CANCELLED`: Cancelado antes de ejecución (ej: sistema pausado)

---

### 3.2. SignedOrder

**Representa:** La orden **ya firmada** y lista para enviar a Polymarket.

**Campos requeridos:**

```python
class SignedOrder:
    signed_order_id: UUID              # ID único interno
    intent_id: UUID                    # FK a OrderIntent
    trace_id: UUID                     # Heredado del intent
    
    # Información de la wallet
    wallet_address: str                # Dirección de la wallet usada
    chain_id: int                      # Chain ID (ej: 137 para Polygon)
    
    # Información EIP-712
    domain_separator: str              # Hash del domain EIP-712
    domain_json: dict                  # Domain completo (para auditoría)
    message_struct: dict              # Estructura EIP-712 antes de firmar
    message_hash: str                  # Hash del mensaje firmado
    signature: str                     # Firma hex (0x...)
    
    # Metadatos
    created_at: datetime
    expires_at: datetime | None        # Si la orden tiene expiración
    
    # Estado
    status: str                        # "READY_TO_SEND", "SENT", "SEND_FAILED"
```

**Estados del SignedOrder:**
- `READY_TO_SEND`: Firmada pero aún no enviada
- `SENT`: Enviada a Polymarket (esperando respuesta)
- `SEND_FAILED`: Error al enviar (se crea ExecutionRecord con error)

---

### 3.3. ExecutionRecord

**Representa:** La relación entre una `SignedOrder` y la respuesta de Polymarket.

**Campos requeridos:**

```python
class ExecutionRecord:
    execution_id: UUID                 # ID único interno
    signed_order_id: UUID              # FK a SignedOrder
    trace_id: UUID                     # Heredado
    
    # Respuesta de Polymarket
    polymarket_order_id: str | None    # ID que devuelve Polymarket (si existe)
    
    # Payloads completos (para auditoría)
    request_payload: dict              # JSON completo enviado a Polymarket
    request_payload_hash: str          # Hash para logs (SHA256)
    response_payload: dict | None      # JSON completo de respuesta
    response_payload_hash: str | None  # Hash para logs
    
    # Metadatos HTTP
    http_status_code: int | None
    http_method: str                   # "POST", "PUT", etc.
    endpoint_url: str                  # URL completa del endpoint
    
    # Métricas
    created_at: datetime
    latency_ms: float                  # Tiempo request → response
    
    # Estado
    status: str                        # "ACCEPTED", "REJECTED", "ERROR", "TIMEOUT"
    error_message: str | None
    error_code: str | None             # Código de error de Polymarket (si aplica)
    
    # Retry info
    retry_count: int                   # Número de reintentos
    is_retry: bool                     # Si este es un reintento
```

**Estados del ExecutionRecord:**
- `ACCEPTED`: Orden aceptada por Polymarket (200 OK)
- `REJECTED`: Orden rechazada por validación de Polymarket (400, 422, etc.)
- `ERROR`: Error de red, servidor, etc. (500, 502, etc.)
- `TIMEOUT`: Timeout de la petición

---

### 3.4. OrderStateHistory

**Representa:** Histórico de cambios de estado de la orden en Polymarket.

**Campos requeridos:**

```python
class OrderStateHistory:
    order_state_history_id: UUID
    polymarket_order_id: str           # FK a orden en Polymarket
    trace_id: UUID                     # Para correlación
    
    # Timestamp
    snapshot_at: datetime
    
    # Estado crudo de Polymarket
    raw_state: dict                    # Payload completo devuelto por Polymarket
    
    # Estado parseado
    parsed_state: dict                 # {
                                       #   "status": "OPEN" | "PARTIALLY_FILLED" | 
                                       #            "FILLED" | "CANCELLED" | "EXPIRED",
                                       #   "filled_size": float,
                                       #   "remaining_size": float,
                                       #   "avg_fill_price": float | None,
                                       #   "last_fill_price": float | None,
                                       #   "last_fill_time": datetime | None
                                       # }
    
    # Origen de la consulta
    source: str                        # "SCHEDULED_POLL", "MANUAL_QUERY", 
                                       # "FILL_NOTIFICATION", "CANCEL_NOTIFICATION"
```

**Fuentes de actualización:**
- `SCHEDULED_POLL`: Consulta periódica programada
- `MANUAL_QUERY`: Consulta manual (ej: desde API)
- `FILL_NOTIFICATION`: Notificación de fill (si Polymarket soporta webhooks)
- `CANCEL_NOTIFICATION`: Notificación de cancelación

---

## 4. Flujo de Firma EIP-712

### 4.1. Concepto

Polymarket utiliza firmas **EIP-712** (firma estructurada) para garantizar que:
- El usuario (wallet) autoriza la orden sin exponer su clave privada
- El payload firmado es exactamente el que se envía
- La firma es verificable y no repudiable

### 4.2. Estructura EIP-712

Antes de firmar, el backend construye una estructura EIP-712:

```json
{
  "domain": {
    "name": "Polymarket Exchange",
    "version": "1",
    "chainId": 137,
    "verifyingContract": "0x..."
  },
  "message": {
    "marketId": "pm_market_id",
    "outcome": "YES",
    "price": "979000000000000000",  // En wei (18 decimals)
    "size": "5000000000000000000000", // En wei
    "side": "BUY",
    "nonce": "123456789",
    "expiration": "1735689600",
    "clientOrderId": "intent_id-uuid"
  },
  "primaryType": "Order",
  "types": {
    "EIP712Domain": [
      { "name": "name", "type": "string" },
      { "name": "version", "type": "string" },
      { "name": "chainId", "type": "uint256" },
      { "name": "verifyingContract", "type": "address" }
    ],
    "Order": [
      { "name": "marketId", "type": "string" },
      { "name": "outcome", "type": "string" },
      { "name": "price", "type": "uint256" },
      { "name": "size", "type": "uint256" },
      { "name": "side", "type": "string" },
      { "name": "nonce", "type": "uint256" },
      { "name": "expiration", "type": "uint256" },
      { "name": "clientOrderId", "type": "string" }
    ]
  }
}
```

**Nota:** La estructura concreta se ajustará a la documentación oficial de Polymarket. Este es un ejemplo basado en estándares EIP-712.

### 4.3. Pasos del Flujo de Firma

#### Paso 1: Entrada
- `OrderIntent` aprobado por el Risk Engine
- `trace_id` ya asignado (heredado del intent)

#### Paso 2: Construcción del Mensaje EIP-712

1. **Mapear campos del intent → campos del message:**
   - `intent.polymarket_market_id` → `message.marketId`
   - `intent.outcome` → `message.outcome`
   - `intent.price` → `message.price` (convertir a wei: `price * 10^18`)
   - `intent.size` → `message.size` (convertir a wei: `size * 10^18`)
   - `intent.side` → `message.side`

2. **Generar `clientOrderId`:**
   - Basado en: `intent_id` + hash del contenido + timestamp
   - Formato: `{intent_id}-{hash_short}-{timestamp}`

3. **Obtener `nonce`:**
   - Consultar nonce actual de la wallet desde Polymarket API
   - O usar contador interno si Polymarket no requiere nonce

4. **Calcular `expiration`:**
   - `expiration = now() + order_ttl_seconds`
   - Típicamente 1 hora desde creación

#### Paso 3: Cálculo del Domain

Cargado desde configuración:
- `name`: "Polymarket Exchange" (o según documentación)
- `version`: "1" (o según documentación)
- `chainId`: 137 (Polygon) o según red
- `verifyingContract`: Dirección del contrato verificador

#### Paso 4: Firma

1. Construir estructura EIP-712 completa
2. Calcular `domain_separator` (hash del domain)
3. Calcular `message_hash` (hash del mensaje)
4. Firmar usando clave privada:
   - Usar librería `eth_account` o similar
   - Resultado: `signature` (string hex con prefijo `0x`)

#### Paso 5: Creación de SignedOrder

1. Guardar estructura completa:
   - `domain_json`: Domain completo
   - `message_struct`: Mensaje completo
   - `signature`: Firma hex
   - `domain_separator`: Hash del domain
   - `message_hash`: Hash del mensaje
   - `wallet_address`: Dirección derivada de la clave privada

2. Estado inicial: `READY_TO_SEND`

3. Persistir en base de datos

#### Paso 6: Envío a Polymarket

1. Construir payload HTTP esperado por Polymarket:
   ```json
   {
     "marketId": "...",
     "outcome": "YES",
     "price": "...",
     "size": "...",
     "side": "BUY",
     "signature": "0x...",
     "clientOrderId": "...",
     "nonce": "...",
     "expiration": "..."
   }
   ```

2. Crear `ExecutionRecord` antes de enviar

3. Enviar POST a endpoint de Polymarket

4. Actualizar `ExecutionRecord` con respuesta

5. Actualizar `SignedOrder.status` según resultado

---

## 5. Seguridad de Claves y Firmas

### 5.1. Ubicación de la Clave Privada

#### Opción 1: Backend con Signer Local (MVP)

**Implementación:**
- Clave privada almacenada en variable de entorno cifrada
- O en manager de secretos (AWS Secrets Manager, HashiCorp Vault, etc.)
- Nunca se loggea ni se muestra
- El módulo de firma es un submódulo aislado (`app/core/signer.py`)

**Ventajas:**
- Simple de implementar
- Control total del proceso

**Desventajas:**
- Clave privada accesible al proceso del backend
- Riesgo si el servidor es comprometido

#### Opción 2: Servicio Externo de Firma (Recomendado a Futuro)

**Implementación:**
- Microservicio dedicado que recibe el message y devuelve signature
- El backend NO ve la clave privada directamente
- Se puede montar como HSM / Signer service
- Comunicación mediante API REST con autenticación

**Ventajas:**
- Mayor seguridad (clave privada aislada)
- Escalable
- Cumple con mejores prácticas de seguridad

**Desventajas:**
- Mayor complejidad
- Latencia adicional (aunque mínima)

**Recomendación:** Para el MVP, empezar con Opción 1 pero diseñar la interfaz para migrar fácilmente a Opción 2.

### 5.2. Requisitos de Seguridad

**La clave privada:**
- ❌ Nunca se loggea
- ❌ No se guarda en base de datos
- ❌ No se envía por red a otros servicios en texto plano
- ❌ No se expone en mensajes de error
- ✅ Se carga una sola vez al inicio (o bajo demanda con caché seguro)
- ✅ Se mantiene en memoria solo el tiempo necesario para firmar

**Todas las operaciones de firma deben:**
- Tener logs a nivel de `intent_id` + hash del mensaje, pero **nunca** exponer la clave
- Estar encapsuladas en un módulo `signer.py` / `wallet_signer.py`
- Validar que el mensaje no ha sido modificado antes de firmar
- Usar librerías criptográficas probadas (`eth_account`, `web3.py`)

**Ejemplo de log seguro:**
```json
{
  "timestamp": "2025-01-18T10:25:00.123Z",
  "level": "INFO",
  "component": "signer",
  "event_type": "order_signed",
  "trace_id": "...",
  "intent_id": "...",
  "message_hash": "0xabc123...",
  "wallet_address": "0x1234...",
  "message": "Order signed successfully"
}
```

---

## 6. Trazabilidad y Auditoría Completa

### 6.1. Relaciones Clave (IDs y Correlaciones)

Para garantizar trazabilidad completa:

**Cadena de IDs:**
```
trace_id (generado en Strategy)
  └─> intent_id (OrderIntent)
      └─> signed_order_id (SignedOrder)
          └─> execution_id (ExecutionRecord)
              └─> polymarket_order_id (de Polymarket)
                  └─> order_state_history_id (OrderStateHistory)
```

**Relaciones en base de datos:**
- `OrderIntent.trace_id` → UUID único por ciclo de vida
- `SignedOrder.intent_id` → FK a `OrderIntent`
- `ExecutionRecord.signed_order_id` → FK a `SignedOrder`
- `OrderStateHistory.polymarket_order_id` → FK a orden en Polymarket

**Propagación del trace_id:**
El `trace_id` se genera cuando Strategy crea el `OrderIntent` y se propaga por:
- Logs estructurados
- `OrderIntent`
- `SignedOrder`
- `ExecutionRecord`
- `OrderStateHistory`

Esto permite correlacionar todos los eventos relacionados con una orden.

### 6.2. Logging Estructurado (JSON)

Todos los logs relacionados con ejecución deben ser **estructurados en JSON** con campos mínimos:

**Campos requeridos:**
- `timestamp`: ISO 8601 con timezone
- `level`: `INFO`, `WARN`, `ERROR`, `DEBUG`
- `trace_id`: UUID para correlación
- `component`: `strategy`, `risk`, `execution`, `signer`, `order_monitor`
- `event_type`: Tipo de evento (ver abajo)
- `message`: Mensaje legible

**Campos opcionales (según contexto):**
- `intent_id`: Si aplica
- `signed_order_id`: Si aplica
- `polymarket_order_id`: Si aplica
- `execution_id`: Si aplica
- `request_payload_hash`: Hash del payload (no el payload completo)
- `response_payload_hash`: Hash de la respuesta
- `latency_ms`: Latencia en milisegundos
- `error_type`: Tipo de error (si aplica)
- `error_code`: Código de error (si aplica)
- `extra`: Objeto JSON con detalles adicionales

**Tipos de eventos (`event_type`):**
- `order_intent_created`: Intent creado por Strategy
- `order_intent_approved`: Intent aprobado por Risk Engine
- `order_intent_rejected`: Intent rechazado por Risk Engine
- `order_signed`: Orden firmada exitosamente
- `order_signing_failed`: Error al firmar
- `order_sent`: Orden enviada a Polymarket
- `order_accepted`: Orden aceptada por Polymarket
- `order_rejected`: Orden rechazada por Polymarket
- `order_filled`: Orden ejecutada completamente
- `order_partially_filled`: Orden ejecutada parcialmente
- `order_cancelled`: Orden cancelada
- `order_expired`: Orden expirada
- `order_error`: Error genérico

**Ejemplo de log:**
```json
{
  "timestamp": "2025-01-18T10:25:00.123Z",
  "level": "INFO",
  "component": "execution",
  "event_type": "order_sent",
  "trace_id": "b3c1e7fc-2a5f-4b7a-9c90-1b...",
  "intent_id": "c7a9c6b0-8f1a-4ef0-9e21-3a...",
  "signed_order_id": "04b684cb-3c3f-4d4f-92d7-5c...",
  "request_payload_hash": "0xabc123...",
  "latency_ms": 183,
  "message": "Order sent to Polymarket trading API",
  "extra": {
    "endpoint": "/api/v1/orders",
    "http_status": 200
  }
}
```

### 6.3. Almacenamiento de Payloads

**Para auditoría completa, es recomendable:**

1. **Guardar payloads completos en base de datos:**
   - `SignedOrder.message_struct`: Estructura EIP-712 completa
   - `ExecutionRecord.request_payload`: Payload HTTP completo enviado
   - `ExecutionRecord.response_payload`: Respuesta completa de Polymarket
   - `OrderStateHistory.raw_state`: Estado crudo de Polymarket

2. **En logs, solo guardar hashes:**
   - `request_payload_hash`: SHA256 del payload
   - `response_payload_hash`: SHA256 de la respuesta
   - Esto permite verificar integridad sin saturar logs

3. **Almacenamiento opcional en storage externo:**
   - Para payloads muy grandes, guardar en S3/Storage y referenciar URL
   - Útil para análisis post-mortem detallado

**Esto permite:**
- Reconstruir cualquier caso si hay incidente
- Demostrar exactamente lo que se firmó y envió
- Auditar decisiones y errores
- Cumplir con requisitos regulatorios (si aplica)

---

## 7. Ciclo de Vida Completo de una Orden

### 7.1. Secuencia Detallada

```
1. Strategy Engine crea OrderIntent
   └─> Genera trace_id
   └─> Estado: PENDING_EXECUTION
   └─> Log: order_intent_created

2. Risk Engine aprueba OrderIntent
   └─> Estado: PENDING_EXECUTION (sin cambio)
   └─> Log: order_intent_approved

3. Execution Engine recibe OrderIntent
   └─> Hereda trace_id
   └─> Log: order_received_for_execution

4. Execution Engine llama a Signer
   ├─> Construye EIP-712 message
   ├─> Firma con clave privada
   ├─> Crea SignedOrder
   │   └─> Estado: READY_TO_SEND
   │   └─> Persiste en DB
   └─> Log: order_signed

5. Execution Engine envía orden a Polymarket
   ├─> Crea ExecutionRecord (antes de enviar)
   ├─> Construye payload HTTP
   ├─> Envía POST a Polymarket
   ├─> Mide latencia (request → response)
   ├─> Actualiza ExecutionRecord con respuesta
   │   └─> Estado: ACCEPTED / REJECTED / ERROR / TIMEOUT
   ├─> Actualiza SignedOrder.status
   │   └─> SENT (si aceptada) / SEND_FAILED (si error)
   └─> Log: order_sent / order_accepted / order_rejected

6. Order Monitor (proceso en background)
   ├─> Consulta periódicamente Polymarket para polymarket_order_id
   ├─> Crea entradas en OrderStateHistory
   └─> Detecta cambios de estado:
       ├─> OPEN → PARTIALLY_FILLED
       ├─> PARTIALLY_FILLED → FILLED
       ├─> OPEN → CANCELLED
       └─> OPEN → EXPIRED

7. Cuando orden pasa a FILLED:
   ├─> Actualiza Position en Portfolio Engine
   ├─> Crea Trade record
   ├─> Actualiza Exposure
   ├─> Actualiza OrderIntent.status = EXECUTED
   └─> Log: order_filled
```

### 7.2. Order Monitor (Proceso de Monitoreo)

El Order Monitor es un proceso en background que:

1. **Consulta periódicamente** órdenes pendientes en Polymarket
2. **Crea entradas** en `OrderStateHistory` para cada cambio detectado
3. **Detecta transiciones** de estado:
   - `OPEN` → `PARTIALLY_FILLED`
   - `PARTIALLY_FILLED` → `FILLED`
   - `OPEN` → `CANCELLED`
   - `OPEN` → `EXPIRED`

4. **Notifica** a otros módulos cuando hay cambios relevantes:
   - Position Engine (cuando hay fill)
   - Metrics (para estadísticas)
   - Dashboard (para UI)

**Frecuencia de polling:**
- Órdenes recientes (< 5 min): Cada 2 segundos
- Órdenes antiguas (> 5 min): Cada 30 segundos
- Órdenes muy antiguas (> 1 hora): Cada 5 minutos

**Optimización:**
- Usar WebSocket si Polymarket lo soporta (mejor que polling)
- Batch queries cuando sea posible
- Respeta rate limits de Polymarket

---

## 8. Manejo de Errores

### 8.1. Error en Firma (Signer)

**Ejemplos:**
- Clave privada no disponible
- Fallo en librería de firma
- Inconsistencia en el mensaje EIP-712
- Wallet no encontrada o inactiva

**Acción:**
1. `SignedOrder` **NO se crea**
2. `OrderIntent.status` → `REJECTED_BY_EXECUTION`
3. Log ERROR con:
   - `trace_id`
   - `intent_id`
   - `error_type = SIGNING_ERROR`
   - `error_message` (sin exponer clave privada)
   - `stacktrace` (si se guarda internamente, no en logs de producción)

**No se reintenta** (error crítico, requiere intervención)

### 8.2. Error HTTP al Enviar a Polymarket

**Ejemplos:**
- Timeout de red
- 429 (rate limit)
- 500 (error del servidor)
- 502/503 (servicio no disponible)

**Acción:**
1. `ExecutionRecord` con `status = ERROR` o `TIMEOUT`
2. `SignedOrder.status` → `SEND_FAILED`
3. **Lógica de retry:**
   - Máximo 3 reintentos
   - Backoff exponencial: 1s, 2s, 4s
   - No duplicar órdenes: usar `clientOrderId` único
   - Si falla después de 3 intentos: marcar como `REJECTED_BY_EXECUTION`

4. Log WARN/ERROR con:
   - `trace_id`
   - `signed_order_id`
   - `http_status_code`
   - `error_type = HTTP_ERROR` o `TIMEOUT_ERROR`
   - `retry_count`

### 8.3. Error de Validación de Polymarket

**Ejemplos:**
- Orden rechazada por precio fuera de rango
- Tamaño mínimo no cumplido
- Mercado cerrado en el momento del envío
- Firma inválida
- Nonce incorrecto

**Acción:**
1. `ExecutionRecord` con `status = REJECTED`
2. `SignedOrder.status` → `SEND_FAILED`
3. `OrderIntent.status` → `REJECTED_BY_EXECUTION`
4. Log ERROR con:
   - `trace_id`
   - `signed_order_id`
   - `error_type = EXCHANGE_REJECT`
   - `error_code`: Código de error de Polymarket
   - `error_message`: Mensaje de error de Polymarket
   - `reason`: Razón específica del rechazo

**No se reintenta** (error de validación, requiere corrección)

### 8.4. Error en Order Monitor

**Ejemplos:**
- Timeout al consultar estado
- Error de parsing de respuesta
- Orden no encontrada en Polymarket

**Acción:**
1. Log WARN con:
   - `trace_id`
   - `polymarket_order_id`
   - `error_type = MONITOR_ERROR`
2. Reintentar en siguiente ciclo de polling
3. Si persiste > 10 minutos: marcar como `MONITORING_FAILED` (requiere investigación manual)

---

## 9. Requisitos Específicos de Trazabilidad (Checklist)

### 9.1. Trazabilidad Hacia Atrás

Cada orden debe poder trazarse hacia atrás:
```
polymarket_order_id 
  → execution_id 
    → signed_order_id 
      → intent_id 
        → espn_event_id 
          → polymarket_market_id
```

**Implementación:**
- Todas las entidades tienen FK a la entidad anterior
- Queries SQL simples pueden reconstruir la cadena completa

### 9.2. Trazabilidad Hacia Adelante

Cada intent debe poder trazarse hacia adelante:
```
intent_id 
  → signed_order_id 
    → execution_records 
      → order_state_history 
        → final_position
```

**Implementación:**
- Queries con JOINs pueden reconstruir el flujo completo
- Dashboard puede mostrar el estado completo de una orden

### 9.3. Reconstrucción de Incidentes

Cada incidente se debe poder reconstruir:
- `trace_id` + logs estructurados + payload hashes permiten rearmar la historia completa
- Todos los logs relacionados tienen el mismo `trace_id`
- Payloads completos están en base de datos (o storage)

**Herramientas:**
- Query por `trace_id` en logs
- Query por `trace_id` en base de datos
- Reconstrucción de payloads desde hashes

### 9.4. Auditoría de Firmas

Cada firma debe ser auditable (sin exponer claves):
- ✅ `message_struct` guardado (estructura EIP-712 completa)
- ✅ `signature` guardada (firma hex)
- ✅ `wallet_address` usada
- ✅ `domain EIP-712` guardado
- ✅ `message_hash` guardado (para verificación)
- ✅ `domain_separator` guardado (para verificación)

**Verificación:**
- Se puede verificar la firma usando solo los datos guardados
- No se necesita la clave privada para verificar

### 9.5. Métricas Agregadas

**Métricas de flujo:**
- Número de intents creados
- Número de intents aprobados
- Número de órdenes firmadas
- Número de órdenes enviadas
- Número de órdenes aceptadas
- Número de órdenes filled
- Tasa de conversión en cada etapa

**Métricas de errores:**
- Tasa de error por tipo:
  - `SIGNING_ERROR`
  - `HTTP_ERROR`
  - `TIMEOUT_ERROR`
  - `EXCHANGE_REJECT`
  - `MONITOR_ERROR`

**Métricas de latencia:**
- Latencia de firma (intent → signed)
- Latencia de envío (signed → sent)
- Latencia de aceptación (sent → accepted)
- Latencia end-to-end (intent → filled)

---

## 10. Estructura de Archivos a Implementar

```
backend/app/
├── core/
│   ├── execution.py          # Execution Engine (ya existe, actualizar)
│   ├── signer.py             # Módulo de firma EIP-712 (NUEVO)
│   └── order_monitor.py      # Order Monitor (NUEVO)
│
├── models/
│   ├── order_intent.py       # Modelo OrderIntent (NUEVO)
│   ├── signed_order.py       # Modelo SignedOrder (NUEVO)
│   ├── execution_record.py   # Modelo ExecutionRecord (NUEVO)
│   └── order_state_history.py # Modelo OrderStateHistory (NUEVO)
│
└── services/
    └── audit_service.py      # Servicio de auditoría y trazabilidad (NUEVO)
```

### 10.1. Módulos Principales

**`app/core/signer.py`:**
- Clase `OrderSigner`
- Método `sign_order(intent: OrderIntent) -> SignedOrder`
- Manejo seguro de claves privadas
- Implementación EIP-712

**`app/core/execution.py`:**
- Clase `Execution` (actualizar existente)
- Método `execute_intent(intent: ApprovedOrderIntent) -> ExecutionRecord`
- Integración con Signer
- Envío a Polymarket
- Manejo de errores y retries

**`app/core/order_monitor.py`:**
- Clase `OrderMonitor`
- Método `monitor_orders()` (background task)
- Polling de Polymarket
- Actualización de `OrderStateHistory`
- Detección de fills y cambios de estado

**`app/services/audit_service.py`:**
- Clase `AuditService`
- Métodos de consulta de trazabilidad
- Reconstrucción de historiales
- Generación de reportes de auditoría

---

## 11. Resumen

El módulo de **Ejecución, Firmas y Trazabilidad** es el corazón operativo del sistema:

- ✅ Convierte decisiones de trading (`OrderIntent`) en órdenes reales firmadas y enviadas a Polymarket
- ✅ Garantiza seguridad en el uso de claves privadas
- ✅ Proporciona trazabilidad completa en todo el ciclo de vida:
  - Desde la idea (intent)
  - Hasta la ejecución (fill)
  - Pasando por todas las firmas, payloads y respuestas

**Un diseño correcto de este módulo:**
- Protege capital (hasta 200k € y más)
- Permite analizar errores
- Justifica decisiones
- Mejora estrategias
- Depura incidentes de forma profesional
- Cumple con requisitos de auditoría y compliance

**Este documento sirve como especificación técnica completa para implementar:**
- `app/core/execution.py` (actualizar)
- `app/core/signer.py` (nuevo)
- `app/core/order_monitor.py` (nuevo)
- `app/models/order_intent.py` (nuevo)
- `app/models/signed_order.py` (nuevo)
- `app/models/execution_record.py` (nuevo)
- `app/models/order_state_history.py` (nuevo)
- `app/services/audit_service.py` (nuevo)

---

## 12. Próximos Pasos

1. **Revisar documentación oficial de Polymarket** para:
   - Estructura exacta de EIP-712
   - Endpoints de trading API
   - Formatos de órdenes y respuestas
   - Rate limits y mejores prácticas

2. **Implementar modelos de base de datos** (Alembic migrations)

3. **Implementar módulo de firma** (`signer.py`)

4. **Actualizar Execution Engine** con nueva arquitectura

5. **Implementar Order Monitor** como background task

6. **Implementar logging estructurado** con trace_id

7. **Crear tests unitarios** para cada componente

8. **Crear tests de integración** para flujo completo
