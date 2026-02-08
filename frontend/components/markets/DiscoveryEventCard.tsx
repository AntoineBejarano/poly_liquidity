'use client';

import type { DiscoveryScreenerEvent, DiscoveryScreenerMarket } from '@/lib/discovery/types';
import { getEventAggregates, formatTtrMinutes } from '@/lib/discovery/event-aggregates';
import type { SportsLiveUpdate } from '@/hooks/useSportsWebSocket';
import type { SportsLiveEventState } from '@/lib/discovery/types';
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

/** TTR exacto y urgencia (color). Siempre muestra tiempo restante exacto. */
function getTtrDisplay(ev: DiscoveryScreenerEvent): { label: string; urgent: boolean } | null {
  const agg = getEventAggregates(ev);
  const ttrMin = agg.ttrMinutes;
  if (ttrMin == null) return null;
  if (ttrMin < 0) return { label: 'Terminado', urgent: false };
  const label = formatTtrMinutes(ttrMin);
  const urgent = ttrMin < 15;
  return { label, urgent };
}

/** Volatility label badge: NON_VOLATILE / VOLATILE / CHAOTIC / UNKNOWN */
function VolatilityLabelBadge({ label, reason }: { label: string | null | undefined; reason?: string | null }) {
  if (!label) return null;
  const style =
    label === 'CHAOTIC'
      ? 'bg-[#EF4444]/15 text-[#EF4444]'
      : label === 'VOLATILE'
        ? 'bg-[#F59E0B]/15 text-[#F59E0B]'
        : label === 'UNKNOWN'
          ? 'bg-[#374151]/80 text-[#6B7280]'
          : 'bg-[#6B7280]/20 text-[#9CA3AF]';
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium tracking-wide ${style}`}>
          {label.replace(/_/g, ' ')}
        </span>
      </TooltipTrigger>
      <TooltipContent>
        <p>Event volatility (from market rolling vol)</p>
        {reason && <p className="text-muted-foreground text-xs">{reason}</p>}
      </TooltipContent>
    </Tooltip>
  );
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
  /** Resolved live state (WS first, then time-based fallback). LIVE badge only when LIVE or LIVE_ESTIMATED. */
  eventState?: SportsLiveEventState | null;
  /** Only set when WS_CONFIRMED_LIVE with high-confidence match. Score/period shown only then. */
  liveUpdate?: SportsLiveUpdate | null;
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
  eventState,
  liveUpdate,
}: DiscoveryEventCardProps) {
  const agg = getEventAggregates(ev);
  const ttrDisplay = getTtrDisplay(ev);
  const cardStyle = getCardInterestStyle(agg.hasPositiveEdge, agg.worstFillability, !!noTradeableState);
  const timestamp = formatEventTimestamp(ev);
  const showHardBadge = agg.worstFillability != null && agg.worstFillability < 60;
  const showLiveBadge =
    eventState === 'WS_CONFIRMED_LIVE' || eventState === 'TIME_BASED_LIVE_ESTIMATED';

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
        {/* Row 1: Event name (main) + live score/period + timestamp + badges */}
        <div className="flex flex-wrap items-center gap-2 px-4 pt-4 pb-1">
          <span className="text-[#6B7280] shrink-0">
            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </span>
          <div className="min-w-0 flex-1">
            <span className="font-semibold text-[#E5E7EB] truncate block">{ev.title}</span>
            {liveUpdate && (liveUpdate.score || liveUpdate.period) && (
              <span className="text-xs font-medium text-[#22C55E] tabular-nums mr-2">
                {liveUpdate.score && <span>{liveUpdate.score}</span>}
                {liveUpdate.period && (
                  <span className="text-[#9CA3AF] ml-1">
                    {liveUpdate.elapsed ? `${liveUpdate.period} ${liveUpdate.elapsed}` : liveUpdate.period}
                  </span>
                )}
              </span>
            )}
            {timestamp && (
              <span className="text-xs text-[#6B7280]">{timestamp}</span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-1.5 shrink-0">
            {showLiveBadge && (
              <span
                className="rounded-full bg-[#22C55E]/15 text-[#22C55E] px-2 py-0.5 text-[11px] font-medium tracking-wide uppercase"
                title={eventState === 'WS_CONFIRMED_LIVE' ? 'En vivo (WebSocket)' : 'En vivo (estimado por tiempo)'}
              >
                LIVE
              </span>
            )}
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
            {ttrDisplay && (
              <span
                className={`rounded px-2 py-0.5 text-[11px] font-medium tabular-nums ${
                  ttrDisplay.urgent ? 'bg-[#F59E0B]/15 text-[#F59E0B]' : 'bg-[#374151]/80 text-[#9CA3AF]'
                }`}
                title="Tiempo hasta resolución"
              >
                TTR {ttrDisplay.label}
              </span>
            )}
            <VolatilityLabelBadge
              label={ev.metrics?.volatility_label}
              reason={ev.metrics?.volatility_label_reason ?? undefined}
            />
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

        {/* Row 3: N markets · N tradeables · Termina en (exacto) · Ends date · optional Best market */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 px-4 pb-4 pl-[2.25rem] text-[11px] text-[#6B7280]">
          <span className="tabular-nums">{agg.nMarkets} markets</span>
          <span className="tabular-nums">{agg.nTradeable} tradeable</span>
          {agg.ttrMinutes != null && agg.ttrMinutes >= 0 && (
            <>
              <span className="opacity-70">·</span>
              <span className="tabular-nums">Termina en {formatTtrMinutes(agg.ttrMinutes)}</span>
            </>
          )}
          {ev.end_date && (
            <>
              <span className="opacity-70">·</span>
              <span>Fecha fin {formatEndDate(ev.end_date)}</span>
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
