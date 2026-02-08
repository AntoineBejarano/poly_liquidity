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
}

/**
 * Muestra los outcomes de un mercado con su probabilidad (%), precio en céntimos y barra de progreso.
 */
export function MarketOutcomesWithProbability({ market, compact = false }: MarketOutcomesWithProbabilityProps) {
  const labels = getOutcomeLabels(market);
  const prices = parseOutcomePrices(market.outcome_prices);
  const hasPrices = prices.length > 0;
  const pairs: { label: string; prob: number }[] = labels.map((label, i) => {
    let prob = prices[i] ?? 0;
    if (prices.length === 1 && labels.length === 2 && i === 1) prob = 1 - prices[0];
    return { label, prob };
  });
  if (pairs.length === 0) return null;

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
    <div className="mt-2">
      <p className="text-xs text-muted-foreground mb-1.5 font-medium">Probabilidad por opción</p>
      <div className="space-y-2">
        {pairs.map(({ label, prob }, i) => {
          const pct = Math.round(prob * 100);
          const cents = (prob * 100).toFixed(1);
          const showValue = hasPrices && prob >= 0;
          return (
            <div
              key={i}
              className="rounded-lg border border-border bg-card overflow-hidden"
              style={{ borderLeftColor: 'hsl(var(--primary))', borderLeftWidth: '3px' }}
            >
              <div className="flex items-center justify-between gap-3 px-3 py-2">
                <span className="text-sm font-medium text-foreground truncate">{label}</span>
                <div className="flex flex-col items-end shrink-0">
                  <span className={`text-sm font-semibold ${showValue ? 'text-emerald-500' : 'text-muted-foreground'}`}>
                    {showValue ? `${pct}%` : '—'}
                  </span>
                  <span className="text-xs text-muted-foreground">{showValue ? `${cents}¢` : '—'}</span>
                </div>
              </div>
              <div className="h-1.5 bg-muted overflow-hidden">
                <div
                  className={`h-full transition-all ${showValue ? 'bg-emerald-500/80' : 'bg-muted-foreground/20'}`}
                  style={{ width: showValue ? `${Math.min(100, Math.max(0, pct))}%` : '0%' }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
