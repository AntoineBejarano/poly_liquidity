/**
 * Tipos normalizados para Discovery (Gamma-first).
 * Estructura UI unificada independiente del formato raw de la API.
 */

export interface DiscoveryTag {
  tag_id: string;
  name: string;
  slug?: string | null;
}

export interface DiscoveryMarket {
  market_id: string;
  polymarket_id: string;
  name: string;
  enabled: boolean;
  series_id: string | null;
  series_name: string | null;
  event_id: string | null;
  event_title: string | null;
  tags: Array<{ tag_id: string; name: string }>;
  clob_token_ids?: {
    primary?: string | null;
    primary_yes?: string | null;
    primary_no?: string | null;
    selection_hint?: string;
  };
  spread?: number | null;
  bestBid?: number | null;
  bestAsk?: number | null;
}

export interface DiscoveryEvent {
  event_id: string;
  polymarket_event_id: string;
  title: string;
  slug?: string | null;
  markets_count: number;
  markets?: DiscoveryMarket[];
  liquidity_usd?: number;
}

export interface DiscoverySeries {
  series_id: string;
  polymarket_series_id: string;
  name: string;
  slug?: string | null;
  markets_count: number;
  events_count?: number;
}

export interface MarketsPaginationMeta {
  hasMore: boolean;
  offset: number;
  limit: number;
  partialPage?: boolean;
  partialReason?: string;
}

export type DiscoveryView = 'markets' | 'events' | 'series';

export type AddScope = 'market' | 'event' | 'series';

/** Tradeable market from /api/polymarket/discovery (market-first, flat list) */
export interface DiscoveryTradeableMarket {
  market_id: string;
  polymarket_id: string;
  question: string;
  clob_token_ids: {
    primary_yes?: string | null;
    primary_no?: string | null;
    primary?: string | null;
  };
  active: boolean;
  acceptingOrders: boolean;
  archived: boolean;
  closed: boolean;
  liquidity?: number;
  volume24hr?: number;
  /** Total (all-time) volume for filtering/sorting */
  volume?: number;
  event_id: string;
  event_title: string;
  event_end_date?: string | null;
  event_archived?: boolean;
  event_tags: Array<{ slug: string; label: string }>;
  series_slug?: string | null;
  time_to_resolution_minutes?: number | null;
  /** Outcomes para UI (ej. Moneyline: [ ABE ] [ DRAW ] [ DFC ]) */
  outcomes?: string | string[] | null;
  short_outcomes?: string | string[] | null;
  /** Precios por outcome: string "0.92,0.08" o array [0.92, 0.08] — probabilidad 0–1 (o % 0–100) por posición */
  outcome_prices?: string | number[] | null;
  sports_market_type?: string | null;
  market_group?: number | null;
  /** Derivado: abierto + acepta órdenes (se puede operar). Para filtro discovery. */
  tradeable?: boolean;
}

export interface FetchDiscoveryParams {
  tag_slug: string;
  closed?: boolean;
  limit?: number;
  offset?: number;
  end_date_max?: string | null;
  live?: boolean;
  league?: string | null;
}

export interface FetchDiscoveryResult {
  markets: DiscoveryTradeableMarket[];
  count: number;
}

/** Event-first discovery: evento con mercados anidados (modelo Event → Markets → Outcomes). */
export interface DiscoveryEventWithMarkets {
  event_id: string;
  title: string;
  subtitle: string;
  end_date?: string | null;
  start_date?: string | null;
  markets: DiscoveryTradeableMarket[];
  markets_count: number;
}

export interface FetchDiscoveryEventsResult {
  events: DiscoveryEventWithMarkets[];
  count: number;
}

// --- Discovery Screener (métricas diferenciales: edge, slippage, fillability) ---

export interface BestOpportunity {
  marketId?: string | null;
  outcome?: string | null;
  edge_cents?: number | null;
  slippage_1k_cents?: number | null;
  fillability_score?: number | null;
  liquidity_usd?: number | null;
  freshness_ms?: number | null;
}

/** Market con métricas de screener (orderbook enrichment). */
export interface DiscoveryScreenerMarket extends DiscoveryTradeableMarket {
  best_bid?: number | null;
  best_ask?: number | null;
  mid_price?: number | null;
  fair_price?: number | null;
  edge_cents?: number | null;
  spread_bps?: number | null;
  depth_50bps_usd?: number | null;
  slippage_1k_cents?: number | null;
  fillability_score?: number | null;
  stale_ms?: number | null;
  liquidity_usd?: number | null;
  tradeable_reasons?: string[];
  /** Rolling volatility (std of log returns): 5m window */
  vol_5m?: number | null;
  /** Rolling volatility: 15m window */
  vol_15m?: number | null;
  vol_source?: 'MID' | 'LAST_TRADE' | null;
  vol_samples_5m?: number | null;
  vol_samples_15m?: number | null;
  vol_last_updated_at?: number | null;
}

/** Métricas de volatilidad a nivel evento (agregadas de mercados). */
export interface DiscoveryEventVolatilityMetrics {
  max_vol_5m?: number | null;
  max_vol_15m?: number | null;
  hot_markets_count_5m?: number | null;
  volatility_label?: 'NON_VOLATILE' | 'VOLATILE' | 'CHAOTIC' | 'UNKNOWN' | null;
  volatility_label_reason?: string | null;
}

/** Evento con best opportunity y event_score para ranking. */
export interface DiscoveryScreenerEvent {
  event_id: string;
  title: string;
  subtitle?: string | null;
  end_date?: string | null;
  start_date?: string | null;
  markets: DiscoveryScreenerMarket[];
  markets_count: number;
  best_opportunity?: BestOpportunity | null;
  event_score?: number | null;
  /** Métricas de volatilidad agregadas y etiqueta 3 estados. */
  metrics?: DiscoveryEventVolatilityMetrics | null;
}

export interface FetchScreenerParams {
  tag_slug: string;
  closed?: boolean;
  limit?: number;
  offset?: number;
  tradeable_only?: boolean;
  min_edge_cents?: number | null;
  max_slippage_1k?: number | null;
  min_fillability?: number | null;
  min_liquidity?: number | null;
  sort?: 'event_score' | 'edge' | 'liquidity' | 'slippage' | 'freshness';
  end_date_max?: string | null;
  /** Sports live: only events in play window (start - 15m, end + tolerance). */
  live?: boolean;
  /** League slug for live tolerances (nfl, nba, etc.). */
  league?: string | null;
}

export interface FetchScreenerResult {
  events: DiscoveryScreenerEvent[];
  count: number;
}
