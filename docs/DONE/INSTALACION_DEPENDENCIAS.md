# Instalación de Dependencias

## Backend (Python)

### Instalación

```powershell
cd backend
pip install -r requirements.txt
```

### Dependencias Principales Instaladas

- ✅ **FastAPI** 0.124.4 - Framework web
- ✅ **Uvicorn** 0.38.0 - Servidor ASGI
- ✅ **SQLAlchemy** 2.0.45 - ORM
- ✅ **Alembic** 1.17.2 - Migraciones de base de datos
- ✅ **asyncpg** 0.31.0 - Cliente PostgreSQL async
- ✅ **psycopg2-binary** 2.9.11 - Cliente PostgreSQL (instalado globalmente)
- ✅ **httpx** 0.28.1 - Cliente HTTP async
- ✅ **pydantic** 2.12.5 - Validación de datos
- ✅ **py-clob-client** 0.31.0 - Cliente oficial de Polymarket CLOB
- ✅ **websockets** 15.0.1 - WebSockets
- ✅ **cryptography** 46.0.3 - Criptografía
- ✅ **python-jose** 3.5.0 - JWT tokens

### Nota sobre psycopg2-binary

En Windows, `psycopg2-binary` puede requerir compilación. Si falla:
- Ya está instalado globalmente (versión 2.9.11)
- O usar `asyncpg` que es puro Python y funciona mejor en Windows

## Frontend (Next.js con pnpm)

### Instalación

```powershell
cd frontend
pnpm install
```

### Configuración

Se creó `frontend/.npmrc` con:
```
auto-install-peers=true
shamefully-hoist=false
```

### Dependencias Principales Instaladas

- ✅ **Next.js** 16.0.10 - Framework React
- ✅ **React** 19.2.3 - Biblioteca UI
- ✅ **React DOM** 19.2.3 - Renderizado React
- ✅ **@stackframe/stack** 2.8.56 - Autenticación
- ✅ **@tailwindcss/postcss** 4.1.18 - CSS framework
- ✅ **TypeScript** 5.9.3 - Tipado estático
- ✅ **Tailwind CSS** 4.1.18 - Estilos

### Nota sobre Peer Dependencies

Hay un warning sobre `lucide-react` que requiere React 16-18, pero funciona con React 19.

## Verificación

### Backend

```powershell
cd backend
python -c "import fastapi, uvicorn, sqlalchemy, alembic; print('Backend dependencies OK')"
```

### Frontend

```powershell
cd frontend
pnpm run build
```

## Comandos Útiles

### Backend

```powershell
# Activar entorno virtual (si usas venv)
.\venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```powershell
# Instalar dependencias
pnpm install

# Desarrollo
pnpm run dev

# Build
pnpm run build

# Producción
pnpm start
```

