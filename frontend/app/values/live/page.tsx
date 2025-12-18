'use client';

import { useEffect, useState } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { useRouter } from 'next/navigation';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { GlobalSignalHeader } from '@/components/values/GlobalSignalHeader';
import { LiveValuesStream } from '@/components/values/LiveValuesStream';
import { EdgeDynamics } from '@/components/values/EdgeDynamics';
import { SourceHealthBreakdown } from '@/components/values/SourceHealthBreakdown';
import { SignalQualityPanel } from '@/components/values/SignalQualityPanel';
import { StrategyReadiness } from '@/components/values/StrategyReadiness';
import { SignalAlerts } from '@/components/values/SignalAlerts';
import { SignalLifecycleView } from '@/components/values/SignalLifecycleView';
import { HistoricalContext } from '@/components/values/HistoricalContext';

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

interface GlobalSignalState {
  activeValues: number;
  executableValues: number;
  degradedValues: number;
  lastRefresh: number;
  systemStatus: 'healthy' | 'partial-degradation' | 'signal-feed-compromised';
}

export default function ValuesLivePage() {
  const user = useUser();
  const stackApp = useStackApp();
  const router = useRouter();
  const { isConnected } = useBackendConnection();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [values, setValues] = useState<ValueSignal[]>([]);
  const [globalState, setGlobalState] = useState<GlobalSignalState>({
    activeValues: 0,
    executableValues: 0,
    degradedValues: 0,
    lastRefresh: 0,
    systemStatus: 'healthy',
  });
  const [selectedValue, setSelectedValue] = useState<ValueSignal | null>(null);
  const [alerts, setAlerts] = useState<Array<{
    id: string;
    severity: 'warning' | 'error' | 'info';
    message: string;
    timestamp: string;
    valueId?: string;
  }>>([]);

  useEffect(() => {
    if (!user || !isConnected) {
      setLoading(false);
      return;
    }

    const api = initApiClient(createTokenGetter(user, stackApp));

    const fetchData = async () => {
      try {
        setLoading(true);
        
        // TODO: Replace with actual API endpoints
        // const [valuesResponse, globalResponse, alertsResponse] = await Promise.all([
        //   api.get<{ values: ValueSignal[] }>('/values/live'),
        //   api.get<GlobalSignalState>('/values/global-state'),
        //   api.get<Array<{ id: string; severity: string; message: string; timestamp: string }>>('/values/alerts'),
        // ]);

        // Mock data for now
        const mockValues: ValueSignal[] = [
          {
            id: 'value-1',
            type: 'surebet',
            event: 'NFL Championship',
            market: 'Winner',
            venues: ['Polymarket', 'Pinnacle'],
            edgeNet: 3.2,
            edgeDelta: 0.1,
            confidence: 'high',
            age: 5,
            status: 'fresh',
            lifecycle: 'tradable',
            sources: [
              { id: 'pm', name: 'Polymarket', timestamp: new Date().toISOString(), latency: 120, stability: 0.98, status: 'synced' },
              { id: 'pn', name: 'Pinnacle', timestamp: new Date().toISOString(), latency: 450, stability: 0.95, status: 'lagging' },
            ],
            quality: {
              sourcesConfirming: 2,
              historicalConsistency: 0.92,
              invalidationRatio: 0.05,
              contradictions: 0,
            },
            edgeHistory: [
              { timestamp: Date.now() - 120000, edge: 2.8 },
              { timestamp: Date.now() - 90000, edge: 3.0 },
              { timestamp: Date.now() - 60000, edge: 3.1 },
              { timestamp: Date.now() - 30000, edge: 3.2 },
              { timestamp: Date.now(), edge: 3.2 },
            ],
            historical: {
              timesDetectedToday: 12,
              avgDuration: 180,
              executablePercent: 85,
              profitablePercent: 72,
            },
          },
          {
            id: 'value-2',
            type: 'near-resolution',
            event: 'Bitcoin Price',
            market: 'BTC > $50k by EOY',
            venues: ['Polymarket'],
            edgeNet: 2.5,
            edgeDelta: -0.3,
            confidence: 'medium',
            age: 45,
            status: 'decaying',
            lifecycle: 'decaying',
            sources: [
              { id: 'pm', name: 'Polymarket', timestamp: new Date().toISOString(), latency: 150, stability: 0.97, status: 'synced' },
            ],
            quality: {
              sourcesConfirming: 1,
              historicalConsistency: 0.78,
              invalidationRatio: 0.15,
              contradictions: 0,
            },
            edgeHistory: [
              { timestamp: Date.now() - 120000, edge: 3.2 },
              { timestamp: Date.now() - 90000, edge: 3.0 },
              { timestamp: Date.now() - 60000, edge: 2.8 },
              { timestamp: Date.now() - 30000, edge: 2.6 },
              { timestamp: Date.now(), edge: 2.5 },
            ],
            historical: {
              timesDetectedToday: 8,
              avgDuration: 120,
              executablePercent: 60,
            },
          },
        ];

        const mockGlobalState: GlobalSignalState = {
          activeValues: mockValues.length,
          executableValues: mockValues.filter(v => v.status !== 'invalidated' && v.status !== 'stale').length,
          degradedValues: mockValues.filter(v => v.status === 'decaying' || v.status === 'stale').length,
          lastRefresh: Date.now(),
          systemStatus: 'healthy',
        };

        const mockAlerts = [
          {
            id: 'alert-1',
            severity: 'warning' as const,
            message: 'Edge colapsó en <1s para value-2',
            timestamp: new Date().toISOString(),
            valueId: 'value-2',
          },
        ];

        setValues(mockValues);
        setGlobalState(mockGlobalState);
        setAlerts(mockAlerts);
        setError(null);
      } catch (err) {
        console.error('Error fetching values data:', err);
        setError(err instanceof Error ? err.message : 'Error al cargar datos');
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    // Polling fallback
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [user, stackApp, isConnected]);

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner text="Cargando señales de value..." />
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="space-y-4">
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6 w-full">
        {/* Connection Status */}
        <div className="flex items-center justify-end gap-2 flex-wrap">
          <Badge variant={isConnected ? 'default' : 'error'} className="whitespace-nowrap">
            {isConnected ? '🟢 Conectado' : '🔴 Desconectado'}
          </Badge>
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            Actualizado: {new Date(globalState.lastRefresh).toLocaleTimeString('es-ES')}
          </span>
        </div>

        {/* 1. Global Signal Header */}
        <div className="w-full">
          <GlobalSignalHeader state={globalState} />
        </div>

        {/* 2. Live Values Stream */}
        <div className="w-full">
          <LiveValuesStream 
            values={values} 
            onSelectValue={setSelectedValue}
            selectedValue={selectedValue}
          />
        </div>

        {/* 3. Edge Dynamics (solo si hay value seleccionada) */}
        {selectedValue && (
          <div className="w-full">
            <EdgeDynamics value={selectedValue} />
          </div>
        )}

        {/* 4. Source Health Breakdown */}
        <div className="w-full">
          <SourceHealthBreakdown values={values} selectedValue={selectedValue} />
        </div>

        {/* 5. Quality & Confidence Panel */}
        <div className="w-full">
          <SignalQualityPanel values={values} selectedValue={selectedValue} />
        </div>

        {/* 6. Strategy Readiness */}
        <div className="w-full">
          <StrategyReadiness values={values} />
        </div>

        {/* 7. Anomalies & Alerts */}
        <div className="w-full">
          <SignalAlerts alerts={alerts} values={values} />
        </div>

        {/* 8. Signal Lifecycle View */}
        <div className="w-full">
          <SignalLifecycleView values={values} />
        </div>

        {/* 9. Historical Context */}
        {selectedValue && (
          <div className="w-full">
            <HistoricalContext value={selectedValue} />
          </div>
        )}
      </div>
    </Layout>
  );
}

