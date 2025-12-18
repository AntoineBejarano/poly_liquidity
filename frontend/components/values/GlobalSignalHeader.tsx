'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity, AlertCircle, CheckCircle2, Clock } from 'lucide-react';

interface GlobalSignalState {
  activeValues: number;
  executableValues: number;
  degradedValues: number;
  lastRefresh: number;
  systemStatus: 'healthy' | 'partial-degradation' | 'signal-feed-compromised';
}

interface GlobalSignalHeaderProps {
  state: GlobalSignalState;
}

export function GlobalSignalHeader({ state }: GlobalSignalHeaderProps) {
  const getStatusBadge = () => {
    switch (state.systemStatus) {
      case 'healthy':
        return (
          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Healthy
          </Badge>
        );
      case 'partial-degradation':
        return (
          <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
            <AlertCircle className="h-3 w-3 mr-1" />
            Partial Degradation
          </Badge>
        );
      case 'signal-feed-compromised':
        return (
          <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
            <AlertCircle className="h-3 w-3 mr-1" />
            Signal Feed Compromised
          </Badge>
        );
    }
  };

  const getLastRefreshText = () => {
    const secondsAgo = Math.floor((Date.now() - state.lastRefresh) / 1000);
    if (secondsAgo < 60) {
      return `${secondsAgo.toFixed(1)}s ago`;
    }
    const minutesAgo = Math.floor(secondsAgo / 60);
    return `${minutesAgo}m ago`;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Global Signal Health
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Values Activas</div>
            <div className="text-2xl font-bold">{state.activeValues}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Ejecutables</div>
            <div className="text-2xl font-bold text-green-600">{state.executableValues}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Degradadas</div>
            <div className="text-2xl font-bold text-yellow-600">{state.degradedValues}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Last Refresh</div>
            <div className="text-sm font-medium flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {getLastRefreshText()}
            </div>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Estado del Sistema de Signals</span>
            {getStatusBadge()}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

