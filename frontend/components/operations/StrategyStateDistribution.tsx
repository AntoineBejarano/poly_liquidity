'use client';

import { useMemo } from 'react';
import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { Card, CardContent } from '@/components/ui/card';
import { CardsGridSkeleton } from '@/components/ui/skeleton';
import { Strategy } from '@/types/strategy';

interface StrategyStatus {
  strategyId: string;
  strategyName: string;
  strategyType: string;
  status: 'running' | 'paused' | 'degraded' | 'error';
  currentExposure: number;
  activeAlertsCount: number;
  lastActivity: string | null;
}

interface StrategyStateDistributionData {
  strategies: Strategy[];
  strategyStatuses: StrategyStatus[];
}

export function StrategyStateDistribution() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<StrategyStateDistributionData>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected) {
        throw new Error('User not authenticated or backend not connected');
      }

      const api = initApiClient(createTokenGetter(user, stackApp));
      const strategiesData = await api.get<Strategy[]>('/api/strategies');

      // Build strategy statuses
      const statuses: StrategyStatus[] = strategiesData.map((strategy) => {
        let strategyType = 'Custom';
        if (strategy.tags?.includes('surebet') || strategy.name.toLowerCase().includes('surebet')) {
          strategyType = 'Surebet';
        } else if (strategy.tags?.includes('liquidity') || strategy.name.toLowerCase().includes('liquidity')) {
          strategyType = 'Liquidity NR';
        } else if (strategy.tags?.includes('value') || strategy.name.toLowerCase().includes('value')) {
          strategyType = 'Value';
        }

        let status: 'running' | 'paused' | 'degraded' | 'error' = 'paused';
        if (strategy.is_active) {
          status = 'running';
        } else if (strategy.disabled_at) {
          status = 'error';
        }

        return {
          strategyId: strategy.id,
          strategyName: strategy.name,
          strategyType,
          status,
          currentExposure: 0,
          activeAlertsCount: 0,
          lastActivity: strategy.updated_at || null,
        };
      });

      return {
        strategies: strategiesData,
        strategyStatuses: statuses,
      };
    },
    dependencies: [user, stackApp, isConnected],
    refreshInterval: 10000,
    enabled: !!user && !!stackApp && isConnected,
    showSkeleton: true,
    skeletonComponent: () => <CardsGridSkeleton count={4} columns={4} />,
    showRefreshingIndicator: false, // No mostrar indicador en este componente pequeño
  });

  const strategyStatuses = data?.strategyStatuses || [];

  // Calculate strategy state distribution
  const stateDistribution = useMemo(() => {
    const running = strategyStatuses.filter(s => s.status === 'running').length;
    const paused = strategyStatuses.filter(s => s.status === 'paused').length;
    const error = strategyStatuses.filter(s => s.status === 'error').length;
    const degraded = strategyStatuses.filter(s => s.status === 'degraded').length;
    return { running, paused, error, degraded, total: strategyStatuses.length };
  }, [strategyStatuses]);

  if (renderSkeleton) {
    return <>{renderSkeleton}</>;
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 relative">
      {renderRefreshingIndicator}
      <Card>
        <CardContent className="pt-6">
          <div className="text-center">
            <div className="text-h2 text-green-600 dark:text-green-500">{stateDistribution.running}</div>
            <div className="text-caption mt-1">Running</div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6">
          <div className="text-center">
            <div className="text-h2 text-muted-foreground">{stateDistribution.paused}</div>
            <div className="text-caption mt-1">Paused</div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6">
          <div className="text-center">
            <div className="text-h2 text-yellow-600 dark:text-yellow-500">{stateDistribution.degraded}</div>
            <div className="text-caption mt-1">Degraded</div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6">
          <div className="text-center">
            <div className="text-h2 text-red-600 dark:text-red-500">{stateDistribution.error}</div>
            <div className="text-caption mt-1">Error</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

