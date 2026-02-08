'use client';

import type { DiscoveryTradeableMarket } from '@/lib/discovery/types';

function getOutcomeLabels(m: DiscoveryTradeableMarket): string[] {
  const short = m.short_outcomes;
  if (Array.isArray(short) && short.length > 0) return short;
  if (typeof short === 'string' && short.trim()) {
    if (short.trim().startsWith('[')) {
      try {
        const arr = JSON.parse(short) as string[];
        return Array.isArray(arr) ? arr : [short.trim()];
      } catch {
        return short.split(/[|,]/).map((s) => s.trim()).filter(Boolean);
      }
    }
    return short.split(/[|,]/).map((s) => s.trim()).filter(Boolean);
  }
  const out = m.outcomes;
  if (Array.isArray(out) && out.length > 0) return out;
  if (typeof out === 'string' && out.trim()) {
    if (out.trim().startsWith('[')) {
      try {
        const arr = JSON.parse(out) as string[];
        return Array.isArray(arr) ? arr : [out.trim()];
      } catch {
        return out.split(/[|,]/).map((s) => s.trim()).filter(Boolean);
      }
    }
    return out.split(/[|,]/).map((s) => s.trim()).filter(Boolean);
  }
  return [m.question];
}

/** Acepta string "0.65,0.35" o "65,35" (%), o array [0.65, 0.35]. Devuelve siempre probabilidades 0–1. */
function parseOutcomePrices(raw: string | number[] | null | undefined): number[] {
  if (raw == null) return [];
  if (Array.isArray(raw)) {
    return raw.map((n) => {
      const v = Number(n);
      if (Number.isNaN(v) || v < 0) return 0;
      return v > 1 && v <= 100 ? v / 100 : Math.min(1, v);
    });
  }
  if (typeof raw !== 'string' || !raw.trim()) return [];
  return raw
    .split(',')
    .map((s) => parseFloat(s.trim()))
    .filter((n) => !Number.isNaN(n) && n >= 0)
    .map((n) => (n > 1 && n <= 100 ? n / 100 : Math.min(1, n)));
}

export interface MarketOutcomesWithProbabilityProps {
  market: DiscoveryTradeableMarket;
  /** Si true, diseño compacto (chips + % inline). Si false, tarjetas por outcome como en Polymarket. */
  compact?: boolean;
  /** Contexto: una sola línea sobria, sin cajas; probabilidad secundaria (no compite con edge). */
  variant?: 'default' | 'context';
}

/**
 * Muestra los outcomes de un mercado con su probabilidad (%), precio en céntimos y barra de progreso.
 */
export function MarketOutcomesWithProbability({ market, compact = false, variant = 'default' }: MarketOutcomesWithProbabilityProps) {
  const labels = getOutcomeLabels(market);
  const prices = parseOutcomePrices(market.outcome_prices);
  const hasPrices = prices.length > 0;
  const pairs: { label: string; prob: number }[] = labels.map((label, i) => {
    let prob = prices[i] ?? 0;
    if (prices.length === 1 && labels.length === 2 && i === 1) prob = 1 - prices[0];
    return { label, prob };
  });
  if (pairs.length === 0) return null;

  /* Context: una línea, tipografía pequeña y neutra; no compite con edge */
  if (variant === 'context') {
    return (
      <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
        {pairs.map(({ label, prob }, i) => (
          <span key={i} className="tabular-nums">
            <span className="text-foreground/70 font-medium">{label}</span>
            {' '}
            {hasPrices && prob >= 0 ? `${Math.round(prob * 100)}%` : '—'}
          </span>
        ))}
      </div>
    );
  }

  if (compact) {
    return (
      <div className="flex flex-wrap gap-2 items-center mt-1">
        {pairs.map(({ label, prob }, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-1.5 px-2 py-1 text-xs font-medium rounded-md bg-muted/80 text-foreground border border-border"
          >
            <span>{label}</span>
            <span className="text-emerald-500 font-semibold">{hasPrices && prob > 0 ? `${Math.round(prob * 100)}%` : '—'}</span>
          </span>
        ))}
      </div>
    );
  }

  return (
    <div className="mt-1.5">
      <p className="text-[11px] text-muted-foreground mb-1 font-medium uppercase tracking-wide">Probabilidad</p>
      <div className="space-y-1.5">
        {pairs.map(({ label, prob }, i) => {
          const pct = Math.round(prob * 100);
          const showValue = hasPrices && prob >= 0;
          return (
            <div
              key={i}
              className="flex items-center justify-between gap-2 py-1 border-b border-border/50 last:border-b-0"
            >
              <span className="text-xs text-foreground/80 truncate">{label}</span>
              <span className={`text-xs tabular-nums shrink-0 ${showValue ? 'text-muted-foreground' : 'text-muted-foreground/70'}`}>
                {showValue ? `${pct}%` : '—'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
