'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertTriangle, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

interface RiskMonitorProps {
  currentExposure: number;
  maxExposure: number;
  capitalUsed: number;
  capitalAssigned: number;
  activeEvents: number;
  alerts: Array<{
    id: string;
    type: 'warning' | 'critical';
    message: string;
  }>;
}

export function RiskMonitor({
  currentExposure,
  maxExposure,
  capitalUsed,
  capitalAssigned,
  activeEvents,
  alerts,
}: RiskMonitorProps) {
  const exposurePercent = maxExposure > 0 ? (currentExposure / maxExposure) * 100 : 0;
  const capitalPercent = capitalAssigned > 0 ? (capitalUsed / capitalAssigned) * 100 : 0;

  const getExposureColor = (percent: number) => {
    if (percent >= 90) return 'text-red-600';
    if (percent >= 75) return 'text-yellow-600';
    return 'text-green-600';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Monitor de Riesgo
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Exposure */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Exposición Actual</span>
            <span className={cn("text-sm font-semibold", getExposureColor(exposurePercent))}>
              ${currentExposure.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} / ${maxExposure.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <Progress value={Math.min(exposurePercent, 100)} className="h-2" />
          <div className="text-xs text-muted-foreground mt-1">
            {exposurePercent.toFixed(1)}% del límite máximo
          </div>
        </div>

        {/* Capital */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Capital Usado</span>
            <span className="text-sm font-semibold">
              ${capitalUsed.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} / ${capitalAssigned.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <Progress value={Math.min(capitalPercent, 100)} className="h-2" />
          <div className="text-xs text-muted-foreground mt-1">
            {capitalPercent.toFixed(1)}% del capital asignado
          </div>
        </div>

        {/* Active Events */}
        <div className="grid grid-cols-3 gap-4 p-4 bg-muted rounded-lg">
          <div>
            <div className="text-xs text-muted-foreground">Eventos Activos</div>
            <div className="text-lg font-semibold">{activeEvents}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Exposición Promedio</div>
            <div className="text-lg font-semibold">
              ${activeEvents > 0 ? (currentExposure / activeEvents).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Capital Disponible</div>
            <div className="text-lg font-semibold text-green-600">
              ${Math.max(0, capitalAssigned - capitalUsed).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
        </div>

        {/* Alerts */}
        {alerts.length > 0 && (
          <div className="space-y-2">
            {alerts.map((alert) => (
              <Alert 
                key={alert.id} 
                variant={alert.type === 'critical' ? 'destructive' : 'default'}
              >
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{alert.message}</AlertDescription>
              </Alert>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

