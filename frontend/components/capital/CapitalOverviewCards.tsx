'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { CardsGridSkeleton } from '@/components/ui/skeleton';

interface DashboardData {
  equity: number;
  realized_pnl: number;
  unrealized_pnl: number;
  global_exposure: number;
  active_markets: number;
  system_active: boolean;
}

function formatCurrency(value: number) {
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const EMPTY_DASHBOARD: DashboardData = {
  equity: 0,
  realized_pnl: 0,
  unrealized_pnl: 0,
  global_exposure: 0,
  active_markets: 0,
  system_active: false,
};

export function CapitalOverviewCards() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const { isDemo } = useDataMode();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<DashboardData>({
    fetchFn: async () => {
      if (!user || !stackApp) {
        throw new Error('User not authenticated');
      }
      if (isDemo) {
        return EMPTY_DASHBOARD;
      }
      if (!isConnected) {
        return EMPTY_DASHBOARD;
      }
      const api = initApiClient(createTokenGetter(user, stackApp));
      return (await api.get<DashboardData>('/dashboard')) ?? EMPTY_DASHBOARD;
    },
    dependencies: [user, stackApp, isConnected, isDemo],
    refreshInterval: isDemo ? 0 : 10000,
    enabled: !!user && !!stackApp && (isConnected || isDemo),
    showSkeleton: true,
    skeletonComponent: () => <CardsGridSkeleton count={4} columns={4} />,
    showRefreshingIndicator: true,
  });

  if (renderSkeleton) {
    return <>{renderSkeleton}</>;
  }

  if (!data) {
    return null;
  }

  const totalEquity = data.equity || 0;
  const totalRealizedPnL = data.realized_pnl || 0;
  const totalUnrealizedPnL = data.unrealized_pnl || 0;
  const capitalAtRisk = data.global_exposure || 0;
  const availableLiquidity = totalEquity - capitalAtRisk;

  // Calculate pending settlement (positions waiting for resolution)
  // Note: This would need positions data, but for now we'll use 0
  const pendingSettlement = 0; // TODO: Calculate from positions

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 relative">
      {renderRefreshingIndicator}
      
      <Card className="border">
        <CardHeader className="pb-3">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Total Equity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold tabular-nums">{formatCurrency(totalEquity)}</div>
          <Separator className="my-3" />
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Base</span>
              <span className="font-mono">{formatCurrency(totalEquity - totalRealizedPnL - totalUnrealizedPnL)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Realized</span>
              <span className={`font-mono ${totalRealizedPnL >= 0 ? '' : 'text-red-600'}`}>
                {totalRealizedPnL >= 0 ? '+' : ''}{formatCurrency(totalRealizedPnL)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Unrealized</span>
              <span className={`font-mono ${totalUnrealizedPnL >= 0 ? '' : 'text-red-600'}`}>
                {totalUnrealizedPnL >= 0 ? '+' : ''}{formatCurrency(totalUnrealizedPnL)}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border">
        <CardHeader className="pb-3">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Available Liquidity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold tabular-nums">{formatCurrency(availableLiquidity)}</div>
          <Separator className="my-3" />
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Utilization</span>
              <span className="font-mono">
                {totalEquity > 0 ? ((availableLiquidity / totalEquity) * 100).toFixed(1) : 0}%
              </span>
            </div>
            <Progress
              value={totalEquity > 0 ? (availableLiquidity / totalEquity) * 100 : 0}
              className="h-1.5 bg-muted"
            />
          </div>
        </CardContent>
      </Card>

      <Card className="border">
        <CardHeader className="pb-3">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Capital at Risk</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold tabular-nums">{formatCurrency(capitalAtRisk)}</div>
          <Separator className="my-3" />
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Exposure</span>
              <span className="font-mono">
                {totalEquity > 0 ? ((capitalAtRisk / totalEquity) * 100).toFixed(1) : 0}%
              </span>
            </div>
            <Progress
              value={totalEquity > 0 ? (capitalAtRisk / totalEquity) * 100 : 0}
              className="h-1.5 bg-muted"
            />
          </div>
        </CardContent>
      </Card>

      <Card className="border">
        <CardHeader className="pb-3">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Pending Settlement</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold tabular-nums">{formatCurrency(pendingSettlement)}</div>
          <Separator className="my-3" />
          <div className="text-xs text-muted-foreground">
            {pendingSettlement > 0 ? (
              <span className="font-mono">0 events</span>
            ) : (
              <span>—</span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

