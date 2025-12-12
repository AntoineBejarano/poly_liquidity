"""
Market scanner - discovers and updates Polymarket candidate markets.

Este módulo ha sido refactorizado. La nueva implementación está en:
- app.core.scanner.scanner (Scanner principal)
- app.core.scanner.models (Modelos de datos)
- app.core.scanner.filters (Filtros)
- app.core.scanner.normalizer (Normalización)

Este archivo mantiene compatibilidad hacia atrás.
"""
from app.core.scanner.scanner import Scanner

__all__ = ["Scanner"]
    """Market scanner service."""
    
    def __init__(self):
        self._last_scan: datetime | None = None
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def _fetch_markets_from_polymarket(self) -> List[Dict[str, Any]]:
        """
        Fetch markets from Polymarket Data API with rate limiting and caching.
        
        Uses cache to reduce redundant API calls and stay within rate limits.
        """
        cache_key = "market_list"
        
        # Check cache first
        cached = await api_cache.get(cache_key)
        if cached is not None:
            return cached
        
        client = await self._get_client()
        
        # Acquire rate limit permission (Data API: 200 req / 10s)
        try:
            # Wait up to 5 seconds for capacity
            if not await rate_limiter.wait_for_capacity(EndpointType.DATA_API, timeout=5.0):
                print("Warning: Rate limit timeout, skipping market fetch")
                return []
            
            # TODO: Replace with actual Polymarket API endpoint
            # Example structure (needs to be adjusted based on actual API):
            try:
                # This is a placeholder - actual endpoint will be implemented
                # response = await client.get(f"{settings.polymarket_api_url}/markets")
                # 
                # # Check for rate limit errors
                # if response.status_code == 429:
                #     await rate_limiter.record_violation(EndpointType.DATA_API)
                #     raise Exception("Rate limit exceeded")
                # 
                # response.raise_for_status()
                # markets = response.json()
                # result = markets.get("data", [])
                
                # For now, return empty list (will be implemented with real API)
                result = []
                
                # Cache the result
                await api_cache.set(cache_key, result)
                return result
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    await rate_limiter.record_violation(EndpointType.DATA_API)
                    print("Rate limit exceeded, endpoint may be blocked")
                raise
        except Exception as e:
            print(f"Error fetching markets from Polymarket: {e}")
            return []
    
    def _filter_candidate_markets(self, markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter markets based on candidate criteria:
        - Only binary markets (YES/NO)
        - Only OPEN markets
        - Only outcomes with price >= MIN_CANDIDATE_PRICE
        - event_state not marked as RESOLVED
        """
        min_price = config_service.get("min_candidate_price", 0.97)
        candidates = []
        
        for market in markets:
            # Filter: binary markets only
            # Check if it's a binary market (has YES/NO outcomes)
            outcome_type = market.get("outcome_type") or market.get("type")
            if outcome_type and outcome_type != "BINARY":
                continue
            
            # Filter: only OPEN markets
            status = market.get("status") or market.get("market_status")
            if status and status != "OPEN":
                continue
            
            # Filter: price >= MIN_CANDIDATE_PRICE
            # Price might be in different fields depending on API structure
            price = market.get("price") or market.get("last_price") or market.get("current_price", 0.0)
            if price < min_price:
                continue
            
            # Filter: event_state not RESOLVED
            # This will be checked against state.events
            
            candidates.append(market)
        
        return candidates
    
    def _update_market_state(self, market_data: Dict[str, Any], db_market: Market):
        """Update market state in memory."""
        market_id = db_market.id
        
        if market_id not in state.markets:
            from app.core.state import MarketState
            state.markets[market_id] = MarketState()
            state.markets[market_id].market_id = market_id
        
        market_state = state.markets[market_id]
        market_state.polymarket_id = market_data.get("id")
        market_state.last_price = market_data.get("price")
        market_state.spread = market_data.get("spread", 0.0)
        market_state.volume = market_data.get("volume", 0.0)
        market_state.orderbook_snapshot = market_data.get("orderbook", {})
        market_state.updated_at = datetime.utcnow()
    
    async def tick(self):
        """
        Scan markets periodically.
        Updates state.markets and persists to DB.
        """
        # Check if enough time has passed since last scan
        config = config_service.get_risk_config()
        scan_interval = config.scan_interval_seconds
        
        if self._last_scan:
            time_since_scan = (datetime.utcnow() - self._last_scan).total_seconds()
            if time_since_scan < scan_interval:
                return  # Too soon to scan again
        
        # Fetch markets from Polymarket
        markets = await self._fetch_markets_from_polymarket()
        
        # Filter candidates
        candidates = self._filter_candidate_markets(markets)
        
        # Update state and DB
        db = SessionLocal()
        try:
            for market_data in candidates:
                polymarket_id = market_data.get("id")
                if not polymarket_id:
                    continue
                
                # Find or create market in DB
                db_market = db.query(Market).filter(
                    Market.polymarket_id == polymarket_id
                ).first()
                
                if not db_market:
                    # Create new market
                    db_market = Market(
                        id=uuid4(),
                        polymarket_id=polymarket_id,
                        question=market_data.get("question", ""),
                        outcome=market_data.get("outcome", "YES"),
                        status="OPEN",
                        last_price=market_data.get("price"),
                    )
                    db.add(db_market)
                    db.flush()
                    
                    # Create event for this market
                    event = Event(
                        id=uuid4(),
                        market_id=db_market.id,
                        external_event_id=market_data.get("external_event_id"),
                        state="LIVE",
                    )
                    db.add(event)
                else:
                    # Update existing market
                    db_market.last_price = market_data.get("price")
                    db_market.updated_at = datetime.utcnow()
                
                # Update state
                self._update_market_state(market_data, db_market)
            
            db.commit()
            self._last_scan = datetime.utcnow()
        except Exception as e:
            db.rollback()
            print(f"Error in scanner tick: {e}")
        finally:
            db.close()
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
