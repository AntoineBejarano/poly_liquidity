'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter, ApiResponseError } from '@/lib/api';
import { toast } from 'sonner';
import type { Strategy } from '@/types/strategy';
import { useStackApp } from '@stackframe/stack';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { SidePanel } from '@/components/ui/side-panel';
import { Badge } from '@/components/ui/badge';
import { Copy, Check, ChevronLeft, ChevronRight } from 'lucide-react';
import { MetricChip } from '@/components/ui/metric-chip';
import { Panel } from '@/components/ui/panel';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

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
  /** Gamma spread (precedencia 1 si existe) */
  spread?: number | null;
  /** Gamma best bid/ask (precedencia 2 si ambos existen) */
  bestBid?: number | null;
  bestAsk?: number | null;
}

interface MarketsData {
  markets: Market[];
  orderbookMetrics?: Record<string, any>;
  pagination?: { hasMore: boolean; offset: number; limit: number; partialPage?: boolean };
}

interface TagOption {
  tag_id: string;
  name: string;
  slug?: string;
}

/** Fase 7: opción de serie desde GET /series (proxy Gamma). */
interface SeriesOption {
  series_id: string;
  name: string;
  slug?: string | null;
  markets_count?: number;
}

const DEFAULT_LIMIT = 50;
const DEFAULT_ORDER = 'createdAt';

/** Fase 7.4: Cache L1 en frontend para /directory/tags y /series. TTL 10 min. */
const CACHE_TTL_MS = 10 * 60 * 1000;
const marketsPageCache: {
  tags: { data: TagOption[] | null; expiresAt: number };
  series: { data: SeriesOption[] | null; expiresAt: number };
} = {
  tags: { data: null, expiresAt: 0 },
  series: { data: null, expiresAt: 0 },
};
const CACHE_THRESHOLD_FOR_FILTER = 15; // Fase 7.5: mostrar filtro en dropdown si hay más de N opciones
const SEARCH_DEBOUNCE_MS = 500; // Fase 5: debounce búsqueda server-side 400–600ms
const MARKETS_DEFAULT_TAG_KEY = 'markets_selected_tag_id';

export default function MarketsPage() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const { isDemo } = useDataMode();
  const searchParams = useSearchParams();
  const [searchTerm, setSearchTerm] = useState('');
  const [searchDebounced, setSearchDebounced] = useState('');
  const [limit] = useState(DEFAULT_LIMIT);
  const [offset, setOffset] = useState(0);
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

  const { data, error, renderSkeleton } = useComponentDataLoader<MarketsData>({
    fetchFn: async () => {
      if (!user || !stackApp) {
        throw new Error('User not authenticated');
      }
      if (isDemo) {
        return { markets: [], orderbookMetrics: {}, pagination: { hasMore: false, offset: 0, limit, partialPage: false } };
      }
      const api = initApiClient(createTokenGetter(user, stackApp));
      const { data: marketList, headers } = await api.getWithHeaders<Market[]>('/markets', {
        params: marketsParams(),
      });
      const list = marketList ?? [];
      const hasMore = (headers.get('X-Has-More') ?? '').toLowerCase() === 'true';
      const respOffset = parseInt(headers.get('X-Offset') ?? String(offset), 10);
      const respLimit = parseInt(headers.get('X-Limit') ?? String(limit), 10);
      const partialPage = (headers.get('X-Partial-Page') ?? '').toLowerCase() === 'true';
      const tokenIds = list
        .map((m) => m.clob_token_ids?.primary ?? m.clob_token_ids?.primary_yes)
        .filter((id): id is string => !!id)
        .slice(0, 100);
      const tokenIdsParam = tokenIds.length > 0 ? tokenIds.join(',') : undefined;
      const obResponse = await api.get<{
        metrics?: Record<string, any>;
        found_token_ids_count?: number;
        partial?: boolean;
      }>(tokenIdsParam
        ? `/markets/orderbook-metrics?token_ids=${encodeURIComponent(tokenIdsParam)}`
        : '/markets/orderbook-metrics');
      const orderbookMetrics = obResponse?.metrics ?? {};
      return {
        markets: list,
        orderbookMetrics,
        pagination: { hasMore, offset: respOffset, limit: respLimit, partialPage },
      };
    },
    dependencies: [user, stackApp, isDemo, limit, offset, order, ascending, tagId, seriesId, enabledFilter, searchDebounced],
    refreshInterval: isDemo ? 0 : 30000,
    enabled: !!user && !!stackApp,
    showSkeleton: true,
    skeletonComponent: () => (
      <div className="space-y-2">
        {[...Array(10)].map((_, i) => (
          <div key={i} className="h-9 bg-muted animate-pulse rounded" />
        ))}
      </div>
    ),
  });

  // Fase 5: debounce búsqueda server-side 400–600ms; al cambiar searchDebounced, reset offset
  useEffect(() => {
    const t = setTimeout(() => {
      setSearchDebounced(searchTerm);
      setOffset(0);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [searchTerm]);

  // Inicializar tag_id desde localStorage o NEXT_PUBLIC_MARKETS_DEFAULT_TAG_ID (solo cliente)
  useEffect(() => {
    const fromUrl = searchParams?.get('tag_id');
    if (fromUrl) return;
    try {
      const stored = localStorage.getItem(MARKETS_DEFAULT_TAG_KEY);
      const envDefault = (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_MARKETS_DEFAULT_TAG_ID)?.trim() ?? '';
      const initial = stored || envDefault || '';
      if (initial) setTagId(initial);
    } catch {}
  }, []);

  // Persistir tag_id en localStorage (Fase 5.5)
  useEffect(() => {
    if (!tagId) return;
    try {
      localStorage.setItem(MARKETS_DEFAULT_TAG_KEY, tagId);
    } catch {}
  }, [tagId]);

  // Sincronizar strategy_id desde URL o localStorage
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

  // Sincronizar tag_id desde URL si viene (opcional)
  useEffect(() => {
    const fromUrl = searchParams?.get('tag_id');
    if (fromUrl) {
      setTagId(fromUrl);
      setOffset(0);
      try {
        localStorage.setItem(MARKETS_DEFAULT_TAG_KEY, fromUrl);
      } catch {}
    }
  }, [searchParams]);

  // Cargar tags (Fase 5.5 / 7.1). Fase 7.4: cache L1 10 min. Backend usa Gamma si DB vacía.
  useEffect(() => {
    if (!user || !stackApp || isDemo) return;
    const now = Date.now();
    if (marketsPageCache.tags.data && marketsPageCache.tags.expiresAt > now) {
      setTagOptions(marketsPageCache.tags.data);
      return;
    }
    const api = initApiClient(createTokenGetter(user, stackApp));
    api.get<{ items?: TagOption[] }>('/directory/tags?limit=200&offset=0', true).then((res) => {
      const items = res?.items ?? [];
      const list = Array.isArray(items) ? items : [];
      marketsPageCache.tags = { data: list, expiresAt: now + CACHE_TTL_MS };
      if (list.length > 0) setTagOptions(list);
    }).catch(() => setTagOptions([]));
  }, [user, stackApp, isDemo]);

  // Fallback: si /directory/tags viene vacío (DB sin tags hasta que corra el Scanner), derivar categorías
  // desde los tags que ya traen los markets de GET /markets — misma fuente que la lista, sin datos desactualizados.
  useEffect(() => {
    const markets = data?.markets;
    if (!markets?.length || tagOptions.length > 0) return;
    const seen = new Set<string>();
    const derived: TagOption[] = [];
    for (const m of markets) {
      for (const t of m.tags ?? []) {
        const id = (t as { tag_id?: string; name?: string }).tag_id || (t as { tag_id?: string; name?: string }).name;
        if (id && !seen.has(id)) {
          seen.add(id);
          const name = (t as { tag_id?: string; name?: string }).name ?? id;
          derived.push({ tag_id: id, name });
        }
      }
    }
    if (derived.length > 0) setTagOptions(derived);
  }, [data?.markets, tagOptions.length]);

  // Fase 7.2: Series desde GET /series. 7.3: si falla, dropdown deshabilitado. 7.4: cache L1 10 min.
  useEffect(() => {
    if (!user || !stackApp || isDemo) return;
    setSeriesLoadFailed(false);
    const now = Date.now();
    if (marketsPageCache.series.data && marketsPageCache.series.expiresAt > now) {
      setSeriesOptions(marketsPageCache.series.data);
      return;
    }
    const api = initApiClient(createTokenGetter(user, stackApp));
    api.get<SeriesOption[] | { series_id: string; name: string; slug?: string }[]>('/series', true)
      .then((raw) => {
        const list = Array.isArray(raw) ? raw : [];
        const options: SeriesOption[] = list.map((s: any) => ({
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
  }, [user, stackApp, isDemo]);

  // Fase 8.1: Cargar estrategias para selector Add to Universe (GET /api/strategies)
  useEffect(() => {
    if (!user || !stackApp || isDemo) return;
    const api = initApiClient(createTokenGetter(user, stackApp));
    api.get<Strategy[]>('/api/strategies', true).then((list) => {
      setStrategies(Array.isArray(list) ? list : []);
    }).catch(() => setStrategies([]));
  }, [user, stackApp, isDemo]);

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

  /** Fase 6: Token Selection Policy — usar solo selection_hint y primary del backend. */
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

  /** Fase 6: Precedencia spread — 1) Gamma spread 2) Gamma bestBid/bestAsk 3) orderbookMetrics 4) mensaje. */
  function getSpreadDisplay(
    market: Market,
    orderbookData: Record<string, any> | null | undefined
  ): { value: string; color: string; source: 'gamma_spread' | 'gamma_bid_ask' | 'orderbook' | 'fallback' } {
    const spread = market.spread;
    if (spread != null && typeof spread === 'number') {
      const bps = Math.round(spread);
      return {
        value: `${bps} bps`,
        color: bps < 50 ? 'green' : bps < 150 ? 'yellow' : 'red',
        source: 'gamma_spread',
      };
    }
    const bid = market.bestBid;
    const ask = market.bestAsk;
    if (bid != null && ask != null && typeof bid === 'number' && typeof ask === 'number') {
      const bps = Math.round((ask - bid) * 10000);
      return {
        value: `${bps} bps`,
        color: bps < 50 ? 'green' : bps < 150 ? 'yellow' : 'red',
        source: 'gamma_bid_ask',
      };
    }
    const obBps = orderbookData?.spread_bps;
    if (obBps != null) {
      return {
        value: `${Math.round(obBps)} bps`,
        color: obBps < 50 ? 'green' : obBps < 150 ? 'yellow' : 'red',
        source: 'orderbook',
      };
    }
    return { value: '—', color: 'neutral', source: 'fallback' };
  }

  /** YES/NO para mostrar/copiar; usa primary_yes/primary_no del backend cuando existen. */
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

  // Búsqueda vía param search en GET /markets (debounced); no filtro client-side adicional
  const filteredMarkets = data?.markets ?? [];

  const pagination = data?.pagination;
  const hasMore = pagination?.hasMore ?? false;
  const currentOffset = pagination?.offset ?? offset;
  const showPartialMessage = pagination?.partialPage === true;

  // Fase 7.5: filtrar listas grandes en dropdown (typeahead client-side)
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
        {/* Topbar compacto con filtros — Fase 5/5.5: query params, tag_id, reset offset */}
        <div className="flex items-center gap-2 flex-wrap">
          <Input
            placeholder="Buscar (por nombre, ~500ms)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 min-w-[200px]"
          />
          <Select
            value={tagId || 'all'}
            onValueChange={(v) => {
              const next = v === 'all' ? '' : v;
              setTagId(next);
              setOffset(0);
            }}
            onOpenChange={(open) => {
              if (!open) setTagFilterInput('');
            }}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Categoría" />
            </SelectTrigger>
            <SelectContent>
              {tagOptions.length > CACHE_THRESHOLD_FOR_FILTER && (
                <div className="p-2 border-b">
                  <Input
                    placeholder="Filtrar categorías..."
                    value={tagFilterInput}
                    onChange={(e) => setTagFilterInput(e.target.value)}
                    className="h-8 text-sm"
                    onPointerDown={(e) => e.stopPropagation()}
                  />
                </div>
              )}
              <SelectItem value="all">Todas las categorías</SelectItem>
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
          {/* Fase 7.2: Series desde GET /series. 7.3: deshabilitado si endpoint falla. */}
          <Select
            value={seriesId || 'all'}
            onValueChange={(v) => {
              const next = v === 'all' ? '' : v;
              setSeriesId(next);
              setOffset(0);
            }}
            onOpenChange={(open) => {
              if (!open) setSeriesFilterInput('');
            }}
            disabled={seriesLoadFailed}
          >
            <SelectTrigger className="w-[180px]" title={seriesLoadFailed ? 'Series no disponible' : undefined}>
              <SelectValue placeholder={seriesLoadFailed ? 'Series (no disponible)' : 'Series'} />
            </SelectTrigger>
            <SelectContent>
              {seriesOptions.length > CACHE_THRESHOLD_FOR_FILTER && (
                <div className="p-2 border-b">
                  <Input
                    placeholder="Filtrar series..."
                    value={seriesFilterInput}
                    onChange={(e) => setSeriesFilterInput(e.target.value)}
                    className="h-8 text-sm"
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
          {isDemo && (
            <Badge variant="outline" className="text-[11px] bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200 border-amber-200 dark:border-amber-800">
              Modo Demo
            </Badge>
          )}
        </div>

        {/* Error de API en modo Real */}
        {error && !isDemo && (
          <Alert variant="destructive">
            <AlertTitle>Error al cargar markets</AlertTitle>
            <AlertDescription>{error.message}</AlertDescription>
          </Alert>
        )}
        {showPartialMessage && (
          <Alert>
            <AlertTitle>Resultados truncados</AlertTitle>
            <AlertDescription>
              Se alcanzó el límite de búsqueda. Refina filtros o categoría para ver más.
            </AlertDescription>
          </Alert>
        )}
        {/* Tabla densa */}
        {renderSkeleton}
        {data && (
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
                      No se encontraron markets
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredMarkets.map((market) => {
                    const policy = getTokenSelectionPolicy(market);
                    const tokenIds = getClobTokenIds(market);
                    // Fase 6.3: métricas solo con token primary (página actual)
                    const tokenForMetrics = policy.tokenForMetrics;
                    const orderbookData = tokenForMetrics ? data?.orderbookMetrics?.[tokenForMetrics] : null;
                    const spreadInfo = getSpreadDisplay(market, orderbookData);

                    const depthUsdc = orderbookData?.depth_usdc_at_50bps ?? 0;
                    const depthDisplay = depthUsdc > 0 ? `$${(depthUsdc / 1000).toFixed(1)}k` : '—';
                    const impactBps = orderbookData?.impact_bps_for_usdc_1000 ?? 0;
                    const impactDisplay = impactBps > 0 ? `${Math.round(impactBps)} bps` : '—';

                    const metricsUnavailable = policy.selectionHint === 'none';
                    const spreadLabel = metricsUnavailable
                      ? 'Token IDs unavailable'
                      : spreadInfo.source === 'fallback'
                        ? 'Not subscribed'
                        : spreadInfo.value;
                    const depthLabel = metricsUnavailable ? 'Token IDs unavailable' : (depthDisplay === '—' ? 'Not subscribed' : depthDisplay);
                    const impactLabel = metricsUnavailable ? 'Token IDs unavailable' : (impactDisplay === '—' ? 'Not subscribed' : impactDisplay);

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
                              {policy.selectionHint === 'multi' && (
                                <Badge variant="secondary" className="text-[10px]">Multi (sampled)</Badge>
                              )}
                              {tokenIds.YES ? (
                                <>
                                  <code className="text-[11px] font-mono bg-muted px-1.5 py-0.5 rounded truncate max-w-[120px]">
                                    {tokenIds.YES.slice(0, 8)}...
                                  </code>
                                  <Button
                                    variant="ghost"
                                    size="compact-sm"
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
                            <span className="text-muted-foreground text-[11px]">{policy.displayLabel}</span>
                          ) : tokenIds.NO ? (
                            <div className="flex items-center gap-1">
                              <code className="text-[11px] font-mono bg-muted px-1.5 py-0.5 rounded truncate max-w-[120px]">
                                {tokenIds.NO.slice(0, 8)}...
                              </code>
                              <Button
                                variant="ghost"
                                size="compact-sm"
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
                          <MetricChip
                            label=""
                            value={spreadLabel}
                            color={spreadInfo.color}
                            tooltip={
                              metricsUnavailable
                                ? 'Sin token IDs para este market.'
                                : spreadInfo.source === 'fallback'
                                  ? 'Sin datos de orderbook para este token.'
                                  : 'Diferencia entre mejor bid y ask. Spread bajo = más liquidez.'
                            }
                          />
                        </TableCell>
                        <TableCell>
                          <MetricChip
                            label=""
                            value={depthLabel}
                            tooltip="Liquidez disponible a 50bps del mejor precio"
                          />
                        </TableCell>
                        <TableCell>
                          <MetricChip
                            label=""
                            value={impactLabel}
                            tooltip="Impacto en precio al ejecutar $1000"
                          />
                        </TableCell>
                        <TableCell>
                          <Button
                            size="compact-sm"
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

        {/* Paginación Prev/Next — Fase 5 */}
        {data && !isDemo && (
          <div className="flex items-center justify-between gap-2 py-2">
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
              {currentOffset + 1}–{currentOffset + (data?.markets?.length ?? 0)} (límite {limit})
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
        )}

        {/* Side Panel con detalles */}
        <SidePanel
          open={!!selectedMarket}
          onClose={() => setSelectedMarket(null)}
          title={selectedMarket?.name}
        >
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
                {selectedMarket && getTokenSelectionPolicy(selectedMarket).displayLabel && (
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
                          <Button
                            size="compact-sm"
                            variant="ghost"
                            onClick={() => handleCopyTokenId(tokenId)}
                          >
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </Panel>
              <Button
                size="compact"
                className="w-full"
                disabled={!!(selectedMarket && addingToUniverse === (selectedMarket.polymarket_id ?? selectedMarket.market_id))}
                onClick={() => {
                  if (selectedMarket) {
                    handleAddToUniverse(selectedMarket);
                  }
                }}
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
