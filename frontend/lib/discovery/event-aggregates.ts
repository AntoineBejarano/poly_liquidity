/**
 * Agregados por evento para filtros y ordenación (sin depender del componente card).
 */
import type { DiscoveryScreenerEvent, DiscoveryScreenerMarket } from '@/lib/discovery/types';

export interface EventAggregates {
  vol24: number;
  volTotal: number;
  liq: number;
  bestEdgeCents: number | null;
  hasPositiveEdge: boolean;
  minSpreadBps: number | null;
  minSlippage1k: number | null;
  depth50: number | null;
  nMarkets: number;
  nTradeable: number;
  worstFillability: number | null;
  bestMarket: string | null;
  eventScore: number | null;
  freshnessMs: number | null;
  /** Tiempo hasta resolución en minutos (mínimo de markets o desde end_date). Null si no se puede calcular. */
  ttrMinutes: number | null;
}

/** Formatea minutos restantes a texto exacto: "45m", "1h 23m", "2d 5h". */
export function formatTtrMinutes(min: number): string {
  if (min < 0) return 'Terminado';
  if (min < 1) return '< 1m';
  if (min < 60) return `${Math.round(min)}m`;
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  if (h < 24) return m > 0 ? `${h}h ${m}m` : `${h}h`;
  const d = Math.floor(h / 24);
  const hRest = h % 24;
  if (hRest > 0) return `${d}d ${hRest}h`;
  return `${d}d`;
}

export function getEventAggregates(ev: DiscoveryScreenerEvent): EventAggregates {
  const markets = ev.markets || [];
  const vol24 = markets.reduce((s, m) => s + (m.volume24hr ?? 0), 0);
  const volTotal = markets.reduce((s, m) => s + (m.volume ?? 0), 0);
  const liq = markets.reduce(
    (s, m) => s + (Number(m.liquidity) || Number((m as DiscoveryScreenerMarket).liquidity_usd) || 0),
    0
  );
  const bestEdgeCents = markets.reduce<number | null>((best, m) => {
    const e = m.edge_cents;
    if (e == null) return best;
    if (best == null) return e;
    return e > best ? e : best;
  }, null);
  const hasPositiveEdge = markets.some((m) => (m.edge_cents ?? 0) > 0);
  const minSpreadBps = markets.reduce<number | null>((min, m) => {
    const s = m.spread_bps;
    if (s == null) return min;
    if (min == null) return s;
    return s < min ? s : min;
  }, null);
  const minSlippage1k =
    markets.reduce<number | null>((min, m) => {
      const s = m.slippage_1k_cents;
      if (s == null) return min;
      if (min == null) return s;
      return s < min ? s : min;
    }, null) ?? ev.best_opportunity?.slippage_1k_cents ?? null;
  const depth50 = markets.reduce<number | null>((best, m) => {
    const d = m.depth_50bps_usd;
    if (d == null) return best;
    if (best == null) return d;
    return d > best ? d : best;
  }, null);
  const nTradeable = markets.filter((m) => m.fillability_score != null || m.edge_cents != null).length;
  const worstFillability = markets.reduce<number | null>((worst, m) => {
    const f = m.fillability_score;
    if (f == null) return worst;
    if (worst == null) return f;
    return f < worst ? f : worst;
  }, ev.best_opportunity?.fillability_score ?? null);
  const bestMarket = (() => {
    const withEdge = markets.filter((m) => m.edge_cents != null);
    if (withEdge.length === 0) return null;
    const top = withEdge.reduce((a, b) => ((a.edge_cents ?? 0) >= (b.edge_cents ?? 0) ? a : b));
    return top.question || top.market_id;
  })();

  let ttrMinutes: number | null = null;
  const fromMarkets = markets
    .map((m) => m.time_to_resolution_minutes)
    .filter((t): t is number => t != null && t >= 0);
  if (fromMarkets.length > 0) {
    ttrMinutes = Math.min(...fromMarkets);
  } else if (ev.end_date) {
    const endMs = new Date(ev.end_date).getTime();
    const nowMs = Date.now();
    ttrMinutes = (endMs - nowMs) / (60 * 1000);
    if (ttrMinutes < 0) ttrMinutes = 0;
  }

  return {
    vol24,
    volTotal,
    liq,
    bestEdgeCents,
    hasPositiveEdge,
    minSpreadBps,
    minSlippage1k,
    depth50,
    nMarkets: markets.length,
    nTradeable,
    worstFillability,
    bestMarket,
    eventScore: ev.event_score ?? null,
    freshnessMs: ev.best_opportunity?.freshness_ms ?? null,
    ttrMinutes,
  };
}

export type DiscoverySortKey =
  | 'event_score'
  | 'edge'
  | 'liquidity'
  | 'slippage'
  | 'freshness'
  | 'volume24'
  | 'volumeTotal'
  | 'ends';

export function sortEventsBy(
  events: DiscoveryScreenerEvent[],
  sortBy: DiscoverySortKey
): DiscoveryScreenerEvent[] {
  const arr = [...events];
  const getAgg = (ev: DiscoveryScreenerEvent) => getEventAggregates(ev);
  arr.sort((a, b) => {
    const agA = getAgg(a);
    const agB = getAgg(b);
    switch (sortBy) {
      case 'event_score':
        return (agB.eventScore ?? -Infinity) - (agA.eventScore ?? -Infinity);
      case 'edge':
        return (agB.bestEdgeCents ?? -Infinity) - (agA.bestEdgeCents ?? -Infinity);
      case 'liquidity':
        return agB.liq - agA.liq;
      case 'slippage': {
        const sa = agA.minSlippage1k ?? Infinity;
        const sb = agB.minSlippage1k ?? Infinity;
        return sa - sb;
      }
      case 'freshness': {
        const fa = agA.freshnessMs ?? Infinity;
        const fb = agB.freshnessMs ?? Infinity;
        return fa - fb;
      }
      case 'volume24':
        return agB.vol24 - agA.vol24;
      case 'volumeTotal':
        return agB.volTotal - agA.volTotal;
      case 'ends': {
        const ta = getAgg(a).ttrMinutes;
        const tb = getAgg(b).ttrMinutes;
        const va = ta != null && ta >= 0 ? ta : Infinity;
        const vb = tb != null && tb >= 0 ? tb : Infinity;
        return va - vb;
      }
      default:
        return 0;
    }
  });
  return arr;
}

/** Filtro por etiqueta de volatilidad del evento (NON_VOLATILE, VOLATILE, CHAOTIC). */
export type VolatilityFilter = 'any' | 'NON_VOLATILE' | 'VOLATILE' | 'CHAOTIC';
/** Filtro por facilidad de ejecución (peor fillability del evento: GOOD ≥80, OK 60-79, HARD <60). */
export type ExecutionFilter = 'any' | 'GOOD' | 'OK' | 'HARD';

/** Límite TTR en minutos: solo eventos que resuelven en ≤ X min. */
export type TtrFilterMinutes = number | null; // null = cualquiera

export interface DiscoveryFiltersState {
  tradeableOnly: boolean;
  minEdgeCents: number | null;
  minVol24: number | null;
  maxSpreadBps: number | null;
  volatilityLabel: VolatilityFilter;
  executionLabel: ExecutionFilter;
  /** Solo eventos que resuelven en ≤ este número de minutos. null = sin filtro. */
  ttrMaxMinutes: TtrFilterMinutes;
}

function executionCategory(worstFillability: number | null): ExecutionFilter {
  if (worstFillability == null) return 'HARD';
  if (worstFillability >= 80) return 'GOOD';
  if (worstFillability >= 60) return 'OK';
  return 'HARD';
}

export function filterEventsBy(
  events: DiscoveryScreenerEvent[],
  filters: DiscoveryFiltersState,
  tradeableFilter: 'yes' | 'all'
): DiscoveryScreenerEvent[] {
  let out = events;
  if (tradeableFilter === 'yes') {
    out = out
      .filter((ev) => ev.markets.some((m) => m.tradeable !== false))
      .map((ev) => ({
        ...ev,
        markets: ev.markets.filter((m) => m.tradeable !== false),
        markets_count: ev.markets.filter((m) => m.tradeable !== false).length,
      }));
  }
  if (filters.minEdgeCents != null && filters.minEdgeCents > 0) {
    out = out.filter((ev) => {
      const agg = getEventAggregates(ev);
      return agg.bestEdgeCents != null && agg.bestEdgeCents >= filters.minEdgeCents!;
    });
  }
  if (filters.minVol24 != null && filters.minVol24 > 0) {
    out = out.filter((ev) => getEventAggregates(ev).vol24 >= filters.minVol24!);
  }
  if (filters.maxSpreadBps != null) {
    out = out.filter((ev) => {
      const agg = getEventAggregates(ev);
      return agg.minSpreadBps == null || agg.minSpreadBps <= filters.maxSpreadBps!;
    });
  }
  if (filters.volatilityLabel && filters.volatilityLabel !== 'any') {
    out = out.filter((ev) => ev.metrics?.volatility_label === filters.volatilityLabel);
  }
  if (filters.executionLabel && filters.executionLabel !== 'any') {
    out = out.filter((ev) => {
      const agg = getEventAggregates(ev);
      return executionCategory(agg.worstFillability) === filters.executionLabel;
    });
  }
  if (filters.ttrMaxMinutes != null && filters.ttrMaxMinutes > 0) {
    out = out.filter((ev) => {
      const agg = getEventAggregates(ev);
      return agg.ttrMinutes != null && agg.ttrMinutes >= 0 && agg.ttrMinutes <= filters.ttrMaxMinutes!;
    });
  }
  return out;
}
