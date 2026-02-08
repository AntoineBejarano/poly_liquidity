'use client';

import type { DiscoveryScreenerMarket } from '@/lib/discovery/types';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

function formatUsdShort(value: number | string | null | undefined): string {
  const n = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(n) || n <= 0) return '—';
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}

function getOutcomeLabel(m: DiscoveryScreenerMarket): string {
  const short = m.short_outcomes;
  if (Array.isArray(short) && short[0]) return String(short[0]);
  if (typeof short === 'string' && short.trim()) return short.split(/[|,]/)[0]?.trim() || 'Yes';
  const out = m.outcomes;
  if (Array.isArray(out) && out[0]) return String(out[0]);
  if (typeof out === 'string' && out.trim()) return out.split(/[|,]/)[0]?.trim() || 'Yes';
  return 'Yes';
}

const FILLABILITY_STYLES = {
  great: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 rounded-full px-2.5 py-0.5 text-xs font-medium',
  ok: 'bg-amber-500/15 text-amber-600 dark:text-amber-400 rounded-full px-2.5 py-0.5 text-xs font-medium',
  hard: 'bg-red-500/10 text-red-600 dark:text-red-400 rounded-full px-2.5 py-0.5 text-xs font-medium',
} as const;

/** Fillability pill: GREAT / OK / HARD — premium pill for market Hero row */
export function fillabilityBadge(score: number | null | undefined) {
  if (score == null) return null;
  const label = score >= 80 ? 'GREAT' : score >= 60 ? 'OK' : 'HARD';
  const style = score >= 80 ? FILLABILITY_STYLES.great : score >= 60 ? FILLABILITY_STYLES.ok : FILLABILITY_STYLES.hard;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className={style}>Fillability {score} · {label}</span>
      </TooltipTrigger>
      <TooltipContent>
        <p>Execution quality score (spread, depth, freshness)</p>
      </TooltipContent>
    </Tooltip>
  );
}

/** Compact pill for event cards: only label (GREAT / OK / HARD) */
export function fillabilityPillCompact(score: number | null | undefined) {
  if (score == null) return null;
  const label = score >= 80 ? 'GREAT' : score >= 60 ? 'OK' : 'HARD';
  const style = score >= 80 ? FILLABILITY_STYLES.great : score >= 60 ? FILLABILITY_STYLES.ok : FILLABILITY_STYLES.hard;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className={style}>{label}</span>
      </TooltipTrigger>
      <TooltipContent>
        <p>Fillability {score} — execution quality</p>
      </TooltipContent>
    </Tooltip>
  );
}

interface MarketDiscoveryMetricsProps {
  market: DiscoveryScreenerMarket;
  compact?: boolean;
  /** Terminal layout: Alpha block → Execution chips → Pricing (small) → Context */
  variant?: 'default' | 'terminal';
}

/**
 * UI tipo Bloomberg: Hero (edge) → Price (ask/bid/mid) → Microstructure (spread, depth, fresh).
 * variant=terminal: blocks + institutional palette.
 *
 * Edge: no se calcula en frontend. El backend obtiene best_bid/best_ask del orderbook,
 * calcula fair_price y edge_cents = (fair - best_ask) * 100, y envía todo en la API.
 * Mostramos precios (Ask/Bid/Mid/Fair) cuando vienen en la respuesta para que el trader vea el origen del edge.
 */
export function MarketDiscoveryMetrics({ market, compact, variant = 'default' }: MarketDiscoveryMetricsProps) {
  const m = market;
  const hasHero = m.edge_cents != null || m.slippage_1k_cents != null || m.fillability_score != null;
  const hasPrice = m.best_ask != null || m.best_bid != null || m.mid_price != null;
  const hasMicro = m.spread_bps != null || m.depth_50bps_usd != null || m.stale_ms != null;
  const showNotTradeable = !m.tradeable && (m.tradeable_reasons?.length ?? 0) > 0;

  if (!hasHero && !hasPrice && !hasMicro && !showNotTradeable) {
    return null;
  }

  const edgeVal = m.edge_cents ?? 0;
  const edgePositive = edgeVal > 0;
  const isTerminal = variant === 'terminal';

  const edgeColor = isTerminal
    ? edgePositive ? 'text-[#22C55E]' : 'text-[#EF4444]'
    : edgePositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground';
  const textSecondary = isTerminal ? 'text-[#9CA3AF]' : 'text-muted-foreground';
  const textMuted = isTerminal ? 'text-[#6B7280]' : 'text-muted-foreground/90';

  if (isTerminal) {
    return (
      <div className="space-y-4">
        {/* 1️⃣ ALPHA BLOCK — dominant; EDGE always tied to this market (instrument) */}
        {(m.edge_cents != null || showNotTradeable) && (
          <div className="flex flex-wrap items-baseline gap-2">
            {m.edge_cents != null && (
              <>
                <span className="text-xs font-medium uppercase tracking-wider text-[#9CA3AF]">
                  {getOutcomeLabel(m)}
                </span>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className={`text-xl font-bold tabular-nums tracking-wide ${edgeColor}`}>
                      {edgePositive ? '+' : ''}{m.edge_cents.toFixed(1)}¢ EDGE
                    </span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Edge = (Fair − Ask)×100¢, calculado en backend desde el orderbook.</p>
                    <p className="mt-1 text-muted-foreground">Ask / Bid / Mid / Fair se muestran abajo cuando hay libro.</p>
                  </TooltipContent>
                </Tooltip>
              </>
            )}
            {showNotTradeable && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="text-xs text-[#9CA3AF] cursor-help underline decoration-dotted ml-2">
                    Not tradeable
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  <ul className="list-disc pl-3 space-y-0.5 text-xs">
                    {(m.tradeable_reasons ?? []).map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </TooltipContent>
              </Tooltip>
            )}
          </div>
        )}
        {/* 2️⃣ EXECUTION BLOCK — chips */}
        <div className="flex flex-wrap items-center gap-2">
          {m.slippage_1k_cents != null && (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className={`rounded px-2 py-1 text-xs font-medium tabular-nums ${textSecondary} bg-[#1F2937]`}>
                  Slippage $1k: {m.slippage_1k_cents.toFixed(1)}¢
                </span>
              </TooltipTrigger>
              <TooltipContent><p>Estimated cost to execute $1k notional</p></TooltipContent>
            </Tooltip>
          )}
          {m.spread_bps != null && (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className={`rounded px-2 py-1 text-xs font-medium tabular-nums ${textSecondary} bg-[#1F2937]`}>
                  Spread: {m.spread_bps.toFixed(0)}bps
                </span>
              </TooltipTrigger>
              <TooltipContent><p>(best_ask − best_bid) / mid × 10,000</p></TooltipContent>
            </Tooltip>
          )}
          {(m.fillability_score != null || m.liquidity_usd != null || m.liquidity != null) && (
            <span className={`rounded px-2 py-1 text-xs font-medium ${textSecondary} bg-[#1F2937]`}>
              Liq: {formatUsdShort(m.liquidity_usd ?? m.liquidity)}
              {m.fillability_score != null && ` · ${m.fillability_score}/100`}
            </span>
          )}
        </div>
        {/* 3️⃣ PRICING BLOCK — origen del edge; siempre visible si hay edge o precios */}
        {(hasPrice || m.edge_cents != null) && (
          <div className="rounded bg-[#0B0F14]/60 px-3 py-2 border border-[#1F2937]">
            <p className="text-[10px] uppercase tracking-wider text-[#6B7280] mb-1">Pricing (origen del edge)</p>
            {hasPrice ? (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-0.5 text-xs tabular-nums text-[#9CA3AF]">
                {m.best_ask != null && <span>Ask <span className="text-[#E5E7EB]">{(m.best_ask * 100).toFixed(1)}%</span></span>}
                {m.best_bid != null && <span>Bid <span className="text-[#E5E7EB]">{(m.best_bid * 100).toFixed(1)}%</span></span>}
                {m.mid_price != null && <span>Mid <span className="text-[#E5E7EB]">{(m.mid_price * 100).toFixed(1)}%</span></span>}
                {m.fair_price != null && <span>Fair <span className="text-[#E5E7EB]">{(m.fair_price * 100).toFixed(1)}%</span></span>}
              </div>
            ) : (
              <p className="text-xs text-[#6B7280]">Ask/Bid/Fair no disponibles (sin libro en respuesta)</p>
            )}
          </div>
        )}
        {/* 4️⃣ CONTEXT BLOCK */}
        {(m.time_to_resolution_minutes != null || m.stale_ms != null) && (
          <div className={`flex flex-wrap items-center gap-x-3 text-[11px] ${textMuted}`}>
            {m.time_to_resolution_minutes != null && (
              <span className="tabular-nums">TTR: {Math.round(m.time_to_resolution_minutes)}m</span>
            )}
            {m.stale_ms != null && <span className="tabular-nums">Fresh {m.stale_ms}ms</span>}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3 pt-1">
      {(hasHero || showNotTradeable) && (
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1.5">
          {m.edge_cents != null && (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className={`text-lg font-bold tabular-nums ${edgeColor}`}>
                  {edgePositive ? '+' : ''}{m.edge_cents.toFixed(1)}¢ EDGE
                </span>
              </TooltipTrigger>
              <TooltipContent><p>Indicative edge vs best ask</p></TooltipContent>
            </Tooltip>
          )}
          {m.slippage_1k_cents != null && (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className={`text-sm ${textSecondary} tabular-nums`}>Slippage $1k: {m.slippage_1k_cents.toFixed(1)}¢</span>
              </TooltipTrigger>
              <TooltipContent><p>Estimated cost to execute $1k notional</p></TooltipContent>
            </Tooltip>
          )}
          {fillabilityBadge(m.fillability_score)}
          {showNotTradeable && (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className={`text-xs ${textSecondary} cursor-help underline decoration-dotted`}>Not tradeable</span>
              </TooltipTrigger>
              <TooltipContent>
                <ul className="list-disc pl-3 space-y-0.5 text-xs">
                  {(m.tradeable_reasons ?? []).map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      )}
      {hasPrice && (
        <div className={`flex flex-wrap items-center gap-x-4 gap-y-0.5 text-xs ${textSecondary}`}>
          <span className="font-medium text-foreground/80">{getOutcomeLabel(m)}</span>
          {m.best_ask != null && <span className="tabular-nums">Ask {(m.best_ask * 100).toFixed(1)}%</span>}
          {m.best_bid != null && <span className="tabular-nums">Bid {(m.best_bid * 100).toFixed(1)}%</span>}
          {m.mid_price != null && <span className="tabular-nums">Mid {(m.mid_price * 100).toFixed(1)}%</span>}
          {m.fair_price != null && <span className="tabular-nums">Fair {(m.fair_price * 100).toFixed(1)}%</span>}
        </div>
      )}
      {hasMicro && (
        <div className={`flex flex-wrap items-center gap-x-1 text-[11px] ${textMuted}`}>
          {m.spread_bps != null && <><Tooltip><TooltipTrigger asChild><span className="tabular-nums">Spread {m.spread_bps.toFixed(0)}bps</span></TooltipTrigger><TooltipContent><p>(best_ask − best_bid) / mid × 10,000</p></TooltipContent></Tooltip>{(m.depth_50bps_usd != null || m.stale_ms != null) && <span className="opacity-60">•</span>}</>}
          {m.depth_50bps_usd != null && <><Tooltip><TooltipTrigger asChild><span className="tabular-nums">Depth {formatUsdShort(m.depth_50bps_usd)}</span></TooltipTrigger><TooltipContent><p>USD within ±50bps of mid</p></TooltipContent></Tooltip>{m.stale_ms != null && <span className="opacity-60">•</span>}</>}
          {m.stale_ms != null && <Tooltip><TooltipTrigger asChild><span className="tabular-nums">Fresh {m.stale_ms}ms</span></TooltipTrigger><TooltipContent><p>Book snapshot age</p></TooltipContent></Tooltip>}
        </div>
      )}
    </div>
  );
}
