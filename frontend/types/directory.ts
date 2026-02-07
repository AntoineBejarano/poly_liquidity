/**
 * Tipos para Directory (Phase 1) y Universe (Phase 2).
 * Alineado con backend: directory.py y strategies.py (UniverseConfig).
 */

export interface DirectoryMeta {
  last_scanned_at: string | null;
  freshness: 'fresh' | 'stale';
  source: string;
  data_age_seconds?: number | null;
}

export interface DirectoryCategory {
  category: string;
}

export interface DirectoryTag {
  tag_id: string;
  polymarket_tag_id: string | null;
  name: string;
  slug: string | null;
  label: string | null;
}

export interface DirectoryMarket {
  market_id: string;
  polymarket_id: string;
  name: string;
  category: string | null;
  enabled: boolean;
  series_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface DirectoryEvent {
  event_id: string;
  polymarket_event_id: string | null;
  market_id: string;
  market_name: string | null;
  start_time: string | null;
  end_time: string | null;
  state: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface DirectoryCategoriesResponse {
  items: DirectoryCategory[];
  total: number;
  _meta: DirectoryMeta;
}

export interface DirectoryTagsResponse {
  items: DirectoryTag[];
  total: number;
  limit: number;
  offset: number;
  _meta: DirectoryMeta;
}

export interface DirectoryMarketsResponse {
  items: DirectoryMarket[];
  total: number;
  limit: number;
  offset: number;
  _meta: DirectoryMeta;
}

export interface DirectoryEventsResponse {
  items: DirectoryEvent[];
  total: number;
  limit: number;
  offset: number;
  _meta: DirectoryMeta;
}

/** Filtro temporal (Phase 2). */
export interface TimeFilterConfig {
  window?: 'UPCOMING' | 'ACTIVE' | 'ANY' | null;
  next_days?: number | null;
  max_time_to_resolution_minutes?: number | null;
}

/** Configuración del universo de una estrategia. */
export interface UniverseConfig {
  categories?: string[];
  markets?: string[];
  tags?: string[];
  events?: string[];
  time_filter?: TimeFilterConfig | null;
  auto_attach?: boolean;
  deny_list?: string[];
  /** Phase 4: límites y dry-run */
  max_events_per_strategy?: number | null;
  max_auto_attaches_per_hour?: number | null;
  auto_attach_dry_run?: boolean;
}

/** Ítem del Universe Builder (series, event, market). */
export interface UniverseItem {
  id: string;
  type: 'series' | 'event' | 'market';
  ref_id: string;
  include_future?: boolean;
}

export interface UniverseResponse {
  strategy_id: string;
  universe: UniverseConfig & {
    categories: string[];
    markets: string[];
    tags: string[];
    events: string[];
    items?: UniverseItem[];
    series_refs?: Array<{ ref_id: string; include_future?: boolean }>;
    time_filter: TimeFilterConfig | null;
    auto_attach: boolean;
    deny_list: string[];
  };
}
