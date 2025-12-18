'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';

interface Alert {
  id: string;
  severity: 'warning' | 'error' | 'info';
  message: string;
  timestamp: string;
  valueId?: string;
}

interface ValueSignal {
  id: string;
  event: string;
  market: string;
}

interface SignalAlertsProps {
  alerts: Alert[];
  values: ValueSignal[];
}

export function SignalAlerts({ alerts, values }: SignalAlertsProps) {
  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'error':
        return <AlertCircle className="h-4 w-4" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4" />;
      default:
        return <Info className="h-4 w-4" />;
    }
  };

  const getSeverityVariant = (severity: string): 'default' | 'destructive' => {
    return severity === 'error' ? 'destructive' : 'default';
  };

  const getValueName = (valueId: string) => {
    const value = values.find(v => v.id === valueId);
    return value ? `${value.event} - ${value.market}` : valueId;
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  if (alerts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Active Signal Alerts
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-4 text-muted-foreground text-sm">
            No hay alertas activas
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5" />
          Active Signal Alerts
          <Badge variant="outline" className="ml-2">
            {alerts.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {alerts.map((alert) => (
          <Alert key={alert.id} variant={getSeverityVariant(alert.severity)}>
            <div className="flex items-start gap-2">
              {getSeverityIcon(alert.severity)}
              <div className="flex-1">
                <AlertDescription>
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-medium">{alert.message}</div>
                      {alert.valueId && (
                        <div className="text-xs text-muted-foreground mt-1">
                          Value: {getValueName(alert.valueId)}
                        </div>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground ml-4">
                      {formatTimestamp(alert.timestamp)}
                    </div>
                  </div>
                </AlertDescription>
              </div>
            </div>
          </Alert>
        ))}
      </CardContent>
    </Card>
  );
}

