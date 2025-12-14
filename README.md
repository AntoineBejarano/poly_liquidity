# PolyLiquidity Desk

Sistema de trading algorítmico automatizado para proveer liquidez de cashout near-resolution en Polymarket y ejecutar estrategia de pre-settlement arbitrage.

## 🎯 Visión General

PolyLiquidity Desk es un sistema de trading algorítmico que opera en Polymarket utilizando datos externos verificados (principalmente de eventos deportivos) para detectar oportunidades de entrada cuando un evento está cerca de resolverse o ya ha terminado realmente. El objetivo es comprar contratos infravalorados antes de que el mercado oficial los cierre.

### Características Principales

- **Arquitectura Modular**: Sistema completamente modular, desacoplado, observable y testeable
- **Arquitectura Orientada a Eventos**: Sistema reactivo a eventos del mundo real
- **Monitoreo en Tiempo Real**: Observación continua del estado de salud, latencia y APIs externas
- **Gestión de Riesgo**: Control exhaustivo sobre exposición, tamaño de órdenes y seguridad operacional
- **Trazabilidad Completa**: Registro detallado de todas las acciones y decisiones del sistema
- **Historical Replay**: Capacidad de reconstruir estados pasados y re-ejecutar escenarios
- **Live Control**: Visualización y supervisión en tiempo real del sistema

## 📋 Stack Tecnológico

### Backend
- **Python 3.12+**
- **FastAPI** - Framework web asíncrono
- **SQLAlchemy + Alembic** - ORM y migraciones
- **PostgreSQL / SQLite** - Base de datos
- **Pytest** - Framework de testing
- **Asyncio** - Programación asíncrona
- **Pydantic** - Validación de datos
- **Ethereum Libraries** - Firma EIP-712

### Frontend
- **Next.js 14** (App Router)
- **TypeScript**
- **Tailwind CSS**
- **Stack OAuth**

## 🚀 Setup Inicial

### Backend

1. **Crear entorno virtual:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno:**
```bash
cp .env.example .env
# Editar .env con tus valores (ver variables requeridas abajo)
```

4. **Variables de entorno requeridas:**

**Esenciales para Polymarket:**
```bash
# Wallet privada (hex string con "0x")
PRIVATE_KEY=0x...

# Dirección de proxy wallet (visible en polymarket.com/settings)
FUNDER_ADDRESS=0x...  # O usar POLYMARKET_PROXY_ADDRESS

# Credenciales API L2 de Polymarket
POLYMARKET_API_KEY=...
POLYMARKET_API_SECRET=...
POLYMARKET_API_PASSPHRASE=...

# Configuración de red
CHAIN_ID=137  # Polygon mainnet
RPC_URL=https://polygon-rpc.com/  # URL de tu proveedor RPC
```

**Base de datos y otros:**
```bash
DATABASE_URL=postgresql://...  # O sqlite:///:memory: para desarrollo
STACK_SECRET_SERVER_KEY=...    # Clave secreta para Stack OAuth
WALLET_ENCRYPTION_KEY=...      # Clave para encriptar wallets en DB (solo si usas DB, base64 Fernet key)
```

**Builders (opcional):**
```bash
BUILDER_API_KEY=...
BUILDER_SECRET=...
BUILDER_PASS_PHRASE=...
```

⚠️ **IMPORTANTE:** Nunca subas claves privadas a control de versiones. Usa archivos `.env` y agrégalos a `.gitignore`.

5. **Ejecutar servidor:**
```bash
uvicorn app.main:app --reload
```

### Frontend

1. **Instalar dependencias:**
```bash
cd frontend
npm install
```

2. **Configurar variables de entorno:**
```bash
cp .env.local.example .env.local
# Editar .env.local con tus valores
```

3. **Ejecutar servidor de desarrollo:**
```bash
npm run dev
```

## 🧪 Testing

### Ejecutar Tests Unitarios

```bash
cd backend
pytest tests/unit/ -v
```

### Ejecutar Tests con Coverage

```bash
cd backend
pytest tests/unit/ --cov=app --cov-report=html
```

### Estado de Tests

- ✅ **257 tests unitarios pasando**
- ✅ Cobertura completa de módulos críticos
- ✅ Tests de integración estructurados (requieren FastAPI completo)

## 📁 Estructura del Proyecto

```
poly_liquidity/
├── backend/
│   ├── app/
│   │   ├── api/                    # Endpoints REST
│   │   │   ├── markets.py         # Gestión de mercados
│   │   │   ├── positions.py       # Gestión de posiciones
│   │   │   ├── risk.py            # Configuración de riesgo
│   │   │   ├── system.py          # Configuración del sistema
│   │   │   ├── wallets.py         # Gestión de wallets
│   │   │   ├── checkers.py        # Configuración de checkers
│   │   │   ├── control.py         # Control del sistema
│   │   │   ├── history.py         # Historical Replay API
│   │   │   ├── dashboard.py       # Dashboard API
│   │   │   ├── websocket.py       # WebSocket API
│   │   │   ├── metrics.py         # Métricas API
│   │   │   ├── live.py            # Live Control API
│   │   │   └── runtime.py         # Runtime Supervisor API
│   │   ├── core/                   # Lógica del bot (modular)
│   │   │   ├── wallet.py          # Wallet Service
│   │   │   ├── metrics/           # Metrics & Observability Layer
│   │   │   ├── runtime_supervisor/ # Runtime Supervisor
│   │   │   ├── scanner/           # Scanner Engine
│   │   │   ├── event_mapping_layer/ # Event Mapping Layer
│   │   │   ├── checkers/          # Checker System
│   │   │   ├── event_watch_engine/ # Event Watch Engine
│   │   │   ├── strategy/          # Strategy Engine
│   │   │   ├── risk_engine/       # Risk Engine
│   │   │   ├── execution/         # Execution Engine
│   │   │   ├── historical_replay/ # Historical Replay
│   │   │   ├── live_control/      # Live Control
│   │   │   ├── api_cache.py       # API Cache
│   │   │   ├── rate_limiter.py    # Rate Limiter
│   │   │   ├── latency_monitor.py # Latency Monitor
│   │   │   └── config_service.py  # Config Service
│   │   ├── models/                 # Modelos SQLAlchemy
│   │   ├── main.py                 # FastAPI app (main loop)
│   │   ├── settings.py             # Configuración
│   │   └── database.py             # Conexión DB
│   ├── tests/
│   │   ├── unit/                   # Tests unitarios (257 tests)
│   │   └── integration/            # Tests de integración
│   ├── alembic/                    # Migraciones
│   └── requirements.txt
├── frontend/
│   ├── app/                        # Next.js App Router
│   ├── components/                 # Componentes React
│   └── lib/                        # Utilidades
└── docs/                           # Documentación
    ├── overall.md                  # Arquitectura general
    ├── algoritmo_backend.md        # Algoritmo del backend
    ├── PLAN_REFACTORIZACION.md     # Plan de refactorización
    └── services/                   # Especificaciones de servicios
```

## 🏗️ Arquitectura del Sistema

El sistema sigue una arquitectura modular con el siguiente flujo:

```
Scanner → Event Mapping → Event Watch Engine → Strategy → Risk → Execution → Metrics → Runtime Supervisor
```

### Módulos Principales

1. **Scanner Engine** - Descubrimiento y filtrado de mercados en Polymarket
2. **Event Mapping Layer** - Mapeo de mercados Polymarket a eventos reales (ESPN, etc.)
3. **Checker System** - Verificación del estado de eventos mediante APIs externas
4. **Event Watch Engine** - Monitoreo en tiempo real de eventos con watchers paralelos
5. **Strategy Engine** - Decisión de órdenes (precio, tamaño, momento de entrada)
6. **Risk Engine** - Validación de riesgo y ajuste de tamaños
7. **Execution Engine** - Firma EIP-712 y envío de órdenes a Polymarket
8. **Runtime Supervisor** - Supervisión de salud del sistema, circuit breakers, fail-safes
9. **Metrics & Observability** - Recopilación, almacenamiento y alertas de métricas
10. **Historical Replay** - Registro, consulta y replay de eventos históricos
11. **Live Control** - Visualización y supervisión en tiempo real

### Flujo de Ejecución

El `main_loop` ejecuta continuamente el siguiente flujo:

1. **Scanner**: Escanea mercados activos (rate-limited, cached)
2. **Event Mapping**: Mapea mercados a eventos externos
3. **Event Watch Engine**: Monitorea estado de eventos en tiempo real
4. **Strategy**: Genera `OrderIntent` basado en condiciones de mercado
5. **Risk Engine**: Valida y ajusta `OrderIntent` → `ApprovedOrderIntent`
6. **Execution**: Firma EIP-712 y envía órdenes a Polymarket
7. **Metrics**: Registra métricas del sistema
8. **Runtime Supervisor**: Calcula modo de operación (GREEN/YELLOW/RED) y gestiona circuit breakers

## ✅ Estado de Refactorización

**Todas las fases de refactorización están completadas (FASE 0-14):**

- ✅ **FASE 0**: Preparación y Testing Infrastructure
- ✅ **FASE 1**: Wallet Service
- ✅ **FASE 2**: Metrics & Observability Layer
- ✅ **FASE 3**: Runtime Supervisor
- ✅ **FASE 4**: Scanner Engine
- ✅ **FASE 5**: Event Mapping Layer
- ✅ **FASE 6**: Checker System
- ✅ **FASE 7**: Event Watch Engine
- ✅ **FASE 8**: Strategy Engine
- ✅ **FASE 9**: Risk Engine
- ✅ **FASE 10**: Execution Engine
- ✅ **FASE 11**: Historical Replay
- ✅ **FASE 12**: Live Control
- ✅ **FASE 13**: Integración y Main Loop
- ✅ **FASE 14**: Testing Completo y Validación

Ver `docs/PLAN_REFACTORIZACION.md` para detalles completos de cada fase.

## 📚 Documentación

- **`docs/overall.md`** - Arquitectura general del sistema
- **`docs/algoritmo_backend.md`** - Algoritmo detallado del backend
- **`docs/PLAN_REFACTORIZACION.md`** - Plan completo de refactorización
- **`docs/POLYMARKET_CLIENT_INTEGRATION.md`** - Integración con cliente oficial de Polymarket (`py-clob-client`)
- **`docs/POLYMARKET_WEBSOCKET_INTEGRATION.md`** - Integración con WebSockets de Polymarket (updates en tiempo real)
- **`docs/services/`** - Especificaciones detalladas de cada servicio:
  - `wallet_service.md` - Gestión de wallets
  - `metrics_observabilitiy.md` - Sistema de métricas
  - `runtime_supervisor.md` - Supervisión del sistema
  - `scanner.md` - Scanner de mercados
  - `event_mapping_layer.md` - Mapeo de eventos
  - `checker_system.md` - Sistema de checkers
  - `event_watch_engine.md` - Motor de watchers
  - `strategy.md` - Motor de estrategia
  - `risk_engine.md` - Motor de riesgo
  - `execution.md` - Motor de ejecución
  - `signatures_trazability.md` - Firmas y trazabilidad
  - `historical_replay.md` - Historical Replay
  - `livecontrol.md` - Live Control

## 🔧 Configuración

### Variables de Entorno (Backend)

**Esenciales para Polymarket:**
```bash
# Wallet privada (hex string con "0x")
PRIVATE_KEY=0x...

# Dirección de proxy wallet (visible en polymarket.com/settings)
FUNDER_ADDRESS=0x...  # O usar POLYMARKET_PROXY_ADDRESS

# Credenciales API L2 de Polymarket (OPCIONALES - se generan automáticamente)
# El sistema genera estas credenciales automáticamente usando PRIVATE_KEY y FUNDER_ADDRESS
# Solo necesarias si quieres usar credenciales pre-generadas
# POLYMARKET_API_KEY=...
# POLYMARKET_API_SECRET=...
# POLYMARKET_API_PASSPHRASE=...

# Configuración de red
CHAIN_ID=137  # Polygon mainnet
RPC_URL=https://polygon-rpc.com/  # URL de tu proveedor RPC de Polygon
```

**Base de datos y otros:**
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname
# O para desarrollo: sqlite:///:memory:

# Stack OAuth
STACK_SECRET_SERVER_KEY=your_secret_key

# Wallet Encryption (opcional - solo necesario si usas wallets en DB)
# Si no está configurado, se genera una nueva clave cada vez (solo para desarrollo)
# Para producción, genera una clave con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
WALLET_ENCRYPTION_KEY=
```

**URLs de API (opcionales, valores por defecto incluidos):**
```bash
POLYMARKET_API_URL=https://api.polymarket.com
POLYMARKET_DATA_API_URL=https://data-api.polymarket.com
POLYMARKET_TRADING_API_URL=https://clob.polymarket.com
```

**Builders (opcional):**
```bash
BUILDER_API_KEY=...
BUILDER_SECRET=...
BUILDER_PASS_PHRASE=...
```

⚠️ **IMPORTANTE:** 
- Nunca subas `PRIVATE_KEY`, `POLYMARKET_API_SECRET`, u otras credenciales a control de versiones
- Usa archivos `.env` y asegúrate de que estén en `.gitignore`
- El sistema usa `PRIVATE_KEY` desde variables de entorno en producción (prioridad sobre wallets en DB)

### Tablas de Base de Datos

- **`system_config`** - Configuración del sistema y parámetros de riesgo
- **`wallets`** - Wallets operacionales (claves privadas encriptadas)
- **`secrets`** - Secrets para checkers (API keys, etc.)
- **`markets`** - Mercados escaneados de Polymarket
- **`events`** - Eventos externos mapeados
- **`orders`** - Órdenes enviadas a Polymarket
- **`trades`** - Trades ejecutados
- **`positions`** - Posiciones abiertas
- **`exposures`** - Estado de exposición por mercado
- **`metrics`** - Métricas históricas
- **`event_logs`** - Eventos para Historical Replay

## 🧩 Módulos y Características

### Wallet Service
- Gestión segura de wallets con encriptación
- Rotación en runtime sin reinicio
- Solo una wallet activa a la vez
- Caché en memoria para acceso rápido

### Metrics & Observability
- Recopilación de métricas (latencia, errores, contadores)
- Almacenamiento in-memory (reciente) + persistente (histórico)
- Sistema de alertas (Slack, Discord, Email)
- Exportador Prometheus
- Streaming SSE para dashboards

### Runtime Supervisor
- Cálculo de modo operacional (GREEN/YELLOW/RED)
- Circuit breakers (Trading, Checkers, API)
- Fail-safes automáticos
- Supervisión continua de salud

### Scanner Engine
- Descubrimiento de mercados candidatos
- Filtrado estructural, por categoría y precio
- Normalización y enriquecimiento de datos
- Rate limiting y caching inteligente

### Event Mapping Layer
- Clasificación de eventos (sports, politics, crypto, etc.)
- Mapeo a eventos canónicos externos (ESPN, etc.)
- Scoring de confianza
- Soporte para múltiples tipos de eventos

### Checker System
- Sistema modular de checkers
- Timeouts y retries con exponential backoff
- Circuit breakers por checker
- Quorum rules para agregación de resultados

### Event Watch Engine
- Watchers paralelos por evento
- Arquitectura event-centered (1 watcher por evento real)
- Agregación de estados con quorum rules
- Terminación automática de watchers finalizados

### Strategy Engine
- Condiciones de activación configurable
- Cálculo de precio objetivo con ajustes de latencia
- Cálculo de tamaño con restricciones múltiples
- Heurísticas específicas por tipo de evento

### Risk Engine
- 8 reglas de riesgo configurables
- Ajuste automático de tamaños
- Gestión de exposición (por mercado y global)
- Fail-safes automáticos

### Execution Engine
- Firma EIP-712 completa
- Gestión de nonces
- Rate limiting y retry logic
- Order lifecycle management
- Trazabilidad completa con trace_id
- **Nota:** Considerar usar `py-clob-client` (cliente oficial de Polymarket) - Ver `docs/POLYMARKET_CLIENT_INTEGRATION.md`

### Historical Replay
- Almacenamiento de eventos (SQLite + JSONL)
- Replay de eventos históricos
- Comparación de estrategias (A/B testing)
- Rewind a estados pasados

### Live Control
- State store in-memory thread-safe
- Event bus pub/sub
- Streaming SSE para actualizaciones en tiempo real
- API REST para consulta de estado

## 📊 Estado de Tests

- **257 tests unitarios** - Todos pasando ✅
- **Módulos cubiertos:**
  - Wallet Service
  - Metrics & Observability
  - Runtime Supervisor
  - Scanner Engine
  - Event Mapping Layer
  - Checker System
  - Event Watch Engine
  - Strategy Engine
  - Risk Engine
  - Execution Engine
  - Historical Replay
  - Live Control
  - Event Engine
  - API Cache
  - Rate Limiter
  - Config Service
  - Latency Monitor

## 🔄 Flujo de Desarrollo

1. Los módulos están completamente desacoplados y testeables
2. Cada módulo tiene tests unitarios completos
3. El main loop integra todos los módulos según el flujo definido
4. Los tests usan mocks para APIs externas (fácil actualización cuando cambien los datos)

## 🚨 Notas Importantes

### Configuración de Wallets

El sistema soporta dos modos de operación:

1. **Producción (Variables de Entorno)** - **RECOMENDADO**:
   - Usa `PRIVATE_KEY` desde variables de entorno
   - Usa `FUNDER_ADDRESS` o `POLYMARKET_PROXY_ADDRESS` desde variables de entorno
   - Las credenciales API (`POLYMARKET_API_KEY`, `POLYMARKET_API_SECRET`, `POLYMARKET_API_PASSPHRASE`) son obligatorias para trading real

2. **Desarrollo/Testing (Base de Datos)**:
   - Usa wallets almacenadas en la tabla `wallets` de la DB
   - Las claves privadas están encriptadas usando Fernet
   - La clave de encriptación debe configurarse en `WALLET_ENCRYPTION_KEY`
   - Solo se usa si `PRIVATE_KEY` no está configurado

**Prioridad:** Variables de entorno > Base de datos

### Seguridad

- ⚠️ **NUNCA** subas `PRIVATE_KEY`, `POLYMARKET_API_SECRET`, u otras credenciales a control de versiones
- Usa archivos `.env` y asegúrate de que estén en `.gitignore`
- Las claves privadas en variables de entorno tienen prioridad sobre las almacenadas en DB

### Rate Limiting

- El sistema respeta los límites de Polymarket:
  - Data API: 200 req/10s
  - Trading API: 2400 req/10s

### Circuit Breakers y Fail-Safes

- El sistema tiene circuit breakers para prevenir fallos en cascada
- Fail-safes automáticos para pausar trading en condiciones críticas (latencia alta, errores, exposición excesiva)

### Trazabilidad

- Todas las acciones tienen `trace_id` para auditoría completa
- Historical Replay permite reconstruir estados pasados

## 📝 Licencia

[Especificar licencia si aplica]

## 👥 Contribuir

[Instrucciones para contribuir si aplica]

