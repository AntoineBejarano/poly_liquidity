/**
 * Cliente de Discovery (Gamma-first, público, sin wallet).
 * Usa backend proxy para tags, series, events, markets.
 */

import { initApiClient } from '@/lib/api';
import type { DiscoveryMarket, DiscoveryEvent, DiscoverySeries, DiscoveryTag, MarketsPaginationMeta, DiscoveryTradeableMarket, FetchDiscoveryParams, FetchDiscoveryResult } from './types';
import { transformMarket, transformEvent, transformSeries, transformTag, filterNonEmptyEvents, filterNonEmptySeries } from './transform';

export interface FetchMarketsParams {
  limit?: number;
  offset?: number;
  order?: string;
  ascending?: boolean;
  closed?: string;
  tag_id?: string;
  series_id?: string;
  search?: string;
  enabled?: boolean;
}

export interface FetchMarketsResult {
  markets: DiscoveryMarket[];
  pagination: MarketsPaginationMeta;
}

export interface FetchEventsParams {
  limit?: number;
  offset?: number;
  closed?: boolean;
}

export interface FetchEventsResult {
  events: DiscoveryEvent[];
}

const DEFAULT_LIMIT = 25;
const SEARCH_DEBOUNCE_MS = 500;

export class DiscoveryClient {
  private getToken: () => string | null | Promise<string | null>;
  private baseUrl: string;

  constructor(getToken: () => string | null | Promise<string | null>) {
    this.getToken = getToken;
    this.baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';
    if (!this.baseUrl.startsWith('http')) this.baseUrl = `https://${this.baseUrl}`;
  }

  private async fetchJson<T>(
    path: string,
    params?: Record<string, string | number | boolean>,
    signal?: AbortSignal
  ): Promise<T> {
    const tokenResult = this.getToken();
    const token = tokenResult instanceof Promise ? await tokenResult : tokenResult;
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    const res = await fetch(`${this.baseUrl}${path}${qs}`, { headers, signal });
    if (!res.ok) throw new Error(`Discovery fetch failed: ${res.status}`);
    return res.json();
  }

  async fetchMarkets(params: FetchMarketsParams = {}, signal?: AbortSignal): Promise<FetchMarketsResult> {
    const p: Record<string, string> = {
      limit: String(params.limit ?? DEFAULT_LIMIT),
      offset: String(params.offset ?? 0),
      order: params.order ?? 'createdAt',
      ascending: String(params.ascending ?? false),
      closed: params.closed ?? 'false',
    };
    if (params.tag_id) p.tag_id = params.tag_id;
    if (params.series_id) p.series_id = params.series_id;
    if (params.search?.trim()) p.search = params.search.trim();
    if (params.enabled !== undefined) p.enabled = String(params.enabled);

    const api = initApiClient(this.getToken);
    const { data: raw, headers } = await api.getWithHeaders<DiscoveryMarket[] | { items?: DiscoveryMarket[] }>('/markets', {
      params: p,
      signal,
    });
    const list: DiscoveryMarket[] = Array.isArray(raw)
      ? raw.map(transformMarket)
      : (raw?.items ?? []).map(transformMarket);

    const hasMore = (headers.get('X-Has-More') ?? '').toLowerCase() === 'true';
    const respOffset = parseInt(headers.get('X-Offset') ?? String(params.offset ?? 0), 10);
    const respLimit = parseInt(headers.get('X-Limit') ?? String(params.limit ?? DEFAULT_LIMIT), 10);

    return {
      markets: list,
      pagination: {
        hasMore,
        offset: respOffset,
        limit: respLimit,
      },
    };
  }

  async fetchTags(signal?: AbortSignal): Promise<DiscoveryTag[]> {
    const raw = await this.fetchJson<{ items?: unknown[] } | unknown[]>(
      '/api/polymarket/tags',
      { limit: 200, offset: 0 },
      signal
    );
    const items = Array.isArray(raw) ? raw : (raw?.items ?? []);
    return items.map((t) => transformTag(t as never));
  }

  async fetchSeries(signal?: AbortSignal): Promise<DiscoverySeries[]> {
    const raw = await this.fetchJson<unknown[]>('/series', undefined, signal);
    const list = Array.isArray(raw) ? raw : [];
    const series = list.map((s) => transformSeries(s as never));
    return filterNonEmptySeries(series);
  }

  async fetchDiscovery(params: FetchDiscoveryParams, signal?: AbortSignal): Promise<FetchDiscoveryResult> {
    const p: Record<string, string | number | boolean> = {
      tag_slug: params.tag_slug,
      closed: params.closed ?? false,
      limit: params.limit ?? 100,
      offset: params.offset ?? 0,
      live: params.live ?? false,
    };
    if (params.end_date_max) p.end_date_max = params.end_date_max;
    if (params.league) p.league = params.league;
    const raw = await this.fetchJson<{ markets: unknown[]; count: number }>(
      '/api/polymarket/discovery',
      p,
      signal
    );
    return {
      markets: (raw?.markets ?? []) as DiscoveryTradeableMarket[],
      count: raw?.count ?? 0,
    };
  }

  async fetchEvents(params: FetchEventsParams = {}, signal?: AbortSignal): Promise<DiscoveryEvent[]> {
    const p: Record<string, string> = {
      limit: String(params.limit ?? 50),
      offset: String(params.offset ?? 0),
      closed: String(params.closed ?? false),
    };
    const raw = await this.fetchJson<unknown[]>(
      '/api/polymarket/events',
      p,
      signal
    );
    const list = Array.isArray(raw) ? raw : [];
    const events = list.map((e) => transformEvent(e as never));
    return filterNonEmptyEvents(events);
  }
}
