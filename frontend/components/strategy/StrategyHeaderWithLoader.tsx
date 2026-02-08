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
  onActivate,
  onConfig,
  isLoading,
  onStrategyLoaded,
  strategyOverride,
}: {
  onPause?: () => void;
  onStop?: () => void;
  onActivate?: () => void;
  onConfig?: () => void;
  isLoading?: boolean;
  onStrategyLoaded?: (strategy: Strategy) => void;
  /** Si el padre tiene la estrategia actualizada (p. ej. tras activar/pausar), usarla para no depender del refetch. */
  strategyOverride?: Strategy | null;
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
      const s = await api.get<Strategy>(`/api/strategies/${strategyId}`);
      if (!s) throw new Error('Strategy not found');
      return s;
    },
    dependencies: [user, stackApp, isConnected, strategyId],
    refreshInterval: 60000, // 60 segundos (evitar refrescos frecuentes que muestran "cargando")
    enabled: !!user && !!stackApp && isConnected && !!strategyId && !strategyOverride,
    showSkeleton: true,
    skeletonComponent: CardSkeleton,
    showRefreshingIndicator: false,
    onSuccess: (strategy) => {
      if (onStrategyLoaded) {
        onStrategyLoaded(strategy);
      }
    },
  });

  if (renderSkeleton) {
    return <>{renderSkeleton}</>;
  }

  if (!data && !strategyOverride) {
    return null;
  }

  const strategyToShow = strategyOverride ?? data;

  return (
    <div className="relative">
      {renderRefreshingIndicator}
      <StrategyHeader
        strategy={strategyToShow!}
        onPause={onPause}
        onStop={onStop}
        onActivate={onActivate}
        onConfig={onConfig}
        isLoading={isLoading}
      />
    </div>
  );
}

