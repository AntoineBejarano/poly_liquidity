'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { MarketCard } from './MarketCard';

interface Tag {
  tag_id: string;
  name: string;
}

interface Event {
  event_id: string;
  polymarket_event_id: string;
  market_id: string;
  market_name: string;
  start_time: string | null;
  end_time: string | null;
  state: 'UPCOMING' | 'ACTIVE' | 'FINISHED';
}

interface Market {
  market_id: string;
  polymarket_id: string;
  name: string;
  category: string | null;
  enabled: boolean;
  tags: Tag[];
  events_count: number;
  events?: Event[];
}

interface Series {
  series_id: string;
  polymarket_series_id: string;
  name: string;
  slug: string | null;
  description: string | null;
  series_type: string | null;
  recurrence: string | null;
  markets_count: number;
}

interface SeriesListProps {
  series: Series[];
  markets: Market[];
  events: Event[];
  isConnected: boolean;
  togglingMarket: string | null;
  onToggleMarket: (marketId: string, currentEnabled: boolean) => void;
  showEvents?: boolean;
}

export function SeriesList({
  series,
  markets,
  events,
  isConnected,
  togglingMarket,
  onToggleMarket,
  showEvents = false,
}: SeriesListProps) {
  const [expandedSeries, setExpandedSeries] = useState<Set<string>>(new Set());

  const toggleSeries = (seriesId: string) => {
    setExpandedSeries((prev) => {
      const next = new Set(prev);
      if (next.has(seriesId)) {
        next.delete(seriesId);
      } else {
        next.add(seriesId);
      }
      return next;
    });
  };

  // Group markets by series
  const marketsBySeries = markets.reduce((acc, market) => {
    // Use market.series_id if available, otherwise group under 'no-series'
    const actualSeriesId = (market as any).series_id || 'no-series';
    if (!acc[actualSeriesId]) {
      acc[actualSeriesId] = [];
    }
    acc[actualSeriesId].push(market);
    return acc;
  }, {} as Record<string, Market[]>);

  // Group events by market
  const eventsByMarket = events.reduce((acc, event) => {
    if (!acc[event.market_id]) {
      acc[event.market_id] = [];
    }
    acc[event.market_id].push(event);
    return acc;
  }, {} as Record<string, Event[]>);

  if (series.length === 0) {
    return (
      <div className="border border-border rounded-lg p-8 text-center bg-card">
        <p className="text-sm text-muted-foreground mb-1">No hay series disponibles</p>
        <p className="text-xs text-muted-foreground">
          Las series aparecerán aquí cuando el scanner las descubra
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {series.map((s) => {
        const seriesMarkets = marketsBySeries[s.series_id] || [];
        const isExpanded = expandedSeries.has(s.series_id);

        return (
          <Card key={s.series_id} className="border-border">
            <div
              className="p-4 border-b border-border cursor-pointer hover:bg-muted/50 transition-colors"
              onClick={() => toggleSeries(s.series_id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    )}
                    <h3 className="text-sm font-medium text-foreground">{s.name}</h3>
                    {s.recurrence && (
                      <Badge variant="outline" className="text-xs">
                        {s.recurrence}
                      </Badge>
                    )}
                  </div>
                  {s.description && (
                    <p className="text-xs text-muted-foreground mt-1">{s.description}</p>
                  )}
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs text-muted-foreground">
                      {seriesMarkets.length} markets
                    </span>
                    {s.series_type && (
                      <Badge variant="secondary" className="text-xs">
                        {s.series_type}
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {isExpanded && (
              <div className="p-4 space-y-3">
                {seriesMarkets.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-4">
                    No hay markets en esta serie
                  </p>
                ) : (
                  seriesMarkets.map((market) => (
                    <MarketCard
                      key={market.market_id}
                      market_id={market.market_id}
                      polymarket_id={market.polymarket_id}
                      name={market.name}
                      category={market.category}
                      enabled={market.enabled}
                      tags={market.tags}
                      events_count={market.events_count}
                      events={showEvents ? eventsByMarket[market.market_id] || [] : undefined}
                      isConnected={isConnected}
                      toggling={togglingMarket === market.market_id}
                      onToggle={onToggleMarket}
                      showEvents={showEvents}
                    />
                  ))
                )}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}

