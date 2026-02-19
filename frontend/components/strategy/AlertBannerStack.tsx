'use client';

import { useState } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ChevronDown, ChevronUp } from 'lucide-react';

export type AlertSeverity = 'error' | 'warning' | 'info';

export interface AlertBannerItem {
  id: string;
  severity: AlertSeverity;
  message: React.ReactNode;
  onDismiss?: () => void;
  dismissLabel?: string;
}

const SEVERITY_ORDER: Record<AlertSeverity, number> = { error: 3, warning: 2, info: 1 };

interface AlertBannerStackProps {
  alerts: AlertBannerItem[];
  /** Máximo de banners visibles antes de colapsar. Default 2. */
  maxVisible?: number;
  className?: string;
}

export function AlertBannerStack({ alerts, maxVisible = 2, className }: AlertBannerStackProps) {
  const [expanded, setExpanded] = useState(false);

  if (alerts.length === 0) return null;

  const sorted = [...alerts].sort((a, b) => SEVERITY_ORDER[b.severity] - SEVERITY_ORDER[a.severity]);
  const visible = expanded ? sorted : sorted.slice(0, maxVisible);
  const hiddenCount = sorted.length - visible.length;

  return (
    <div className={cn('space-y-2', className)}>
      {visible.map((alert) => (
        <Alert
          key={alert.id}
          variant={alert.severity === 'error' ? 'destructive' : 'default'}
          className={cn(
            'flex flex-row items-center justify-between gap-2',
            alert.severity === 'info' && 'border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30',
            alert.severity === 'warning' && 'border-amber-500/50 bg-amber-500/5'
          )}
        >
          <AlertDescription className="flex-1">{alert.message}</AlertDescription>
          {(alert.onDismiss || (alert.dismissLabel && !alert.onDismiss)) && (
            <Button
              variant="ghost"
              size="sm"
              className={cn(
                'shrink-0',
                alert.severity === 'error' && 'text-destructive hover:text-destructive'
              )}
              onClick={alert.onDismiss}
            >
              {alert.dismissLabel ?? 'Cerrar'}
            </Button>
          )}
        </Alert>
      ))}
      {!expanded && hiddenCount > 0 && (
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground hover:text-foreground w-full justify-center gap-1"
          onClick={() => setExpanded(true)}
        >
          <ChevronDown className="h-4 w-4" />
          {hiddenCount} alerta{hiddenCount > 1 ? 's' : ''} más
        </Button>
      )}
      {expanded && sorted.length > maxVisible && (
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground hover:text-foreground w-full justify-center gap-1"
          onClick={() => setExpanded(false)}
        >
          <ChevronUp className="h-4 w-4" />
          Ocultar
        </Button>
      )}
    </div>
  );
}
