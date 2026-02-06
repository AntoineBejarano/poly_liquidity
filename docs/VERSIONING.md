# Versionado de la aplicación

La app muestra la versión en el frontend (cuadro Conectado/Desconectado) y en el backend (`GET /health`).

## Versión automática en cada despliegue

**Si construyes con Docker sin pasar versión**, cada build usa la **fecha y hora del build** como versión: `YYYY.MM.DD.HHMMSS` (ej. `2026.02.06.143052`). Así cada despliegue tiene una versión distinta sin configurar nada.

- **Backend:** el Dockerfile genera `/app/version.txt` en la imagen; el health lo lee.
- **Frontend:** el Dockerfile genera la versión en la etapa de build y la embebe en el bundle.

## Versión manual (opcional)

Puedes fijar la versión con build args:

```bash
# Backend
docker build -f backend/Dockerfile.backend --build-arg APP_VERSION=v1.2.3 -t poly-backend .

# Frontend
docker build -f frontend/Dockerfile.frontend \
  --build-arg NEXT_PUBLIC_APP_VERSION=v1.2.3 \
  --build-arg NEXT_PUBLIC_API_URL=https://tu-api.com \
  -t poly-frontend .
```

O con git: `APP_VERSION=$(git describe --tags --always)`.

## Docker Compose

En `docker-compose.yml` los build args usan `${APP_VERSION:-dev}`. Si no defines `APP_VERSION`, se usa `dev` y **dentro del Dockerfile** se sustituye por la fecha/hora del build (porque el default del ARG es `dev`). Así `docker compose build` ya genera versión automática.

Para forzar una versión concreta:

```bash
APP_VERSION=v1.2.0 docker compose build
```

O en un `.env` en la raíz: `APP_VERSION=v1.2.0`.

## Dónde se muestra

- **Frontend:** dentro del cuadro "Conectado / Desconectado" (sidebar y header móvil), como "Conectado · v2026.02.06.143052".
- **Backend:** en `GET /health`, campo `version`.

## Variables de entorno / build args

| Variable | Dónde | Uso |
|----------|--------|-----|
| `APP_VERSION` | Backend (build arg) | Si no se pasa o es `dev`, se usa timestamp del build. Si se pasa, se escribe en `/app/version.txt`. |
| `NEXT_PUBLIC_APP_VERSION` | Frontend (build arg) | Si no se pasa o es `dev`, se usa timestamp del build en `npm run build`. |

En Railway u otro CI: al hacer `docker build` sin build args, la versión será automática (timestamp). Si quieres semver o git, pasa el build arg en la configuración del servicio.
