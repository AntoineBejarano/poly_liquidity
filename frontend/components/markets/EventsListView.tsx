'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { DiscoveryEvent } from '@/lib/discovery/types';

interface EventsListViewProps {
  events: DiscoveryEvent[];
  loading?: boolean;
  onAddEvent: (event: DiscoveryEvent) => void;
  addingId: string | null;
}

export function EventsListView({
  events,
  loading = false,
  onAddEvent,
  addingId,
}: EventsListViewProps) {
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

  if (events.length === 0) {
    return (
      <div className="py-12 text-center text-muted-foreground text-sm">
        No hay eventos con estos filtros.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {events.map((event) => {
        const id = event.polymarket_event_id ?? event.event_id;
        const expanded = expandedIds.has(id);
        const isAdding = addingId === id;

        return (
          <div
            key={id}
            className="border rounded-lg overflow-hidden bg-card"
          >
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
                  {event.title}
                </span>
                <span className="text-xs text-muted-foreground">
                  {event.markets_count} market{event.markets_count !== 1 ? 's' : ''}
                </span>
              </div>
              <Button
                size="sm"
                variant="outline"
                disabled={isAdding || event.markets_count === 0}
                onClick={() => onAddEvent(event)}
              >
                {isAdding ? '...' : 'Add all markets'}
              </Button>
            </div>
            {expanded && event.markets && event.markets.length > 0 && (
              <div className="border-t bg-muted/30 px-3 py-2 space-y-1">
                {event.markets.map((m) => (
                  <div
                    key={m.polymarket_id}
                    className="text-xs text-muted-foreground truncate"
                  >
                    {m.name}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
