'use client';

import { useUser, useStackApp } from '@stackframe/stack';
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Layout } from '@/components/Layout';
import { useDataMode } from '@/hooks/useDataMode';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { DiscoveryClient } from '@/lib/discovery';
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
import {
  useSportsWebSocket,
  computeEventState,
  getLiveUpdateForDisplay,
  getLiveUpdatesList,
  isLiveFromWs,
  matchEventToSportResult,
} from '@/hooks/useSportsWebSocket';
import type { SportsLiveUpdate } from '@/hooks/useSportsWebSocket';

const OVERFETCH_LIMIT = 100;
/** Tags base para tener pool amplio de eventos con mercados; se suman ligas dinámicas del WS */
const BASE_TAGS = ['sports', 'arg', 'lal', 'cbb', 'soccer', 'nfl', 'nba', 'ncaab', 'mlb', 'nhl'];

/** Ítem de la lista Live: evento con datos Gamma o solo datos del WS */
type LiveListItem =
  | { type: 'event'; event: DiscoveryScreenerEvent }
  | { type: 'ws_only'; update: SportsLiveUpdate };

const defaultFilters: DiscoveryFiltersState = {
  tradeableOnly: false,
  minEdgeCents: null,
  minVol24: null,
  maxSpreadBps: null,
  volatilityLabel: 'any',
  executionLabel: 'any',
  ttrMaxMinutes: null,
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

export default function SportsLivePage() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isDemo } = useDataMode();

  const [events, setEvents] = useState<DiscoveryScreenerEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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

  const { updatesByKey, connectionStatus } = useSportsWebSocket(!isDemo);

  /** Tags: base amplia (para tener eventos con mercados) + ligas que envía el WS. */
  const tagsToFetch = useMemo(() => {
    const leagues = new Set<string>(BASE_TAGS);
    updatesByKey.forEach((u) => {
      if (isLiveFromWs(u) && u.leagueAbbreviation) leagues.add(u.leagueAbbreviation);
    });
    return Array.from(leagues).sort();
  }, [updatesByKey]);

  const searched = useMemo(() => searchEvents(events, searchQuery), [events, searchQuery]);
  const filtered = useMemo(
    () => filterEventsBy(searched, filters, tradeableFilter),
    [searched, filters, tradeableFilter]
  );
  const sorted = useMemo(() => sortEventsBy(filtered, sortBy), [filtered, sortBy]);
  const noTradeableButHasEvents = tradeableFilter === 'yes' && filtered.length === 0 && searched.length > 0;
  const noEventsMatchFilters = filtered.length === 0 && searched.length > 0;

  const baseEvents = noTradeableButHasEvents ? sortEventsBy(searched, sortBy) : sorted;

  /** Eventos con TODOS los mercados (sin filtrar por tradeable) para mostrar en la card. */
  const fullEventsById = useMemo(() => {
    const m = new Map<string, DiscoveryScreenerEvent>();
    searched.forEach((e) => m.set(e.event_id, e));
    return m;
  }, [searched]);

  /** Lista dinámica: match por gameId (Gamma = WS) primero, luego por título; el resto como ws_only. */
  const displayList = useMemo((): LiveListItem[] => {
    const matchedGameIds = new Set<number>();
    const matched: LiveListItem[] = [];
    const liveUpdates = getLiveUpdatesList(updatesByKey);

    // 1) Mapeo directo por gameId (documentación Polymarket: market.gameId = WS gameId)
    for (const ev of baseEvents) {
      const gid = ev.game_id ?? ev.markets?.[0]?.game_id;
      if (gid == null) continue;
      const u = liveUpdates.find((x) => x.gameId === gid);
      if (u && !matchedGameIds.has(u.gameId)) {
        matchedGameIds.add(u.gameId);
        matched.push({ type: 'event', event: ev });
      }
    }

    // 2) Fallback: match por título para eventos sin game_id o no matcheados
    for (const ev of baseEvents) {
      if (matched.some((i) => i.type === 'event' && i.event.event_id === ev.event_id)) continue;
      const m = matchEventToSportResult(ev.title ?? '', updatesByKey);
      if (m && isLiveFromWs(m.update) && !matchedGameIds.has(m.update.gameId)) {
        matchedGameIds.add(m.update.gameId);
        matched.push({ type: 'event', event: ev });
      }
    }

    const wsOnly: LiveListItem[] = liveUpdates
      .filter((u) => !matchedGameIds.has(u.gameId))
      .map((u) => ({ type: 'ws_only' as const, update: u }));
    return [...matched, ...wsOnly];
  }, [baseEvents, updatesByKey]);

  // Observability: log when a sport_result has no matching event (solo para ítems tipo event)
  useEffect(() => {
    if (isDemo || updatesByKey.size === 0) return;
    const eventTitles = displayList
      .filter((i): i is LiveListItem & { type: 'event' } => i.type === 'event')
      .map((i) => (i.event.title ?? '').trim().toLowerCase());
    for (const [, u] of updatesByKey) {
      if (!isLiveFromWs(u) && !u.ended) continue;
      const home = (u.homeTeam ?? '').trim().toLowerCase();
      const away = (u.awayTeam ?? '').trim().toLowerCase();
      if (!home || !away) continue;
      const matched = eventTitles.some((t) => t.includes(home) && t.includes(away));
      if (!matched && process.env.NODE_ENV === 'development') {
        console.debug(
          '[SportsLive] matching_failure: sport_result has no matching event',
          { key: u.slug ?? `game:${u.gameId}`, homeTeam: u.homeTeam, awayTeam: u.awayTeam }
        );
      }
    }
  }, [displayList, updatesByKey, isDemo]);

  const fetchEvents = useCallback(
    async (tags: string[]) => {
      if (isDemo) return;
      setLoading(true);
      setError(null);
      try {
        const client = new DiscoveryClient(createTokenGetter(user ?? undefined, stackApp ?? undefined));
        const opts = {
          closed: false,
          limit: OVERFETCH_LIMIT,
          offset: 0,
          tradeable_only: tradeableFilter === 'yes',
          min_edge_cents: filters.minEdgeCents ?? undefined,
          sort: 'event_score' as const,
          live: false,
        };
        const results = await Promise.all(
          tags.map((tag_slug) => client.fetchDiscoveryScreener({ ...opts, tag_slug }))
        );
        const byId = new Map<string, DiscoveryScreenerEvent>();
        for (const r of results) {
          for (const ev of r.events) {
            if (ev.event_id && !byId.has(ev.event_id)) byId.set(ev.event_id, ev);
          }
        }
        setEvents(Array.from(byId.values()));
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Error al cargar');
        setEvents([]);
      } finally {
        setLoading(false);
      }
    },
    [isDemo, user, stackApp, tradeableFilter, filters.minEdgeCents]
  );

  const lastTagsRef = useRef<string>('');
  useEffect(() => {
    if (isDemo) {
      setLoading(false);
      return;
    }
    const key = tagsToFetch.join(',');
    if (key === lastTagsRef.current) return;
    lastTagsRef.current = key;
    fetchEvents(tagsToFetch);
  }, [isDemo, fetchEvents, tagsToFetch]);

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

  return (
    <Layout>
      <TooltipProvider>
        <div className="space-y-4 p-4">
          <Link href="/markets" className="text-sm text-muted-foreground hover:text-foreground">
            ← Discovery
          </Link>
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <h1 className="text-xl font-semibold">Sports — Eventos</h1>
              <div className="flex items-center gap-2">
                {!isDemo && (
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
                      connectionStatus === 'open'
                        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                        : 'bg-red-500/15 text-red-400 border border-red-500/30'
                    }`}
                    title={
                      connectionStatus === 'open'
                        ? 'WebSocket conectado (resultados en vivo disponibles)'
                        : connectionStatus === 'connecting'
                          ? 'Conectando…'
                          : 'Sin conexión al WebSocket de deportes'
                    }
                  >
                    <span
                      className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                        connectionStatus === 'open' ? 'bg-emerald-400' : 'bg-red-400'
                      }`}
                    />
                    {connectionStatus === 'open'
                      ? 'WS Connected'
                      : connectionStatus === 'connecting'
                        ? 'Conectando…'
                        : 'Not connected'}
                  </span>
                )}
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
                <Button variant="outline" size="sm" onClick={() => fetchEvents(tagsToFetch)} disabled={loading}>
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
                placeholder="Buscar partidos..."
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
                Con el filtro &quot;Solo tradeables&quot; no hay mercados con precios disponibles.
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
                    : connectionStatus === 'open'
                      ? 'Solo se muestran partidos en vivo (WebSocket). No hay ninguno ahora.'
                      : connectionStatus === 'connecting'
                        ? 'Conectando al WebSocket… Solo se listan partidos en vivo.'
                        : 'Solo se muestran partidos en vivo (WebSocket). Conecta para ver la lista.'}
                </p>
              ) : (
                displayList.map((item) => {
                  if (item.type === 'ws_only') {
                    const u = item.update;
                    return (
                      <div
                        key={`ws-${u.gameId}`}
                        className="rounded-lg border border-[#1F2937] bg-[#111827] p-4 flex flex-wrap items-center gap-3"
                      >
                        <span className="font-semibold text-[#E5E7EB]">
                          {u.awayTeam} @ {u.homeTeam}
                        </span>
                        <span className="text-[#22C55E] font-medium tabular-nums">{u.score}</span>
                        {u.period && (
                          <span className="text-[#9CA3AF] text-sm">
                            {u.period}
                            {u.elapsed ? ` ${u.elapsed}` : ''}
                          </span>
                        )}
                        {u.leagueAbbreviation && (
                          <span className="text-[11px] uppercase text-[#6B7280]">{u.leagueAbbreviation}</span>
                        )}
                        <span className="text-xs text-[#6B7280]">Solo datos en vivo (sin mercados)</span>
                      </div>
                    );
                  }
                  const ev = item.event;
                  const fullEv = fullEventsById.get(ev.event_id) ?? ev;
                  const eventState = computeEventState(
                    ev.title ?? '',
                    ev.live_estimated,
                    updatesByKey
                  );
                  const liveUpdate = getLiveUpdateForDisplay(
                    ev.title ?? '',
                    ev.live_estimated,
                    updatesByKey
                  );
                  return (
                    <DiscoveryEventCard
                      key={ev.event_id}
                      event={fullEv}
                      isExpanded={expandedEventId === ev.event_id}
                      onToggle={() => setExpandedEventId(expandedEventId === ev.event_id ? null : ev.event_id)}
                      noTradeableState={noTradeableButHasEvents}
                      isDemo={isDemo}
                      selectedStrategyId={selectedStrategyId}
                      addingToUniverse={addingToUniverse}
                      onAddEvent={() => handleAddEventToUniverse(fullEv)}
                      onAddMarket={handleRequestAddToUniverse}
                      eventState={eventState}
                      liveUpdate={liveUpdate}
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
                  );
                })
              )}
            </div>
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
