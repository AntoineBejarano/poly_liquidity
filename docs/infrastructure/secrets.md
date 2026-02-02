# Secrets Management

**Purpose**: Guide for managing environment variables, private keys, and wallet service configuration.

**Audience**: Engineers setting up the system, DevOps, security team.

**Where this is used**: Backend configuration, wallet service, execution engine.

**Last updated**: 2025-01-XX

---

## Environment Variables

### Backend - Required

These variables are **necessary** for the server to start:

```bash
# Stack Auth (authentication)
STACK_SECRET_SERVER_KEY=sk_live_...

# Database
DATABASE_URL=postgresql://user:password@host:port/dbname
# Or for local development:
# DATABASE_URL=sqlite:///./poly_liquidity.db
```

### Backend - Optional (but needed for real trading)

These variables are **optional** to start the server, but **necessary** to operate on Polymarket:

```bash
# Private Wallet (hex string with "0x")
PRIVATE_KEY=0x1234567890abcdef...

# Proxy Wallet Address (visible in polymarket.com/settings)
FUNDER_ADDRESS=0x1234567890abcdef...
# Or alternatively:
POLYMARKET_PROXY_ADDRESS=0x1234567890abcdef...

# Blockchain Network Configuration
CHAIN_ID=137  # Polygon mainnet (default: 137)
RPC_URL=https://polygon-rpc.com/  # URL of your RPC provider
```

**Note:** You do NOT need `POLYMARKET_API_KEY`, `POLYMARKET_API_SECRET`, or `POLYMARKET_API_PASSPHRASE`. The system generates these automatically.

### Backend - Optional (additional features)

```bash
# Builders (for MEV protection, optional)
BUILDER_API_KEY=...
BUILDER_SECRET=...
BUILDER_PASSPHRASE=...

# Wallet Encryption (only if using wallets in DB, not needed if using PRIVATE_KEY)
# To generate a key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
WALLET_ENCRYPTION_KEY=base64_encoded_fernet_key

# Notifications (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
EMAIL_CONFIG={"smtp_host": "...", "smtp_port": 587, ...}

# API URLs (have default values, only change if necessary)
POLYMARKET_API_URL=https://api.polymarket.com
POLYMARKET_DATA_API_URL=https://data-api.polymarket.com
POLYMARKET_GAMMA_API_URL=https://gamma-api.polymarket.com
POLYMARKET_TRADING_API_URL=https://clob.polymarket.com

# Server Configuration (have defaults)
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Frontend - Required

These variables are **necessary** for the frontend to work:

```bash
# Stack Auth (authentication)
NEXT_PUBLIC_STACK_PROJECT_ID=prj_...
NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY=pk_live_...

# Backend URL
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
# Or alternatively:
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Quick Summary

**Minimum for Development (without real trading):**

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

**For Real Trading on Polymarket:**

Add to **Backend `.env`**:
```bash
PRIVATE_KEY=0x...                    # Private key of your wallet
FUNDER_ADDRESS=0x...                 # Proxy address (polymarket.com/settings)
RPC_URL=https://polygon-rpc.com/     # Polygon RPC URL
CHAIN_ID=137                         # Polygon mainnet
```

---

## Where to Get Credentials

### Stack Auth:
1. Go to https://stack-auth.com
2. Create a project
3. Get `STACK_SECRET_SERVER_KEY` (backend)
4. Get `NEXT_PUBLIC_STACK_PROJECT_ID` and `NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY` (frontend)

### Polymarket:
1. Go to https://polymarket.com/settings
2. Find your **Proxy Address** (this is `FUNDER_ADDRESS`) - copy this address
3. **You do NOT need to create API Keys** - the system generates them automatically

### Private Wallet:
- Export your private key from MetaMask or your wallet
- Must start with `0x`
- **⚠️ NEVER share this key**

### RPC URL:
- Use a Polygon RPC provider such as:
  - Alchemy: https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY
  - Infura: https://polygon-mainnet.infura.io/v3/YOUR_KEY
  - QuickNode: https://your-endpoint.polygon.quiknode.pro/YOUR_KEY
  - Or public: https://polygon-rpc.com/

---

## Wallet Service

### Purpose

The **WalletService** manages operational signing resources used by the ExecutionEngine to send orders to Polymarket.

**Key Characteristics:**
- ✅ NOT part of user system
- ✅ NOT managed via environment variables
- ✅ NOT dependent on human operator in real-time
- ✅ Critical operational resource, equivalent to signing key manager of a financial trading system

**Equivalent to a hardware key manager**, but implemented in software with necessary guarantees to operate hundreds of thousands of euros in volume.

### Design Requirements

1. **Only One Active Wallet**
   - Only one wallet can be active at a time
   - Prevents inconsistencies, unwanted exposures, or parallel orders signed by multiple identities

2. **Runtime Rotation Without Restart**
   - Migrate to new keys
   - Update permissions
   - Rotate compromised keys
   - Change wallet after crash or blockchain quirk
   - **Without stopping the trading engine**

3. **Secure Private Keys**
   - ❌ Never in logs
   - ❌ Never in exceptions
   - ❌ Never in frontend endpoints
   - ❌ Never in environment variables
   - ❌ Never in DevOps filesystems

4. **Efficient Cache and Atomization**
   - Once active, private key must be available decrypted in RAM (never on disk)
   - Ready to sign thousands of orders in seconds

### Database Schema

**Table `wallets` in PostgreSQL:**

```sql
CREATE TABLE wallets (
    id UUID PRIMARY KEY,
    label TEXT NOT NULL,
    address TEXT NOT NULL,
    encrypted_private_key BYTEA NOT NULL,
    active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_wallets_active ON wallets(active);
CREATE INDEX idx_wallets_address ON wallets(address);
```

**Important Properties:**

- **`encrypted_private_key`**: Stored encrypted using **AES-256-GCM** (or equivalent), with random IV + authentication tag, never stored in plain text
- **`active`**: **Hard invariant**: only one can be active, guaranteed via SQL transactions with mutual exclusion

**Critical Rule:**
> Private key is never stored in plain text.

### Service API

```python
class WalletService:
    """Operational wallet management service."""
    
    @classmethod
    async def get_active_wallet(cls) -> WalletInMemory:
        """
        Gets active wallet (address + decrypted private key).
        Memory cache for fast access.
        
        Returns:
            WalletInMemory: Active wallet with decrypted private key
            None: If no active wallet
        """
        pass
    
    @classmethod
    async def set_active_wallet(
        cls,
        wallet_id: UUID,
        *,
        cancel_open_orders: bool = True
    ) -> None:
        """
        Changes active wallet.
        
        Args:
            wallet_id: ID of wallet to activate
            cancel_open_orders: If True, cancels open orders before changing
        """
        pass
    
    @classmethod
    async def create_wallet(
        cls,
        label: str,
        address: str,
        private_key: str
    ) -> WalletModel:
        """
        Creates new wallet encrypting private key.
        
        Args:
            label: Descriptive label
            address: Public wallet address
            private_key: Private key in plain text (encrypted before saving)
        """
        pass
```

### Encryption

**Encryption Method:**
- Uses **Fernet** (symmetric encryption) or **AES-256-GCM**
- Key stored in `WALLET_ENCRYPTION_KEY` environment variable
- Each wallet encrypted with unique IV

**Key Generation:**
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
# Store in WALLET_ENCRYPTION_KEY environment variable
```

### Memory Cache

**Active wallet private key:**
- Decrypted and cached in memory
- Never written to disk
- Cleared when wallet deactivated
- Fast access for signing operations

---

## Security Best Practices

### Environment Variables

1. **NEVER commit** `.env` or `.env.local` to version control
2. Ensure they are in `.gitignore`
3. Private keys and secrets must be kept secure
4. For production, use a secrets manager (AWS Secrets Manager, Vault, etc.)

### Private Key Handling

- ❌ Never logged
- ❌ Never stored in database in plain text
- ❌ Never sent over network in plain text
- ❌ Never exposed in error messages
- ✅ Loaded once at startup (or on-demand with secure cache)
- ✅ Kept in memory only as long as needed for signing

### Wallet Service

- Only one active wallet at a time
- Private keys encrypted at rest
- Decrypted only in memory when active
- Rotation without system restart
- Audit trail of all wallet operations

---

## Related Documentation

- [`../exchange/polymarket-integration.md`](../exchange/polymarket-integration.md) - API key generation
- [`../architecture/execution-engine.md`](../architecture/execution-engine.md) - Signing operations
- [`../security/secrets-handling.md`](../security/secrets-handling.md) - Security practices

---

## Open Questions

- What is the procedure for key rotation in production?
- How do we handle key compromise scenarios?
- What is the backup strategy for encrypted keys?




