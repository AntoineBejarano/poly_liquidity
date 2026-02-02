'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
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

interface StrategyCapital {
  strategyId: string;
  strategyName: string;
  capitalAssigned: number;
  capitalInUse: number;
  capitalFree: number;
  percentOfTotal: number;
}

interface CapitalAllocationData {
  dashboard: DashboardData;
  strategies: Strategy[];
  positions: any[];
  strategyMetrics: Record<string, any>;
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

export function CapitalAllocationTable() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const { isDemo } = useDataMode();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<CapitalAllocationData>({
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
      const metricsPromises = (strategiesData ?? []).map(async (strategy) => {
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
        strategies: strategiesData ?? [],
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
          <CardTitle className="text-sm font-semibold">Capital Allocation by Strategy</CardTitle>
        </CardHeader>
        <CardContent>
          <StrategyTableSkeleton rows={5} columns={5} />
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

  // Calculate capital allocation by strategy
  const strategyCapital: StrategyCapital[] = data.strategies.map((strategy) => {
    const strategyPositions = data.positions.filter((pos) => {
      // TODO: Match positions to strategy by event assignment
      return true; // For now, show all positions
    });

    const capitalInUse = strategyPositions.reduce((sum, pos) => sum + (pos.size * pos.avg_price), 0);
    const capitalAssigned = 10000; // Mock - should come from strategy.risk_config
    const capitalFree = Math.max(0, capitalAssigned - capitalInUse);

    return {
      strategyId: strategy.id,
      strategyName: strategy.name,
      capitalAssigned,
      capitalInUse,
      capitalFree,
      percentOfTotal: data.dashboard.equity > 0 ? (capitalAssigned / data.dashboard.equity) * 100 : 0,
    };
  });

  return (
    <Card className="relative">
      {renderRefreshingIndicator}
      <CardHeader>
        <CardTitle className="text-sm font-semibold">Capital Allocation by Strategy</CardTitle>
        <CardDescription className="text-xs">Distribution of assigned capital across active strategies</CardDescription>
      </CardHeader>
      <CardContent>
        {strategyCapital.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground text-sm">
            <p>No strategies configured</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-b">
                <TableHead className="font-medium">Strategy</TableHead>
                <TableHead className="text-right font-medium">Assigned</TableHead>
                <TableHead className="text-right font-medium">In Use</TableHead>
                <TableHead className="text-right font-medium">Free</TableHead>
                <TableHead className="text-right font-medium">Util %</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {strategyCapital.map((sc) => (
                <TableRow key={sc.strategyId} className="border-b">
                  <TableCell className="font-medium">{sc.strategyName}</TableCell>
                  <TableCell className="text-right font-mono text-sm">{formatCurrency(sc.capitalAssigned)}</TableCell>
                  <TableCell className="text-right">
                    <div className="space-y-1.5">
                      <div className="font-mono text-sm">{formatCurrency(sc.capitalInUse)}</div>
                      <div className="flex items-center gap-2">
                        <Progress
                          value={sc.capitalAssigned > 0 ? (sc.capitalInUse / sc.capitalAssigned) * 100 : 0}
                          className="h-1 flex-1 bg-muted"
                        />
                        <span className="text-xs text-muted-foreground font-mono w-10 text-right">
                          {sc.capitalAssigned > 0 ? ((sc.capitalInUse / sc.capitalAssigned) * 100).toFixed(0) : 0}%
                        </span>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm">{formatCurrency(sc.capitalFree)}</TableCell>
                  <TableCell className="text-right font-mono text-sm">{sc.percentOfTotal.toFixed(1)}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

