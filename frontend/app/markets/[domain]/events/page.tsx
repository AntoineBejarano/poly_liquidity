'use client';

import { useParams } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { Layout } from '@/components/Layout';
import { useDataMode } from '@/hooks/useDataMode';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { DiscoveryClient, getDomainBySlug, isValidDomainSlug } from '@/lib/discovery';
import { getTimeBucketMinutes, getEndDateMaxIso } from '@/lib/discovery/time-bucket';
import type { DiscoveryEventWithMarkets, DiscoveryTradeableMarket } from '@/lib/discovery/types';
import type { Strategy } from '@/types/strategy';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import Link from 'next/link';
import { RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import { AddToUniverseConfirmDialog } from '@/components/markets/AddToUniverseConfirmDialog';
import { MarketOutcomesWithProbability } from '@/components/markets/MarketOutcomesWithProbability';

const OVERFETCH_LIMIT = 100;
const TTR_OPTIONS = [null, '15M', '1H', '1D'] as const;

function formatEventTime(iso: string | null | undefined): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function formatUsdShort(value: number | null | undefined): string {
  if (value == null || value <= 0) return '—';
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
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

function searchEvents(events: DiscoveryEventWithMarkets[], query: string): DiscoveryEventWithMarkets[] {
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

function sortEvents(events: DiscoveryEventWithMarkets[], sortBy: EventSortKey): DiscoveryEventWithMarkets[] {
  const getLiq = (ev: DiscoveryEventWithMarkets) => ev.markets.reduce((s, m) => s + (m.liquidity ?? 0), 0);
  const getVol24 = (ev: DiscoveryEventWithMarkets) => ev.markets.reduce((s, m) => s + (m.volume24hr ?? 0), 0);
  const getVolTotal = (ev: DiscoveryEventWithMarkets) => ev.markets.reduce((s, m) => s + (m.volume ?? 0), 0);
  const getEndTime = (ev: DiscoveryEventWithMarkets) => (ev.end_date ? new Date(ev.end_date).getTime() : 0);
  return [...events].sort((a, b) => {
    if (sortBy === 'liquidity') return getLiq(b) - getLiq(a);
    if (sortBy === 'volume24') return getVol24(b) - getVol24(a);
    if (sortBy === 'volumeTotal') return getVolTotal(b) - getVolTotal(a);
    return getEndTime(a) - getEndTime(b); // ends: próximos primero
  });
}

export default function DomainEventsPage() {
  const params = useParams();
  const domainSlug = (params?.domain as string) ?? '';
  const user = useUser();
  const stackApp = useStackApp();
  const { isDemo } = useDataMode();

  const [events, setEvents] = useState<DiscoveryEventWithMarkets[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [ttrBucket, setTtrBucket] = useState<typeof TTR_OPTIONS[number]>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>('');
  const [addingToUniverse, setAddingToUniverse] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [marketToAdd, setMarketToAdd] = useState<DiscoveryTradeableMarket | null>(null);
  const [sortBy, setSortBy] = useState<EventSortKey>('liquidity');
  const [tradeableFilter, setTradeableFilter] = useState<'yes' | 'all'>('yes');

  const domain = getDomainBySlug(domainSlug);
  const searched = useMemo(() => searchEvents(events, searchQuery), [events, searchQuery]);
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
  const isValid = isValidDomainSlug(domainSlug) && domain?.gammaTagSlug;

  const endDateMax = useMemo(() => {
    if (ttrBucket && getTimeBucketMinutes(ttrBucket) != null) {
      return getEndDateMaxIso(getTimeBucketMinutes(ttrBucket)!);
    }
    return undefined;
  }, [ttrBucket]);

  const fetchEvents = useCallback(
    async (off: number, append: boolean) => {
      if (!domain?.gammaTagSlug || isDemo) return;
      setLoading(true);
      setError(null);
      try {
        const client = new DiscoveryClient(createTokenGetter(user ?? undefined, stackApp ?? undefined));
        const result = await client.fetchDiscoveryEvents({
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
    [domain, isDemo, user, stackApp, endDateMax]
  );

  useEffect(() => {
    if (isValid && domain?.gammaTagSlug && !isDemo) {
      setOffset(0);
      fetchEvents(0, false);
    } else {
      setLoading(false);
      setEvents([]);
    }
  }, [isValid, domain?.gammaTagSlug, isDemo, fetchEvents]);

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

  const handleAddEventToUniverse = async (ev: DiscoveryEventWithMarkets) => {
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

  if (!isValid || !domain?.gammaTagSlug) {
    return (
      <Layout>
        <Alert variant="destructive">
          <AlertTitle>Dominio no válido</AlertTitle>
          <AlertDescription>Usa /markets/crypto/events o /markets/politics/events.</AlertDescription>
        </Alert>
      </Layout>
    );
  }

  const domainLabel = domainSlug.charAt(0).toUpperCase() + domainSlug.slice(1);

  return (
    <Layout>
      <div className="space-y-4 p-4">
        <Link href="/markets" className="text-sm text-muted-foreground hover:text-foreground">
          ← Discovery
        </Link>
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <h1 className="text-xl font-semibold">{domainLabel} — Eventos</h1>
            <div className="flex items-center gap-2">
              <Select value={ttrBucket ?? 'all'} onValueChange={(v) => setTtrBucket(v === 'all' ? null : (v as typeof TTR_OPTIONS[number]))}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue placeholder="TTR" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {TTR_OPTIONS.filter(Boolean).map((b) => (
                    <SelectItem key={b!} value={b!}>{b}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
          <div className="space-y-2">
            {displayList.length === 0 && !noTradeableButHasEvents ? (
              <p className="text-center text-muted-foreground py-8">No hay eventos con estos filtros.</p>
            ) : (
              displayList.map((ev) => {
                const isExpanded = expandedEventId === ev.event_id;
                const timeStr = formatEventTime(ev.start_date || ev.end_date);
                const eventVol24 = ev.markets.reduce((s, m) => s + (m.volume24hr ?? 0), 0);
                const eventVolTotal = ev.markets.reduce((s, m) => s + (m.volume ?? 0), 0);
                const eventLiq = ev.markets.reduce((s, m) => s + (m.liquidity ?? 0), 0);
                return (
                  <div
                    key={ev.event_id}
                    className={`border rounded-lg overflow-hidden ${noTradeableButHasEvents ? 'border-red-500/60 bg-red-500/10' : 'border-border bg-card'}`}
                  >
                    {noTradeableButHasEvents && (
                      <div className="px-3 py-1.5 bg-red-500/20 border-b border-red-500/40 text-sm font-medium text-red-600 dark:text-red-400">
                        Ninguno tradeable
                      </div>
                    )}
                    <div
                      className={`flex items-center justify-between gap-4 p-3 cursor-pointer transition-colors ${noTradeableButHasEvents ? 'hover:bg-red-500/10' : 'hover:bg-muted/30'}`}
                      onClick={() => setExpandedEventId(isExpanded ? null : ev.event_id)}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-muted-foreground shrink-0">
                          {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                        </span>
                        <div className="min-w-0">
                          <p className="font-medium text-foreground truncate">{ev.title}</p>
                          {(ev.subtitle || timeStr) && (
                            <p className="text-xs text-muted-foreground truncate">
                              {[ev.subtitle, timeStr].filter(Boolean).join(' · ')}
                            </p>
                          )}
                          <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-1 text-xs text-muted-foreground">
                            <span><strong className="text-foreground/80">24h Vol:</strong> {formatUsdShort(eventVol24)}</span>
                            <span><strong className="text-foreground/80">Total Vol:</strong> {formatUsdShort(eventVolTotal)}</span>
                            <span><strong className="text-foreground/80">Liq:</strong> {formatUsdShort(eventLiq)}</span>
                            <span><strong className="text-foreground/80">Ends:</strong> {formatEndDate(ev.end_date)}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-xs text-muted-foreground">{ev.markets_count} mercados</span>
                        {!isDemo && selectedStrategyId && (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={!!addingToUniverse}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleAddEventToUniverse(ev);
                            }}
                          >
                            {addingToUniverse === `event:${ev.event_id}` ? '…' : 'Añadir evento al universo'}
                          </Button>
                        )}
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="border-t border-border bg-muted/20">
                        {ev.markets.map((m) => (
                          <div
                            key={m.market_id}
                            className="px-4 py-3 pl-10 border-b border-border/50 last:border-b-0"
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div className="min-w-0 flex-1">
                                <p className="text-sm font-medium text-foreground mb-1">{m.question}</p>
                                <MarketOutcomesWithProbability market={m} compact={false} />
                              </div>
                              <div className="flex items-center gap-2 shrink-0">
                                {m.liquidity != null && m.liquidity > 0 && (
                                  <span className="text-xs text-muted-foreground">{formatUsdShort(m.liquidity)} liq</span>
                                )}
                                {!isDemo && selectedStrategyId && (
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    disabled={!!addingToUniverse}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleRequestAddToUniverse(m);
                                    }}
                                  >
                                    Añadir mercado al universo
                                  </Button>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })
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
          onConfirm={() => marketToAdd && handleAddToUniverse(marketToAdd)}
          loading={!!addingToUniverse}
        />
      </div>
    </Layout>
  );
}
