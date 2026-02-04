'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useDataMode } from '@/hooks/useDataMode';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CardSkeleton } from '@/components/ui/skeleton';
import Link from 'next/link';
import { TrendingUp, ExternalLink } from 'lucide-react';

interface ValuesSnapshot {
  activeSignals: number;
  executableSignals: number;
  bestEdge: number | null;
  feedStatus: 'ok' | 'degraded' | 'error';
}

interface ValuesSnapshotData {
  valuesSnapshot: ValuesSnapshot;
}

const MOCK_SNAPSHOT: ValuesSnapshot = {
  activeSignals: 2,
  executableSignals: 1,
  bestEdge: 3.2,
  feedStatus: 'ok',
};

export function ValuesSnapshotCard() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isDemo } = useDataMode();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<ValuesSnapshotData>({
    fetchFn: async () => {
      if (!user || !stackApp) {
        throw new Error('User not authenticated');
      }
      if (isDemo) {
        return { valuesSnapshot: MOCK_SNAPSHOT };
      }
      const api = initApiClient(createTokenGetter(user, stackApp));
      try {
        const response = await api.get<ValuesSnapshot>('/values/snapshot').catch(() => null);
        return { valuesSnapshot: response ?? { activeSignals: 0, executableSignals: 0, bestEdge: null, feedStatus: 'ok' as const } };
      } catch {
        return { valuesSnapshot: { activeSignals: 0, executableSignals: 0, bestEdge: null, feedStatus: 'ok' as const } };
      }
    },
    dependencies: [user, stackApp, isDemo],
    refreshInterval: isDemo ? 0 : 10000,
    enabled: !!user && !!stackApp,
    showSkeleton: true,
    skeletonComponent: CardSkeleton,
    showRefreshingIndicator: true,
  });

  if (renderSkeleton) {
    return <>{renderSkeleton}</>;
  }

  const valuesSnapshot = data?.valuesSnapshot;

  if (!valuesSnapshot) {
    return null;
  }

  return (
    <Card className="relative">
      {renderRefreshingIndicator}
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Execution Input Signals
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
            <span className="text-sm font-medium">Active Signals</span>
            <span className="text-lg font-semibold">{valuesSnapshot.activeSignals}</span>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
            <span className="text-sm font-medium">Executable Signals</span>
            <span className="text-lg font-semibold">{valuesSnapshot.executableSignals}</span>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
            <span className="text-sm font-medium">Best Current Edge</span>
            <span className="text-lg font-semibold">
              {valuesSnapshot.bestEdge !== null ? `${valuesSnapshot.bestEdge.toFixed(2)}%` : '—'}
            </span>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
            <span className="text-sm font-medium">Feed Status</span>
            <Badge variant={valuesSnapshot.feedStatus === 'ok' ? 'success' : 'error'}>
              {valuesSnapshot.feedStatus === 'ok' ? 'OK' : valuesSnapshot.feedStatus}
            </Badge>
          </div>
          <div className="pt-2">
            <Button variant="outline" size="sm" className="w-full" asChild>
              <Link href="/values/live">
                View Values Live
                <ExternalLink className="h-3 w-3 ml-1" />
              </Link>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

