'use client';

import { useState } from 'react';
import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useDataMode } from '@/hooks/useDataMode';
import { LiveValuesStream, type ValueSignal } from './LiveValuesStream';
import { ListSkeleton } from '@/components/ui/skeleton';

interface LiveValuesStreamWithLoaderProps {
  onSelectValue?: (value: ValueSignal | null) => void;
}

const MOCK_VALUES: ValueSignal[] = [
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

export function LiveValuesStreamWithLoader({ onSelectValue }: LiveValuesStreamWithLoaderProps) {
  const user = useUser();
  const stackApp = useStackApp();
  const { isDemo } = useDataMode();
  const [selectedValue, setSelectedValue] = useState<ValueSignal | null>(null);

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<ValueSignal[]>({
    fetchFn: async () => {
      if (!user || !stackApp) {
        throw new Error('User not authenticated');
      }
      if (isDemo) {
        return MOCK_VALUES;
      }
      const api = initApiClient(createTokenGetter(user, stackApp));
      try {
        const response = await api.get<{ values: ValueSignal[] }>('/values/live').catch(() => ({ values: [] }));
        return response?.values ?? [];
      } catch {
        return [];
      }
    },
    dependencies: [user, stackApp, isDemo],
    refreshInterval: isDemo ? 0 : 5000,
    enabled: !!user && !!stackApp,
    showSkeleton: true,
    skeletonComponent: () => <ListSkeleton items={3} />,
    showRefreshingIndicator: true,
  });

  const handleSelectValue = (value: ValueSignal | null) => {
    setSelectedValue(value);
    if (onSelectValue) {
      onSelectValue(value);
    }
  };

  if (renderSkeleton) {
    return <>{renderSkeleton}</>;
  }

  const values = data || [];

  return (
    <div className="relative">
      {renderRefreshingIndicator}
      <LiveValuesStream
        values={values}
        onSelectValue={handleSelectValue}
        selectedValue={selectedValue}
      />
    </div>
  );
}

