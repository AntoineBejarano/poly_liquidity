'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { DirectoryTag, DirectoryMeta } from '@/types/directory';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';

const DEBOUNCE_MS = 250;
const TAG_FILTER_THRESHOLD = 8; // Mostrar búsqueda cuando hay muchos tags

export interface DirectoryFiltersState {
  search: string;
  tagId: string | null;
  nextDays: number | null;
  window: 'UPCOMING' | 'ACTIVE' | 'ANY' | null;
}

interface DirectoryFiltersProps {
  tags: DirectoryTag[];
  meta: DirectoryMeta | null;
  filters: DirectoryFiltersState;
  onFiltersChange: (f: DirectoryFiltersState) => void;
  onSearchSubmit?: (search: string) => void;
}

export function DirectoryFilters({
  tags,
  meta,
  filters,
  onFiltersChange,
  onSearchSubmit,
}: DirectoryFiltersProps) {
  const [searchInput, setSearchInput] = useState(filters.search);
  const [tagFilterInput, setTagFilterInput] = useState('');

  const filteredTags = useMemo(() => {
    if (!tagFilterInput.trim()) return tags;
    const q = tagFilterInput.toLowerCase().trim();
    return tags.filter((t) =>
      (t.name || t.slug || t.tag_id).toLowerCase().includes(q)
    );
  }, [tags, tagFilterInput]);

  const applySearch = useCallback(
    (value: string) => {
      onFiltersChange({ ...filters, search: value });
      onSearchSubmit?.(value);
    },
    [filters, onFiltersChange, onSearchSubmit]
  );

  useEffect(() => {
    const t = setTimeout(() => applySearch(searchInput), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [searchInput]);

  // Sync local search with external filters when parent changes filter
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional sync from prop to local state
    setSearchInput(filters.search);
  }, [filters.search]);

  const removeChip = (key: keyof DirectoryFiltersState, value: string | number | null) => {
    if (key === 'tagId') onFiltersChange({ ...filters, tagId: null });
    if (key === 'nextDays') onFiltersChange({ ...filters, nextDays: null });
    if (key === 'window') onFiltersChange({ ...filters, window: null });
  };

  const freshnessLabel = meta?.last_scanned_at
    ? new Date(meta.last_scanned_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
    : null;
  const isStale = meta?.freshness === 'stale';

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Buscar eventos o mercados..."
            className="w-full pl-9 pr-8 py-2 text-sm text-foreground bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
            aria-label="Buscar"
          />
          {searchInput && (
            <button
              type="button"
              onClick={() => setSearchInput('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground rounded focus:outline-none focus:ring-2 focus:ring-primary/50"
              aria-label="Limpiar búsqueda"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
        <Select
          value={filters.tagId ?? 'all'}
          onValueChange={(v) => onFiltersChange({ ...filters, tagId: v === 'all' ? null : v })}
          onOpenChange={(open) => { if (!open) setTagFilterInput(''); }}
        >
          <SelectTrigger className="w-[180px] bg-background" aria-label="Tag">
            <SelectValue placeholder="Tag" />
          </SelectTrigger>
          <SelectContent>
            {tags.length > TAG_FILTER_THRESHOLD && (
              <div className="p-2 border-b border-border">
                <Input
                  placeholder="Buscar tag..."
                  value={tagFilterInput}
                  onChange={(e) => setTagFilterInput(e.target.value)}
                  className="h-8 text-sm bg-background text-foreground"
                  onPointerDown={(e) => e.stopPropagation()}
                />
              </div>
            )}
            <SelectItem value="all">Todos los tags</SelectItem>
            {filteredTags.map((t) => (
              <SelectItem key={t.tag_id} value={t.tag_id}>
                {t.name || t.slug || t.tag_id}
              </SelectItem>
            ))}
            {filteredTags.length === 0 && tags.length > 0 && (
              <div className="py-2 px-2 text-sm text-muted-foreground">Ninguna coincidencia</div>
            )}
          </SelectContent>
        </Select>
        <Select
          value={filters.nextDays != null ? String(filters.nextDays) : 'all'}
          onValueChange={(v) =>
            onFiltersChange({ ...filters, nextDays: v === 'all' ? null : Number(v) })
          }
        >
          <SelectTrigger className="w-[160px] bg-background" aria-label="Próximos días">
            <SelectValue placeholder="Tiempo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Cualquier tiempo</SelectItem>
            <SelectItem value="1">Próximas 24h</SelectItem>
            <SelectItem value="7">Próximos 7 días</SelectItem>
            <SelectItem value="14">Próximos 14 días</SelectItem>
            <SelectItem value="30">Próximos 30 días</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={filters.window ?? 'all'}
          onValueChange={(v) =>
            onFiltersChange({
              ...filters,
              window: v === 'all' ? null : (v as 'UPCOMING' | 'ACTIVE' | 'ANY'),
            })
          }
        >
          <SelectTrigger className="w-[160px] bg-background" aria-label="Ventana">
            <SelectValue placeholder="Ventana" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Cualquier estado</SelectItem>
            <SelectItem value="UPCOMING">UPCOMING</SelectItem>
            <SelectItem value="ACTIVE">ACTIVE</SelectItem>
            <SelectItem value="ANY">ANY</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Chips de filtros activos */}
      <div className="flex flex-wrap gap-2">
        {filters.tagId && (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md bg-muted text-foreground border border-border">
            {tags.find((t) => t.tag_id === filters.tagId)?.name || filters.tagId}
            <button
              type="button"
              onClick={() => removeChip('tagId', filters.tagId)}
              className="p-0.5 rounded hover:bg-muted-foreground/20 focus:outline-none focus:ring-2 focus:ring-primary/50"
              aria-label="Quitar tag"
            >
              <span aria-hidden="true">×</span>
            </button>
          </span>
        )}
        {filters.nextDays != null && (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md bg-muted text-foreground border border-border">
            Próximos {filters.nextDays} días
            <button
              type="button"
              onClick={() => removeChip('nextDays', filters.nextDays)}
              className="p-0.5 rounded hover:bg-muted-foreground/20 focus:outline-none focus:ring-2 focus:ring-primary/50"
              aria-label="Quitar filtro días"
            >
              <span aria-hidden="true">×</span>
            </button>
          </span>
        )}
        {filters.window && (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md bg-muted text-foreground border border-border">
            {filters.window}
            <button
              type="button"
              onClick={() => removeChip('window', filters.window)}
              className="p-0.5 rounded hover:bg-muted-foreground/20 focus:outline-none focus:ring-2 focus:ring-primary/50"
              aria-label="Quitar ventana"
            >
              <span aria-hidden="true">×</span>
            </button>
          </span>
        )}
      </div>

      {/* Freshness */}
      <div className="text-xs text-muted-foreground flex items-center gap-2">
        {freshnessLabel && (
          <span>Datos actualizados a las {freshnessLabel}</span>
        )}
        {isStale && meta && (
          <span className="text-amber-600 dark:text-amber-400">· Los datos pueden estar desactualizados</span>
        )}
      </div>
    </div>
  );
}
