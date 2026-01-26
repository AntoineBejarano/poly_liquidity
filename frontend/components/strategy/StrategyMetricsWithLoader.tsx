'use client';

import { useParams } from 'next/navigation';
import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { StrategyMetrics } from './StrategyMetrics';
import { CardSkeleton } from '@/components/ui/skeleton';
import { StrategyMetric } from '@/types/strategy';

export function StrategyMetricsWithLoader() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const params = useParams();
  const strategyId = params.id as string;

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<StrategyMetric[]>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected || !strategyId) {
        throw new Error('User not authenticated or strategy ID missing');
      }

      const api = initApiClient(createTokenGetter(user, stackApp));
      const response = await api.get<{ metrics: StrategyMetric[] }>(`/strategies/${strategyId}/metrics`).catch(() => ({ metrics: [] }));
      return response.metrics || [];
    },
    dependencies: [user, stackApp, isConnected, strategyId],
    refreshInterval: 10000,
    enabled: !!user && !!stackApp && isConnected && !!strategyId,
    showSkeleton: true,
    skeletonComponent: CardSkeleton,
    showRefreshingIndicator: true,
  });

  if (renderSkeleton) {
    return <>{renderSkeleton}</>;
  }

  const metrics = data || [];

  return (
    <div className="relative">
      {renderRefreshingIndicator}
      <StrategyMetrics metrics={metrics} />
    </div>
  );
}

