'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { StrategyTableSkeleton } from '@/components/ui/skeleton';

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

function formatCurrency(value: number) {
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function OpenPositionsTable() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<Position[]>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected) {
        throw new Error('User not authenticated or backend not connected');
      }
      const api = initApiClient(createTokenGetter(user, stackApp));
      return await api.get<Position[]>('/positions?resolved=false').catch(() => []);
    },
    dependencies: [user, stackApp, isConnected],
    refreshInterval: 10000,
    enabled: !!user && !!stackApp && isConnected,
    showSkeleton: true,
    skeletonComponent: () => (
      <Card>
        <CardHeader>
          <CardTitle>Open Positions</CardTitle>
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

  const positions = data || [];

  return (
    <Card className="relative">
      {renderRefreshingIndicator}
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
  );
}

