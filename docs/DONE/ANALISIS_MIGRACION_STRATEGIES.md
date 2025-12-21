# Análisis y Plan de Migración - Sistema de Estrategias Basado en Grafos

## Objetivo

Analizar el código existente de estrategias y definir qué eliminar, qué reutilizar y cómo migrar al nuevo sistema basado en grafos.

---

## 1. Análisis del Código Existente

### 1.1. Estructura Actual

```
backend/app/core/strategy/
├── __init__.py          # Exporta Strategy, OrderIntent, etc.
├── strategy.py          # Clase Strategy con lógica hardcodeada (728 líneas)
└── models.py            # OrderIntent, MarketState, EventState, StrategyConfig
```

### 1.2. Componentes Actuales

#### ✅ **REUTILIZAR (con adaptaciones)**

**1. `OrderIntent` (models.py)**
- **Estado**: ✅ Útil, pero necesita adaptación
- **Uso actual**: Output del Strategy Engine → Input del Risk Engine
- **Cambios necesarios**:
  - Agregar `strategy_id: UUID` (nuevo)
  - Agregar `graph_execution_id: UUID` (nuevo, opcional)
  - Mantener `event_id`, `outcome`, `side`, `price`, `size`, `reason`, `trace_id`
  - El `metadata` puede contener el contexto completo del grafo
- **Decisión**: ✅ **REUTILIZAR** - Es el contrato con Risk Engine

**2. `MarketState` (models.py)**
- **Estado**: ✅ Útil para State Cache
- **Uso actual**: Input del Strategy Engine
- **Cambios necesarios**:
  - Ninguno, se puede usar tal cual
  - Se almacenará en State Cache como `event.{event_id}.market_state`
- **Decisión**: ✅ **REUTILIZAR** - Perfecto para State Cache

**3. `EventState` (models.py)**
- **Estado**: ✅ Útil para State Cache
- **Uso actual**: Input del Strategy Engine
- **Cambios necesarios**:
  - Ninguno, se puede usar tal cual
  - Se almacenará en State Cache como `event.{event_id}.event_state`
- **Decisión**: ✅ **REUTILIZAR** - Perfecto para State Cache

#### ❌ **ELIMINAR (será reemplazado)**

**1. `Strategy` (strategy.py)**
- **Estado**: ❌ Lógica hardcodeada, incompatible con grafos
- **Problemas**:
  - Lógica de decisión hardcodeada en métodos privados
  - No es declarativo
  - No soporta múltiples estrategias
  - No es extensible
- **Decisión**: ❌ **ELIMINAR** - Será reemplazado por `StrategyEngine` + grafos

**2. `StrategyConfig` (models.py)**
- **Estado**: ❌ Será reemplazado por configuración en grafos
- **Problemas**:
  - Configuración global, no por estrategia
  - No es declarativo
- **Decisión**: ❌ **ELIMINAR** - La configuración irá en `risk_config` y `decision_graph`

**3. `NoEntryReason` (models.py)**
- **Estado**: ⚠️ Opcional, puede eliminarse
- **Uso actual**: Solo para logging
- **Decisión**: ⚠️ **OPCIONAL** - Se puede eliminar o mantener para compatibilidad

### 1.3. Integraciones Actuales

#### **Main Loop (main.py)**
```python
# Línea 130-131
strategy = Strategy()

# Línea 229
intents = await strategy.tick()

# Línea 265
_approved_intents = await risk_engine.tick(intents)
```

**Cambios necesarios**:
- Reemplazar `Strategy()` por `StrategyEngine()`
- El nuevo `StrategyEngine` tiene un `ControlLoop` que corre en paralelo
- Los intents se generan desde grafos, no desde `strategy.tick()`

#### **Risk Engine (risk_engine.py)**
```python
# Línea 12
from app.core.strategy.models import OrderIntent

# Línea 542
async def tick(self, intents: List[OrderIntent]) -> List[ApprovedOrderIntent]:
```

**Cambios necesarios**:
- ✅ **NINGUNO** - Risk Engine sigue recibiendo `List[OrderIntent]`
- El contrato se mantiene igual
- Solo cambia de dónde vienen los intents (grafos en lugar de clase Strategy)

#### **Config Service (config_service.py)**
```python
# Línea 130-131
from app.core.strategy.models import StrategyConfig
self._strategy_config = StrategyConfig(...)

# Línea 241
def get_strategy_config(self):
    return self._strategy_config
```

**Cambios necesarios**:
- ⚠️ **DEPRECAR** - `get_strategy_config()` ya no se usará
- Las estrategias nuevas cargan su configuración desde DB (grafos)
- Mantener por compatibilidad temporal si hay código que lo usa

#### **Decision Trace Service**
```python
# Usa "strategy" como component
decision_trace_service.log_decision(
    component="strategy",
    decision_stage="STRATEGY",
    ...
)
```

**Cambios necesarios**:
- ✅ **MANTENER** - Sigue siendo "strategy"
- Agregar `graph_execution_id` a los traces cuando aplique

---

## 2. Plan de Migración

### FASE 0: Preparación (ANTES de implementar)

#### 2.1. Crear Nuevo Módulo (sin tocar el existente)

```
backend/app/core/strategy_engine/    # NUEVO módulo
├── __init__.py
├── control_loop.py
├── graph_runtime.py
├── strategy_engine.py
├── state_cache_service.py
├── nodes/
│   ├── __init__.py
│   ├── base.py
│   ├── collect_state.py
│   ├── edge_and_risk_check.py
│   ├── calculate_order_size.py
│   └── emit_execution_intent.py
└── models.py  # Nuevos modelos (Strategy, GraphExecution, etc.)
```

**Ventaja**: Podemos desarrollar el nuevo sistema sin romper el existente.

#### 2.2. Adaptar OrderIntent

**Archivo**: `backend/app/core/strategy_engine/models.py`

```python
from app.core.strategy.models import OrderIntent as BaseOrderIntent
from uuid import UUID

class OrderIntent(BaseOrderIntent):
    """OrderIntent extendido para el nuevo sistema."""
    strategy_id: Optional[UUID] = None
    graph_execution_id: Optional[UUID] = None
    
    # Mantener todos los campos originales
    # event_id, outcome, side, price, size, reason, metadata, trace_id
```

**Alternativa**: Modificar directamente `backend/app/core/strategy/models.py` agregando campos opcionales.

#### 2.3. Crear Alias Temporal

Para mantener compatibilidad durante la migración:

```python
# backend/app/core/strategy_engine/models.py
from app.core.strategy.models import (
    OrderIntent as LegacyOrderIntent,
    MarketState,
    EventState
)

# El nuevo OrderIntent extiende el legacy
class OrderIntent(LegacyOrderIntent):
    strategy_id: Optional[UUID] = None
    graph_execution_id: Optional[UUID] = None
```

---

### FASE 1: Implementar Nuevo Sistema (Paralelo)

Implementar todo el nuevo sistema en `strategy_engine/` sin tocar `strategy/`.

**Ventajas**:
- El sistema actual sigue funcionando
- Podemos desarrollar y testear el nuevo sistema
- No hay riesgo de romper producción

---

### FASE 2: Migración Gradual (Opción A - Recomendada)

#### 2.1. Feature Flag

```python
# backend/app/settings.py
USE_GRAPH_STRATEGIES = os.getenv("USE_GRAPH_STRATEGIES", "false").lower() == "true"

# backend/app/main.py
if USE_GRAPH_STRATEGIES:
    from app.core.strategy_engine import StrategyEngine
    strategy_engine = StrategyEngine()
    await strategy_engine.control_loop.start(db)
else:
    from app.core.strategy import Strategy
    strategy = Strategy()
    # ... código actual
```

#### 2.2. Migrar Estrategias una por una

1. Crear estrategias nuevas usando grafos
2. Mantener el sistema legacy para estrategias existentes
3. Gradualmente migrar o desactivar estrategias legacy

#### 2.3. Eliminar Código Legacy

Una vez que todas las estrategias usen grafos:
1. Eliminar `backend/app/core/strategy/strategy.py`
2. Eliminar `StrategyConfig` de `models.py`
3. Eliminar feature flag
4. Renombrar `strategy_engine/` a `strategy/` (opcional)

---

### FASE 3: Migración Completa (Opción B - Más Limpia)

#### 3.1. Implementar Todo el Nuevo Sistema

Completar FASE 1 y FASE 2 del plan de implementación.

#### 3.2. Reemplazar en Main Loop

```python
# backend/app/main.py

# ANTES:
from app.core.strategy import Strategy
strategy = Strategy()
intents = await strategy.tick()

# DESPUÉS:
from app.core.strategy_engine import StrategyEngine
strategy_engine = StrategyEngine()
strategy_engine.initialize(db)
await strategy_engine.control_loop.start(db)

# Los intents se generan automáticamente desde el Control Loop
# y se pasan al Risk Engine
```

#### 3.3. Eliminar Código Legacy

Una vez que el nuevo sistema esté funcionando:

```bash
# Eliminar archivos
rm backend/app/core/strategy/strategy.py
rm backend/app/core/strategy/__init__.py  # O mantenerlo solo para exports

# Actualizar imports
# Buscar y reemplazar todos los imports de Strategy
```

---

## 3. Archivos a Eliminar/Modificar

### ❌ **ELIMINAR Completamente**

1. `backend/app/core/strategy/strategy.py` (728 líneas)
   - Lógica hardcodeada incompatible con grafos
   - Será reemplazado por `strategy_engine/strategy_engine.py` + grafos

2. `backend/app/core/strategy/models.py` → `StrategyConfig` (clase)
   - Ya no se usa, configuración va en grafos

3. `backend/app/core/strategy/models.py` → `NoEntryReason` (opcional)
   - Solo para logging, puede eliminarse o mantener para compatibilidad

### ✅ **MODIFICAR (Adaptar)**

1. `backend/app/core/strategy/models.py` → `OrderIntent`
   - Agregar `strategy_id: Optional[UUID]`
   - Agregar `graph_execution_id: Optional[UUID]`
   - Mantener todo lo demás

2. `backend/app/main.py`
   - Reemplazar instanciación de `Strategy()` por `StrategyEngine()`
   - Integrar `ControlLoop` en el main loop

3. `backend/app/core/config_service.py`
   - Deprecar `get_strategy_config()` (mantener por compatibilidad temporal)

### ✅ **MANTENER (Sin Cambios)**

1. `backend/app/core/strategy/models.py` → `MarketState`
   - Se usa en State Cache

2. `backend/app/core/strategy/models.py` → `EventState`
   - Se usa en State Cache

3. `backend/app/core/risk_engine/risk_engine.py`
   - No cambia, sigue recibiendo `List[OrderIntent]`

---

## 4. Checklist de Migración

### Pre-Migración

- [ ] Crear nuevo módulo `strategy_engine/` sin tocar `strategy/`
- [ ] Implementar Control Loop
- [ ] Implementar Graph Runtime
- [ ] Implementar State Cache Service
- [ ] Implementar nodos básicos
- [ ] Crear migración de base de datos (FASE 1 del plan)
- [ ] Tests del nuevo sistema

### Migración

- [ ] Adaptar `OrderIntent` (agregar campos nuevos)
- [ ] Integrar `StrategyEngine` en main loop
- [ ] Crear feature flag `USE_GRAPH_STRATEGIES`
- [ ] Probar con estrategias de prueba
- [ ] Validar que Risk Engine sigue funcionando

### Post-Migración

- [ ] Eliminar `backend/app/core/strategy/strategy.py`
- [ ] Eliminar `StrategyConfig` de models.py
- [ ] Deprecar `get_strategy_config()` en config_service
- [ ] Actualizar todos los imports
- [ ] Limpiar código no usado
- [ ] Documentar cambios

---

## 5. Riesgos y Mitigaciones

### Riesgo 1: Romper el sistema actual

**Mitigación**:
- Desarrollar nuevo sistema en módulo separado
- Usar feature flag para activar/desactivar
- Mantener código legacy hasta que nuevo sistema esté probado

### Riesgo 2: Incompatibilidad con Risk Engine

**Mitigación**:
- Mantener `OrderIntent` compatible
- Solo agregar campos opcionales
- Risk Engine no necesita cambios

### Riesgo 3: Pérdida de funcionalidad durante migración

**Mitigación**:
- Implementar todos los nodos necesarios antes de migrar
- Crear estrategias de prueba equivalentes a las actuales
- Validar que generan los mismos intents

---

## 6. Recomendación Final

**Opción Recomendada: Migración Gradual (Opción A)**

1. **Desarrollar nuevo sistema en paralelo** (`strategy_engine/`)
2. **Mantener sistema actual funcionando** (`strategy/`)
3. **Usar feature flag** para activar nuevo sistema
4. **Migrar gradualmente** estrategias al nuevo sistema
5. **Eliminar código legacy** una vez que todo esté migrado

**Ventajas**:
- ✅ No rompe producción
- ✅ Permite desarrollo y testing seguro
- ✅ Migración gradual sin presión
- ✅ Rollback fácil si hay problemas

**Desventajas**:
- ⚠️ Código duplicado temporalmente
- ⚠️ Más complejidad durante la transición

---

## 7. Orden de Implementación

1. **Crear estructura nueva** (`strategy_engine/`)
2. **Adaptar `OrderIntent`** (agregar campos)
3. **Implementar nuevo sistema** (según plan de implementación)
4. **Crear feature flag**
5. **Integrar en main loop** (con feature flag)
6. **Probar con estrategias de prueba**
7. **Migrar estrategias reales**
8. **Eliminar código legacy**

---

## 8. Archivos Específicos a Modificar

### `backend/app/core/strategy/models.py`

**Cambios**:
```python
# AGREGAR campos a OrderIntent
class OrderIntent(BaseModel):
    # ... campos existentes ...
    strategy_id: Optional[UUID] = None  # NUEVO
    graph_execution_id: Optional[UUID] = None  # NUEVO
```

**O eliminar `StrategyConfig` y `NoEntryReason` si no se usan**.

### `backend/app/main.py`

**Cambios**:
```python
# REEMPLAZAR
from app.core.strategy import Strategy
strategy = Strategy()
intents = await strategy.tick()

# POR
from app.core.strategy_engine import StrategyEngine
strategy_engine = StrategyEngine()
strategy_engine.initialize(db)
# Control Loop corre en background
```

### `backend/app/core/config_service.py`

**Cambios**:
```python
# DEPRECAR (mantener por compatibilidad)
def get_strategy_config(self):
    """DEPRECATED: Use strategy configuration from DB instead."""
    warnings.warn("get_strategy_config() is deprecated", DeprecationWarning)
    # ... código actual ...
```

---

## Conclusión

**Resumen**:
- ✅ **Reutilizar**: `OrderIntent`, `MarketState`, `EventState`
- ❌ **Eliminar**: `Strategy` (clase), `StrategyConfig`, `NoEntryReason` (opcional)
- ✅ **Nuevo**: Todo el sistema de grafos en `strategy_engine/`
- ✅ **Migración**: Gradual con feature flag

**Recomendación**: Empezar implementando el nuevo sistema en paralelo, sin tocar el existente, y luego migrar gradualmente.

