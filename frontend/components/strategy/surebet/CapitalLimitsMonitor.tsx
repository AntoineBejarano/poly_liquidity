'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { DollarSign, TrendingDown, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CapitalLimitsMonitorProps {
  capitalAssigned: number;
  capitalUsed: number;
  /** Balance USDC de la wallet Polymarket (GET /api/polymarket/balance). Opcional. */
  walletBalanceUsdc?: number | null;
  activeTrades: number;
  dailyPnL: number;
  drawdown: number;
  alerts: Array<{
    id: string;
    type: 'warning' | 'critical';
    message: string;
  }>;
}

export function CapitalLimitsMonitor({
  capitalAssigned,
  capitalUsed,
  walletBalanceUsdc,
  activeTrades,
  dailyPnL,
  drawdown,
  alerts,
}: CapitalLimitsMonitorProps) {
  const capitalPercent = capitalAssigned > 0 ? (capitalUsed / capitalAssigned) * 100 : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <DollarSign className="h-5 w-5" />
          Capital & Limits Monitor
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Balance Polymarket (wallet real) */}
        {walletBalanceUsdc != null && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium">Balance Polymarket (USDC)</span>
              <span className="text-sm font-semibold">
                ${walletBalanceUsdc.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              Wallet conectada (actualización ~60s)
            </div>
          </div>
        )}

        {/* Capital Usage */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Capital usado</span>
            <span className="text-sm font-semibold">
              ${capitalUsed.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} / ${capitalAssigned.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <Progress value={Math.min(capitalPercent, 100)} className="h-2" />
          <div className="text-xs text-muted-foreground mt-1">
            {capitalPercent.toFixed(1)}% del capital asignado
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-muted rounded-lg">
          <div>
            <div className="text-xs text-muted-foreground">Trades activos</div>
            <div className="text-lg font-semibold">{activeTrades}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Daily PnL</div>
            <div className={cn(
              "text-lg font-semibold",
              dailyPnL >= 0 ? "text-green-600" : "text-red-600"
            )}>
              {dailyPnL >= 0 ? '+' : ''}${dailyPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Drawdown</div>
            <div className={cn(
              "text-lg font-semibold flex items-center gap-1",
              drawdown > -5 ? "text-green-600" :
              drawdown > -10 ? "text-yellow-600" : "text-red-600"
            )}>
              <TrendingDown className="h-4 w-4" />
              {drawdown.toFixed(2)}%
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">
              {walletBalanceUsdc != null ? 'Balance Polymarket (USDC)' : 'Límite restante'}
            </div>
            <div className="text-lg font-semibold text-green-600">
              ${(walletBalanceUsdc != null ? walletBalanceUsdc : Math.max(0, capitalAssigned - capitalUsed)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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

