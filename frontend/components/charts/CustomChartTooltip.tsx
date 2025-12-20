'use client';

import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface CustomChartTooltipProps {
  active?: boolean;
  payload?: Array<{
    name?: string;
    value?: number | string;
    color?: string;
    dataKey?: string;
    formatter?: (value: any) => string;
  }>;
  label?: string;
  labelFormatter?: (label: string) => string;
  valueFormatter?: (value: number) => string;
}

export function CustomChartTooltip({
  active,
  payload,
  label,
  labelFormatter,
  valueFormatter = (value: number) => value.toLocaleString(),
}: CustomChartTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const formattedLabel = labelFormatter ? labelFormatter(label || '') : label;

  return (
    <Card className="p-3 shadow-premium-md border-border/50">
      {formattedLabel && (
        <p className="text-caption mb-2 font-medium">{formattedLabel}</p>
      )}
      <div className="space-y-1.5">
        {payload.map((entry, index) => {
          const value = typeof entry.value === 'number' ? entry.value : parseFloat(entry.value || '0');
          const formattedValue = entry.formatter 
            ? entry.formatter(value) 
            : valueFormatter(value);
          
          return (
            <div key={index} className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: entry.color || 'hsl(var(--foreground))' }}
              />
              <span className="text-body font-medium">
                {entry.name || entry.dataKey}: {formattedValue}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

