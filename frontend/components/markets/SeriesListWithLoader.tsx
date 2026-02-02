'use client';

import { useState } from 'react';
import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
import { SeriesList } from './SeriesList';
import { ListSkeleton } from '@/components/ui/skeleton';

interface Series {
  series_id: string;
  polymarket_series_id: string;
  name: string;
  slug: string | null;
  description: string | null;
  series_type: string | null;
  recurrence: string | null;
  markets_count: number;
  created_at: string;
  updated_at: string;
}

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

interface SeriesListData {
  series: Series[];
  markets: Market[];
  events: Event[];
}

interface SeriesListWithLoaderProps {
  onToggleMarket?: (marketId: string, currentEnabled: boolean) => void;
  showEvents?: boolean;
}

export function SeriesListWithLoader({ onToggleMarket, showEvents = false }: SeriesListWithLoaderProps) {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const { isDemo } = useDataMode();
  const [togglingMarket, setTogglingMarket] = useState<string | null>(null);

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<SeriesListData>({
    fetchFn: async () => {
      if (!user || !stackApp) {
        throw new Error('User not authenticated');
      }
      if (isDemo) {
        return { series: [], markets: [], events: [] };
      }
      if (!isConnected) {
        return { series: [], markets: [], events: [] };
      }
      const api = initApiClient(createTokenGetter(user, stackApp));

      const [seriesData, marketsData, eventsData] = await Promise.all([
        api.get<Series[]>('/series'),
        api.get<Market[]>('/markets'),
        api.get<Event[]>('/markets/events/list'),
      ]);

      return {
        series: seriesData ?? [],
        markets: marketsData ?? [],
        events: eventsData ?? [],
      };
    },
    dependencies: [user, stackApp, isConnected, isDemo],
    refreshInterval: isDemo ? 0 : 10000,
    enabled: !!user && !!stackApp && (isConnected || isDemo),
    showSkeleton: true,
    skeletonComponent: () => <ListSkeleton items={3} />,
    showRefreshingIndicator: true,
  });

  const handleToggleMarket = async (marketId: string, currentEnabled: boolean) => {
    if (!user || !stackApp || !isConnected || isDemo || togglingMarket) return;
    
    setTogglingMarket(marketId);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.patch(`/markets/${marketId}/enable`, { enabled: !currentEnabled });
      
      // Refetch data
      // Note: In a real implementation, we might want to update local state optimistically
      // For now, the refreshInterval will handle the update
    } catch (err) {
      console.error('Error toggling market:', err);
    } finally {
      setTogglingMarket(null);
    }
    
    if (onToggleMarket) {
      onToggleMarket(marketId, currentEnabled);
    }
  };

  if (renderSkeleton) {
    return <>{renderSkeleton}</>;
  }

  const series = data?.series || [];
  const markets = data?.markets || [];
  const events = data?.events || [];

  return (
    <div className="relative">
      {renderRefreshingIndicator}
      <SeriesList
        series={series}
        markets={markets}
        events={events}
        isConnected={isConnected}
        togglingMarket={togglingMarket}
        onToggleMarket={handleToggleMarket}
        showEvents={showEvents}
      />
    </div>
  );
}

