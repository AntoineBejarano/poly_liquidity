'use client';

import type { UniverseConfig } from '@/types/directory';

interface UniverseSummaryProps {
  universe: UniverseConfig;
  eligibleCount?: number | null;
  saving?: boolean;
  saveError?: string | null;
  onSave?: () => void;
  hasChanges?: boolean;
}

export function UniverseSummary({
  universe,
  eligibleCount,
  saving,
  saveError,
  onSave,
  hasChanges = false,
}: UniverseSummaryProps) {
  const categories = universe.categories ?? [];
  const tags = universe.tags ?? [];
  const markets = universe.markets ?? [];
  const events = universe.events ?? [];
  const timeFilter = universe.time_filter;
  const autoAttach = universe.auto_attach ?? false;

  return (
    <div className="border border-border rounded-lg bg-card p-4 space-y-3">
      <h3 className="text-sm font-semibold text-foreground">Resumen del universo</h3>
      <div className="text-xs text-muted-foreground space-y-1">
        {categories.length > 0 && (
          <p>
            <span className="font-medium text-foreground">Categorías:</span>{' '}
            {categories.join(', ')}
          </p>
        )}
        {tags.length > 0 && (
          <p>
            <span className="font-medium text-foreground">Tags:</span>{' '}
            {tags.join(', ')}
          </p>
        )}
        {markets.length > 0 && (
          <p>
            <span className="font-medium text-foreground">Markets (explícitos):</span> {markets.length}
          </p>
        )}
        {events.length > 0 && (
          <p>
            <span className="font-medium text-foreground">Events (explícitos):</span> {events.length}
          </p>
        )}
        {timeFilter && (
          <p>
            <span className="font-medium text-foreground">Tiempo:</span>{' '}
            {timeFilter.window && `Ventana ${timeFilter.window}`}
            {timeFilter.next_days != null && ` · Próximos ${timeFilter.next_days} días`}
            {timeFilter.max_time_to_resolution_minutes != null &&
              ` · Max ${timeFilter.max_time_to_resolution_minutes} min a resolución`}
          </p>
        )}
        {categories.length === 0 && tags.length === 0 && markets.length === 0 && events.length === 0 && !timeFilter && (
          <p>Sin filtros: ningún evento será elegible por selectores. Puedes añadir categorías, tags o ventana temporal.</p>
        )}
      </div>
      {eligibleCount != null && (
        <p className="text-xs">
          <span className="text-muted-foreground">Eventos elegibles con estos filtros:</span>{' '}
          <span className="font-semibold text-foreground">{eligibleCount}</span>
        </p>
      )}
      {onSave && (
        <div className="pt-2">
          <button
            type="button"
            onClick={onSave}
            disabled={saving || !hasChanges}
            className="px-4 py-2 text-xs font-medium text-primary-foreground bg-primary rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 transition-colors"
          >
            {saving ? 'Guardando…' : 'Guardar universo'}
          </button>
        </div>
      )}
      {saveError && (
        <p className="text-xs text-destructive bg-destructive/10 px-2 py-1.5 rounded border border-destructive/30">
          {saveError}
        </p>
      )}
      {autoAttach && (
        <p className="text-xs text-muted-foreground">
          Auto-attach está activado: la estrategia puede asignar automáticamente nuevos eventos que cumplan el universo.
        </p>
      )}
      {universe.max_events_per_strategy != null && (
        <p className="text-xs text-muted-foreground">
          Límites: max {universe.max_events_per_strategy} eventos · {universe.max_auto_attaches_per_hour ?? '—'} auto-attachs/hora
          {universe.auto_attach_dry_run ? ' · Dry-run activo' : ''}
        </p>
      )}
    </div>
  );
}
