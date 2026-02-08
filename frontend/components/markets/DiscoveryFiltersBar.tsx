'use client';

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';
import {
  type DiscoverySortKey,
  type DiscoveryFiltersState,
  type VolatilityFilter,
  type ExecutionFilter,
} from '@/lib/discovery/event-aggregates';

const SORT_OPTIONS: { value: DiscoverySortKey; label: string }[] = [
  { value: 'event_score', label: 'Puntuación' },
  { value: 'edge', label: 'Mejor edge' },
  { value: 'liquidity', label: 'Liquidez' },
  { value: 'slippage', label: 'Mejor slippage' },
  { value: 'freshness', label: 'Actualidad' },
  { value: 'volume24', label: 'Volumen 24h' },
  { value: 'volumeTotal', label: 'Volumen total' },
  { value: 'ends', label: 'Próximos a terminar' },
];

const ANY = 'any';
const MIN_EDGE_OPTIONS = [
  { value: ANY, label: 'Cualquier edge' },
  { value: '0.5', label: '≥ 0,5¢' },
  { value: '1', label: '≥ 1¢' },
  { value: '2', label: '≥ 2¢' },
  { value: '5', label: '≥ 5¢' },
];

const VOLATILITY_OPTIONS: { value: VolatilityFilter; label: string }[] = [
  { value: 'any', label: 'Cualquier volatilidad' },
  { value: 'NON_VOLATILE', label: 'Tranquilo' },
  { value: 'VOLATILE', label: 'Volátil' },
  { value: 'CHAOTIC', label: 'Caótico' },
];

const EXECUTION_OPTIONS: { value: ExecutionFilter; label: string }[] = [
  { value: 'any', label: 'Cualquier ejecución' },
  { value: 'GOOD', label: 'Fácil' },
  { value: 'OK', label: 'Aceptable' },
  { value: 'HARD', label: 'Difícil' },
];

const MIN_VOL24_OPTIONS = [
  { value: ANY, label: 'Cualquier vol 24h' },
  { value: '1000', label: '≥ $1K' },
  { value: '10000', label: '≥ $10K' },
  { value: '100000', label: '≥ $100K' },
];

const MAX_SPREAD_OPTIONS = [
  { value: ANY, label: 'Cualquier spread' },
  { value: '200', label: '≤ 200 bps' },
  { value: '400', label: '≤ 400 bps' },
  { value: '1000', label: '≤ 1000 bps' },
];

function toNum(v: string | null): number | null {
  if (v == null || v === '' || v === ANY) return null;
  const n = Number(v);
  return Number.isNaN(n) ? null : n;
}

export interface DiscoveryFiltersBarProps {
  /** Sort */
  sortBy: DiscoverySortKey;
  onSortChange: (v: DiscoverySortKey) => void;
  /** Tradeable filter (client-side or for display) */
  tradeableFilter: 'yes' | 'all';
  onTradeableFilterChange: (v: 'yes' | 'all') => void;
  /** TTR bucket (end_date_max) - optional, e.g. events page */
  ttrBucket?: string | null;
  onTtrBucketChange?: (v: string | null) => void;
  showTtr?: boolean;
  /** API + client filters */
  filters: DiscoveryFiltersState;
  onFiltersChange: (f: DiscoveryFiltersState) => void;
  /** Show advanced row (min vol 24h, max spread) */
  showAdvanced?: boolean;
  /** Compact mode (single row) */
  compact?: boolean;
  /** Terminal styling */
  terminal?: boolean;
}

const defaultFilters: DiscoveryFiltersState = {
  tradeableOnly: false,
  minEdgeCents: null,
  minVol24: null,
  maxSpreadBps: null,
  volatilityLabel: 'any',
  executionLabel: 'any',
};

export function DiscoveryFiltersBar({
  sortBy,
  onSortChange,
  tradeableFilter,
  onTradeableFilterChange,
  ttrBucket,
  onTtrBucketChange,
  showTtr = false,
  filters,
  onFiltersChange,
  showAdvanced = true,
  compact = false,
  terminal = true,
}: DiscoveryFiltersBarProps) {
  const hasActiveFilters =
    (filters.minEdgeCents != null && filters.minEdgeCents > 0) ||
    (filters.minVol24 != null && filters.minVol24 > 0) ||
    filters.maxSpreadBps != null ||
    (filters.volatilityLabel && filters.volatilityLabel !== 'any') ||
    (filters.executionLabel && filters.executionLabel !== 'any');

  const clearFilters = () => onFiltersChange(defaultFilters);

  const wrap = terminal ? 'rounded-lg bg-[#111827] border border-[#1F2937] p-3' : '';
  const labelClass = terminal ? 'text-[#9CA3AF]' : 'text-muted-foreground';
  const selectClass = terminal
    ? 'border-[#374151] bg-[#0B0F14] text-[#E5E7EB] hover:bg-[#1F2937]'
    : '';

  return (
    <div className={`space-y-3 ${wrap}`}>
      {/* Row 1: Sort + Tradeable + TTR + API filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`text-xs font-medium uppercase tracking-wider ${labelClass}`}>Ordenar</span>
          <Select value={sortBy} onValueChange={(v) => onSortChange(v as DiscoverySortKey)}>
            <SelectTrigger className={`w-[160px] h-8 text-xs ${selectClass}`}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SORT_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`text-xs font-medium uppercase tracking-wider ${labelClass}`}>Tradeable</span>
          <Select value={tradeableFilter} onValueChange={(v) => onTradeableFilterChange(v as 'yes' | 'all')}>
            <SelectTrigger className={`w-[130px] h-8 text-xs ${selectClass}`}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="yes">Solo tradeables</SelectItem>
              <SelectItem value="all">Todos</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {showTtr && onTtrBucketChange && (
          <div className="flex items-center gap-1.5 shrink-0">
            <span className={`text-xs font-medium uppercase tracking-wider ${labelClass}`}>TTR</span>
            <Select
              value={ttrBucket ?? 'all'}
              onValueChange={(v) => onTtrBucketChange(v === 'all' ? null : v)}
            >
              <SelectTrigger className={`w-[100px] h-8 text-xs ${selectClass}`}>
                <SelectValue placeholder="TTR" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="15M">15M</SelectItem>
                <SelectItem value="1H">1H</SelectItem>
                <SelectItem value="1D">1D</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`text-xs font-medium uppercase tracking-wider ${labelClass}`}>Edge mín.</span>
          <Select
            value={filters.minEdgeCents != null ? String(filters.minEdgeCents) : ANY}
            onValueChange={(v) => onFiltersChange({ ...filters, minEdgeCents: toNum(v) })}
          >
            <SelectTrigger className={`w-[120px] h-8 text-xs ${selectClass}`}>
              <SelectValue placeholder="Edge" />
            </SelectTrigger>
            <SelectContent>
              {MIN_EDGE_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`text-xs font-medium uppercase tracking-wider ${labelClass}`}>Volatilidad</span>
          <Select
            value={filters.volatilityLabel ?? 'any'}
            onValueChange={(v) => onFiltersChange({ ...filters, volatilityLabel: v as VolatilityFilter })}
          >
            <SelectTrigger className={`w-[140px] h-8 text-xs ${selectClass}`}>
              <SelectValue placeholder="Volatilidad" />
            </SelectTrigger>
            <SelectContent>
              {VOLATILITY_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`text-xs font-medium uppercase tracking-wider ${labelClass}`}>Ejecución</span>
          <Select
            value={filters.executionLabel ?? 'any'}
            onValueChange={(v) => onFiltersChange({ ...filters, executionLabel: v as ExecutionFilter })}
          >
            <SelectTrigger className={`w-[140px] h-8 text-xs ${selectClass}`}>
              <SelectValue placeholder="Ejecución" />
            </SelectTrigger>
            <SelectContent>
              {EXECUTION_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {hasActiveFilters && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className={`h-8 text-xs ${terminal ? 'text-[#9CA3AF] hover:bg-[#1F2937] hover:text-[#E5E7EB]' : ''}`}
            onClick={clearFilters}
          >
            <X className="h-3.5 w-3.5 mr-1" />
            Limpiar filtros
          </Button>
        )}
      </div>

      {/* Row 2: Advanced (client-side only) */}
      {showAdvanced && !compact && (
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-[#1F2937]/80">
          <span className={`text-[11px] font-medium uppercase tracking-wider ${labelClass}`}>Volumen y spread</span>
          <Select
            value={filters.minVol24 != null ? String(filters.minVol24) : ANY}
            onValueChange={(v) => onFiltersChange({ ...filters, minVol24: toNum(v) })}
          >
            <SelectTrigger className={`w-[130px] h-7 text-xs ${selectClass}`}>
              <SelectValue placeholder="Vol. 24h mín." />
            </SelectTrigger>
            <SelectContent>
              {MIN_VOL24_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={filters.maxSpreadBps != null ? String(filters.maxSpreadBps) : ANY}
            onValueChange={(v) => onFiltersChange({ ...filters, maxSpreadBps: toNum(v) })}
          >
            <SelectTrigger className={`w-[130px] h-7 text-xs ${selectClass}`}>
              <SelectValue placeholder="Spread máx." />
            </SelectTrigger>
            <SelectContent>
              {MAX_SPREAD_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
    </div>
  );
}
