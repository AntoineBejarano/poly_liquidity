# PolyLiquidity Desk

Sistema monolítico para proveer liquidez de cashout near-resolution en Polymarket y ejecutar estrategia de pre-settlement arbitrage.

## Stack Tecnológico

### Backend
- Python 3.12
- FastAPI
- SQLAlchemy + Alembic
- Neon Database (PostgreSQL)

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Stack OAuth

## Setup Inicial

### Backend

1. Crear entorno virtual:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus valores
```

4. Ejecutar servidor:
```bash
uvicorn app.main:app --reload
```

### Frontend

1. Instalar dependencias:
```bash
cd frontend
npm install
```

2. Configurar variables de entorno:
```bash
cp .env.local.example .env.local
# Editar .env.local con tus valores
```

3. Ejecutar servidor de desarrollo:
```bash
npm run dev
```

## Estructura del Proyecto

```
polyliquidity/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints REST
│   │   ├── core/         # Lógica del bot
│   │   ├── models/       # Modelos SQLAlchemy
│   │   ├── main.py       # FastAPI app
│   │   ├── settings.py   # Configuración
│   │   └── database.py   # Conexión DB
│   ├── alembic/          # Migraciones
│   └── requirements.txt
├── frontend/
│   ├── app/              # Next.js App Router
│   ├── components/       # Componentes React
│   └── lib/              # Utilidades
└── docs/                 # Documentación
```

## Fases de Desarrollo

Ver `docs/tech_view.md` para el plan completo de desarrollo.

## Notas

- La configuración del sistema y riesgo se almacena en la tabla `system_config` de la DB
- Los wallets se gestionan en la tabla `wallets` de la DB
- Los secrets de checkers se gestionan en la tabla `secrets` de la DB

