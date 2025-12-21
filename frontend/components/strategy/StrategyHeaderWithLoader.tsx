'use client';

import { useParams } from 'next/navigation';
import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { StrategyHeader } from './StrategyHeader';
import { CardSkeleton } from '@/components/ui/skeleton';
import { Strategy } from '@/types/strategy';

export function StrategyHeaderWithLoader({
  onPause,
  onStop,
  onConfig,
  isLoading,
  onStrategyLoaded,
}: {
  onPause?: () => void;
  onStop?: () => void;
  onConfig?: () => void;
  isLoading?: boolean;
  onStrategyLoaded?: (strategy: Strategy) => void;
}) {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const params = useParams();
  const strategyId = params.id as string;

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<Strategy>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected || !strategyId) {
        throw new Error('User not authenticated or strategy ID missing');
      }

      const api = initApiClient(createTokenGetter(user, stackApp));
      return await api.get<Strategy>(`/strategies/${strategyId}`);
    },
    dependencies: [user, stackApp, isConnected, strategyId],
    refreshInterval: 30000, // 30 segundos (menos frecuente)
    enabled: !!user && !!stackApp && isConnected && !!strategyId,
    showSkeleton: true,
    skeletonComponent: CardSkeleton,
    showRefreshingIndicator: true,
    onSuccess: (strategy) => {
      if (onStrategyLoaded) {
        onStrategyLoaded(strategy);
      }
    },
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
      <StrategyHeader
        strategy={data}
        onPause={onPause}
        onStop={onStop}
        onConfig={onConfig}
        isLoading={isLoading}
      />
    </div>
  );
}

