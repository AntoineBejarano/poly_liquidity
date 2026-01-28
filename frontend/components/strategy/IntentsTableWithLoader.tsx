'use client';

import { useParams } from 'next/navigation';
import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { IntentsTable } from './IntentsTable';
import { StrategyTableSkeleton } from '@/components/ui/skeleton';
import { ExecutionIntent } from '@/types/strategy';

export function IntentsTableWithLoader() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const params = useParams();
  const strategyId = params.id as string;

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<ExecutionIntent[]>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected || !strategyId) {
        throw new Error('User not authenticated or strategy ID missing');
      }

      const api = initApiClient(createTokenGetter(user, stackApp));
      // Use executions endpoint which returns Execution Plans (as per roadmap PHASE 4)
      const response = await api.get<{ executions: any[]; total: number }>(`/api/strategies/${strategyId}/executions?limit=20`).catch(() => ({ executions: [], total: 0 }));
      // Map Execution Plans to ExecutionIntent format for compatibility
      return (response.executions || []).map((plan: any) => ({
        id: plan.plan_id || plan.id,
        strategy_id: plan.strategy_id,
        event_id: plan.event_id,
        side: plan.legs?.[0]?.side || 'BUY',
        outcome: plan.legs?.[0]?.outcome || 'YES',
        target_price: plan.legs?.[0]?.target_price || 0,
        size: plan.legs?.[0]?.size || 0,
        size_usdc: plan.legs?.[0]?.size_usdc || 0,
        status: plan.status || 'PENDING',
        created_at: plan.created_at,
        trace_id: plan.trace_id,
      })) as ExecutionIntent[];
    },
    dependencies: [user, stackApp, isConnected, strategyId],
    refreshInterval: 10000,
    enabled: !!user && !!stackApp && isConnected && !!strategyId,
    showSkeleton: true,
    skeletonComponent: () => (
      <div className="space-y-3">
        <StrategyTableSkeleton rows={5} columns={6} />
      </div>
    ),
    showRefreshingIndicator: true,
  });

  if (renderSkeleton) {
    return <>{renderSkeleton}</>;
  }

  const intents = data || [];

  return (
    <div className="relative">
      {renderRefreshingIndicator}
      <IntentsTable intents={intents} />
    </div>
  );
}

