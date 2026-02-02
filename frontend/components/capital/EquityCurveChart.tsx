'use client';

import { useState } from 'react';
import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import { CustomChartTooltip } from '@/components/charts/CustomChartTooltip';

interface EquityPoint {
  timestamp: string;
  equity: number;
}

function formatCurrency(value: number) {
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPercent(value: number) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

export function EquityCurveChart() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const { isDemo } = useDataMode();
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | 'all'>('30d');

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<{ data: EquityPoint[] }>({
    fetchFn: async () => {
      if (!user || !stackApp) {
        throw new Error('User not authenticated');
      }
      if (isDemo) {
        return { data: [] };
      }
      if (!isConnected) {
        return { data: [] };
      }
      const api = initApiClient(createTokenGetter(user, stackApp));
      const historyResponse = await api.get<{ data: EquityPoint[] }>(`/history/equity?range=${timeRange}`);
      return historyResponse ?? { data: [] };
    },
    dependencies: [user, stackApp, isConnected, isDemo, timeRange],
    enabled: !!user && !!stackApp && (isConnected || isDemo),
    showSkeleton: false, // No mostrar skeleton completo, solo el chart
    showRefreshingIndicator: true,
  });

  const equityHistory = data?.data || [];

  return (
    <Card className="relative">
      {renderRefreshingIndicator}
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
            <Skeleton className="h-64 w-full" />
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
                content={<CustomChartTooltip 
                  valueFormatter={formatCurrency}
                  labelFormatter={(label) => label}
                />}
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
  );
}

