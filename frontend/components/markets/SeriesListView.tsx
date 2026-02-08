'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { DiscoverySeries } from '@/lib/discovery/types';

interface SeriesListViewProps {
  series: DiscoverySeries[];
  loading?: boolean;
  onAddSeries: (s: DiscoverySeries) => void;
  addingId: string | null;
}

export function SeriesListView({
  series,
  loading = false,
  onAddSeries,
  addingId,
}: SeriesListViewProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    const next = new Set(expandedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setExpandedIds(next);
  };

  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-14 bg-muted animate-pulse rounded-lg" />
        ))}
      </div>
    );
  }

  if (series.length === 0) {
    return (
      <div className="py-12 text-center text-muted-foreground text-sm">
        No hay series con estos filtros.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {series.map((s) => {
        const id = s.polymarket_series_id ?? s.series_id;
        const expanded = expandedIds.has(id);
        const isAdding = addingId === id;

        return (
          <div key={id} className="border rounded-lg overflow-hidden bg-card">
            <div className="flex items-center gap-2 p-3">
              <button
                type="button"
                onClick={() => toggle(id)}
                className="p-0.5 hover:bg-muted rounded"
                aria-expanded={expanded}
              >
                {expanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </button>
              <div className="flex-1 min-w-0">
                <span className="font-medium text-sm truncate block">
                  {s.name}
                </span>
                <span className="text-xs text-muted-foreground">
                  {s.markets_count ?? 0} market{(s.markets_count ?? 0) !== 1 ? 's' : ''}
                  {s.events_count != null && ` · ${s.events_count} event${s.events_count !== 1 ? 's' : ''}`}
                </span>
              </div>
              <Button
                size="sm"
                variant="outline"
                disabled={isAdding || (s.markets_count ?? 0) === 0}
                onClick={() => onAddSeries(s)}
              >
                {isAdding ? '...' : 'Add series'}
              </Button>
            </div>
            {expanded && (
              <div className="border-t bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                Expandir muestra detalles cuando hay endpoint de markets por serie.
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
