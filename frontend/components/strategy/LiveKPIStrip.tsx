'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { InfoTooltip } from '@/components/ui/info-tooltip';

const STALENESS_THRESHOLD_MS = 5 * 60 * 1000; // 5 min

export interface LiveKPIStripProps {
  totalPnL: number;
  totalExposure: number;
  maxExposure: number;
  totalIntents: number;
  approvedIntents: number;
  executedIntents: number;
  winRate: number;
  lastCalculatedAt?: string | null;
  isLoading?: boolean;
}

export function LiveKPIStrip({
  totalPnL,
  totalExposure,
  maxExposure,
  totalIntents,
  approvedIntents,
  executedIntents,
  winRate,
  lastCalculatedAt,
  isLoading = false,
}: LiveKPIStripProps) {
  const [now, setNow] = useState(0);
  useEffect(() => {
    const update = () => setNow(Date.now());
    update();
    const id = setInterval(update, 60000);
    return () => clearInterval(id);
  }, []);

  const lastActionMs = lastCalculatedAt ? now - new Date(lastCalculatedAt).getTime() : 0;
  const lastActionMins = Math.max(0, Math.floor(lastActionMs / 60000));
  const lastActionText = lastCalculatedAt
    ? now > 0
      ? `Hace ${lastActionMins} min`
      : '...'
    : 'Sin actividad';
  const isStale = lastActionMs > STALENESS_THRESHOLD_MS;

  const exposurePct = maxExposure > 0 ? Math.min(100, (totalExposure / maxExposure) * 100) : 0;

  if (isLoading) {
    return (
      <div className="flex items-center gap-0 border-b border-border/40 py-2.5">
        <div className="flex-1 flex items-center gap-4 px-4">
          <div className="h-5 w-16 animate-pulse rounded bg-muted/50" />
          <div className="h-4 w-32 animate-pulse rounded bg-muted/50" />
          <div className="h-4 w-20 animate-pulse rounded bg-muted/50" />
          <div className="h-4 w-24 animate-pulse rounded bg-muted/50" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-border/40 py-2.5">
      {/* PnL */}
      <div className="flex items-baseline gap-2">
        <span className="text-label text-[11px] uppercase tracking-wider">PnL</span>
        <span
          className={cn(
            'text-[13px] font-semibold tabular-nums',
            totalPnL > 0 && 'text-primary',
            totalPnL < 0 && 'text-destructive',
            totalPnL === 0 && 'text-foreground'
          )}
        >
          {totalPnL >= 0 ? '+' : ''}${totalPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      </div>

      {/* Exposición + bar */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-baseline gap-2 shrink-0">
          <span className="text-label text-[11px] uppercase tracking-wider">Exposición</span>
          <span className="text-[13px] font-medium tabular-nums">
            ${totalExposure.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="flex items-center gap-2 min-w-[120px] max-w-[180px]">
          <div className="h-1.5 flex-1 min-w-0 rounded-full bg-muted/50 overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-300',
                exposurePct >= 90 ? 'bg-destructive' : exposurePct >= 70 ? 'bg-amber-500' : 'bg-primary/70'
              )}
              style={{ width: `${exposurePct}%` }}
            />
          </div>
          <span className="text-[11px] text-muted-foreground tabular-nums shrink-0">
            ${(maxExposure / 1000).toFixed(0)}k
          </span>
        </div>
      </div>

      {/* Intentos */}
      <div className="flex items-baseline gap-2">
        <span className="text-label text-[11px] uppercase tracking-wider flex items-center gap-1">
          Intentos
          <InfoTooltip
            content="Solicitudes de ejecución emitidas por el grafo de decisión."
            title="Intentos"
          />
        </span>
        <span className="text-[13px] font-medium tabular-nums">{totalIntents}</span>
        <span className="text-[11px] text-muted-foreground">
          ({approvedIntents} ok · {Math.max(0, totalIntents - approvedIntents)} rej)
        </span>
      </div>

      {/* Tasa acierto */}
      <div className="flex items-baseline gap-2">
        <span className="text-label text-[11px] uppercase tracking-wider">Tasa acierto</span>
        <span className="text-[13px] font-medium tabular-nums">{winRate.toFixed(1)}%</span>
        {executedIntents > 0 && (
          <span className="text-[11px] text-muted-foreground">{executedIntents} ejec</span>
        )}
      </div>

      {/* Última acción */}
      <div className="flex items-baseline gap-2 ml-auto">
        <span className="text-label text-[11px] uppercase tracking-wider">Última acción</span>
        <span
          className={cn(
            'text-[12px] tabular-nums',
            isStale ? 'text-muted-foreground/70' : 'text-muted-foreground'
          )}
          title={isStale ? 'Datos desactualizados (>5 min)' : undefined}
        >
          {lastActionText}
        </span>
      </div>
    </div>
  );
}
