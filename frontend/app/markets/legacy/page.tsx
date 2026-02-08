'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter, ApiResponseError } from '@/lib/api';
import { toast } from 'sonner';
import type { Strategy } from '@/types/strategy';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { SidePanel } from '@/components/ui/side-panel';
import { Badge } from '@/components/ui/badge';
import { Copy, Check, ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import { MetricChip } from '@/components/ui/metric-chip';
import { Panel } from '@/components/ui/panel';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import Link from 'next/link';

interface ClobTokenIds {
  primary_yes?: string | null;
  primary_no?: string | null;
  primary?: string | null;
  selection_hint?: string;
  clob_token_ids_all?: string[] | null;
  clob_token_ids_by_key?: Record<string, string> | null;
}

interface Market {
  market_id: string;
  polymarket_id: string;
  name: string;
  category: string | null;
  enabled: boolean;
  series_id: string | null;
  series_name: string | null;
  tags: Array<{ tag_id: string; name: string }>;
  clob_token_ids?: ClobTokenIds;
  events_count: number;
  polymarket_payload?: {
    clobTokenIds?: { YES?: string; NO?: string } | string[];
    outcomes?: Array<{ outcome: string; token_id?: string }>;
  };
  spread?: number | null;
  bestBid?: number | null;
  bestAsk?: number | null;
}

export interface MarketsPaginationMeta {
  hasMore: boolean;
  offset: number;
  limit: number;
  partialPage?: boolean;
  partialReason?: string;
  orderEffective?: string;
  cache?: string;
  cacheAge?: number;
  cacheProvider?: string;
}

interface MarketsData {
  markets: Market[];
  orderbookMetrics?: Record<string, unknown>;
  pagination?: MarketsPaginationMeta;
  _unavailableReason?: string;
  _debug?: { statusCode: number; latencyMs: number; hasMore: string; partialPage: string; cache: string; cacheAge: string };
}

interface TagOption {
  tag_id: string;
  name: string;
  slug?: string;
}

interface SeriesOption {
  series_id: string;
  name: string;
  slug?: string | null;
  markets_count?: number;
}

const DEFAULT_LIMIT = typeof process !== 'undefined' && process.env.NEXT_PUBLIC_MARKETS_PAGE_SIZE
  ? Math.max(10, Math.min(100, parseInt(process.env.NEXT_PUBLIC_MARKETS_PAGE_SIZE, 10) || 25))
  : 25;
const DEFAULT_ORDER = 'createdAt';
const VISIBILITY_REFETCH_DEBOUNCE_MS = 5000;
const VISIBILITY_REFETCH_MIN_INTERVAL_MS = 15000;
const REFRESH_BUTTON_COOLDOWN_MS = 8000;
const CACHE_TTL_MS = 10 * 60 * 1000;
const CACHE_THRESHOLD_FOR_FILTER = 8;
const SEARCH_DEBOUNCE_MS = 500;

const marketsPageCache: {
  tags: { data: TagOption[] | null; expiresAt: number };
  series: { data: SeriesOption[] | null; expiresAt: number };
} = {
  tags: { data: null, expiresAt: 0 },
  series: { data: null, expiresAt: 0 },
};

export default function MarketsLegacyPage() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const { isDemo } = useDataMode();
  const searchParams = useSearchParams();

  const [searchTerm, setSearchTerm] = useState('');
  const [searchDebounced, setSearchDebounced] = useState('');
  const [limit, setLimit] = useState(DEFAULT_LIMIT);
  const [offset, setOffset] = useState(0);
  const [lastFetchedAt, setLastFetchedAt] = useState<number | null>(null);
  const [refreshCooldownUntil, setRefreshCooldownUntil] = useState<number>(0);
  const [tick, setTick] = useState(() => Date.now());
  const lastRefetchTriggeredRef = useRef<number>(0);
  const visibilityDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [order, setOrder] = useState(DEFAULT_ORDER);
  const [ascending, setAscending] = useState(false);
  const [tagId, setTagId] = useState<string>('');
  const [seriesId, setSeriesId] = useState<string>('');
  const [enabledFilter, setEnabledFilter] = useState<boolean | ''>('');
  const [tagOptions, setTagOptions] = useState<TagOption[]>([]);
  const [seriesOptions, setSeriesOptions] = useState<SeriesOption[]>([]);
  const [seriesLoadFailed, setSeriesLoadFailed] = useState(false);
  const [tagFilterInput, setTagFilterInput] = useState('');
  const [seriesFilterInput, setSeriesFilterInput] = useState('');
  const [selectedMarket, setSelectedMarket] = useState<Market | null>(null);
  const [copiedTokenId, setCopiedTokenId] = useState<string | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>('');
  const [addingToUniverse, setAddingToUniverse] = useState<string | null>(null);
  const strategySelectRef = useRef<HTMLButtonElement | null>(null);
  const lastSuccessfulDataRef = useRef<Omit<MarketsData, '_unavailableReason' | '_debug'> | null>(null);

  const marketsFetchEnabled = !isDemo && (!!tagId || !!seriesId || searchDebounced.trim() !== '');

  useEffect(() => {
    if (lastFetchedAt == null) return;
    const id = setInterval(() => setTick(Date.now()), 1000);
    return () => clearInterval(id);
  }, [lastFetchedAt]);

  const marketsParams = useCallback(() => {
    const params: Record<string, string> = {
      limit: String(limit),
      offset: String(offset),
      order,
      ascending: String(ascending),
      closed: 'false',
    };
    if (tagId) params.tag_id = tagId;
    if (seriesId) params.series_id = seriesId;
    if (enabledFilter === true) params.enabled = 'true';
    if (enabledFilter === false) params.enabled = 'false';
    if (searchDebounced.trim()) params.search = searchDebounced.trim();
    return params;
  }, [limit, offset, order, ascending, tagId, seriesId, enabledFilter, searchDebounced]);

  const { data, error, renderSkeleton, refetch, isRefreshing } = useComponentDataLoader<MarketsData>({
    fetchFn: async (signal) => {
      if (isDemo) {
        return { markets: [], orderbookMetrics: {}, pagination: { hasMore: false, offset: 0, limit, partialPage: false } };
      }
      const api = initApiClient(createTokenGetter(user ?? undefined, stackApp ?? undefined));
      const params = marketsParams();
      const startMs = typeof performance !== 'undefined' ? performance.now() : 0;
      try {
        const { data: rawResponse, headers } = await api.getWithHeaders<Market[] | { items?: Market[] }>('/markets', {
          params,
          signal,
        });
        const list: Market[] = Array.isArray(rawResponse)
          ? rawResponse
          : (rawResponse && typeof rawResponse === 'object' && Array.isArray((rawResponse as { items?: Market[] }).items)
            ? (rawResponse as { items: Market[] }).items
            : []);
        const latencyMs = typeof performance !== 'undefined' ? Math.round(performance.now() - startMs) : 0;
        const hasMore = (headers.get('X-Has-More') ?? '').toLowerCase() === 'true';
        const respOffset = parseInt(headers.get('X-Offset') ?? String(offset), 10);
        const respLimit = parseInt(headers.get('X-Limit') ?? String(limit), 10);
        const partialPage = (headers.get('X-Partial-Page') ?? '').toLowerCase() === 'true';
        const partialReason = headers.get('X-Partial-Reason') ?? undefined;
        const orderEffective = headers.get('X-Order-Effective') ?? undefined;
        const cache = headers.get('X-Cache') ?? undefined;
        const cacheAgeStr = headers.get('X-Cache-Age');
        const cacheAge = cacheAgeStr != null ? parseInt(cacheAgeStr, 10) : undefined;
        const cacheProvider = headers.get('X-Cache-Provider') ?? undefined;
        const paginationMeta: MarketsPaginationMeta = {
          hasMore,
          offset: respOffset,
          limit: respLimit,
          partialPage: partialPage || undefined,
          partialReason: partialReason || undefined,
          orderEffective: orderEffective || undefined,
          cache: cache || undefined,
          cacheAge: Number.isNaN(cacheAge as number) ? undefined : (cacheAge as number),
          cacheProvider: cacheProvider || undefined,
        };
        const tokenIds = list
          .map((m) => m.clob_token_ids?.primary ?? m.clob_token_ids?.primary_yes)
          .filter((id): id is string => !!id)
          .slice(0, limit);
        const tokenIdsParam = tokenIds.length > 0 ? tokenIds.join(',') : '';
        let orderbookMetrics: Record<string, unknown> = {};
        if (tokenIdsParam && user && stackApp) {
          try {
            const obResponse = await api.get<{ metrics?: Record<string, unknown> }>(
              `/markets/orderbook-metrics?token_ids=${encodeURIComponent(tokenIdsParam)}`,
              { signal }
            );
            orderbookMetrics = obResponse?.metrics ?? {};
          } catch {
            orderbookMetrics = {};
          }
        }
        const result: Omit<MarketsData, '_unavailableReason' | '_debug'> = {
          markets: list,
          orderbookMetrics,
          pagination: paginationMeta,
        };
        lastSuccessfulDataRef.current = result;
        return result;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        const isSoftError =
          (err instanceof ApiResponseError && err.statusCode === 503) ||
          /gamma\s*timeout|temporarily\s*unavailable/i.test(msg);
        const stale = lastSuccessfulDataRef.current;
        if (isSoftError && stale) {
          return {
            ...stale,
            _unavailableReason: msg,
            _debug: process.env.NODE_ENV === 'development' ? { statusCode: 0, latencyMs: 0, hasMore: '—', partialPage: '—', cache: '—', cacheAge: '—' } : undefined,
          } as MarketsData;
        }
        throw err;
      }
    },
    dependencies: [isDemo, limit, offset, order, ascending, tagId, seriesId, enabledFilter, searchDebounced],
    refreshInterval: 0,
    enabled: marketsFetchEnabled,
    onSuccess: () => setLastFetchedAt(Date.now()),
    showSkeleton: true,
    skeletonComponent: () => (
      <div className="space-y-2">
        {[...Array(10)].map((_, i) => (
          <div key={i} className="h-9 bg-muted animate-pulse rounded" />
        ))}
      </div>
    ),
  });

  useEffect(() => {
    const t = setTimeout(() => {
      setSearchDebounced(searchTerm);
      setOffset(0);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [searchTerm]);

  useEffect(() => {
    const fromUrl = searchParams?.get('tag_id');
    if (fromUrl) return;
    try {
      const stored = localStorage.getItem('markets_selected_tag_id');
      const envDefault = (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_MARKETS_DEFAULT_TAG_ID)?.trim() ?? '';
      const initial = stored || envDefault || '';
      if (initial) setTagId(initial);
    } catch {}
  }, []);

  useEffect(() => {
    const fromUrl = searchParams?.get('strategy_id');
    if (fromUrl) {
      setSelectedStrategyId(fromUrl);
      try {
        localStorage.setItem('markets_selected_strategy_id', fromUrl);
      } catch {}
      return;
    }
    try {
      const fromStorage = localStorage.getItem('markets_selected_strategy_id');
      if (fromStorage) setSelectedStrategyId(fromStorage);
    } catch {}
  }, [searchParams]);

  useEffect(() => {
    const fromUrl = searchParams?.get('tag_id');
    if (fromUrl) {
      setTagId(fromUrl);
      setOffset(0);
    }
  }, [searchParams]);

  useEffect(() => {
    if (isDemo) return;
    const now = Date.now();
    if (marketsPageCache.tags.data && marketsPageCache.tags.expiresAt > now) {
      setTagOptions(marketsPageCache.tags.data);
      return;
    }
    const ac = new AbortController();
    const api = initApiClient(createTokenGetter(user ?? undefined, stackApp ?? undefined));
    api
      .get<{ items?: TagOption[] }>('/api/polymarket/tags?limit=200&offset=0', { silent: true, signal: ac.signal })
      .then((res) => {
        const items = res?.items ?? [];
        const list = Array.isArray(items) ? items : [];
        if (list.length > 0) {
          marketsPageCache.tags = { data: list, expiresAt: now + CACHE_TTL_MS };
          setTagOptions(list);
        } else {
          api
            .get<Market[]>('/markets', {
              params: { limit: '50', offset: '0', order: 'createdAt', ascending: 'false', closed: 'false' },
              silent: true,
              signal: ac.signal,
            })
            .then((marketsData) => {
              const markets = Array.isArray(marketsData) ? marketsData : [];
              const seen = new Set<string>();
              const derived: TagOption[] = [];
              for (const m of markets) {
                for (const t of (m as Market).tags ?? []) {
                  const id = (t as { tag_id?: string; name?: string }).tag_id ?? (t as { tag_id?: string; name?: string }).name ?? '';
                  if (id && !seen.has(id)) {
                    seen.add(id);
                    derived.push({ tag_id: id, name: (t as { name?: string }).name ?? id });
                  }
                }
              }
              if (derived.length > 0) {
                marketsPageCache.tags = { data: derived, expiresAt: now + CACHE_TTL_MS };
                setTagOptions(derived);
              }
            })
            .catch(() => {});
        }
      })
      .catch(() => {});
    return () => ac.abort();
  }, [isDemo, user, stackApp]);

  useEffect(() => {
    if (isDemo) return;
    setSeriesLoadFailed(false);
    const now = Date.now();
    if (marketsPageCache.series.data && marketsPageCache.series.expiresAt > now) {
      setSeriesOptions(marketsPageCache.series.data);
      return;
    }
    const api = initApiClient(createTokenGetter(user ?? undefined, stackApp ?? undefined));
    api.get<SeriesOption[] | { series_id: string; name: string; slug?: string }[]>('/series', true)
      .then((raw) => {
        const list = Array.isArray(raw) ? raw : [];
        const options: SeriesOption[] = list.map((s: { series_id?: string; id?: string; name?: string; slug?: string; markets_count?: number }) => ({
          series_id: s.series_id ?? s.id ?? '',
          name: s.name ?? '',
          slug: s.slug ?? null,
          markets_count: s.markets_count,
        })).filter((s) => s.series_id);
        marketsPageCache.series = { data: options, expiresAt: now + CACHE_TTL_MS };
        setSeriesOptions(options);
      })
      .catch(() => {
        setSeriesOptions([]);
        setSeriesLoadFailed(true);
      });
  }, [isDemo, user, stackApp]);

  useEffect(() => {
    if (!user || !stackApp || isDemo) return;
    const api = initApiClient(createTokenGetter(user, stackApp));
    api.get<Strategy[]>('/api/strategies', true).then((list) => {
      setStrategies(Array.isArray(list) ? list : []);
    }).catch(() => setStrategies([]));
  }, [user, stackApp, isDemo]);

  useEffect(() => {
    if (isDemo) return;
    const onVisibility = () => {
      if (document.visibilityState !== 'visible') return;
      const now = Date.now();
      if (now - lastRefetchTriggeredRef.current < VISIBILITY_REFETCH_DEBOUNCE_MS) return;
      if (lastFetchedAt == null) return;
      if (now - lastFetchedAt < VISIBILITY_REFETCH_MIN_INTERVAL_MS) return;
      lastRefetchTriggeredRef.current = now;
      refetch();
    };
    const handler = () => {
      if (visibilityDebounceRef.current) clearTimeout(visibilityDebounceRef.current);
      visibilityDebounceRef.current = setTimeout(onVisibility, 300);
    };
    document.addEventListener('visibilitychange', handler);
    return () => {
      document.removeEventListener('visibilitychange', handler);
      if (visibilityDebounceRef.current) clearTimeout(visibilityDebounceRef.current);
    };
  }, [isDemo, refetch, lastFetchedAt]);

  const handleRefresh = useCallback(() => {
    const now = Date.now();
    if (now < refreshCooldownUntil) return;
    setRefreshCooldownUntil(now + REFRESH_BUTTON_COOLDOWN_MS);
    lastRefetchTriggeredRef.current = now;
    refetch();
  }, [refetch, refreshCooldownUntil]);

  const handleCopyTokenId = async (tokenId: string) => {
    await navigator.clipboard.writeText(tokenId);
    setCopiedTokenId(tokenId);
    setTimeout(() => setCopiedTokenId(null), 2000);
  };

  const handleAddToUniverse = async (market: Market) => {
    if (!selectedStrategyId || !user || !stackApp || isDemo) {
      if (!selectedStrategyId) {
        toast.error('Selecciona una estrategia para añadir el market');
        strategySelectRef.current?.focus();
      }
      return;
    }
    const marketId = market.polymarket_id ?? market.market_id;
    setAddingToUniverse(marketId);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      const res = await api.post<{ added?: boolean }>(
        `/api/strategies/${selectedStrategyId}/universe/markets`,
        { market_id: marketId }
      );
      const added = res?.added ?? true;
      toast.success(added ? 'Añadido al universo' : 'Ya estaba en el universo');
      if (selectedMarket?.polymarket_id === marketId || selectedMarket?.market_id === marketId) {
        setSelectedMarket(null);
      }
    } catch (e) {
      if (e instanceof ApiResponseError) {
        if (e.statusCode === 400) toast.error('Market deshabilitado internamente');
        else if (e.statusCode === 404) toast.error('Estrategia no encontrada');
        else toast.error(e.message);
      } else {
        toast.error(e instanceof Error ? e.message : 'Error al añadir');
      }
    } finally {
      setAddingToUniverse(null);
    }
  };

  function getTokenSelectionPolicy(market: Market): {
    tokenForMetrics: string | null;
    selectionHint: string;
    displayLabel?: string;
  } {
    const c = market.clob_token_ids;
    const hint = (c?.selection_hint ?? 'none') as string;
    const primary = c?.primary ?? null;
    const tokenForMetrics = primary && String(primary).trim() ? String(primary) : null;
    let displayLabel: string | undefined;
    if (hint === 'none') displayLabel = 'Token IDs unavailable';
    else if (hint === 'multi') displayLabel = 'Multi (sampled)';
    return { tokenForMetrics, selectionHint: hint, displayLabel };
  }

  function getSpreadDisplay(
    market: Market,
    orderbookData: Record<string, unknown> | null | undefined
  ): { value: string; color: string } {
    const spread = market.spread;
    if (spread != null && typeof spread === 'number') {
      const bps = Math.round(spread);
      return { value: `${bps} bps`, color: bps < 50 ? 'green' : bps < 150 ? 'yellow' : 'red' };
    }
    const bid = market.bestBid;
    const ask = market.bestAsk;
    if (bid != null && ask != null && typeof bid === 'number' && typeof ask === 'number') {
      const bps = Math.round((ask - bid) * 10000);
      return { value: `${bps} bps`, color: bps < 50 ? 'green' : bps < 150 ? 'yellow' : 'red' };
    }
    const obBps = orderbookData?.spread_bps as number | undefined;
    if (obBps != null) {
      return { value: `${Math.round(obBps)} bps`, color: obBps < 50 ? 'green' : obBps < 150 ? 'yellow' : 'red' };
    }
    return { value: '—', color: 'neutral' };
  }

  const getClobTokenIds = (market: Market): { YES?: string; NO?: string } => {
    const c = market.clob_token_ids;
    if (c?.primary_yes != null || c?.primary_no != null || c?.primary != null) {
      return {
        YES: (c.primary_yes ?? c.primary) ?? undefined,
        NO: c.primary_no ?? undefined,
      };
    }
    const payload = market.polymarket_payload;
    if (!payload?.clobTokenIds) return {};
    if (Array.isArray(payload.clobTokenIds)) {
      return { YES: payload.clobTokenIds[0], NO: payload.clobTokenIds[1] };
    }
    if (typeof payload.clobTokenIds === 'object') {
      return payload.clobTokenIds as { YES?: string; NO?: string };
    }
    return {};
  };

  const filteredMarkets = data?.markets ?? [];
  const pagination = data?.pagination;
  const hasMore = pagination?.hasMore ?? false;
  const currentOffset = pagination?.offset ?? offset;
  const showPartialMessage = pagination?.partialPage === true;
  const showStaleBadge = pagination?.cache === 'stale';
  const unavailableReason = data?._unavailableReason;
  const showUnavailableBanner = !!unavailableReason;
  const showHardError = !!error && !data;
  const showInitialPrompt = !isDemo && !data && !error && !marketsFetchEnabled;

  const tagFilterLower = tagFilterInput.trim().toLowerCase();
  const filteredTagOptions = tagFilterLower
    ? tagOptions.filter((t) => (t.name || t.tag_id).toLowerCase().includes(tagFilterLower))
    : tagOptions;
  const seriesFilterLower = seriesFilterInput.trim().toLowerCase();
  const filteredSeriesOptions = seriesFilterLower
    ? seriesOptions.filter((s) => (s.name || s.series_id).toLowerCase().includes(seriesFilterLower))
    : seriesOptions;

  return (
    <Layout>
      <div className="space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          <Link href="/markets" className="text-sm text-muted-foreground hover:text-foreground">
            ← Volver a Discovery
          </Link>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Input
            placeholder="Buscar (por nombre, ~500ms)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 min-w-[200px]"
          />
          <Select
            value={seriesId || 'all'}
            onValueChange={(v) => {
              setSeriesId(v === 'all' ? '' : v);
              setOffset(0);
            }}
            onOpenChange={(open) => { if (!open) setSeriesFilterInput(''); }}
            disabled={seriesLoadFailed}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder={seriesLoadFailed ? 'Series (no disponible)' : 'Serie (colección)'} />
            </SelectTrigger>
            <SelectContent>
              {seriesOptions.length > CACHE_THRESHOLD_FOR_FILTER && (
                <div className="p-2 border-b border-border">
                  <Input
                    placeholder="Buscar serie..."
                    value={seriesFilterInput}
                    onChange={(e) => setSeriesFilterInput(e.target.value)}
                    className="h-8 text-sm bg-background text-foreground"
                    onPointerDown={(e) => e.stopPropagation()}
                  />
                </div>
              )}
              <SelectItem value="all">Todas las series</SelectItem>
              {filteredSeriesOptions.length === 0 ? (
                <div className="py-2 px-2 text-sm text-muted-foreground">Ninguna coincidencia</div>
              ) : (
                filteredSeriesOptions.map((s) => (
                  <SelectItem key={s.series_id} value={s.series_id}>
                    {s.name || s.series_id}
                    {s.markets_count != null ? ` (${s.markets_count})` : ''}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
          <Select
            value={tagId || 'all'}
            onValueChange={(v) => {
              setTagId(v === 'all' ? '' : v);
              setOffset(0);
            }}
            onOpenChange={(open) => { if (!open) setTagFilterInput(''); }}
            disabled={tagOptions.length === 0}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Etiquetas" />
            </SelectTrigger>
            <SelectContent>
              {tagOptions.length > CACHE_THRESHOLD_FOR_FILTER && (
                <div className="p-2 border-b border-border">
                  <Input
                    placeholder="Buscar etiqueta..."
                    value={tagFilterInput}
                    onChange={(e) => setTagFilterInput(e.target.value)}
                    className="h-8 text-sm bg-background text-foreground"
                    onPointerDown={(e) => e.stopPropagation()}
                  />
                </div>
              )}
              <SelectItem value="all">Todas las etiquetas</SelectItem>
              {filteredTagOptions.length === 0 ? (
                <div className="py-2 px-2 text-sm text-muted-foreground">Ninguna coincidencia</div>
              ) : (
                filteredTagOptions.map((t) => (
                  <SelectItem key={t.tag_id} value={t.tag_id}>
                    {t.name || t.tag_id}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
          <Select
            value={enabledFilter === '' ? 'all' : enabledFilter ? 'enabled' : 'disabled'}
            onValueChange={(v) => {
              setEnabledFilter(v === 'all' ? '' : v === 'enabled');
              setOffset(0);
            }}
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Enabled" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="enabled">Tradable</SelectItem>
              <SelectItem value="disabled">Disabled</SelectItem>
            </SelectContent>
          </Select>
          {!isDemo && (
            <Select
              value={selectedStrategyId || '_none'}
              onValueChange={(v) => {
                const sid = v === '_none' ? '' : v;
                setSelectedStrategyId(sid);
                try {
                  if (sid) localStorage.setItem('markets_selected_strategy_id', sid);
                  else localStorage.removeItem('markets_selected_strategy_id');
                } catch {}
              }}
            >
              <SelectTrigger ref={strategySelectRef} className="w-[200px]" aria-label="Estrategia (Add to Universe)">
                <SelectValue placeholder="Estrategia (Add to Universe)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_none">— Ninguna —</SelectItem>
                {strategies.map((s) => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          {!isDemo && (
            <>
              <Button
                variant="outline"
                size="sm"
                disabled={isRefreshing || (refreshCooldownUntil > Date.now())}
                onClick={handleRefresh}
                aria-label="Actualizar"
                className="shrink-0"
              >
                <RefreshCw className={`h-4 w-4 mr-1 ${isRefreshing ? 'animate-spin' : ''}`} />
                Actualizar
              </Button>
              {lastFetchedAt != null && data && (
                <span className="text-xs text-muted-foreground self-center">
                  Actualizado hace {Math.max(0, Math.floor((tick - lastFetchedAt) / 1000))} s
                </span>
              )}
            </>
          )}
        </div>

        {showInitialPrompt && (
          <Alert className="border-primary/30 bg-primary/5">
            <AlertTitle>Ver mercados</AlertTitle>
            <AlertDescription>
              Elige una <strong>serie</strong> (colección/tema), una <strong>etiqueta</strong> (tags) o escribe una búsqueda para cargar los mercados.
            </AlertDescription>
          </Alert>
        )}

        {showHardError && !isDemo && (
          <Alert variant="destructive">
            <AlertTitle>Error al cargar markets</AlertTitle>
            <AlertDescription>{error?.message}</AlertDescription>
          </Alert>
        )}

        {showUnavailableBanner && !isDemo && (
          <Alert variant="default" className="border-amber-500/50 bg-amber-50/50 dark:bg-amber-950/20 dark:border-amber-700/50">
            <AlertTitle>Datos en vivo temporalmente no disponibles</AlertTitle>
            <AlertDescription className="flex flex-wrap items-center gap-2">
              <span>Se muestran los últimos resultados cargados.</span>
              <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isRefreshing}>
                {isRefreshing ? 'Reintentando…' : 'Reintentar'}
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {showPartialMessage && (
          <Alert>
            <AlertTitle>Resultados truncados</AlertTitle>
            <AlertDescription>
              {pagination?.partialReason ?? 'Refina serie, etiqueta o búsqueda para ver más.'}
            </AlertDescription>
          </Alert>
        )}

        {showStaleBadge && (
          <Badge variant="secondary" className="text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-600">
            Cached / stale
          </Badge>
        )}

        {renderSkeleton}
        {data && !renderSkeleton && (
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Market</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>YES Token</TableHead>
                  <TableHead>NO Token</TableHead>
                  <TableHead>Spread</TableHead>
                  <TableHead>Liquidity</TableHead>
                  <TableHead>Impact</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredMarkets.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                      Aún no hay datos con estos filtros. Prueba otra serie, etiqueta o búsqueda.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredMarkets.map((market) => {
                    const policy = getTokenSelectionPolicy(market);
                    const tokenIds = getClobTokenIds(market);
                    const tokenForMetrics = policy.tokenForMetrics;
                    const orderbookData = tokenForMetrics ? data?.orderbookMetrics?.[tokenForMetrics] as Record<string, unknown> : null;
                    const spreadInfo = getSpreadDisplay(market, orderbookData);
                    const depthUsdc = (orderbookData?.depth_usdc_at_50bps as number) ?? 0;
                    const depthDisplay = depthUsdc > 0 ? `$${(depthUsdc / 1000).toFixed(1)}k` : '—';
                    const impactBps = (orderbookData?.impact_bps_for_usdc_1000 as number) ?? 0;
                    const impactDisplay = impactBps > 0 ? `${Math.round(impactBps)} bps` : '—';
                    const metricsUnavailable = policy.selectionHint === 'none';
                    const spreadLabel = metricsUnavailable ? 'Token IDs unavailable' : spreadInfo.value;
                    const depthLabel = metricsUnavailable ? 'Token IDs unavailable' : depthDisplay;
                    const impactLabel = metricsUnavailable ? 'Token IDs unavailable' : impactDisplay;

                    return (
                      <TableRow
                        key={market.market_id}
                        className="cursor-pointer"
                        onClick={() => setSelectedMarket(market)}
                      >
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            <span className="font-medium text-[13px]">{market.name}</span>
                            {market.tags && market.tags.length > 0 && (
                              <div className="flex gap-1 flex-wrap">
                                {market.tags.slice(0, 2).map((tag) => (
                                  <Badge key={tag.tag_id} variant="secondary" className="text-[10px] px-1.5 py-0">
                                    {tag.name}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={market.enabled ? 'default' : 'secondary'} className="text-[11px]">
                            {market.enabled ? 'Tradable' : 'Disabled'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {policy.selectionHint === 'none' ? (
                            <span className="text-muted-foreground text-[11px]">{policy.displayLabel}</span>
                          ) : (
                            <div className="flex items-center gap-1 flex-wrap">
                              {tokenIds.YES ? (
                                <>
                                  <code className="text-[11px] font-mono bg-muted px-1.5 py-0.5 rounded truncate max-w-[120px]">
                                    {tokenIds.YES.slice(0, 8)}...
                                  </code>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-6 w-6 p-0"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleCopyTokenId(tokenIds.YES!);
                                    }}
                                  >
                                    {copiedTokenId === tokenIds.YES ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                                  </Button>
                                </>
                              ) : (
                                <span className="text-muted-foreground text-[11px]">—</span>
                              )}
                            </div>
                          )}
                        </TableCell>
                        <TableCell>
                          {policy.selectionHint === 'none' ? (
                            <span className="text-muted-foreground text-[11px]">—</span>
                          ) : tokenIds.NO ? (
                            <div className="flex items-center gap-1">
                              <code className="text-[11px] font-mono bg-muted px-1.5 py-0.5 rounded truncate max-w-[120px]">
                                {tokenIds.NO.slice(0, 8)}...
                              </code>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleCopyTokenId(tokenIds.NO!);
                                }}
                              >
                                {copiedTokenId === tokenIds.NO ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                              </Button>
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-[11px]">—</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <MetricChip label="" value={spreadLabel} color={spreadInfo.color} />
                        </TableCell>
                        <TableCell>
                          <MetricChip label="" value={depthLabel} />
                        </TableCell>
                        <TableCell>
                          <MetricChip label="" value={impactLabel} />
                        </TableCell>
                        <TableCell>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={addingToUniverse === (market.polymarket_id ?? market.market_id)}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleAddToUniverse(market);
                            }}
                          >
                            {addingToUniverse === (market.polymarket_id ?? market.market_id) ? '...' : 'Add to Universe'}
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        )}

        {data && !isDemo && (
          <div className="flex items-center justify-between gap-4 py-2 flex-wrap">
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={currentOffset === 0}
                onClick={() => setOffset(Math.max(0, currentOffset - limit))}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Anterior
              </Button>
              <span className="text-sm text-muted-foreground">
                Resultados {currentOffset + 1}–{currentOffset + (data?.markets?.length ?? 0)}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={!hasMore}
                onClick={() => setOffset(currentOffset + limit)}
              >
                Siguiente
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
            <Select
              value={String(limit)}
              onValueChange={(v) => {
                const n = parseInt(v, 10);
                if (!Number.isNaN(n)) {
                  setLimit(n);
                  setOffset(0);
                }
              }}
            >
              <SelectTrigger className="w-[120px]" aria-label="Resultados por página">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="25">25 por página</SelectItem>
                <SelectItem value="50">50 por página</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        <SidePanel open={!!selectedMarket} onClose={() => setSelectedMarket(null)} title={selectedMarket?.name}>
          {selectedMarket && (
            <div className="space-y-3">
              <Panel>
                <h4 className="text-sm font-semibold mb-2">Outcomes</h4>
                <div className="space-y-2">
                  {selectedMarket.polymarket_payload?.outcomes?.map((outcome, idx) => (
                    <div key={idx} className="flex items-center justify-between text-[13px]">
                      <span>{outcome.outcome}</span>
                      {outcome.token_id && (
                        <code className="text-[11px] font-mono bg-muted px-2 py-1 rounded">
                          {outcome.token_id.slice(0, 16)}...
                        </code>
                      )}
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel>
                <h4 className="text-sm font-semibold mb-2">Token IDs</h4>
                {getTokenSelectionPolicy(selectedMarket).displayLabel && (
                  <p className="text-[11px] text-muted-foreground mb-2">
                    {getTokenSelectionPolicy(selectedMarket).displayLabel}
                  </p>
                )}
                <div className="space-y-2">
                  {Object.entries(getClobTokenIds(selectedMarket)).length === 0 ? (
                    <p className="text-[13px] text-muted-foreground">Token IDs unavailable</p>
                  ) : (
                    Object.entries(getClobTokenIds(selectedMarket)).map(([outcome, tokenId]) => (
                      <div key={outcome} className="flex items-center justify-between gap-2">
                        <span className="text-[13px]">{outcome}:</span>
                        <div className="flex items-center gap-1 flex-1">
                          <code className="text-[11px] font-mono bg-muted px-2 py-1 rounded flex-1 truncate">
                            {tokenId}
                          </code>
                          <Button size="sm" variant="ghost" onClick={() => handleCopyTokenId(tokenId)}>
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </Panel>
              <Button
                size="sm"
                className="w-full"
                disabled={!!(selectedMarket && addingToUniverse === (selectedMarket.polymarket_id ?? selectedMarket.market_id))}
                onClick={() => handleAddToUniverse(selectedMarket)}
              >
                {selectedMarket && addingToUniverse === (selectedMarket.polymarket_id ?? selectedMarket.market_id)
                  ? 'Añadiendo...'
                  : 'Add to Strategy Universe'}
              </Button>
            </div>
          )}
        </SidePanel>
      </div>
    </Layout>
  );
}
