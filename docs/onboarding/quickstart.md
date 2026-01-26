# Quickstart Guide

**Purpose**: Step-by-step guide for new engineers to set up and run the system.

**Audience**: New engineers, developers setting up the development environment.

**Where this is used**: Initial setup, onboarding process.

**Last updated**: 2025-01-XX

---

## Prerequisites

- **Python 3.12** installed
- **Node.js 18+** and **npm** installed
- **PostgreSQL** database (or Neon for cloud)
- **Stack Auth** account

---

## Step 1: Backend Setup

### 1.1. Create Virtual Environment

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
```

### 1.2. Install Dependencies

```powershell
pip install -r requirements.txt
```

**Main Dependencies:**
- FastAPI 0.124.4 - Web framework
- Uvicorn 0.38.0 - ASGI server
- SQLAlchemy 2.0.45 - ORM
- Alembic 1.17.2 - Database migrations
- asyncpg 0.31.0 - PostgreSQL async client
- httpx 0.28.1 - HTTP async client
- py-clob-client 0.31.0 - Official Polymarket CLOB client
- websockets 15.0.1 - WebSockets
- cryptography 46.0.3 - Cryptography

### 1.3. Configure Environment Variables

Create `backend/.env` file:

```env
# Stack Auth (REQUIRED)
STACK_SECRET_SERVER_KEY=sk_live_...

# Database (REQUIRED)
DATABASE_URL=postgresql://user:password@host/database?sslmode=require
# Or for local: DATABASE_URL=sqlite:///./poly_liquidity.db

# Polymarket (Optional - needed for real trading)
PRIVATE_KEY=0x...
FUNDER_ADDRESS=0x...
RPC_URL=https://polygon-rpc.com/
CHAIN_ID=137

# Server (Optional, defaults)
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 1.4. Run Database Migrations

```powershell
cd backend
python -m alembic upgrade head
```

### 1.5. Start Backend Server

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at: `http://localhost:8000`

---

## Step 2: Frontend Setup

### 2.1. Install Dependencies

```powershell
cd frontend
pnpm install
```

**Main Dependencies:**
- Next.js 16.0.10 - React framework
- React 19.2.3 - UI library
- @stackframe/stack 2.8.56 - Authentication
- TypeScript 5.9.3 - Static typing
- Tailwind CSS 4.1.18 - Styling

### 2.2. Configure Environment Variables

Create `frontend/.env.local` file:

```env
# Stack Auth (REQUIRED)
NEXT_PUBLIC_STACK_PROJECT_ID=prj_...
NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY=pk_live_...

# Backend (REQUIRED)
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### 2.3. Start Development Server

```powershell
cd frontend
pnpm run dev
```

Frontend available at: `http://localhost:3000`

---

## Step 3: Verify Setup

### 3.1. Check Backend Health

```bash
curl http://localhost:8000/health
```

Should return: `{"status": "ok"}`

### 3.2. Check Frontend

Open browser: `http://localhost:3000`

Should see login page or dashboard.

---

## Getting Credentials

### Stack Auth

1. Go to https://stack-auth.com
2. Create a project
3. Get credentials:
   - `STACK_SECRET_SERVER_KEY` (backend)
   - `NEXT_PUBLIC_STACK_PROJECT_ID` (frontend)
   - `NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY` (frontend)

### Polymarket (for real trading)

1. Go to https://polymarket.com/settings
2. Find **Proxy Address** → this is `FUNDER_ADDRESS`
3. Export private key from MetaMask → this is `PRIVATE_KEY` (must start with `0x`)

**Note:** You do NOT need to create API keys manually. The system generates them automatically.

---

## Common Issues

### Backend won't start

- Check `DATABASE_URL` is correct
- Check `STACK_SECRET_SERVER_KEY` is set
- Verify Python 3.12 is installed
- Check port 8000 is not in use

### Frontend won't start

- Check Node.js 18+ is installed
- Verify `NEXT_PUBLIC_BACKEND_URL` points to running backend
- Check Stack Auth credentials are correct

### Database connection errors

- Verify `DATABASE_URL` format
- Check database is accessible
- For Neon, ensure SSL mode is set: `?sslmode=require`

---

## Next Steps

1. Read [`../architecture/system-overview.md`](../architecture/system-overview.md) for system architecture
2. Review [`../strategies/README.md`](../strategies/README.md) for strategy concepts
3. Check [`../infrastructure/secrets.md`](../infrastructure/secrets.md) for security setup
4. See [`../operations/runbook.md`](../operations/runbook.md) for operational procedures

---

## Related Documentation

- [`../infrastructure/secrets.md`](../infrastructure/secrets.md) - Environment variables
- [`../architecture/system-overview.md`](../architecture/system-overview.md) - System architecture
- [`../operations/runbook.md`](../operations/runbook.md) - Operations guide



