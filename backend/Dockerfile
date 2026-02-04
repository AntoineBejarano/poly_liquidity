# Build context: raíz del repositorio (monorepo).
# Ejemplo: docker build -f backend/Dockerfile .
# Railway usa contexto = raíz; no uses este archivo con contexto = backend/.

FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python (rutas desde la raíz del repo)
COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Código de la aplicación
COPY backend/ /app/backend/
COPY scripts/ /app/scripts/

RUN chmod +x /app/scripts/start.sh

EXPOSE 8000

CMD ["/app/scripts/start.sh"]
