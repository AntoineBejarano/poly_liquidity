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
      // Use live-status endpoint which includes metrics (as per roadmap PHASE 4)
      const response = await api.get<{ metrics: any; status: any }>(`/api/strategies/${strategyId}/live-status`).catch(() => ({ metrics: {}, status: {} }));
      // Extract metrics from live-status response
      const metricsData = response.metrics || {};
      // Convert to StrategyMetric[] format
      const metrics: StrategyMetric[] = [
        {
          name: 'Total Exposure',
          value: metricsData.total_exposure_usdc || 0,
          unit: 'USDC',
          trend: 'neutral',
        },
        {
          name: 'Active Orders',
          value: metricsData.active_orders || 0,
          unit: 'orders',
          trend: 'neutral',
        },
        {
          name: 'Plans Created',
          value: metricsData.plans_created_total || 0,
          unit: 'plans',
          trend: 'neutral',
        },
        {
          name: 'Plans Executed',
          value: metricsData.plans_executed_total || 0,
          unit: 'plans',
          trend: 'neutral',
        },
      ];
      return metrics;
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

