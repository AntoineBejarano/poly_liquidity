'use client';

import { InfoTooltip } from './info-tooltip';
import { cn } from '@/lib/utils';

interface MetricChipProps {
  label: string;
  value: string;
  color?: 'green' | 'yellow' | 'red' | 'neutral';
  tooltip?: string;
  className?: string;
}

export function MetricChip({ label, value, color = 'neutral', tooltip, className }: MetricChipProps) {
  const colorStyles = {
    green: 'text-green-600 dark:text-green-400',
    yellow: 'text-yellow-600 dark:text-yellow-400',
    red: 'text-red-600 dark:text-red-400',
    neutral: 'text-foreground',
  };
  
  return (
    <div className={cn("flex items-center gap-1.5 px-2 py-1 rounded border bg-card", className)}>
      <span className="text-[11px] text-muted-foreground">{label}</span>
      {tooltip && <InfoTooltip content={tooltip} />}
      <span className={cn("text-[13px] font-medium", colorStyles[color])}>{value}</span>
    </div>
  );
}

