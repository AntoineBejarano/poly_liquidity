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
      const response = await api.get<{ intents: ExecutionIntent[]; total: number }>(`/strategies/${strategyId}/intents?limit=20`).catch(() => ({ intents: [], total: 0 }));
      return response.intents || [];
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

