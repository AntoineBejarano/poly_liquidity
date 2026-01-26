# Integración con Polymarket Python CLOB Client

## Estado de la Integración

✅ **COMPLETADO** - El cliente oficial de Polymarket está integrado en el Execution Engine.

### Cambios Realizados

1. ✅ Agregado `py-clob-client` a `requirements.txt`
2. ✅ Creado `PolymarketCLOBWrapper` (`backend/app/core/execution/polymarket_client_wrapper.py`)
3. ✅ Refactorizado `Execution` para usar el wrapper cuando está disponible
4. ✅ Mantenida compatibilidad con implementación legacy para desarrollo/testing

## Cliente Oficial de Polymarket

Polymarket proporciona un cliente oficial de Python para interactuar con su CLOB (Central Limit Order Book): `py-clob-client`.

**PyPI Package:** `py-clob-client`  
**Documentación:** https://github.com/Polymarket/py-clob-client  
**Requisitos:** Python 3.9+

## Instalación

```bash
pip install py-clob-client
```

O instalar todas las dependencias:

```bash
pip install -r requirements.txt
```

## Configuración

El cliente oficial usa las mismas variables de entorno que ya configuramos:

```bash
# Variables de entorno requeridas
PRIVATE_KEY=<your-private-key>          # Clave privada de wallet (hex con "0x")
FUNDER_ADDRESS=<your-funder-address>    # Dirección que contiene fondos (para proxy wallets)
CHAIN_ID=137                            # Polygon mainnet

# Variables opcionales
POLYMARKET_PROXY_ADDRESS=<proxy-addr>   # Alternativa a FUNDER_ADDRESS
POLYMARKET_TRADING_API_URL=https://clob.polymarket.com  # URL del CLOB API
```

## Cómo Funciona la Integración

El Execution Engine ahora tiene dos modos de operación:

### 1. Modo con Cliente Oficial (Producción)

Cuando `PRIVATE_KEY` y `FUNDER_ADDRESS` están configurados:

- El sistema usa `PolymarketCLOBWrapper` que encapsula `py-clob-client`
- Las órdenes se crean usando `create_limit_order()` del cliente oficial
- La firma EIP-712, nonces y autenticación se manejan automáticamente
- Método: `Execution._send_order_via_official_client()`

### 2. Modo Legacy (Desarrollo/Testing)

Cuando el cliente oficial no está disponible:

- El sistema usa la implementación manual existente
- Firma EIP-712 manual con `EIP712Signer`
- Manejo manual de nonces con `NonceManager`
- Método: `Execution._send_order_to_polymarket()`

## Uso del Cliente

### Cliente Read-Only (sin autenticación)

```python
from py_clob_client.client import ClobClient

client = ClobClient("https://clob.polymarket.com")  # Level 0 (no auth)

ok = client.get_ok()
time = client.get_server_time()
markets = client.get_simplified_markets()
```

### Cliente para Trading (EOA - Externally Owned Account)

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
    signature_type=0,  # 0 para EOA (MetaMask, hardware wallets)
    funder=FUNDER
)
client.set_api_creds(client.create_or_derive_api_creds())
```

### Cliente para Trading (Proxy Wallet - Email/Magic)

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
    signature_type=1,  # 1 para email/Magic wallet signatures
    funder=FUNDER
)
client.set_api_creds(client.create_or_derive_api_creds())
```

### Tipos de Signature

- `signature_type=0` (default): EOA estándar - MetaMask, hardware wallets, wallets donde controlas la private key directamente
- `signature_type=1`: Email/Magic wallet signatures (delegated signing)
- `signature_type=2`: Browser wallet proxy signatures (proxy contracts, no conexiones directas)

## Operaciones Disponibles

### Obtener Mercados

```python
client = ClobClient("https://clob.polymarket.com")
markets = client.get_simplified_markets()
```

### Obtener Precios y Orderbooks

```python
from py_clob_client.clob_types import BookParams

token_id = "<token-id>"
mid = client.get_midpoint(token_id)
price = client.get_price(token_id, side="BUY")
book = client.get_order_book(token_id)
books = client.get_order_books([BookParams(token_id=token_id)])
```

### Crear Market Order (compra por monto en $)

```python
from py_clob_client.clob_types import MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

mo = MarketOrderArgs(
    token_id="<token-id>",
    amount=25.0,  # Monto en USD
    side=BUY,
    order_type=OrderType.FOK  # Fill or Kill
)
signed = client.create_market_order(mo)
resp = client.post_order(signed, OrderType.FOK)
```

### Crear Limit Order (shares a un precio)

```python
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

order = OrderArgs(
    token_id="<token-id>",
    price=0.01,
    size=5.0,  # Cantidad de shares
    side=BUY
)
signed = client.create_order(order)
resp = client.post_order(signed, OrderType.GTC)  # Good Till Cancel
```

### Gestionar Órdenes

```python
from py_clob_client.clob_types import OpenOrderParams

# Obtener órdenes abiertas
open_orders = client.get_orders(OpenOrderParams())

# Cancelar una orden
order_id = open_orders[0]["id"] if open_orders else None
if order_id:
    client.cancel(order_id)

# Cancelar todas las órdenes
client.cancel_all()
```

### Obtener Trades

```python
last = client.get_last_trade_price("<token-id>")
trades = client.get_trades()
```

## Token Allowances (Solo para MetaMask/EOA)

### ¿Necesito configurar allowances?

- **Email/Magic wallet:** No se necesita acción - los allowances se configuran automáticamente
- **MetaMask o hardware wallet:** **Sí, necesitas configurar allowances antes de tradear**

### ¿Qué son los allowances?

Los allowances son permisos. Antes de que Polymarket pueda mover tus fondos para ejecutar trades, necesitas dar permiso a los contratos del exchange para acceder a tu USDC y conditional tokens.

### Configuración Rápida

Necesitas aprobar dos tipos de tokens:

1. **USDC** (para depósitos y trading)
2. **Conditional Tokens** (los outcome tokens que tradas)

### Addresses para Approve

**Para USDC (token de trading):**
- Token: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`
- Approve para estos contratos:
  - `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E` (Main exchange)
  - `0xC5d563A36AE78145C45a50134d48A1215220f80a` (Neg risk markets)
  - `0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296` (Neg risk adapter)

**Para Conditional Tokens:**
- Token: `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045`
- Approve para los mismos tres contratos arriba

## Implementación en nuestro Código

### PolymarketCLOBWrapper

El wrapper (`backend/app/core/execution/polymarket_client_wrapper.py`) proporciona:

- Inicialización automática desde `settings`
- Métodos simplificados: `create_limit_order()`, `create_market_order()`, `cancel_order()`, etc.
- Logging estructurado consistente con nuestro sistema
- Manejo de errores robusto

### Execution Engine

El `Execution` engine:

1. Intenta usar el cliente oficial si está disponible
2. Cae back a la implementación legacy si no está disponible
3. Mantiene trazabilidad completa en ambos modos
4. Registra métricas de latencia y éxito/fallo

### Obtención de token_id

**IMPORTANTE:** El cliente oficial usa `token_id` (ID del outcome token YES/NO), no `market_id`.

Actualmente tenemos un método placeholder `_get_token_id_from_market()` que necesita ser implementado completamente. En producción, necesitamos:

1. Obtener el token_id real desde la API de Polymarket
2. O almacenar el token_id cuando escaneamos mercados
3. O derivarlo desde el `polymarket_id` y outcome

## Archivos Modificados/Creados

- ✅ `backend/requirements.txt` - Agregado `py-clob-client>=1.0.0`
- ✅ `backend/app/core/execution/polymarket_client_wrapper.py` - Nuevo wrapper
- ✅ `backend/app/core/execution/execution.py` - Integrado uso del wrapper
- ✅ `backend/app/core/execution/__init__.py` - Exporta wrapper
- ✅ `docs/POLYMARKET_CLIENT_INTEGRATION.md` - Este documento

## Próximos Pasos

1. ⏳ Implementar obtención real de `token_id` desde Polymarket API
2. ⏳ Actualizar tests para usar el nuevo wrapper
3. ⏳ Validar integración completa en entorno de desarrollo
4. ⏳ Documentar proceso de obtención de token_id

## Referencias

- [py-clob-client GitHub](https://github.com/Polymarket/py-clob-client)
- [Polymarket API Documentation](https://docs.polymarket.com/)
- [Polymarket CLOB API](https://docs.polymarket.com/developers/clob-rest-api)
