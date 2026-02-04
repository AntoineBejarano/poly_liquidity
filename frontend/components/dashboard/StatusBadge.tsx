'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

type StatusType = 'running' | 'paused' | 'stopped' | 'error' | 'degraded';
type HealthType = 'ok' | 'degraded' | 'error';

interface StatusBadgeProps {
  status: StatusType | HealthType;
  className?: string;
}

const statusConfig: Record<StatusType | HealthType, { label: string; variant: 'success' | 'warning' | 'error' | 'default' }> = {
  running: { label: 'En ejecución', variant: 'success' },
  paused: { label: 'Pausada', variant: 'default' },
  stopped: { label: 'Detenida', variant: 'default' },
  error: { label: 'Error', variant: 'error' },
  degraded: { label: 'Degradada', variant: 'warning' },
  ok: { label: 'OK', variant: 'success' },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status];
  
  return (
    <Badge variant={config.variant} className={cn(className)}>
      {config.label}
    </Badge>
  );
}

