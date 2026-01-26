# Variables de Entorno Requeridas

## 🔴 Backend - OBLIGATORIAS

Estas variables son **necesarias** para que el servidor inicie:

```bash
# Stack Auth (autenticación)
STACK_SECRET_SERVER_KEY=sk_live_...  # Clave secreta de Stack Auth

# Base de Datos
DATABASE_URL=postgresql://user:password@host:port/dbname
# O para desarrollo local:
# DATABASE_URL=sqlite:///./poly_liquidity.db
```

## 🟡 Backend - OPCIONALES (pero necesarias para trading real)

Estas variables son **opcionales** para iniciar el servidor, pero **necesarias** para operar en Polymarket:

```bash
# Wallet Privada (hex string con "0x")
PRIVATE_KEY=0x1234567890abcdef...

# Dirección de Proxy Wallet (visible en polymarket.com/settings)
FUNDER_ADDRESS=0x1234567890abcdef...
# O alternativamente:
POLYMARKET_PROXY_ADDRESS=0x1234567890abcdef...

# Credenciales API L2 de Polymarket (OPCIONALES - se generan automáticamente)
# El sistema genera estas credenciales automáticamente usando PRIVATE_KEY y FUNDER_ADDRESS
# Solo necesarias si quieres usar credenciales pre-generadas
# POLYMARKET_API_KEY=tu_api_key
# POLYMARKET_API_SECRET=tu_api_secret
# POLYMARKET_API_PASSPHRASE=tu_passphrase

# Configuración de Red Blockchain
CHAIN_ID=137  # Polygon mainnet (default: 137)
RPC_URL=https://polygon-rpc.com/  # URL de tu proveedor RPC
```

## 🔵 Backend - OPCIONALES (funcionalidades adicionales)

```bash
# Builders (para MEV protection, opcional)
BUILDER_API_KEY=...
BUILDER_SECRET=...
BUILDER_PASSPHRASE=...

# Wallet Encryption (solo si usas wallets en DB, no necesario si usas PRIVATE_KEY)
# Para generar una clave: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
WALLET_ENCRYPTION_KEY=base64_encoded_fernet_key

# Notificaciones (opcional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
EMAIL_CONFIG={"smtp_host": "...", "smtp_port": 587, ...}

# URLs de API (tienen valores por defecto, solo cambiar si necesario)
POLYMARKET_API_URL=https://api.polymarket.com
POLYMARKET_DATA_API_URL=https://data-api.polymarket.com
POLYMARKET_GAMMA_API_URL=https://gamma-api.polymarket.com
POLYMARKET_TRADING_API_URL=https://clob.polymarket.com

# Configuración del Servidor (tienen valores por defecto)
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## 🔴 Frontend - OBLIGATORIAS

Estas variables son **necesarias** para que el frontend funcione:

```bash
# Stack Auth (autenticación)
NEXT_PUBLIC_STACK_PROJECT_ID=prj_...
NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY=pk_live_...

# URL del Backend
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
# O alternativamente:
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📝 Resumen Rápido

### Mínimo para Desarrollo (sin trading real):

**Backend `.env`:**
```bash
STACK_SECRET_SERVER_KEY=sk_live_...
DATABASE_URL=sqlite:///./poly_liquidity.db
```

**Frontend `.env.local`:**
```bash
NEXT_PUBLIC_STACK_PROJECT_ID=prj_...
NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY=pk_live_...
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### Para Trading Real en Polymarket:

Agregar al **Backend `.env`**:
```bash
PRIVATE_KEY=0x...                    # Clave privada de tu wallet
FUNDER_ADDRESS=0x...                 # Dirección proxy (polymarket.com/settings)
RPC_URL=https://polygon-rpc.com/     # URL RPC de Polygon
CHAIN_ID=137                         # Polygon mainnet
```

**Importante:** No necesitas `POLYMARKET_API_KEY`, `POLYMARKET_API_SECRET` ni `POLYMARKET_API_PASSPHRASE`. El sistema las genera automáticamente.

## 🔐 Dónde Obtener las Credenciales

### Stack Auth:
1. Ve a https://stack-auth.com
2. Crea un proyecto
3. Obtén `STACK_SECRET_SERVER_KEY` (backend)
4. Obtén `NEXT_PUBLIC_STACK_PROJECT_ID` y `NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY` (frontend)

### Polymarket:
1. Ve a https://polymarket.com/settings
2. Encuentra tu **Proxy Address** (es `FUNDER_ADDRESS`) - copia esta dirección
3. **No necesitas crear API Keys** - el sistema las genera automáticamente

### Wallet Privada:
- Exporta tu clave privada de MetaMask o tu wallet
- Debe empezar con `0x`
- **⚠️ NUNCA compartas esta clave**

### RPC URL:
- Usa un proveedor RPC de Polygon como:
  - Alchemy: https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY
  - Infura: https://polygon-mainnet.infura.io/v3/YOUR_KEY
  - QuickNode: https://your-endpoint.polygon.quiknode.pro/YOUR_KEY
  - O público: https://polygon-rpc.com/

## ⚠️ Notas Importantes

1. **NUNCA subas** `.env` o `.env.local` a control de versiones
2. Asegúrate de que estén en `.gitignore`
3. Las claves privadas y secretos deben mantenerse seguros
4. Para producción, usa un gestor de secretos (AWS Secrets Manager, Vault, etc.)

