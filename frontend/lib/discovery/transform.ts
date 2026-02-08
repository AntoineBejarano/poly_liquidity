/**
 * Transforma respuestas raw de Gamma/backend a modelos UI normalizados.
 */

import type { DiscoveryMarket, DiscoveryEvent, DiscoverySeries, DiscoveryTag } from './types';

/** Raw Gamma event (desde GET /api/polymarket/events) */
interface RawGammaEvent {
  id?: string;
  _id?: string;
  title?: string;
  slug?: string;
  markets?: Array<{
    id?: string;
    question?: string;
    clobTokenIds?: unknown;
    outcomePrices?: string;
  }>;
  [key: string]: unknown;
}

/** Raw backend market (desde GET /markets) */
interface RawBackendMarket {
  market_id?: string;
  polymarket_id?: string;
  name?: string;
  question?: string;
  enabled?: boolean;
  series_id?: string | null;
  series_name?: string | null;
  tags?: Array<{ tag_id: string; name: string }>;
  clob_token_ids?: Record<string, unknown>;
  spread?: number | null;
  bestBid?: number | null;
  bestAsk?: number | null;
  [key: string]: unknown;
}

/** Raw Gamma series (desde GET /series) */
interface RawSeries {
  series_id?: string;
  id?: string;
  name?: string;
  slug?: string;
  markets_count?: number;
  [key: string]: unknown;
}

/** Raw Gamma tag (desde GET /api/polymarket/tags) */
interface RawTag {
  tag_id?: string;
  id?: string;
  slug?: string;
  name?: string;
  label?: string;
  [key: string]: unknown;
}

export function transformMarket(raw: RawBackendMarket): DiscoveryMarket {
  const id = raw.polymarket_id ?? raw.market_id ?? '';
  return {
    market_id: id,
    polymarket_id: id,
    name: raw.name ?? raw.question ?? id,
    enabled: raw.enabled ?? false,
    series_id: raw.series_id ?? null,
    series_name: raw.series_name ?? null,
    event_id: (raw as { event_id?: string }).event_id ?? null,
    event_title: (raw as { event_title?: string }).event_title ?? null,
    tags: raw.tags ?? [],
    clob_token_ids: raw.clob_token_ids as DiscoveryMarket['clob_token_ids'],
    spread: raw.spread ?? null,
    bestBid: raw.bestBid ?? null,
    bestAsk: raw.bestAsk ?? null,
  };
}

export function transformEvent(raw: RawGammaEvent): DiscoveryEvent {
  const id = String(raw.id ?? raw._id ?? '');
  const markets = raw.markets ?? [];
  const marketCount = Array.isArray(markets) ? markets.length : 0;
  const marketsNorm: DiscoveryMarket[] = (markets as RawBackendMarket[]).map((m) =>
    transformMarket({
      market_id: m.id ?? m.market_id,
      polymarket_id: m.id ?? m.polymarket_id,
      name: m.question ?? m.name,
      enabled: true,
      series_id: null,
      series_name: null,
      tags: m.tags ?? [],
      clob_token_ids: m.clob_token_ids,
    })
  );
  return {
    event_id: id,
    polymarket_event_id: id,
    title: raw.title ?? id,
    slug: raw.slug ?? null,
    markets_count: marketCount,
    markets: marketCount > 0 ? marketsNorm : undefined,
  };
}

export function transformSeries(raw: RawSeries): DiscoverySeries {
  const id = raw.series_id ?? raw.id ?? '';
  return {
    series_id: id,
    polymarket_series_id: id,
    name: raw.name ?? id,
    slug: raw.slug ?? null,
    markets_count: raw.markets_count ?? 0,
    events_count: (raw as { events_count?: number }).events_count,
  };
}

export function transformTag(raw: RawTag): DiscoveryTag {
  const id = String(raw.tag_id ?? raw.id ?? raw.slug ?? '');
  return {
    tag_id: id,
    name: raw.name ?? raw.label ?? id,
    slug: raw.slug ?? null,
  };
}

/** Filtra eventos sin markets. No mostrar entidades vacías. */
export function filterNonEmptyEvents(events: DiscoveryEvent[]): DiscoveryEvent[] {
  return events.filter((e) => e.markets_count > 0);
}

/** Filtra series sin markets. No mostrar entidades vacías. */
export function filterNonEmptySeries(series: DiscoverySeries[]): DiscoverySeries[] {
  return series.filter((s) => (s.markets_count ?? 0) > 0);
}
