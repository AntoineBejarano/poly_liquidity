# Plan de Implementación: Series → Markets → Events → Outcomes

## Estado Actual

### ✅ Lo que ya tenemos:
1. **Modelo Market** - Parcialmente correcto (falta `series_id`)
   - ✅ `name`, `enabled`, `category`
   - ⚠️ Tiene `metadata` (JSON) - **DEBE RENOMBRARSE** a `polymarket_payload`
   - ❌ Falta `series_id` (ForeignKey a Series)
   
2. **Modelo Event** - ⚠️ **REQUIERE CORRECCIÓN**
   - ⚠️ Actualmente tiene `event_id` como String (debería ser `polymarket_event_id`)
   - ⚠️ Falta UUID interno `event_id` (o usar el `id` de BaseModel)
   - ✅ `market_id`, `start_time`, `end_time`, `state` correctos
   - ⚠️ **CRÍTICO**: `metadata` debe renombrarse a `polymarket_payload` (colisión con Base.metadata)
   - **Acción requerida**: 
     - Renombrar columna `metadata` → `polymarket_payload`
     - Renombrar columna `event_id` → `polymarket_event_id` (si es String de Polymarket)
     - Usar `id` (UUID de BaseModel) como identificador interno
   
3. **Frontend Markets Page** - Básico
   - ✅ Separación Markets/Events en tabs
   - ✅ Toggle enable/disable markets
   - ❌ Falta mostrar Series
   - ❌ Falta mostrar Tags
   
4. **Endpoints API Markets** - Básicos
   - ✅ `GET /markets` - Lista markets
   - ✅ `PATCH /markets/{id}/enable` - Activar/desactivar
   - ✅ `GET /markets/events/list` - Lista events
   - ❌ Falta endpoints para Series
   - ❌ Falta endpoints para Tags

### ❌ Lo que falta:
1. **Modelo Series** - No existe
2. **Modelo Tag** - No existe
3. **Modelo MarketTag** (tabla de relación) - No existe
4. **Scanner** - Actualmente crea Markets directamente, debe descubrir Series → Markets → Events
5. **Strategy/Execution** - Necesita verificación para operar solo sobre Events

---

## Plan de Implementación

### Fase 1: Modelos de Base de Datos

#### 1.1 Crear modelo Series
```python
# backend/app/models/series.py
class Series(BaseModel):
    __tablename__ = "series"
    
    polymarket_series_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=True, index=True)
    description = Column(String, nullable=True)
    series_type = Column(String, nullable=True)  # ej: "recurring", "one-time" (best-effort, no crítico)
    recurrence = Column(String, nullable=True)  # ej: "15m", "1h", "daily" (best-effort, puede venir implícito)
    # ⚠️ NO usar 'metadata' - es nombre reservado en SQLAlchemy (colisiona con Base.metadata)
    polymarket_payload = Column(JSON, nullable=True)  # Datos raw de Polymarket API
    
    # Relationships
    markets = relationship("Market", back_populates="series")
    
    # Nota: series_type y recurrence pueden no estar siempre disponibles.
    # Usar tags + name parsing como fallback para inferir frecuencia.
```

#### 1.2 Crear modelo Tag
```python
# backend/app/models/tag.py
class Tag(BaseModel):
    __tablename__ = "tags"
    
    polymarket_tag_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=True, index=True)
    label = Column(String, nullable=True)
    # ⚠️ NO usar 'metadata' - es nombre reservado en SQLAlchemy
    polymarket_payload = Column(JSON, nullable=True)  # Datos raw de Polymarket API
    
    # Relationships
    markets = relationship("MarketTag", back_populates="tag")
```

#### 1.3 Crear modelo MarketTag (tabla de relación)
```python
# backend/app/models/market_tag.py
class MarketTag(BaseModel):
    __tablename__ = "market_tags"
    
    market_id = Column(UUID, ForeignKey("markets.id"), nullable=False, index=True)
    tag_id = Column(UUID, ForeignKey("tags.id"), nullable=False, index=True)
    
    # Relationships
    market = relationship("Market", back_populates="tags")
    tag = relationship("Tag", back_populates="markets")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('market_id', 'tag_id', name='uq_market_tag'),
    )
```

#### 1.4 Actualizar modelo Market
```python
# Agregar a backend/app/models/market.py
series_id = Column(UUID, ForeignKey("series.id"), nullable=True, index=True)
tags = relationship("MarketTag", back_populates="market", cascade="all, delete-orphan")
series = relationship("Series", back_populates="markets")

# ⚠️ Verificar que Market.metadata (si existe) se renombre a polymarket_payload
# para evitar colisión con Base.metadata de SQLAlchemy
```

---

### Fase 2: Endpoints API

#### 2.1 Endpoints Series
```python
# backend/app/api/series.py
GET /series - Lista todas las series
GET /series/{id} - Detalles de una serie con sus markets
GET /series/{id}/markets - Markets de una serie
```

#### 2.2 Endpoints Tags
```python
# backend/app/api/tags.py
GET /tags - Lista todos los tags
GET /tags/{id} - Detalles de un tag
GET /tags/{id}/markets - Markets con este tag
```

#### 2.3 Actualizar endpoints Markets
```python
# Actualizar backend/app/api/markets.py
GET /markets - Agregar filtros por series_id y tags
GET /markets/{id} - Incluir series y tags en respuesta
```

---

### Fase 3: Scanner - Descubrimiento Series → Markets → Events

#### 3.1 Flujo del Scanner
```
1. Scanner consulta Polymarket API:
   - GET /series → Descubre Series
   - Para cada Series: GET /series/{id} → Descubre Markets
   - Para cada Market activo (enabled=true):
     - GET /markets/{id} → Descubre Events activos/futuros
     - Crea/actualiza Events en DB
```

#### 3.2 Actualizar Scanner
```python
# backend/app/core/scanner/scanner.py

# ⚠️ IMPORTANTE: Implementar caching para evitar explosión de requests
# - Cachear Series y Markets con updated_at / etag / last_seen
# - No rediscover todo en cada tick
# - Solo actualizar Series/Markets que hayan cambiado

async def discover_series_and_markets():
    """Descubre Series desde Polymarket API"""
    # GET https://gamma-api.polymarket.com/series
    # Guarda Series en DB
    # ⚠️ Cachear resultado, solo actualizar si updated_at cambió
    
async def discover_markets_from_series(series_id):
    """Descubre Markets de una Series"""
    # GET https://gamma-api.polymarket.com/series/{id}
    # Extrae markets del response
    # Guarda Markets en DB con series_id
    # ⚠️ Cachear, solo actualizar si hay cambios
    
async def discover_events_from_market(market_id):
    """Descubre Events de un Market activo (solo si enabled=true)"""
    # GET https://gamma-api.polymarket.com/markets/{id}
    # Extrae events del response
    # Crea/actualiza Events en DB con:
    #   - polymarket_event_id (ID de Polymarket, String)
    #   - event_id (UUID interno de nuestra DB)
    #   - market_id
    #   - start_time, end_time
    #   - state (UPCOMING, ACTIVE, FINISHED)
    # ⚠️ Solo ejecutar para Markets con enabled=true
```

---

### Fase 4: Frontend - Jerarquía Series → Markets → Events

#### 4.1 Estructura de la página Markets
```
Markets Page
├── Series View (opcional, colapsable)
│   ├── Series 1: "Bitcoin Up or Down"
│   │   ├── Market: "BTC Up or Down – 15 min" [Toggle Enable]
│   │   │   ├── Tags: crypto, bitcoin, 15m, up-down
│   │   │   └── Events (read-only):
│   │   │       ├── Event: "BTC Up or Down 18:00–18:15" [ACTIVE]
│   │   │       └── Event: "BTC Up or Down 18:15–18:30" [UPCOMING]
│   │   └── Market: "BTC Up or Down – 1h" [Toggle Enable]
│   └── Series 2: "Ethereum Up or Down"
│       └── ...
├── Markets View (flat, con filtros)
│   ├── Filtros: Series, Tags, Category, Enabled
│   └── Tabla de Markets con toggle enable/disable
└── Events View (read-only)
    ├── Filtros: Market, State (UPCOMING/ACTIVE/FINISHED)
    └── Tabla de Events
```

#### 4.2 Componentes necesarios
- `SeriesList` - Lista de series con markets anidados
- `MarketCard` - Card de market con toggle y tags
- `EventList` - Lista de events (read-only)
- `TagFilter` - Filtro por tags (múltiple selección)
- `SeriesFilter` - Filtro por series

---

### Fase 5: Strategy y Execution - Operar solo sobre Events

#### 5.1 Verificar Strategy
```python
# backend/app/core/strategy/strategy.py
# Asegurar que Strategy.tick() recibe Events, no Markets
# Los OrderIntents deben referenciar event_id, no market_id
```

#### 5.2 Verificar Execution
```python
# backend/app/core/execution/execution.py
# Asegurar que Execution.tick() opera sobre Events
# Los orders deben usar token_id del Event (no del Market)
```

#### 5.3 Actualizar OrderIntent
```python
# Cambiar de:
market_id: UUID
# A:
event_id: UUID  # ID del Event (no Market)
outcome: str    # "YES" o "NO" o "UP" o "DOWN"
```

⚠️ **IMPACTO CRÍTICO**: Este cambio afecta múltiples componentes:

1. **RiskEngine** - Revisar exposición por market vs por event
   - Normalmente: exposición se controla por market (agregado)
   - Ejecución: ocurre por event (individual)
   - Necesario: mapear event_id → market_id para cálculos de exposición

2. **Métricas y Reporting** - Actualizar agregaciones
   - Agrupar por market_id para exposición total
   - Agrupar por event_id para ejecución individual

3. **Positions** - Verificar si se crean por market o por event
   - Recomendación: mantener positions por market (agregado)
   - Events individuales contribuyen a la position del market

---

### Fase 6: Migración de Base de Datos

#### 6.1 Script de migración
```sql
-- ⚠️ IMPORTANTE: Renombrar 'metadata' a 'polymarket_payload' en todas las tablas
-- para evitar colisión con Base.metadata de SQLAlchemy

-- Crear tabla series
CREATE TABLE series (
    id UUID PRIMARY KEY,
    polymarket_series_id VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    slug VARCHAR,
    description TEXT,
    series_type VARCHAR,  -- best-effort, puede ser NULL
    recurrence VARCHAR,   -- best-effort, puede ser NULL
    polymarket_payload JSONB,  -- ⚠️ NO usar 'metadata'
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Crear tabla tags
CREATE TABLE tags (
    id UUID PRIMARY KEY,
    polymarket_tag_id VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    slug VARCHAR,
    label VARCHAR,
    polymarket_payload JSONB,  -- ⚠️ NO usar 'metadata'
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Crear tabla market_tags
CREATE TABLE market_tags (
    id UUID PRIMARY KEY,
    market_id UUID REFERENCES markets(id),
    tag_id UUID REFERENCES tags(id),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    UNIQUE(market_id, tag_id)
);

-- Agregar series_id a markets
ALTER TABLE markets ADD COLUMN series_id UUID REFERENCES series(id);

-- ⚠️ Migración para Event: Renombrar metadata y asegurar polymarket_event_id
-- Si events ya existe con 'metadata', renombrarlo:
-- ALTER TABLE events RENAME COLUMN metadata TO polymarket_payload;
-- Si event_id es String (ID de Polymarket), renombrarlo a polymarket_event_id:
-- ALTER TABLE events RENAME COLUMN event_id TO polymarket_event_id;
-- Agregar nuevo event_id como UUID interno si no existe:
-- ALTER TABLE events ADD COLUMN event_id UUID DEFAULT gen_random_uuid();
-- CREATE UNIQUE INDEX idx_events_polymarket_event_id ON events(polymarket_event_id);

-- Crear índices
CREATE INDEX idx_series_polymarket_id ON series(polymarket_series_id);
CREATE INDEX idx_tags_polymarket_id ON tags(polymarket_tag_id);
CREATE INDEX idx_markets_series_id ON markets(series_id);
CREATE INDEX idx_market_tags_market_id ON market_tags(market_id);
CREATE INDEX idx_market_tags_tag_id ON market_tags(tag_id);

-- ⚠️ Si Market tiene columna 'metadata', renombrarla también:
-- ALTER TABLE markets RENAME COLUMN metadata TO polymarket_payload;
```

---

## Prioridades

### Alta Prioridad (Crítico para funcionamiento)
1. ✅ Crear modelos Series, Tag, MarketTag
2. ✅ Actualizar modelo Market con series_id
3. ✅ Actualizar Scanner para descubrir Series → Markets → Events
4. ✅ Verificar Strategy/Execution operan sobre Events

### Media Prioridad (Mejora UX)
5. ✅ Actualizar frontend para mostrar Series → Markets → Events
6. ✅ Agregar filtros por Tags en frontend
7. ✅ Endpoints API para Series y Tags

### Baja Prioridad (Nice to have)
8. ✅ Migración de datos existentes
9. ✅ Tests unitarios para nuevos modelos
10. ✅ Documentación API

---

## Notas Importantes

1. **NO activar Series para trading** - Solo Markets pueden activarse
2. **NO activar Tags para trading** - Solo para filtrado/búsqueda
3. **Events se descubren automáticamente** - No se activan manualmente
4. **Strategy/Execution solo operan Events** - Nunca Markets o Series
5. **Outcomes son parte del Event** - Se obtienen del polymarket_payload del Event

## ⚠️ Ajustes Críticos (Evitar Bugs)

### 1. NO usar `metadata` como nombre de columna
- **Problema**: `metadata` es nombre reservado en SQLAlchemy (colisiona con `Base.metadata`)
- **Solución**: Usar `polymarket_payload` o `extra_data` o `raw_payload`
- **Aplicar en**: Series, Tag, Event, Market (si existe)

### 2. series_type y recurrence son best-effort
- **Problema**: Polymarket no siempre expone estos campos estructurados
- **Solución**: 
  - Mantener campos como nullable
  - Usar tags + name parsing como fallback
  - No hacer lógica crítica basada solo en ellos

### 3. Scanner: Implementar caching
- **Problema**: Flujo Series → Series/{id} → Markets/{id} puede explotar en requests
- **Solución**:
  - Cachear Series y Markets con `updated_at` / `etag` / `last_seen`
  - No rediscover todo en cada tick
  - Solo actualizar lo que haya cambiado

### 4. Event: Guardar polymarket_event_id explícito
- **Problema**: Necesitamos distinguir UUID interno vs ID de Polymarket
- **Solución**:
  - `event_id`: UUID interno de nuestra DB
  - `polymarket_event_id`: String, ID de Polymarket (único, indexado)
  - Facilita migraciones, debugging y reconciliación con API

### 5. OrderIntent: Revisar impacto en RiskEngine
- **Problema**: Cambio de `market_id` a `event_id` afecta exposición
- **Solución**:
  - Exposición se controla por market (agregado)
  - Ejecución ocurre por event (individual)
  - Mapear `event_id` → `market_id` para cálculos de exposición
  - Actualizar RiskEngine para mantener exposición por market

---

## Próximos Pasos

1. Implementar modelos Series, Tag, MarketTag
2. Actualizar modelo Market
3. Crear endpoints API básicos
4. Actualizar Scanner
5. Actualizar frontend
6. Verificar Strategy/Execution
7. Crear migración de BD

