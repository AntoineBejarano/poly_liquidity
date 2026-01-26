'use client';

import { useState, useMemo } from 'react';
import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { MarketCard } from './MarketCard';
import { ListSkeleton } from '@/components/ui/skeleton';

interface Tag {
  tag_id: string;
  name: string;
}

interface Market {
  market_id: string;
  polymarket_id: string;
  name: string;
  category: string | null;
  enabled: boolean;
  series_id: string | null;
  series_name: string | null;
  tags: Tag[];
  events_count: number;
  created_at: string;
  updated_at: string;
}

interface Event {
  event_id: string;
  polymarket_event_id: string;
  market_id: string;
  market_name: string;
  start_time: string | null;
  end_time: string | null;
  state: 'UPCOMING' | 'ACTIVE' | 'FINISHED';
  created_at: string;
  updated_at: string;
}

interface MarketsListData {
  markets: Market[];
  events: Event[];
}

interface MarketsListWithLoaderProps {
  searchTerm?: string;
  categoryFilter?: string;
  seriesFilter?: string;
  selectedTags?: string[];
  enabledFilter?: string;
  onToggleMarket?: (marketId: string, currentEnabled: boolean) => void;
  showEvents?: boolean;
}

export function MarketsListWithLoader({
  searchTerm = '',
  categoryFilter = 'all',
  seriesFilter = 'all',
  selectedTags = [],
  enabledFilter = 'all',
  onToggleMarket,
  showEvents = false,
}: MarketsListWithLoaderProps) {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const [togglingMarket, setTogglingMarket] = useState<string | null>(null);

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<MarketsListData>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected) {
        throw new Error('User not authenticated or backend not connected');
      }

      const api = initApiClient(createTokenGetter(user, stackApp));
      
      const [marketsData, eventsData] = await Promise.all([
        api.get<Market[]>('/markets').catch(() => []),
        api.get<Event[]>('/markets/events/list').catch(() => []),
      ]);

      return {
        markets: marketsData,
        events: eventsData,
      };
    },
    dependencies: [user, stackApp, isConnected],
    refreshInterval: 10000,
    enabled: !!user && !!stackApp && isConnected,
    showSkeleton: true,
    skeletonComponent: () => <ListSkeleton items={5} />,
    showRefreshingIndicator: true,
  });

  const handleToggleMarket = async (marketId: string, currentEnabled: boolean) => {
    if (!user || !stackApp || !isConnected || togglingMarket) return;
    
    setTogglingMarket(marketId);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.patch(`/markets/${marketId}/enable`, { enabled: !currentEnabled });
    } catch (err) {
      console.error('Error toggling market:', err);
    } finally {
      setTogglingMarket(null);
    }
    
    if (onToggleMarket) {
      onToggleMarket(marketId, currentEnabled);
    }
  };

  // Group events by market
  const eventsByMarket = useMemo(() => {
    const events = data?.events || [];
    return events.reduce((acc, event) => {
      if (!acc[event.market_id]) {
        acc[event.market_id] = [];
      }
      acc[event.market_id].push(event);
      return acc;
    }, {} as Record<string, Event[]>);
  }, [data?.events]);

  // Filter markets
  const filteredMarkets = useMemo(() => {
    const markets = data?.markets || [];
    return markets.filter(market => {
      if (searchTerm && !market.name.toLowerCase().includes(searchTerm.toLowerCase())) {
        return false;
      }
      if (categoryFilter !== 'all' && market.category !== categoryFilter) {
        return false;
      }
      if (seriesFilter !== 'all' && market.series_id !== seriesFilter) {
        return false;
      }
      if (selectedTags.length > 0 && !market.tags.some(t => selectedTags.includes(t.tag_id))) {
        return false;
      }
      if (enabledFilter !== 'all') {
        const isEnabled = enabledFilter === 'enabled';
        if (market.enabled !== isEnabled) return false;
      }
      return true;
    });
  }, [data?.markets, searchTerm, categoryFilter, seriesFilter, selectedTags, enabledFilter]);

  if (renderSkeleton) {
    return <>{renderSkeleton}</>;
  }

  return (
    <div className="relative">
      {renderRefreshingIndicator}
      <div className="space-y-3">
        {filteredMarkets.length === 0 ? (
          <div className="border border-border rounded-lg p-8 text-center bg-card">
            <p className="text-sm text-muted-foreground">No hay markets disponibles</p>
          </div>
        ) : (
          filteredMarkets.map((market) => (
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
              onToggle={handleToggleMarket}
              showEvents={showEvents}
            />
          ))
        )}
      </div>
    </div>
  );
}

