# Configuración de Logging

## Resumen

La configuración de logging ha sido optimizada para reducir el ruido de librerías externas y hacer los logs más legibles.

## Configuración Actual

### Nivel de Logging por Defecto
- **Nivel general**: `INFO` (configurable desde `settings.log_level`)
- **Librerías externas**: `WARNING` (solo warnings y errores)

### Librerías Silenciadas

Las siguientes librerías están configuradas en nivel `WARNING` para reducir ruido:

- `httpcore` - Cliente HTTP de bajo nivel
- `httpx` - Cliente HTTP asíncrono
- `urllib3` - Cliente HTTP (usado por requests)
- `asyncio` - Event loop de Python
- `uvicorn.access` - Logs de acceso HTTP
- `uvicorn` - Servidor ASGI (nivel INFO)

### Configuración desde Variables de Entorno

Puedes cambiar el nivel de logging desde `.env`:

```env
LOG_LEVEL=INFO  # Opciones: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Ejemplos

### Ver solo errores y warnings
```env
LOG_LEVEL=WARNING
```

### Ver todo (incluyendo debug de la aplicación)
```env
LOG_LEVEL=DEBUG
```

**Nota**: Incluso con `DEBUG`, las librerías externas (`httpcore`, `httpx`, etc.) seguirán en `WARNING` para mantener los logs legibles.

### Ver solo información importante
```env
LOG_LEVEL=INFO
```

## Logs de la Aplicación

Los logs de nuestra aplicación (`app.*`) respetan el nivel configurado en `LOG_LEVEL`.

Para ver logs de debug de la aplicación específicamente:

```python
# En el código, puedes usar:
logger.debug("Mensaje de debug")
logger.info("Mensaje informativo")
logger.warning("Advertencia")
logger.error("Error")
```

## Cambios Realizados

1. ✅ Nivel por defecto cambiado de `DEBUG` a `INFO`
2. ✅ Librerías externas configuradas en `WARNING`
3. ✅ Configuración respeta `settings.log_level`
4. ✅ Logs de acceso HTTP reducidos

## Resultado

Antes: Logs con muchos mensajes DEBUG de `httpcore` y `httpx` que hacían difícil leer información importante.

Después: Logs limpios con solo información relevante (INFO, WARNING, ERROR) de la aplicación, sin ruido de librerías externas.

