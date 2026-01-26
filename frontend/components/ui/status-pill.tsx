'use client';

import { cn } from '@/lib/utils';

interface StatusPillProps {
  status: 'active' | 'paused' | 'error' | 'degraded';
  label?: string;
  className?: string;
}

export function StatusPill({ status, label, className }: StatusPillProps) {
  const statusConfig = {
    active: {
      bg: 'bg-green-500/20 dark:bg-green-600/20',
      text: 'text-green-600 dark:text-green-400',
      dot: 'bg-green-500 dark:bg-green-600',
      defaultLabel: 'Active',
    },
    paused: {
      bg: 'bg-yellow-500/20 dark:bg-yellow-600/20',
      text: 'text-yellow-600 dark:text-yellow-400',
      dot: 'bg-yellow-500 dark:bg-yellow-600',
      defaultLabel: 'Paused',
    },
    error: {
      bg: 'bg-red-500/20 dark:bg-red-600/20',
      text: 'text-red-600 dark:text-red-400',
      dot: 'bg-red-500 dark:bg-red-600',
      defaultLabel: 'Error',
    },
    degraded: {
      bg: 'bg-orange-500/20 dark:bg-orange-600/20',
      text: 'text-orange-600 dark:text-orange-400',
      dot: 'bg-orange-500 dark:bg-orange-600',
      defaultLabel: 'Degraded',
    },
  };

  const config = statusConfig[status];

  return (
    <div className={cn("flex items-center gap-1.5 px-2 py-1 rounded border", config.bg, className)}>
      <span className={cn("w-2 h-2 rounded-full", config.dot)}></span>
      <span className={cn("text-[13px] font-medium", config.text)}>
        {label || config.defaultLabel}
      </span>
    </div>
  );
}

