# Guía de Plantillas de Estrategias

Este documento explica cómo usar las plantillas de estrategias predefinidas y cómo crear estrategias comunes.

## Plantillas Disponibles

### 1. Near-Resolution Liquidity Provider

**Qué hace:**
- Detecta cuando un evento ya terminó en el mundo real pero aún no ha sido resuelto por Polymarket
- Provee liquidez comprando a usuarios que quieren salir antes de la resolución
- Captura un diferencial de precio (ej: compra a 0.98, resuelve a 1.00 = 2% ganancia)

**Cuándo entra:**
- Evento terminado y confirmado por fuentes externas
- Precio en Polymarket entre 0.95 y 0.98
- Exposición dentro de límites de riesgo

**Cómo configurarla:**
1. Selecciona la plantilla "Near-Resolution Liquidity Provider"
2. Configura la fuente externa de confirmación de eventos (Support Graph)
3. Ajusta los límites de precio y tamaño de orden en el nodo `check_price_range` y `calculate_size`
4. Asigna eventos a la estrategia

**Support Graph necesario:**
- `confirm_event_result`: Obtiene confirmación del resultado del evento desde una fuente externa

---

### 2. Surebet Polymarket-Pinnacle

**Qué hace:**
- Detecta diferencias de precio entre Polymarket y Pinnacle
- Compra en el mercado más barato y vende en el más caro
- Captura el arbitraje puro

**Cuándo entra:**
- Existe una oportunidad de surebet (profit > 2%)
- Precio en Polymarket diferente al de Pinnacle
- Exposición dentro de límites

**Cómo configurarla:**
1. Selecciona la plantilla "Surebet Polymarket-Pinnacle"
2. Configura la fuente externa de Pinnacle (Support Graph)
3. Ajusta el porcentaje de profit mínimo requerido
4. Configura el tamaño de orden como porcentaje del bank

**Support Graph necesario:**
- `fetch_pinnacle_odds`: Obtiene las odds de Pinnacle cada 10 segundos
- Calcula si existe oportunidad de surebet

---

## Cómo Crear una Estrategia desde una Plantilla

### Paso 1: Seleccionar Plantilla
1. Ve a `/strategies/create`
2. En el paso 0, selecciona una plantilla
3. La plantilla carga automáticamente:
   - Decision Graph completo
   - Support Graphs necesarios
   - Configuración de riesgo básica
   - Nombre y descripción

### Paso 2: Personalizar
1. **Información Básica**: Ajusta nombre, descripción y tags
2. **Decision Graph**: 
   - Revisa los nodos y sus condiciones
   - Ajusta los valores de los checks (precios, porcentajes)
   - Modifica el tamaño de orden si es necesario
3. **Support Graphs**:
   - Configura las fuentes externas (IDs de ExternalDataSource)
   - Ajusta los triggers (intervalos, condiciones)
4. **Risk Config**: Ajusta límites de exposición y tamaño de orden

### Paso 3: Configurar Fuentes Externas
Antes de activar la estrategia, necesitas:
1. Crear las External Data Sources necesarias:
   - Para Liquidity Near End: fuente de confirmación de eventos
   - Para Surebet: fuente de odds de Pinnacle
2. Obtener los IDs de estas fuentes
3. Actualizar los Support Graphs con los IDs correctos

---

## Ejemplo: Configurar Liquidity Near End

### 1. Crear External Data Source para Confirmación

```json
{
  "name": "Sports API - Event Results",
  "connector_type": "custom_api",
  "connector_config": {
    "base_url": "https://api.sports.com",
    "api_key_name": "X-API-Key",
    "api_key_value": "tu-api-key",
    "method": "GET"
  }
}
```

### 2. Obtener el ID de la fuente
- Ve a la página de External Data Sources
- Copia el ID de la fuente creada

### 3. Actualizar Support Graph
En el Support Graph `confirm_event_result`, actualiza:
```json
{
  "source_id": "UUID-de-tu-fuente-externa",
  "endpoint": "/api/event/result",
  "params": {
    "event_id": "{{event.id}}"
  }
}
```

### 4. Ajustar Condiciones del Decision Graph
En el nodo `check_price_range`, ajusta los límites:
```json
{
  "conditions": [
    {
      "field": "market_state.last_price",
      "operator": ">=",
      "value": 0.94  // Precio mínimo
    },
    {
      "field": "market_state.last_price",
      "operator": "<=",
      "value": 0.97  // Precio máximo
    }
  ]
}
```

### 5. Configurar Tamaño de Orden
En el nodo `calculate_size`:
```json
{
  "method": "fixed_range",
  "min": 200,   // Mínimo $200
  "max": 3000   // Máximo $3000
}
```

---

## Ejemplo: Configurar Surebet Polymarket-Pinnacle

### 1. Crear External Data Source para Pinnacle

```json
{
  "name": "Pinnacle Odds API",
  "connector_type": "custom_api",
  "connector_config": {
    "base_url": "https://api.pinnacle.com",
    "api_key_name": "Authorization",
    "api_key_value": "Bearer tu-token",
    "method": "GET"
  }
}
```

### 2. Actualizar Support Graph
En `fetch_pinnacle_odds`, actualiza:
```json
{
  "source_id": "UUID-de-pinnacle",
  "endpoint": "/v1/odds",
  "params": {
    "sportId": "29",
    "eventIds": "{{event.external_event_id}}"
  }
}
```

### 3. Ajustar Profit Mínimo
En el nodo `check_surebet_opportunity`:
```json
{
  "conditions": [
    {
      "field": "external_data.surebet_opportunity.profit_percentage",
      "operator": ">=",
      "value": 0.03  // Mínimo 3% de profit
    }
  ]
}
```

---

## Consejos

1. **Empieza con plantillas**: Usa las plantillas como base, no intentes crear desde cero
2. **Prueba con eventos pequeños**: Activa la estrategia con eventos de bajo valor primero
3. **Monitorea las ejecuciones**: Revisa los Graph Executions para ver qué está pasando
4. **Ajusta gradualmente**: Haz cambios pequeños y prueba cada uno
5. **Documenta tus cambios**: Anota qué modificaste y por qué

---

## Troubleshooting

### La estrategia no genera intents
- Verifica que los eventos asignados estén en estado "ACTIVE"
- Revisa las condiciones del Decision Graph
- Verifica que el State Cache tenga los datos necesarios

### Support Graph no se ejecuta
- Verifica que el trigger esté configurado correctamente
- Revisa que la fuente externa esté activa
- Verifica los logs de ejecución del Support Graph

### Error al obtener datos externos
- Verifica que el External Data Source esté configurado correctamente
- Revisa que la API key sea válida
- Verifica que el endpoint sea correcto

