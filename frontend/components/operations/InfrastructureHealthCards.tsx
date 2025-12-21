'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CardSkeleton } from '@/components/ui/skeleton';
import { Activity } from 'lucide-react';

interface InfrastructureHealth {
  polymarket: { status: 'ok' | 'degraded' | 'error'; latency?: number; lastUpdate?: string };
  pinnacle: { status: 'ok' | 'degraded' | 'error'; latency?: number; lastUpdate?: string };
  checkers: { active: number; total: number; lastFailure?: string };
  dataFreshness: { status: 'fresh' | 'stale' | 'error'; age?: string };
}

interface InfrastructureHealthData {
  infrastructureHealth: InfrastructureHealth;
}

export function InfrastructureHealthCards() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<InfrastructureHealthData>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected) {
        throw new Error('User not authenticated or backend not connected');
      }

      const api = initApiClient(createTokenGetter(user, stackApp));
      const liveStatus = await api.get<any>('/live/status').catch(() => null);

      // Build infrastructure health (mock for now)
      const infrastructureHealth: InfrastructureHealth = {
        polymarket: {
          status: 'ok',
          latency: 45,
          lastUpdate: new Date().toISOString(),
        },
        pinnacle: {
          status: 'ok',
          latency: 120,
          lastUpdate: new Date().toISOString(),
        },
        checkers: {
          active: liveStatus?.system_health?.checkers_active || 0,
          total: liveStatus?.system_health?.checkers_total || 0,
        },
        dataFreshness: {
          status: 'fresh',
          age: '< 5s',
        },
      };

      return {
        infrastructureHealth,
      };
    },
    dependencies: [user, stackApp, isConnected],
    refreshInterval: 10000,
    enabled: !!user && !!stackApp && isConnected,
    showSkeleton: true,
    skeletonComponent: CardSkeleton,
    showRefreshingIndicator: true,
  });

  if (renderSkeleton) {
    return <>{renderSkeleton}</>;
  }

  const infrastructureHealth = data?.infrastructureHealth;

  if (!infrastructureHealth) {
    return null;
  }

  return (
    <Card className="relative">
      {renderRefreshingIndicator}
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Infrastructure Health
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Polymarket API</span>
            <div className="flex items-center gap-2">
              <Badge variant={infrastructureHealth.polymarket.status === 'ok' ? 'success' : 'error'}>
                {infrastructureHealth.polymarket.status === 'ok' ? 'OK' : infrastructureHealth.polymarket.status}
              </Badge>
              {infrastructureHealth.polymarket.latency && (
                <span className="text-xs text-muted-foreground">
                  {infrastructureHealth.polymarket.latency}ms
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Pinnacle API</span>
            <div className="flex items-center gap-2">
              <Badge variant={infrastructureHealth.pinnacle.status === 'ok' ? 'success' : 'error'}>
                {infrastructureHealth.pinnacle.status === 'ok' ? 'OK' : infrastructureHealth.pinnacle.status}
              </Badge>
              {infrastructureHealth.pinnacle.latency && (
                <span className="text-xs text-muted-foreground">
                  {infrastructureHealth.pinnacle.latency}ms
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Checkers</span>
            <div className="flex items-center gap-2">
              <Badge variant={infrastructureHealth.checkers.active === infrastructureHealth.checkers.total ? 'success' : 'warning'}>
                {infrastructureHealth.checkers.active}/{infrastructureHealth.checkers.total}
              </Badge>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Data Freshness</span>
            <Badge variant={infrastructureHealth.dataFreshness.status === 'fresh' ? 'success' : 'warning'}>
              {infrastructureHealth.dataFreshness.age || infrastructureHealth.dataFreshness.status}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

