'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
import { EventList } from './EventList';
import { TableSkeleton } from '@/components/ui/skeleton';

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

interface EventsListData {
  events: Event[];
}

interface EventsListWithLoaderProps {
  stateFilter?: string;
}

export function EventsListWithLoader({ stateFilter = 'all' }: EventsListWithLoaderProps) {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const { isDemo } = useDataMode();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<EventsListData>({
    fetchFn: async () => {
      if (!user || !stackApp) {
        throw new Error('User not authenticated');
      }
      if (isDemo) {
        return { events: [] };
      }
      if (!isConnected) {
        return { events: [] };
      }
      const api = initApiClient(createTokenGetter(user, stackApp));
      const eventsData = await api.get<Event[]>('/markets/events/list');

      return {
        events: eventsData ?? [],
      };
    },
    dependencies: [user, stackApp, isConnected, isDemo],
    refreshInterval: isDemo ? 0 : 10000,
    enabled: !!user && !!stackApp && (isConnected || isDemo),
    showSkeleton: true,
    skeletonComponent: () => <TableSkeleton rows={5} columns={6} />,
    showRefreshingIndicator: true,
  });

  if (renderSkeleton) {
    return <>{renderSkeleton}</>;
  }

  const events = data?.events || [];

  return (
    <div className="relative">
      {renderRefreshingIndicator}
      <EventList events={events} stateFilter={stateFilter} />
    </div>
  );
}

