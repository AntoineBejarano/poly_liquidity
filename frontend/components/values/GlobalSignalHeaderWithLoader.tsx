'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { GlobalSignalHeader } from './GlobalSignalHeader';
import { CardSkeleton } from '@/components/ui/skeleton';

interface GlobalSignalState {
  activeValues: number;
  executableValues: number;
  degradedValues: number;
  lastRefresh: number;
  systemStatus: 'healthy' | 'partial-degradation' | 'signal-feed-compromised';
}

export function GlobalSignalHeaderWithLoader() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<GlobalSignalState>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected) {
        throw new Error('User not authenticated or backend not connected');
      }

      const api = initApiClient(createTokenGetter(user, stackApp));
      
      // TODO: Replace with actual API endpoint
      // const response = await api.get<GlobalSignalState>('/values/global-state');
      // return response;

      // Mock data for now
      const mockGlobalState: GlobalSignalState = {
        activeValues: 2,
        executableValues: 1,
        degradedValues: 1,
        lastRefresh: Date.now(),
        systemStatus: 'healthy',
      };

      return mockGlobalState;
    },
    dependencies: [user, stackApp, isConnected],
    refreshInterval: 5000,
    enabled: !!user && !!stackApp && isConnected,
    showSkeleton: true,
    skeletonComponent: CardSkeleton,
    showRefreshingIndicator: true,
  });

  if (renderSkeleton) {
    return <>{renderSkeleton}</>;
  }

  if (!data) {
    return null;
  }

  return (
    <div className="relative">
      {renderRefreshingIndicator}
      <GlobalSignalHeader state={data} />
    </div>
  );
}

