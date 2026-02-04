'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useDataMode } from '@/hooks/useDataMode';
import { GlobalSignalHeader } from './GlobalSignalHeader';
import { CardSkeleton } from '@/components/ui/skeleton';

interface GlobalSignalState {
  activeValues: number;
  executableValues: number;
  degradedValues: number;
  lastRefresh: number;
  systemStatus: 'healthy' | 'partial-degradation' | 'signal-feed-compromised';
}

const MOCK_GLOBAL_STATE: GlobalSignalState = {
  activeValues: 2,
  executableValues: 1,
  degradedValues: 1,
  lastRefresh: Date.now(),
  systemStatus: 'healthy',
};

export function GlobalSignalHeaderWithLoader() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isDemo } = useDataMode();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<GlobalSignalState>({
    fetchFn: async () => {
      if (!user || !stackApp) {
        throw new Error('User not authenticated');
      }
      if (isDemo) {
        return { ...MOCK_GLOBAL_STATE, lastRefresh: Date.now() };
      }
      const api = initApiClient(createTokenGetter(user, stackApp));
      try {
        const response = await api.get<GlobalSignalState>('/values/global-state').catch(() => null);
        return response ?? { ...MOCK_GLOBAL_STATE, activeValues: 0, executableValues: 0, degradedValues: 0 };
      } catch {
        return { ...MOCK_GLOBAL_STATE, activeValues: 0, executableValues: 0, degradedValues: 0 };
      }
    },
    dependencies: [user, stackApp, isDemo],
    refreshInterval: isDemo ? 0 : 5000,
    enabled: !!user && !!stackApp,
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

