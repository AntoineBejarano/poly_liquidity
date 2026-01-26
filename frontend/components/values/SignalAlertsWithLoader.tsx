'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { SignalAlerts } from './SignalAlerts';
import { CardSkeleton } from '@/components/ui/skeleton';

interface ValueSignal {
  id: string;
  type: 'surebet' | 'near-resolution' | 'liquidity-gap' | 'custom';
  event: string;
  market: string;
  venues: string[];
  edgeNet: number;
  edgeDelta: number;
  confidence: 'high' | 'medium' | 'low';
  age: number;
  status: 'fresh' | 'improving' | 'decaying' | 'stale' | 'invalidated';
  lifecycle: 'detected' | 'confirmed' | 'tradable' | 'decaying' | 'invalidated' | 'executing';
  sources: {
    id: string;
    name: string;
    timestamp: string;
    latency: number;
    stability: number;
    status: 'synced' | 'lagging' | 'out-of-sync';
  }[];
  quality: {
    sourcesConfirming: number;
    historicalConsistency: number;
    invalidationRatio: number;
    contradictions: number;
  };
  edgeHistory: Array<{ timestamp: number; edge: number }>;
  historical: {
    timesDetectedToday: number;
    avgDuration: number;
    executablePercent: number;
    profitablePercent?: number;
  };
}

interface Alert {
  id: string;
  severity: 'warning' | 'error' | 'info';
  message: string;
  timestamp: string;
  valueId?: string;
}

interface SignalAlertsData {
  alerts: Alert[];
  values: ValueSignal[];
}

export function SignalAlertsWithLoader() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<SignalAlertsData>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected) {
        throw new Error('User not authenticated or backend not connected');
      }

      const api = initApiClient(createTokenGetter(user, stackApp));
      
      // TODO: Replace with actual API endpoints
      // const [alertsResponse, valuesResponse] = await Promise.all([
      //   api.get<Alert[]>('/values/alerts'),
      //   api.get<{ values: ValueSignal[] }>('/values/live'),
      // ]);
      // return {
      //   alerts: alertsResponse,
      //   values: valuesResponse.values,
      // };

      // Mock data for now
      const mockAlerts: Alert[] = [
        {
          id: 'alert-1',
          severity: 'warning',
          message: 'Edge colapsó en <1s para value-2',
          timestamp: new Date().toISOString(),
          valueId: 'value-2',
        },
      ];

      const mockValues: ValueSignal[] = []; // Empty for now, could be fetched separately

      return {
        alerts: mockAlerts,
        values: mockValues,
      };
    },
    dependencies: [user, stackApp, isConnected],
    refreshInterval: 5000,
    enabled: !!user && !!stackApp && isConnected,
    showSkeleton: false, // No mostrar skeleton si no hay alerts
    showRefreshingIndicator: true,
  });

  const alerts = data?.alerts || [];
  const values = data?.values || [];

  // No mostrar nada si no hay alerts
  if (alerts.length === 0 && !renderSkeleton) {
    return null;
  }

  return (
    <div className="relative">
      {renderRefreshingIndicator}
      {renderSkeleton ? (
        <>{renderSkeleton}</>
      ) : (
        <SignalAlerts alerts={alerts} values={values} />
      )}
    </div>
  );
}

