'use client';

import { useState } from 'react';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { SeriesListWithLoader } from '@/components/markets/SeriesListWithLoader';
import { MarketsListWithLoader } from '@/components/markets/MarketsListWithLoader';
import { EventsListWithLoader } from '@/components/markets/EventsListWithLoader';
import { TagsFilterWithLoader } from '@/components/markets/TagsFilterWithLoader';
import { SeriesFilterWithLoader } from '@/components/markets/SeriesFilterWithLoader';
import { CategoriesFilterWithLoader } from '@/components/markets/CategoriesFilterWithLoader';
import { MarketsCountBadge } from '@/components/markets/MarketsCountBadge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export default function MarketsPage() {
  const user = useUser();
  const { isConnected } = useBackendConnection();
  const [activeTab, setActiveTab] = useState<'series' | 'markets' | 'events'>('markets');
  const [viewMode, setViewMode] = useState<'flat' | 'hierarchical'>('flat');
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [seriesFilter, setSeriesFilter] = useState<string>('all');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [enabledFilter, setEnabledFilter] = useState<string>('all');
  const [stateFilter, setStateFilter] = useState<string>('all');

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
            Series <MarketsCountBadge type="series" />
          </button>
          <button
            onClick={() => setActiveTab('markets')}
            className={`px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === 'markets'
                ? 'border-b-2 border-slate-900 text-slate-900'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Markets <MarketsCountBadge type="markets" />
          </button>
          <button
            onClick={() => setActiveTab('events')}
            className={`px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === 'events'
                ? 'border-b-2 border-slate-900 text-slate-900'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Events <MarketsCountBadge type="events" />
          </button>
        </div>

        {/* Series Tab - Carga independiente */}
        {activeTab === 'series' && (
          <div className="space-y-4">
            <SeriesListWithLoader showEvents={true} />
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
                <CategoriesFilterWithLoader
                  categoryFilter={categoryFilter}
                  onCategoryChange={setCategoryFilter}
                />
                <SeriesFilterWithLoader
                  selectedSeries={seriesFilter}
                  onSelectionChange={setSeriesFilter}
                />
                <TagsFilterWithLoader
                  selectedTags={selectedTags}
                  onSelectionChange={setSelectedTags}
                />
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

            {/* Markets Display - Carga independiente */}
            {viewMode === 'flat' ? (
              <MarketsListWithLoader
                searchTerm={searchTerm}
                categoryFilter={categoryFilter}
                seriesFilter={seriesFilter}
                selectedTags={selectedTags}
                enabledFilter={enabledFilter}
                showEvents={true}
              />
            ) : (
              <SeriesListWithLoader showEvents={true} />
            )}
          </div>
        )}

        {/* Events Tab - Carga independiente */}
        {activeTab === 'events' && (
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex gap-2 items-center">
              <Select value={stateFilter} onValueChange={setStateFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Todos los estados" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los estados</SelectItem>
                  <SelectItem value="UPCOMING">Próximos</SelectItem>
                  <SelectItem value="ACTIVE">Activos</SelectItem>
                  <SelectItem value="FINISHED">Finalizados</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Events Table - Carga independiente */}
            <EventsListWithLoader stateFilter={stateFilter} />
          </div>
        )}
      </div>
    </Layout>
  );
}
