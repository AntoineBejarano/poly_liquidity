'use client';

import { useCallback, useEffect, useState } from 'react';
import type { DirectoryCategory, DirectoryTag, DirectoryMeta } from '@/types/directory';

const DEBOUNCE_MS = 250;

export interface DirectoryFiltersState {
  search: string;
  category: string | null;
  tagId: string | null;
  nextDays: number | null;
  window: 'UPCOMING' | 'ACTIVE' | 'ANY' | null;
}

interface DirectoryFiltersProps {
  categories: DirectoryCategory[];
  tags: DirectoryTag[];
  meta: DirectoryMeta | null;
  filters: DirectoryFiltersState;
  onFiltersChange: (f: DirectoryFiltersState) => void;
  onSearchSubmit?: (search: string) => void;
}

export function DirectoryFilters({
  categories,
  tags,
  meta,
  filters,
  onFiltersChange,
  onSearchSubmit,
}: DirectoryFiltersProps) {
  const [searchInput, setSearchInput] = useState(filters.search);

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

  useEffect(() => {
    setSearchInput(filters.search);
  }, [filters.search]);

  const removeChip = (key: keyof DirectoryFiltersState, value: string | number | null) => {
    if (key === 'category') onFiltersChange({ ...filters, category: null });
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
        <select
          value={filters.category ?? ''}
          onChange={(e) => onFiltersChange({ ...filters, category: e.target.value || null })}
          className="px-3 py-2 text-sm text-foreground bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
          aria-label="Categoría"
        >
          <option value="">Todas las categorías</option>
          {categories.map((c) => (
            <option key={c.category} value={c.category}>
              {c.category}
            </option>
          ))}
        </select>
        <select
          value={filters.tagId ?? ''}
          onChange={(e) => onFiltersChange({ ...filters, tagId: e.target.value || null })}
          className="px-3 py-2 text-sm text-foreground bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
          aria-label="Tag"
        >
          <option value="">Todos los tags</option>
          {tags.map((t) => (
            <option key={t.tag_id} value={t.tag_id}>
              {t.name || t.slug || t.tag_id}
            </option>
          ))}
        </select>
        <select
          value={filters.nextDays ?? ''}
          onChange={(e) => onFiltersChange({ ...filters, nextDays: e.target.value ? Number(e.target.value) : null })}
          className="px-3 py-2 text-sm text-foreground bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
          aria-label="Próximos días"
        >
          <option value="">Cualquier tiempo</option>
          <option value="1">Próximas 24h</option>
          <option value="7">Próximos 7 días</option>
          <option value="14">Próximos 14 días</option>
          <option value="30">Próximos 30 días</option>
        </select>
        <select
          value={filters.window ?? ''}
          onChange={(e) =>
            onFiltersChange({
              ...filters,
              window: (e.target.value as 'UPCOMING' | 'ACTIVE' | 'ANY') || null,
            })
          }
          className="px-3 py-2 text-sm text-foreground bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
          aria-label="Ventana"
        >
          <option value="">Cualquier estado</option>
          <option value="UPCOMING">UPCOMING</option>
          <option value="ACTIVE">ACTIVE</option>
          <option value="ANY">ANY</option>
        </select>
      </div>

      {/* Chips de filtros activos */}
      <div className="flex flex-wrap gap-2">
        {filters.category && (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md bg-muted text-foreground border border-border">
            {filters.category}
            <button
              type="button"
              onClick={() => removeChip('category', filters.category)}
              className="p-0.5 rounded hover:bg-muted-foreground/20 focus:outline-none focus:ring-2 focus:ring-primary/50"
              aria-label={`Quitar categoría ${filters.category}`}
            >
              <span aria-hidden="true">×</span>
            </button>
          </span>
        )}
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
