'use client';

import { useEffect, useState } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';

interface Series {
  series_id: string;
  polymarket_series_id: string;
  name: string;
  slug: string | null;
  description: string | null;
  series_type: string | null;
  recurrence: string | null;
  markets_count: number;
  created_at: string;
  updated_at: string;
}

interface Tag {
  tag_id: string;
  name: string;
}

interface Market {
  market_id: string;
  polymarket_id: string;
  name: string;
  category: string | null;
  enabled: boolean;
  series_id: string | null;
  series_name: string | null;
  tags: Tag[];
  events_count: number;
  created_at: string;
  updated_at: string;
}

interface Event {
  event_id: string;
  polymarket_event_id: string;
  market_id: string;
  market_name: string;
  start_time: string | null;
  end_time: string | null;
  state: 'UPCOMING' | 'ACTIVE' | 'FINISHED';
  created_at: string;
  updated_at: string;
}

export default function MarketsPage() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const [series, setSeries] = useState<Series[]>([]);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'series' | 'markets' | 'events'>('markets');
  const [viewMode, setViewMode] = useState<'flat' | 'hierarchical'>('flat');
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [seriesFilter, setSeriesFilter] = useState<string>('all');
  const [tagFilter, setTagFilter] = useState<string>('all');
  const [enabledFilter, setEnabledFilter] = useState<string>('all');
  const [stateFilter, setStateFilter] = useState<string>('all');
  const [togglingMarket, setTogglingMarket] = useState<string | null>(null);
  const [expandedSeries, setExpandedSeries] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!user || !stackApp) return;

    const api = initApiClient(createTokenGetter(user, stackApp));
    let isInitialLoad = true;

    const fetchData = async (isInitial = false) => {
      try {
        // Fetch series, markets, events, and tags
        const [seriesData, marketsData, eventsData, tagsData] = await Promise.all([
          api.get<Series[]>('/series').catch(() => []),
          api.get<Market[]>('/markets').catch(() => []),
          api.get<Event[]>('/markets/events/list').catch(() => []),
          api.get<Tag[]>('/tags').catch(() => []),
        ]);

        setSeries(seriesData);
        setMarkets(marketsData);
        setEvents(eventsData);
        setTags(tagsData);
      } catch (err) {
        console.error('Error fetching data:', err);
      } finally {
        // Solo desactivar loading en la carga inicial
        if (isInitial) {
          setLoading(false);
        }
      }
    };

    // Carga inicial con loading
    setLoading(true);
    fetchData(true);
    
    // Actualizaciones periódicas sin mostrar loading
    const interval = setInterval(() => {
      isInitialLoad = false;
      fetchData(false);
    }, 5000); // Refresh every 5 seconds
    
    return () => clearInterval(interval);
  }, [user, stackApp]);

  const handleToggleMarket = async (marketId: string, currentEnabled: boolean) => {
    if (!user || !stackApp || !isConnected || togglingMarket) return;
    
    setTogglingMarket(marketId);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.patch(`/markets/${marketId}/enable`, { enabled: !currentEnabled });
      
      // Update local state
      setMarkets(prev => prev.map(m => 
        m.market_id === marketId ? { ...m, enabled: !currentEnabled } : m
      ));
    } catch (err) {
      console.error('Error toggling market:', err);
    } finally {
      setTogglingMarket(null);
    }
  };

  const toggleSeries = (seriesId: string) => {
    setExpandedSeries(prev => {
      const next = new Set(prev);
      if (next.has(seriesId)) {
        next.delete(seriesId);
      } else {
        next.add(seriesId);
      }
      return next;
    });
  };

  // Filter markets based on active filters
  const filteredMarkets = markets.filter(market => {
    if (searchTerm && !market.name.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    if (categoryFilter !== 'all' && market.category !== categoryFilter) {
      return false;
    }
    if (seriesFilter !== 'all' && market.series_id !== seriesFilter) {
      return false;
    }
    if (tagFilter !== 'all' && !market.tags.some(t => t.tag_id === tagFilter)) {
      return false;
    }
    if (enabledFilter !== 'all') {
      const isEnabled = enabledFilter === 'enabled';
      if (market.enabled !== isEnabled) return false;
    }
    return true;
  });

  // Filter events
  const filteredEvents = events.filter(event => {
    if (stateFilter !== 'all' && event.state !== stateFilter) {
      return false;
    }
    return true;
  });

  // Group markets by series for hierarchical view
  const marketsBySeries = filteredMarkets.reduce((acc, market) => {
    const seriesId = market.series_id || 'no-series';
    if (!acc[seriesId]) {
      acc[seriesId] = {
        series: market.series_name ? series.find(s => s.series_id === market.series_id) : null,
        markets: []
      };
    }
    acc[seriesId].markets.push(market);
    return acc;
  }, {} as Record<string, { series: Series | null; markets: Market[] }>);

  const categories = Array.from(new Set(markets.map(m => m.category).filter(Boolean))) as string[];

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner text="Cargando mercados..." />
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-medium text-slate-900">Mercados</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Series: agrupadores lógicos. Markets: plantillas. Events: instancias tradeables.
            </p>
          </div>
          {!isConnected && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-slate-200 bg-slate-50">
              <div className="w-1.5 h-1.5 rounded-full bg-slate-300"></div>
              <span className="text-xs text-slate-500">Demo</span>
            </div>
          )}
        </div>

        {!isConnected && (
          <div className="border border-slate-200 rounded-lg p-3 bg-white">
            <p className="text-xs text-slate-500">
              Modo demostración. Conecta el backend para activar/desactivar markets.
            </p>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 border-b border-slate-200 mb-4">
          <button
            onClick={() => setActiveTab('series')}
            className={`px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === 'series'
                ? 'border-b-2 border-slate-900 text-slate-900'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Series ({series.length})
          </button>
          <button
            onClick={() => setActiveTab('markets')}
            className={`px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === 'markets'
                ? 'border-b-2 border-slate-900 text-slate-900'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Markets ({markets.length})
          </button>
          <button
            onClick={() => setActiveTab('events')}
            className={`px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === 'events'
                ? 'border-b-2 border-slate-900 text-slate-900'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Events ({events.length})
          </button>
        </div>

        {/* Series Tab */}
        {activeTab === 'series' && (
          <div className="space-y-4">
            {series.length === 0 ? (
              <div className="border border-slate-200 rounded-lg p-8 text-center bg-white">
                <p className="text-xs text-slate-500 mb-1">No hay series disponibles</p>
                <p className="text-xs text-slate-400">
                  Las series aparecerán aquí cuando el scanner las descubra
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {series.map((s) => {
                  const seriesMarkets = markets.filter(m => m.series_id === s.series_id);
                  const isExpanded = expandedSeries.has(s.series_id);
                  
                  return (
                    <div key={s.series_id} className="border border-slate-200 rounded-lg bg-white">
                      <div
                        className="p-3 border-b border-slate-100 cursor-pointer hover:bg-slate-50 transition-colors"
                        onClick={() => toggleSeries(s.series_id)}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <h3 className="text-xs font-medium text-slate-900">{s.name}</h3>
                            {s.description && (
                              <p className="text-xs text-slate-500 mt-0.5">{s.description}</p>
                            )}
                            <div className="flex items-center gap-2 mt-1">
                              <span className="text-xs text-slate-400">
                                {seriesMarkets.length} markets
                              </span>
                              {s.recurrence && (
                                <span className="text-xs text-slate-400">• {s.recurrence}</span>
                              )}
                            </div>
                          </div>
                          <button className="text-slate-400 hover:text-slate-600">
                            <svg
                              className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </button>
                        </div>
                      </div>
                      
                      {isExpanded && (
                        <div className="p-3 space-y-2">
                          {seriesMarkets.length === 0 ? (
                            <p className="text-xs text-slate-400 text-center py-2">
                              No hay markets en esta serie
                            </p>
                          ) : (
                            seriesMarkets.map((market) => (
                              <div
                                key={market.market_id}
                                className="p-2 border border-slate-200 rounded bg-slate-50 hover:bg-slate-100 transition-colors"
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex-1">
                                    <div className="text-xs font-medium text-slate-900">
                                      {market.name}
                                    </div>
                                    {market.category && (
                                      <div className="text-xs text-slate-500 mt-0.5">
                                        {market.category}
                                      </div>
                                    )}
                                    {market.tags.length > 0 && (
                                      <div className="flex flex-wrap gap-1 mt-1">
                                        {market.tags.map((tag) => (
                                          <span
                                            key={tag.tag_id}
                                            className="text-xs px-1.5 py-0.5 rounded bg-slate-200 text-slate-600"
                                          >
                                            {tag.name}
                                          </span>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs text-slate-500">
                                      {market.events_count} events
                                    </span>
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleToggleMarket(market.market_id, market.enabled);
                                      }}
                                      disabled={!isConnected || togglingMarket === market.market_id}
                                      className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                                        market.enabled
                                          ? 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                                          : 'bg-slate-900 text-white hover:bg-slate-800'
                                      } disabled:opacity-40 disabled:cursor-not-allowed`}
                                    >
                                      {togglingMarket === market.market_id ? '...' : market.enabled ? 'ON' : 'OFF'}
                                    </button>
                                  </div>
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Markets Tab */}
        {activeTab === 'markets' && (
          <div className="space-y-4">
            {/* View Mode Toggle */}
            <div className="flex items-center justify-between">
              <div className="flex gap-2 items-center flex-wrap">
                <input
                  type="text"
                  placeholder="Buscar markets..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="px-3 py-1.5 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-slate-400"
                />
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="px-2 py-1.5 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-slate-400"
                >
                  <option value="all">Todas las categorías</option>
                  {categories.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
                <select
                  value={seriesFilter}
                  onChange={(e) => setSeriesFilter(e.target.value)}
                  className="px-2 py-1.5 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-slate-400"
                >
                  <option value="all">Todas las series</option>
                  {series.map(s => (
                    <option key={s.series_id} value={s.series_id}>{s.name}</option>
                  ))}
                </select>
                <select
                  value={tagFilter}
                  onChange={(e) => setTagFilter(e.target.value)}
                  className="px-2 py-1.5 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-slate-400"
                >
                  <option value="all">Todos los tags</option>
                  {tags.map(t => (
                    <option key={t.tag_id} value={t.tag_id}>{t.name}</option>
                  ))}
                </select>
                <select
                  value={enabledFilter}
                  onChange={(e) => setEnabledFilter(e.target.value)}
                  className="px-2 py-1.5 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-slate-400"
                >
                  <option value="all">Todos</option>
                  <option value="enabled">Activos</option>
                  <option value="disabled">Inactivos</option>
                </select>
              </div>
              <div className="flex gap-1 border border-slate-200 rounded">
                <button
                  onClick={() => setViewMode('flat')}
                  className={`px-2 py-1 text-xs font-medium transition-colors ${
                    viewMode === 'flat'
                      ? 'bg-slate-900 text-white'
                      : 'bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  Lista
                </button>
                <button
                  onClick={() => setViewMode('hierarchical')}
                  className={`px-2 py-1 text-xs font-medium transition-colors ${
                    viewMode === 'hierarchical'
                      ? 'bg-slate-900 text-white'
                      : 'bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  Por Series
                </button>
              </div>
            </div>

            {/* Markets Display */}
            {viewMode === 'flat' ? (
              <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
                <div className="overflow-x-auto">
                  <table className="min-w-full">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                          Market
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                          Series
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                          Tags
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                          Categoría
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                          Events
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                          Estado
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                          Acción
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredMarkets.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="px-4 py-8 text-center text-xs text-slate-500">
                            No hay markets disponibles
                          </td>
                        </tr>
                      ) : (
                        filteredMarkets.map((market) => (
                          <tr key={market.market_id} className="hover:bg-slate-50 transition-colors">
                            <td className="px-4 py-3">
                              <div className="text-xs text-slate-900 font-medium">
                                {market.name}
                              </div>
                              <div className="text-xs text-slate-400 mt-0.5 font-mono">
                                {market.polymarket_id.substring(0, 16)}...
                              </div>
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-600">
                              {market.series_name || '-'}
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex flex-wrap gap-1">
                                {market.tags.length > 0 ? (
                                  market.tags.map((tag) => (
                                    <span
                                      key={tag.tag_id}
                                      className="text-xs px-1.5 py-0.5 rounded bg-slate-100 text-slate-600"
                                    >
                                      {tag.name}
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-xs text-slate-400">-</span>
                                )}
                              </div>
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-600">
                              {market.category || '-'}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-600">
                              {market.events_count}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap">
                              <span className={`text-xs px-1.5 py-0.5 rounded border ${
                                market.enabled
                                  ? 'bg-slate-100 text-slate-700 border-slate-200'
                                  : 'bg-slate-50 text-slate-500 border-slate-200'
                              }`}>
                                {market.enabled ? 'Activo' : 'Inactivo'}
                              </span>
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap">
                              <button
                                onClick={() => handleToggleMarket(market.market_id, market.enabled)}
                                disabled={!isConnected || togglingMarket === market.market_id}
                                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                                  market.enabled
                                    ? 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                                    : 'bg-slate-900 text-white hover:bg-slate-800'
                                } disabled:opacity-40 disabled:cursor-not-allowed`}
                              >
                                {togglingMarket === market.market_id ? (
                                  <span className="flex items-center gap-1">
                                    <span className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin"></span>
                                    ...
                                  </span>
                                ) : (
                                  market.enabled ? 'Desactivar' : 'Activar'
                                )}
                              </button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {Object.entries(marketsBySeries).map(([seriesId, { series: seriesData, markets: seriesMarkets }]) => (
                  <div key={seriesId} className="border border-slate-200 rounded-lg bg-white">
                    <div className="p-3 border-b border-slate-100">
                      <h3 className="text-xs font-medium text-slate-900">
                        {seriesData?.name || 'Sin Serie'}
                      </h3>
                      {seriesData?.description && (
                        <p className="text-xs text-slate-500 mt-0.5">{seriesData.description}</p>
                      )}
                    </div>
                    <div className="p-3 space-y-2">
                      {seriesMarkets.length === 0 ? (
                        <p className="text-xs text-slate-400 text-center py-2">
                          No hay markets en esta serie
                        </p>
                      ) : (
                        seriesMarkets.map((market) => (
                          <div
                            key={market.market_id}
                            className="p-2 border border-slate-200 rounded bg-slate-50 hover:bg-slate-100 transition-colors"
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex-1">
                                <div className="text-xs font-medium text-slate-900">
                                  {market.name}
                                </div>
                                {market.category && (
                                  <div className="text-xs text-slate-500 mt-0.5">
                                    {market.category}
                                  </div>
                                )}
                                {market.tags.length > 0 && (
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {market.tags.map((tag) => (
                                      <span
                                        key={tag.tag_id}
                                        className="text-xs px-1.5 py-0.5 rounded bg-slate-200 text-slate-600"
                                      >
                                        {tag.name}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-slate-500">
                                  {market.events_count} events
                                </span>
                                <button
                                  onClick={() => handleToggleMarket(market.market_id, market.enabled)}
                                  disabled={!isConnected || togglingMarket === market.market_id}
                                  className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                                    market.enabled
                                      ? 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                                      : 'bg-slate-900 text-white hover:bg-slate-800'
                                  } disabled:opacity-40 disabled:cursor-not-allowed`}
                                >
                                  {togglingMarket === market.market_id ? '...' : market.enabled ? 'ON' : 'OFF'}
                                </button>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Events Tab */}
        {activeTab === 'events' && (
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex gap-2 items-center">
              <select
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
                className="px-2 py-1.5 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-slate-400"
              >
                <option value="all">Todos los estados</option>
                <option value="UPCOMING">Próximos</option>
                <option value="ACTIVE">Activos</option>
                <option value="FINISHED">Finalizados</option>
              </select>
            </div>

            {/* Events Table */}
            <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Event ID
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Market
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Inicio
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Fin
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Estado
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredEvents.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-xs text-slate-500">
                          No hay events disponibles
                        </td>
                      </tr>
                    ) : (
                      filteredEvents.map((event) => (
                        <tr key={event.event_id} className="hover:bg-slate-50 transition-colors">
                          <td className="px-4 py-3">
                            <div className="text-xs text-slate-900 font-medium font-mono">
                              {event.polymarket_event_id.substring(0, 20)}...
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="text-xs text-slate-900">
                              {event.market_name}
                            </div>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-600">
                            {event.start_time ? (
                              new Date(event.start_time).toLocaleString('es-ES', {
                                day: '2-digit',
                                month: '2-digit',
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            ) : (
                              '-'
                            )}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-600">
                            {event.end_time ? (
                              new Date(event.end_time).toLocaleString('es-ES', {
                                day: '2-digit',
                                month: '2-digit',
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            ) : (
                              '-'
                            )}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className={`text-xs px-1.5 py-0.5 rounded border ${
                              event.state === 'ACTIVE'
                                ? 'bg-green-100 text-green-700 border-green-200'
                                : event.state === 'UPCOMING'
                                ? 'bg-blue-100 text-blue-700 border-blue-200'
                                : 'bg-slate-100 text-slate-600 border-slate-200'
                            }`}>
                              {event.state}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
