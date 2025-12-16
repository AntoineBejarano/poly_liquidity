# Frontend: Configuración y Decision Traces

## Resumen

Implementación completa del frontend para consumir los endpoints de configuración del sistema y decision traces, incluyendo mejoras visuales con gráficos y timeline.

## Páginas Implementadas

### 1. Configuración del Sistema (`/settings/config`)

**Características:**
- Muestra todas las configuraciones agrupadas por categoría
- Tabla interactiva con edición inline
- Protección de parámetros:
  - `is_readonly`: Badge visual y bloqueo de edición
  - `requires_confirmation`: Diálogo de confirmación antes de cambios críticos
- Validación de tipos y valores (min/max)
- Filtrado por categoría con tabs
- Modo demo cuando el backend no está conectado

**Endpoints consumidos:**
- `GET /system/config?include_metadata=true` - Obtener configuración completa
- `PUT /system/config/{key}` - Actualizar parámetro

### 2. Decision Traces (`/decision-traces`)

**Características:**
- Lista de traces con paginación
- Filtros avanzados:
  - Componente (scanner, event_engine, strategy, risk, execution)
  - Etapa (SCAN, EVENT_CONFIRMATION, STRATEGY, RISK, EXECUTION)
  - Decisión (APPROVED, REJECTED, ADJUSTED, CANCELLED, SIMULATED)
  - Trace ID (UUID)
- **Timeline Visual**: Componente `DecisionTraceTimeline` que muestra el pipeline completo
- **Gráficos de Estadísticas**: Componente `DecisionTraceStats` con:
  - Decisiones por etapa (barras de progreso)
  - Distribución de decisiones (gráfico de barras)
  - Métricas de rendimiento (latencia promedio, mín, máx, confianza)
- Vista de pipeline completo con detalles expandibles

**Endpoints consumidos:**
- `GET /system/decision-traces` - Listar traces con filtros
- `GET /system/decision-traces/{trace_id}` - Obtener pipeline completo

## Componentes Creados

### DecisionTraceTimeline

Timeline visual que muestra todas las etapas de una decisión en orden cronológico:
- Línea de tiempo vertical con puntos de color por etapa
- Cards con información detallada de cada etapa
- Colores diferenciados por etapa y decisión
- Información de latencia y confianza
- Detalles expandibles (input/output data)

### DecisionTraceStats

Gráficos y estadísticas de los traces:
- **Decisiones por Etapa**: Barras de progreso mostrando approved/rejected por etapa
- **Distribución de Decisiones**: Gráfico de barras con porcentajes
- **Métricas de Rendimiento**: Latencia (promedio, mín, máx) y confianza promedio

## Navegación

- Agregado "Decision Traces" al Sidebar (icono: 🔍)
- Link corregido en Settings page (`/settings/config`)

## Testing

Script de prueba creado: `backend/test_endpoints.py`
- Prueba endpoints de health, config y decision traces
- Usa httpx (async) para compatibilidad con el proyecto
- Maneja errores de conexión gracefully

## Características Visuales

- **Diseño consistente**: Usa las mismas clases CSS que otras páginas
- **Colores por etapa**: Cada etapa tiene un color único
- **Colores por decisión**: Verde (APPROVED), Rojo (REJECTED), Amarillo (ADJUSTED), etc.
- **Timeline interactivo**: Visualización clara del flujo de decisión
- **Gráficos nativos**: Sin dependencias adicionales, usando SVG y CSS

## Próximos Pasos Sugeridos

1. **Exportación**: Agregar funcionalidad para exportar traces a CSV/JSON
2. **Búsqueda avanzada**: Búsqueda por texto en razones y metadata
3. **Filtros guardados**: Permitir guardar combinaciones de filtros
4. **Comparación de traces**: Comparar dos traces lado a lado
5. **Alertas**: Notificaciones cuando se detectan patrones anómalos


