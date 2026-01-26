'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { CardSkeleton } from '@/components/ui/skeleton';
import Link from 'next/link';
import { AlertCircle, AlertTriangle, ExternalLink } from 'lucide-react';

interface OperationalAlert {
  id: string;
  strategyId: string;
  strategyName: string;
  severity: 'warning' | 'error' | 'critical';
  message: string;
  timestamp: string;
}

interface OperationalAlertsData {
  operationalAlerts: OperationalAlert[];
}

function getSeverityIcon(severity: string) {
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

export function OperationalAlertsList() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<OperationalAlertsData>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected) {
        throw new Error('User not authenticated or backend not connected');
      }

      const api = initApiClient(createTokenGetter(user, stackApp));
      const liveStatus = await api.get<any>('/live/status').catch(() => null);

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

      return {
        operationalAlerts: alerts,
      };
    },
    dependencies: [user, stackApp, isConnected],
    refreshInterval: 5000,
    enabled: !!user && !!stackApp && isConnected,
    showSkeleton: false, // No mostrar skeleton si no hay alerts
    showRefreshingIndicator: true,
  });

  const operationalAlerts = data?.operationalAlerts || [];

  // No mostrar nada si no hay alerts
  if (operationalAlerts.length === 0) {
    return null;
  }

  return (
    <Card className="relative border-l-4 border-l-red-500 dark:border-l-red-600">
      {renderRefreshingIndicator}
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-500" />
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
  );
}

