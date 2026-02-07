'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';

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
  const { isDemo } = useDataMode();

  const endpoint = type === 'series' ? '/series' : type === 'markets' ? '/markets' : '/markets/events/list';

  const { data } = useComponentDataLoader<MarketsCountData | any[]>({
    fetchFn: async () => {
      if (isDemo) return [];
      if (!isConnected && !!user) return [];
      const api = initApiClient(createTokenGetter(user ?? undefined, stackApp ?? undefined));
      const result = await api.get<any[]>(endpoint);
      return Array.isArray(result) ? result : [];
    },
    dependencies: [user, stackApp, isConnected, isDemo],
    refreshInterval: isDemo ? 0 : 10000,
    enabled: isDemo || isConnected || !user,
    showSkeleton: false,
    showRefreshingIndicator: false,
  });

  const count = Array.isArray(data) ? data.length : 0;

  return <span>({count})</span>;
}

