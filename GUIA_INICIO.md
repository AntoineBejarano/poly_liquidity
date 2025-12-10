# Guía de Inicio - PolyLiquidity Desk

## Prerrequisitos

- **Python 3.12** instalado
- **Node.js 18+** y **npm** instalados
- **Base de datos Neon** configurada con `DATABASE_URL`
- **Stack Auth** configurado con `STACK_SECRET_SERVER_KEY`

## Paso 1: Configurar Backend

### 1.1. Crear entorno virtual

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
```

### 1.2. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 1.3. Configurar variables de entorno

Crear archivo `backend/.env` con:

```env
# Stack Auth (REQUERIDO)
STACK_SECRET_SERVER_KEY=tu_stack_secret_server_key_aqui

# Database (REQUERIDO)
DATABASE_URL=postgresql://usuario:password@host/database?sslmode=require

# Polymarket (Opcional)
POLYMARKET_API_URL=https://api.polymarket.com
POLYMARKET_API_KEY=tu_api_key_si_la_tienes

# Server (Opcional, valores por defecto)
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000

# Logging (Opcional)
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 1.4. Ejecutar migraciones de base de datos

```powershell
cd backend
python -m alembic upgrade head
```

### 1.5. Iniciar servidor backend

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El backend estará disponible en: `http://localhost:8000`

## Paso 2: Configurar Frontend

### 2.1. Instalar dependencias

```powershell
cd frontend
npm install
```

### 2.2. Configurar variables de entorno

Crear archivo `frontend/.env.local` con:

```env
# Stack Auth (REQUERIDO)
NEXT_PUBLIC_STACK_PROJECT_ID=tu_project_id_aqui
NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY=tu_publishable_client_key_aqui

# Backend (REQUERIDO)
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### 2.3. Iniciar servidor de desarrollo

```powershell
cd frontend
npm run dev
```

El frontend estará disponible en: `http://localhost:3000`

## Paso 3: Verificar que todo funciona

1. **Backend Health Check:**
   - Abrir: `http://localhost:8000/health`
   - Debería retornar: `{"status": "ok", ...}`

2. **Frontend:**
   - Abrir: `http://localhost:3000`
   - Deberías ver la página de login de Stack Auth

## Comandos Útiles

### Backend

```powershell
# Activar entorno virtual
cd backend
.\venv\Scripts\activate

# Ejecutar migraciones
python -m alembic upgrade head

# Crear nueva migración
python -m alembic revision -m "descripcion"

# Ver estado de migraciones
python -m alembic current
python -m alembic history

# Iniciar servidor
uvicorn app.main:app --reload
```

### Frontend

```powershell
# Instalar dependencias
npm install

# Desarrollo
npm run dev

# Build para producción
npm run build

# Iniciar producción
npm start

# Linting
npm run lint
```

## Solución de Problemas

### Error: "STACK_SECRET_SERVER_KEY not found"
- Verifica que el archivo `backend/.env` existe y tiene la variable `STACK_SECRET_SERVER_KEY`

### Error: "DATABASE_URL not found"
- Verifica que el archivo `backend/.env` existe y tiene la variable `DATABASE_URL`
- Asegúrate de que la URL de Neon incluye los parámetros de autenticación

### Error: "Multiple heads are present" en Alembic
- Ya debería estar resuelto con la migración de merge `003_merge_users_migrations.py`
- Si persiste, ejecuta: `python -m alembic heads` para verificar

### Error: "Module not found" en Python
- Asegúrate de que el entorno virtual está activado
- Reinstala dependencias: `pip install -r requirements.txt`

### Error: "Port 8000 already in use"
- Cambia el puerto: `uvicorn app.main:app --reload --port 8001`
- O mata el proceso que está usando el puerto

### Frontend no se conecta al backend
- Verifica que `NEXT_PUBLIC_BACKEND_URL` en `frontend/.env.local` apunta al backend correcto
- Verifica que el backend está corriendo
- Revisa la consola del navegador para errores CORS

## Estructura de URLs

- **Backend API:** `http://localhost:8000`
- **Backend Docs (Swagger):** `http://localhost:8000/docs`
- **Backend Health:** `http://localhost:8000/health`
- **Frontend:** `http://localhost:3000`

## Próximos Pasos

1. **Configurar Stack Auth:**
   - Obtener `STACK_SECRET_SERVER_KEY` desde el dashboard de Stack Auth
   - Configurar `NEXT_PUBLIC_STACK_PROJECT_ID` y `NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY`

2. **Configurar Base de Datos:**
   - Crear branch en Neon Database
   - Obtener `DATABASE_URL` desde el dashboard de Neon
   - Ejecutar migraciones

3. **Configurar Sistema:**
   - Una vez iniciado, acceder al frontend
   - Configurar parámetros de riesgo en `/risk`
   - Agregar wallets en `/settings/wallets`
   - Configurar checkers en `/settings/checkers`


