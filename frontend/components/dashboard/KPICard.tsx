'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string | number;
  trend?: {
    value: string;
    isPositive: boolean;
  };
  breakdown?: React.ReactNode;
  className?: string;
}

export function KPICard({ title, value, trend, breakdown, className }: KPICardProps) {
  return (
    <Card className={cn("h-full flex flex-col", className)}>
      <CardHeader className="pb-3 flex-shrink-0">
        <CardTitle className="text-sm font-medium text-muted-foreground leading-tight">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col justify-between min-h-0">
        <div>
          <div className="text-2xl font-bold leading-tight break-words">{value}</div>
          {trend && (
            <div className={cn(
              "flex items-center gap-1 text-xs mt-2",
              trend.isPositive ? "text-green-600" : "text-red-600"
            )}>
              {trend.isPositive ? (
                <TrendingUp className="h-3 w-3 flex-shrink-0" />
              ) : (
                <TrendingDown className="h-3 w-3 flex-shrink-0" />
              )}
              <span className="whitespace-nowrap">{trend.value}</span>
            </div>
          )}
        </div>
        {breakdown && (
          <div className="text-xs text-muted-foreground mt-3 leading-relaxed">
            {breakdown}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

