"""
Execution engine - interacts with Polymarket CLOB to send and manage orders.

DEPRECATED: Este archivo se mantiene por compatibilidad.
Usar app.core.execution.execution.Execution en su lugar.
"""
from app.core.execution import Execution as NewExecution

# Re-exportar para compatibilidad
Execution = NewExecution
    """Execution service."""
    
    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._pending_orders: Dict[str, Order] = {}  # Track orders sent to Polymarket
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    def _sign_order_payload(self, payload: Dict[str, Any], private_key: str) -> str:
        """
        Sign order payload using EIP-712.
        This is a placeholder - actual EIP-712 signing needs Polymarket's domain.
        """
        # TODO: Implement proper EIP-712 signing with Polymarket's domain
        # For now, this is a placeholder
        try:
            # Example EIP-712 signing (needs actual domain and types from Polymarket)
            # message = encode_defunct(text=json.dumps(payload))
            # signed = Account.sign_message(message, private_key)
            # return signed.signature.hex()
            
            # Placeholder
            return "0x" + "0" * 128
        except Exception as e:
            print(f"Error signing order: {e}")
            raise
    
    async def _send_order_to_polymarket(self, order_data: Dict[str, Any], signature: str) -> str | None:
        """
        Send order to Polymarket Trading API with rate limiting.
        
        Trading API: 2400 req / 10s (sufficient for burst execution).
        Measures end-to-end execution latency (order generation → confirmation).
        Returns order_id from Polymarket if successful, None otherwise.
        """
        # Start measuring execution latency (end-to-end)
        execution_start = time.monotonic_ns()
        
        client = await self._get_client()
        
        # Acquire rate limit permission (Trading API: 2400 req / 10s)
        try:
            # Wait up to 2 seconds for capacity (should be fast for trading)
            if not await rate_limiter.wait_for_capacity(EndpointType.TRADING_ORDER, timeout=2.0):
                print("Warning: Rate limit timeout for trading order")
                return None
            
            # TODO: Replace with actual Polymarket API endpoint
            # This is a placeholder - actual endpoint needs to be determined
            try:
                # payload = {
                #     "market": order_data["market_id"],
                #     "side": order_data["side"],
                #     "price": order_data["price"],
                #     "size": order_data["size"],
                #     "signature": signature
                # }
                # response = await client.post(f"{settings.polymarket_api_url}/orders", json=payload)
                # 
                # # Check for rate limit errors
                # if response.status_code == 429:
                #     await rate_limiter.record_violation(EndpointType.TRADING_ORDER)
                #     raise Exception("Rate limit exceeded")
                # 
                # response.raise_for_status()
                # if response.status_code == 200:
                #     order_id = response.json().get("order_id")
                #     
                #     # Measure execution latency (end-to-end)
                #     execution_end = time.monotonic_ns()
                #     execution_latency_ms = (execution_end - execution_start) / 1_000_000
                #     latency_monitor.record_execution_latency(execution_latency_ms)
                #     
                #     return order_id
                
                # For now, simulate execution latency measurement
                await asyncio.sleep(0.1)  # Simulate network + processing time
                execution_end = time.monotonic_ns()
                execution_latency_ms = (execution_end - execution_start) / 1_000_000
                latency_monitor.record_execution_latency(execution_latency_ms)
                
                print(f"Would send order to Polymarket: {order_data} (latency: {execution_latency_ms:.2f}ms)")
                return None
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    await rate_limiter.record_violation(EndpointType.TRADING_ORDER)
                    print("Rate limit exceeded for trading API")
                raise
        except Exception as e:
            print(f"Error sending order to Polymarket: {e}")
            return None
    
    async def _create_order_in_db(self, intent: ApprovedOrderIntent, polymarket_order_id: str | None) -> Order:
        """Create order record in database."""
        db = SessionLocal()
        try:
            order = Order(
                id=uuid4(),
                polymarket_order_id=polymarket_order_id,
                market_id=intent.market_id,
                side=intent.side,
                price=intent.price,
                size=intent.size,
                status="NEW",
                filled_size=0.0,
            )
            db.add(order)
            db.commit()
            db.refresh(order)
            return order
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    
    async def _update_order_state(self, order_id, status: str, filled_size: float):
        """Update order state in memory and DB."""
        if order_id in state.orders:
            state.orders[order_id].status = status
            state.orders[order_id].filled_size = filled_size
            state.orders[order_id].updated_at = datetime.utcnow()
        
        # Update in DB
        db = SessionLocal()
        try:
            db_order = db.query(Order).filter(Order.id == order_id).first()
            if db_order:
                db_order.status = status
                db_order.filled_size = filled_size
                db_order.updated_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error updating order in DB: {e}")
        finally:
            db.close()
    
    async def _handle_fill(self, order_id, fill_price: float, fill_size: float):
        """Handle order fill - update position and create trade."""
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return
            
            # Create trade record
            trade = Trade(
                id=uuid4(),
                order_id=order_id,
                market_id=order.market_id,
                fill_price=fill_price,
                fill_size=fill_size,
                direction=order.side,
                timestamp=datetime.utcnow(),
            )
            db.add(trade)
            
            # Update or create position
            position = db.query(Position).filter(Position.market_id == order.market_id).first()
            if not position:
                position = Position(
                    id=uuid4(),
                    market_id=order.market_id,
                    size=fill_size,
                    avg_price=fill_price,
                    resolved=False,
                )
                db.add(position)
            else:
                # Recalculate average price
                total_cost = (position.size * position.avg_price) + (fill_size * fill_price)
                total_size = position.size + fill_size
                position.avg_price = total_cost / total_size if total_size > 0 else fill_price
                position.size = total_size
            
            # Update position state
            if order.market_id not in state.positions:
                from app.core.state import PositionState
                state.positions[order.market_id] = PositionState()
                state.positions[order.market_id].market_id = order.market_id
            
            pos_state = state.positions[order.market_id]
            pos_state.size = position.size
            pos_state.avg_price = position.avg_price
            pos_state.updated_at = datetime.utcnow()
            
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error handling fill: {e}")
        finally:
            db.close()
    
    async def _poll_order_status(self, order_id):
        """
        Poll Polymarket for order status and fills with rate limiting.
        
        Uses Data API for order status (200 req / 10s).
        This is a placeholder - actual implementation needs Polymarket API.
        """
        # TODO: Implement polling from Polymarket API with rate limiting
        # Example:
        # try:
        #     if not await rate_limiter.wait_for_capacity(EndpointType.DATA_API, timeout=1.0):
        #         return  # Skip this poll, will retry next tick
        #     
        #     client = await self._get_client()
        #     response = await client.get(f"{settings.polymarket_api_url}/orders/{order_id}")
        #     
        #     if response.status_code == 429:
        #         await rate_limiter.record_violation(EndpointType.DATA_API)
        #         return
        #     
        #     response.raise_for_status()
        #     order_status = response.json()
        #     # Process order status...
        # except Exception as e:
        #     print(f"Error polling order status: {e}")
        
        # For now, this is a placeholder
        pass
    
    async def _cancel_order(self, order_id):
        """
        Cancel an order in Polymarket with rate limiting.
        
        Uses Trading API for cancellations (2400 req / 10s).
        """
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order or order.status in ("FILLED", "CANCELLED"):
                return
            
            # Acquire rate limit permission
            if not await rate_limiter.wait_for_capacity(EndpointType.TRADING_ORDER, timeout=1.0):
                print(f"Warning: Rate limit timeout for cancel order {order_id}")
                return
            
            # TODO: Send cancel to Polymarket API
            # try:
            #     client = await self._get_client()
            #     response = await client.delete(f"{settings.polymarket_api_url}/orders/{order.polymarket_order_id}")
            #     
            #     if response.status_code == 429:
            #         await rate_limiter.record_violation(EndpointType.TRADING_ORDER)
            #         return
            #     
            #     response.raise_for_status()
            # except httpx.HTTPStatusError as e:
            #     if e.response.status_code == 429:
            #         await rate_limiter.record_violation(EndpointType.TRADING_ORDER)
            #     raise
            
            # Update status
            await self._update_order_state(order_id, "CANCELLED", order.filled_size)
        finally:
            db.close()
    
    async def _cancel_all_open_orders(self, market_id=None):
        """Cancel all open orders, optionally for a specific market."""
        db = SessionLocal()
        try:
            query = db.query(Order).filter(Order.status.in_(["NEW", "PARTIALLY_FILLED"]))
            if market_id:
                query = query.filter(Order.market_id == market_id)
            
            orders = query.all()
            for order in orders:
                await self._cancel_order(order.id)
        finally:
            db.close()
    
    async def tick(self, approved_intents: List[ApprovedOrderIntent]):
        """
        Send/cancel orders based on approved intents.
        """
        # Check trading circuit breaker
        from app.core.runtime_supervisor import RuntimeSupervisor
        # Importar runtime_supervisor de forma lazy para evitar importación circular
        import app.main as main_module
        runtime_supervisor = main_module.runtime_supervisor
        
        if runtime_supervisor.trading_circuit.is_open():
            print("Trading circuit breaker OPEN: Not sending new orders")
            return
        
        # Check wallet is available
        wallet = await wallet_service.get_active_wallet()
        if not wallet:
            print("Warning: No active wallet, cannot execute orders")
            return
        
        # wallet is now WalletInMemory (Pydantic model), access attributes directly
        
        # Send new orders
        for intent in approved_intents:
            try:
                # Build order payload
                order_data = {
                    "market_id": str(intent.market_id),
                    "side": intent.side,
                    "price": intent.price,
                    "size": intent.size,
                }
                
                # Sign order (wallet is WalletInMemory, access private_key attribute)
                signature = self._sign_order_payload(order_data, wallet.private_key)
                
                # Send to Polymarket
                polymarket_order_id = await self._send_order_to_polymarket(order_data, signature)
                
                # Create order in DB
                order = await self._create_order_in_db(intent, polymarket_order_id)
                
                # Update state
                from app.core.state import OrderState
                order_state = OrderState()
                order_state.order_id = order.id
                order_state.market_id = order.market_id
                order_state.status = order.status
                order_state.filled_size = order.filled_size
                order_state.updated_at = order.created_at
                state.orders[order.id] = order_state
                
                # Track pending order
                self._pending_orders[str(order.id)] = order
                
                # Registrar éxito en circuit breaker
                runtime_supervisor.record_trading_success()
                
            except Exception as e:
                print(f"Error executing order intent: {e}")
                # Registrar fallo en circuit breaker
                runtime_supervisor.record_trading_failure()
        
        # Poll for order status updates (simplified - should be async/background)
        # This will be improved with WebSocket or better polling mechanism
        for order_id, order in list(self._pending_orders.items()):
            if order.status in ("FILLED", "CANCELLED"):
                self._pending_orders.pop(order_id)
            else:
                await self._poll_order_status(order.id)
        
        # Cancel orders if system is paused or market is paused
        if not state.system_active:
            await self._cancel_all_open_orders()
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
