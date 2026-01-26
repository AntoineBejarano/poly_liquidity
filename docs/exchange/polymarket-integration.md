# Polymarket Integration

**Purpose**: Technical specification for Polymarket API integration, including official client, WebSocket connections, and API analysis.

**Audience**: Engineers implementing or maintaining Polymarket integration, execution engine developers.

**Where this is used**: Execution engine, scanner, order monitoring, real-time updates.

**Last updated**: 2025-01-XX

---

## Overview

The system integrates with Polymarket using:

1. **Official Python CLOB Client** (`py-clob-client`) for trading operations
2. **WebSocket connections** for real-time order and market updates
3. **Gamma API** for market scanning and data retrieval

---

## Official Python CLOB Client

### Status

✅ **COMPLETED** - The official Polymarket client is integrated in the Execution Engine.

### Package Information

- **PyPI Package:** `py-clob-client`
- **Documentation:** https://github.com/Polymarket/py-clob-client
- **Requirements:** Python 3.9+

### Installation

```bash
pip install py-clob-client
```

Or install all dependencies:

```bash
pip install -r requirements.txt
```

### Configuration

The official client uses the same environment variables already configured:

```bash
# Required environment variables
PRIVATE_KEY=<your-private-key>          # Private key of wallet (hex with "0x")
FUNDER_ADDRESS=<your-funder-address>    # Address containing funds (for proxy wallets)
CHAIN_ID=137                            # Polygon mainnet

# Optional variables
POLYMARKET_PROXY_ADDRESS=<proxy-addr>   # Alternative to FUNDER_ADDRESS
POLYMARKET_TRADING_API_URL=https://clob.polymarket.com  # CLOB API URL
```

### Integration Modes

The Execution Engine has two modes of operation:

#### 1. Official Client Mode (Production)

When `PRIVATE_KEY` and `FUNDER_ADDRESS` are configured:

- System uses `PolymarketCLOBWrapper` that encapsulates `py-clob-client`
- Orders are created using `create_limit_order()` from official client
- EIP-712 signing, nonces, and authentication handled automatically
- Method: `Execution._send_order_via_official_client()`

#### 2. Legacy Mode (Development/Testing)

When official client is not available:

- System uses existing manual implementation
- Manual EIP-712 signing with `EIP712Signer`
- Manual nonce management with `NonceManager`
- Method: `Execution._send_order_to_polymarket()`

### Usage Examples

#### Read-Only Client (no authentication)

```python
from py_clob_client.client import ClobClient

client = ClobClient("https://clob.polymarket.com")  # Level 0 (no auth)

ok = client.get_ok()
time = client.get_server_time()
markets = client.get_simplified_markets()
```

#### Trading Client (EOA - Externally Owned Account)

```python
from py_clob_client.client import ClobClient

HOST = "https://clob.polymarket.com"
CHAIN_ID = 137
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
FUNDER = os.getenv("FUNDER_ADDRESS")

client = ClobClient(
    HOST,
    key=PRIVATE_KEY,
    chain_id=CHAIN_ID,
    signature_type=0,  # 0 for EOA (MetaMask, hardware wallets)
    funder=FUNDER
)

# Create order
order = client.create_limit_order(
    token_id="...",
    price=0.95,
    size=1000,
    side="BUY"
)
```

---

## WebSocket Integration

### Status

✅ **COMPLETED** - WebSocket client created and ready for integration.

### Overview

Polymarket provides WebSockets (WSS) for real-time updates on:

- **USER Channel**: Orders and trades of authenticated user
- **MARKET Channel**: Orderbooks and price changes of public markets

This eliminates the need for constant polling and provides near real-time updates.

### Available Channels

#### USER Channel (Requires Authentication)

Receives updates on:
- **Trade Messages**: When a trade executes (MATCHED, MINED, CONFIRMED, RETRYING, FAILED)
- **Order Messages**: When an order is placed (PLACEMENT), updated (UPDATE), or cancelled (CANCELLATION)

#### MARKET Channel (Public)

Receives updates on:
- **Book Messages**: Complete orderbook snapshot when changes occur
- **price_change Messages**: Changes in individual price levels
- **tick_size_change Messages**: Changes in minimum tick size
- **last_trade_price Messages**: Last executed trade price

### Configuration

#### Obtaining API Keys

First, obtain API keys using the CLOB client:

```python
from py_clob_client.client import ClobClient
from app.settings import settings

host = "https://clob.polymarket.com"
client = ClobClient(
    host,
    key=settings.private_key,
    chain_id=settings.chain_id or 137,
    signature_type=1,  # or 0 for EOA
    funder=settings.funder_address
)

# Derive API keys
api_key, api_secret, api_passphrase = client.derive_api_key()
```

Or use the client method:

```python
api_creds = client.create_or_derive_api_creds()
api_key = api_creds.get("apiKey")
api_secret = api_creds.get("secret")
api_passphrase = api_creds.get("passphrase")
```

### Usage Example

```python
from app.core.execution.polymarket_websocket import (
    get_websocket_manager,
    WebSocketAuth
)

# Configure authentication
manager = get_websocket_manager()
manager.set_auth(
    api_key="your-api-key",
    secret="your-secret",
    passphrase="your-passphrase"
)

# Callback for trades
def handle_trade(trade_msg):
    print(f"Trade executed: {trade_msg['id']}")
    print(f"Status: {trade_msg['status']}")
    print(f"Price: {trade_msg['price']}, Size: {trade_msg['size']}")
    # Update order in Execution Engine
    # execution._handle_fill(...)

# Callback for order updates
def handle_order_update(order_msg):
    event_type = order_msg['type']  # PLACEMENT, UPDATE, CANCELLATION
    order_id = order_msg['id']
    # Handle order update

# Subscribe to USER channel
manager.subscribe_user(
    on_trade=handle_trade,
    on_order=handle_order_update
)

# Subscribe to MARKET channel for specific market
manager.subscribe_market(
    market_id="0x...",
    on_book_update=lambda msg: print(f"Book update: {msg}"),
    on_price_change=lambda msg: print(f"Price change: {msg}")
)
```

---

## Gamma API Integration

### Status

✅ **UPDATED** - Now uses **Gamma API** (`gamma-api.polymarket.com`) instead of Data API.

### Implementation

The Scanner uses the Gamma API `/events` endpoint (recommended by official documentation):

```python
async def _fetch_markets_from_polymarket(self) -> List[Dict[str, Any]]:
    """
    Fetch markets from Polymarket Gamma API with rate limiting and caching.
    
    Uses Gamma API /events endpoint (most efficient for retrieving all active markets).
    Implements pagination to fetch all markets.
    """
    # Uses Gamma API: https://gamma-api.polymarket.com/events
    # Parameters:
    # - order=id: Order by event ID
    # - ascending=false: Get newest events first
    # - closed=false: Only active markets (CRITICAL)
    # - limit=100: 100 events per page
    # - offset: For pagination
```

### Best Practices

1. ✅ **Use `/events` endpoint** to get all active markets
2. ✅ **Recommended Parameters**:
   - `order=id` - Order by event ID
   - `ascending=false` - Get newest events first
   - `closed=false` - Only active markets (CRITICAL)
   - `limit=100` - Control response size
   - `offset` - For pagination

3. ✅ **Pagination**:
   - Implemented with loop processing multiple pages
   - Safety limit: 10 pages (1000 markets)
   - Automatically stops when no more results

### Example Request

```bash
# First page
curl "https://gamma-api.polymarket.com/events?order=id&ascending=false&closed=false&limit=100&offset=0"

# Second page
curl "https://gamma-api.polymarket.com/events?order=id&ascending=false&closed=false&limit=100&offset=100"
```

### Rate Limiting

- **Polymarket Scanner**: 200 req / 10s
- **Trading API**: 2400 req / 10s
- **Data API**: 200 req / 10s

### Features

1. **Automatic Pagination**:
   - Processes up to 10 pages (1000 markets maximum for safety)
   - Automatically stops when no more results
   - Extracts markets from each event (events contain markets)

2. **Rate Limiting**:
   - Respects API limits (200 req / 10s)
   - Handles 429 errors correctly
   - Uses cache as fallback

3. **Caching**:
   - 5-second cache to reduce calls
   - Fallback to cache on error

4. **Logging**:
   - Informative logs about number of markets obtained
   - Error logs with complete traceback

---

## API Endpoints Summary

### Trading Endpoints

- **Base URL**: `https://clob.polymarket.com`
- **Create Order**: `POST /orders`
- **Cancel Order**: `DELETE /orders/:order_id`
- **Get Order**: `GET /orders/:order_id`
- **Get Fills**: `GET /fills?order_id=:id`

### Data Endpoints

- **Gamma API Base**: `https://gamma-api.polymarket.com`
- **Get Events**: `GET /events` (recommended for scanning)
- **Get Markets**: `GET /markets` (alternative)

### WebSocket Endpoints

- **WSS URL**: `wss://clob.polymarket.com/ws`
- **USER Channel**: Requires authentication
- **MARKET Channel**: Public

---

## Error Handling

### Common Errors

1. **429 Rate Limit**
   - Action: Exponential backoff, retry after delay
   - Maximum 3 retries

2. **401 Unauthorized**
   - Action: Check API keys, regenerate if needed
   - Verify signature and nonce

3. **400 Bad Request**
   - Action: Validate order parameters
   - Check market status

4. **500 Server Error**
   - Action: Retry with backoff
   - Use cache if available

### Circuit Breaker

If more than X errors in Y seconds:

- Trading Circuit Breaker opens
- No new orders until cooldown
- Cancel open orders
- System alerts

---

## Security Considerations

### Private Key Handling

- ❌ Never logged
- ❌ Never stored in database
- ❌ Never sent over network in plain text
- ❌ Never exposed in error messages
- ✅ Loaded once at startup (or on-demand with secure cache)
- ✅ Kept in memory only as long as needed for signing

### API Key Management

- Store in secure environment variables
- Rotate periodically
- Use different keys for production and development
- Never commit to version control

---

## Related Documentation

- [`../architecture/execution-engine.md`](../architecture/execution-engine.md) - Execution flow
- [`../architecture/data-flow.md`](../architecture/data-flow.md) - Scanner implementation
- [`../exchange/order-lifecycle.md`](../exchange/order-lifecycle.md) - Order lifecycle
- [`../exchange/failure-modes.md`](../exchange/failure-modes.md) - Failure handling

---

## Open Questions

- What are the exact rate limits for each endpoint?
- How do we handle WebSocket reconnection?
- What is the procedure for handling orphaned orders?
- How do we verify API key permissions?



