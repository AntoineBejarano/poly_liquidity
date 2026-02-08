'use client';

import { useParams } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { Layout } from '@/components/Layout';
import { useDataMode } from '@/hooks/useDataMode';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { DiscoveryClient, getLeagueBySlug, isValidLeagueSlug } from '@/lib/discovery';
import {
  filterEventsBy,
  sortEventsBy,
  type DiscoverySortKey,
  type DiscoveryFiltersState,
} from '@/lib/discovery/event-aggregates';
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
import { DiscoveryFiltersBar } from '@/components/markets/DiscoveryFiltersBar';
import { TooltipProvider } from '@/components/ui/tooltip';

const OVERFETCH_LIMIT = 100;

const defaultFilters: DiscoveryFiltersState = {
  tradeableOnly: false,
  minEdgeCents: null,
  minVol24: null,
  maxSpreadBps: null,
  volatilityLabel: 'any',
  executionLabel: 'any',
};

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

export default function SportsLeagueGamesPage() {
  const params = useParams();
  const leagueSlug = (params?.league as string) ?? '';
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
  const [sortBy, setSortBy] = useState<DiscoverySortKey>('event_score');
  const [tradeableFilter, setTradeableFilter] = useState<'yes' | 'all'>('yes');
  const [filters, setFilters] = useState<DiscoveryFiltersState>(defaultFilters);

  const league = getLeagueBySlug(leagueSlug);
  const searched = useMemo(() => searchEvents(events, searchQuery), [events, searchQuery]);
  const filtered = useMemo(
    () => filterEventsBy(searched, filters, tradeableFilter),
    [searched, filters, tradeableFilter]
  );
  const sorted = useMemo(() => sortEventsBy(filtered, sortBy), [filtered, sortBy]);
  const noTradeableButHasEvents = tradeableFilter === 'yes' && filtered.length === 0 && searched.length > 0;
  const noEventsMatchFilters = filtered.length === 0 && searched.length > 0;
  const displayList = useMemo(
    () => (noTradeableButHasEvents ? sortEventsBy(searched, sortBy) : sorted),
    [noTradeableButHasEvents, searched, sortBy, sorted]
  );
  const isValid = isValidLeagueSlug(leagueSlug);

  const fetchEvents = useCallback(
    async (off: number, append: boolean) => {
      if (!league?.gammaTagSlug || isDemo) return;
      setLoading(true);
      setError(null);
      try {
        const client = new DiscoveryClient(createTokenGetter(user ?? undefined, stackApp ?? undefined));
        const result = await client.fetchDiscoveryScreener({
          tag_slug: league.gammaTagSlug,
          closed: false,
          limit: OVERFETCH_LIMIT,
          offset: off,
          tradeable_only: tradeableFilter === 'yes',
          min_edge_cents: filters.minEdgeCents ?? undefined,
          sort: 'event_score',
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
    [league, isDemo, user, stackApp, tradeableFilter, filters.minEdgeCents]
  );

  useEffect(() => {
    if (isValid && league?.gammaTagSlug && !isDemo) {
      setOffset(0);
      fetchEvents(0, false);
    } else {
      setLoading(false);
      setEvents([]);
    }
  }, [isValid, league?.gammaTagSlug, isDemo, fetchEvents]);

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
          <AlertTitle>Liga no válida</AlertTitle>
          <AlertDescription>Usa /sports/nfl/games, /sports/nba/games, etc.</AlertDescription>
        </Alert>
      </Layout>
    );
  }

  const leagueLabel = league?.leagueSlug?.toUpperCase() ?? leagueSlug;

  return (
    <Layout>
      <TooltipProvider>
        <div className="space-y-4 p-4">
          <Link href="/markets" className="text-sm text-muted-foreground hover:text-foreground">
            ← Discovery
          </Link>
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <h1 className="text-xl font-semibold">{leagueLabel} — Eventos</h1>
              <div className="flex items-center gap-2">
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
            <DiscoveryFiltersBar
              sortBy={sortBy}
              onSortChange={setSortBy}
              tradeableFilter={tradeableFilter}
              onTradeableFilterChange={setTradeableFilter}
              showTtr={false}
              filters={filters}
              onFiltersChange={setFilters}
              showAdvanced={true}
              terminal={true}
            />
            <div className="flex items-center gap-2 flex-wrap">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={`Buscar por partido o evento en ${leagueLabel}...`}
                className="flex-1 min-w-[200px] max-w-sm px-3 py-2 text-sm border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
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
                Con el filtro &quot;Solo tradeables&quot; no hay mercados con precios. Los eventos siguientes no tienen mercados con precios disponibles.
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
                  {noEventsMatchFilters
                    ? 'No hay eventos que coincidan con los filtros seleccionados. Prueba a cambiar o limpiar filtros.'
                    : 'No hay eventos para esta liga.'}
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
                                {(m as DiscoveryScreenerMarket).sports_market_type && (
                                  <p className="text-[11px] uppercase tracking-wider text-[#6B7280]">
                                    {(m as DiscoveryScreenerMarket).sports_market_type}
                                  </p>
                                )}
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
