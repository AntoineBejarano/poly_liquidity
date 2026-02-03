'use client';

import type { DirectoryEvent } from '@/types/directory';

interface DirectoryEventListProps {
  events: DirectoryEvent[];
  total: number;
  loading: boolean;
  limit: number;
  offset: number;
  onLoadMore?: () => void;
  hasMore?: boolean;
}

function formatTime(iso: string | null): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return '—';
  }
}

export function DirectoryEventList({
  events,
  total,
  loading,
  limit,
  offset,
  onLoadMore,
  hasMore = false,
}: DirectoryEventListProps) {
  if (loading && events.length === 0) {
    return (
      <div className="border border-border rounded-lg overflow-hidden bg-card">
        <table className="w-full">
          <thead className="bg-muted/50 border-b border-border">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Evento</th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Market</th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Estado</th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Fin</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {Array.from({ length: 5 }).map((_, i) => (
              <tr key={i}>
                <td className="px-4 py-3"><div className="h-4 w-48 bg-muted/60 rounded animate-pulse" /></td>
                <td className="px-4 py-3"><div className="h-4 w-32 bg-muted/60 rounded animate-pulse" /></td>
                <td className="px-4 py-3"><div className="h-4 w-16 bg-muted/60 rounded animate-pulse" /></td>
                <td className="px-4 py-3"><div className="h-4 w-24 bg-muted/60 rounded animate-pulse" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (!loading && events.length === 0) {
    return (
      <div className="border border-border rounded-lg bg-card p-8 text-center">
        <p className="text-sm text-muted-foreground">
          Ningún evento coincide con los filtros. Prueba a cambiar categoría, tag o ventana temporal.
        </p>
        <p className="text-xs text-muted-foreground mt-2">
          Si no ves datos, verifica que el Scanner haya ejecutado y que haya mercados habilitados en Mercados.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="border border-border rounded-lg overflow-hidden bg-card">
        <table className="w-full">
          <thead className="bg-muted/50 border-b border-border sticky top-0 z-10">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Evento</th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Market</th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Estado</th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Fin</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {events.map((event) => (
              <tr key={event.event_id} className="hover:bg-muted/30 transition-colors duration-150">
                <td className="px-4 py-2">
                  <div className="text-xs font-medium text-foreground">{event.market_name || event.event_id}</div>
                  <div className="text-xs text-muted-foreground truncate max-w-[200px]" title={event.event_id}>
                    {event.event_id}
                  </div>
                </td>
                <td className="px-4 py-2 text-xs text-muted-foreground truncate max-w-[180px]">
                  {event.market_id}
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                      event.state === 'ACTIVE'
                        ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'
                        : event.state === 'UPCOMING'
                        ? 'bg-sky-500/20 text-sky-600 dark:text-sky-400'
                        : 'bg-muted text-muted-foreground'
                    }`}
                  >
                    {event.state}
                  </span>
                </td>
                <td className="px-4 py-2 text-xs text-muted-foreground">
                  {formatTime(event.end_time)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          Mostrando {offset + 1}–{Math.min(offset + limit, total)} de {total} eventos
        </span>
        {hasMore && onLoadMore && (
          <button
            type="button"
            onClick={onLoadMore}
            disabled={loading}
            className="px-3 py-1.5 font-medium text-primary hover:bg-primary/10 rounded focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
          >
            {loading ? 'Cargando…' : 'Cargar más'}
          </button>
        )}
      </div>
    </div>
  );
}
