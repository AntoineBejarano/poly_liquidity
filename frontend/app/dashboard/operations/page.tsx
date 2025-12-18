'use client';

import { useEffect, useState, useMemo } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Strategy } from '@/types/strategy';
import Link from 'next/link';
import { 
  AlertTriangle, 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  ExternalLink,
  Activity,
  TrendingUp
} from 'lucide-react';

interface StrategyStatus {
  strategyId: string;
  strategyName: string;
  strategyType: string;
  status: 'running' | 'paused' | 'degraded' | 'error';
  currentExposure: number;
  activeAlertsCount: number;
  lastActivity: string | null;
}

interface OperationalAlert {
  id: string;
  strategyId: string;
  strategyName: string;
  severity: 'warning' | 'error' | 'critical';
  message: string;
  timestamp: string;
}

interface InfrastructureHealth {
  polymarket: { status: 'ok' | 'degraded' | 'error'; latency?: number; lastUpdate?: string };
  pinnacle: { status: 'ok' | 'degraded' | 'error'; latency?: number; lastUpdate?: string };
  checkers: { active: number; total: number; lastFailure?: string };
  dataFreshness: { status: 'fresh' | 'stale' | 'error'; age?: string };
}

interface ValuesSnapshot {
  activeSignals: number;
  executableSignals: number;
  bestEdge: number | null;
  feedStatus: 'ok' | 'degraded' | 'error';
}

export default function OperationsDashboardPage() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [strategyStatuses, setStrategyStatuses] = useState<StrategyStatus[]>([]);
  const [operationalAlerts, setOperationalAlerts] = useState<OperationalAlert[]>([]);
  const [infrastructureHealth, setInfrastructureHealth] = useState<InfrastructureHealth | null>(null);
  const [valuesSnapshot, setValuesSnapshot] = useState<ValuesSnapshot | null>(null);
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
        
        // Fetch strategies
        const strategiesData = await api.get<Strategy[]>('/strategies');
        setStrategies(strategiesData);

        // Fetch live status for operational data
        const liveStatus = await api.get<any>('/live/status').catch(() => null);

        // Build strategy statuses
        const statuses: StrategyStatus[] = strategiesData.map((strategy) => {
          // Determine strategy type from tags or name
          let strategyType = 'Custom';
          if (strategy.tags?.includes('surebet') || strategy.name.toLowerCase().includes('surebet')) {
            strategyType = 'Surebet';
          } else if (strategy.tags?.includes('liquidity') || strategy.name.toLowerCase().includes('liquidity')) {
            strategyType = 'Liquidity NR';
          } else if (strategy.tags?.includes('value') || strategy.name.toLowerCase().includes('value')) {
            strategyType = 'Value';
          }

          // Determine status
          let status: 'running' | 'paused' | 'degraded' | 'error' = 'paused';
          if (strategy.is_active) {
            status = 'running';
            // TODO: Check for degraded/error states from live status
          } else if (strategy.disabled_at) {
            status = 'error';
          }

          // Mock exposure and alerts (TODO: Get from actual data)
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

        setStrategyStatuses(statuses);

        // Build operational alerts from live status
        const alerts: OperationalAlert[] = [];
        if (liveStatus?.risk_alerts) {
          liveStatus.risk_alerts.forEach((alert: any, idx: number) => {
            if (alert.severity === 'warning' || alert.severity === 'error' || alert.severity === 'critical') {
              alerts.push({
                id: `alert-${idx}`,
                strategyId: '', // TODO: Map to strategy if available
                strategyName: 'System', // TODO: Get actual strategy name
                severity: alert.severity,
                message: alert.message,
                timestamp: new Date().toISOString(), // TODO: Get actual timestamp
              });
            }
          });
        }
        setOperationalAlerts(alerts);

        // Build infrastructure health (mock for now)
        setInfrastructureHealth({
          polymarket: {
            status: 'ok',
            latency: 45,
            lastUpdate: new Date().toISOString(),
          },
          pinnacle: {
            status: 'ok',
            latency: 120,
            lastUpdate: new Date().toISOString(),
          },
          checkers: {
            active: liveStatus?.system_health?.checkers_active || 0,
            total: liveStatus?.system_health?.checkers_total || 0,
          },
          dataFreshness: {
            status: 'fresh',
            age: '< 5s',
          },
        });

        // Build values snapshot (mock for now)
        setValuesSnapshot({
          activeSignals: 0, // TODO: Get from values API
          executableSignals: 0,
          bestEdge: null,
          feedStatus: 'ok',
        });

        setError(null);
      } catch (err) {
        console.error('Error fetching operations data:', err);
        setError(err instanceof Error ? err.message : 'Error al cargar datos operativos');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    
    // Refresh data every 5 seconds for near-real-time updates
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [user, stackApp, isConnected]);

  // Calculate strategy state distribution
  const stateDistribution = useMemo(() => {
    const running = strategyStatuses.filter(s => s.status === 'running').length;
    const paused = strategyStatuses.filter(s => s.status === 'paused').length;
    const error = strategyStatuses.filter(s => s.status === 'error').length;
    const degraded = strategyStatuses.filter(s => s.status === 'degraded').length;
    return { running, paused, error, degraded, total: strategyStatuses.length };
  }, [strategyStatuses]);

  const getStatusBadge = (status: string) => {
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
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      default:
        return <AlertTriangle className="h-4 w-4" />;
    }
  };

  const formatTimeAgo = (timestamp: string | null) => {
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
  };

  if (!user) {
    return null;
  }

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner fullScreen text="Cargando operations dashboard..." />
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6 w-full max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Operations Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Centro de control operativo: estrategias activas, alertas y salud del sistema
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={isConnected ? 'success' : 'error'}>
              {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </Badge>
          </div>
        </div>

        {/* 2. Operational Alerts (High Priority) */}
        {operationalAlerts.length > 0 && (
          <Card className="border-l-4 border-l-red-500">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-red-600" />
                Operational Alerts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {operationalAlerts.map((alert) => (
                  <Alert 
                    key={alert.id}
                    variant={alert.severity === 'critical' ? 'destructive' : 'default'}
                    className="flex items-start justify-between"
                  >
                    <div className="flex items-start gap-3 flex-1">
                      {getSeverityIcon(alert.severity)}
                      <div className="flex-1">
                        <AlertTitle className="flex items-center gap-2">
                          {alert.strategyName}
                          <Badge variant={alert.severity === 'critical' ? 'error' : alert.severity === 'error' ? 'error' : 'warning'}>
                            {alert.severity.toUpperCase()}
                          </Badge>
                        </AlertTitle>
                        <AlertDescription className="mt-1">
                          {alert.message}
                          <span className="text-xs text-muted-foreground ml-2">
                            {formatTimeAgo(alert.timestamp)}
                          </span>
                        </AlertDescription>
                      </div>
                    </div>
                    {alert.strategyId && (
                      <Button variant="ghost" size="sm" asChild>
                        <Link href={`/strategies/${alert.strategyId}/live`}>
                          Go to Live Control
                          <ExternalLink className="h-3 w-3 ml-1" />
                        </Link>
                      </Button>
                    )}
                  </Alert>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* 5. Strategy State Distribution (Quick Visual) */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{stateDistribution.running}</div>
                <div className="text-xs text-muted-foreground mt-1">Running</div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-600">{stateDistribution.paused}</div>
                <div className="text-xs text-muted-foreground mt-1">Paused</div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">{stateDistribution.degraded}</div>
                <div className="text-xs text-muted-foreground mt-1">Degraded</div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{stateDistribution.error}</div>
                <div className="text-xs text-muted-foreground mt-1">Error</div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 1. Active Strategies Overview */}
        <Card>
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
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Exposure</TableHead>
                    <TableHead className="text-right">Alerts</TableHead>
                    <TableHead>Last Activity</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {strategyStatuses.map((status) => (
                    <TableRow key={status.strategyId}>
                      <TableCell className="font-medium">{status.strategyName}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{status.strategyType}</Badge>
                      </TableCell>
                      <TableCell>{getStatusBadge(status.status)}</TableCell>
                      <TableCell className="text-right">
                        {status.currentExposure > 0 ? `$${status.currentExposure.toLocaleString()}` : '—'}
                      </TableCell>
                      <TableCell className="text-right">
                        {status.activeAlertsCount > 0 ? (
                          <Badge variant="error">{status.activeAlertsCount}</Badge>
                        ) : (
                          '—'
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {formatTimeAgo(status.lastActivity)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" asChild>
                          <Link href={`/strategies/${status.strategyId}/live`}>
                            Live Control
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

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 3. Infrastructure Health */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Infrastructure Health
              </CardTitle>
            </CardHeader>
            <CardContent>
              {infrastructureHealth ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Polymarket API</span>
                    <div className="flex items-center gap-2">
                      <Badge variant={infrastructureHealth.polymarket.status === 'ok' ? 'success' : 'error'}>
                        {infrastructureHealth.polymarket.status === 'ok' ? 'OK' : infrastructureHealth.polymarket.status}
                      </Badge>
                      {infrastructureHealth.polymarket.latency && (
                        <span className="text-xs text-muted-foreground">
                          {infrastructureHealth.polymarket.latency}ms
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Pinnacle API</span>
                    <div className="flex items-center gap-2">
                      <Badge variant={infrastructureHealth.pinnacle.status === 'ok' ? 'success' : 'error'}>
                        {infrastructureHealth.pinnacle.status === 'ok' ? 'OK' : infrastructureHealth.pinnacle.status}
                      </Badge>
                      {infrastructureHealth.pinnacle.latency && (
                        <span className="text-xs text-muted-foreground">
                          {infrastructureHealth.pinnacle.latency}ms
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Checkers</span>
                    <div className="flex items-center gap-2">
                      <Badge variant={infrastructureHealth.checkers.active === infrastructureHealth.checkers.total ? 'success' : 'warning'}>
                        {infrastructureHealth.checkers.active}/{infrastructureHealth.checkers.total}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Data Freshness</span>
                    <Badge variant={infrastructureHealth.dataFreshness.status === 'fresh' ? 'success' : 'warning'}>
                      {infrastructureHealth.dataFreshness.age || infrastructureHealth.dataFreshness.status}
                    </Badge>
                  </div>
                </div>
              ) : (
                <div className="text-center py-4 text-muted-foreground text-sm">—</div>
              )}
            </CardContent>
          </Card>

          {/* 4. Execution Input Signals (Values Snapshot) */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Execution Input Signals
              </CardTitle>
            </CardHeader>
            <CardContent>
              {valuesSnapshot ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Active Signals</span>
                    <span className="text-lg font-semibold">{valuesSnapshot.activeSignals}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Executable Signals</span>
                    <span className="text-lg font-semibold">{valuesSnapshot.executableSignals}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Best Current Edge</span>
                    <span className="text-lg font-semibold">
                      {valuesSnapshot.bestEdge !== null ? `${valuesSnapshot.bestEdge.toFixed(2)}%` : '—'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
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
              ) : (
                <div className="text-center py-4 text-muted-foreground text-sm">—</div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
}
