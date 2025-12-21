'use client';

import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface RefreshingIndicatorProps {
  isRefreshing: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
}

/**
 * Componente sutil para indicar que los datos se están actualizando.
 * 
 * Usado durante refreshes automáticos para no bloquear la UI.
 * Aparece como un pequeño spinner o badge en la esquina.
 */
export function RefreshingIndicator({
  isRefreshing,
  className,
  size = 'sm',
  showText = false,
}: RefreshingIndicatorProps) {
  if (!isRefreshing) return null;

  const sizeClasses = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  };

  return (
    <div
      className={cn(
        'flex items-center gap-1.5 text-xs text-muted-foreground',
        className
      )}
    >
      <Loader2
        className={cn(
          'animate-spin text-muted-foreground',
          sizeClasses[size]
        )}
      />
      {showText && (
        <span className="text-xs text-muted-foreground">Actualizando...</span>
      )}
    </div>
  );
}

