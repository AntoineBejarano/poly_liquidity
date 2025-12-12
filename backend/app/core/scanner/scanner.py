"""
Market scanner - discovers and updates Polymarket candidate markets.

Refactorizado según especificación en docs/services/scanner.md
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4, UUID
from app.core.state import state
from app.core.config_service import config_service
from app.core.rate_limiter import rate_limiter, EndpointType
from app.core.api_cache import api_cache
from app.core.metrics.metrics_service import metrics_service
from app.database import SessionLocal
from app.models.market import Market
from app.models.event import Event
from app.settings import settings
from app.core.scanner.models import CandidateMarket
from app.core.scanner.filters import ScannerFilters
from app.core.scanner.normalizer import ScannerNormalizer


class Scanner:
    """
    Market scanner service.
    
    Responsabilidades:
    - Descargar mercados activos de Polymarket
    - Filtrar mercados relevantes
    - Normalizar y enriquecer datos
    - Reducir consumo de API mediante caching
    - Mantener trazabilidad completa
    """
    
    def __init__(self, config=None):
        """
        Inicializa el scanner.
        
        Args:
            config: RiskConfig (opcional, para tests)
        """
        self._last_scan: Optional[datetime] = None
        self._client: Optional[httpx.AsyncClient] = None
        self.filters = ScannerFilters(config=config)
        self.normalizer = ScannerNormalizer()
        self._event_mapping_layer = None  # Lazy import para evitar circular dependency
        self._event_watch_coordinator = None  # Lazy import para evitar circular dependency
        self._scan_count = 0
        self._markets_scanned_total = 0
        self._markets_filtered_total = 0
    
    @property
    def event_mapping_layer(self):
        """Lazy import de EventMappingLayer para evitar circular dependency."""
        if self._event_mapping_layer is None:
            from app.core.event_mapping_layer import EventMappingLayer
            self._event_mapping_layer = EventMappingLayer()
        return self._event_mapping_layer
    
    def _get_event_watch_coordinator(self):
        """Lazy import de EventWatchCoordinator para evitar circular dependency."""
        if self._event_watch_coordinator is None:
            try:
                from app.core.event_watch_engine import EventWatchCoordinator
                self._event_watch_coordinator = EventWatchCoordinator()
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to import EventWatchCoordinator: {e}")
                return None
        return self._event_watch_coordinator
    
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
        cache_key = "scanner:markets_raw"
        cache_ttl = 5  # 5 segundos
        
        # Check cache first
        cached = await api_cache.get(cache_key)
        if cached is not None:
            return cached
        
        client = await self._get_client()
        
        # Acquire rate limit permission (Data API: 200 req / 10s)
        try:
            # Wait up to 5 seconds for capacity
            if not await rate_limiter.wait_for_capacity(EndpointType.DATA_API, timeout=5.0):
                print("Warning: Rate limit timeout, using cached markets if available")
                # Intentar obtener cache antiguo como fallback
                cached = await api_cache.get(cache_key)
                return cached if cached is not None else []
            
            # TODO: Replace with actual Polymarket API endpoint
            # Example structure (needs to be adjusted based on actual API):
            try:
                # This is a placeholder - actual endpoint will be implemented
                # response = await client.get(f"{settings.polymarket_api_url}/markets?limit=100")
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
                await api_cache.set(cache_key, result, ttl=cache_ttl)
                return result
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    await rate_limiter.record_violation(EndpointType.DATA_API)
                    print("Rate limit exceeded, endpoint may be blocked")
                    # Usar cache como fallback
                    cached = await api_cache.get(cache_key)
                    return cached if cached is not None else []
                raise
        except Exception as e:
            print(f"Error fetching markets from Polymarket: {e}")
            # Usar cache como fallback
            cached = await api_cache.get(cache_key)
            return cached if cached is not None else []
    
    def _filter_candidate_markets(
        self,
        markets: List[Dict[str, Any]],
        trace_id: str
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filtra mercados candidatos aplicando todos los filtros.
        
        Args:
            markets: Lista de mercados raw
            trace_id: ID de trazabilidad
        
        Returns:
            (mercados_que_pasan, razones_de_rechazo)
        """
        candidates = []
        rejections = []
        
        for market in markets:
            # Aplicar todos los filtros
            passes, reason = self.filters.apply_all_filters(market)
            
            if passes:
                candidates.append(market)
            else:
                rejections.append({
                    "polymarket_id": market.get("id") or market.get("market_id", "unknown"),
                    "reason": reason,
                    "trace_id": trace_id
                })
        
        return candidates, rejections
    
    def _normalize_markets(
        self,
        markets: List[Dict[str, Any]],
        trace_id: str
    ) -> List[CandidateMarket]:
        """
        Normaliza mercados raw a CandidateMarket.
        
        Args:
            markets: Lista de mercados raw que pasaron filtros
            trace_id: ID de trazabilidad
        
        Returns:
            Lista de CandidateMarket normalizados
        """
        normalized = []
        
        for market in markets:
            try:
                candidate = self.normalizer.normalize_market(market, trace_id)
                normalized.append(candidate)
            except Exception as e:
                print(f"Error normalizing market {market.get('id', 'unknown')}: {e}")
                continue
        
        return normalized
    
    def _update_market_state(self, candidate: CandidateMarket, db_market: Market):
        """Update market state in memory."""
        market_id = db_market.id
        
        if market_id not in state.markets:
            from app.core.state import MarketState
            state.markets[market_id] = MarketState()
            state.markets[market_id].market_id = market_id
        
        market_state = state.markets[market_id]
        market_state.polymarket_id = candidate.polymarket_id
        market_state.last_price = candidate.best_yes_price
        market_state.spread = candidate.spread
        market_state.volume = candidate.volume_24h
        market_state.updated_at = datetime.utcnow()
    
    async def tick(self):
        """
        Scan markets periodically.
        
        Updates state.markets and persists to DB.
        Emite métricas del proceso de escaneo.
        """
        # Generar trace_id para este scan
        trace_id = str(uuid4())
        
        # Check if enough time has passed since last scan
        config = config_service.get_risk_config()
        scan_interval = config.scan_interval_seconds
        
        if self._last_scan:
            time_since_scan = (datetime.utcnow() - self._last_scan).total_seconds()
            if time_since_scan < scan_interval:
                return  # Too soon to scan again
        
        scan_start = datetime.utcnow()
        
        try:
            # Fetch markets from Polymarket
            markets = await self._fetch_markets_from_polymarket()
            
            # Filter candidates
            candidates_raw, rejections = self._filter_candidate_markets(markets, trace_id)
            
            # Normalize markets
            candidates = self._normalize_markets(candidates_raw, trace_id)
            
            # Map markets to external events using Event Mapping Layer
            event_descriptors = await self.event_mapping_layer.map_markets(candidates)
            
            # Emitir métricas
            mapped_count = sum(1 for desc in event_descriptors if desc.mapped)
            await metrics_service.collector.record_event(
                "scanner_scan_completed",
                {
                    "markets_fetched": len(markets),
                    "markets_filtered": len(candidates),
                    "markets_rejected": len(rejections),
                    "markets_mapped": mapped_count,
                    "trace_id": trace_id,
                    "value": len(candidates)
                },
                component="scanner"
            )
            
            # Update state and DB
            db = SessionLocal()
            try:
                for candidate, descriptor in zip(candidates, event_descriptors):
                    # Find or create market in DB
                    db_market = db.query(Market).filter(
                        Market.polymarket_id == candidate.polymarket_id
                    ).first()
                    
                    if not db_market:
                        # Create new market
                        db_market = Market(
                            id=uuid4(),
                            polymarket_id=candidate.polymarket_id,
                            question=candidate.question,
                            outcome="YES",
                            status=candidate.status,
                            last_price=candidate.best_yes_price,
                        )
                        db.add(db_market)
                        db.flush()
                        
                        # Create event for this market
                        event = Event(
                            id=uuid4(),
                            market_id=db_market.id,
                            external_event_id=descriptor.canonical_event_id if descriptor.mapped else None,
                            state="LIVE",
                        )
                        db.add(event)
                    else:
                        # Update existing market
                        db_market.last_price = candidate.best_yes_price
                        db_market.updated_at = datetime.utcnow()
                        
                    # Update event with mapping if available
                    event = db.query(Event).filter(Event.market_id == db_market.id).first()
                    if event and descriptor.mapped and descriptor.canonical_event_id:
                        event.external_event_id = descriptor.canonical_event_id
                    
                    # Register watcher for mapped events (lazy import para evitar circular dependency)
                    if descriptor.mapped and descriptor.canonical_event_id:
                        try:
                            event_watch_coordinator = self._get_event_watch_coordinator()
                            if event_watch_coordinator:
                                await event_watch_coordinator.register_event(descriptor, db_market.id)
                        except Exception as e:
                            logger.warning(f"Failed to register watcher for event {descriptor.canonical_event_id}: {e}")
                    
                    # Update state
                    self._update_market_state(candidate, db_market)
                
                db.commit()
                self._last_scan = datetime.utcnow()
                
                # Actualizar contadores
                self._scan_count += 1
                self._markets_scanned_total += len(markets)
                self._markets_filtered_total += len(candidates)
                
            except Exception as e:
                db.rollback()
                print(f"Error in scanner tick: {e}")
                # Emitir métrica de error
                await metrics_service.collector.record_event(
                    "scanner_error",
                    {
                        "error": str(e),
                        "trace_id": trace_id,
                        "value": 1.0
                    },
                    component="scanner"
                )
            finally:
                db.close()
            
            # Calcular latencia del scan
            scan_duration_ms = (datetime.utcnow() - scan_start).total_seconds() * 1000
            await metrics_service.collector.store.store_metric(
                "scanner_latency_ms",
                scan_duration_ms,
                component="scanner"
            )
            
        except Exception as e:
            print(f"Critical error in scanner tick: {e}")
            # Emitir métrica de error crítico
            await metrics_service.collector.record_event(
                "scanner_critical_error",
                {
                    "error": str(e),
                    "trace_id": trace_id,
                    "value": 1.0
                },
                component="scanner"
            )
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del scanner."""
        return {
            "scan_count": self._scan_count,
            "markets_scanned_total": self._markets_scanned_total,
            "markets_filtered_total": self._markets_filtered_total,
            "last_scan": self._last_scan.isoformat() if self._last_scan else None
        }

