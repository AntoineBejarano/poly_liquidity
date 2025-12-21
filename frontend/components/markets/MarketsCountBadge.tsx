'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';

interface MarketsCountData {
  count: number;
}

interface MarketsCountBadgeProps {
  type: 'series' | 'markets' | 'events';
}

export function MarketsCountBadge({ type }: MarketsCountBadgeProps) {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();

  const endpoint = type === 'series' ? '/series' : type === 'markets' ? '/markets' : '/markets/events/list';

  const { data } = useComponentDataLoader<MarketsCountData | any[]>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected) {
        throw new Error('User not authenticated or backend not connected');
      }

      const api = initApiClient(createTokenGetter(user, stackApp));
      const result = await api.get<any[]>(endpoint).catch(() => []);
      
      return Array.isArray(result) ? result : [];
    },
    dependencies: [user, stackApp, isConnected],
    refreshInterval: 10000,
    enabled: !!user && !!stackApp && isConnected,
    showSkeleton: false,
    showRefreshingIndicator: false,
  });

  const count = Array.isArray(data) ? data.length : 0;

  return <span>({count})</span>;
}

