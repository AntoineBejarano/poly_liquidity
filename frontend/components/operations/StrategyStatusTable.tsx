'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { StrategyTableSkeleton } from '@/components/ui/skeleton';
import { Strategy } from '@/types/strategy';
import Link from 'next/link';
import { CheckCircle2, Clock, AlertTriangle, AlertCircle, ExternalLink } from 'lucide-react';

interface StrategyStatus {
  strategyId: string;
  strategyName: string;
  strategyType: string;
  status: 'running' | 'paused' | 'degraded' | 'error';
  currentExposure: number;
  activeAlertsCount: number;
  lastActivity: string | null;
}

interface StrategyStatusData {
  strategies: Strategy[];
  strategyStatuses: StrategyStatus[];
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'running':
      return <Badge variant="success" className="gap-1"><CheckCircle2 className="h-3 w-3" /> Running</Badge>;
    case 'paused':
      return <Badge variant="default" className="gap-1"><Clock className="h-3 w-3" /> Paused</Badge>;
    case 'degraded':
      return <Badge variant="warning" className="gap-1"><AlertTriangle className="h-3 w-3" /> Degraded</Badge>;
    case 'error':
      return <Badge variant="error" className="gap-1"><AlertCircle className="h-3 w-3" /> Error</Badge>;
    default:
      return <Badge variant="default">{status}</Badge>;
  }
}

function formatTimeAgo(timestamp: string | null) {
  if (!timestamp) return '—';
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export function StrategyStatusTable() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const { isDemo } = useDataMode();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<StrategyStatusData>({
    fetchFn: async () => {
      if (!user || !stackApp) {
        throw new Error('User not authenticated');
      }
      if (isDemo) {
        return { strategies: [], strategyStatuses: [] };
      }
      if (!isConnected) {
        return { strategies: [], strategyStatuses: [] };
      }
      const api = initApiClient(createTokenGetter(user, stackApp));
      const strategiesData = await api.get<Strategy[]>('/api/strategies');

      // Build strategy statuses
      const statuses: StrategyStatus[] = strategiesData.map((strategy) => {
        let strategyType = 'Custom';
        if (strategy.tags?.includes('surebet') || strategy.name.toLowerCase().includes('surebet')) {
          strategyType = 'Surebet';
        } else if (strategy.tags?.includes('liquidity') || strategy.name.toLowerCase().includes('liquidity')) {
          strategyType = 'Liquidity NR';
        } else if (strategy.tags?.includes('value') || strategy.name.toLowerCase().includes('value')) {
          strategyType = 'Value';
        }

        let status: 'running' | 'paused' | 'degraded' | 'error' = 'paused';
        if (strategy.is_active) {
          status = 'running';
        } else if (strategy.disabled_at) {
          status = 'error';
        }

        const currentExposure = 0; // TODO: Get from strategy metrics
        const activeAlertsCount = 0; // TODO: Count alerts for this strategy
        const lastActivity = strategy.updated_at || null;

        return {
          strategyId: strategy.id,
          strategyName: strategy.name,
          strategyType,
          status,
          currentExposure,
          activeAlertsCount,
          lastActivity,
        };
      });

      return {
        strategies: strategiesData,
        strategyStatuses: statuses,
      };
    },
    dependencies: [user, stackApp, isConnected, isDemo],
    refreshInterval: isDemo ? 0 : 10000,
    enabled: !!user && !!stackApp && (isConnected || isDemo),
    showSkeleton: true,
    skeletonComponent: () => (
      <Card>
        <CardHeader>
          <CardTitle>Active Strategies Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <StrategyTableSkeleton rows={5} columns={7} />
        </CardContent>
      </Card>
    ),
    showRefreshingIndicator: true,
  });

  if (renderSkeleton) {
    return <>{renderSkeleton}</>;
  }

  const strategyStatuses = data?.strategyStatuses || [];

  return (
    <Card className="relative">
      {renderRefreshingIndicator}
      <CardHeader>
        <CardTitle>Active Strategies Overview</CardTitle>
      </CardHeader>
      <CardContent>
        {strategyStatuses.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>No hay estrategias configuradas</p>
            <p className="text-xs mt-1">Las estrategias activas aparecerán aquí</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Strategy</TableHead>
                <TableHead className="hidden sm:table-cell">Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="hidden sm:table-cell text-right">Exposure</TableHead>
                <TableHead className="hidden sm:table-cell text-right">Alerts</TableHead>
                <TableHead className="hidden sm:table-cell">Last Activity</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {strategyStatuses.map((status) => (
                <TableRow key={status.strategyId}>
                  <TableCell className="font-medium">
                    <div>{status.strategyName}</div>
                    <div className="sm:hidden text-xs text-muted-foreground mt-1 space-y-0.5">
                      <div>Type: {status.strategyType}</div>
                      <div>Last: {formatTimeAgo(status.lastActivity)}</div>
                      <div>Alerts: {status.activeAlertsCount || '—'}</div>
                    </div>
                  </TableCell>
                  <TableCell className="hidden sm:table-cell">
                    <Badge variant="outline">{status.strategyType}</Badge>
                  </TableCell>
                  <TableCell>{getStatusBadge(status.status)}</TableCell>
                  <TableCell className="hidden sm:table-cell text-right">
                    {status.currentExposure > 0 ? `$${status.currentExposure.toLocaleString()}` : '—'}
                  </TableCell>
                  <TableCell className="hidden sm:table-cell text-right">
                    {status.activeAlertsCount > 0 ? (
                      <Badge variant="error">{status.activeAlertsCount}</Badge>
                    ) : (
                      '—'
                    )}
                  </TableCell>
                  <TableCell className="hidden sm:table-cell text-muted-foreground text-sm">
                    {formatTimeAgo(status.lastActivity)}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" asChild>
                      <Link href={`/strategies/${status.strategyId}/live`}>
                        <span className="hidden sm:inline">Live Control</span>
                        <ExternalLink className="h-3 w-3 ml-1" />
                      </Link>
                    </Button>
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

