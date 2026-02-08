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
  event_id: string;
  event_title: string;
  event_end_date?: string | null;
  event_archived?: boolean;
  event_tags: Array<{ slug: string; label: string }>;
  series_slug?: string | null;
  time_to_resolution_minutes?: number | null;
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
