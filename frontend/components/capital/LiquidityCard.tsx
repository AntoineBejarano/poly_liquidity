'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CardSkeleton } from '@/components/ui/skeleton';

interface DashboardData {
  equity: number;
  realized_pnl: number;
  unrealized_pnl: number;
  global_exposure: number;
  active_markets: number;
  system_active: boolean;
}

interface Position {
  market_id: string;
  polymarket_id: string;
  question: string;
  size: number;
  avg_price: number;
  current_price: number;
  unrealized_pnl: number;
  resolved: boolean;
  payout: number | null;
  resolved_at?: string | null;
  created_at?: string | null;
}

interface LiquidityData {
  dashboard: DashboardData;
  positions: Position[];
}

function formatCurrency(value: number) {
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function LiquidityCard() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<LiquidityData>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected) {
        throw new Error('User not authenticated or backend not connected');
      }
      const api = initApiClient(createTokenGetter(user, stackApp));

      const [dashboard, positionsData] = await Promise.all([
        api.get<DashboardData>('/dashboard'),
        api.get<Position[]>('/positions?resolved=false').catch(() => []),
      ]);

      return {
        dashboard,
        positions: positionsData,
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

  if (!data) {
    return null;
  }

  const totalEquity = data.dashboard.equity || 0;
  const capitalAtRisk = data.dashboard.global_exposure || 0;
  const availableLiquidity = totalEquity - capitalAtRisk;

  // Calculate pending settlement
  const pendingSettlement = data.positions
    .filter((pos) => pos.resolved && !pos.payout)
    .reduce((sum, pos) => sum + (pos.size * pos.avg_price), 0);

  const lockedCapital = {
    inPositions: capitalAtRisk,
    pendingSettlement,
    total: capitalAtRisk + pendingSettlement,
  };

  // Estimate time to full liquidity
  const estimatedTimeToLiquidity = data.positions.length > 0 ? '2-4 hours' : 'Immediate';

  return (
    <Card className="relative">
      {renderRefreshingIndicator}
      <CardHeader>
        <CardTitle>Liquidity & Cash-Out</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <div className="text-sm font-medium text-muted-foreground mb-2">Withdrawable Now</div>
            <div className="text-2xl font-bold">{formatCurrency(availableLiquidity)}</div>
            <div className="text-xs text-muted-foreground mt-1">
              Capital disponible inmediatamente para retiro
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-muted-foreground mb-2">Locked Capital</div>
            <div className="text-2xl font-bold">{formatCurrency(lockedCapital.total)}</div>
            <div className="text-xs text-muted-foreground mt-1">
              En posiciones: {formatCurrency(lockedCapital.inPositions)}<br />
              Pendiente: {formatCurrency(lockedCapital.pendingSettlement)}
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-muted-foreground mb-2">Estimated Time to Full Liquidity</div>
            <div className="text-2xl font-bold">{estimatedTimeToLiquidity}</div>
            <div className="text-xs text-muted-foreground mt-1">
              Tiempo estimado hasta que todo el capital esté disponible
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

