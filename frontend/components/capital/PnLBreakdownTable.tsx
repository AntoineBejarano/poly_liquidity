'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { StrategyTableSkeleton } from '@/components/ui/skeleton';
import { Strategy } from '@/types/strategy';

interface DashboardData {
  equity: number;
  realized_pnl: number;
  unrealized_pnl: number;
  global_exposure: number;
  active_markets: number;
  system_active: boolean;
}

interface StrategyPnL {
  strategyId: string;
  strategyName: string;
  realizedPnL: number;
  unrealizedPnL: number;
  totalPnL: number;
  roi: number;
  tradeCount: number;
}

interface PnLData {
  dashboard: DashboardData;
  strategies: Strategy[];
  positions: any[];
  strategyMetrics: Record<string, any>;
}

function formatCurrency(value: number) {
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPercent(value: number) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

const EMPTY_DASHBOARD: DashboardData = {
  equity: 0,
  realized_pnl: 0,
  unrealized_pnl: 0,
  global_exposure: 0,
  active_markets: 0,
  system_active: false,
};

export function PnLBreakdownTable() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const { isDemo } = useDataMode();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<PnLData>({
    fetchFn: async () => {
      if (!user || !stackApp) {
        throw new Error('User not authenticated');
      }
      if (isDemo) {
        return {
          dashboard: EMPTY_DASHBOARD,
          strategies: [],
          positions: [],
          strategyMetrics: {},
        };
      }
      if (!isConnected) {
        return {
          dashboard: EMPTY_DASHBOARD,
          strategies: [],
          positions: [],
          strategyMetrics: {},
        };
      }
      const api = initApiClient(createTokenGetter(user, stackApp));

      const [dashboard, strategiesData, positionsData] = await Promise.all([
        api.get<DashboardData>('/dashboard'),
        api.get<Strategy[]>('/api/strategies'),
        api.get<any[]>('/positions?resolved=false').catch(() => []),
      ]);

      const strategies = strategiesData ?? [];
      // Fetch metrics for each strategy
      const metricsPromises = strategies.map(async (strategy) => {
        try {
          const metrics = await api.get<any>(`/api/strategies/${strategy.id}/metrics`);
          return { strategyId: strategy.id, metrics: metrics.metrics || [] };
        } catch {
          return { strategyId: strategy.id, metrics: [] };
        }
      });
      
      const metricsResults = await Promise.all(metricsPromises);
      const metricsMap: Record<string, any> = {};
      metricsResults.forEach(({ strategyId, metrics }) => {
        metricsMap[strategyId] = metrics;
      });

      return {
        dashboard: dashboard ?? EMPTY_DASHBOARD,
        strategies,
        positions: positionsData ?? [],
        strategyMetrics: metricsMap,
      };
    },
    dependencies: [user, stackApp, isConnected, isDemo],
    refreshInterval: isDemo ? 0 : 10000,
    enabled: !!user && !!stackApp && (isConnected || isDemo),
    showSkeleton: true,
    skeletonComponent: () => (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold">PnL Breakdown by Strategy</CardTitle>
        </CardHeader>
        <CardContent>
          <StrategyTableSkeleton rows={5} columns={6} />
        </CardContent>
      </Card>
    ),
    showRefreshingIndicator: true,
  });

  if (renderSkeleton) {
    return <>{renderSkeleton}</>;
  }

  if (!data) {
    return null;
  }

  // Calculate PnL by strategy
  const strategyPnL: StrategyPnL[] = data.strategies.map((strategy) => {
    const strategyPositions = data.positions.filter((pos) => {
      // TODO: Match positions to strategy by event assignment
      return true; // For now, show all positions
    });

    const metrics = data.strategyMetrics[strategy.id] || [];
    const latestMetric = metrics[0] || {};
    const realizedPnL = latestMetric.total_pnl_usdc || 0;
    const unrealizedPnL = strategyPositions.reduce((sum, pos) => sum + (pos.unrealized_pnl || 0), 0);
    const totalPnL = realizedPnL + unrealizedPnL;
    const capitalAssigned = 10000; // Mock
    const roi = capitalAssigned > 0 ? (totalPnL / capitalAssigned) * 100 : 0;
    const tradeCount = latestMetric.executed_intents || 0;

    return {
      strategyId: strategy.id,
      strategyName: strategy.name,
      realizedPnL,
      unrealizedPnL,
      totalPnL,
      roi,
      tradeCount,
    };
  });

  return (
    <Card className="relative">
      {renderRefreshingIndicator}
      <CardHeader>
        <CardTitle className="text-sm font-semibold">PnL Breakdown by Strategy</CardTitle>
        <CardDescription className="text-xs">Performance and return on investment metrics</CardDescription>
      </CardHeader>
      <CardContent>
        {strategyPnL.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground text-sm">
            <p>No PnL data available</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-b">
                <TableHead className="font-medium">Strategy</TableHead>
                <TableHead className="text-right font-medium">Realized</TableHead>
                <TableHead className="text-right font-medium">Unrealized</TableHead>
                <TableHead className="text-right font-medium">Total PnL</TableHead>
                <TableHead className="text-right font-medium">ROI</TableHead>
                <TableHead className="text-right font-medium">Trades</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {strategyPnL.map((sc) => (
                <TableRow key={sc.strategyId} className="border-b">
                  <TableCell className="font-medium">{sc.strategyName}</TableCell>
                  <TableCell className={`text-right font-mono text-sm ${sc.realizedPnL >= 0 ? '' : 'text-red-600'}`}>
                    {sc.realizedPnL >= 0 ? '+' : ''}{formatCurrency(sc.realizedPnL)}
                  </TableCell>
                  <TableCell className={`text-right font-mono text-sm ${sc.unrealizedPnL >= 0 ? '' : 'text-red-600'}`}>
                    {sc.unrealizedPnL >= 0 ? '+' : ''}{formatCurrency(sc.unrealizedPnL)}
                  </TableCell>
                  <TableCell className={`text-right font-mono font-semibold ${sc.totalPnL >= 0 ? '' : 'text-red-600'}`}>
                    {sc.totalPnL >= 0 ? '+' : ''}{formatCurrency(sc.totalPnL)}
                  </TableCell>
                  <TableCell className={`text-right font-mono text-sm ${sc.roi >= 0 ? '' : 'text-red-600'}`}>
                    {formatPercent(sc.roi)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm text-muted-foreground">{sc.tradeCount}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

