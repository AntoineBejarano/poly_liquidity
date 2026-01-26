'use client';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { AlertTriangle, X } from 'lucide-react';
import { useState } from 'react';

export interface AlertItem {
  id: string;
  type: 'critical' | 'warning';
  message: string;
  details?: string;
  strategyId?: string;
  actionLabel?: string;
  onAction?: () => void;
}

interface AlertBannerProps {
  alerts: AlertItem[];
  onDismiss?: (alertId: string) => void;
}

export function AlertBanner({ alerts, onDismiss }: AlertBannerProps) {
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  if (alerts.length === 0) {
    return null;
  }

  const handleDismiss = (alertId: string) => {
    setDismissed((prev) => new Set(prev).add(alertId));
    onDismiss?.(alertId);
  };

  const visibleAlerts = alerts.filter((alert) => !dismissed.has(alert.id));

  if (visibleAlerts.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2 w-full">
      {visibleAlerts.map((alert) => (
        <Alert
          key={alert.id}
          variant={alert.type === 'critical' ? 'destructive' : 'warning'}
          className="flex items-start justify-between gap-4"
        >
          <div className="flex-1">
            <AlertTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              {alert.message}
            </AlertTitle>
            {alert.details && (
              <AlertDescription className="mt-1">
                {alert.details}
              </AlertDescription>
            )}
            {alert.actionLabel && alert.onAction && (
              <div className="mt-2 flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={alert.onAction}
                >
                  {alert.actionLabel}
                </Button>
              </div>
            )}
          </div>
          {onDismiss && (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => handleDismiss(alert.id)}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </Alert>
      ))}
    </div>
  );
}

