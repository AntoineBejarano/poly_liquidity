'use client';

import { useParams } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { Layout } from '@/components/Layout';
import { useDataMode } from '@/hooks/useDataMode';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { DiscoveryClient, getDomainBySlug, isValidDomainSlug } from '@/lib/discovery';
import { getTimeBucketMinutes, getEndDateMaxIso, isValidTimeBucket } from '@/lib/discovery/time-bucket';
import type { DiscoveryScreenerEvent, DiscoveryScreenerMarket, DiscoveryTradeableMarket } from '@/lib/discovery/types';
import type { Strategy } from '@/types/strategy';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import Link from 'next/link';
import { RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { AddToUniverseConfirmDialog } from '@/components/markets/AddToUniverseConfirmDialog';
import { MarketOutcomesWithProbability } from '@/components/markets/MarketOutcomesWithProbability';
import { MarketDiscoveryMetrics } from '@/components/markets/MarketDiscoveryMetrics';
import { DiscoveryEventCard } from '@/components/markets/DiscoveryEventCard';
import { TooltipProvider } from '@/components/ui/tooltip';

const OVERFETCH_LIMIT = 100;

function formatEventTime(iso: string | null | undefined): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function formatUsdShort(value: number | string | null | undefined): string {
  const n = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(n) || n <= 0) return '—';
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function formatEndDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { month: 'numeric', day: 'numeric', year: 'numeric' });
  } catch {
    return '—';
  }
}

function searchEvents(events: DiscoveryScreenerEvent[], query: string): DiscoveryScreenerEvent[] {
  const q = query.trim().toLowerCase();
  if (!q) return events;
  return events.filter(
    (ev) =>
      (ev.title ?? '').toLowerCase().includes(q) ||
      (ev.subtitle ?? '').toLowerCase().includes(q) ||
      ev.event_id.toLowerCase().includes(q)
  );
}

const EVENT_SORT_OPTIONS = ['liquidity', 'volume24', 'volumeTotal', 'ends'] as const;
type EventSortKey = (typeof EVENT_SORT_OPTIONS)[number];

function sortEvents(events: DiscoveryScreenerEvent[], sortBy: EventSortKey): DiscoveryScreenerEvent[] {
  const getLiq = (ev: DiscoveryScreenerEvent) => ev.markets.reduce((s, m) => s + (Number(m.liquidity) || Number((m as DiscoveryScreenerMarket).liquidity_usd) || 0), 0);
  const getVol24 = (ev: DiscoveryScreenerEvent) => ev.markets.reduce((s, m) => s + (m.volume24hr ?? 0), 0);
  const getVolTotal = (ev: DiscoveryScreenerEvent) => ev.markets.reduce((s, m) => s + (m.volume ?? 0), 0);
  const getEndTime = (ev: DiscoveryScreenerEvent) => (ev.end_date ? new Date(ev.end_date).getTime() : 0);
  return [...events].sort((a, b) => {
    if (sortBy === 'liquidity') return getLiq(b) - getLiq(a);
    if (sortBy === 'volume24') return getVol24(b) - getVol24(a);
    if (sortBy === 'volumeTotal') return getVolTotal(b) - getVolTotal(a);
    return getEndTime(a) - getEndTime(b);
  });
}

/** Filtra eventos: solo mercados con TTR <= ttrMinutes (resolución en ese intervalo, ej. apuesta cada 5 min). */
function filterEventsByTtr(events: DiscoveryScreenerEvent[], ttrMinutes: number): DiscoveryScreenerEvent[] {
  return events
    .map((ev) => ({
      ...ev,
      markets: ev.markets.filter(
        (m) => m.time_to_resolution_minutes != null && m.time_to_resolution_minutes >= 0 && m.time_to_resolution_minutes <= ttrMinutes
      ),
    }))
    .filter((ev) => ev.markets.length > 0)
    .map((ev) => ({ ...ev, markets_count: ev.markets.length }));
}

export default function DomainTimeBucketPage() {
  const params = useParams();
  const domainSlug = (params?.domain as string) ?? '';
  const timeBucketSlug = (params?.timeBucket as string) ?? '15M';
  const user = useUser();
  const stackApp = useStackApp();
  const { isDemo } = useDataMode();

  const [events, setEvents] = useState<DiscoveryScreenerEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>('');
  const [addingToUniverse, setAddingToUniverse] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [marketToAdd, setMarketToAdd] = useState<DiscoveryTradeableMarket | null>(null);
  const [sortBy, setSortBy] = useState<EventSortKey>('liquidity');
  const [tradeableFilter, setTradeableFilter] = useState<'yes' | 'all'>('yes');

  const domain = getDomainBySlug(domainSlug);
  const ttrMinutes = getTimeBucketMinutes(timeBucketSlug);
  const isValid = isValidDomainSlug(domainSlug) && domain?.supportsTimeBucket && isValidTimeBucket(timeBucketSlug) && ttrMinutes != null;

  const endDateMax = useMemo(() => (ttrMinutes != null ? getEndDateMaxIso(ttrMinutes) : undefined), [ttrMinutes]);

  const eventsInTtr = useMemo(() => {
    if (ttrMinutes == null) return events;
    return filterEventsByTtr(events, ttrMinutes);
  }, [events, ttrMinutes]);

  const searched = useMemo(() => searchEvents(eventsInTtr, searchQuery), [eventsInTtr, searchQuery]);
  const filteredByTradeable = useMemo(() => {
    if (tradeableFilter === 'all') return searched;
    return searched
      .filter((ev) => ev.markets.some((m) => m.tradeable !== false))
      .map((ev) => ({
        ...ev,
        markets: ev.markets.filter((m) => m.tradeable !== false),
        markets_count: ev.markets.filter((m) => m.tradeable !== false).length,
      }));
  }, [searched, tradeableFilter]);
  const sorted = useMemo(() => sortEvents(filteredByTradeable, sortBy), [filteredByTradeable, sortBy]);
  const noTradeableButHasEvents = tradeableFilter === 'yes' && filteredByTradeable.length === 0 && searched.length > 0;
  const displayList = useMemo(
    () => (noTradeableButHasEvents ? sortEvents(searched, sortBy) : sorted),
    [noTradeableButHasEvents, searched, sortBy, sorted]
  );

  const fetchEvents = useCallback(
    async (off: number, append: boolean) => {
      if (!domain?.gammaTagSlug || isDemo) return;
      setLoading(true);
      setError(null);
      try {
        const client = new DiscoveryClient(createTokenGetter(user ?? undefined, stackApp ?? undefined));
        const result = await client.fetchDiscoveryScreener({
          tag_slug: domain.gammaTagSlug,
          closed: false,
          limit: OVERFETCH_LIMIT,
          offset: off,
          end_date_max: endDateMax ?? undefined,
        });
        setEvents((prev) => (append ? [...prev, ...result.events] : result.events));
        setHasMore(result.events.length >= OVERFETCH_LIMIT);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Error al cargar');
        setEvents([]);
      } finally {
        setLoading(false);
      }
    },
    [domain?.gammaTagSlug, isDemo, user, stackApp, endDateMax]
  );

  useEffect(() => {
    if (isValid && domain?.gammaTagSlug && !isDemo) {
      setOffset(0);
      fetchEvents(0, false);
    } else {
      setLoading(false);
      setEvents([]);
    }
  }, [isValid, domain?.gammaTagSlug, isDemo, fetchEvents, timeBucketSlug]);

  useEffect(() => {
    if (!user || !stackApp || isDemo) return;
    const api = initApiClient(createTokenGetter(user, stackApp));
    api.get<Strategy[]>('/api/strategies', true).then((list) => setStrategies(Array.isArray(list) ? list : [])).catch(() => setStrategies([]));
  }, [user, stackApp, isDemo]);

  const handleAddToUniverse = async (market: DiscoveryTradeableMarket) => {
    if (!user || !stackApp || isDemo) return;
    if (!selectedStrategyId) {
      toast.error('Selecciona una estrategia');
      return;
    }
    setAddingToUniverse(market.polymarket_id);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.post(`/api/strategies/${selectedStrategyId}/universe/markets`, { market_id: market.polymarket_id });
      toast.success('Añadido al universo');
      setMarketToAdd(null);
      setConfirmOpen(false);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Error al añadir');
    } finally {
      setAddingToUniverse(null);
    }
  };

  const handleAddEventToUniverse = async (ev: DiscoveryScreenerEvent) => {
    if (!user || !stackApp || isDemo) return;
    if (!selectedStrategyId) {
      toast.error('Selecciona una estrategia');
      return;
    }
    setAddingToUniverse(`event:${ev.event_id}`);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.post(`/api/strategies/${selectedStrategyId}/universe/items`, {
        type: 'event',
        ref_id: ev.event_id,
        include_future: false,
      });
      toast.success('Evento añadido al universo');
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Error al añadir evento');
    } finally {
      setAddingToUniverse(null);
    }
  };

  const handleRequestAddToUniverse = (market: DiscoveryTradeableMarket) => {
    if (!selectedStrategyId) {
      toast.error('Selecciona una estrategia');
      return;
    }
    setMarketToAdd(market);
    setConfirmOpen(true);
  };

  const loadMore = () => {
    const nextOffset = offset + OVERFETCH_LIMIT;
    setOffset(nextOffset);
    fetchEvents(nextOffset, true);
  };

  if (!isValid) {
    return (
      <Layout>
        <Alert variant="destructive">
          <AlertTitle>Ruta inválida</AlertTitle>
          <AlertDescription>
            Dominio o time bucket no válido. Usa /markets/crypto/5M, /markets/crypto/15M, /markets/politics/1D, etc.
          </AlertDescription>
        </Alert>
      </Layout>
    );
  }

  const domainLabel = domainSlug.charAt(0).toUpperCase() + domainSlug.slice(1);

  return (
    <Layout>
      <TooltipProvider>
      <div className="space-y-4 p-4">
        <Link href="/markets" className="text-sm text-muted-foreground hover:text-foreground">
          ← Discovery
        </Link>
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <h1 className="text-xl font-semibold">
              {domainLabel} / {timeBucketSlug}
            </h1>
            <p className="text-sm text-muted-foreground w-full md:w-auto">
              Eventos con mercados que resuelven en &le; {ttrMinutes} min (apuesta cada {timeBucketSlug}).
            </p>
            <div className="flex items-center gap-2">
              <Link
                href={`/markets/${domainSlug}/events`}
                className="rounded-md border px-3 py-2 text-sm font-medium transition-colors hover:bg-muted"
              >
                Ver todos los eventos
              </Link>
              {!isDemo && (
                <Select value={selectedStrategyId || '_none'} onValueChange={(v) => setSelectedStrategyId(v === '_none' ? '' : v)}>
                  <SelectTrigger className="w-[220px]">
                    <SelectValue placeholder="Estrategia (añadir al universo)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_none">— Ninguna —</SelectItem>
                    {strategies.map((s) => (
                      <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <Button variant="outline" size="sm" onClick={() => fetchEvents(0, false)} disabled={loading}>
                <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                Actualizar
              </Button>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={`Buscar por evento en ${domainLabel}...`}
              className="flex-1 min-w-[200px] max-w-sm px-3 py-2 text-sm border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            <Select value={tradeableFilter} onValueChange={(v) => setTradeableFilter(v as 'yes' | 'all')}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Tradeable" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="yes">Solo tradeables</SelectItem>
                <SelectItem value="all">Todos</SelectItem>
              </SelectContent>
            </Select>
            <Select value={sortBy} onValueChange={(v) => setSortBy(v as EventSortKey)}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Ordenar por" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="liquidity">Liquidez</SelectItem>
                <SelectItem value="volume24">Vol 24h</SelectItem>
                <SelectItem value="volumeTotal">Vol total</SelectItem>
                <SelectItem value="ends">Ends (próximos)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {!isDemo && strategies.length > 0 && (
            <p className="text-xs text-muted-foreground">
              El universo pertenece a una estrategia. Selecciona una estrategia arriba para poder añadir <strong>todo el evento</strong> o <strong>mercados sueltos</strong> (al expandir el evento).
            </p>
          )}
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {noTradeableButHasEvents && (
          <Alert variant="destructive" className="border-red-500 bg-red-500/10">
            <AlertTitle>Ninguno tradeable</AlertTitle>
            <AlertDescription>
              Con el filtro &quot;Solo tradeables&quot; no hay mercados con precios. Los eventos siguientes no tienen mercados con precios disponibles (no se puede mostrar probabilidad ni operar).
            </AlertDescription>
          </Alert>
        )}

        {loading && events.length === 0 ? (
          <div className="space-y-2">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-20 bg-muted animate-pulse rounded-lg" />
            ))}
          </div>
        ) : (
          <div className="rounded-xl bg-[#0B0F14] min-h-[40vh] p-3 space-y-2">
            {displayList.length === 0 && !noTradeableButHasEvents ? (
              <p className="text-center text-[#9CA3AF] py-8">
                No hay eventos con mercados que resuelvan en &le; {ttrMinutes} min. Prueba otro time bucket o <Link href={`/markets/${domainSlug}/events`} className="text-[#22C55E] underline">ver todos los eventos</Link>.
              </p>
            ) : (
              displayList.map((ev) => (
                <DiscoveryEventCard
                  key={ev.event_id}
                  event={ev}
                  isExpanded={expandedEventId === ev.event_id}
                  onToggle={() => setExpandedEventId(expandedEventId === ev.event_id ? null : ev.event_id)}
                  noTradeableState={noTradeableButHasEvents}
                  isDemo={isDemo}
                  selectedStrategyId={selectedStrategyId}
                  addingToUniverse={addingToUniverse}
                  onAddEvent={() => handleAddEventToUniverse(ev)}
                  onAddMarket={handleRequestAddToUniverse}
                  renderExpanded={(event) => (
                    <>
                      {event.markets.map((m) => (
                        <div
                          key={m.market_id}
                          className="px-4 py-4 pl-10 border-b border-[#1F2937] last:border-b-0"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0 flex-1 space-y-3">
                              <p className="text-sm font-medium text-[#E5E7EB]">{m.question}</p>
                              <MarketDiscoveryMetrics market={m as DiscoveryScreenerMarket} variant="terminal" />
                              <MarketOutcomesWithProbability market={m} variant="context" />
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              {!isDemo && selectedStrategyId && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="border-[#374151] text-[#9CA3AF] hover:bg-[#1F2937]"
                                  disabled={!!addingToUniverse}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleRequestAddToUniverse(m as DiscoveryTradeableMarket);
                                  }}
                                >
                                  Añadir mercado
                                </Button>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </>
                  )}
                />
              ))
            )}
          </div>
        )}

        {hasMore && (
          <Button variant="outline" onClick={loadMore} disabled={loading}>
            Cargar más eventos
          </Button>
        )}

        <AddToUniverseConfirmDialog
          open={confirmOpen}
          onOpenChange={setConfirmOpen}
          market={marketToAdd}
          strategyName={strategies.find((s) => s.id === selectedStrategyId)?.name ?? ''}
          onConfirm={() => { if (marketToAdd) void handleAddToUniverse(marketToAdd); }}
          loading={!!addingToUniverse}
        />
      </div>
      </TooltipProvider>
    </Layout>
  );
}
