# Integración con WebSockets de Polymarket

## Estado de la Integración

✅ **COMPLETADO** - Cliente WebSocket creado y listo para integración.

### Cambios Realizados

1. ✅ Creado `PolymarketWebSocketClient` para conexiones WebSocket
2. ✅ Creado `PolymarketWebSocketManager` para gestionar múltiples conexiones
3. ✅ Soporte para USER channel (órdenes y trades del usuario)
4. ✅ Soporte para MARKET channel (orderbooks y precios públicos)
5. ✅ Agregado `websocket-client` a `requirements.txt`

## Overview

Polymarket proporciona WebSockets (WSS) para recibir updates en tiempo real sobre:
- **USER Channel**: Órdenes y trades del usuario autenticado
- **MARKET Channel**: Orderbooks y cambios de precio de mercados públicos

Esto elimina la necesidad de polling constante y proporciona actualizaciones casi en tiempo real.

## Canales Disponibles

### USER Channel (Requiere Autenticación)

Recibe updates sobre:
- **Trade Messages**: Cuando se ejecuta un trade (MATCHED, MINED, CONFIRMED, RETRYING, FAILED)
- **Order Messages**: Cuando una orden se coloca (PLACEMENT), actualiza (UPDATE), o cancela (CANCELLATION)

### MARKET Channel (Público)

Recibe updates sobre:
- **Book Messages**: Snapshot completo del orderbook cuando hay cambios
- **price_change Messages**: Cambios en niveles de precio individuales
- **tick_size_change Messages**: Cambios en el tick size mínimo
- **last_trade_price Messages**: Último precio de trade ejecutado

## Configuración

### Obtención de API Keys

Primero necesitas obtener tus API keys usando el cliente CLOB:

```python
from py_clob_client.client import ClobClient
from app.settings import settings

host = "https://clob.polymarket.com"
client = ClobClient(
    host,
    key=settings.private_key,
    chain_id=settings.chain_id or 137,
    signature_type=1,  # o 0 para EOA
    funder=settings.funder_address
)

# Derivar API keys
api_key, api_secret, api_passphrase = client.derive_api_key()
```

O usar el método del cliente:

```python
api_creds = client.create_or_derive_api_creds()
api_key = api_creds.get("apiKey")
api_secret = api_creds.get("secret")
api_passphrase = api_creds.get("passphrase")
```

## Uso del Cliente WebSocket

### Ejemplo Básico - USER Channel

```python
from app.core.execution.polymarket_websocket import (
    get_websocket_manager,
    WebSocketAuth
)

# Configurar autenticación
manager = get_websocket_manager()
manager.set_auth(
    api_key="your-api-key",
    secret="your-secret",
    passphrase="your-passphrase"
)

# Callback para trades
def handle_trade(trade_msg):
    print(f"Trade executed: {trade_msg['id']}")
    print(f"Status: {trade_msg['status']}")
    print(f"Price: {trade_msg['price']}, Size: {trade_msg['size']}")
    # Actualizar orden en Execution Engine
    # execution._handle_fill(...)

# Callback para updates de órdenes
def handle_order_update(order_msg):
    event_type = order_msg['type']  # PLACEMENT, UPDATE, CANCELLATION
    order_id = order_msg['id']
    print(f"Order {event_type}: {order_id}")
    # Actualizar estado de orden en Execution Engine

manager.on_trade = handle_trade
manager.on_order_update = handle_order_update

# Conectar a USER channel (None = todos los mercados)
manager.connect_user_channel(market_ids=None)

# Mantener conexión activa
import time
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    manager.disconnect_all()
```

### Ejemplo - MARKET Channel

```python
from app.core.execution.polymarket_websocket import get_websocket_manager

manager = get_websocket_manager()

# Callback para updates del orderbook
def handle_book_update(book_msg):
    market = book_msg['market']
    bids = book_msg.get('bids', [])
    asks = book_msg.get('asks', [])
    print(f"Book update for market {market}")
    print(f"Best bid: {bids[0]['price'] if bids else 'N/A'}")
    print(f"Best ask: {asks[0]['price'] if asks else 'N/A'}")
    # Actualizar MarketState en Strategy Engine

# Callback para cambios de precio
def handle_price_change(price_msg):
    market = price_msg['market']
    for change in price_msg['price_changes']:
        print(f"Price change: {change['asset_id']} - {change['price']}")
        print(f"Best bid: {change['best_bid']}, Best ask: {change['best_ask']}")
    # Actualizar precios en Strategy Engine

manager.on_book_update = handle_book_update
manager.on_price_change = handle_price_change

# Conectar a MARKET channel para un asset específico
asset_ids = ["109681959945973300464568698402968596289258214226684818748321941747028805721376"]
manager.connect_market_channel(asset_ids=asset_ids, market_id="market-1")

# Mantener conexión activa
import time
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    manager.disconnect_all()
```

## Integración con Execution Engine

El WebSocket puede reemplazar o complementar el polling de órdenes:

### Opción 1: Reemplazar Polling

```python
# En Execution Engine
from app.core.execution.polymarket_websocket import get_websocket_manager

class Execution:
    def __init__(self, ...):
        # ... existing code ...
        self._setup_websocket()
    
    def _setup_websocket(self):
        """Configura WebSocket para updates en tiempo real."""
        manager = get_websocket_manager()
        
        # Obtener credenciales API desde el cliente CLOB
        polymarket_client = get_polymarket_client()
        if polymarket_client.is_available():
            client = polymarket_client.get_client()
            api_creds = client.create_or_derive_api_creds()
            manager.set_auth(
                api_key=api_creds.get("apiKey"),
                secret=api_creds.get("secret"),
                passphrase=api_creds.get("passphrase")
            )
            
            # Configurar callbacks
            manager.on_trade = self._handle_websocket_trade
            manager.on_order_update = self._handle_websocket_order_update
            
            # Conectar
            manager.connect_user_channel()
    
    def _handle_websocket_trade(self, trade_msg: Dict[str, Any]):
        """Maneja trade event desde WebSocket."""
        trade_id = trade_msg['id']
        order_id = trade_msg['taker_order_id']
        status = trade_msg['status']
        price = float(trade_msg['price'])
        size = float(trade_msg['size'])
        
        # Actualizar orden cuando se confirma
        if status == "CONFIRMED":
            # Buscar orden por order_id
            db_order = self._find_order_by_polymarket_id(order_id)
            if db_order:
                await self._handle_fill(db_order.id, price, size)
    
    def _handle_websocket_order_update(self, order_msg: Dict[str, Any]):
        """Maneja order event desde WebSocket."""
        order_id = order_msg['id']
        event_type = order_msg['type']  # PLACEMENT, UPDATE, CANCELLATION
        size_matched = float(order_msg.get('size_matched', '0'))
        
        # Actualizar estado de orden
        db_order = self._find_order_by_polymarket_id(order_id)
        if db_order:
            if event_type == "CANCELLATION":
                await self._update_order_state(
                    db_order.id,
                    "CANCELLED",
                    reason="Cancelled via WebSocket"
                )
            elif event_type == "UPDATE":
                # Orden parcialmente llenada
                await self._update_order_state(
                    db_order.id,
                    "PARTIALLY_FILLED",
                    filled_size=size_matched
                )
```

### Opción 2: Complementar Polling

Usar WebSocket como fuente principal y polling como fallback:

```python
class Execution:
    def __init__(self, ...):
        self._use_websocket = True  # Configurable
        if self._use_websocket:
            self._setup_websocket()
        # Polling sigue disponible como fallback
    
    async def _poll_order_status(self, order_id: UUID):
        """Polling de respaldo si WebSocket no está disponible."""
        if self._use_websocket and get_websocket_manager().user_client.is_connected:
            # WebSocket está activo, no hacer polling
            return
        
        # Usar polling legacy
        # ... existing polling code ...
```

## Integración con Strategy Engine

El MARKET channel puede proporcionar precios en tiempo real:

```python
# En Strategy Engine
from app.core.execution.polymarket_websocket import get_websocket_manager

class Strategy:
    def __init__(self, ...):
        self._setup_market_websocket()
    
    def _setup_market_websocket(self):
        """Configura WebSocket para updates de precios."""
        manager = get_websocket_manager()
        
        manager.on_price_change = self._handle_price_change
        manager.on_book_update = self._handle_book_update
    
    def _handle_price_change(self, price_msg: Dict[str, Any]):
        """Actualiza precios cuando cambian."""
        market_id = price_msg['market']
        for change in price_msg['price_changes']:
            asset_id = change['asset_id']
            best_bid = float(change['best_bid'])
            best_ask = float(change['best_ask'])
            
            # Actualizar MarketState
            if market_id in self._market_states:
                self._market_states[market_id].best_bid = best_bid
                self._market_states[market_id].best_ask = best_ask
                self._market_states[market_id].updated_at = datetime.utcnow()
    
    def _handle_book_update(self, book_msg: Dict[str, Any]):
        """Actualiza orderbook completo."""
        market_id = book_msg['market']
        bids = book_msg.get('bids', [])
        asks = book_msg.get('asks', [])
        
        # Actualizar MarketState con orderbook completo
        if market_id in self._market_states:
            self._market_states[market_id].orderbook_snapshot = {
                'bids': bids,
                'asks': asks,
                'timestamp': book_msg['timestamp']
            }
```

## Estructura de Mensajes

### Trade Message (USER Channel)

```json
{
  "asset_id": "52114319501245915516055106046884209969926127482827954674443846427813813222426",
  "event_type": "trade",
  "id": "28c4d2eb-bbea-40e7-a9f0-b2fdb56b2c2e",
  "last_update": "1672290701",
  "maker_orders": [...],
  "market": "0xbd31dc8a20211944f6b70f31557f1001557b59905b7738480ca09bd4532f84af",
  "matchtime": "1672290701",
  "outcome": "YES",
  "owner": "9180014b-33c8-9240-a14b-bdca11c0a465",
  "price": "0.57",
  "side": "BUY",
  "size": "10",
  "status": "MATCHED",
  "taker_order_id": "0x06bc63e346ed4ceddce9efd6b3af37c8f8f440c92fe7da6b2d0f9e4ccbc50c42",
  "timestamp": "1672290701",
  "trade_owner": "9180014b-33c8-9240-a14b-bdca11c0a465",
  "type": "TRADE"
}
```

### Order Message (USER Channel)

```json
{
  "asset_id": "52114319501245915516055106046884209969926127482827954674443846427813813222426",
  "associate_trades": null,
  "event_type": "order",
  "id": "0xff354cd7ca7539dfa9c28d90943ab5779a4eac34b9b37a757d7b32bdfb11790b",
  "market": "0xbd31dc8a20211944f6b70f31557f1001557b59905b7738480ca09bd4532f84af",
  "order_owner": "9180014b-33c8-9240-a14b-bdca11c0a465",
  "original_size": "10",
  "outcome": "YES",
  "owner": "9180014b-33c8-9240-a14b-bdca11c0a465",
  "price": "0.57",
  "side": "SELL",
  "size_matched": "0",
  "timestamp": "1672290687",
  "type": "PLACEMENT"
}
```

### Book Message (MARKET Channel)

```json
{
  "event_type": "book",
  "asset_id": "65818619657568813474341868652308942079804919287380422192892211131408793125422",
  "market": "0xbd31dc8a20211944f6b70f31557f1001557b59905b7738480ca09bd4532f84af",
  "bids": [
    { "price": ".48", "size": "30" },
    { "price": ".49", "size": "20" }
  ],
  "asks": [
    { "price": ".52", "size": "25" },
    { "price": ".53", "size": "60" }
  ],
  "timestamp": "123456789000",
  "hash": "0x0...."
}
```

### price_change Message (MARKET Channel)

```json
{
  "market": "0x5f65177b394277fd294cd75650044e32ba009a95022d88a0c1d565897d72f8f1",
  "price_changes": [
    {
      "asset_id": "71321045679252212594626385532706912750332728571942532289631379312455583992563",
      "price": "0.5",
      "size": "200",
      "side": "BUY",
      "hash": "56621a121a47ed9333273e21c83b660cff37ae50",
      "best_bid": "0.5",
      "best_ask": "1"
    }
  ],
  "timestamp": "1757908892351",
  "event_type": "price_change"
}
```

## Archivos Creados/Modificados

- ✅ `backend/app/core/execution/polymarket_websocket.py` - Cliente WebSocket
- ✅ `backend/requirements.txt` - Agregado `websocket-client==1.6.4`
- ✅ `docs/POLYMARKET_WEBSOCKET_INTEGRATION.md` - Este documento

## Estado de la Integración

✅ **COMPLETADO** - Integración completa con Execution Engine y Strategy Engine.

### Funcionalidades Implementadas

1. ✅ **Execution Engine Integration**
   - WebSocket USER channel conectado automáticamente al inicializar Execution
   - Callbacks para recibir trades y updates de órdenes en tiempo real
   - Polling se omite cuando WebSocket está activo
   - Manejo de fills automático desde WebSocket trade events

2. ✅ **Strategy Engine Integration**
   - Callbacks configurados para recibir updates de orderbooks y precios
   - Actualización automática de MarketState cuando llegan updates via WebSocket
   - Método `subscribe_to_market()` para suscribirse a mercados específicos

3. ✅ **Reconexión Automática**
   - Implementada en `PolymarketWebSocketClient._run_with_reconnect()`
   - Soporte para límite de reintentos o reintentos infinitos (max_retries=0)
   - Delay configurable entre reintentos (default: 5 segundos)

4. ✅ **Fallback a Polling**
   - Si WebSocket no está disponible o desconectado, el sistema automáticamente usa polling
   - `_poll_order_status()` verifica si WebSocket está activo antes de hacer polling

## Próximos Pasos

1. ⏳ Agregar tests unitarios para WebSocket integration
2. ⏳ Mejorar mapeo de asset_id (token_id) desde market_id para Strategy Engine
3. ⏳ Agregar métricas de latencia de WebSocket vs polling
4. ⏳ Documentar proceso de obtención de API keys
5. ⏳ Agregar soporte para múltiples websockets simultáneos (mejor escalabilidad)

## Referencias

- [Polymarket WebSocket Documentation](https://docs.polymarket.com/developers/clob-rest-api/wss-overview)
- [websocket-client Library](https://github.com/websocket-client/websocket-client)

