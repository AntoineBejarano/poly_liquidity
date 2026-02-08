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
      const metricsData = response?.metrics ?? {};
      // Build one StrategyMetric-compatible object from live-status for StrategyMetrics
      const now = new Date().toISOString();
      const m: StrategyMetric = {
        id: 'live',
        strategy_id: strategyId,
        period_start: now,
        period_end: now,
        total_intents: metricsData.total_intents ?? 0,
        approved_intents: metricsData.approved_intents ?? 0,
        executed_intents: metricsData.executed_intents ?? 0,
        rejected_intents: metricsData.rejected_intents ?? 0,
        total_volume_usdc: metricsData.total_volume_usdc ?? 0,
        total_exposure_usdc: metricsData.total_exposure_usdc ?? 0,
        total_pnl_usdc: metricsData.total_pnl_usdc,
        win_rate: metricsData.win_rate,
        calculated_at: now,
      };
      return [m];
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
      <StrategyMetrics metrics={metrics} strategyId={strategyId} />
    </div>
  );
}

