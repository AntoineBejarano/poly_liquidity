# Servidores Iniciados

## Estado Actual

### Frontend (Next.js con pnpm)
- ✅ **Puerto**: 3000
- ✅ **Estado**: Corriendo
- ✅ **URL**: http://localhost:3000
- ✅ **Proceso**: PID 15888

### Backend (FastAPI con uvicorn)
- ⚠️ **Puerto**: 8000
- ⚠️ **Estado**: Iniciando o requiere configuración
- ⚠️ **URL**: http://localhost:8000
- ⚠️ **Procesos Python**: 2 procesos corriendo (PIDs 14052, 21816)

## Variables de Entorno Requeridas

El backend requiere las siguientes variables de entorno en `backend/.env`:

### Esenciales
```env
STACK_SECRET_SERVER_KEY=tu_stack_secret_server_key_aqui
DATABASE_URL=postgresql://usuario:password@host/database?sslmode=require
```

### Opcionales (para funcionalidad completa)
```env
# Polymarket Trading
POLYMARKET_API_KEY=...
POLYMARKET_API_SECRET=...
POLYMARKET_API_PASSPHRASE=...

# Wallet
PRIVATE_KEY=0x...
FUNDER_ADDRESS=0x...

# RPC
RPC_URL=https://polygon-rpc.com/
CHAIN_ID=137
```

## Comandos para Iniciar

### Backend
```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```powershell
cd frontend
pnpm run dev
```

## Verificación

### Backend Health Check
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/health"
```

### Frontend
```powershell
Invoke-WebRequest -Uri "http://localhost:3000"
```

## Páginas Disponibles

Una vez ambos servidores estén corriendo:

- **Frontend**: http://localhost:3000
  - Dashboard: http://localhost:3000/dashboard
  - Configuración: http://localhost:3000/settings/config
  - Decision Traces: http://localhost:3000/decision-traces
  - Mercados: http://localhost:3000/markets
  - Posiciones: http://localhost:3000/positions

- **Backend API**: http://localhost:8000
  - Health: http://localhost:8000/health
  - Docs: http://localhost:8000/docs
  - Config: http://localhost:8000/system/config
  - Decision Traces: http://localhost:8000/system/decision-traces




