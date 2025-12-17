# Plan de Ejecución Unificado - Sistema de Estrategias Basado en Grafos

## Objetivo

Definir el orden exacto de ejecución combinando la preparación de migración y la implementación del nuevo sistema.

---

## Orden de Ejecución Recomendado

### **ETAPA 1: Preparación Mínima** (1-2 días)
**Objetivo**: Crear la estructura base sin romper nada

#### 1.1. Adaptar OrderIntent
- [ ] Modificar `backend/app/core/strategy/models.py`
  - Agregar `strategy_id: Optional[UUID] = None` a `OrderIntent`
  - Agregar `graph_execution_id: Optional[UUID] = None` a `OrderIntent`
  - **Importante**: Campos opcionales, no rompe compatibilidad

#### 1.2. Crear Estructura del Nuevo Módulo
- [ ] Crear directorio `backend/app/core/strategy_engine/`
- [ ] Crear archivos vacíos:
  ```
  strategy_engine/
  ├── __init__.py
  ├── models.py (por ahora vacío, solo imports)
  ├── control_loop.py (stub)
  ├── graph_runtime.py (stub)
  ├── strategy_engine.py (stub)
  ├── state_cache_service.py (stub)
  └── nodes/
      ├── __init__.py
      └── base.py (stub)
  ```

#### 1.3. Setup Básico de Models
- [ ] En `strategy_engine/models.py`:
  ```python
  # Reutilizar modelos existentes
  from app.core.strategy.models import (
      OrderIntent,  # Ya tiene los campos nuevos
      MarketState,
      EventState
  )
  
  # Exportar para uso futuro
  __all__ = ["OrderIntent", "MarketState", "EventState"]
  ```

**Resultado**: Estructura lista, sin romper nada, código legacy sigue funcionando.

---

### **ETAPA 2: Base de Datos** (2-3 días)
**Objetivo**: Crear las tablas necesarias

#### 2.1. Crear Modelos SQLAlchemy
- [ ] `backend/app/models/strategy.py` - Modelo Strategy
- [ ] `backend/app/models/graph_node_definition.py` - Catálogo de nodos
- [ ] `backend/app/models/graph_execution.py` - Trazabilidad
- [ ] `backend/app/models/state_cache.py` - Cache de estado
- [ ] `backend/app/models/strategy_event.py` - Asignación eventos
- [ ] `backend/app/models/execution_intent.py` - Intents (si no existe)
- [ ] `backend/app/models/strategy_metric.py` - Métricas
- [ ] `backend/app/models/external_data_source.py` - Fuentes externas

#### 2.2. Crear Migración Alembic
- [ ] `backend/alembic/versions/010_create_strategies_graph_system.py`
- [ ] Ejecutar migración: `alembic upgrade head`
- [ ] Verificar tablas creadas

#### 2.3. Seed de Nodos Predefinidos
- [ ] `backend/scripts/seed_graph_node_definitions.py`
- [ ] Ejecutar script para poblar `graph_node_definitions`

**Resultado**: Base de datos lista, modelos creados, nodos disponibles.

---

### **ETAPA 3: Backend Core - State Cache** (1-2 días)
**Objetivo**: Implementar el State Cache Service (fundación)

#### 3.1. State Cache Service
- [ ] `backend/app/core/strategy_engine/state_cache_service.py`
- [ ] Implementar `get()`, `set()`, `get_many()`
- [ ] Cache en memoria + persistencia DB
- [ ] Tests unitarios

**Resultado**: State Cache funcionando, Support Graphs pueden escribir, Decision Graph puede leer.

---

### **ETAPA 4: Backend Core - Graph Runtime** (3-4 días)
**Objetivo**: Implementar el runtime de ejecución de grafos

#### 4.1. Base de Nodos
- [ ] `backend/app/core/strategy_engine/nodes/base.py`
  - Clase `GraphNode` (ABC)
  - Clases `NodeResult`, `ConditionalResult`, `ExecutionIntentResult`

#### 4.2. Nodos Básicos (Hot Path)
- [ ] `backend/app/core/strategy_engine/nodes/collect_state.py`
- [ ] `backend/app/core/strategy_engine/nodes/edge_and_risk_check.py`
- [ ] `backend/app/core/strategy_engine/nodes/calculate_order_size.py`
- [ ] `backend/app/core/strategy_engine/nodes/emit_execution_intent.py`
- [ ] `backend/app/core/strategy_engine/nodes/noop.py`

#### 4.3. Graph Runtime
- [ ] `backend/app/core/strategy_engine/graph_runtime.py`
  - `execute_graph()` - Ejecuta un grafo
  - `_get_next_node()` - Determina siguiente nodo
  - Registro de nodos
- [ ] Tests unitarios

**Resultado**: Puedo ejecutar grafos JSON, nodos funcionan, intents se generan.

---

### **ETAPA 5: Backend Core - Strategy Engine** (2-3 días)
**Objetivo**: Orquestador principal

#### 5.1. Strategy Engine
- [ ] `backend/app/core/strategy_engine/strategy_engine.py`
  - `initialize()`
  - `execute_decision_graph()`
  - `execute_support_graph()`
- [ ] Tests unitarios

#### 5.2. Control Loop
- [ ] `backend/app/core/strategy_engine/control_loop.py`
  - `start()` - Inicia el loop
  - `tick()` - Tick principal
  - `load_active_strategies()` - Carga desde DB
  - `_should_observe()` - Verifica timing
  - `_check_triggers()` - Verifica triggers
  - `_execute_support_graphs()` - Ejecuta support graphs async
- [ ] Tests unitarios

**Resultado**: Strategy Engine completo, Control Loop funcionando, puede ejecutar estrategias desde DB.

---

### **ETAPA 6: Backend Core - Support Graphs** (2-3 días)
**Objetivo**: Nodos para cold path

#### 6.1. Nodos de Support Graphs
- [ ] `backend/app/core/strategy_engine/nodes/fetch_external_source.py`
- [ ] `backend/app/core/strategy_engine/nodes/update_state_cache.py`
- [ ] `backend/app/core/strategy_engine/nodes/validate_with_ai.py` (opcional, para futuro)
- [ ] `backend/app/core/strategy_engine/nodes/log.py`

#### 6.2. Sistema de Conectores (Plugins)
- [ ] `backend/app/core/connectors/base.py` - Clase base
- [ ] `backend/app/core/connectors/registry.py` - Registro
- [ ] Tests unitarios

**Resultado**: Support Graphs pueden ejecutarse, conectores funcionan.

---

### **ETAPA 7: APIs REST** (3-4 días)
**Objetivo**: Endpoints para frontend

#### 7.1. API de Estrategias
- [ ] `backend/app/api/strategies.py`
  - `GET /strategies` - Lista estrategias
  - `POST /strategies` - Crear estrategia
  - `GET /strategies/{id}` - Detalle
  - `PUT /strategies/{id}` - Actualizar
  - `POST /strategies/{id}/activate` - Activar
  - `POST /strategies/{id}/deactivate` - Desactivar
  - `GET /strategies/{id}/graph` - Obtener grafo
  - `PUT /strategies/{id}/graph` - Actualizar grafo
  - `GET /strategies/{id}/events` - Eventos asignados
  - `POST /strategies/{id}/events` - Asignar evento
  - `GET /strategies/{id}/intents` - Intents generados
  - `GET /strategies/{id}/metrics` - Métricas

#### 7.2. API de Nodos
- [ ] `backend/app/api/graph_nodes.py`
  - `GET /graph-nodes` - Lista nodos disponibles
  - `GET /graph-nodes/{node_type}` - Detalle de nodo

#### 7.3. API de State Cache
- [ ] `backend/app/api/state_cache.py`
  - `GET /state-cache` - Obtener valores

#### 7.4. Registrar Routers
- [ ] Agregar routers a `backend/app/main.py`

**Resultado**: APIs funcionando, frontend puede interactuar.

---

### **ETAPA 8: Integración con Main Loop** (1-2 días)
**Objetivo**: Integrar sin romper el sistema actual

#### 8.1. Feature Flag
- [ ] Agregar `USE_GRAPH_STRATEGIES` a `backend/app/settings.py`
- [ ] Leer desde variable de entorno

#### 8.2. Integración Condicional
- [ ] Modificar `backend/app/main.py`:
  ```python
  if settings.USE_GRAPH_STRATEGIES:
      from app.core.strategy_engine import StrategyEngine
      strategy_engine = StrategyEngine()
      strategy_engine.initialize(db)
      # Iniciar Control Loop en background
      asyncio.create_task(strategy_engine.control_loop.start(db))
  else:
      # Código actual (legacy)
      from app.core.strategy import Strategy
      strategy = Strategy()
      # ... código actual ...
  ```

#### 8.3. Conectar Intents con Risk Engine
- [ ] El Control Loop genera intents
- [ ] Los intents se pasan al Risk Engine (igual que antes)
- [ ] Verificar que Risk Engine sigue funcionando

**Resultado**: Sistema nuevo integrado, feature flag permite activar/desactivar.

---

### **ETAPA 9: Testing y Validación** (2-3 días)
**Objetivo**: Asegurar que todo funciona

#### 9.1. Tests Unitarios
- [ ] Tests de State Cache Service
- [ ] Tests de Graph Runtime
- [ ] Tests de Nodos
- [ ] Tests de Strategy Engine
- [ ] Tests de Control Loop

#### 9.2. Tests de Integración
- [ ] Test completo: Crear estrategia → Activar → Generar intents
- [ ] Test de Support Graphs
- [ ] Test de APIs

#### 9.3. Estrategia de Prueba
- [ ] Crear una estrategia simple en DB
- [ ] Activar con feature flag
- [ ] Verificar que genera intents
- [ ] Verificar que Risk Engine los procesa

**Resultado**: Sistema probado, listo para usar.

---

### **ETAPA 10: Frontend - Constructor de Grafos** (5-7 días)
**Objetivo**: UI para crear estrategias

#### 10.1. Instalar Dependencias
- [ ] Instalar React Flow: `npm install reactflow`
- [ ] Configurar TypeScript types

#### 10.2. Componente GraphBuilder
- [ ] `frontend/components/GraphBuilder/GraphBuilder.tsx`
- [ ] `frontend/components/GraphBuilder/NodeConfigPanel.tsx`
- [ ] `frontend/components/GraphBuilder/NodePalette.tsx`
- [ ] Funciones de conversión: `graphToReactFlow()`, `reactFlowToGraph()`

#### 10.3. Página de Estrategias
- [ ] `frontend/app/strategies/page.tsx` - Lista de estrategias
- [ ] `frontend/app/strategies/create/page.tsx` - Crear estrategia
- [ ] `frontend/app/strategies/[id]/page.tsx` - Detalle
- [ ] `frontend/app/strategies/[id]/configure/page.tsx` - Configurar grafo

**Resultado**: Frontend completo, usuarios pueden crear estrategias visualmente.

---

### **ETAPA 11: Frontend - Visualización** (3-4 días)
**Objetivo**: Ver operativa y métricas

#### 11.1. Página de Métricas
- [ ] `frontend/app/strategies/[id]/metrics/page.tsx`
- [ ] Gráficos de PnL, volumen, win rate
- [ ] Tabla de intents

#### 11.2. Comparación de Estrategias
- [ ] `frontend/app/strategies/compare/page.tsx`
- [ ] Tabla comparativa
- [ ] Gráficos superpuestos

**Resultado**: Visualización completa.

---

### **ETAPA 12: Migración y Limpieza** (1-2 días)
**Objetivo**: Eliminar código legacy

#### 12.1. Migrar Estrategias Existentes (si las hay)
- [ ] Crear estrategias equivalentes usando grafos
- [ ] Validar que generan mismos intents

#### 12.2. Eliminar Código Legacy
- [ ] Eliminar `backend/app/core/strategy/strategy.py`
- [ ] Eliminar `StrategyConfig` de `models.py` (o deprecar)
- [ ] Eliminar `NoEntryReason` (opcional)
- [ ] Actualizar `backend/app/core/strategy/__init__.py`

#### 12.3. Eliminar Feature Flag
- [ ] Remover `USE_GRAPH_STRATEGIES`
- [ ] Eliminar código condicional en `main.py`
- [ ] Dejar solo el nuevo sistema

#### 12.4. Deprecar Config Service
- [ ] Marcar `get_strategy_config()` como deprecated
- [ ] Agregar warning

**Resultado**: Código limpio, solo sistema nuevo.

---

## Resumen del Orden

```
ETAPA 1: Preparación Mínima (estructura)
    ↓
ETAPA 2: Base de Datos (modelos, migraciones)
    ↓
ETAPA 3: State Cache (fundación)
    ↓
ETAPA 4: Graph Runtime (ejecución de grafos)
    ↓
ETAPA 5: Strategy Engine + Control Loop (orquestación)
    ↓
ETAPA 6: Support Graphs (cold path)
    ↓
ETAPA 7: APIs REST (interfaz backend-frontend)
    ↓
ETAPA 8: Integración Main Loop (feature flag)
    ↓
ETAPA 9: Testing (validación)
    ↓
ETAPA 10: Frontend Constructor (UI creación)
    ↓
ETAPA 11: Frontend Visualización (métricas)
    ↓
ETAPA 12: Migración y Limpieza (eliminar legacy)
```

---

## Tiempo Estimado Total

- **Backend Core**: ~15-20 días
- **APIs**: ~3-4 días
- **Frontend**: ~8-11 días
- **Testing y Migración**: ~3-5 días

**Total**: ~29-40 días (1.5-2 meses)

---

## Puntos Críticos

### ✅ **Hacer Primero (Fundación)**
1. Adaptar `OrderIntent` (ETAPA 1.1)
2. Crear estructura (ETAPA 1.2)
3. Base de datos (ETAPA 2)
4. State Cache (ETAPA 3)

### ⚠️ **No Saltar Etapas**
- No implementar Control Loop sin Graph Runtime
- No implementar APIs sin Strategy Engine
- No hacer frontend sin APIs

### 🔄 **Iteraciones**
- Cada etapa debe ser testeable
- Probar después de cada etapa
- No acumular deuda técnica

---

## Recomendación Final

**Empezar con ETAPA 1 y ETAPA 2** (Preparación + Base de Datos).

Esto nos da:
- ✅ Estructura lista
- ✅ Base de datos funcionando
- ✅ Sin romper código existente
- ✅ Base sólida para el resto

Luego continuar secuencialmente con las demás etapas.

---

## Checklist de Inicio

Antes de empezar, verificar:

- [ ] Código actual funciona (tests pasan)
- [ ] Base de datos accesible
- [ ] Entorno de desarrollo configurado
- [ ] Documentación leída y entendida
- [ ] Plan de ejecución revisado

**¿Listo para empezar?** → Comenzar con ETAPA 1.

