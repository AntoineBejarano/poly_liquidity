# PolyLiquidity Desk – Especificación Técnica Detallada

## 0. Visión general

**PolyLiquidity Desk** es un sistema monolítico (backend + frontend en un solo proyecto) diseñado para:

- Proveer **liquidez de cashout near-resolution** en Polymarket.
- Ejecutar una estrategia de **pre-settlement arbitrage** (comprar outcomes casi seguros a descuento mínimo).
- Mover **millones de euros en volumen**, con:
  - Control de riesgo estricto.
  - Auditabilidad completa.
  - Panel de control configurable vía frontend.

El sistema se diseña para ser:

- **Monolito**: sin microservicios, sin colas distribuidas.
- **State-driven**: el estado vivo está en memoria del backend; la base de datos es persistencia, no fuente de decisión.
- **Operado por humanos ricos**: interfaz cuidada, parámetros de riesgo configurables, historial completo.

---

## Stack tecnológico

### Backend
- Lenguaje: **Python 3.12**
- Framework API: **FastAPI**
- Concurrencia: **asyncio**
- HTTP client: **httpx**
- WebSockets: `websockets` o soporte nativo de FastAPI
- ORM: **SQLAlchemy**
- Migraciones: **Alembic**
- Base de datos: **Neon Database (PostgreSQL en cloud, serverless/autoscaling)**
- Configuración: `pydantic-settings` o similar
- Logs: `structlog` / `logging` con JSON logs

### Base de datos
- **Neon Database (PostgreSQL)**:
  - Branches para entornos (`dev`, `staging`, `prod`).
  - Connection pooling gestionado por Neon.
  - Se accede vía `DATABASE_URL` (env var).
  - **Autenticación**: NO requiere API key adicional. La autenticación se realiza usando el **JWT obtenido de Stack Auth**.
  - El backend usa el JWT del usuario autenticado para autenticarse con Neon en cada query.

### Autenticación / Autorización
- Proveedor: **Stack OAuth** (servicio externo de OAuth).
- Uso:
  - El frontend integra SDK de Stack OAuth para login.
  - El backend recibe un **JWT / access token** en cada request.
  - El backend valida el token (firma + claims) usando `STACK_SECRET_SERVER_KEY`.
  - El backend mapea `user_id` remoto a un registro local `users`.
  - **El mismo JWT se usa para autenticarse con Neon Database** (no se requiere API key adicional de Neon).

### Frontend
- Framework: **Next.js (React + TypeScript)**  
- Build: **App Router** (o Pages Router, a decidir, pero App Router es preferible).
- Styling: **Tailwind CSS**
- Charts: **Recharts** (o similar) para PnL, exposición, histórico.
- Auth: SDK de **Stack OAuth** para React.
- Comunicación con backend:
  - REST (HTTP) para consultas y cambios de configuración.
  - WebSocket para eventos en tiempo real (fills, alerts de riesgo, estado del bot).

---

## Arquitectura global (monolito)

Estructura del repo:

```bash
polyliquidity/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── settings.py
│   │   ├── database.py
│   │   ├── api/
│   │   │   ├── markets.py
│   │   │   ├── positions.py
│   │   │   ├── risk.py
│   │   │   ├── history.py
│   │   │   └── control.py
│   │   ├── core/
│   │   │   ├── scanner.py
│   │   │   ├── event_agents.py
│   │   │   ├── event_engine.py
│   │   │   ├── checkers/
│   │   │   │   ├── base.py
│   │   │   │   ├── registry.py
│   │   │   │   └── implementations/
│   │   │   ├── secrets.py
│   │   │   ├── strategy.py
│   │   │   ├── execution.py
│   │   │   ├── risk_engine.py
│   │   │   ├── state.py
│   │   │   └── metrics.py
│   │   ├── models/
│   │   │   ├── base.py
│   │   │   ├── market.py
│   │   │   ├── event.py
│   │   │   ├── event_checker.py
│   │   │   ├── checker_config.py
│   │   │   ├── secret.py
│   │   │   ├── order.py
│   │   │   ├── trade.py
│   │   │   ├── position.py
│   │   │   ├── exposure.py
│   │   │   └── user.py
│   │   └── alembic/
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx            # Dashboard
│   │   ├── markets/
│   │   ├── positions/
│   │   ├── history/
│   │   ├── risk/
│   │   └── settings/
│   ├── components/
│   ├── lib/
│   │   ├── api.ts
│   │   └── ws.ts
│   └── package.json
└── TECH_SPEC.md
```

**Backend:**
- `app/`: FastAPI, endpoints, wiring.
- `core/`: lógica del motor del bot.
- `models/`: ORM SQLAlchemy.

**Frontend:**
- Páginas de dashboard, markets, positions, history, risk, settings.

---

# Fases de Desarrollo

## FASE 1: Setup inicial y estructura del proyecto

### Objetivo
Crear la estructura base del proyecto, configurar entornos y dependencias.

### Tareas

1. **Crear estructura de directorios**
   - Backend: `backend/app/` con subdirectorios `api/`, `core/`, `models/`
   - Frontend: `frontend/` con estructura de Next.js App Router
   - Archivos de configuración base

2. **Configurar backend**
   - `requirements.txt` con dependencias:
     - FastAPI, uvicorn
     - SQLAlchemy, Alembic
     - httpx, websockets
     - pydantic-settings
     - structlog
   - `backend/app/settings.py`: configuración con `pydantic-settings`
   - `backend/app/database.py`: conexión a Neon (SQLAlchemy)
     - Configurar para usar JWT de Stack Auth en las conexiones
     - NO requiere API key adicional de Neon
   - `backend/app/main.py`: FastAPI app básica con health check
   - `alembic.ini` y configuración de Alembic

3. **Configurar frontend**
   - `package.json` con Next.js, TypeScript, Tailwind CSS
   - Configuración de Tailwind
   - Estructura de carpetas `app/`, `components/`, `lib/`
   - `next.config.js` básico

4. **Variables de entorno**

   **Backend (`.env`):**
   ```bash
   # ============================================
   # AUTENTICACIÓN Y BASE DE DATOS
   # ============================================
   
   # Stack Auth - Server Key (para validar tokens)
   STACK_SECRET_SERVER_KEY='ssk_j7z6yr2krm7v1gd6g3vfef1vt3r2bdqfs2f9a70qc2tv8'
   
   # Neon Database - Connection String
   # La DB usa el JWT de Stack Auth para autenticación, NO requiere API key adicional
   DATABASE_URL='postgresql://neondb_owner:npg_yIe73bNMWgLz@ep-lively-union-a4iepcwe-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require'
   
   # Neon Data API (opcional, para queries REST directas si se necesita)
   DATA_API_ENDPOINT='https://ep-lively-union-a4iepcwe.apirest.us-east-1.aws.neon.tech/neondb/rest/v1'
   
   # ============================================
   # POLYMARKET
   # ============================================
   
   # Polymarket API
   POLYMARKET_API_URL='https://api.polymarket.com'  # o la URL correcta
   # POLYMARKET_API_KEY solo si es necesario para la API pública
   
   # ============================================
   # SERVER CONFIGURATION
   # ============================================
   
   # Entorno de ejecución
   ENVIRONMENT=development  # development, staging, production
   
   # Backend host y puerto
   HOST=0.0.0.0  # Escuchar en todas las interfaces
   PORT=8000  # Puerto del servidor FastAPI
   
   # CORS (si el frontend está en otro dominio)
   CORS_ORIGINS=http://localhost:3000,https://tudominio.com  # Separados por comas
   
   # ============================================
   # LOGGING
   # ============================================
   
   # Nivel de logging
   LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
   
   # Formato de logs
   LOG_FORMAT=json  # json o text
   ```

   **Nota importante:**
   - **Toda la configuración del sistema y riesgo se almacena en la tabla `system_config` de la DB**
   - **El wallet se gestiona como recurso en la tabla `wallets` de la DB** (NO como variable de entorno)
   - No se usan variables de entorno para: `TICK_SECONDS`, `SCAN_INTERVAL_SECONDS`, `MIN_CANDIDATE_PRICE`, `MIN_FEED_CONFIDENCE`, `CHECKER_TIMEOUT_SECONDS`, ni ninguna configuración de riesgo
   - Estas configuraciones se cargan desde la DB al arrancar y se pueden modificar desde el frontend
   - Solo se mantienen variables técnicas esenciales (DB, JWT, server, logging)

   **Frontend (`.env.local`):**
   ```bash
   # Stack Auth - Public Keys (para Next.js)
   NEXT_PUBLIC_STACK_PROJECT_ID='32ee526b-a970-4239-b401-c0af891804f9'
   NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY='pck_61kjyfggywecv7bpaxm4n7j82640qse8q1y2e09cqphg0'
   
   # Backend URL
   NEXT_PUBLIC_BACKEND_URL='http://localhost:8000'  # o la URL de producción
   ```

   **Nota importante:**
   - **Neon Database NO requiere API key adicional**: La autenticación se hace usando el JWT obtenido de Stack Auth
   - El backend valida el JWT de Stack Auth y lo usa para autenticarse con Neon
   - `DATABASE_URL` contiene las credenciales de conexión, pero las queries se autentican con el JWT del usuario

5. **Docker (opcional para desarrollo)**
   - `Dockerfile` para backend
   - `docker-compose.yml` si se usa localmente

### Entregables
- Estructura de proyecto completa
- Backend corriendo con `/health` endpoint
- Frontend corriendo (página vacía)
- Dependencias instaladas

---

## FASE 2: Base de datos y modelos

### Objetivo
Definir y crear todas las tablas en Neon usando Alembic.

### Tareas

1. **Modelos SQLAlchemy**

   **`models/base.py`**
   - Base class para todos los modelos
   - Timestamps comunes (`created_at`, `updated_at`)

   **`models/user.py`**
   ```python
   class User:
       id: UUID (PK)
       stack_oauth_user_id: str (unique)
       email: str
       role: str (admin, viewer)
       created_at: datetime
   ```

   **`models/wallet.py`**
   ```python
   class Wallet:
       id: UUID (PK)
       label: str  # "main", "backup", "testing"
       address: str  # public address
       encrypted_private_key: bytes  # bytea en PostgreSQL, clave privada encriptada
       active: bool  # SOLO UNA puede estar activa
       created_at: datetime
       updated_at: datetime
   ```
   - El wallet es un recurso operativo, NO configuración del sistema
   - Solo puede haber UNA wallet activa (invariante)
   - Se gestiona desde el frontend (control plane)
   - Se usa en ExecutionEngine para firmar órdenes
   - Permite rotación en runtime sin reinicio

   **`models/market.py`**
   ```python
   class Market:
       id: UUID (PK)
       polymarket_id: str (unique)
       question: str
       outcome: str (YES/NO)
       status: str (OPEN / RESOLVED / PAUSED)
       last_price: float
       resolution_outcome: str (YES / NO / NULL)
       resolved_at: datetime (nullable)
       created_at: datetime
       updated_at: datetime
   ```

   **`models/event.py`**
   ```python
   class Event:
       id: UUID (PK)
       market_id: UUID (FK → markets.id)
       external_event_id: str
       state: str (LIVE / FINISHED_UNCONFIRMED / FINISHED_CONFIRMED)
       confidence: float
       feed_a_confirmed: bool
       feed_b_confirmed: bool
       finished_at: datetime (nullable)
       created_at: datetime
       updated_at: datetime
   ```

   **`models/order.py`**
   ```python
   class Order:
       id: UUID (PK)
       polymarket_order_id: str (index)
       market_id: UUID (FK)
       side: str (BUY)
       price: float
       size: float
       status: str (NEW / PARTIALLY_FILLED / FILLED / CANCELLED)
       filled_size: float
       created_at: datetime
       updated_at: datetime
   ```

   **`models/trade.py`**
   ```python
   class Trade:
       id: UUID (PK)
       order_id: UUID (FK → orders.id)
       market_id: UUID (FK)
       fill_price: float
       fill_size: float
       direction: str (BUY)
       timestamp: datetime
   ```

   **`models/position.py`**
   ```python
   class Position:
       id: UUID (PK)
       market_id: UUID (FK)
       size: float
       avg_price: float
       resolved: bool
       payout: float (nullable)
       created_at: datetime
       updated_at: datetime
   ```

   **`models/exposure.py`**
   ```python
   class Exposure:
       id: UUID (PK)
       market_id: UUID (FK)
       notional: float  # size * avg_price
       max_allowed: float
       breached: bool
       timestamp: datetime
   ```

   **`models/system_config.py`**
   ```python
   class SystemConfig:
       id: UUID (PK)
       key: str (unique)  # ej. "tick_seconds", "min_candidate_price"
       value: str  # valor serializado (JSON o string)
       value_type: str  # "float", "int", "bool", "string"
       category: str  # "system", "risk", "scanner", "event_engine"
       description: str
       updated_at: datetime
       updated_by: UUID (FK → users.id, nullable)
   ```
   - Almacena toda la configuración del sistema y riesgo
   - Permite actualización desde frontend
   - Historial de cambios (opcional, se puede añadir tabla de historial)
   - Categorías: `system`, `risk`, `scanner`, `event_engine`

   **`models/event_checker.py`**
   ```python
   class EventChecker:
       id: UUID (PK)
       implementation_key: str  # selecciona qué clase de checker instanciar
       category: str  # sports, crypto, politics, etc.
       name: str
       description: str
       enabled: bool
       created_at: datetime
       updated_at: datetime
   ```
   - Define qué tipos de señales puede usar el sistema
   - Permite soportar múltiples proveedores para la misma categoría
   - Permite cambiar proveedores sin cambiar código

   **`models/checker_config.py`**
   ```python
   class CheckerConfig:
       id: UUID (PK)
       checker_id: UUID (FK → event_checkers.id)
       secret_name: str (nullable, FK → secrets.name)
       weight: float  # para agregación de señales
       timeout_seconds: float
       enabled: bool
       created_at: datetime
       updated_at: datetime
   ```
   - Define cómo se comporta un checker en runtime
   - Permite habilitar/deshabilitar checkers dinámicamente
   - Permite ajustar pesos y timeouts en vivo
   - `secret_name` es el enlace entre checker logic y sus credenciales runtime

   **`models/secret.py`**
   ```python
   class Secret:
       id: UUID (PK)
       name: str (unique)  # identificador del secret
       value: str  # valor encriptado o plain (según política de seguridad)
       description: str
       created_at: datetime
       updated_at: datetime
   ```
   - Existe solo porque la detección de eventos depende de APIs externas
   - Permite cambiar proveedores de API sobre la marcha
   - Permite rotar keys durante operación
   - Permite experimentar con diferentes checkers de forma segura
   - **No es autenticación de usuario, no es OAuth, no es secrets genéricos**
   - Es infraestructura de detección de eventos

3. **Migraciones Alembic**
   - `alembic init alembic`
   - Configurar `alembic/env.py` para usar `database.py`
   - Primera migración: `alembic revision --autogenerate`
   - Revisar y ajustar migración generada
   - `alembic upgrade head`

3. **Relaciones y constraints**
   - Foreign keys correctamente definidas
   - Índices en campos de búsqueda frecuente
   - Constraints de unicidad donde corresponda

### Entregables
- Todos los modelos definidos
- Migraciones Alembic funcionando
- Tablas creadas en Neon (branch dev)
- Tests básicos de inserción/consulta

---

## FASE 3: Sistema de estado y configuración

### Objetivo
Implementar el sistema de estado en memoria y la configuración de riesgo.

### Tareas

1. **`core/state.py` – State Manager**

   Mantiene el estado vivo del sistema:

   ```python
   class SystemState:
       system_active: bool
       markets: dict[MarketId, MarketState]
       events: dict[MarketId, EventState]
       orders: dict[OrderId, OrderState]
       positions: dict[MarketId, PositionState]
       exposures: dict[MarketId, ExposureState]
       risk_config: RiskConfig
   ```

   Funcionalidades:
   - Cargar estado desde DB al arrancar
   - Actualizar estado en memoria en cada tick
   - Persistir cambios relevantes asíncronamente a Neon
   - Thread-safe (si es necesario)

2. **Configuración de sistema y riesgo**

   **`SystemConfigService`**
   - Servicio para cargar y gestionar configuración desde tabla `system_config`
   - Carga toda la configuración al arrancar
   - Cache en memoria para acceso rápido
   - Invalidación de cache cuando se actualiza desde frontend

   **`RiskConfig` (pydantic model):**
   ```python
   class RiskConfig:
       max_exposure_per_market: float  # ej. 20k–100k
       max_global_exposure: float  # ej. % del bankroll
       max_markets_active: int
       max_exposure_per_event_type: dict[str, float]  # opcional
       min_entry_price: float  # ej. 0.98 o 0.99
       target_margin: float  # ej. 0.001–0.002
       min_candidate_price: float  # ej. 0.97
       safety_tick: float
       max_single_order_size: float
       tick_seconds: float
       scan_interval_seconds: float
       min_feed_confidence: float
       checker_timeout_seconds: float
   ```

   **Valores por defecto (se insertan en DB en primera migración):**
   - `tick_seconds`: 1.0
   - `scan_interval_seconds`: 30.0
   - `min_candidate_price`: 0.97
   - `min_feed_confidence`: 0.8
   - `checker_timeout_seconds`: 5.0
   - `max_exposure_per_market`: 50000.0
   - `max_global_exposure`: 500000.0
   - `max_markets_active`: 30
   - `min_entry_price`: 0.98
   - `target_margin`: 0.001
   - `safety_tick`: 0.0001
   - `max_single_order_size`: 10000.0

   - **Cargar desde DB** (tabla `system_config`)
   - **NO usar env vars** para esta configuración
   - Permitir actualización desde API (Fase 7)
   - Los cambios se aplican sin reinicio (cache invalidation)

3. **Ciclo principal (event loop)**

   En `main.py` o módulo separado:

   ```python
   async def main_loop():
       while state.system_active:
           await scanner.tick()         # 1. Escanear mercados
           await event_engine.tick()    # 2. Actualizar estado de eventos externos
           await strategy.tick()        # 3. Decidir órdenes
           await risk_engine.tick()     # 4. Aplicar límites de riesgo
           await execution.tick()       # 5. Enviar/cancelar órdenes
           await metrics.tick()         # 6. Registrar métricas
           await asyncio.sleep(settings.TICK_SECONDS)
   ```

   - Lanzar desde startup event de FastAPI
   - Manejar shutdown graceful

4. **Persistencia asíncrona**
   - Función para guardar cambios de estado a DB sin bloquear el loop
   - Batch updates cuando sea posible

5. **`core/secrets.py` – SecretService**

   **Objetivo:** Proveer credenciales a checkers durante ejecución sin requerir reinicio.

   **Por qué existe:**
   - La detección de eventos depende de APIs externas
   - Las credenciales deben ser configurables en runtime desde el frontend
   - Los checkers deben poder acceder a credenciales dinámicamente
   - Evitar reiniciar el event engine cuando cambian credenciales

   **Responsabilidades:**
   - Proporcionar credenciales a checkers durante ejecución
   - Permitir actualizaciones en vivo desde frontend
   - Cachear credenciales para que checkers sean rápidos
   - Evitar reiniciar el event engine

   **Implementación:**
   ```python
   class SecretService:
       async def get_secret(secret_name: str) -> str | None
       async def set_secret(secret_name: str, value: str)
       async def delete_secret(secret_name: str)
       def invalidate_cache(secret_name: str)
   ```
   - Cache en memoria para acceso rápido
   - Invalidación de cache cuando se actualiza un secret
   - Sin reinicio requerido

   **Nota crítica:** Este servicio existe para soportar detección de eventos en runtime, no para seguridad. Los secrets son una dependencia runtime de la detección de eventos.

6. **`core/wallet.py` – WalletService**

   **Objetivo:** Gestionar wallets como recurso operativo único, permitir rotación en runtime.

   **Por qué existe:**
   - El wallet NO es "configuración del sistema", es un recurso operativo del execution engine
   - Debe poder activarse/desactivarse en runtime
   - Solo puede haber UNA wallet activa (invariante)
   - Permite rotación manual sin reinicio
   - No depende del usuario, no vive en env vars

   **Arquitectura mental:**
   ```
   Frontend (control plane)
      │
      │  set active wallet
      ▼
   Backend
    ├── WalletService
    ├── EventEngine (global, agnóstico)
    ├── Strategy (agnóstico)
    ├── Risk (agnóstico)
    └── Execution (usa wallet activa)
   ```

   **Responsabilidades:**
   - Gestionar wallets como recurso único
   - Permitir rotación manual
   - Cachear la wallet activa (address + private key descifrada)
   - Impedir estados inválidos (más de una activa, ninguna activa)

   **API interna:**
   ```python
   class WalletService:
       def get_active_wallet() -> Wallet:
           """
           Devuelve la wallet activa (address + private key descifrada).
           Cache en memoria para acceso rápido.
           """
           pass
       
       async def set_active_wallet(wallet_id: UUID) -> None:
           """
           Cambia la wallet activa.
           - Invalida cache
           - Cancela órdenes abiertas
           - Requiere confirmación explícita
           - Solo puede haber una activa
           """
           pass
       
       async def create_wallet(label: str, address: str, private_key: str) -> Wallet:
           """Crear nueva wallet (private key se encripta antes de guardar)"""
           pass
       
       async def list_wallets() -> list[Wallet]:
           """Listar todas las wallets"""
           pass
   ```

   **Invariantes (reglas duras):**
   - Nunca ejecutar si no hay wallet activa
   - Nunca permitir más de una activa
   - Cambio de wallet:
     - Invalida cache
     - Cancela órdenes abiertas
     - Requiere confirmación explícita

   **Uso en ExecutionEngine:**
   ```python
   # En execution.py
   wallet = WalletService.get_active_wallet()
   # wallet.address y wallet.private_key (descifrada, cacheada)
   # Firmar órdenes con private_key
   # Enviar a Polymarket
   ```

   **Seguridad:**
   - Private key se almacena encriptada en DB (`encrypted_private_key`)
   - Se descifra solo cuando se cachea la wallet activa
   - Cache en memoria (no persistir private key descifrada)
   - Rotación de clave de encriptación (opcional, para producción)

### Entregables
- `SystemState` funcionando
- `SystemConfigService` cargando configuración desde DB
- `RiskConfig` cargándose correctamente desde DB
- `WalletService` funcionando con cache y gestión de wallet activa
- Loop principal corriendo (aunque los servicios aún no hagan nada)
- Estado persistiéndose a DB

---

## FASE 4: Scanner y Event Engine

### Objetivo
Implementar el descubrimiento de mercados y la detección de eventos finalizados.

### Tareas

1. **`core/scanner.py` – Market Scanner**

   Objetivo: descubrir y actualizar mercados de Polymarket candidatos.

   **Lógica:**
   - Llamar periódicamente a la API pública de Polymarket:
     - Lista de mercados
     - Precios de outcomes
   - Filtrar:
     - Solo mercados binarios (YES/NO)
     - Solo mercados OPEN
     - Solo outcomes con precio >= `MIN_CANDIDATE_PRICE` (ej. 0.97)
   
   **Para cada mercado candidato:**
   - Actualizar `state.markets[market_id]` con:
     - `last_price`
     - `spread`
     - `volume`
     - `orderbook_snapshot`
   
   **Condición de entrada "escáner":**
   - Un mercado solo pasa al pipeline de estrategia si:
     - `price >= MIN_CANDIDATE_PRICE`
     - `event_state` no está marcado como RESOLVED
     - Market está activo en Polymarket
   
   El scanner no decide entrar, solo marca candidatos.

   **Implementación:**
   - Cliente HTTP con `httpx` para Polymarket API
   - Parsing de respuesta de Polymarket
   - Actualización de `state.markets`
   - Persistencia a tabla `markets` en DB

2. **`core/checkers/` – Sistema de Checkers Dinámicos**

   **Objetivo:** Sistema pluggable de checkers que detectan finalización de eventos más rápido que Polymarket.

   **Por qué existe:**
   - La detección de eventos NO está hardcodeada
   - El bot NO asume un proveedor específico, número fijo de feeds, o tipo de evento específico
   - Los eventos se clasifican por categoría (sports, crypto, politics, etc.)
   - Cada categoría define qué checkers están activos
   - Cada checker consulta una fuente externa y retorna una señal sobre si el evento ha terminado
   - Las credenciales deben ser configurables en runtime porque:
     - Diferentes checkers se habilitan/deshabilitan dinámicamente
     - Las keys pueden cambiar o rotar
     - El operador puede querer cambiar proveedores sin redeploy
     - El event engine debe adaptarse inmediatamente

   **Arquitectura:**

   **`core/checkers/base.py`**
   ```python
   class BaseChecker(ABC):
       @abstractmethod
       async def check(
           self, 
           external_event_id: str,
           credentials: dict[str, str] | None
       ) -> CheckerResult:
           """
           Responde: ¿Según esta fuente externa, está el evento terminado?
           
           credentials: dict con API keys, tokens, etc. provistos por SecretService
           """
           pass
   
   class CheckerResult(BaseModel):
       state: Literal["LIVE", "FINISHED"]
       confidence: float  # 0.0–1.0
       finished_at: datetime | None
       raw_payload: dict  # para auditoría
       source: str
   ```

   **`core/checkers/registry.py`**
   - Registro de implementaciones de checkers disponibles
   - Mapeo `implementation_key` → clase de checker
   - Permite registrar nuevos checkers sin modificar código core

   **`core/checkers/implementations/`**
   - Implementaciones concretas de checkers:
     - `sports_checker.py` (ej. Sportradar, ESPN)
     - `crypto_checker.py` (ej. CoinGecko, exchanges)
     - `politics_checker.py` (ej. news APIs)
   - Cada checker implementa `BaseChecker`
   - Cada checker puede requerir diferentes credenciales (API key, token, etc.)

   **Flujo de ejecución de un checker:**
   1. Leer `CheckerConfig` desde DB
   2. Si `secret_name` está configurado:
      - Cargar credencial vía `SecretService.get_secret(secret_name)`
   3. Ejecutar lógica del checker usando esa credencial
   4. Retornar:
      - `state` (FINISHED / LIVE)
      - `confidence`
      - `raw_payload` (para auditoría)

   El checker nunca sabe de dónde vino la credencial, solo recibe un string.

3. **`core/event_engine.py` – Event Engine (con Checkers Dinámicos)**

   Objetivo: decidir cuándo el evento está realmente terminado usando checkers configurables en runtime.

   **Estados:**
   - `LIVE`
   - `FINISHED_UNCONFIRMED`
   - `FINISHED_CONFIRMED`

   **Flujo completo de decisión (crítico para entender):**
   ```
   Market Scanner
      ↓
   Event Engine
      ↓
   Cargar checkers activos para categoría del evento
      ↓
   Para cada checker:
      ├── Cargar credenciales dinámicamente (SecretService)
      ├── Llamar API externa
      └── Producir señal Finished / Not Finished
      ↓
   Agregar señales (reglas de quorum)
      ↓
   Establecer EventState (LIVE / FINISHED_CONFIRMED)
      ↓
   Strategy puede entrar
   ```

   **Lógica de transición:**
   - Por defecto: `LIVE`
   - Si al menos un checker indica `FINISHED`:
     - Pasar a `FINISHED_UNCONFIRMED`
   - Si ≥ 2 checkers independientes coinciden en `FINISHED` con `confidence >= MIN_FEED_CONFIDENCE`:
     - Pasar a `FINISHED_CONFIRMED`

   **Implementación:**
   1. Para cada `market` con `external_event_id` y `category` definidos:
      - Cargar `EventChecker` activos para esa categoría desde DB
      - Para cada checker activo:
        - Cargar `CheckerConfig` asociado
        - Si `secret_name` está configurado:
          - Obtener credencial vía `SecretService.get_secret(secret_name)`
        - Instanciar checker usando `implementation_key` del registry
        - Ejecutar `checker.check(external_event_id, credentials)`
        - Recibir `CheckerResult`
   2. Agregar resultados:
      - Si ≥ 2 checkers devuelven `state = FINISHED` con `confidence >= MIN_FEED_CONFIDENCE`:
        - Marcar `EventState = FINISHED_CONFIRMED`
      - Si solo 1:
        - `EventState = FINISHED_UNCONFIRMED`
      - Si ninguno:
        - `EventState = LIVE`

   **Persistencia:**
   - Actualizar `state.events[market_id]` (memoria)
   - Guardar/actualizar en tabla `events` (Neon) para histórico
   - Guardar resultados de checkers individuales para auditoría

   **Restricciones de implementación (críticas):**
   - Los checkers deben ser pluggables en runtime
   - Las credenciales deben ser hot-reloadables
   - EventEngine NO debe depender de env vars para feeds
   - La lógica de decisión debe sobrevivir cambios de config sin reinicio
   - **Las credenciales se requieren dentro del hot path de decisión**
   - Reiniciar la app cada vez que cambia una credencial es inaceptable porque:
     - Interrumpe el event loop
     - Riesgo de perder la ventana de decisión
     - Hace la experimentación imposible

   Solo mercados con `FINISHED_CONFIRMED` se consideran para compras agresivas.

### Entregables
- Scanner descubriendo mercados de Polymarket
- Sistema de checkers dinámicos funcionando (base, registry, al menos una implementación mock)
- SecretService funcionando con cache y hot-reload
- Event engine usando checkers dinámicos para determinar estados
- Estado de eventos persistiéndose en DB
- Checkers cargando credenciales dinámicamente sin reinicio

---

## FASE 5: Strategy y Risk Engine

### Objetivo
Implementar la lógica de decisión de compra y el control de riesgo.

### Tareas

1. **`core/strategy.py` – Strategy Engine**

   Objetivo: decidir:
   - Si entramos
   - A qué precio (bid)
   - Con qué tamaño (size)

   **Inputs por mercado:**
   - `market_price` (ej. 0.995, 0.999)
   - `spread` (best ask – best bid)
   - `event_state` (de event_engine)
   - `exposure_actual` (de risk_engine)

   **Parámetros de estrategia:**
   - `MIN_ENTRY_PRICE` (ej. 0.98 o 0.99)
   - `TARGET_MARGIN` (ej. 0.001–0.002)
   - `MAX_HOLD_TIME` (limitación opcional)

   **Condición para "hacer la apuesta" (comprar):**
   Un mercado se convierte en target de compra cuando:
   - `event_state == FINISHED_CONFIRMED`
   - `market_price >= MIN_ENTRY_PRICE`
   - `risk_engine` indica que hay capacidad de exposición (no se supera `MAX_EXPOSURE_PER_MARKET` ni `MAX_GLOBAL_EXPOSURE`)

   **Cálculo de precio objetivo:**
   ```python
   target_price = min(
       best_ask_price - SAFETY_TICK,
       1.0 - TARGET_MARGIN
   )
   ```
   - `TARGET_MARGIN` = margen deseado hacia 1.0 (ej. 0.001 → compras a 0.999)
   - `SAFETY_TICK` = pequeño descuento del best ask para no pagar demasiado

   **Cálculo de tamaño (size):**
   Basado en:
   - `max_per_market` (en € o USDC)
   - `current_exposure_market`
   - Liquidez disponible en orderbook al precio objetivo

   ```python
   size = min(
       MAX_EXPOSURE_PER_MARKET - current_exposure_market,
       max_orderbook_liquidity_at_target_price,
       MAX_SINGLE_ORDER_SIZE
   )
   ```

   **Resultado de `strategy.tick()`:**
   Conjunto de intenciones de orden (order intents):

   ```python
   class OrderIntent(BaseModel):
       market_id: str
       side: Literal["BUY"]
       price: float
       size: float
   ```

   Estas intenciones pasan a `risk_engine` y `execution`.

   El `StrategyService` **no envía órdenes**, solo las propone.

2. **`core/risk_engine.py` – Risk Engine**

   Objetivo: no reventar.

   **Inputs:**
   - Positions actuales
   - Orders abiertos
   - Configuración de riesgo (modificable desde frontend):
     - `MAX_EXPOSURE_PER_MARKET` (ej. 20k–100k)
     - `MAX_GLOBAL_EXPOSURE` (ej. % del bankroll)
     - `MAX_MARKETS_ACTIVE`
     - `MAX_EXPOSURE_PER_EVENT_TYPE` (opcional: deportes, política, etc.)

   **Lógica:**
   Para cada `OrderIntent`:
   1. Calcula `exposure_new_market = exposure_market_actual + intent.size * intent.price`
   2. Calcula `exposure_new_global = exposure_global_actual + intent.size * intent.price`
   3. Si se excede alguna regla:
      - Marcar intent como bloqueado
   4. Opcional: cooldown tras grandes fills (no volver a entrar en X minutos)

   **Flujo:**
   1. Calcular nueva exposición hipotética si cada `OrderIntent` se ejecutase
   2. Comprobar reglas:
      - `exposure_new_market <= MAX_EXPOSURE_PER_MARKET`
      - `exposure_new_global <= MAX_GLOBAL_EXPOSURE`
      - `num_markets_active <= MAX_MARKETS_ACTIVE`
   3. Sólo pasar a `ExecutionService` las intenciones que cumplan todas las reglas

   **Actualiza:**
   - `state.exposures` (en memoria)
   - Tabla `exposures` en DB con snapshots periódicos

   El `RiskEngine`:
   - Filtra las intenciones
   - Produce una lista de `ApprovedOrderIntents` que van a execution

### Entregables
- Strategy generando `OrderIntents` correctamente
- Risk engine validando y filtrando intenciones
- Exposiciones calculándose y persistiéndose
- Condiciones de entrada funcionando según especificación

---

## FASE 6: Execution Engine

### Objetivo
Implementar la interacción con la CLOB de Polymarket para enviar y gestionar órdenes.

### Tareas

1. **`core/execution.py` – Execution Engine**

   Objetivo: interactuar con la CLOB de Polymarket.

   **Funciones clave:**
   - Enviar órdenes limit BUY según `ApprovedOrderIntents`
   - Cancelar órdenes obsoletas (por:
     - Cambio de estado de evento
     - Cambios de riesgo
     - Pausa del sistema)
   - Recibir fills (vía polling o WebSocket de Polymarket)

   **Flujo:**
   
   **Por cada `ApprovedOrderIntent`:**
   1. Obtener wallet activa:
      - `wallet = WalletService.get_active_wallet()`
      - Si no hay wallet activa: rechazar intent (no ejecutar)
   2. Construir payload de orden:
      - `market_id`
      - `side = BUY`
      - `price`
      - `size`
   3. Firmar payload con private key de wallet activa (EIP-712)
      - Usar `wallet.private_key` (descifrada, cacheada)
   4. Enviar a endpoint de Polymarket
   5. Registrar nuevo `Order` en DB (tabla `orders`) y en `state.orders`

   **Polling / WebSocket para fills:**
   - Actualizar `filled_size`, `status`
   - Actualizar positions:
     - Si es fill BUY: aumentar `size` y recalcular `avg_price`
   - Guardar `trades` en tabla `trades` para histórico

   **Cancelaciones:**
   - Si `system_active == False` o market pausado:
     - Enviar cancel a todas las órdenes abiertas de ese mercado
   - Actualizar estado local `Order.status = CANCELLED`

   **Implementación:**
   - Cliente HTTP para API de Polymarket
   - Firma de mensajes EIP-712 (usar librería como `eth_account`)
   - **Usar `WalletService.get_active_wallet()`** para obtener wallet activa
   - **NO usar env vars para wallet** - el wallet es un recurso gestionado en DB
   - Polling de estado de órdenes
   - WebSocket opcional si Polymarket lo soporta
   - Validar que existe wallet activa antes de ejecutar órdenes

### Entregables
- Execution engine usando `WalletService.get_active_wallet()` para obtener wallet
- Validación de wallet activa antes de ejecutar órdenes
- Firma EIP-712 funcionando con private key de wallet activa
- Fills detectándose y actualizando positions
- Cancelaciones funcionando
- Estado de órdenes sincronizado con Polymarket

---

## FASE 7: API Backend básica

### Objetivo
Implementar endpoints REST para el frontend y autenticación con Stack OAuth.

### Tareas

1. **Autenticación**

   - Middleware de FastAPI para validar tokens de Stack OAuth
   - Validación usando `STACK_SECRET_SERVER_KEY`:
     - Firma del token
     - Caducidad
     - Claims mínimos (`sub`, `email`)
   - Mapeo `sub` → `users.stack_oauth_user_id`
   - Crear/actualizar usuario en DB si no existe
   - Decorador o dependencia para rutas protegidas
   
   **Integración con Neon Database:**
   - El JWT validado de Stack Auth se usa para autenticarse con Neon
   - NO se requiere API key adicional de Neon
   - Las queries a Neon se autentican usando el JWT del usuario autenticado
   - Configurar SQLAlchemy para pasar el JWT en las conexiones a Neon

2. **Endpoints principales**

   **`GET /health`**
   - Devuelve `{"status": "ok"}` y meta de versión
   - Sin auth (para checks de despliegue)

   **`GET /dashboard`**
   - Devuelve:
     ```json
     {
       "equity": 123456.78,
       "realized_pnl": 2345.67,
       "unrealized_pnl": 890.12,
       "global_exposure": 45678.9,
       "active_markets": 12,
       "system_active": true
     }
     ```

   **`GET /markets`**
   - Listado de mercados activos y recientes:
     ```json
     [
       {
         "market_id": "uuid",
         "polymarket_id": "xxx",
         "question": "BTC up or down",
         "outcome": "UP",
         "status": "OPEN",
         "last_price": 0.999,
         "event_state": "FINISHED_CONFIRMED",
         "exposure": 50000,
         "created_at": "...",
         "updated_at": "..."
       }
     ]
     ```
   - Opciones de filtro: `status`, `event_state`
   - Paginación opcional

   **`GET /positions`**
   - Devuelve:
     ```json
     [
       {
         "market_id": "uuid",
         "polymarket_id": "xxx",
         "size": 100000,
         "avg_price": 0.998,
         "current_price": 0.999,
         "unrealized_pnl": 100,
         "resolved": false,
         "payout": null
       }
     ]
     ```

   **`GET /risk/config`**
   - Devuelve la configuración actual:
     ```json
     {
       "max_exposure_per_market": 50000,
       "max_global_exposure": 500000,
       "min_entry_price": 0.98,
       "target_margin": 0.001,
       "max_markets_active": 30
     }
     ```

   **`POST /risk/config`**
   - Actualiza configuración (solo usuario con rol admin)
   - Body:
     ```json
     {
       "max_exposure_per_market": 60000,
       "max_global_exposure": 600000,
       "min_entry_price": 0.99,
       "target_margin": 0.0015,
       "max_markets_active": 25
     }
     ```
   - Los cambios se aplican inmediatamente (invalidación de cache)

   **`GET /system/config`**
   - Devuelve toda la configuración del sistema (desde tabla `system_config`):
     ```json
     {
       "system": {
         "tick_seconds": 1.0,
         "scan_interval_seconds": 30.0,
         "checker_timeout_seconds": 5.0
       },
       "scanner": {
         "min_candidate_price": 0.97,
         "min_volume": 1000.0
       },
       "event_engine": {
         "min_feed_confidence": 0.8
       },
       "risk": {
         "max_exposure_per_market": 50000.0,
         "max_global_exposure": 500000.0,
         "max_markets_active": 30,
         "min_entry_price": 0.98,
         "target_margin": 0.001,
         "safety_tick": 0.0001,
         "max_single_order_size": 10000.0
       }
     }
     ```

   **`GET /system/config/{key}`**
   - Obtener un valor de configuración específico:
     ```json
     {
       "key": "tick_seconds",
       "value": "1.0",
       "value_type": "float",
       "category": "system",
       "description": "Intervalo entre ticks del loop principal"
     }
     ```

   **`PUT /system/config/{key}`**
   - Actualizar un valor de configuración (solo admin):
     ```json
     {
       "value": "2.0",
       "description": "Nueva descripción (opcional)"
     }
     ```
   - Los cambios se aplican inmediatamente (invalidación de cache en `SystemConfigService`)
   - No requiere reinicio del sistema

   **`POST /control/pause`**
   - Pone `state.system_active = False`
   - Cancela todas las órdenes abiertas
   - No se generan nuevas órdenes

   **`POST /control/resume`**
   - Pone `state.system_active = True`
   - El loop vuelve a actuar (scanner, estrategia, etc.)

   **`POST /control/market/{market_id}/pause`**
   - Pausa solo un market concreto: no se generan nuevas órdenes para ese market, pero el sistema sigue activo para el resto

   **`GET /wallets`**
   - Lista todas las wallets (solo admin):
     ```json
     [
       {
         "id": "uuid",
         "label": "main",
         "address": "0x...",
         "active": true,
         "created_at": "...",
         "updated_at": "..."
       }
     ]
     ```
   - **NO se expone `private_key`** (ni encriptada ni descifrada)

   **`POST /wallets`**
   - Crear nueva wallet (solo admin):
     ```json
     {
       "label": "backup",
       "address": "0x...",
       "private_key": "0x..."  # Se encripta antes de guardar
     }
     ```
   - La nueva wallet se crea como inactiva por defecto

   **`PUT /wallets/{wallet_id}/activate`**
   - Activar una wallet (solo admin):
     - Desactiva automáticamente la wallet activa actual
     - Activa la wallet especificada
     - Invalida cache en `WalletService`
     - **Cancela todas las órdenes abiertas** (requiere confirmación explícita)
     - Body opcional para confirmación:
       ```json
       {
         "confirm": true,
         "cancel_open_orders": true
       }
       ```

   **`GET /wallets/active`**
   - Obtener wallet activa:
     ```json
     {
       "id": "uuid",
       "label": "main",
       "address": "0x...",
       "active": true
     }
     ```
   - **NO se expone `private_key`**

   **`DELETE /wallets/{wallet_id}`**
   - Eliminar wallet (solo admin):
     - No se puede eliminar si está activa
     - Requiere desactivarla primero

   **`GET /checkers`**
   - Lista todos los checkers disponibles (desde `event_checkers`):
     ```json
     [
       {
         "id": "uuid",
         "implementation_key": "sportradar_v1",
         "category": "sports",
         "name": "Sportradar API",
         "description": "Sports event results",
         "enabled": true
       }
     ]
     ```

   **`POST /checkers`**
   - Crear nuevo checker (solo admin)
   - Body:
     ```json
     {
       "implementation_key": "sportradar_v1",
       "category": "sports",
       "name": "Sportradar API",
       "description": "Sports event results"
     }
     ```

   **`PUT /checkers/{checker_id}`**
   - Actualizar checker (habilitar/deshabilitar, etc.) (solo admin)

   **`GET /checkers/{checker_id}/configs`**
   - Obtener configuraciones de un checker:
     ```json
     [
       {
         "id": "uuid",
         "checker_id": "uuid",
         "secret_name": "sportradar_api_key",
         "weight": 1.0,
         "timeout_seconds": 5.0,
         "enabled": true
       }
     ]
     ```

   **`POST /checkers/{checker_id}/configs`**
   - Crear o actualizar configuración de checker (solo admin)
   - Body:
     ```json
     {
       "secret_name": "sportradar_api_key",
       "weight": 1.0,
       "timeout_seconds": 5.0,
       "enabled": true
     }
     ```
   - Si `secret_name` cambia, invalidar cache en `SecretService`

   **`GET /secrets`**
   - Lista todos los secrets (solo admin, valores enmascarados):
     ```json
     [
       {
         "name": "sportradar_api_key",
         "description": "Sportradar API key",
         "created_at": "...",
         "has_value": true
       }
     ]
     ```
   - Los valores reales NO se exponen en listado

   **`GET /secrets/{secret_name}`**
   - Obtener un secret específico (solo admin):
     ```json
     {
       "name": "sportradar_api_key",
       "value": "actual_key_value",
       "description": "Sportradar API key"
     }
     ```

   **`POST /secrets`** o **`PUT /secrets/{secret_name}`**
   - Crear o actualizar secret (solo admin)
   - Body:
     ```json
     {
       "name": "sportradar_api_key",
       "value": "new_api_key_value",
       "description": "Sportradar API key"
     }
     ```
   - Al actualizar: invalidar cache en `SecretService` para ese secret
   - **No requiere reinicio**: el cambio es inmediato

   **`DELETE /secrets/{secret_name}`**
   - Eliminar secret (solo admin)
   - Invalidar cache

   **`GET /checkers/implementations`**
   - Lista todas las implementaciones de checkers disponibles en el registry:
     ```json
     [
       {
         "key": "sportradar_v1",
         "category": "sports",
         "description": "Sportradar API checker",
         "required_credentials": ["api_key"]
       }
     ]
     ```

3. **Organización de endpoints**
   - `api/markets.py`: endpoints de mercados
   - `api/positions.py`: endpoints de posiciones
   - `api/risk.py`: endpoints de riesgo
   - `api/system.py`: endpoints de configuración del sistema
   - `api/wallets.py`: endpoints de gestión de wallets
   - `api/history.py`: endpoints de histórico (Fase 8)
   - `api/control.py`: endpoints de control
   - `api/checkers.py`: endpoints de checkers y secrets

4. **Validación y errores**
   - Pydantic models para request/response
   - Manejo de errores consistente
   - Códigos HTTP apropiados

### Entregables
- Autenticación con Stack OAuth funcionando
- Todos los endpoints REST implementados (incluyendo `/wallets`, `/system/config`, `/checkers`, `/secrets`)
- Validación de requests
- Control de acceso por roles
- Endpoints de wallets permitiendo rotación en runtime

---

## FASE 8: Métricas y persistencia

### Objetivo
Implementar el cálculo de métricas y el sistema de histórico.

### Tareas

1. **`core/metrics.py` – Metrics & History Engine**

   Objetivo: poder:
   - Ver historial de entradas (qué compramos, cuándo, a qué precio)
   - Ver resultados (cuánto pagó cada market)
   - Calcular PnL, win-rate, drawdown

   **Métricas calculadas:**

   **Realized PnL por market:**
   - `cost_total = Σ (fill_size * fill_price)` de todos los BUY en ese market
   - Si outcome ganado: `payout_total = size_total * 1.0`
   - Si perdido: `payout_total = 0`
   - `realized_pnl = payout_total - cost_total`
   - Se guarda en `positions.payout` y se expone en `/history`

   **Unrealized PnL:**
   - Para markets no resueltos:
     - `theoretical_value = size_total * current_price` (de Polymarket)
     - `cost_total = size_total * avg_price`
     - `unrealized_pnl = theoretical_value - cost_total`

   **Win-rate de mercados:**
   - Markets donde nuestra posición fue en el outcome ganador vs total

   **Max drawdown:**
   - Respecto a equity

   **Exposición:**
   - Por market: `exposure_market = size_total * avg_price`
   - Global: `exposure_global = Σ exposure_market`
   - El RiskEngine compara esto con los límites de config

   **Persistencia:**
   - Todo se persiste en tablas:
     - `trades`
     - `positions`
     - `markets` (con resolución)
     - `payouts` (puede integrarse en positions)

2. **Endpoints de histórico**

   **`GET /history/trades`**
   - Devuelve el histórico de fills (paginado):
     ```json
     {
       "items": [
         {
           "trade_id": "uuid",
           "market_id": "uuid",
           "polymarket_id": "xxx",
           "fill_price": 0.999,
           "fill_size": 1000,
           "direction": "BUY",
           "timestamp": "..."
         }
       ],
       "next_cursor": null
     }
     ```

   **`GET /history/markets`**
   - Resumen PnL por market:
     ```json
     [
       {
         "market_id": "uuid",
         "polymarket_id": "xxx",
         "question": "BTC up or down",
         "outcome": "UP",
         "resolved": true,
         "resolution_outcome": "UP",
         "cost_total": 12345.67,
         "payout_total": 12456.78,
         "realized_pnl": 111.11,
         "resolved_at": "..."
       }
     ]
     ```

   **`GET /history/equity`** (opcional)
   - Serie temporal de equity para gráficos

3. **Cálculos críticos**

   **Condición exacta de entrada ("cuándo apuesta el bot"):**
   Para cada market:
   - `event_state == FINISHED_CONFIRMED`
   - `current_price >= MIN_ENTRY_PRICE`
   - `exposure_market + (size * price) <= MAX_EXPOSURE_PER_MARKET`
   - `exposure_global + (size * price) <= MAX_GLOBAL_EXPOSURE`
   - Estrategia fija: `target_price = min(1 - TARGET_MARGIN, best_ask - SAFETY_TICK)`
   - Si `size > 0` y todas las condiciones se cumplen: se genera `OrderIntent`

### Entregables
- Métricas calculándose correctamente
- Endpoints de histórico funcionando
- PnL (realized y unrealized) preciso
- Win-rate y drawdown calculándose

---

## FASE 9: Frontend básico (autenticación y dashboard)

### Objetivo
Implementar autenticación con Stack OAuth y el dashboard básico.

### Tareas

1. **Integración con Stack OAuth**
   - Instalar SDK de Stack OAuth para React
   - Wrapper `<AuthProvider>` en `layout.tsx`
   - Rutas protegidas:
     - `/` (dashboard)
     - `/markets`
     - `/positions`
     - `/history`
     - `/risk`
     - `/settings`
   - Al autenticarse:
     - Se obtiene `access_token`
     - Se añade a headers `Authorization: Bearer <token>` en `lib/api.ts`

2. **Layout general**
   - Sidebar con navegación:
     - Dashboard
     - Markets
     - Positions
     - History
     - Risk
     - Settings
   - Header:
     - Estado del sistema (ON/OFF)
     - Usuario logeado (Stack OAuth)
     - Botón de Logout

3. **`lib/api.ts`**
   - Cliente HTTP para backend
   - Interceptores para añadir token
   - Funciones helper para cada endpoint

4. **Dashboard (`/` - `page.tsx`)**
   - Componentes:
     - Card: Equity total
     - Card: PnL realized
     - Card: PnL unrealized
     - Card: Global exposure
     - Gráfico: Equity vs tiempo (usar Recharts, datos desde `/history/equity`)
     - Tabla: Últimos trades
   - Se actualiza vía:
     - Polling (`GET /dashboard` cada X segundos)
     - WebSocket para eventos importantes (Fase 11)

5. **Estilos básicos**
   - Tailwind CSS configurado
   - Componentes reutilizables básicos (Card, Button, Table)

### Entregables
- Autenticación funcionando
- Dashboard mostrando datos básicos
- Layout y navegación funcionando
- Cliente API configurado

---

## FASE 10: Frontend completo (todas las páginas)

### Objetivo
Implementar todas las páginas restantes del frontend.

### Tareas

1. **`/markets`**
   - Tabla con:
     - `market_id`
     - `question`
     - `outcome`
     - `last_price`
     - `event_state`
     - `exposure`
     - `status` (OPEN/RESOLVED/PAUSED)
   - Acciones:
     - Ver detalle
     - Pausar/unpausar mercado
   - Al clicar un market:
     - Página de detalle:
       - Precios históricos (mini chart si quieres)
       - Trades en ese market
       - PnL por market
       - Exposición actual
       - Event state (fuentes confirmadas, timestamps)

2. **`/positions`**
   - Tabla:
     - `polymarket_id`
     - `question`
     - `size`
     - `avg_price`
     - `current_price`
     - `unrealized_pnl`
     - `resolved`
     - `payout` (si aplica)
   - Filtros:
     - Solo abiertos
     - Solo resueltos
     - PnL positivo / negativo

3. **`/history`**
   - Subsecciones:
     - **Trades:**
       - Tabla paginada de todos los fills
     - **Markets:**
       - PnL por market, con filtros de fecha
     - **Equity:**
       - Gráfico de equity/time, win-rate, drawdown

4. **`/risk`**
   - Form con sliders/inputs:
     - `max_exposure_per_market`
     - `max_global_exposure`
     - `min_entry_price`
     - `target_margin`
     - `max_markets_active`
   - Botón "Guardar" → `POST /risk/config`
   - Mostrar:
     - Exposición actual vs límites

5. **`/settings`**
   - **Gestión de Wallets:**
     - Lista de wallets existentes:
       - Mostrar: `label`, `address`, estado `active`
       - Indicador visual de wallet activa
     - Botón "Añadir Wallet":
       - Form: `label`, `address`, `private_key`
       - La nueva wallet se crea como inactiva
       - `POST /wallets`
     - Activar wallet:
       - Botón "Activar" en cada wallet inactiva
       - Modal de confirmación:
         - Advertencia: "Esto cancelará todas las órdenes abiertas"
         - Checkbox: "Cancelar órdenes abiertas"
         - Confirmar → `PUT /wallets/{id}/activate`
       - **Cambio aplicado inmediatamente** (invalida cache, cancela órdenes)
     - Eliminar wallet:
       - Solo si está inactiva
       - `DELETE /wallets/{id}`
     - Ver wallet activa:
       - Card destacada mostrando wallet activa actual
       - `GET /wallets/active`
   
   - **Configuración del Sistema:**
     - Ajustar `tick_seconds` (intervalo del loop principal)
     - Ajustar `scan_interval_seconds` (intervalo de escaneo)
     - Ajustar `checker_timeout_seconds` (timeout de checkers)
     - Ajustar `min_candidate_price` (precio mínimo candidato)
     - Ajustar `min_feed_confidence` (confianza mínima de checkers)
     - Todos los cambios se guardan vía `PUT /system/config/{key}`
     - **Cambios aplicados inmediatamente sin reinicio**
   
   - **Configuración de Riesgo:**
     - Ya gestionada en `/risk`, pero también accesible desde aquí
   
   - **Zona de debug:**
     - Ver estado bruto (solo admin)
     - Ver configuración completa del sistema

6. **`/checkers` (nueva página, parte del control plane)**

   **Por qué existe:**
   - El frontend es el control plane del bot, no solo "admin UI"
   - El operador debe poder agregar nuevos proveedores de API, pegar nuevas API keys, activar/desactivar checkers, y ver inmediatamente su efecto en la detección de eventos
   - Si esto requiere redeploy, el sistema es inutilizable y la estrategia no puede adaptarse

   **Funcionalidades:**

   **Gestión de Secrets:**
   - Lista de secrets existentes (valores enmascarados)
   - Botón "Añadir Secret":
     - Form: `name`, `value`, `description`
     - Al guardar: `POST /secrets`
     - **Cambio es inmediato**: no requiere reinicio
   - Editar secret existente:
     - Cambiar valor
     - Invalidar cache automáticamente
   - Eliminar secret

   **Gestión de Checkers:**
   - Lista de checkers disponibles (desde `GET /checkers`)
   - Para cada checker:
     - Ver implementaciones disponibles (`GET /checkers/implementations`)
     - Crear nuevo checker:
       - Seleccionar `implementation_key`
       - Especificar `category`, `name`, `description`
     - Ver configuraciones del checker
     - Crear/editar configuración:
       - Asignar `secret_name` (dropdown de secrets disponibles)
       - Ajustar `weight`, `timeout_seconds`
       - Habilitar/deshabilitar
     - Habilitar/deshabilitar checker completo

   **Flujos críticos que el frontend debe soportar:**
   1. Añadir o actualizar una credencial (secret)
   2. Asignar esa credencial a uno o más checkers
   3. Habilitar o deshabilitar esos checkers
   4. Observar transiciones de estado de eventos impulsadas por esos checkers

   **UI/UX:**
   - Sección "Secrets" con tabla y formulario
   - Sección "Checkers" con:
     - Lista de checkers por categoría
     - Para cada checker: lista de configuraciones
     - Formulario para crear/editar configuración
   - Indicadores visuales:
     - Checker habilitado/deshabilitado
     - Secret asignado/no asignado
     - Estado de última ejecución del checker (opcional)
   - Feedback inmediato:
     - "Secret actualizado - cambios aplicados sin reinicio"
     - "Checker habilitado - activo en próximo tick"

   **Nota:** Esta página es parte del trading loop, no un afterthought. El operador debe poder experimentar con diferentes proveedores y configuraciones en tiempo real.

7. **Componentes reutilizables**
   - Tablas con paginación
   - Formularios con validación
   - Modales
   - Gráficos (Recharts)

### Entregables
- Todas las páginas implementadas
- Navegación funcionando entre páginas
- Formularios guardando configuración
- Visualización de datos completa

---

## FASE 11: WebSocket y tiempo real

### Objetivo
Implementar comunicación WebSocket para actualizaciones en tiempo real.

### Tareas

1. **Backend WebSocket**

   **`ws://.../stream`**
   - Canal de eventos en tiempo real para el frontend
   - Tipos de eventos:
     - `ORDER_FILLED`
     - `RISK_ALERT`
     - `SYSTEM_STATUS_CHANGED`
     - `MARKET_UPDATED`
     - `POSITION_UPDATED`

   **Ejemplo:**
   ```json
   {
     "type": "RISK_ALERT",
     "payload": {
       "market_id": "uuid",
       "exposure": 95000,
       "max_allowed": 100000
     }
   }
   ```

   **Implementación:**
   - Endpoint WebSocket en FastAPI
   - Broadcast de eventos desde los servicios core
   - Gestión de conexiones (múltiples clientes)
   - Reconexión automática en frontend

2. **Frontend WebSocket**

   **`lib/ws.ts`**
   - Cliente WebSocket
   - Reconexión automática
   - Manejo de eventos
   - Integración con React (hooks, context)

   **Uso en componentes:**
   - Dashboard: actualizar métricas en tiempo real
   - Markets: actualizar precios y estados
   - Positions: actualizar PnL
   - Notificaciones de alertas de riesgo

3. **Eventos a emitir**
   - Desde `execution.py`: `ORDER_FILLED`
   - Desde `risk_engine.py`: `RISK_ALERT`
   - Desde control: `SYSTEM_STATUS_CHANGED`
   - Desde `scanner.py`: `MARKET_UPDATED`
   - Desde `execution.py` (fills): `POSITION_UPDATED`

### Entregables
- WebSocket funcionando backend y frontend
- Eventos en tiempo real actualizando UI
- Reconexión automática
- Dashboard y otras páginas actualizándose en tiempo real

---

## FASE 12: Despliegue y optimizaciones

### Objetivo
Preparar el sistema para producción y optimizaciones finales.

### Tareas

1. **Backend - Despliegue**

   **Contenedor Docker:**
   - `Dockerfile` con Python 3.12
   - FastAPI + Uvicorn
   - Alembic para migraciones
   - Variables de entorno (solo variables técnicas esenciales):
     ```bash
     # Autenticación y DB
     STACK_SECRET_SERVER_KEY='ssk_j7z6yr2krm7v1gd6g3vfef1vt3r2bdqfs2f9a70qc2tv8'
     DATABASE_URL='postgresql://neondb_owner:npg_yIe73bNMWgLz@ep-lively-union-a4iepcwe-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require'
     DATA_API_ENDPOINT='https://ep-lively-union-a4iepcwe.apirest.us-east-1.aws.neon.tech/neondb/rest/v1'
     
     # Polymarket
     POLYMARKET_API_URL='https://api.polymarket.com'
     
     # Server
     ENVIRONMENT=production
     HOST=0.0.0.0
     PORT=8000
     CORS_ORIGINS=https://tudominio.com
     
     # Logging
     LOG_LEVEL=INFO
     LOG_FORMAT=json
     ```
     - **Nota**: Toda la configuración del sistema y riesgo se almacena en la tabla `system_config` de la DB
     - **Nota**: Los wallets se gestionan en la tabla `wallets` de la DB (NO como env vars)
     - **Nota**: En producción, usar secret manager (AWS Secrets Manager, Vault, etc.) para `STACK_SECRET_SERVER_KEY`
     - **Nota**: Las private keys de wallets se almacenan encriptadas en la DB

   **Arranque:**
   - `alembic upgrade head`
   - `uvicorn app.main:app`
   - El loop principal se lanza desde startup event de FastAPI

   **Optimizaciones:**
   - Connection pooling para DB
   - Logging estructurado (JSON)
   - Health checks
   - Graceful shutdown

2. **Frontend - Despliegue**

   **Next.js desplegado en Vercel / similar:**
   - Variables de entorno:
     ```bash
     # Stack Auth (public keys para Next.js)
     NEXT_PUBLIC_STACK_PROJECT_ID='32ee526b-a970-4239-b401-c0af891804f9'
     NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY='pck_61kjyfggywecv7bpaxm4n7j82640qse8q1y2e09cqphg0'
     
     # Backend URL
     NEXT_PUBLIC_BACKEND_URL='https://api.tudominio.com'
     ```
   - El frontend solo habla con el backend, no directamente con Polymarket ni con Neon

   **Optimizaciones:**
   - Build optimizado
   - Lazy loading de componentes
   - Caching de datos cuando sea apropiado

3. **Neon Database**

   - Proyecto Neon ya configurado con DB `neondb`
   - **Importante**: Neon NO requiere API key adicional
   - La autenticación se realiza usando el JWT de Stack Auth
   - Configurar branches `dev` y `prod` si es necesario
   - Usar `DATABASE_URL` de cada branch en los entornos correspondientes
   - Backup strategy
   - El backend debe configurarse para pasar el JWT en las conexiones a Neon

4. **Monitoreo y logs**

   - Logging estructurado (JSON)
   - Métricas expuestas (opcional: Prometheus)
   - Alertas para errores críticos
   - Dashboard de monitoreo (opcional)

5. **Testing**

   - Tests unitarios para lógica crítica
   - Tests de integración para API
   - Tests end-to-end para flujos principales

6. **Documentación**

   - README con instrucciones de setup
   - Documentación de API (OpenAPI/Swagger)
   - Guía de despliegue

### Entregables
- Sistema desplegado en producción
- Monitoreo funcionando
- Logs estructurados
- Documentación completa
- Tests básicos

---

## Resumen de fases

1. **Fase 1**: Setup inicial y estructura del proyecto
2. **Fase 2**: Base de datos y modelos
3. **Fase 3**: Sistema de estado y configuración
4. **Fase 4**: Scanner y Event Engine
5. **Fase 5**: Strategy y Risk Engine
6. **Fase 6**: Execution Engine
7. **Fase 7**: API Backend básica
8. **Fase 8**: Métricas y persistencia
9. **Fase 9**: Frontend básico (autenticación y dashboard)
10. **Fase 10**: Frontend completo (todas las páginas)
11. **Fase 11**: WebSocket y tiempo real
12. **Fase 12**: Despliegue y optimizaciones

---

## Servicios internos (resumen)

### `ScannerService`
- Responsabilidad: Conectarse periódicamente a la API pública de Polymarket, mapear markets de Polymarket → `markets` internos, actualizar `state.markets` y tabla `markets`.
- Inputs: `SCAN_INTERVAL_SECONDS`, `MIN_CANDIDATE_PRICE`, `MIN_VOLUME`, API Key / endpoints de Polymarket.
- Outputs: `MarketState` actualizado en memoria (`last_price`, `spread`, `orderbook_snapshot`), nuevos registros / updates en DB.

### `CheckerSystem` (Sistema de Checkers Dinámicos)
- Responsabilidad: Sistema pluggable de checkers que detectan finalización de eventos más rápido que Polymarket.
- Arquitectura: Checkers son plugins runtime que responden "¿Está el evento terminado según esta fuente externa?"
- Cada checker puede requerir credenciales (API keys, tokens) que se cargan dinámicamente vía `SecretService`.
- Los checkers se registran por `implementation_key` y se asignan a categorías (sports, crypto, politics, etc.).
- **Crítico**: Las credenciales son hot-reloadables sin reinicio. Esto permite cambiar proveedores de API sobre la marcha, rotar keys durante operación, y experimentar con diferentes checkers de forma segura.

### `SecretService`
- Responsabilidad: Proporcionar credenciales a checkers durante ejecución sin requerir reinicio.
- Funcionalidades: Cache en memoria para acceso rápido, invalidación de cache cuando se actualiza un secret, actualizaciones en vivo desde frontend.
- **Nota crítica**: Este servicio existe para soportar detección de eventos en runtime, no para seguridad. Los secrets son una dependencia runtime de la detección de eventos.

### `EventEngine` (con Checkers Dinámicos)
- Responsabilidad: Determinar `EventState` de cada market usando checkers configurables en runtime.
- Flujo completo: Para cada `market` con `external_event_id` y `category` definidos → Cargar checkers activos para esa categoría → Para cada checker: cargar credenciales dinámicamente (SecretService) → Llamar API externa → Producir señal Finished/Not Finished → Agregar señales (reglas de quorum) → Establecer EventState.
- Lógica: Si ≥ 2 checkers independientes coinciden en `FINISHED` con `confidence >= MIN_FEED_CONFIDENCE`: `FINISHED_CONFIRMED`. Si solo 1: `FINISHED_UNCONFIRMED`. Si ninguno: `LIVE`.
- **Restricciones críticas**: Checkers deben ser pluggables en runtime, credenciales hot-reloadables, EventEngine NO debe depender de env vars para feeds, la lógica de decisión debe sobrevivir cambios de config sin reinicio.
- Persistencia: Actualizar `state.events[market_id]`, guardar/actualizar en tabla `events`, guardar resultados de checkers individuales para auditoría.

### `StrategyService`
- Responsabilidad: Procesar `MarketState`, `EventState`, `ExposureState`, producir `OrderIntents` (intenciones de compra).
- Flujo: Ignorar cualquier market donde `event_state != FINISHED_CONFIRMED` o `market_price < MIN_ENTRY_PRICE`. Calcular `target_price = min(1 - TARGET_MARGIN, best_ask - SAFETY_TICK)`. Estimar tamaño máximo posible según liquidez en el orderbook al `target_price`, límites duros de tamaño por orden (`MAX_SINGLE_ORDER_SIZE`). Construir `OrderIntent` (si el tamaño mínimo es aceptable).
- El `StrategyService` **no envía órdenes**, solo las propone.

### `RiskEngine`
- Responsabilidad: Validar o rechazar `OrderIntents` según reglas de riesgo.
- Flujo: Calcular nueva exposición hipotética si cada `OrderIntent` se ejecutase. Comprobar reglas: `exposure_new_market <= MAX_EXPOSURE_PER_MARKET`, `exposure_new_global <= MAX_GLOBAL_EXPOSURE`, `num_markets_active <= MAX_MARKETS_ACTIVE`. Sólo pasar a `ExecutionService` las intenciones que cumplan todas las reglas.
- Actualiza: `state.exposures` (en memoria), tabla `exposures` en DB con snapshots periódicos.

### `ExecutionService`
- Responsabilidad: Traducir `ApprovedOrderIntents` a órdenes reales en Polymarket, mantener `orders` y `trades` consistentes.
- Flujo: Para cada `ApprovedOrderIntent`: Construir payload de orden CLOB, firmar con clave de wallet, enviar a Polymarket, crear registro `Order` en DB y en `state.orders`. Fills: Vía WebSocket / polling a Polymarket, actualizar `Order.status`, `filled_size`, `Position.size`, `avg_price`, crear `Trade` en DB. Cancelaciones: Trigger manual (desde frontend) o automático (riesgo o pausa), enviar `cancel` a Polymarket, actualizar estado local `Order.status = CANCELLED`.

### `MetricsService`
- Responsabilidad: Calcular y exponer métricas clave: PnL (realizado y no realizado), exposición por mercado, histórico de equity, win-rate, drawdown, etc.
- Datos: Usa `trades`, `positions`, `markets` y resoluciones para recalcular PnL, construir series temporales para el frontend.
- Expone: Endpoints `/history/*` para el frontend, datos agregados para el dashboard.

---

## Cálculos críticos (referencia rápida)

### PnL por market
Para un market resuelto:
- `cost_total = Σ (fill_size * fill_price)` de todos los BUY en ese market
- Si outcome ganado: `payout_total = size_total * 1.0`
- Si perdido: `payout_total = 0`
- `realized_pnl = payout_total - cost_total`

### PnL no realizado (unrealized)
Para markets no resueltos:
- `theoretical_value = size_total * current_price` (de Polymarket)
- `cost_total = size_total * avg_price`
- `unrealized_pnl = theoretical_value - cost_total`

### Exposición
- Por market: `exposure_market = size_total * avg_price`
- Global: `exposure_global = Σ exposure_market`

### Condición exacta de entrada ("cuándo apuesta el bot")
Para cada market:
- `event_state == FINISHED_CONFIRMED`
- `current_price >= MIN_ENTRY_PRICE`
- `exposure_market + (size * price) <= MAX_EXPOSURE_PER_MARKET`
- `exposure_global + (size * price) <= MAX_GLOBAL_EXPOSURE`
- Estrategia fija: `target_price = min(1 - TARGET_MARGIN, best_ask - SAFETY_TICK)`
- Si `size > 0` y todas las condiciones se cumplen: se genera `OrderIntent`

---

## Sistema de Detección Dinámica de Eventos (Checkers) - Arquitectura y Justificación

### Objetivo del Sistema

El sistema debe detectar la finalización de eventos **más rápido que Polymarket**. Esto se logra consultando proveedores de datos externos (APIs deportivas, feeds financieros, etc.) a través de un sistema de checkers pluggable.

### Por Qué Este Diseño Existe

**El problema fundamental:**
- La detección de eventos NO está hardcodeada
- El bot NO asume:
  - Un proveedor específico (ej. Sportradar)
  - Un número fijo de feeds
  - Un tipo de evento específico

**La solución:**
- Los eventos se clasifican por categoría (sports, crypto, politics, etc.)
- Cada categoría define qué checkers están activos
- Cada checker:
  - Consulta una fuente externa
  - Retorna una señal sobre si el evento ha terminado

**Por qué las credenciales deben ser configurables en runtime:**
- Diferentes checkers se habilitan/deshabilitan dinámicamente
- Las keys pueden cambiar o rotar
- El operador puede querer cambiar proveedores sin redeploy
- El event engine debe adaptarse inmediatamente

**Los secrets NO son una característica de seguridad, son una dependencia runtime de la detección de eventos.**

### Flujo Completo de Decisión (Crítico para Entender)

```
Market Scanner
   ↓
Event Engine
   ↓
Cargar checkers activos para categoría del evento
   ↓
Para cada checker:
   ├── Cargar credenciales dinámicamente (SecretService)
   ├── Llamar API externa
   └── Producir señal Finished / Not Finished
   ↓
Agregar señales (reglas de quorum)
   ↓
Establecer EventState (LIVE / FINISHED_CONFIRMED)
   ↓
Strategy puede entrar
```

**Las credenciales se requieren dentro de este hot path de decisión.**

### Modelo de Datos - Por Qué Existe (No Solo Qué Almacena)

**Tabla `event_checkers`:**
- Define qué tipos de señales puede usar el sistema
- Permite soportar múltiples proveedores para la misma categoría
- Permite cambiar proveedores sin cambiar código
- Campos clave: `implementation_key` (selecciona qué clase instanciar), `category` (determina para qué eventos aplica)

**Tabla `checker_configs`:**
- Define cómo se comporta un checker en runtime
- Permite habilitar/deshabilitar checkers dinámicamente
- Permite ajustar pesos y timeouts en vivo
- Campo crítico: `secret_name` (enlace entre checker logic y sus credenciales runtime)

**Tabla `secrets`:**
- Existe solo porque la detección de eventos depende de APIs externas
- Permite cambiar proveedores de API sobre la marcha
- Permite rotar keys durante operación
- Permite experimentar con diferentes checkers de forma segura
- **NO es autenticación de usuario, NO es OAuth, NO es secrets genéricos**
- **Es infraestructura de detección de eventos**

### Ejecución de Checkers (Lo Que Cursor Debe Implementar)

Cuando se ejecuta un checker:

1. Leer `CheckerConfig` desde DB
2. Si `secret_name` está configurado:
   - Cargar credencial vía `SecretService.get_secret(secret_name)`
3. Ejecutar lógica del checker usando esa credencial
4. Retornar:
   - `state` (FINISHED / LIVE)
   - `confidence`
   - `raw_payload` (para auditoría)

**El checker nunca sabe de dónde vino la credencial. Solo sabe que recibió un string.**

### Frontend - Requisito Funcional (No "Settings UI")

**Por qué el frontend debe gestionar esto:**
- El frontend es el control plane del bot, no "admin UI"
- El operador debe poder:
  - Añadir un nuevo proveedor de API
  - Pegar una nueva API key
  - Activar/desactivar un checker
  - Ver inmediatamente su efecto en la detección de eventos

**Si esto requiere redeploy:**
- El sistema es inutilizable
- La estrategia no puede adaptarse

**Flujos que el frontend debe soportar:**
1. Añadir o actualizar una credencial (secret)
2. Asignar esa credencial a uno o más checkers
3. Habilitar o deshabilitar esos checkers
4. Observar transiciones de estado de eventos impulsadas por esos checkers

**El frontend es parte del trading loop, no un afterthought.**

### Por Qué Este Diseño Importa (Explícitamente)

Este sistema está construido para explotar la asimetría de tiempo-hasta-resolución.

**La asimetría desaparece si:**
- Los feeds están hardcodeados
- Las credenciales son estáticas
- La configuración requiere reinicios

**Esta arquitectura existe solo para preservar esa asimetría.**

### Restricciones de Implementación Que Cursor Debe Respetar

1. **Checkers deben ser pluggables en runtime**
   - No hardcodear implementaciones
   - Usar registry pattern

2. **Credenciales deben ser hot-reloadables**
   - Cache en memoria con invalidación
   - No requerir reinicio

3. **EventEngine NO debe depender de env vars para feeds**
   - Todo debe venir de DB/config
   - Secrets desde tabla `secrets`

4. **La lógica de decisión debe sobrevivir cambios de config sin reinicio**
   - Cargar checkers activos en cada tick
   - Cargar credenciales bajo demanda

5. **Reiniciar la app cada vez que cambia una credencial es inaceptable porque:**
   - Interrumpe el event loop
   - Riesgo de perder la ventana de decisión
   - Hace la experimentación imposible

### Resumen (Para Cursor)

**Esto NO es "gestión de secrets".**

**Esto es:**
Un motor de detección de eventos configurable en runtime cuya corrección y rentabilidad dependen de cambiar y credencializar dinámicamente fuentes de datos externas sin interrumpir la ejecución.

**Los secrets existen solo porque:**
- La detección de eventos depende de APIs externas
- Y esas APIs deben ser cambiables en vivo

**Si Cursor entiende esto, implementará lo correcto.**

---

## Resumen Completo de Variables de Entorno

### Backend (`.env`)

**Solo variables técnicas esenciales. Toda la configuración del sistema, riesgo y wallets va en la DB.**

#### Autenticación y Base de Datos
- `STACK_SECRET_SERVER_KEY` - **REQUERIDO** - Server key de Stack Auth para validar tokens
- `DATABASE_URL` - **REQUERIDO** - Connection string de Neon Database
- `DATA_API_ENDPOINT` - Opcional - Endpoint REST de Neon (si se necesita)

#### Polymarket
- `POLYMARKET_API_URL` - **REQUERIDO** - URL base de la API de Polymarket
- `POLYMARKET_API_KEY` - Opcional - Solo si la API pública requiere autenticación

#### Server
- `ENVIRONMENT` - Default: `development` - Entorno: `development`, `staging`, `production`
- `HOST` - Default: `0.0.0.0` - Host del servidor
- `PORT` - Default: `8000` - Puerto del servidor FastAPI
- `CORS_ORIGINS` - Default: `http://localhost:3000` - Orígenes permitidos (separados por comas)

#### Logging
- `LOG_LEVEL` - Default: `INFO` - Nivel: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- `LOG_FORMAT` - Default: `json` - Formato: `json` o `text`

### Recursos en Base de Datos

#### Wallets (`wallets`)

**Los wallets se gestionan como recursos operativos en la tabla `wallets`:**

- `id` - UUID, PK
- `label` - String (ej. "main", "backup", "testing")
- `address` - String (public address)
- `encrypted_private_key` - Bytes (clave privada encriptada)
- `active` - Boolean (SOLO UNA puede estar activa)
- `created_at`, `updated_at` - Timestamps

**Características:**
- Solo puede haber UNA wallet activa (invariante)
- Se gestiona desde el frontend (control plane)
- Permite rotación en runtime sin reinicio
- Private key se almacena encriptada en DB
- Se descifra solo cuando se cachea la wallet activa

#### Configuración (`system_config`)

**Toda esta configuración se almacena en la tabla `system_config` y se puede modificar desde el frontend:**

#### Sistema
- `tick_seconds` - Default: `1.0` - Intervalo entre ticks del loop principal
- `scan_interval_seconds` - Default: `30.0` - Intervalo entre escaneos de mercados
- `checker_timeout_seconds` - Default: `5.0` - Timeout máximo para checkers

#### Scanner
- `min_candidate_price` - Default: `0.97` - Precio mínimo para considerar candidato
- `min_volume` - Opcional - Volumen mínimo en USDC

#### Event Engine
- `min_feed_confidence` - Default: `0.8` - Confianza mínima requerida (0.0-1.0)

#### Configuración de Riesgo
- `max_exposure_per_market` - Default: `50000.0` - Exposición máxima por mercado (USDC)
- `max_global_exposure` - Default: `500000.0` - Exposición global máxima (USDC)
- `max_markets_active` - Default: `30` - Número máximo de mercados activos
- `min_entry_price` - Default: `0.98` - Precio mínimo de entrada
- `target_margin` - Default: `0.001` - Margen objetivo hacia 1.0
- `safety_tick` - Default: `0.0001` - Descuento del best ask
- `max_single_order_size` - Default: `10000.0` - Tamaño máximo de orden (USDC)

### Frontend (`.env.local`)

#### Stack Auth (Public Keys)
- `NEXT_PUBLIC_STACK_PROJECT_ID` - **REQUERIDO** - Project ID de Stack Auth
- `NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY` - **REQUERIDO** - Client key pública

#### Backend
- `NEXT_PUBLIC_BACKEND_URL` - **REQUERIDO** - URL del backend API

### Variables Críticas de Seguridad

⚠️ **NUNCA commitear en código o repositorio:**
- `STACK_SECRET_SERVER_KEY` - Server key de Stack Auth
- Cualquier secret almacenado en la tabla `secrets` (se gestionan desde el frontend)

---

## Rate Limiting y Gestión de Límites de API de Polymarket

### Restricciones de Rate Limits de Polymarket

Polymarket impone límites estrictos de rate limiting en todos sus endpoints. El bot debe implementar una capa interna de rate limiting para evitar throttling o bloqueos.

**Límites clave:**
- **Data API**: max 200 req / 10s (cuello de botella principal)
- **Alternative Data API**: 1200 req/min con bloqueo de 10 minutos en caso de violación
- **CLOB book/price/midprice**: ~200 req / 10s por endpoint
- **Trading POST /order**: 2400 req / 10s (suficiente para ejecución en ráfaga)

### Arquitectura de Rate Limiting

#### `core/rate_limiter.py` - RateLimiter con Ventanas Deslizantes

**Implementación:**
- Ventana deslizante por endpoint usando `deque` de timestamps
- Thread-safe para operaciones async con `asyncio.Lock`
- Soporte para bloqueo temporal (Alternative Data API: 10 minutos)
- Métodos principales:
  - `acquire(endpoint)` - Adquirir permiso para hacer una request
  - `wait_for_capacity(endpoint, timeout)` - Esperar hasta que haya capacidad
  - `make_request(endpoint, timeout)` - Hacer request con rate limiting
  - `record_violation(endpoint)` - Registrar violación (bloquea endpoint si aplica)

**Endpoints configurados:**
```python
EndpointType.DATA_API          # 200 req / 10s
EndpointType.ALTERNATIVE_DATA_API  # 1200 req/min (bloqueo 10min)
EndpointType.CLOB_BOOK         # 200 req / 10s
EndpointType.CLOB_PRICE        # 200 req / 10s
EndpointType.CLOB_MIDPRICE     # 200 req / 10s
EndpointType.TRADING_ORDER     # 2400 req / 10s
```

#### `core/api_cache.py` - Caché de Respuestas API

**Objetivo:** Reducir llamadas redundantes a Data API.

**Características:**
- Caché en memoria con TTL por tipo de dato
- TTLs por defecto:
  - `market_list`: 30 segundos
  - `market_detail`: 10 segundos
  - `orderbook`: 5 segundos
  - `price`: 5 segundos
  - `event_data`: 60 segundos
- Limpieza automática de entradas expiradas (cada 60 segundos)
- Thread-safe para operaciones async

### Integración en Componentes

#### Scanner (`core/scanner.py`)
- **Endpoint usado:** `DATA_API` (200 req / 10s)
- **Caché:** Lista de mercados se cachea por 30 segundos
- **Flujo:**
  1. Verificar caché antes de hacer request
  2. Si no hay caché, esperar capacidad con `wait_for_capacity()`
  3. Hacer request a Polymarket
  4. Cachear resultado
  5. Manejar errores 429 (Too Many Requests) registrando violación

#### EventEngine (`core/event_engine.py`)
- **Nota:** EventEngine no hace llamadas directas a Polymarket Data API
- Los checkers usan APIs externas (sports, crypto, etc.)
- Si EventEngine necesita datos de Polymarket en el futuro:
  - **Batching:** Agrupar mercados por categoría y hacer requests en lotes
  - **Caché:** Usar `api_cache` con TTL apropiado
  - **Rate limiting:** Usar `rate_limiter` con `EndpointType.DATA_API`

#### Execution (`core/execution.py`)
- **Endpoints usados:**
  - `TRADING_ORDER` (2400 req / 10s) para enviar/cancelar órdenes
  - `DATA_API` (200 req / 10s) para polling de estado de órdenes
- **Flujo:**
  1. Esperar capacidad con timeout corto (1-2 segundos)
  2. Hacer request
  3. Manejar errores 429 registrando violación
  4. Si timeout, skip request y reintentar en siguiente tick

### Requisitos de Implementación

1. **Ningún componente puede exceder límites de Data API**
   - El motor de eventos arriesga bloqueo de 10 minutos si se viola
   - Scanner debe usar caché agresivamente
   - EventEngine debe hacer batching si necesita Data API

2. **MarketScanner debe solo trackear mercados activos/near-resolution**
   - No escanear todos los mercados continuamente
   - Filtrar candidatos antes de hacer requests

3. **EventEngine debe hacer batching y caching de Data API requests**
   - Agrupar mercados por categoría
   - Hacer requests en lotes (max 10 mercados por batch)
   - Cachear resultados con TTL apropiado

4. **RateLimiter con ventanas deslizantes debe implementarse por endpoint**
   - Cada endpoint tiene su propia ventana deslizante
   - Thread-safe para operaciones concurrentes

5. **ExecutionEngine puede hacer high-burst trading pero debe mantenerse dentro de límites**
   - Trading API tiene límite generoso (2400 req / 10s)
   - Aún así debe usar rate limiter para evitar violaciones

### Manejo de Errores

**Error 429 (Too Many Requests):**
- Registrar violación con `rate_limiter.record_violation()`
- Para Alternative Data API, esto bloquea el endpoint por 10 minutos
- Retry con backoff exponencial

**Timeout de Rate Limit:**
- Si `wait_for_capacity()` retorna `False` (timeout):
  - Scanner: Retornar lista vacía o datos cacheados
  - Execution: Skip request, reintentar en siguiente tick
  - EventEngine: Usar datos cacheados o skip mercado

### Monitoreo

**Métricas útiles:**
- Tasa de hits/misses del caché
- Tiempo de espera promedio en rate limiter
- Número de timeouts de rate limit
- Violaciones registradas (especialmente Alternative Data API)

### Variables Críticas de Seguridad

⚠️ **NUNCA commitear en código o repositorio:**
- `STACK_SECRET_SERVER_KEY` - Server key de Stack Auth
- Cualquier secret almacenado en la tabla `secrets` (se gestionan desde el frontend)
- Private keys de wallets (se almacenan encriptadas en la tabla `wallets`)

**Recomendación para producción:**
- Usar secret manager (AWS Secrets Manager, HashiCorp Vault, etc.) para `STACK_SECRET_SERVER_KEY`
- Variables de entorno en el servicio de despliegue (Vercel, Railway, etc.)
- Rotación periódica de keys
- Encriptación fuerte para private keys en tabla `wallets` (usar clave de encriptación separada)

### Migración Inicial de Configuración

**Al crear la tabla `system_config`, se debe ejecutar una migración de datos que inserte los valores por defecto:**

```python
# En la migración de Alembic, después de crear la tabla system_config
default_configs = [
    {"key": "tick_seconds", "value": "1.0", "value_type": "float", "category": "system"},
    {"key": "scan_interval_seconds", "value": "30.0", "value_type": "float", "category": "scanner"},
    {"key": "min_candidate_price", "value": "0.97", "value_type": "float", "category": "scanner"},
    {"key": "min_feed_confidence", "value": "0.8", "value_type": "float", "category": "event_engine"},
    {"key": "checker_timeout_seconds", "value": "5.0", "value_type": "float", "category": "event_engine"},
    {"key": "max_exposure_per_market", "value": "50000.0", "value_type": "float", "category": "risk"},
    {"key": "max_global_exposure", "value": "500000.0", "value_type": "float", "category": "risk"},
    {"key": "max_markets_active", "value": "30", "value_type": "int", "category": "risk"},
    {"key": "min_entry_price", "value": "0.98", "value_type": "float", "category": "risk"},
    {"key": "target_margin", "value": "0.001", "value_type": "float", "category": "risk"},
    {"key": "safety_tick", "value": "0.0001", "value_type": "float", "category": "risk"},
    {"key": "max_single_order_size", "value": "10000.0", "value_type": "float", "category": "risk"},
]
```

Estos valores se pueden modificar después desde el frontend sin reiniciar el sistema.
