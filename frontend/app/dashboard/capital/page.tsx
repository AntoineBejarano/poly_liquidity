'use client';

import { useEffect, useState, useMemo } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Info } from 'lucide-react';
import { Strategy } from '@/types/strategy';

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

interface StrategyCapital {
  strategyId: string;
  strategyName: string;
  capitalAssigned: number;
  capitalInUse: number;
  capitalFree: number;
  percentOfTotal: number;
  realizedPnL: number;
  unrealizedPnL: number;
  totalPnL: number;
  roi: number;
  tradeCount: number;
}

interface EquityPoint {
  timestamp: string;
  equity: number;
}

export default function CapitalDashboardPage() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [strategyMetrics, setStrategyMetrics] = useState<Record<string, any>>({});
  const [equityHistory, setEquityHistory] = useState<EquityPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user || !isConnected) {
      setLoading(false);
      return;
    }

    const api = initApiClient(createTokenGetter(user, stackApp));

    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Fetch all data in parallel
        const [dashboard, strategiesData, positionsData] = await Promise.all([
          api.get<DashboardData>('/dashboard'),
          api.get<Strategy[]>('/strategies'),
          api.get<Position[]>('/positions?resolved=false').catch(() => []),
        ]);

        setDashboardData(dashboard);
        setStrategies(strategiesData);
        setPositions(positionsData);

        // Fetch metrics for each strategy
        const metricsPromises = strategiesData.map(async (strategy) => {
          try {
            const metrics = await api.get<any>(`/strategies/${strategy.id}/metrics`);
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
        setStrategyMetrics(metricsMap);

        // Mock equity history (TODO: Replace with real endpoint)
        const mockHistory: EquityPoint[] = [];
        const now = new Date();
        for (let i = 30; i >= 0; i--) {
          const date = new Date(now);
          date.setDate(date.getDate() - i);
          mockHistory.push({
            timestamp: date.toISOString(),
            equity: dashboard.equity + (Math.random() * 1000 - 500),
          });
        }
        setEquityHistory(mockHistory);

        setError(null);
      } catch (err) {
        console.error('Error fetching capital data:', err);
        setError(err instanceof Error ? err.message : 'Error al cargar datos de capital');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    
    // Refresh data every 10 seconds
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [user, stackApp, isConnected]);

  // Calculate capital allocation by strategy
  const strategyCapital = useMemo<StrategyCapital[]>(() => {
    if (!dashboardData || !strategies.length) return [];

    return strategies.map((strategy) => {
      // Get strategy positions
      const strategyPositions = positions.filter((pos) => {
        // TODO: Match positions to strategy by event assignment
        return true; // For now, show all positions
      });

      // Calculate capital in use from positions
      const capitalInUse = strategyPositions.reduce((sum, pos) => sum + (pos.size * pos.avg_price), 0);
      
      // Get capital assigned from strategy config (TODO: Get from actual config)
      const capitalAssigned = 10000; // Mock - should come from strategy.risk_config
      const capitalFree = Math.max(0, capitalAssigned - capitalInUse);

      // Calculate PnL from metrics
      const metrics = strategyMetrics[strategy.id] || [];
      const latestMetric = metrics[0] || {};
      const realizedPnL = latestMetric.total_pnl_usdc || 0;
      const unrealizedPnL = strategyPositions.reduce((sum, pos) => sum + (pos.unrealized_pnl || 0), 0);
      const totalPnL = realizedPnL + unrealizedPnL;
      const roi = capitalAssigned > 0 ? (totalPnL / capitalAssigned) * 100 : 0;
      const tradeCount = latestMetric.executed_intents || 0;

      return {
        strategyId: strategy.id,
        strategyName: strategy.name,
        capitalAssigned,
        capitalInUse,
        capitalFree,
        percentOfTotal: dashboardData.equity > 0 ? (capitalAssigned / dashboardData.equity) * 100 : 0,
        realizedPnL,
        unrealizedPnL,
        totalPnL,
        roi,
        tradeCount,
      };
    });
  }, [strategies, positions, dashboardData, strategyMetrics]);

  // Calculate aggregated metrics
  const totalEquity = dashboardData?.equity || 0;
  const totalRealizedPnL = dashboardData?.realized_pnl || 0;
  const totalUnrealizedPnL = dashboardData?.unrealized_pnl || 0;
  const capitalAtRisk = dashboardData?.global_exposure || 0;
  const availableLiquidity = totalEquity - capitalAtRisk;
  
  // Calculate pending settlement (positions waiting for resolution)
  const pendingSettlement = positions
    .filter((pos) => pos.resolved && !pos.payout)
    .reduce((sum, pos) => sum + (pos.size * pos.avg_price), 0);

  // Calculate locked capital reasons
  const lockedCapital = {
    inPositions: capitalAtRisk,
    pendingSettlement,
    total: capitalAtRisk + pendingSettlement,
  };

  // Estimate time to full liquidity (mock - should be calculated from event resolution dates)
  const estimatedTimeToLiquidity = positions.length > 0 ? '2-4 hours' : 'Immediate';

  if (!user) {
    return null;
  }

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner fullScreen text="Cargando capital dashboard..." />
      </Layout>
    );
  }

  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  return (
    <Layout>
      <div className="space-y-6 w-full max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Capital Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Centro financiero: capital, PnL, liquidez y asignación por estrategia
            </p>
          </div>
        </div>

        {/* 1. Capital Overview */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Capital Overview
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs">
                    <p>Vista agregada del capital total, liquidez disponible y capital comprometido</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-muted-foreground">Total Equity</span>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Info className="h-3 w-3 text-muted-foreground cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Capital inicial + PnL realizado + PnL no realizado</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <div className="text-2xl font-bold">{formatCurrency(totalEquity)}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  Base: {formatCurrency(totalEquity - totalRealizedPnL - totalUnrealizedPnL)}<br />
                  Realizado: {formatCurrency(totalRealizedPnL)}<br />
                  No realizado: {formatCurrency(totalUnrealizedPnL)}
                </div>
              </div>

              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-muted-foreground">Available Liquidity</span>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Info className="h-3 w-3 text-muted-foreground cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Capital libre para nuevas estrategias o cash-out</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <div className="text-2xl font-bold">{formatCurrency(availableLiquidity)}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {totalEquity > 0 ? ((availableLiquidity / totalEquity) * 100).toFixed(1) : 0}% del total
                </div>
              </div>

              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-muted-foreground">Capital at Risk</span>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Info className="h-3 w-3 text-muted-foreground cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Capital actualmente comprometido en posiciones abiertas</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <div className="text-2xl font-bold">{formatCurrency(capitalAtRisk)}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {totalEquity > 0 ? ((capitalAtRisk / totalEquity) * 100).toFixed(1) : 0}% del total
                </div>
              </div>

              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-muted-foreground">Pending Settlement</span>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Info className="h-3 w-3 text-muted-foreground cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Capital bloqueado esperando resolución de eventos (ej. Polymarket)</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <div className="text-2xl font-bold">{formatCurrency(pendingSettlement)}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {pendingSettlement > 0 ? `${positions.filter(p => p.resolved && !p.payout).length} eventos` : '—'}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 2. Capital Allocation by Strategy */}
        <Card>
          <CardHeader>
            <CardTitle>Capital Allocation by Strategy</CardTitle>
          </CardHeader>
          <CardContent>
            {strategyCapital.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p>No hay estrategias configuradas</p>
                <p className="text-xs mt-1">El capital asignado aparecerá aquí cuando crees estrategias</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Strategy</TableHead>
                    <TableHead className="text-right">Capital Assigned</TableHead>
                    <TableHead className="text-right">Capital In Use</TableHead>
                    <TableHead className="text-right">Capital Free</TableHead>
                    <TableHead className="text-right">% of Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {strategyCapital.map((sc) => (
                    <TableRow key={sc.strategyId}>
                      <TableCell className="font-medium">{sc.strategyName}</TableCell>
                      <TableCell className="text-right">{formatCurrency(sc.capitalAssigned)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(sc.capitalInUse)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(sc.capitalFree)}</TableCell>
                      <TableCell className="text-right">{sc.percentOfTotal.toFixed(1)}%</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* 3. PnL Breakdown by Strategy */}
        <Card>
          <CardHeader>
            <CardTitle>PnL Breakdown by Strategy</CardTitle>
          </CardHeader>
          <CardContent>
            {strategyCapital.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p>—</p>
                <p className="text-xs mt-1">No hay datos de PnL disponibles</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Strategy</TableHead>
                    <TableHead className="text-right">PnL Realized</TableHead>
                    <TableHead className="text-right">PnL Unrealized</TableHead>
                    <TableHead className="text-right">Total PnL</TableHead>
                    <TableHead className="text-right">ROI %</TableHead>
                    <TableHead className="text-right">Trades</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {strategyCapital.map((sc) => (
                    <TableRow key={sc.strategyId}>
                      <TableCell className="font-medium">{sc.strategyName}</TableCell>
                      <TableCell className={`text-right ${sc.realizedPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(sc.realizedPnL)}
                      </TableCell>
                      <TableCell className={`text-right ${sc.unrealizedPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(sc.unrealizedPnL)}
                      </TableCell>
                      <TableCell className={`text-right font-semibold ${sc.totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(sc.totalPnL)}
                      </TableCell>
                      <TableCell className={`text-right ${sc.roi >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatPercent(sc.roi)}
                      </TableCell>
                      <TableCell className="text-right">{sc.tradeCount}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* 4. Liquidity & Cash-Out */}
        <Card>
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

        {/* 5. Open Positions (Financial View) */}
        <Card>
          <CardHeader>
            <CardTitle>Open Positions</CardTitle>
          </CardHeader>
          <CardContent>
            {positions.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p>—</p>
                <p className="text-xs mt-1">No hay posiciones abiertas</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Strategy</TableHead>
                    <TableHead>Event / Market</TableHead>
                    <TableHead className="text-right">Capital Exposed</TableHead>
                    <TableHead className="text-right">Current PnL</TableHead>
                    <TableHead>Settlement Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {positions.map((pos) => (
                    <TableRow key={pos.market_id}>
                      <TableCell>—</TableCell>
                      <TableCell className="max-w-xs truncate">{pos.question || pos.polymarket_id}</TableCell>
                      <TableCell className="text-right">{formatCurrency(pos.size * pos.avg_price)}</TableCell>
                      <TableCell className={`text-right ${pos.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(pos.unrealized_pnl)}
                      </TableCell>
                      <TableCell>
                        {pos.resolved ? (
                          <span className="text-xs text-muted-foreground">Pending resolution</span>
                        ) : (
                          <span className="text-xs text-muted-foreground">Open</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* 6. Equity Curve (Compact) */}
        <Card>
          <CardHeader>
            <CardTitle>Equity Curve</CardTitle>
          </CardHeader>
          <CardContent>
            {equityHistory.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p>—</p>
                <p className="text-xs mt-1">No hay datos históricos disponibles</p>
              </div>
            ) : (
              <div className="h-64 flex items-end justify-between gap-1">
                {equityHistory.map((point, idx) => {
                  const maxEquity = Math.max(...equityHistory.map(p => p.equity));
                  const minEquity = Math.min(...equityHistory.map(p => p.equity));
                  const range = maxEquity - minEquity || 1;
                  const height = ((point.equity - minEquity) / range) * 100;
                  
                  return (
                    <div
                      key={idx}
                      className="flex-1 bg-primary/20 hover:bg-primary/40 transition-colors rounded-t"
                      style={{ height: `${height}%` }}
                      title={`${new Date(point.timestamp).toLocaleDateString()}: ${formatCurrency(point.equity)}`}
                    />
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
