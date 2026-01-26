'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, Clock, Target, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProfitEfficiencyMetricsProps {
  totalPnLGross: number;
  totalPnLNet: number;
  profitPerTrade: number;
  avgExecutionTime: number; // ms
  avgSlippage: number; // %
  successRate: number; // % fully hedged
}

export function ProfitEfficiencyMetrics({
  totalPnLGross,
  totalPnLNet,
  profitPerTrade,
  avgExecutionTime,
  avgSlippage,
  successRate,
}: ProfitEfficiencyMetricsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Profit & Efficiency Metrics
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
          {/* PnL Total */}
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">PnL Total (Gross)</div>
            <div className={cn(
              "text-2xl font-bold",
              totalPnLGross >= 0 ? "text-green-600" : "text-red-600"
            )}>
              {totalPnLGross >= 0 ? '+' : ''}${totalPnLGross.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">PnL Total (Net)</div>
            <div className={cn(
              "text-2xl font-bold",
              totalPnLNet >= 0 ? "text-green-600" : "text-red-600"
            )}>
              {totalPnLNet >= 0 ? '+' : ''}${totalPnLNet.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Profit por Trade</div>
            <div className={cn(
              "text-2xl font-bold",
              profitPerTrade >= 0 ? "text-green-600" : "text-red-600"
            )}>
              {profitPerTrade >= 0 ? '+' : ''}${profitPerTrade.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>

          {/* Efficiency Metrics */}
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Avg Execution Time
            </div>
            <div className={cn(
              "text-xl font-semibold",
              avgExecutionTime < 500 ? "text-green-600" :
              avgExecutionTime < 1000 ? "text-yellow-600" : "text-red-600"
            )}>
              {avgExecutionTime}ms
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <Target className="h-3 w-3" />
              Avg Slippage
            </div>
            <div className={cn(
              "text-xl font-semibold",
              Math.abs(avgSlippage) < 0.5 ? "text-green-600" :
              Math.abs(avgSlippage) < 1.0 ? "text-yellow-600" : "text-red-600"
            )}>
              {avgSlippage >= 0 ? '+' : ''}{avgSlippage.toFixed(2)}%
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" />
              Success Rate
            </div>
            <div className={cn(
              "text-xl font-semibold",
              successRate >= 90 ? "text-green-600" :
              successRate >= 75 ? "text-yellow-600" : "text-red-600"
            )}>
              {successRate.toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground">fully hedged</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

