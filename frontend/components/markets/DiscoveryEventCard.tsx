'use client';

import type { DiscoveryScreenerEvent, DiscoveryScreenerMarket } from '@/lib/discovery/types';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { ChevronDown, ChevronRight } from 'lucide-react';

function formatUsdShort(value: number | string | null | undefined): string {
  const n = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(n) || n <= 0) return '—';
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function formatEndDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { month: 'numeric', day: 'numeric', year: 'numeric' });
  } catch {
    return '—';
  }
}

function formatEventTimestamp(ev: DiscoveryScreenerEvent): string {
  if (ev.end_date) {
    try {
      const d = new Date(ev.end_date);
      return d.toLocaleDateString(undefined, { month: 'numeric', day: 'numeric', year: 'numeric' });
    } catch {
      return '—';
    }
  }
  if (ev.start_date) {
    try {
      const d = new Date(ev.start_date);
      return d.toLocaleDateString(undefined, { month: 'numeric', day: 'numeric' });
    } catch {
      return '—';
    }
  }
  return '';
}

/** Urgency from TTR (min) or end_date. <15m = amber, else gray */
function getUrgency(ev: DiscoveryScreenerEvent): { label: string; urgent: boolean } | null {
  const markets = ev.markets || [];
  let ttrMin: number | null = null;
  for (const m of markets) {
    const t = m.time_to_resolution_minutes;
    if (t != null && t >= 0 && (ttrMin == null || t < ttrMin)) ttrMin = t;
  }
  if (ttrMin != null) {
    if (ttrMin < 15) return { label: `⏱ ${Math.round(ttrMin)}m`, urgent: true };
    if (ttrMin < 60) return { label: `⏱ ${Math.round(ttrMin)}m`, urgent: false };
    return { label: '1h+', urgent: false };
  }
  if (ev.end_date) {
    const end = new Date(ev.end_date).getTime();
    const now = Date.now();
    const minLeft = (end - now) / (60 * 1000);
    if (minLeft < 15 && minLeft > 0) return { label: 'Ends < 15m', urgent: true };
  }
  return null;
}

/** Tradeability: GOOD / OK / HARD / ILLQ (semantic colors) */
function TradeabilityPill({ score, liquidity }: { score: number | null | undefined; liquidity: number | null | undefined }) {
  const illq = (score == null && (liquidity == null || liquidity < 500)) || liquidity == null;
  if (illq) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="rounded-full bg-[#374151]/80 text-[#9CA3AF] px-2.5 py-0.5 text-xs font-medium tracking-wide">
            ILLQ
          </span>
        </TooltipTrigger>
        <TooltipContent><p>Illiquid or no execution data</p></TooltipContent>
      </Tooltip>
    );
  }
  if (score == null) return null;
  const label = score >= 80 ? 'GOOD' : score >= 60 ? 'OK' : 'HARD';
  const style =
    score >= 80
      ? 'bg-[#22C55E]/15 text-[#22C55E]'
      : score >= 60
        ? 'bg-[#EAB308]/15 text-[#EAB308]'
        : 'bg-[#EF4444]/15 text-[#EF4444]';
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium tracking-wide ${style}`}>
          {label}
        </span>
      </TooltipTrigger>
      <TooltipContent><p>Execution quality (spread, depth, freshness)</p></TooltipContent>
    </Tooltip>
  );
}

/** Aggregates for collapsed card: best edge, min spread, min slippage, depth, vols, counts, best market name */
function getEventAggregates(ev: DiscoveryScreenerEvent) {
  const markets = ev.markets || [];
  const vol24 = markets.reduce((s, m) => s + (m.volume24hr ?? 0), 0);
  const volTotal = markets.reduce((s, m) => s + (m.volume ?? 0), 0);
  const liq = markets.reduce((s, m) => s + (Number(m.liquidity) || Number((m as DiscoveryScreenerMarket).liquidity_usd) || 0), 0);
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
  const minSlippage1k = markets.reduce<number | null>((min, m) => {
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
  };
}

/** Card tint: interesting (positive edge) = green accent; low fillability = red; else neutral */
function getCardInterestStyle(hasPositiveEdge: boolean, worstFillability: number | null, noTradeableState: boolean) {
  if (noTradeableState) return 'border-red-500/40 bg-red-500/5';
  if (hasPositiveEdge) return 'border-[#22C55E]/30 bg-[#22C55E]/5 hover:bg-[#22C55E]/8 hover:border-[#22C55E]/50';
  if (worstFillability != null && worstFillability < 60) return 'border-[#EF4444]/20 bg-[#EF4444]/5 hover:bg-[#EF4444]/8 hover:border-[#EF4444]/30';
  return 'border-[#1F2937] bg-[#111827] hover:bg-[#151B28] hover:border-[#374151]';
}

export interface DiscoveryEventCardProps {
  event: DiscoveryScreenerEvent;
  isExpanded: boolean;
  onToggle: () => void;
  noTradeableState?: boolean;
  isDemo?: boolean;
  selectedStrategyId?: string;
  addingToUniverse?: string | null;
  onAddEvent?: () => void;
  onAddMarket?: (m: DiscoveryScreenerMarket) => void;
  renderExpanded: (event: DiscoveryScreenerEvent) => React.ReactNode;
}

export function DiscoveryEventCard({
  event: ev,
  isExpanded,
  onToggle,
  noTradeableState,
  isDemo,
  selectedStrategyId,
  addingToUniverse,
  onAddEvent,
  onAddMarket,
  renderExpanded,
}: DiscoveryEventCardProps) {
  const agg = getEventAggregates(ev);
  const urgency = getUrgency(ev);
  const cardStyle = getCardInterestStyle(agg.hasPositiveEdge, agg.worstFillability, !!noTradeableState);
  const timestamp = formatEventTimestamp(ev);
  const showHardBadge = agg.worstFillability != null && agg.worstFillability < 60;

  return (
    <div className={`rounded-lg overflow-hidden border transition-all duration-150 ${cardStyle}`}>
      {noTradeableState && (
        <div className="px-3 py-1.5 bg-red-500/10 border-b border-red-500/30 text-xs font-medium text-red-400 tracking-wide uppercase">
          Ninguno tradeable
        </div>
      )}
      <button
        type="button"
        className="w-full text-left outline-none"
        onClick={onToggle}
      >
        {/* Row 1: Event name (main) + timestamp + badges: TRADEABLE, HARD, TTR */}
        <div className="flex flex-wrap items-center gap-2 px-4 pt-4 pb-1">
          <span className="text-[#6B7280] shrink-0">
            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </span>
          <div className="min-w-0 flex-1">
            <span className="font-semibold text-[#E5E7EB] truncate block">{ev.title}</span>
            {timestamp && (
              <span className="text-xs text-[#6B7280]">{timestamp}</span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-1.5 shrink-0">
            {agg.nTradeable > 0 && (
              <span className="rounded-full bg-[#22C55E]/15 text-[#22C55E] px-2 py-0.5 text-[11px] font-medium tracking-wide uppercase">
                Tradeable
              </span>
            )}
            {showHardBadge && (
              <span className="rounded-full bg-[#EF4444]/15 text-[#EF4444] px-2 py-0.5 text-[11px] font-medium tracking-wide">
                HARD
              </span>
            )}
            {urgency && (
              <span
                className={`rounded px-2 py-0.5 text-[11px] font-medium tabular-nums ${
                  urgency.urgent ? 'bg-[#F59E0B]/15 text-[#F59E0B]' : 'bg-[#374151]/80 text-[#9CA3AF]'
                }`}
              >
                TTR {urgency.label.replace('⏱ ', '')}
              </span>
            )}
            {!isDemo && selectedStrategyId && onAddEvent && (
              <Button
                size="sm"
                variant="outline"
                className="border-[#374151] text-[#9CA3AF] hover:bg-[#1F2937] hover:text-[#E5E7EB]"
                disabled={!!addingToUniverse}
                onClick={(e) => {
                  e.stopPropagation();
                  onAddEvent();
                }}
              >
                {addingToUniverse === `event:${ev.event_id}` ? '…' : 'Añadir evento'}
              </Button>
            )}
          </div>
        </div>

        {/* Row 2: Best edge | Min spread | Slippage $1k | Depth | Liq | Vol 24h */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 pl-[2.25rem] text-xs">
          {agg.hasPositiveEdge && agg.bestEdgeCents != null && agg.bestEdgeCents > 0 ? (
            <span className="font-semibold tabular-nums text-[#22C55E]">
              Best edge +{agg.bestEdgeCents.toFixed(1)}¢
            </span>
          ) : (
            <span className="text-[#6B7280]">No positive edge</span>
          )}
          {agg.minSpreadBps != null && (
            <span className="text-[#9CA3AF] tabular-nums">Min spread {agg.minSpreadBps.toFixed(0)} bps</span>
          )}
          {agg.minSlippage1k != null && (
            <span className="text-[#9CA3AF] tabular-nums">Slippage $1k: {agg.minSlippage1k.toFixed(0)}¢</span>
          )}
          {agg.depth50 != null && (
            <span className="text-[#9CA3AF] tabular-nums">Depth@50bps {formatUsdShort(agg.depth50)}</span>
          )}
          <span className="text-[#9CA3AF] tabular-nums">Liq {formatUsdShort(agg.liq)}</span>
          <span className="text-[#9CA3AF] tabular-nums">24h Vol {formatUsdShort(agg.vol24)}</span>
          <span className="text-[#9CA3AF] tabular-nums">Total Vol {formatUsdShort(agg.volTotal)}</span>
        </div>

        {/* Row 3: N markets · N tradeables · Ends · optional Best market */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 px-4 pb-4 pl-[2.25rem] text-[11px] text-[#6B7280]">
          <span className="tabular-nums">{agg.nMarkets} markets</span>
          <span className="tabular-nums">{agg.nTradeable} tradeable</span>
          {ev.end_date && (
            <>
              <span className="opacity-70">·</span>
              <span>Ends {formatEndDate(ev.end_date)}</span>
            </>
          )}
          {agg.bestMarket && (
            <>
              <span className="opacity-70">·</span>
              <span className="truncate max-w-[200px]" title={agg.bestMarket}>
                Best: {agg.bestMarket}
              </span>
            </>
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-[#1F2937] bg-[#0B0F14]/50">
          {renderExpanded(ev)}
        </div>
      )}
    </div>
  );
}
