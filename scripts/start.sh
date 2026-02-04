#!/bin/bash
set -e

# Esperar a que la base de datos esté lista (opcional; falla silencioso si no hay DB)
wait_for_db() {
    echo "Esperando base de datos..."
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if (cd /app/backend && PYTHONPATH=/app/backend python -c "
import sys
try:
    from app.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('Base de datos lista')
    sys.exit(0)
except Exception as e:
    print(e, file=sys.stderr)
    sys.exit(1)
" 2>/dev/null); then
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    echo "No se pudo conectar a la base de datos (seguimos igual para SQLite/local)"
    return 0
}
wait_for_db || true

# Migraciones (Alembic)
echo "Ejecutando migraciones..."
cd /app/backend
export PYTHONPATH=/app/backend
alembic upgrade head || true

# Arrancar la API (Railway inyecta PORT)
PORT=${PORT:-8000}
export PYTHONPATH=/app/backend
cd /app/backend
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
