"""
Smoke Tests INTERNAL - Deterministas, CI.

No tocan Polymarket real.
Inyectan mensajes WS de ejemplo en el pipeline y verifican que acaban en cache.

Sirven para detectar:
- Router roto
- Publisher roto
- Cache roto
- Schema roto
- Parser roto
"""
import pytest
import asyncio
import time
from sqlalchemy.orm import Session
from app.core.orderbook.service import get_orderbook_service, OrderbookService
from app.core.strategy_engine.state_cache_service import StateCacheService


class TestSmokeInternal:
    """Smoke tests INTERNAL - Deterministas, CI."""
    
    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        """Setup para cada test."""
        # Crear StateCacheService con la sesión de test
        self.db_session = db_session
        self.cache_service = StateCacheService(db_session)
        
        # Resetear el singleton de OrderbookService para usar la sesión de test
        from app.core.orderbook.service import _orderbook_service
        import app.core.orderbook.service as orderbook_service_module
        orderbook_service_module._orderbook_service = None
        
        yield
        # Cleanup después de cada test
        # Resetear el singleton después del test
        orderbook_service_module._orderbook_service = None
    
    @pytest.mark.asyncio
    async def test_smoke_internal_websocket_pipeline(self):
        """
        Smoke test INTERNAL: Verifica que el pipeline WS → Orderbook → Cache funciona.
        
        No requiere conexión real a Polymarket.
        Inyecta mensaje WS de ejemplo y verifica que acaba en State Cache.
        """
        # 1. Crear mensaje WS de ejemplo (fixture)
        book_msg = {
            "event_type": "book",
            "asset_id": "0x1234567890123456789012345678901234567890",
            "market": "0xbd31dc8a123456789012345678901234567890",
            "bids": [
                {"price": ".48", "size": "30"},
                {"price": ".49", "size": "20"}
            ],
            "asks": [
                {"price": ".52", "size": "25"},
                {"price": ".53", "size": "60"}
            ],
            "timestamp": str(int(time.time() * 1000)),
            "hash": "0x0abcdef1234567890abcdef1234567890abcdef"
        }
        
        # 2. Suscribirse al asset_id (necesario para que el orchestrator tenga el book)
        # Inicializar OrderbookService con la sesión de test
        orderbook_service = get_orderbook_service(self.cache_service)
        owner_key = "smoke_internal_test"
        orderbook_service.subscribe(book_msg["asset_id"], owner_key)
        
        try:
            # 3. Inyectar mensaje en el pipeline
            await orderbook_service._handle_ws_book_update_async(book_msg)
            
            # 4. Esperar un poco para que se publique en cache
            await asyncio.sleep(0.1)
            
            # 5. Verificar que está en State Cache
            cache_key = f"pm.orderbook.{book_msg['asset_id']}"
            
            orderbook_state = await self.cache_service.get(cache_key)
            
            assert orderbook_state is not None, "Orderbook debe estar en cache"
            assert "best_bid_price" in orderbook_state, "Debe tener best_bid_price"
            assert "best_ask_price" in orderbook_state, "Debe tener best_ask_price"
            assert orderbook_state["best_bid_price"] == 0.49, f"Best bid debe ser 0.49, obtuvo {orderbook_state['best_bid_price']}"
            assert orderbook_state["best_ask_price"] == 0.52, f"Best ask debe ser 0.52, obtuvo {orderbook_state['best_ask_price']}"
            assert len(orderbook_state.get("bids", [])) == 2, f"Debe tener 2 bids, obtuvo {len(orderbook_state.get('bids', []))}"
            assert len(orderbook_state.get("asks", [])) == 2, f"Debe tener 2 asks, obtuvo {len(orderbook_state.get('asks', []))}"
            
            # Verificar que tiene hash en integrity
            if "integrity" in orderbook_state:
                assert orderbook_state["integrity"].get("hash") == book_msg["hash"], "Hash debe estar en integrity"
        
        finally:
            # Cleanup: Unsubscribe
            try:
                orderbook_service.unsubscribe(book_msg["asset_id"], owner_key)
            except Exception:
                pass
    
    @pytest.mark.asyncio
    async def test_ws_schema_contract_bids_asks(self, db_session: Session):
        """
        Contract test: Parser acepta bids/asks.
        
        Verifica que el parser maneja correctamente el formato estándar.
        """
        book_msg = {
            "event_type": "book",
            "asset_id": "0xcontract_test_bids_asks",
            "market": "0xmarket",
            "bids": [
                {"price": ".48", "size": "30"},
                {"price": ".49", "size": "20"}
            ],
            "asks": [
                {"price": ".52", "size": "25"},
                {"price": ".53", "size": "60"}
            ],
            "timestamp": str(int(time.time() * 1000))
        }
        
        cache_service = StateCacheService(db_session)
        orderbook_service = get_orderbook_service(cache_service)
        owner_key = "smoke_contract_test"
        orderbook_service.subscribe(book_msg["asset_id"], owner_key)
        
        try:
            await orderbook_service._handle_ws_book_update_async(book_msg)
            await asyncio.sleep(0.1)
            
            cache_service = StateCacheService(db_session)
            cache_key = f"pm.orderbook.{book_msg['asset_id']}"
            orderbook_state = await cache_service.get(cache_key)
            
            assert orderbook_state is not None, "Orderbook debe estar en cache con bids/asks"
            assert orderbook_state["best_bid_price"] == 0.49
            assert orderbook_state["best_ask_price"] == 0.52
        finally:
            try:
                orderbook_service.unsubscribe(book_msg["asset_id"], owner_key)
            except Exception:
                pass
    
    @pytest.mark.asyncio
    async def test_ws_schema_contract_buys_sells(self, db_session: Session):
        """
        Contract test: Parser acepta buys/sells (alias de bids/asks).
        
        Verifica que el parser maneja correctamente el formato alternativo.
        """
        book_msg = {
            "event_type": "book",
            "asset_id": "0xcontract_test_buys_sells",
            "market": "0xmarket",
            "buys": [
                {"price": ".48", "size": "30"},
                {"price": ".49", "size": "20"}
            ],
            "sells": [
                {"price": ".52", "size": "25"},
                {"price": ".53", "size": "60"}
            ],
            "timestamp": str(int(time.time() * 1000))
        }
        
        cache_service = StateCacheService(db_session)
        orderbook_service = get_orderbook_service(cache_service)
        owner_key = "smoke_contract_test"
        orderbook_service.subscribe(book_msg["asset_id"], owner_key)
        
        try:
            await orderbook_service._handle_ws_book_update_async(book_msg)
            await asyncio.sleep(0.1)
            
            cache_service = StateCacheService(db_session)
            cache_key = f"pm.orderbook.{book_msg['asset_id']}"
            orderbook_state = await cache_service.get(cache_key)
            
            assert orderbook_state is not None, "Orderbook debe estar en cache con buys/sells"
            assert orderbook_state["best_bid_price"] == 0.49
            assert orderbook_state["best_ask_price"] == 0.52
        finally:
            try:
                orderbook_service.unsubscribe(book_msg["asset_id"], owner_key)
            except Exception:
                pass
    
    @pytest.mark.asyncio
    async def test_ws_schema_contract_hash_optional(self, db_session: Session):
        """
        Contract test: Parser maneja hash opcional.
        
        Verifica que el parser funciona tanto con hash como sin hash.
        """
        # Test con hash
        book_msg_with_hash = {
            "event_type": "book",
            "asset_id": "0xcontract_test_with_hash",
            "market": "0xmarket",
            "bids": [{"price": ".48", "size": "30"}],
            "asks": [{"price": ".52", "size": "25"}],
            "timestamp": str(int(time.time() * 1000)),
            "hash": "0xhash123"
        }
        
        # Test sin hash
        book_msg_without_hash = {
            "event_type": "book",
            "asset_id": "0xcontract_test_without_hash",
            "market": "0xmarket",
            "bids": [{"price": ".48", "size": "30"}],
            "asks": [{"price": ".52", "size": "25"}],
            "timestamp": str(int(time.time() * 1000))
        }
        
        cache_service = StateCacheService(db_session)
        orderbook_service = get_orderbook_service(cache_service)
        owner_key = "smoke_contract_test"
        
        # Test con hash
        orderbook_service.subscribe(book_msg_with_hash["asset_id"], owner_key)
        try:
            await orderbook_service._handle_ws_book_update_async(book_msg_with_hash)
            await asyncio.sleep(0.1)
            
            cache_service = StateCacheService(db_session)
            cache_key = f"pm.orderbook.{book_msg_with_hash['asset_id']}"
            orderbook_state = await cache_service.get(cache_key)
            
            assert orderbook_state is not None, "Orderbook debe estar en cache con hash"
            if "integrity" in orderbook_state:
                assert orderbook_state["integrity"].get("hash") == "0xhash123"
        finally:
            try:
                orderbook_service.unsubscribe(book_msg_with_hash["asset_id"], owner_key)
            except Exception:
                pass
        
        # Test sin hash
        orderbook_service.subscribe(book_msg_without_hash["asset_id"], owner_key)
        try:
            await orderbook_service._handle_ws_book_update_async(book_msg_without_hash)
            await asyncio.sleep(0.1)
            
            cache_service = StateCacheService(db_session)
            cache_key = f"pm.orderbook.{book_msg_without_hash['asset_id']}"
            orderbook_state = await cache_service.get(cache_key)
            
            assert orderbook_state is not None, "Orderbook debe estar en cache sin hash"
        finally:
            try:
                orderbook_service.unsubscribe(book_msg_without_hash["asset_id"], owner_key)
            except Exception:
                pass
    
    @pytest.mark.asyncio
    async def test_ws_schema_contract_string_prices(self, db_session: Session):
        """
        Contract test: Parser maneja strings tipo ".48" → 0.48.
        
        Verifica que el parser convierte correctamente strings a floats.
        """
        book_msg = {
            "event_type": "book",
            "asset_id": "0xcontract_test_strings",
            "market": "0xmarket",
            "bids": [
                {"price": ".48", "size": "30"},
                {"price": "0.49", "size": "20"}
            ],
            "asks": [
                {"price": ".52", "size": "25"},
                {"price": "0.53", "size": "60"}
            ],
            "timestamp": str(int(time.time() * 1000))
        }
        
        cache_service = StateCacheService(db_session)
        orderbook_service = get_orderbook_service(cache_service)
        owner_key = "smoke_contract_test"
        orderbook_service.subscribe(book_msg["asset_id"], owner_key)
        
        try:
            await orderbook_service._handle_ws_book_update_async(book_msg)
            await asyncio.sleep(0.1)
            
            cache_service = StateCacheService(db_session)
            cache_key = f"pm.orderbook.{book_msg['asset_id']}"
            orderbook_state = await cache_service.get(cache_key)
            
            assert orderbook_state is not None, "Orderbook debe estar en cache con strings"
            assert orderbook_state["best_bid_price"] == 0.49, "Debe convertir '.49' y '0.49' correctamente"
            assert orderbook_state["best_ask_price"] == 0.52, "Debe convertir '.52' y '0.52' correctamente"
        finally:
            try:
                orderbook_service.unsubscribe(book_msg["asset_id"], owner_key)
            except Exception:
                pass

