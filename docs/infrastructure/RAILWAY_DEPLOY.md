# Despliegue en Railway (monorepo frontend + backend)

Este proyecto está preparado para desplegar **dos servicios en Railway** desde el mismo repositorio usando Docker.

## Estructura

- **Backend:** `backend/Dockerfile.backend`, `backend/railway.json`, `scripts/start.sh`
- **Frontend:** `frontend/Dockerfile.frontend`, `frontend/railway.json`, `next.config.js` con `output: 'standalone'`

El **contexto de build es la raíz del repo** en ambos servicios (no usar Root Directory en Railway).

## Desplegar en Railway

### 1. Proyecto y repositorio

1. Crea un proyecto en [Railway](https://railway.app) y conecta el repositorio (GitHub/GitLab).
2. Añade un servicio de **PostgreSQL** si vas a usar BD en la nube (recomendado). Railway te dará `DATABASE_URL`.

### 2. Servicio Backend

1. **New → Service** → “Deploy from GitHub repo” (mismo repo).
2. **Build:**
   - Builder: **DOCKERFILE**
   - Dockerfile path: `backend/Dockerfile.backend`
3. **Variables de entorno** (en Settings → Variables):
   - `PORT` — Railway la asigna; el script `start.sh` la usa.
   - `DATABASE_URL` — Connection string de PostgreSQL (ej. del addon de Railway).
   - `CORS_ORIGINS` — URL pública del frontend, ej. `https://tu-frontend.railway.app`
   - Resto según `backend/.env.example` (Stack Auth, Polymarket, Redis, etc.).
4. Genera dominio público para el backend y copia la URL (ej. `https://backend-xxx.railway.app`).

### 3. Servicio Frontend

1. **New → Service** → mismo repo.
2. **Build:**
   - Builder: **DOCKERFILE**
   - Dockerfile path: `frontend/Dockerfile.frontend`
3. **Variables de entorno** (deben estar en el build; son `NEXT_PUBLIC_*`):
   - `NEXT_PUBLIC_BACKEND_URL` o `NEXT_PUBLIC_API_URL` — URL pública del backend (ej. `https://backend-xxx.railway.app`)
   - `NEXT_PUBLIC_APP_URL` — URL pública del frontend (ej. `https://frontend-xxx.railway.app`)
   - `NEXT_PUBLIC_STACK_PROJECT_ID` y `NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY` — Stack Auth.
4. Si cambias cualquier `NEXT_PUBLIC_*`, hay que **volver a desplegar** (rebuild) para que se embeban en el build.
5. Genera dominio público para el frontend.

### 4. Revisar CORS

En el backend, `CORS_ORIGINS` debe incluir la URL del frontend en Railway (con `https://` y sin barra final).

## Build local (opcional)

Desde la raíz del repo:

```bash
# Backend
docker build -f backend/Dockerfile.backend -t poly-backend .

# Frontend (pasar ARGs si necesitas NEXT_PUBLIC_* en build)
docker build -f frontend/Dockerfile.frontend \
  --build-arg NEXT_PUBLIC_API_URL=https://tu-backend.railway.app \
  -t poly-frontend .
```

## Checklist

- [ ] Repo con `backend/` y `frontend/` en la raíz.
- [ ] Backend: `backend/Dockerfile.backend`, `backend/railway.json`, `scripts/start.sh`.
- [ ] Frontend: `output: 'standalone'` en `next.config.js`, `frontend/Dockerfile.frontend`, `frontend/railway.json`.
- [ ] En Railway: dos servicios, **sin** Root Directory; cada uno con su Dockerfile path.
- [ ] Variables: backend (`PORT`, `DATABASE_URL`, `CORS_ORIGINS`, …), frontend (`NEXT_PUBLIC_*`) y rebuild al cambiar `NEXT_PUBLIC_*`.
