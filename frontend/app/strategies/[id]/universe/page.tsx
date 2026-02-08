'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { initApiClient, createTokenGetter, ApiResponseError } from '@/lib/api';
import {
  DiscoveryClient,
  getDomainBySlug,
  DOMAIN_REGISTRY,
  getTimeBucketMinutes,
  getEndDateMaxIso,
  isValidTimeBucket,
  TIME_BUCKET_MINUTES,
  searchMarkets,
} from '@/lib/discovery';
import type { DiscoveryTradeableMarket } from '@/lib/discovery/types';
import type {
  DirectoryMeta,
  DirectoryTag,
  UniverseConfig,
  UniverseResponse,
  UniverseItem,
} from '@/types/directory';
import {
  DirectoryFilters,
  UniverseSummary,
  type DirectoryFiltersState,
} from '@/components/strategy/universe';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { SidePanel } from '@/components/ui/side-panel';
import { MetricChip } from '@/components/ui/metric-chip';
import { DiscoverySearchBar } from '@/components/markets/DiscoverySearchBar';
import { SortableTableHead } from '@/components/markets/SortableTableHead';
import { Copy, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

const OVERFETCH_LIMIT = 100;
const UI_PAGE_SIZE = 50;
const TTR_FILTER_STRICT = true;

/** Dominios con time bucket (Discovery) para el selector */
const DISCOVERY_DOMAINS = DOMAIN_REGISTRY.filter((d) => d.supportsTimeBucket);
const TIME_BUCKET_SLUGS = Object.keys(TIME_BUCKET_MINUTES);

/** Cache para tags/meta del sidebar (config universo). TTL 5 min. */
const DISCOVERY_CACHE_TTL_MS = 5 * 60 * 1000;
const discoveryCache: {
  meta: DirectoryMeta | null;
  tags: DirectoryTag[];
  expiresAt: number;
} = { meta: null, tags: [], expiresAt: 0 };

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
    categories: [],
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
    tagId: u.tags?.[0] ?? null,
    nextDays: tf?.next_days ?? null,
    window: (tf?.window as DirectoryFiltersState['window']) ?? null,
  };
}

export default function StrategyUniversePage() {
  const params = useParams();
  const user = useUser();
  const stackApp = useStackApp();
  const strategyId = params.id as string;

  const [strategyName, setStrategyName] = useState<string>('');
  const [universe, setUniverse] = useState<UniverseResponse['universe'] | null>(null);
  const [universeLoaded, setUniverseLoaded] = useState(false);
  const [filters, setFilters] = useState<DirectoryFiltersState>({
    search: '',
    tagId: null,
    nextDays: null,
    window: null,
  });
  const [meta, setMeta] = useState<DirectoryMeta | null>(null);
  const [tags, setTags] = useState<DirectoryTag[]>([]);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [deletingItemId, setDeletingItemId] = useState<string | null>(null);

  // Discovery: mismo flujo que /markets/[domain]/[timeBucket]
  const [discoveryDomainSlug, setDiscoveryDomainSlug] = useState<string>(DISCOVERY_DOMAINS[0]?.domainSlug ?? '');
  const [discoveryTimeBucketSlug, setDiscoveryTimeBucketSlug] = useState<string>('15M');
  const [discoveryMarkets, setDiscoveryMarkets] = useState<DiscoveryTradeableMarket[]>([]);
  const [discoveryLoading, setDiscoveryLoading] = useState(false);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [discoveryOffset, setDiscoveryOffset] = useState(0);
  const [discoveryHasMore, setDiscoveryHasMore] = useState(false);
  const [discoverySearchQuery, setDiscoverySearchQuery] = useState('');
  const [selectedMarket, setSelectedMarket] = useState<DiscoveryTradeableMarket | null>(null);
  const [addingToUniverse, setAddingToUniverse] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<string | null>('liquidity');
  const [sortAsc, setSortAsc] = useState(false);

  const api = useMemo(
    () => (user && stackApp ? initApiClient(createTokenGetter(user, stackApp)) : null),
    [user?.id ?? '', !!stackApp]
  );

  const domain = getDomainBySlug(discoveryDomainSlug);
  const ttrMinutes = getTimeBucketMinutes(discoveryTimeBucketSlug);
  const discoveryValid = domain?.gammaTagSlug && isValidTimeBucket(discoveryTimeBucketSlug);

  const fetchDiscoveryMarkets = useCallback(
    async (off: number, append: boolean) => {
      if (!domain?.gammaTagSlug || !user || !stackApp) return;
      setDiscoveryLoading(true);
      setDiscoveryError(null);
      try {
        const client = new DiscoveryClient(createTokenGetter(user, stackApp));
        const endDateMax = ttrMinutes != null ? getEndDateMaxIso(ttrMinutes) : undefined;
        const result = await client.fetchDiscovery({
          tag_slug: domain.gammaTagSlug,
          closed: false,
          limit: OVERFETCH_LIMIT,
          offset: off,
          end_date_max: endDateMax ?? undefined,
        });

        let filtered = result.markets;
        if (TTR_FILTER_STRICT && ttrMinutes != null) {
          filtered = result.markets.filter((m) => {
            const ttr = m.time_to_resolution_minutes;
            return ttr != null && ttr >= 0 && ttr <= ttrMinutes;
          });
        }

        setDiscoveryMarkets((prev) => (append ? [...prev, ...filtered] : filtered));
        setDiscoveryHasMore(result.markets.length >= OVERFETCH_LIMIT);
      } catch (e) {
        setDiscoveryError(e instanceof Error ? e.message : 'Error al cargar');
        setDiscoveryMarkets([]);
      } finally {
        setDiscoveryLoading(false);
      }
    },
    [domain, ttrMinutes, user, stackApp]
  );

  useEffect(() => {
    if (discoveryValid && user && stackApp) {
      fetchDiscoveryMarkets(0, false);
      setDiscoveryOffset(0);
    } else {
      setDiscoveryMarkets([]);
      setDiscoveryHasMore(false);
    }
  }, [discoveryValid, discoveryDomainSlug, discoveryTimeBucketSlug, user?.id, !!stackApp]);

  // Cargar estrategia y universo
  useEffect(() => {
    const id = (strategyId ?? '').trim();
    if (!api || !id || id === 'undefined') return;
    let cancelled = false;
    setPageError(null);
    (async () => {
      const strategyRes = await api.get<{ name: string }>(`/api/strategies/${id}`).catch(() => ({ name: '' }));
      if (cancelled) return;
      const universeRes = await api.get<UniverseResponse>(`/api/strategies/${id}/universe`, { returnNullOn404: true });
      if (cancelled) return;
      if (universeRes === null) {
        setPageError(
          'Estrategia no encontrada. Si acabas de crear una nueva, entra desde el listado de estrategias para usar la URL correcta.'
        );
        setUniverseLoaded(true);
        return;
      }
      setStrategyName(strategyRes?.name ?? '');
      setUniverse(universeRes.universe);
      setFilters(universeToFilters(universeRes.universe));
      setUniverseLoaded(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [api, strategyId]);

  // Tags/meta para sidebar (config universo)
  useEffect(() => {
    if (!api) return;
    const now = Date.now();
    if (discoveryCache.expiresAt > now) {
      setMeta(discoveryCache.meta);
      setTags(discoveryCache.tags);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const [metaRes, tagsGammaRes] = await Promise.all([
          api.get<DirectoryMeta>('/directory/meta').catch(() => null),
          api
            .get<{ items: Array<{ tag_id: string; name?: string; slug?: string; label?: string }> }>(
              '/api/polymarket/tags?limit=200&offset=0'
            )
            .catch(() => ({ items: [] })),
        ]);
        if (cancelled) return;
        const tagItems = tagsGammaRes?.items ?? [];
        const mappedTags: DirectoryTag[] = tagItems.map((t) => ({
          tag_id: t.tag_id,
          polymarket_tag_id: t.tag_id,
          name: t.name ?? t.label ?? t.tag_id,
          slug: t.slug ?? null,
          label: t.label ?? t.name ?? t.tag_id,
        }));
        discoveryCache.meta = metaRes ?? null;
        discoveryCache.tags = mappedTags;
        discoveryCache.expiresAt = now + DISCOVERY_CACHE_TTL_MS;
        setMeta(discoveryCache.meta);
        setTags(discoveryCache.tags);
      } catch (e) {
        if (!cancelled) console.error('Error loading tags/meta:', e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [api]);

  const handleAddToUniverse = useCallback(
    async (market: DiscoveryTradeableMarket) => {
      if (!api || !strategyId) {
        toast.error('No se puede añadir');
        return;
      }
      setAddingToUniverse(market.polymarket_id);
      try {
        await api.post(`/api/strategies/${strategyId}/universe/markets`, {
          market_id: market.polymarket_id,
        });
        toast.success('Añadido al universo');
        setSelectedMarket(null);
        const updated = await api.get<UniverseResponse>(`/api/strategies/${strategyId}/universe`);
        setUniverse(updated?.universe ?? null);
      } catch (e) {
        const msg =
          e instanceof ApiResponseError ? e.message : e instanceof Error ? e.message : 'Error al añadir';
        toast.error(msg);
      } finally {
        setAddingToUniverse(null);
      }
    },
    [api, strategyId]
  );

  const handleCopyTokenId = async (tokenId: string) => {
    await navigator.clipboard.writeText(tokenId);
    toast.success('Token copiado');
  };

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortAsc((a) => !a);
    } else {
      setSortBy(key);
      setSortAsc(key === 'question');
    }
  };

  const searched =
    discoverySearchQuery.trim() ? searchMarkets(discoveryMarkets, discoverySearchQuery) : discoveryMarkets;
  const displayedMarkets = [...searched].sort((a, b) => {
    if (!sortBy) return 0;
    let cmp = 0;
    if (sortBy === 'question') {
      cmp = (a.question || '').localeCompare(b.question || '');
    } else if (sortBy === 'ttr') {
      const va = a.time_to_resolution_minutes ?? 999999;
      const vb = b.time_to_resolution_minutes ?? 999999;
      cmp = va - vb;
    } else if (sortBy === 'volume24hr') {
      cmp = (a.volume24hr ?? 0) - (b.volume24hr ?? 0);
    } else if (sortBy === 'liquidity') {
      cmp = (a.liquidity ?? 0) - (b.liquidity ?? 0);
    }
    return sortAsc ? cmp : -cmp;
  });

  const universeItems: UniverseItem[] = universe?.items ?? [];

  const handleDeleteUniverseItem = useCallback(
    async (itemId: string) => {
      if (!api || !strategyId) return;
      setDeletingItemId(itemId);
      try {
        await api.delete(`/api/strategies/${strategyId}/universe/items/${itemId}`);
        const updated = await api.get<UniverseResponse>(`/api/strategies/${strategyId}/universe`);
        setUniverse(updated?.universe ?? null);
      } catch (e) {
        console.error('Error deleting universe item:', e);
      } finally {
        setDeletingItemId(null);
      }
    },
    [api, strategyId]
  );

  const fromForm = filtersToUniverse(filters);
  const currentUniverseForSave: UniverseConfig = {
    ...(universe || {}),
    categories: fromForm.categories,
    tags: fromForm.tags,
    time_filter: fromForm.time_filter ?? undefined,
    markets: fromForm.markets ?? [],
    events: fromForm.events ?? [],
  };
  const hasChanges =
    universeLoaded &&
    universe &&
    (JSON.stringify(currentUniverseForSave.tags) !== JSON.stringify(universe.tags) ||
      JSON.stringify(currentUniverseForSave.time_filter) !== JSON.stringify(universe.time_filter));

  const handleSave = useCallback(async () => {
    if (!api || !strategyId) return;
    setSaveError(null);
    setSaving(true);
    const previousUniverse = universe;
    setUniverse({
      ...universe!,
      tags: currentUniverseForSave.tags ?? [],
      time_filter: currentUniverseForSave.time_filter ?? null,
    });
    try {
      await api.put(`/api/strategies/${strategyId}/universe`, currentUniverseForSave);
      const updated = await api.get<UniverseResponse>(`/api/strategies/${strategyId}/universe`);
      setUniverse(updated?.universe ?? null);
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

  const loadMoreDiscovery = () => {
    const nextOffset = discoveryOffset + OVERFETCH_LIMIT;
    setDiscoveryOffset(nextOffset);
    fetchDiscoveryMarkets(nextOffset, true);
  };

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
              {/* Columna principal: Discovery (igual que /markets/[domain]/[timeBucket]) */}
              <div className="lg:col-span-2 space-y-4">
                <section>
                  <h2 className="text-sm font-semibold text-foreground mb-2">
                    Añadir mercados desde Discovery
                  </h2>
                  <p className="text-xs text-muted-foreground mb-3">
                    Misma fuente que Discovery: elige categoría y ventana de tiempo hasta resolución (TTR).
                  </p>
                  <div className="flex flex-wrap items-center gap-2">
                    <Select
                      value={discoveryDomainSlug}
                      onValueChange={(v) => setDiscoveryDomainSlug(v)}
                    >
                      <SelectTrigger className="w-[140px] bg-background">
                        <SelectValue placeholder="Categoría" />
                      </SelectTrigger>
                      <SelectContent>
                        {DISCOVERY_DOMAINS.map((d) => (
                          <SelectItem key={d.domainSlug} value={d.domainSlug}>
                            {d.domainSlug}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Select
                      value={discoveryTimeBucketSlug}
                      onValueChange={(v) => setDiscoveryTimeBucketSlug(v)}
                    >
                      <SelectTrigger className="w-[100px] bg-background">
                        <SelectValue placeholder="TTR" />
                      </SelectTrigger>
                      <SelectContent>
                        {TIME_BUCKET_SLUGS.map((b) => (
                          <SelectItem key={b} value={b}>
                            {b}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => fetchDiscoveryMarkets(0, false)}
                      disabled={discoveryLoading}
                    >
                      <RefreshCw className={`h-4 w-4 mr-1 ${discoveryLoading ? 'animate-spin' : ''}`} />
                      Actualizar
                    </Button>
                  </div>
                </section>

                <DiscoverySearchBar
                  value={discoverySearchQuery}
                  onChange={setDiscoverySearchQuery}
                  placeholder="Buscar (btc, bitcoin...)"
                />

                {discoveryError && (
                  <p className="text-sm text-destructive">{discoveryError}</p>
                )}

                {discoveryLoading && discoveryMarkets.length === 0 ? (
                  <div className="space-y-2">
                    {[...Array(8)].map((_, i) => (
                      <div key={i} className="h-10 bg-muted animate-pulse rounded" />
                    ))}
                  </div>
                ) : (
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <SortableTableHead
                            label="Market"
                            sortKey="question"
                            currentSortBy={sortBy}
                            sortAsc={sortAsc}
                            onSort={handleSort}
                          />
                          <SortableTableHead
                            label="TTR"
                            sortKey="ttr"
                            currentSortBy={sortBy}
                            sortAsc={sortAsc}
                            onSort={handleSort}
                          />
                          <SortableTableHead
                            label="Vol 24h"
                            sortKey="volume24hr"
                            currentSortBy={sortBy}
                            sortAsc={sortAsc}
                            onSort={handleSort}
                          />
                          <SortableTableHead
                            label="Liquidity"
                            sortKey="liquidity"
                            currentSortBy={sortBy}
                            sortAsc={sortAsc}
                            onSort={handleSort}
                          />
                          <TableHead>Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {discoveryMarkets.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                              Elige categoría y TTR y pulsa Actualizar, o no hay mercados con estos filtros.
                            </TableCell>
                          </TableRow>
                        ) : (
                          displayedMarkets.slice(0, UI_PAGE_SIZE).map((m) => (
                            <TableRow
                              key={m.market_id}
                              className="cursor-pointer"
                              onClick={() => setSelectedMarket(m)}
                            >
                              <TableCell>
                                <div>
                                  <span className="font-medium text-sm">{m.question}</span>
                                  {m.event_title && (
                                    <p className="text-xs text-muted-foreground truncate max-w-md">
                                      {m.event_title}
                                    </p>
                                  )}
                                </div>
                              </TableCell>
                              <TableCell>
                                {m.time_to_resolution_minutes != null ? (
                                  <MetricChip
                                    label="TTR"
                                    value={`${Math.round(m.time_to_resolution_minutes)}m`}
                                  />
                                ) : (
                                  '—'
                                )}
                              </TableCell>
                              <TableCell>
                                {m.volume24hr != null && m.volume24hr > 0 ? (
                                  <span className="text-sm">
                                    ${(m.volume24hr / 1000).toFixed(1)}k
                                  </span>
                                ) : (
                                  '—'
                                )}
                              </TableCell>
                              <TableCell>
                                {m.liquidity != null && m.liquidity > 0 ? (
                                  <span className="text-sm">
                                    ${(m.liquidity / 1000).toFixed(1)}k
                                  </span>
                                ) : (
                                  '—'
                                )}
                              </TableCell>
                              <TableCell>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  disabled={!!addingToUniverse}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleAddToUniverse(m);
                                  }}
                                >
                                  {addingToUniverse === m.polymarket_id ? '…' : 'Add to Universe'}
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </div>
                )}

                {discoveryHasMore && (
                  <Button variant="outline" onClick={loadMoreDiscovery} disabled={discoveryLoading}>
                    Cargar más
                  </Button>
                )}
              </div>

              {/* Sidebar: config universo + items + guardar */}
              <div className="lg:col-span-1 space-y-4">
                {universeItems.length > 0 && (
                  <section>
                    <h2 className="text-sm font-semibold text-foreground mb-2">Items en tu universo</h2>
                    <ul className="space-y-1.5 text-sm">
                      {universeItems.map((it) => (
                        <li
                          key={it.id}
                          className="flex items-center justify-between gap-2 py-1.5 px-2 rounded bg-muted/50 border border-border"
                        >
                          <span className="truncate">
                            <span className="font-medium capitalize">{it.type}</span>: {it.ref_id}
                            {it.include_future && ' (auto)'}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleDeleteUniverseItem(it.id)}
                            disabled={deletingItemId === it.id}
                            className="shrink-0 text-destructive hover:underline text-xs"
                          >
                            {deletingItemId === it.id ? '…' : 'Quitar'}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </section>
                )}
                <section>
                  <h2 className="text-sm font-semibold text-foreground mb-2">Configuración del universo</h2>
                  <DirectoryFilters
                    tags={tags}
                    meta={meta}
                    filters={filters}
                    onFiltersChange={setFilters}
                  />
                </section>
                <UniverseSummary
                  universe={currentUniverseForSave}
                  eligibleCount={discoveryMarkets.length}
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

      <SidePanel
        open={!!selectedMarket}
        onClose={() => setSelectedMarket(null)}
        title={selectedMarket?.question}
      >
        {selectedMarket && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">{selectedMarket.event_title}</p>
            {selectedMarket.clob_token_ids?.primary_yes && (
              <div className="flex items-center gap-2">
                <code className="text-xs bg-muted px-2 py-1 rounded truncate flex-1">
                  {selectedMarket.clob_token_ids.primary_yes.slice(0, 20)}...
                </code>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleCopyTokenId(selectedMarket.clob_token_ids!.primary_yes!)}
                >
                  <Copy className="h-3 w-3" />
                </Button>
              </div>
            )}
            <Button
              size="sm"
              className="w-full"
              disabled={!!addingToUniverse}
              onClick={() => handleAddToUniverse(selectedMarket)}
            >
              {addingToUniverse ? 'Añadiendo…' : 'Add to Strategy Universe'}
            </Button>
          </div>
        )}
      </SidePanel>
    </Layout>
  );
}
