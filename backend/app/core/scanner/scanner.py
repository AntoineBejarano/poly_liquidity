"""
Market scanner - discovers and updates Polymarket candidate markets.

Refactorizado según especificación en docs/services/scanner.md
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from app.core.state import state
from app.core.config_service import config_service
from app.core.decision_trace import decision_trace_service
from app.core.rate_limiter import rate_limiter, EndpointType
from app.core.api_cache import api_cache
from app.core.metrics.metrics_service import metrics_service
from app.database import SessionLocal
from app.models.market import Market
from app.models.event import Event
from app.models.series import Series
from app.models.tag import Tag
from app.models.market_tag import MarketTag
from app.settings import settings
from app.core.scanner.models import CandidateMarket
from app.core.scanner.filters import ScannerFilters
from app.core.scanner.normalizer import ScannerNormalizer
import logging

logger = logging.getLogger(__name__)


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
            # Obtener timeout desde ConfigService
            http_timeout = config_service.get("scanner_http_timeout_seconds", 30.0)
            self._client = httpx.AsyncClient(timeout=http_timeout)
        return self._client
    
    async def _discover_series(self) -> List[Dict[str, Any]]:
        """
        Descubre Series desde Polymarket Gamma API.
        
        ⚠️ IMPORTANTE: Implementa caching para evitar explosión de requests.
        - Cachear Series con updated_at / last_seen
        - No rediscover todo en cada tick
        - Solo actualizar Series que hayan cambiado
        """
        cache_key = "scanner:series_raw"
        cache_ttl_seconds = config_service.get("scanner_series_cache_ttl_seconds", 300)  # 5 minutos por defecto
        cache_ttl = timedelta(seconds=cache_ttl_seconds)
        
        # Check cache first
        cached = await api_cache.get(cache_key)
        if cached is not None:
            logger.debug("Using cached series data")
            return cached
        
        client = await self._get_client()
        
        try:
            # Acquire rate limit permission (GAMMA API: 750 req / 10s)
            if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_GENERAL, timeout=5.0):
                logger.warning("Rate limit timeout for series discovery, using cached data if available")
                cached = await api_cache.get(cache_key)
                return cached if cached is not None else []
            
            url = f"{settings.polymarket_gamma_api_url}/series"
            response = await client.get(url)
            
            if response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_GENERAL)
                logger.warning("Rate limit exceeded for series, using cached data if available")
                cached = await api_cache.get(cache_key)
                return cached if cached is not None else []
            
            response.raise_for_status()
            data = response.json()
            
            # Handle both array and object responses
            if isinstance(data, list):
                series_list = data
            else:
                series_list = data.get("data", [])
            
            logger.info(f"Discovered {len(series_list)} series from Gamma API")
            
            # Cache the result
            await api_cache.set(cache_key, series_list, ttl=cache_ttl)
            return series_list
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_GENERAL)
                logger.warning("Rate limit exceeded, using cached data if available")
                cached = await api_cache.get(cache_key)
                return cached if cached is not None else []
            logger.error(f"HTTP error fetching series: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching series from Polymarket: {e}", exc_info=True)
            cached = await api_cache.get(cache_key)
            return cached if cached is not None else []
    
    async def _discover_markets_from_series(self, series_id: str) -> List[Dict[str, Any]]:
        """
        Descubre Markets de una Series específica.
        
        ⚠️ IMPORTANTE: Implementa caching para evitar explosión de requests.
        - Cachear Markets con updated_at / last_seen
        - Solo actualizar si hay cambios
        """
        cache_key = f"scanner:series:{series_id}:markets"
        cache_ttl_seconds = config_service.get("scanner_markets_cache_ttl_seconds", 60)  # 1 minuto por defecto
        cache_ttl = timedelta(seconds=cache_ttl_seconds)
        
        # Check cache first
        cached = await api_cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Using cached markets for series {series_id}")
            return cached
        
        client = await self._get_client()
        
        try:
            # Acquire rate limit permission (GAMMA API: 750 req / 10s)
            if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_GENERAL, timeout=5.0):
                logger.warning(f"Rate limit timeout for series {series_id} markets, using cached data if available")
                cached = await api_cache.get(cache_key)
                return cached if cached is not None else []
            
            url = f"{settings.polymarket_gamma_api_url}/series/{series_id}"
            response = await client.get(url)
            
            if response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_GENERAL)
                logger.warning(f"Rate limit exceeded for series {series_id}, using cached data if available")
                cached = await api_cache.get(cache_key)
                return cached if cached is not None else []
            
            response.raise_for_status()
            data = response.json()
            
            # Extract markets from series response
            # Series response typically contains a "markets" array
            markets = data.get("markets", [])
            
            # Log para debugging: ver qué estructura tiene la respuesta
            if not markets:
                logger.debug(f"Series {series_id} response keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                # Intentar otras posibles estructuras
                if "data" in data and isinstance(data["data"], list):
                    markets = data["data"]
                elif isinstance(data, list):
                    markets = data
            
            logger.debug(f"Discovered {len(markets)} markets from series {series_id}")
            
            # Cache the result
            await api_cache.set(cache_key, markets, ttl=cache_ttl)
            return markets
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_GENERAL)
                logger.warning(f"Rate limit exceeded for series {series_id}, using cached data if available")
                cached = await api_cache.get(cache_key)
                return cached if cached is not None else []
            logger.error(f"HTTP error fetching markets for series {series_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching markets for series {series_id}: {e}", exc_info=True)
            cached = await api_cache.get(cache_key)
            return cached if cached is not None else []
    
    async def _discover_events_from_market(self, market_id: str) -> List[Dict[str, Any]]:
        """
        Descubre Events de un Market activo (solo si enabled=true).
        
        ⚠️ IMPORTANTE: Solo ejecutar para Markets con enabled=true.
        - Crea/actualiza Events en DB con:
          - polymarket_event_id (ID de Polymarket, String)
          - market_id
          - start_time, end_time
          - state (UPCOMING, ACTIVE, FINISHED)
        """
        cache_key = f"scanner:market:{market_id}:events"
        cache_ttl_seconds = config_service.get("scanner_events_cache_ttl_seconds", 30)  # 30 segundos por defecto
        cache_ttl = timedelta(seconds=cache_ttl_seconds)
        
        # Check cache first
        cached = await api_cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Using cached events for market {market_id}")
            return cached
        
        client = await self._get_client()
        
        try:
            # Acquire rate limit permission (GAMMA MARKETS: 125 req / 10s)
            if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_MARKETS, timeout=5.0):
                logger.warning(f"Rate limit timeout for market {market_id} events, using cached data if available")
                cached = await api_cache.get(cache_key)
                return cached if cached is not None else []
            
            url = f"{settings.polymarket_gamma_api_url}/markets/{market_id}"
            response = await client.get(url)
            
            if response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_MARKETS)
                logger.warning(f"Rate limit exceeded for market {market_id}, using cached data if available")
                cached = await api_cache.get(cache_key)
                return cached if cached is not None else []
            
            response.raise_for_status()
            data = response.json()
            
            # Extract events from market response
            # Market response typically contains events or related data
            # Structure may vary, handle both cases
            events = []
            if "events" in data:
                events = data["events"] if isinstance(data["events"], list) else [data["events"]]
            elif "event" in data:
                events = [data["event"]]
            # Some markets might have events embedded differently
            # Check for common patterns
            
            logger.debug(f"Discovered {len(events)} events from market {market_id}")
            
            # Cache the result
            await api_cache.set(cache_key, events, ttl=cache_ttl)
            return events
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_MARKETS)
                logger.warning(f"Rate limit exceeded for market {market_id}, using cached data if available")
                cached = await api_cache.get(cache_key)
                return cached if cached is not None else []
            logger.error(f"HTTP error fetching events for market {market_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching events for market {market_id}: {e}", exc_info=True)
            cached = await api_cache.get(cache_key)
            return cached if cached is not None else []
    
    async def _fetch_markets_from_polymarket(self) -> List[Dict[str, Any]]:
        """
        Fetch markets from Polymarket Gamma API with rate limiting and caching.
        
        Uses Gamma API /events endpoint (most efficient for retrieving all active markets).
        Implements pagination to fetch all markets.
        
        According to official docs:
        - Use /events endpoint for best efficiency
        - Use closed=false to only get active markets
        - Use order=id&ascending=false to get newest first
        - Implement pagination with limit and offset
        """
        cache_key = "scanner:markets_raw"
        # Obtener TTL desde ConfigService
        cache_ttl_seconds = config_service.get("scanner_cache_ttl_seconds", 5)
        cache_ttl = timedelta(seconds=cache_ttl_seconds)
        
        # Check cache first
        cached = await api_cache.get(cache_key)
        if cached is not None:
            return cached
        
        client = await self._get_client()
        
        # Acquire rate limit permission (Data API: 200 req / 10s)
        # Note: Gamma API may have different limits, but using same endpoint type for now
        try:
            # Wait up to 5 seconds for capacity
            if not await rate_limiter.wait_for_capacity(EndpointType.DATA_API, timeout=5.0):
                logger.warning("Rate limit timeout, using cached markets if available")
                # Intentar obtener cache antiguo como fallback
                cached = await api_cache.get(cache_key)
                return cached if cached is not None else []
            
            # Use Gamma API /events endpoint (recommended approach)
            # Parameters according to official docs:
            # - order=id: Order by event ID
            # - ascending=false: Get newest events first
            # - closed=false: Only active markets (CRITICAL)
            # - limit: Control response size (100 is a good default)
            # - offset: For pagination (start at 0)
            all_markets = []
            # Obtener parámetros de paginación desde ConfigService
            limit = config_service.get("scanner_pagination_limit", 100)
            offset = 0
            max_pages = config_service.get("scanner_max_pages", 10)  # Safety limit
            
            for page in range(max_pages):
                try:
                    url = f"{settings.polymarket_gamma_api_url}/events"
                    params = {
                        "order": "id",
                        "ascending": "false",
                        "closed": "false",
                        "limit": limit,
                        "offset": offset
                    }
                    
                    response = await client.get(url, params=params)
                    
                    # Check for rate limit errors
                    if response.status_code == 429:
                        await rate_limiter.record_violation(EndpointType.DATA_API)
                        logger.warning("Rate limit exceeded, using partial results")
                        break
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    # Extract events from response
                    # According to API docs, /events returns array directly: [...]
                    # But with pagination params, it might return {"data": [...]}
                    # Handle both cases
                    if isinstance(data, list):
                        events = data
                    else:
                        events = data.get("data", [])
                    
                    if not events:
                        # No more events, pagination complete
                        break
                    
                    # Extract markets from events
                    # Events contain their associated markets in "markets" array
                    for event in events:
                        event_markets = event.get("markets", [])
                        if event_markets:
                            all_markets.extend(event_markets)
                    
                    # Check if we got fewer results than limit (last page)
                    if len(events) < limit:
                        break
                    
                    # Move to next page
                    offset += limit
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        await rate_limiter.record_violation(EndpointType.DATA_API)
                        logger.warning("Rate limit exceeded on page fetch, using partial results")
                        break
                    raise
                except Exception as e:
                    logger.error(f"Error fetching page {page}: {e}")
                    # Continue to next page on error, or break if critical
                    break
            
            logger.info(f"Fetched {len(all_markets)} markets from Gamma API (offset={offset}, pages={page+1})")
            
            # Cache the result
            await api_cache.set(cache_key, all_markets, ttl=cache_ttl)
            return all_markets
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.DATA_API)
                logger.warning("Rate limit exceeded, using cached data if available")
                cached = await api_cache.get(cache_key)
                return cached if cached is not None else []
            logger.error(f"HTTP error fetching markets: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching markets from Polymarket: {e}", exc_info=True)
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
    
    async def _discover_events_directly(self) -> List[Dict[str, Any]]:
        """
        Descubre Events directamente desde /events endpoint.
        
        Según documentación de Polymarket:
        - Usa /events?closed=false&limit=100 para obtener eventos activos
        - Ordena por endDate para encontrar eventos próximos a terminar
        - Los eventos contienen información del Market y Series asociados
        """
        cache_key = "scanner:events_raw"
        cache_ttl_seconds = config_service.get("scanner_events_cache_ttl_seconds", 30)
        cache_ttl = timedelta(seconds=cache_ttl_seconds)
        
        # Check cache first
        cached = await api_cache.get(cache_key)
        if cached is not None:
            logger.debug("Using cached events data")
            return cached
        
        client = await self._get_client()
        all_events = []
        
        try:
            # Obtener parámetros de paginación
            limit = config_service.get("scanner_pagination_limit", 100)
            max_pages = config_service.get("scanner_max_pages", 10)
            offset = 0
            
            for page in range(max_pages):
                # Acquire rate limit permission (GAMMA EVENTS: 100 req / 10s)
                if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_EVENTS, timeout=5.0):
                    logger.warning(f"Rate limit timeout for events page {page}, using cached data if available")
                    break
                
                url = f"{settings.polymarket_gamma_api_url}/events"
                params = {
                    "order": "endDate",  # Ordenar por fecha de finalización
                    "ascending": "true",  # Los que terminan primero
                    "closed": "false",  # Solo eventos activos
                    "limit": limit,
                    "offset": offset
                }
                
                response = await client.get(url, params=params)
                
                if response.status_code == 429:
                    await rate_limiter.record_violation(EndpointType.GAMMA_EVENTS)
                    logger.warning("Rate limit exceeded for events, using cached data if available")
                    break
                
                response.raise_for_status()
                data = response.json()
                
                # Handle both array and object responses
                if isinstance(data, list):
                    events = data
                else:
                    events = data.get("data", [])
                
                if not events:
                    break
                
                all_events.extend(events)
                
                # Check if we got fewer results than limit (last page)
                if len(events) < limit:
                    break
                
                offset += limit
            
            logger.info(f"Discovered {len(all_events)} events from Gamma API")
            
            # Cache the result
            await api_cache.set(cache_key, all_events, ttl=cache_ttl)
            return all_events
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_EVENTS)
                logger.warning("Rate limit exceeded, using cached data if available")
                cached = await api_cache.get(cache_key)
                return cached if cached is not None else []
            logger.error(f"HTTP error fetching events: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching events from Polymarket: {e}", exc_info=True)
            cached = await api_cache.get(cache_key)
            return cached if cached is not None else []
    
    async def _discover_markets_directly(self) -> List[Dict[str, Any]]:
        """
        Descubre Markets directamente desde /markets endpoint.
        
        Según documentación de Polymarket:
        - Usa /markets?closed=false&limit=100 para obtener mercados activos
        """
        cache_key = "scanner:markets_raw"
        cache_ttl_seconds = config_service.get("scanner_markets_cache_ttl_seconds", 60)
        cache_ttl = timedelta(seconds=cache_ttl_seconds)
        
        # Check cache first
        cached = await api_cache.get(cache_key)
        if cached is not None:
            logger.debug("Using cached markets data")
            return cached
        
        client = await self._get_client()
        all_markets = []
        
        try:
            # Obtener parámetros de paginación
            limit = config_service.get("scanner_pagination_limit", 100)
            max_pages = config_service.get("scanner_max_pages", 10)
            offset = 0
            
            for page in range(max_pages):
                # Acquire rate limit permission (GAMMA MARKETS: 125 req / 10s)
                if not await rate_limiter.wait_for_capacity(EndpointType.GAMMA_MARKETS, timeout=5.0):
                    logger.warning(f"Rate limit timeout for markets page {page}, using cached data if available")
                    break
                
                url = f"{settings.polymarket_gamma_api_url}/markets"
                params = {
                    "closed": "false",  # Solo mercados activos
                    "limit": limit,
                    "offset": offset
                }
                
                response = await client.get(url, params=params)
                
                if response.status_code == 429:
                    await rate_limiter.record_violation(EndpointType.GAMMA_MARKETS)
                    logger.warning("Rate limit exceeded for markets, using cached data if available")
                    break
                
                response.raise_for_status()
                data = response.json()
                
                # Handle both array and object responses
                if isinstance(data, list):
                    markets = data
                else:
                    markets = data.get("data", [])
                
                if not markets:
                    break
                
                all_markets.extend(markets)
                
                # Check if we got fewer results than limit (last page)
                if len(markets) < limit:
                    break
                
                offset += limit
            
            logger.info(f"Discovered {len(all_markets)} markets from Gamma API")
            
            # Cache the result
            await api_cache.set(cache_key, all_markets, ttl=cache_ttl)
            return all_markets
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                await rate_limiter.record_violation(EndpointType.GAMMA_MARKETS)
                logger.warning("Rate limit exceeded, using cached data if available")
                cached = await api_cache.get(cache_key)
                return cached if cached is not None else []
            logger.error(f"HTTP error fetching markets: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching markets from Polymarket: {e}", exc_info=True)
            cached = await api_cache.get(cache_key)
            return cached if cached is not None else []
    
    async def _discover_series_markets_events(self, trace_id: str):
        """
        Descubre Series → Markets → Events desde Polymarket API.
        
        Flujo actualizado según documentación:
        1. Descubre Events directamente desde /events (ordenados por endDate)
        2. Extrae Markets de los Events
        3. Extrae Series de los Markets (si está disponible)
        4. Crea/actualiza Series, Markets, Events y Tags en DB
        
        ⚠️ IMPORTANTE: Implementa caching para evitar explosión de requests.
        """
        db = SessionLocal()
        try:
            # 1. Descubrir Events directamente (más eficiente)
            events_list = await self._discover_events_directly()
            logger.info(f"Discovered {len(events_list)} events")
            
            # 2. También descubrir Markets directamente (para Markets sin Events activos)
            markets_list = await self._discover_markets_directly()
            logger.info(f"Discovered {len(markets_list)} markets")
            
            # 3. Descubrir Series (para organización/UX)
            series_list = await self._discover_series()
            logger.info(f"Discovered {len(series_list)} series")
            
            series_created = 0
            series_updated = 0
            markets_created = 0
            markets_updated = 0
            events_created = 0
            events_updated = 0
            tags_created = 0
            
            # Procesar Series primero (para tener referencias disponibles)
            series_map = {}  # polymarket_series_id -> db_series
            for series_data in series_list:
                try:
                    # Obtener o crear Series en DB
                    polymarket_series_id = series_data.get("id") or series_data.get("slug") or str(series_data.get("_id", ""))
                    if not polymarket_series_id:
                        continue
                    
                    db_series = db.query(Series).filter(
                        Series.polymarket_series_id == polymarket_series_id
                    ).first()
                    
                    if not db_series:
                        db_series = Series(
                            id=uuid4(),
                            polymarket_series_id=polymarket_series_id,
                            name=series_data.get("name", ""),
                            slug=series_data.get("slug"),
                            description=series_data.get("description"),
                            series_type=series_data.get("series_type"),  # best-effort
                            recurrence=series_data.get("recurrence"),  # best-effort
                            polymarket_payload=series_data,
                        )
                        db.add(db_series)
                        db.flush()
                        series_created += 1
                    else:
                        # Actualizar si hay cambios
                        db_series.name = series_data.get("name", db_series.name)
                        db_series.slug = series_data.get("slug", db_series.slug)
                        db_series.description = series_data.get("description", db_series.description)
                        db_series.series_type = series_data.get("series_type", db_series.series_type)
                        db_series.recurrence = series_data.get("recurrence", db_series.recurrence)
                        db_series.polymarket_payload = series_data
                        db_series.updated_at = datetime.utcnow()
                        series_updated += 1
                    
                    # 2. Descubrir Markets de esta Series
                    markets_data = await self._discover_markets_from_series(polymarket_series_id)
                    
                    for market_data in markets_data:
                        try:
                            polymarket_market_id = market_data.get("id") or market_data.get("slug") or str(market_data.get("_id", ""))
                            if not polymarket_market_id:
                                continue
                            
                            # Obtener o crear Market en DB
                            db_market = db.query(Market).filter(
                                Market.polymarket_id == polymarket_market_id
                            ).first()
                            
                            if not db_market:
                                db_market = Market(
                                    id=uuid4(),
                                    polymarket_id=polymarket_market_id,
                                    name=market_data.get("question") or market_data.get("name", ""),
                                    category=market_data.get("category"),
                                    enabled=False,  # Por defecto desactivado
                                    series_id=db_series.id,
                                    polymarket_payload=market_data,
                                )
                                db.add(db_market)
                                db.flush()
                                markets_created += 1
                            else:
                                # Actualizar si hay cambios
                                if not db_market.series_id:
                                    db_market.series_id = db_series.id
                                db_market.name = market_data.get("question") or market_data.get("name", db_market.name)
                                db_market.category = market_data.get("category", db_market.category)
                                db_market.polymarket_payload = market_data
                                db_market.updated_at = datetime.utcnow()
                                markets_updated += 1
                            
                            # Procesar Tags del market
                            tags_data = market_data.get("tags", [])
                            for tag_data in tags_data:
                                try:
                                    polymarket_tag_id = tag_data.get("id") or tag_data.get("slug") or str(tag_data.get("_id", ""))
                                    if not polymarket_tag_id:
                                        continue
                                    
                                    # Obtener o crear Tag
                                    db_tag = db.query(Tag).filter(
                                        Tag.polymarket_tag_id == polymarket_tag_id
                                    ).first()
                                    
                                    if not db_tag:
                                        db_tag = Tag(
                                            id=uuid4(),
                                            polymarket_tag_id=polymarket_tag_id,
                                            name=tag_data.get("name", ""),
                                            slug=tag_data.get("slug"),
                                            label=tag_data.get("label"),
                                            polymarket_payload=tag_data,
                                        )
                                        db.add(db_tag)
                                        db.flush()
                                        tags_created += 1
                                    
                                    # Crear relación Market-Tag si no existe
                                    market_tag = db.query(MarketTag).filter(
                                        MarketTag.market_id == db_market.id,
                                        MarketTag.tag_id == db_tag.id
                                    ).first()
                                    
                                    if not market_tag:
                                        market_tag = MarketTag(
                                            id=uuid4(),
                                            market_id=db_market.id,
                                            tag_id=db_tag.id,
                                        )
                                        db.add(market_tag)
                                
                                except Exception as e:
                                    logger.warning(f"Error processing tag for market {polymarket_market_id}: {e}")
                                    continue
                            
                            # 3. Descubrir Events solo si el Market está activo (enabled=true)
                            if db_market.enabled:
                                events_data = await self._discover_events_from_market(polymarket_market_id)
                                
                                for event_data in events_data:
                                    try:
                                        polymarket_event_id = event_data.get("id") or str(event_data.get("_id", ""))
                                        if not polymarket_event_id:
                                            continue
                                        
                                        # Obtener o crear Event en DB
                                        db_event = db.query(Event).filter(
                                            Event.polymarket_event_id == polymarket_event_id
                                        ).first()
                                        
                                        # Parsear start_time y end_time
                                        start_time = None
                                        end_time = None
                                        if event_data.get("startDate") or event_data.get("start_time"):
                                            try:
                                                from dateutil import parser
                                                date_str = event_data.get("startDate") or event_data.get("start_time")
                                                start_time = parser.parse(date_str)
                                            except Exception as e:
                                                logger.warning(f"Error parsing start_time for event {polymarket_event_id}: {e}")
                                                pass
                                        if event_data.get("endDate") or event_data.get("end_time"):
                                            try:
                                                from dateutil import parser
                                                date_str = event_data.get("endDate") or event_data.get("end_time")
                                                end_time = parser.parse(date_str)
                                            except Exception as e:
                                                logger.warning(f"Error parsing end_time for event {polymarket_event_id}: {e}")
                                                pass
                                        
                                        # Determinar state
                                        state = "UPCOMING"
                                        if event_data.get("active"):
                                            state = "ACTIVE"
                                        elif event_data.get("closed") or event_data.get("resolved"):
                                            state = "FINISHED"
                                        
                                        if not db_event:
                                            if not start_time or not end_time:
                                                logger.warning(f"Skipping event {polymarket_event_id} - missing start_time or end_time")
                                                continue
                                            
                                            db_event = Event(
                                                id=uuid4(),
                                                polymarket_event_id=polymarket_event_id,
                                                market_id=db_market.id,
                                                start_time=start_time,
                                                end_time=end_time,
                                                state=state,
                                                polymarket_payload=event_data,
                                            )
                                            db.add(db_event)
                                            events_created += 1
                                        else:
                                            # Actualizar si hay cambios
                                            if start_time:
                                                db_event.start_time = start_time
                                            if end_time:
                                                db_event.end_time = end_time
                                            db_event.state = state
                                            db_event.polymarket_payload = event_data
                                            db_event.updated_at = datetime.utcnow()
                                            events_updated += 1
                                    
                                    except Exception as e:
                                        logger.warning(f"Error processing event for market {polymarket_market_id}: {e}")
                                        continue
                        
                        except Exception as e:
                            logger.warning(f"Error processing market in series {polymarket_series_id}: {e}")
                            continue
                
                except Exception as e:
                    logger.warning(f"Error processing series: {e}")
                    continue
            
            # Procesar Markets directamente (desde /markets endpoint)
            markets_map = {}  # polymarket_market_id -> db_market
            for market_data in markets_list:
                try:
                    polymarket_market_id = market_data.get("id") or market_data.get("slug") or str(market_data.get("_id", ""))
                    if not polymarket_market_id:
                        continue
                    
                    # Obtener series_id del market (si está disponible)
                    series_id_from_market = None
                    market_series_data = market_data.get("series") or market_data.get("seriesId")
                    if market_series_data:
                        if isinstance(market_series_data, dict):
                            series_id_str = market_series_data.get("id") or market_series_data.get("slug")
                        else:
                            series_id_str = str(market_series_data)
                        if series_id_str and series_id_str in series_map:
                            series_id_from_market = series_map[series_id_str].id
                    
                    # Obtener o crear Market en DB
                    db_market = db.query(Market).filter(
                        Market.polymarket_id == polymarket_market_id
                    ).first()
                    
                    if not db_market:
                        db_market = Market(
                            id=uuid4(),
                            polymarket_id=polymarket_market_id,
                            name=market_data.get("question") or market_data.get("name", ""),
                            category=market_data.get("category"),
                            enabled=False,  # Por defecto desactivado
                            series_id=series_id_from_market,
                            polymarket_payload=market_data,
                        )
                        db.add(db_market)
                        db.flush()
                        markets_created += 1
                    else:
                        # Actualizar si hay cambios
                        if not db_market.series_id and series_id_from_market:
                            db_market.series_id = series_id_from_market
                        db_market.name = market_data.get("question") or market_data.get("name", db_market.name)
                        db_market.category = market_data.get("category", db_market.category)
                        db_market.polymarket_payload = market_data
                        db_market.updated_at = datetime.utcnow()
                        markets_updated += 1
                    
                    markets_map[polymarket_market_id] = db_market
                    
                    # Procesar Tags del market
                    tags_data = market_data.get("tags", [])
                    for tag_data in tags_data:
                        try:
                            polymarket_tag_id = tag_data.get("id") or tag_data.get("slug") or str(tag_data.get("_id", ""))
                            if not polymarket_tag_id:
                                continue
                            
                            # Obtener o crear Tag
                            db_tag = db.query(Tag).filter(
                                Tag.polymarket_tag_id == polymarket_tag_id
                            ).first()
                            
                            if not db_tag:
                                db_tag = Tag(
                                    id=uuid4(),
                                    polymarket_tag_id=polymarket_tag_id,
                                    name=tag_data.get("name", ""),
                                    slug=tag_data.get("slug"),
                                    label=tag_data.get("label"),
                                    polymarket_payload=tag_data,
                                )
                                db.add(db_tag)
                                db.flush()
                                tags_created += 1
                            
                            # Crear relación Market-Tag si no existe
                            market_tag = db.query(MarketTag).filter(
                                MarketTag.market_id == db_market.id,
                                MarketTag.tag_id == db_tag.id
                            ).first()
                            
                            if not market_tag:
                                market_tag = MarketTag(
                                    id=uuid4(),
                                    market_id=db_market.id,
                                    tag_id=db_tag.id,
                                )
                                db.add(market_tag)
                        
                        except Exception as e:
                            logger.warning(f"Error processing tag for market {polymarket_market_id}: {e}")
                            continue
                
                except Exception as e:
                    logger.warning(f"Error processing market: {e}")
                    continue
            
            # Procesar Events directamente (desde /events endpoint)
            for event_data in events_list:
                try:
                    polymarket_event_id = event_data.get("id") or str(event_data.get("_id", ""))
                    if not polymarket_event_id:
                        continue
                    
                    # Obtener Market del Event
                    market_id_from_event = None
                    event_market_data = event_data.get("market") or event_data.get("marketId")
                    if event_market_data:
                        if isinstance(event_market_data, dict):
                            market_id_str = event_market_data.get("id") or event_market_data.get("slug")
                        else:
                            market_id_str = str(event_market_data)
                        
                        # Buscar Market en DB o en markets_map
                        if market_id_str in markets_map:
                            db_market = markets_map[market_id_str]
                        else:
                            db_market = db.query(Market).filter(
                                Market.polymarket_id == market_id_str
                            ).first()
                            if db_market:
                                markets_map[market_id_str] = db_market
                        
                        if db_market:
                            market_id_from_event = db_market.id
                        else:
                            logger.warning(f"Event {polymarket_event_id} has no associated market in DB, skipping")
                            continue
                    
                    if not market_id_from_event:
                        logger.warning(f"Event {polymarket_event_id} has no associated market, skipping")
                        continue
                    
                    # Parsear start_time y end_time
                    from dateutil import parser
                    start_time = None
                    end_time = None
                    
                    # Intentar diferentes formatos de fecha
                    start_date_str = event_data.get("startDate") or event_data.get("start_time") or event_data.get("startDateIso")
                    if start_date_str:
                        try:
                            start_time = parser.parse(start_date_str.replace('Z', '+00:00') if 'Z' in start_date_str else start_date_str)
                        except Exception as e:
                            logger.warning(f"Error parsing start_time for event {polymarket_event_id}: {e}")
                    
                    end_date_str = event_data.get("endDate") or event_data.get("end_time") or event_data.get("endDateIso")
                    if end_date_str:
                        try:
                            end_time = parser.parse(end_date_str.replace('Z', '+00:00') if 'Z' in end_date_str else end_date_str)
                        except Exception as e:
                            logger.warning(f"Error parsing end_time for event {polymarket_event_id}: {e}")
                    
                    if not start_time or not end_time:
                        logger.warning(f"Skipping event {polymarket_event_id} - missing start_time or end_time")
                        continue
                    
                    # Determinar state
                    state = "UPCOMING"
                    if event_data.get("active") or event_data.get("isActive"):
                        state = "ACTIVE"
                    elif event_data.get("closed") or event_data.get("resolved") or event_data.get("isClosed"):
                        state = "FINISHED"
                    
                    # Obtener o crear Event en DB
                    db_event = db.query(Event).filter(
                        Event.polymarket_event_id == polymarket_event_id
                    ).first()
                    
                    if not db_event:
                        db_event = Event(
                            id=uuid4(),
                            polymarket_event_id=polymarket_event_id,
                            market_id=market_id_from_event,
                            start_time=start_time,
                            end_time=end_time,
                            state=state,
                            polymarket_payload=event_data,
                        )
                        db.add(db_event)
                        events_created += 1
                    else:
                        # Actualizar si hay cambios
                        db_event.start_time = start_time
                        db_event.end_time = end_time
                        db_event.state = state
                        db_event.polymarket_payload = event_data
                        db_event.updated_at = datetime.utcnow()
                        events_updated += 1
                
                except Exception as e:
                    logger.warning(f"Error processing event: {e}", exc_info=True)
                    continue
            
            db.commit()
            
            logger.info(
                f"Discovery complete: "
                f"Series: {series_created} created, {series_updated} updated | "
                f"Markets: {markets_created} created, {markets_updated} updated | "
                f"Events: {events_created} created, {events_updated} updated | "
                f"Tags: {tags_created} created"
            )
            
            # Emitir métricas
            await metrics_service.collector.record_event(
                "scanner_discovery_completed",
                {
                    "series_created": series_created,
                    "series_updated": series_updated,
                    "markets_created": markets_created,
                    "markets_updated": markets_updated,
                    "events_created": events_created,
                    "events_updated": events_updated,
                    "tags_created": tags_created,
                    "trace_id": trace_id,
                },
                component="scanner"
            )
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error in series/markets/events discovery: {e}", exc_info=True)
            raise
        finally:
            db.close()
    
    async def tick(self):
        """
        Scan markets periodically.
        
        Updates state.markets and persists to DB.
        Emite métricas del proceso de escaneo.
        
        Ahora usa el nuevo flujo Series → Markets → Events.
        """
        # Generar trace_id para este scan
        trace_id = str(uuid4())
        
        # Check if enough time has passed since last scan (desde ConfigService)
        scanner_config = config_service.get_scanner_config()
        scan_interval = scanner_config["scan_interval_seconds"]
        
        if self._last_scan:
            time_since_scan = (datetime.utcnow() - self._last_scan).total_seconds()
            if time_since_scan < scan_interval:
                logger.debug(
                    "Scanner skip: %.1fs since last scan < %.1fs interval",
                    time_since_scan,
                    scan_interval,
                )
                return  # Too soon to scan again
        
        logger.info("Scanner running (interval=%.0fs, last_scan=%s)", scan_interval, self._last_scan)
        scan_start = datetime.utcnow()
        
        try:
            # Usar nuevo flujo Series → Markets → Events
            await self._discover_series_markets_events(trace_id)
            
            self._last_scan = datetime.utcnow()
            self._scan_count += 1
            
            # Calcular latencia del scan
            scan_duration_ms = (datetime.utcnow() - scan_start).total_seconds() * 1000
            await metrics_service.collector.store.store_metric(
                "scanner_latency_ms",
                scan_duration_ms,
                component="scanner"
            )
            
        except Exception as e:
            logger.error(f"Critical error in scanner tick: {e}", exc_info=True)
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

