'use client';

import { useEffect, useState, useMemo } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Info, TrendingUp, TrendingDown, DollarSign, PieChart, Lock, Unlock } from 'lucide-react';
import { Strategy } from '@/types/strategy';
import { LineChart, Line, AreaChart, Area, PieChart as RechartsPie, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';

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
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | 'all'>('30d');

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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
                  <span className="font-mono">
                    {positions.filter(p => p.resolved && !p.payout).length} events
                  </span>
                ) : (
                  <span>—</span>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 2. Capital Allocation by Strategy */}
        <Card>
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

        {/* 3. PnL Breakdown by Strategy */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold">PnL Breakdown by Strategy</CardTitle>
            <CardDescription className="text-xs">Performance and return on investment metrics</CardDescription>
          </CardHeader>
          <CardContent>
            {strategyCapital.length === 0 ? (
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
                  {strategyCapital.map((sc) => (
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

        {/* 6. Equity Curve */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1">
                <CardTitle className="text-h3">Equity Curve</CardTitle>
                <CardDescription className="text-caption mt-1">Capital evolution over time</CardDescription>
              </div>
              <Select value={timeRange} onValueChange={(value: any) => setTimeRange(value)}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7d">Last 7 days</SelectItem>
                  <SelectItem value="30d">Last 30 days</SelectItem>
                  <SelectItem value="90d">Last 90 days</SelectItem>
                  <SelectItem value="all">All time</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {equityHistory.length > 0 && (
              <div className="grid grid-cols-3 gap-4 mt-4">
                <div>
                  <div className="text-caption">Current</div>
                  <div className="text-h3">{formatCurrency(equityHistory[equityHistory.length - 1]?.equity || 0)}</div>
                </div>
                <div>
                  <div className="text-caption">Change</div>
                  <div className={`text-h3 ${
                    (equityHistory[equityHistory.length - 1]?.equity - equityHistory[0]?.equity) >= 0
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}>
                    {(equityHistory[equityHistory.length - 1]?.equity - equityHistory[0]?.equity) >= 0 ? '+' : ''}
                    {formatPercent(
                      ((equityHistory[equityHistory.length - 1]?.equity - equityHistory[0]?.equity) /
                        equityHistory[0]?.equity) * 100
                    )}
                  </div>
                </div>
                <div>
                  <div className="text-caption">Peak</div>
                  <div className="text-h3">{formatCurrency(Math.max(...equityHistory.map(p => p.equity)))}</div>
                </div>
              </div>
            )}
          </CardHeader>
          <CardContent>
            {equityHistory.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground text-sm">
                <p>No historical data available</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart
                  data={equityHistory.map(point => ({
                    date: new Date(point.timestamp).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric'
                    }),
                    equity: point.equity,
                  }))}
                  margin={{ top: 5, right: 5, left: 0, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis
                    dataKey="date"
                    stroke="hsl(var(--muted-foreground))"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    dy={10}
                  />
                  <YAxis
                    stroke="hsl(var(--muted-foreground))"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                    dx={-10}
                  />
                  <RechartsTooltip
                    formatter={(value: number) => [formatCurrency(value), 'Equity']}
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                      fontSize: '11px',
                      padding: '8px 12px'
                    }}
                    labelStyle={{
                      color: 'hsl(var(--muted-foreground))',
                      fontSize: '11px',
                      marginBottom: '4px'
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="equity"
                    stroke="hsl(var(--foreground))"
                    strokeWidth={1.5}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
