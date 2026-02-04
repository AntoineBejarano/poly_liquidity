'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { initApiClient, createTokenGetter, ApiResponseError } from '@/lib/api';
import type {
  DirectoryMeta,
  DirectoryCategory,
  DirectoryTag,
  DirectoryEvent,
  DirectoryEventsResponse,
  DirectoryCategoriesResponse,
  DirectoryTagsResponse,
  UniverseConfig,
  UniverseResponse,
} from '@/types/directory';
import {
  DirectoryFilters,
  DirectoryEventList,
  UniverseSummary,
  type DirectoryFiltersState,
} from '@/components/strategy/universe';

const EVENTS_PAGE_SIZE = 20;

function filtersToUniverse(f: DirectoryFiltersState): UniverseConfig {
  const time_filter =
    f.nextDays != null || f.window
      ? {
          next_days: f.nextDays ?? undefined,
          window: f.window ?? undefined,
          max_time_to_resolution_minutes: undefined,
        }
      : undefined;
  return {
    categories: f.category ? [f.category] : [],
    tags: f.tagId ? [f.tagId] : [],
    markets: [],
    events: [],
    time_filter: time_filter ?? null,
    auto_attach: false,
    deny_list: [],
  };
}

function universeToFilters(u: UniverseResponse['universe']): DirectoryFiltersState {
  const tf = u.time_filter;
  return {
    search: '',
    category: u.categories?.[0] ?? null,
    tagId: u.tags?.[0] ?? null,
    nextDays: tf?.next_days ?? null,
    window: (tf?.window as DirectoryFiltersState['window']) ?? null,
  };
}

export default function StrategyUniversePage() {
  const params = useParams();
  const router = useRouter();
  const user = useUser();
  const stackApp = useStackApp();
  const strategyId = params.id as string;

  const [strategyName, setStrategyName] = useState<string>('');
  const [universe, setUniverse] = useState<UniverseResponse['universe'] | null>(null);
  const [universeLoaded, setUniverseLoaded] = useState(false);
  const [filters, setFilters] = useState<DirectoryFiltersState>({
    search: '',
    category: null,
    tagId: null,
    nextDays: null,
    window: null,
  });
  const [meta, setMeta] = useState<DirectoryMeta | null>(null);
  const [categories, setCategories] = useState<DirectoryCategory[]>([]);
  const [tags, setTags] = useState<DirectoryTag[]>([]);
  const [events, setEvents] = useState<DirectoryEvent[]>([]);
  const [eventsTotal, setEventsTotal] = useState(0);
  const [eventsOffset, setEventsOffset] = useState(0);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);

  const api = user && stackApp ? initApiClient(createTokenGetter(user, stackApp)) : null;

  // Load strategy name and current universe
  useEffect(() => {
    if (!api || !strategyId) return;
    (async () => {
      try {
        const [strategyRes, universeRes] = await Promise.all([
          api.get<{ name: string }>(`/api/strategies/${strategyId}`).catch(() => ({ name: '' })),
          api.get<UniverseResponse>(`/api/strategies/${strategyId}/universe`),
        ]);
        setStrategyName(strategyRes?.name ?? '');
        const u = universeRes.universe;
        setUniverse(u);
        setFilters(universeToFilters(u));
        setUniverseLoaded(true);
      } catch (e) {
        console.error('Error loading strategy/universe:', e);
        setPageError(e instanceof Error ? e.message : 'Error al cargar la estrategia');
      }
    })();
  }, [api, strategyId]);

  // Load directory meta, categories, tags (once)
  useEffect(() => {
    if (!api) return;
    (async () => {
      try {
        const [metaRes, catRes, tagsRes] = await Promise.all([
          api.get<DirectoryMeta>('/directory/meta'),
          api.get<DirectoryCategoriesResponse>('/directory/categories'),
          api.get<DirectoryTagsResponse>('/directory/tags?limit=200'),
        ]);
        setMeta(metaRes);
        setCategories(catRes.items);
        setTags(tagsRes.items);
      } catch (e) {
        console.error('Error loading directory:', e);
      }
    })();
  }, [api]);

  // Fetch events when filters (used for Directory) change
  const fetchEvents = useCallback(
    async (offset: number = 0, append: boolean = false) => {
      if (!api) return;
      setEventsLoading(true);
      try {
        const params = new URLSearchParams();
        params.set('limit', String(EVENTS_PAGE_SIZE));
        params.set('offset', String(offset));
        if (filters.category) params.set('category', filters.category);
        if (filters.tagId) params.set('tag_id', filters.tagId);
        if (filters.nextDays != null) params.set('next_days', String(filters.nextDays));
        if (filters.window && filters.window !== 'ANY') params.set('state', filters.window);
        const res = await api.get<DirectoryEventsResponse>(`/directory/events?${params.toString()}`);
        if (append) {
          setEvents((prev) => [...prev, ...res.items]);
        } else {
          setEvents(res.items);
        }
        setEventsTotal(res.total);
        setEventsOffset(offset);
      } catch (e) {
        console.error('Error loading events:', e);
        if (!append) setEvents([]);
        setEventsTotal(0);
      } finally {
        setEventsLoading(false);
      }
    },
    [api, filters.category, filters.tagId, filters.nextDays, filters.window]
  );

  useEffect(() => {
    if (!api) return;
    fetchEvents(0, false);
  }, [api, fetchEvents]);

  const handleLoadMore = useCallback(() => {
    fetchEvents(eventsOffset + EVENTS_PAGE_SIZE, true);
  }, [fetchEvents, eventsOffset]);

  const hasMore = eventsOffset + EVENTS_PAGE_SIZE < eventsTotal;

  // Search filter (client-side on current events)
  const searchLower = filters.search.trim().toLowerCase();
  const displayedEvents =
    searchLower === ''
      ? events
      : events.filter(
          (e) =>
            (e.market_name ?? '').toLowerCase().includes(searchLower) ||
            e.event_id.toLowerCase().includes(searchLower)
        );

  // Payload al guardar: solo actualizamos filtros editables en la UI; preservamos auto_attach, deny_list, Phase 4, etc.
  const fromForm = filtersToUniverse(filters);
  const currentUniverseForSave: UniverseConfig = {
    ...(universe || {}),
    categories: fromForm.categories,
    tags: fromForm.tags,
    time_filter: fromForm.time_filter ?? undefined,
    markets: fromForm.markets,
    events: fromForm.events,
  };
  const hasChanges =
    universeLoaded &&
    universe &&
    (JSON.stringify(currentUniverseForSave.categories) !== JSON.stringify(universe.categories) ||
      JSON.stringify(currentUniverseForSave.tags) !== JSON.stringify(universe.tags) ||
      JSON.stringify(currentUniverseForSave.time_filter) !== JSON.stringify(universe.time_filter));

  const handleSave = useCallback(async () => {
    if (!api || !strategyId) return;
    setSaveError(null);
    setSaving(true);
    const previousUniverse = universe;
    setUniverse({
      ...universe!,
      categories: currentUniverseForSave.categories ?? [],
      tags: currentUniverseForSave.tags ?? [],
      time_filter: currentUniverseForSave.time_filter ?? null,
    });
    try {
      await api.put(`/api/strategies/${strategyId}/universe`, currentUniverseForSave);
      const updated = await api.get<UniverseResponse>(`/api/strategies/${strategyId}/universe`);
      setUniverse(updated.universe);
    } catch (e) {
      setUniverse(previousUniverse ?? null);
      const msg =
        e instanceof ApiResponseError
          ? e.message
          : e instanceof Error
          ? e.message
          : 'Error al guardar el universo';
      setSaveError(msg);
    } finally {
      setSaving(false);
    }
  }, [api, strategyId, universe, currentUniverseForSave]);

  if (!user) return null;

  if (pageError) {
    return (
      <Layout>
        <div className="max-w-[1600px] mx-auto p-4">
          <p className="text-destructive text-sm">{pageError}</p>
          <Link
            href={`/strategies/${strategyId}`}
            className="text-primary text-sm underline mt-2 inline-block"
          >
            Volver a la estrategia
          </Link>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="min-h-screen bg-background flex flex-col">
        <header className="border-b border-border bg-card px-4 py-3 shrink-0">
          <div className="max-w-[1600px] mx-auto flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link
                href={`/strategies/${strategyId}/desk`}
                className="text-muted-foreground hover:text-foreground text-sm"
              >
                ← Desk
              </Link>
              <span className="text-muted-foreground">/</span>
              <h1 className="text-lg font-semibold text-foreground">
                Universe · {strategyName || strategyId}
              </h1>
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 max-w-[1600px] w-full mx-auto">
          {!universeLoaded ? (
            <div className="py-8 text-sm text-muted-foreground">Cargando universo…</div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Columna principal: filtros + lista de eventos */}
              <div className="lg:col-span-2 space-y-4">
                <section>
                  <h2 className="text-sm font-semibold text-foreground mb-2">Filtros</h2>
                  <DirectoryFilters
                    categories={categories}
                    tags={tags}
                    meta={meta}
                    filters={filters}
                    onFiltersChange={setFilters}
                  />
                </section>
                <section>
                  <h2 className="text-sm font-semibold text-foreground mb-2">Eventos elegibles</h2>
                  <DirectoryEventList
                    events={displayedEvents}
                    total={searchLower ? displayedEvents.length : eventsTotal}
                    loading={eventsLoading}
                    limit={EVENTS_PAGE_SIZE}
                    offset={eventsOffset}
                    onLoadMore={handleLoadMore}
                    hasMore={hasMore && searchLower === ''}
                  />
                </section>
              </div>

              {/* Sidebar: resumen y guardar */}
              <div className="lg:col-span-1">
                <UniverseSummary
                  universe={currentUniverseForSave}
                  eligibleCount={eventsTotal}
                  saving={saving}
                  saveError={saveError}
                  onSave={handleSave}
                  hasChanges={!!hasChanges}
                />
              </div>
            </div>
          )}
        </main>
      </div>
    </Layout>
  );
}
