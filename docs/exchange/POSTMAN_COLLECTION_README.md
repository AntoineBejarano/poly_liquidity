# Colección de Postman para Polymarket

Esta colección contiene todos los endpoints necesarios para testear la integración completa con Polymarket.

## Importar la Colección

1. Abre Postman
2. Click en "Import" (esquina superior izquierda)
3. Selecciona el archivo `polymarket-postman-collection.json`
4. La colección aparecerá en tu workspace

## Configurar Variables

Antes de usar la colección, configura las variables de entorno en Postman:

1. Click en la colección "Polymarket Integration Tests"
2. Ve a la pestaña "Variables"
3. Configura las siguientes variables:

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `base_url` | URL del backend | `http://localhost:8000` |
| `event_id` | ID de un evento (se obtiene de 2.1) | `0x...` |
| `market_id` | ID de un mercado (se obtiene de 2.2) | `0x...` |
| `slug` | Slug de un mercado | `will-trump-win-2024` |
| `order_id` | ID de una orden (se obtiene de 3.2 o 4.1) | `0x...` |
| `token_id` | ID de un token CLOB | `0x...` |
| `condition_id` | ID de condición del mercado | `0x...` |
| `timestamp` | Unix timestamp | `1704067200` |

## Uso por Fases

### Fase 1: Configuración

1. **1.1 Verificar Status de Conexión**
   - Verifica que las variables de entorno estén configuradas
   - Verifica estado del cliente CLOB
   - Verifica disponibilidad de APIs

2. **1.2 Test Autenticación**
   - Prueba la autenticación con CLOB API
   - Verifica que las credenciales funcionan

### Fase 2: Datos Públicos

1. **2.1 Listar Events**
   - Obtén una lista de eventos activos
   - Copia un `event_id` de la respuesta y guárdalo en la variable `event_id`

2. **2.2 Obtener Event por ID**
   - Usa el `event_id` de 2.1
   - Obtén información completa del evento
   - Copia un `market_id` de los markets del evento

3. **2.3 Obtener Market por ID**
   - Usa el `market_id` de 2.2
   - Obtén información completa del mercado
   - Copia los `clobTokenIds` si los necesitas

4. **2.4 Obtener Market por Slug**
   - Usa un slug conocido (ej: `will-trump-win-2024`)

5. **2.5 Buscar**
   - Busca eventos/markets por query

6. **2.6 Obtener Orderbook**
   - Usa el `market_id` de 2.2
   - Obtén el orderbook completo del mercado

7. **2.7 Obtener Precios**
   - Usa el `market_id` de 2.2
   - Obtén precios (bid, ask, midpoint)

### Fase 3: Datos de Cuenta

**IMPORTANTE**: Estos endpoints requieren autenticación (PRIVATE_KEY y FUNDER_ADDRESS configuradas).

1. **3.1 Obtener Balance**
   - Obtén el balance USDC de tu cuenta

2. **3.2 Listar Órdenes Abiertas**
   - Lista todas tus órdenes abiertas
   - Copia un `order_id` si quieres testear otros endpoints

3. **3.3 Listar Órdenes con Filtros**
   - Filtra órdenes por market o token_id

4. **3.4 Obtener Orden Específica**
   - Usa un `order_id` de 3.2

5. **3.5 Listar Trades**
   - Lista tus trades históricos

6. **3.6 Listar Trades con Filtros**
   - Filtra trades por market o rango de tiempo

7. **3.7 Verificar Order Scoring**
   - Verifica si una orden está "scoring" (elegible para recompensas)

### Fase 4: Trading

**ADVERTENCIA**: Estos endpoints crean/cancelan órdenes REALES en Polymarket. Usa con precaución.

1. **4.1 Crear Limit Order BUY**
   - Crea una orden limit de compra
   - Asegúrate de tener un `token_id` válido
   - Ajusta `price` y `size` según necesites

2. **4.2 Crear Limit Order SELL**
   - Crea una orden limit de venta

3. **4.3 Crear Market Order**
   - Crea una market order (se ejecuta inmediatamente)
   - **MUY PELIGROSO**: Se ejecuta al instante

4. **4.4 Cancelar Orden**
   - Cancela una orden específica
   - Usa un `order_id` de 3.2 o 4.1/4.2

5. **4.5 Cancelar Todas las Órdenes**
   - **MUY PELIGROSO**: Cancela TODAS las órdenes abiertas

## Flujo de Trabajo Recomendado

1. **Primero**: Ejecuta Fase 1 para verificar configuración
2. **Segundo**: Ejecuta Fase 2 para obtener datos públicos
3. **Tercero**: Si tienes credenciales, ejecuta Fase 3 para ver datos de cuenta
4. **Último**: Solo si estás seguro, ejecuta Fase 4 para trading

## Troubleshooting

### Error 503: "CLOB client not initialized"
- Verifica que `PRIVATE_KEY` y `FUNDER_ADDRESS` estén configuradas en el backend
- Verifica que el backend esté corriendo

### Error 429: "Rate limit exceeded"
- Espera unos segundos antes de volver a intentar
- El sistema tiene rate limiting automático

### Error 404: "Not found"
- Verifica que los IDs que estás usando sean correctos
- Algunos recursos pueden no existir o haber sido eliminados

### Variables no se actualizan
- Asegúrate de guardar las variables después de editarlas
- Algunas variables se pueden actualizar automáticamente desde las respuestas usando scripts de Postman

## Scripts de Postman (Opcional)

Puedes agregar scripts en Postman para actualizar variables automáticamente:

```javascript
// En la pestaña "Tests" de un request:
// Guardar event_id de la respuesta
if (pm.response.code === 200) {
    const response = pm.response.json();
    if (response[0] && response[0].id) {
        pm.collectionVariables.set("event_id", response[0].id);
    }
}
```

## Referencias

- [Documentación de Integración](./polymarket-integration.md)
- [Polymarket CLOB API Docs](https://docs.polymarket.com)

