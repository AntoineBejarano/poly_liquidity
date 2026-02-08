# Análisis Completo: Estrategia Near-Resolution Liquidity Provider

**Fecha**: 2026-02  
**Versión**: 1.0  
**Estado**: Implementado

---

## 📋 Índice

1. [Visión General](#visión-general)
2. [Flujo Completo del Usuario](#flujo-completo-del-usuario)
3. [Configuración de Cuentas y Fuentes Externas](#configuración-de-cuentas-y-fuentes-externas)
4. [Selección y Filtrado de Mercados](#selección-y-filtrado-de-mercados)
5. [Configuración de la Estrategia](#configuración-de-la-estrategia)
6. [Operación y Ejecución](#operación-y-ejecución)
7. [Monitoreo y Observabilidad](#monitoreo-y-observabilidad)
8. [Arquitectura Técnica](#arquitectura-técnica)

---

## Visión General

### ¿Qué es Near-Resolution Liquidity Provider?

La estrategia **Near-Resolution Liquidity Provider** es una estrategia automatizada que:

- **Detecta** cuando un evento real ya ha terminado pero aún no ha sido resuelto por Polymarket
- **Provee liquidez** comprando a usuarios que quieren salir antes de la resolución
- **Captura el diferencial** de precio (ej: compra a 0.98, resuelve a 1.00 = 2% ganancia)
- **Maneja riesgo casi nulo** porque el evento ya está decidido en el mundo real

### Edge Explotado

- **Latencia de resolución**: Polymarket resuelve con retraso después de que el evento termina
- **Urgencia de usuarios**: Muchos usuarios quieren hacer cashout inmediato
- **Falta de liquidez profesional**: El mercado queda sin liquidity providers profesionales
- **Ventana temporal**: Oportunidad entre el fin del evento y la resolución de Polymarket

### Ejemplo Concreto

**Evento**: "¿Ganará el Equipo A el partido?"

1. El partido termina → Equipo A gana claramente
2. Fuentes externas confirman resultado (API deportiva, múltiples feeds)
3. Estado en Polymarket:
   - YES bid: 0.95
   - YES ask: 0.99
   - Liquidez baja
4. **Acción del bot**: Coloca un bid grande unilateral a 0.97-0.98
5. **Resultado**: Compra a 0.98, resuelve a 1.00 = 2% ganancia con riesgo casi nulo

---

## Flujo Completo del Usuario

### Paso 1: Crear External Data Source (Cuenta Externa)

**Antes de crear la estrategia**, el usuario debe configurar una fuente externa que confirme resultados de eventos.

#### 1.1 Acceso a External Data Sources

- **Ruta**: `/external-data-sources` (o desde configuración de estrategia)
- **API Endpoint**: `GET /api/external-data-sources`

#### 1.2 Crear Nueva Fuente

**Modelo de Datos** (`ExternalDataSource`):

```python
{
  "name": "Sports API - Event Results",           # Nombre descriptivo
  "connector_type": "custom_api",                  # Tipo: "pinnacle", "bet365", "custom_api"
  "description": "API para confirmar resultados de eventos deportivos",
  "connector_config": {                            # Configuración JSONB
    "base_url": "https://api.sports.com",
    "api_key_name": "X-API-Key",
    "api_key_value": "tu-api-key-secreta",
    "method": "GET",
    "headers": {
      "Content-Type": "application/json"
    },
    "timeout_seconds": 5,
    "rate_limit": {
      "requests_per_minute": 60
    }
  },
  "is_active": true
}
```

**Campos Requeridos**:
- `name`: Nombre descriptivo de la fuente
- `connector_type`: Tipo de conector (`custom_api`, `pinnacle`, `bet365`)
- `connector_config`: Configuración completa del conector (JSONB)

**Tipos de Conectores Soportados**:
- `custom_api`: API REST personalizada
- `pinnacle`: Integración con Pinnacle Sports
- `bet365`: Integración con Bet365

#### 1.3 Configuración de Custom API

Para Near-Resolution, típicamente se usa `custom_api`:

```json
{
  "connector_type": "custom_api",
  "connector_config": {
    "base_url": "https://api.sports.com",
    "api_key_name": "X-API-Key",
    "api_key_value": "tu-api-key",
    "method": "GET",
    "endpoint_template": "/api/event/result?event_id={event_id}",
    "response_format": "json",
    "timeout_seconds": 5,
    "retry_config": {
      "max_retries": 3,
      "backoff_strategy": "exponential"
    }
  }
}
```

**Respuesta Esperada de la API Externa**:

```json
{
  "event_id": "uuid-del-evento",
  "confirmed": true,
  "result": "YES",  // o "NO"
  "confidence": 0.95,
  "timestamp": "2025-01-XXT10:00:00Z",
  "source": "sports_api"
}
```

#### 1.4 Obtener ID de la Fuente

Después de crear la fuente:
- El sistema asigna un UUID único
- Este ID se usa en la configuración de la estrategia
- **API**: `GET /api/external-data-sources?is_active=true` retorna lista con IDs

---

### Paso 2: Seleccionar y Filtrar Mercados

**Antes o durante la creación de la estrategia**, el usuario puede seleccionar qué mercados operar.

#### 2.1 Página de Mercados

**Ruta**: `/markets`  
**API Endpoint**: `GET /api/markets`

#### 2.2 Filtros Disponibles

El usuario puede filtrar mercados por:

1. **Búsqueda por nombre** (`search`):
   - Campo de texto libre
   - Busca en `name` y `question` del market

2. **Categoría** (`category`):
   - Filtro dropdown con categorías disponibles
   - Ejemplos: `sports`, `crypto`, `politics`, `entertainment`
   - **Componente**: `CategoriesFilterWithLoader`

3. **Series** (`series_id`):
   - Filtro por Series (agrupador lógico)
   - Ejemplo: "Bitcoin Up or Down" (Series) contiene múltiples Markets
   - **Componente**: `SeriesFilterWithLoader`

4. **Tags** (`tag_id`):
   - Filtro por tags (múltiple selección)
   - Ejemplos: `nfl`, `nba`, `crypto`, `presidential`
   - **Componente**: `TagsFilterWithLoader`

5. **Estado Enabled** (`enabled`):
   - `all`: Todos los mercados
   - `enabled`: Solo mercados activados
   - `disabled`: Solo mercados desactivados

#### 2.3 Activar/Desactivar Mercados

**Acción**: Toggle enable/disable por market

- **API**: `PATCH /api/markets/{market_id}/enable`
- **Efecto**: 
  - `enabled=true`: El Scanner descubrirá Events de este Market
  - `enabled=false`: El Market se ignora

**Nota Importante**:
- Los **Markets** son plantillas (no tradeables directamente)
- Los **Events** son instancias concretas que se tradan
- Solo los Markets `enabled=true` generan Events para trading

#### 2.4 Selección en Estrategia

Durante la creación de la estrategia (`/strategies/new/Liquidity`):

**Opciones de Selección**:

1. **Por Categorías** (`selectedCategories`):
   ```typescript
   const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
   // Ejemplo: ["sports", "crypto"]
   ```

2. **Por Markets Específicos** (`selectedMarkets`):
   ```typescript
   const [selectedMarkets, setSelectedMarkets] = useState<string[]>([]);
   // Ejemplo: ["market-uuid-1", "market-uuid-2"]
   ```

3. **Por Events Específicos** (`selectedEvents`):
   ```typescript
   const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
   // Ejemplo: ["event-uuid-1", "event-uuid-2"]
   ```

4. **Auto-Attach** (`autoAttach`):
   ```typescript
   const [autoAttach, setAutoAttach] = useState(false);
   // Si true: automáticamente asigna nuevos Events de Markets seleccionados
   ```

**Payload Final**:

```json
{
  "markets_events": {
    "categories": ["sports", "crypto"],
    "markets": ["market-uuid-1", "market-uuid-2"],
    "events": ["event-uuid-1"],
    "auto_attach": true
  }
}
```

---

### Paso 3: Configurar la Estrategia

**Ruta**: `/strategies/new/Liquidity`  
**Template ID**: `liquidity_near_end`

#### 3.1 Información Básica

```typescript
{
  "name": "Near-Resolution LP - Sports",
  "description": "Provee liquidez en eventos deportivos near-resolution",
  "tags": ["liquidity", "near-resolution", "low-risk"]
}
```

#### 3.2 Cuenta de Ejecución

**Selección de Wallet**:

- **API**: `GET /api/wallets?venue=polymarket`
- **Campos**:
  - `id`: UUID del wallet
  - `name`: Nombre descriptivo
  - `address`: Dirección de la wallet
  - `balance`: Balance en USDC
  - `allowance`: Allowance para trading
  - `status`: `ok` | `limited` | `error`

```typescript
{
  "execution_account": {
    "wallet_id": "wallet-uuid"
  }
}
```

#### 3.3 Capital y Riesgo

```typescript
{
  "capital_risk": {
    "max_capital": 5000,              // Capital máximo total
    "max_exposure_per_event": 2000,   // Exposición máxima por evento
    "max_positions": 5,                // Máximo de posiciones simultáneas
    "order_size": {
      "type": "fixed",                 // o "range"
      "value": 1000                    // Si type="fixed"
      // o "min": 500, "max": 2000 si type="range"
    }
  }
}
```

#### 3.4 Condiciones de Entrada

```typescript
{
  "entry_conditions": {
    "price_range": {
      "min": 0.95,    // Precio mínimo para entrar
      "max": 0.98     // Precio máximo para entrar
    },
    "max_time_to_resolution_minutes": 30,  // Máximo tiempo hasta resolución
    "min_liquidity_usdc": 2000             // Liquidez mínima requerida
  }
}
```

#### 3.5 Fuente Externa de Confirmación

**Campo Crítico**: `external_source_id`

- **Tipo**: Select dropdown
- **Opciones**: Cargadas dinámicamente desde `GET /api/external-data-sources?is_active=true`
- **Valor**: UUID de la External Data Source creada en Paso 1

```typescript
{
  "external_source_id": "external-source-uuid-123"
}
```

**Configuración del Template**:

```python
{
  "key": "external_source_id",
  "label": "Fuente externa de confirmación",
  "type": "select",
  "required": True,
  "description": "Selecciona la fuente externa que confirma resultados de eventos",
  "section": "Fuentes de Datos",
  "options_source": "external_data_sources"  # Carga dinámica
}
```

#### 3.6 Checkers (Opcional)

```typescript
{
  "checkers": [
    {
      "checker_id": "checker-uuid-1",
      "enabled": true
    }
  ]
}
```

**Nota**: Los checkers validan el estado del evento. Para Near-Resolution, típicamente se usa la fuente externa como checker principal.

#### 3.7 Comportamiento de Ejecución

```typescript
{
  "execution_behavior": {
    "execute_immediately": true,      // Ejecutar inmediatamente cuando se crea intent
    "stagger_orders": false,           // Espaciar órdenes en el tiempo
    "max_retries": 3,                  // Máximo de reintentos
    "cooldown_seconds": 5              // Tiempo de espera entre reintentos
  }
}
```

---

### Paso 4: Compilación y Activación

#### 4.1 Compilación del Template

Cuando el usuario guarda la estrategia:

1. **Backend recibe** configuración del formulario
2. **Template Compiler** (`compile_liquidity_near_end`) convierte la configuración en Decision Graph
3. **Support Graph** se configura con `external_source_id`

**Ejemplo de Decision Graph Compilado**:

```json
{
  "decision_graph": {
    "entry_node": "collect_state",
    "nodes": {
      "collect_state": {
        "type": "collect_state",
        "config": {
          "sources": ["market_state", "event_state", "external_data", "risk_state"]
        },
        "next": "compute_signals"
      },
      "check_event_finished": {
        "type": "edge_and_risk_check",
        "config": {
          "conditions": [
            {
              "field": "event_state.state",
              "operator": "==",
              "value": "FINISHED_CONFIRMED"
            },
            {
              "field": "external_data.event_confirmation.confirmed",
              "operator": "==",
              "value": true
            },
            {
              "field": "market_state.last_price",
              "operator": ">=",
              "value": 0.95
            },
            {
              "field": "market_state.last_price",
              "operator": "<=",
              "value": 0.98
            }
          ],
          "logic": "AND"
        },
        "on_true": "calculate_size",
        "on_false": "idle"
      }
    }
  }
}
```

**Support Graph Compilado**:

```json
{
  "support_graphs": [
    {
      "name": "confirm_event_result",
      "trigger": {
        "type": "event_state_change",
        "condition": {
          "field": "event.state",
          "operator": "==",
          "value": "FINISHED"
        }
      },
      "entry_node": "fetch_external_confirmation",
      "nodes": {
        "fetch_external_confirmation": {
          "type": "fetch_external_source",
          "config": {
            "source_id": "{{external_source_id}}",  // Del formulario
            "endpoint": "/api/event/result",
            "params": {
              "event_id": "{{event.id}}"
            },
            "output_key": "event_confirmation"
          },
          "next": "update_cache"
        }
      }
    }
  ]
}
```

#### 4.2 Guardar Estrategia

**API**: `POST /api/strategies`

**Payload Completo**:

```json
{
  "name": "Near-Resolution LP - Sports",
  "description": "...",
  "tags": ["liquidity", "near-resolution"],
  "template_id": "liquidity_near_end",
  "execution_account": {
    "wallet_id": "wallet-uuid"
  },
  "capital_risk": {
    "max_capital": 5000,
    "max_exposure_per_event": 2000,
    "max_positions": 5,
    "order_size": {
      "type": "fixed",
      "value": 1000
    }
  },
  "entry_conditions": {
    "price_range": { "min": 0.95, "max": 0.98 },
    "max_time_to_resolution_minutes": 30,
    "min_liquidity_usdc": 2000
  },
  "markets_events": {
    "categories": ["sports"],
    "markets": [],
    "events": [],
    "auto_attach": true
  },
  "checkers": [],
  "execution_behavior": {
    "execute_immediately": true,
    "stagger_orders": false,
    "max_retries": 3,
    "cooldown_seconds": 5
  },
  "config": {
    "external_source_id": "external-source-uuid-123"
  }
}
```

**Respuesta**:

```json
{
  "id": "strategy-uuid",
  "name": "Near-Resolution LP - Sports",
  "status": "active",
  "created_at": "2025-01-XXT10:00:00Z"
}
```

---

## Operación y Ejecución

### Flujo de Ejecución

#### 1. Scanner Descubre Events

- **Scanner** busca Markets con `enabled=true`
- Descubre nuevos Events de esos Markets
- Crea registros en DB: `Event` con `state=ACTIVE`

#### 2. Event Watcher Detecta Cambio

- **Event Watcher** monitorea Events asignados a la estrategia
- Cuando `event.state` cambia a `FINISHED`:
  - **Trigger** del Support Graph se activa
  - Ejecuta `confirm_event_result` Support Graph

#### 3. Support Graph: Confirmación Externa

**Nodo `fetch_external_confirmation`**:

1. Obtiene `source_id` de la configuración
2. Llama a `FetchExternalSourceNode.execute()`
3. Hace request a la API externa:
   ```
   GET https://api.sports.com/api/event/result?event_id={event.id}
   Headers: X-API-Key: tu-api-key
   ```
4. Recibe respuesta:
   ```json
   {
     "event_id": "uuid",
     "confirmed": true,
     "result": "YES",
     "confidence": 0.95
   }
   ```
5. Almacena en State Cache:
   ```json
   {
     "key": "event.{event.id}.external_confirmation",
     "value": { "confirmed": true, "result": "YES" },
     "ttl_seconds": 3600
   }
   ```

#### 4. Decision Graph: Evaluación

**Trigger**: Strategy Trigger se activa (timer o event change)

**Nodo `collect_state`**:
- Recolecta:
  - `market_state`: Precio, liquidez, orderbook
  - `event_state`: Estado del evento (`FINISHED_CONFIRMED`)
  - `external_data`: Confirmación externa (del cache)
  - `risk_state`: Exposición actual, límites

**Nodo `check_event_finished`**:
- **Condiciones**:
  - ✅ `event_state.state == "FINISHED_CONFIRMED"`
  - ✅ `external_data.event_confirmation.confirmed == true`
  - ✅ `market_state.last_price >= 0.95`
  - ✅ `market_state.last_price <= 0.98`
  - ✅ `risk_state.exposure < max_exposure`
- **Si todas pasan** → `on_true: "calculate_size"`
- **Si alguna falla** → `on_false: "idle"`

**Nodo `calculate_size`**:
- Calcula tamaño de orden según configuración:
  - `fixed`: Usa `value` directamente
  - `range`: Calcula entre `min` y `max` según liquidez
- **Output**: `{ "size": 1000, "size_usdc": 1000, "price": 0.97 }`

**Nodo `build_plan`**:
- Crea Execution Plan:
  ```json
  {
    "plan_id": "plan-uuid",
    "legs": [
      {
        "leg_id": "leg_1",
        "side": "BUY",
        "outcome": "YES",
        "target_price": 0.97,
        "size": 1000,
        "size_usdc": 1000,
        "reason": "Near-resolution liquidity provision"
      }
    ],
    "ttl_ms": 30000,
    "risk_config": {
      "max_slippage": 0.02,
      "max_fill_delay_ms": 5000,
      "abort_on_price_move": true
    }
  }
  ```

**Nodo `emit_plan`**:
- Emite `OrderIntent` al Risk Engine
- Risk Engine valida:
  - Exposición dentro de límites
  - Tamaño de orden válido
  - Límites de riesgo respetados

#### 5. Execution Graph: Ejecución

**Nodo `execution_coordinator`**:

1. **Validación Pre-Ejecución**:
   - Verifica precio no ha cambiado significativamente
   - Verifica liquidez suficiente
   - Verifica TTL no expirado

2. **Ejecución**:
   - Crea orden en Polymarket:
     ```json
     {
       "market_id": "market-uuid",
       "side": "BUY",
       "outcome": "YES",
       "price": 0.97,
       "size": 1000,
       "nonce": 123
     }
     ```
   - Firma con EIP-712
   - Envía a Polymarket Trading API

3. **Monitoreo**:
   - Espera fill (máximo `max_fill_delay_ms`)
   - Si fill completo → `on_success: "end"`
   - Si falla → `on_failure: "compensate"`

4. **Compensación** (si falla):
   - Si alguna leg falla, ejecuta compensación
   - Estrategia: `reverse_all` (revierte todas las legs ejecutadas)

---

## Monitoreo y Observabilidad

### Dashboard de Estrategia

**Ruta**: `/strategies/{strategy_id}/live`

**Métricas Mostradas**:

1. **Estado General**:
   - Status: `active` | `paused` | `error`
   - Capital utilizado / Capital máximo
   - Exposición actual / Exposición máxima
   - Posiciones activas / Máximo de posiciones

2. **Performance**:
   - P&L total
   - P&L por evento
   - Tasa de éxito (fills / intents)
   - Tiempo promedio de ejecución

3. **Eventos Activos**:
   - Lista de Events siendo monitoreados
   - Estado de cada Event
   - Confirmación externa recibida
   - Precio actual vs rango objetivo

4. **Órdenes Recientes**:
   - Historial de OrderIntents
   - Estado: `pending` | `filled` | `cancelled` | `failed`
   - Precio ejecutado vs precio objetivo
   - Slippage

### Decision Traces

**Ruta**: `/strategies/{strategy_id}/traces`

**Información Rastreada**:

- **Trace ID**: UUID único para correlacionar decisiones
- **Decision Stages**:
  - `SCAN`: Mercado evaluado
  - `EVENT_CONFIRMATION`: Confirmación de evento
  - `STRATEGY`: Intent creado
  - `RISK`: Validación de riesgo
  - `EXECUTION`: Orden ejecutada

**Ejemplo de Trace**:

```json
{
  "trace_id": "trace-uuid",
  "decision_stage": "STRATEGY",
  "input_data": {
    "market_id": "market-uuid",
    "best_ask": 0.98,
    "best_bid": 0.97,
    "event_state": "FINISHED_CONFIRMED",
    "event_confidence": 0.95,
    "external_confirmation": {
      "confirmed": true,
      "result": "YES"
    }
  },
  "output_data": {
    "order_intent": {
      "side": "BUY",
      "price": 0.97,
      "size": 1000
    }
  },
  "reason": "All conditions met for near-resolution entry"
}
```

### Alertas

**Tipos de Alertas**:

1. **Confirmación Externa Faltante**:
   - Cuando Support Graph no puede obtener confirmación
   - Causa: API externa down, timeout, error

2. **Precio Fuera de Rango**:
   - Cuando precio se mueve fuera de `[0.95, 0.98]`
   - Estrategia no entra

3. **Exposición Límite Alcanzada**:
   - Cuando `exposure >= max_exposure`
   - Estrategia pausa temporalmente

4. **Orden Fallida**:
   - Cuando Execution Graph falla
   - Se activa compensación

---

## Arquitectura Técnica

### Componentes Principales

#### 1. Template System

**Archivo**: `backend/app/models/strategy_template.py`

- **Template**: `LIQUIDITY_NEAR_END_TEMPLATE`
- Define Decision Graph, Execution Graph, Support Graphs
- Usa placeholders: `{{external_source_id}}`, `{{event.id}}`

#### 2. Template Config

**Archivo**: `backend/app/models/strategy_template_config.py`

- **Config**: `LIQUIDITY_NEAR_END_CONFIG`
- Define campos del formulario
- Valida configuración del usuario
- Compila a Decision Graph

#### 3. Template Compiler

**Archivo**: `backend/app/core/strategy_engine/template_compiler.py`

- **Función**: `compile_liquidity_near_end(config)`
- Toma configuración del usuario
- Reemplaza placeholders
- Genera Decision Graph final

#### 4. Support Graph: Fetch External Source

**Archivo**: `backend/app/core/strategy_engine/nodes/fetch_external_source.py`

- **Nodo**: `FetchExternalSourceNode`
- Lee `source_id` de configuración
- Obtiene `ExternalDataSource` de DB
- Hace request HTTP a API externa
- Retorna datos al contexto

#### 5. State Cache

- **Clave**: `event.{event.id}.external_confirmation`
- **TTL**: 3600 segundos (1 hora)
- **Formato**: JSON con `confirmed`, `result`, `confidence`

### Flujo de Datos

```
1. User crea External Data Source
   ↓
2. User crea Strategy con external_source_id
   ↓
3. Scanner descubre Events de Markets enabled
   ↓
4. Event Watcher detecta event.state = FINISHED
   ↓
5. Support Graph se activa (trigger: event_state_change)
   ↓
6. FetchExternalSourceNode llama API externa
   ↓
7. Resultado se guarda en State Cache
   ↓
8. Decision Graph se activa (trigger: timer o event change)
   ↓
9. CollectStateNode lee del cache
   ↓
10. CheckEventFinishedNode valida condiciones
   ↓
11. CalculateSizeNode calcula tamaño
   ↓
12. BuildPlanNode crea Execution Plan
   ↓
13. EmitPlanNode envía a Risk Engine
   ↓
14. Risk Engine valida y aprueba
   ↓
15. Execution Graph ejecuta orden en Polymarket
```

---

## Resumen de Capacidades Actuales

### ✅ Implementado

1. **Creación de External Data Sources**:
   - ✅ Modelo de datos completo
   - ✅ API endpoints (`GET /api/external-data-sources`)
   - ✅ Configuración de `custom_api`, `pinnacle`, `bet365`
   - ✅ Health checks y estado

2. **Selección de Mercados**:
   - ✅ Filtrado por categoría, series, tags
   - ✅ Búsqueda por nombre
   - ✅ Toggle enable/disable
   - ✅ Selección en formulario de estrategia

3. **Configuración de Estrategia**:
   - ✅ Template `liquidity_near_end`
   - ✅ Formulario completo con todos los campos
   - ✅ Selección dinámica de External Data Sources
   - ✅ Configuración de capital, riesgo, condiciones de entrada

4. **Operación**:
   - ✅ Support Graph para confirmación externa
   - ✅ Decision Graph con validaciones
   - ✅ Execution Graph con compensación
   - ✅ State Cache para datos externos

5. **Monitoreo**:
   - ✅ Dashboard de estrategia
   - ✅ Decision traces
   - ✅ Métricas de performance

### ⚠️ Pendiente / Mejoras Futuras

1. **UI para crear External Data Sources**:
   - ⚠️ Actualmente solo existe API
   - 📋 Pendiente: Formulario en frontend

2. **Validación de External Data Sources**:
   - ⚠️ Health checks básicos
   - 📋 Pendiente: Validación de formato de respuesta

3. **Selección Avanzada de Mercados**:
   - ✅ Filtros básicos implementados
   - 📋 Pendiente: Filtros por múltiples criterios simultáneos

4. **Auto-Discovery de Markets**:
   - ✅ Scanner básico
   - 📋 Pendiente: Auto-asignación inteligente basada en categorías

---

## Conclusión

La estrategia **Near-Resolution Liquidity Provider** está **completamente implementada** desde el punto de vista técnico:

- ✅ Usuario puede crear External Data Sources (vía API)
- ✅ Usuario puede filtrar y seleccionar mercados
- ✅ Usuario puede configurar la estrategia completamente
- ✅ Sistema ejecuta la estrategia automáticamente
- ✅ Sistema monitorea y rastrea todas las decisiones

**Flujo completo funcional**: Desde la creación de cuentas externas hasta la ejecución de órdenes, todo el pipeline está operativo.

**Mejoras pendientes** son principalmente de UX (formularios en frontend) y optimizaciones (auto-discovery inteligente), pero la funcionalidad core está completa.

