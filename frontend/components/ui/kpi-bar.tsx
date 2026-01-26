'use client';

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface KPIProps {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  tooltip?: string;
}

interface KPIBarProps {
  children: ReactNode;
  className?: string;
}

export function KPI({ label, value, trend, tooltip }: KPIProps) {
  const trendIcon = trend === 'up' ? '↑' : trend === 'down' ? '↓' : null;
  const trendColor = trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : '';

  return (
    <div className="flex flex-col gap-1 px-3 py-2 border rounded bg-card">
      <div className="flex items-center gap-1">
        <span className="text-[11px] text-muted-foreground">{label}</span>
        {tooltip && <span className="text-[10px] text-muted-foreground">(?)</span>}
      </div>
      <div className="flex items-baseline gap-1">
        <span className={cn("text-[13px] font-semibold", trendColor)}>
          {typeof value === 'number' ? value.toLocaleString() : value}
        </span>
        {trendIcon && <span className={cn("text-[10px]", trendColor)}>{trendIcon}</span>}
      </div>
    </div>
  );
}

export function KPIBar({ children, className }: KPIBarProps) {
  return (
    <div className={cn("flex items-center gap-2 flex-wrap", className)}>
      {children}
    </div>
  );
}

