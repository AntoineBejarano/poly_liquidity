'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { Strategy, StrategyTemplate } from '@/types/strategy';
import { StrategyConfigForm } from '@/components/StrategyConfigForm';

interface Event {
  id: string;
  name: string;
  market_id: string;
  state: string;
  liquidity?: number;
  volatility?: number;
  time_remaining?: string;
  status?: 'ACTIVE' | 'BLOCKED' | 'ELIGIBLE';
  block_reason?: string;
}

export default function StrategyLiveControlPage() {
  const params = useParams();
  const user = useUser();
  const stackApp = useStackApp();
  const strategyId = params.id as string;

  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [template, setTemplate] = useState<StrategyTemplate | null>(null);
  const [templateConfig, setTemplateConfig] = useState<Record<string, any>>({});
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [entryConditionsExpanded, setEntryConditionsExpanded] = useState(false);
  const [marketFiltersExpanded, setMarketFiltersExpanded] = useState(false);

  useEffect(() => {
    if (!user || !strategyId) return;

    const loadStrategy = async () => {
      try {
        setLoading(true);
        const api = initApiClient(createTokenGetter(user, stackApp));
        const strategyData = await api.get<Strategy>(`/strategies/${strategyId}`);
        setStrategy(strategyData);
      } catch (err) {
        console.error('Error loading strategy:', err);
        setError('Error al cargar la estrategia');
      } finally {
        setLoading(false);
      }
    };

    loadStrategy();
  }, [user, stackApp, strategyId]);

  useEffect(() => {
    if (!user || !strategy) return;

    const loadEvents = async () => {
      try {
        const api = initApiClient(createTokenGetter(user, stackApp));
        const strategyEventsResponse = await api.get<{ events: any[] }>(`/strategies/${strategyId}/events`);
        const assignedEventIds = new Set(strategyEventsResponse.events.map((e: any) => e.event_id));
        const allEvents = await api.get<any[]>('/markets/events/list?state=ACTIVE');
        const finishedEvents = await api.get<any[]>('/markets/events/list?state=FINISHED');
        const allAvailableEvents = [...allEvents, ...finishedEvents];
        
        const mappedEvents: Event[] = allAvailableEvents.map((event: any) => {
          const isAssigned = assignedEventIds.has(event.event_id);
          const status: 'ACTIVE' | 'BLOCKED' | 'ELIGIBLE' = isAssigned 
            ? 'ACTIVE' 
            : event.state === 'FINISHED' 
            ? 'ELIGIBLE' 
            : 'BLOCKED';
          
          return {
            id: event.event_id,
            name: event.market_name || 'Unknown Event',
            market_id: event.market_id,
            state: event.state,
            liquidity: 5000,
            volatility: 0.001,
            time_remaining: event.end_time ? 'Ended' : '+2m',
            status,
            block_reason: status === 'BLOCKED' ? 'Not eligible' : undefined,
          };
        });
        
        setEvents(mappedEvents);
      } catch (err) {
        console.error('Error loading events:', err);
        const mockEvents: Event[] = [
          { id: '1', name: 'Bears vs Packers', market_id: 'm1', state: 'FINISHED', liquidity: 8200, volatility: 0.0005, time_remaining: 'Ended', status: 'ACTIVE' },
          { id: '2', name: 'Valencia vs Madrid', market_id: 'm2', state: 'FINISHED', liquidity: 6100, volatility: 0.001, time_remaining: 'Ended', status: 'ACTIVE' },
          { id: '3', name: 'Bitcoin 8:00–8:15', market_id: 'm3', state: 'ACTIVE', liquidity: 1100, volatility: 0.002, time_remaining: '+2m', status: 'BLOCKED', block_reason: 'Volatility too high' },
        ];
        setEvents(mockEvents);
      }
    };

    loadEvents();
  }, [user, stackApp, strategy, strategyId]);

  if (!user) return null;

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-full">
          <div className="text-sm text-[#6b7280]">Cargando estrategia...</div>
        </div>
      </Layout>
    );
  }

  if (error && !strategy) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-full">
          <div className="text-sm text-[#ef4444]">{error || 'Estrategia no encontrada'}</div>
        </div>
      </Layout>
    );
  }

  const eligibleCount = events.filter(e => e.status === 'ELIGIBLE' || e.status === 'ACTIVE').length;
  const activeCount = events.filter(e => e.status === 'ACTIVE').length;
  const blockedCount = events.filter(e => e.status === 'BLOCKED').length;

  return (
    <Layout>
      <div className="h-screen flex flex-col bg-[#fafbfc]">
        {/* Header */}
        <div className="border-b border-[#e5e7eb] bg-white px-8 py-6">
          <div className="max-w-[1600px] mx-auto flex items-center justify-between">
            <div className="flex-1">
              {strategy ? (
                <>
                  <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">
                    {strategy.name}
                    {strategy.is_active && (
                      <span className="ml-3 inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-[#d1fae5] text-[#065f46]">
                        Active
                      </span>
                    )}
                  </h1>
                  <div className="mt-2 flex items-center gap-6 text-sm text-[#6b7280]">
                    <span>Capital usado: <span className="font-medium text-[#111827]">42k / 50k</span></span>
                    <span>ROI 30d: <span className="font-medium text-[#10b981]">+3.2%</span></span>
                  </div>
                </>
              ) : null}
            </div>
            <div className="flex items-center gap-3">
              {strategy && (
                <button
                  onClick={async () => {
                    if (!user) return;
                    const api = initApiClient(createTokenGetter(user, stackApp));
                    try {
                      if (strategy.is_active) {
                        await api.post(`/strategies/${strategyId}/deactivate`);
                        setStrategy({ ...strategy, is_active: false });
                      } else {
                        await api.post(`/strategies/${strategyId}/activate`);
                        setStrategy({ ...strategy, is_active: true });
                      }
                    } catch (err) {
                      console.error('Error toggling strategy:', err);
                      alert(err instanceof Error ? err.message : 'Error al cambiar estado');
                    }
                  }}
                  className={`px-5 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 ${
                    strategy.is_active
                      ? 'bg-[#fee2e2] text-[#991b1b] hover:bg-[#fecaca]'
                      : 'bg-[#d1fae5] text-[#065f46] hover:bg-[#a7f3d0]'
                  }`}
                >
                  {strategy.is_active ? 'Desactivar' : 'Activar'}
                </button>
              )}
            </div>
          </div>
          {error && (
            <div className="mt-4 max-w-[1600px] mx-auto px-4 py-3 bg-[#fee2e2] border border-[#fecaca] rounded-lg text-sm text-[#991b1b]">
              {error}
            </div>
          )}
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Panel - Configuration */}
          <div className="w-96 border-r border-[#e5e7eb] bg-white overflow-y-auto">
            <div className="p-6 space-y-6">
              {/* Strategy Type Card */}
              <div className="bg-white border border-[#e5e7eb] rounded-xl p-6">
                <label className="block text-xs font-semibold text-[#6b7280] mb-4 tracking-wide">
                  Strategy Type
                </label>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-[#111827]">
                    {template?.name || strategy?.name || 'Unknown'}
                  </span>
                </div>
              </div>

              {/* Entry Conditions Card */}
              {template && template.fields && (
                <div className="bg-white border border-[#e5e7eb] rounded-xl overflow-hidden">
                  <button
                    onClick={() => setEntryConditionsExpanded(!entryConditionsExpanded)}
                    className="w-full flex items-center justify-between px-6 py-4 hover:bg-[#f9fafb] transition-colors duration-200"
                  >
                    <span className="text-sm font-semibold text-[#111827]">Entry Conditions</span>
                    <span className="text-[#9ca3af]">{entryConditionsExpanded ? '▼' : '▶'}</span>
                  </button>
                  {entryConditionsExpanded && (
                    <div className="px-6 pb-6 pt-2">
                      <StrategyConfigForm
                        templateId={template.id}
                        templateName={template.name}
                        templateDescription={template.description}
                        fields={template.fields}
                        initialValues={templateConfig}
                        onChange={setTemplateConfig}
                      />
                    </div>
                  )}
                </div>
              )}

              {/* Risk Limits Card - Always Visible */}
              <div className="bg-white border border-[#e5e7eb] rounded-xl p-6">
                <label className="block text-sm font-semibold text-[#111827] mb-5">
                  Risk Limits
                </label>
                <div className="space-y-5">
                  <div>
                    <label className="block text-xs font-medium text-[#6b7280] mb-2">
                      Max per event
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={strategy?.risk_config?.max_order_size || 5000}
                        onChange={async (e) => {
                          if (!user || !strategy) return;
                          const api = initApiClient(createTokenGetter(user, stackApp));
                          try {
                            await api.put(`/strategies/${strategyId}`, {
                              risk_config: {
                                ...strategy.risk_config,
                                max_order_size: Number(e.target.value),
                              },
                            });
                            setStrategy({
                              ...strategy,
                              risk_config: {
                                ...strategy.risk_config,
                                max_order_size: Number(e.target.value),
                              },
                            });
                          } catch (err) {
                            console.error('Error updating risk config:', err);
                          }
                        }}
                        className="flex-1 px-4 py-3 text-sm text-[#111827] bg-white border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent transition-all duration-200"
                      />
                      <span className="text-xs text-[#9ca3af] font-medium">USDC</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[#6b7280] mb-2">
                      Max total exposure
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={strategy?.risk_config?.max_exposure || 30000}
                        onChange={async (e) => {
                          if (!user || !strategy) return;
                          const api = initApiClient(createTokenGetter(user, stackApp));
                          try {
                            await api.put(`/strategies/${strategyId}`, {
                              risk_config: {
                                ...strategy.risk_config,
                                max_exposure: Number(e.target.value),
                              },
                            });
                            setStrategy({
                              ...strategy,
                              risk_config: {
                                ...strategy.risk_config,
                                max_exposure: Number(e.target.value),
                              },
                            });
                          } catch (err) {
                            console.error('Error updating risk config:', err);
                          }
                        }}
                        className="flex-1 px-4 py-3 text-sm text-[#111827] bg-white border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent transition-all duration-200"
                      />
                      <span className="text-xs text-[#9ca3af] font-medium">USDC</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[#6b7280] mb-3">
                      If locked capital
                    </label>
                    <div className="space-y-2">
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input type="radio" name="locked_capital" defaultChecked className="w-4 h-4 text-[#2563eb] border-[#e5e7eb] focus:ring-[#2563eb]" />
                        <span className="text-sm text-[#111827]">Pause entries</span>
                      </label>
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input type="radio" name="locked_capital" className="w-4 h-4 text-[#2563eb] border-[#e5e7eb] focus:ring-[#2563eb]" />
                        <span className="text-sm text-[#111827]">Continue</span>
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              {/* Market Filters Card */}
              <div className="bg-white border border-[#e5e7eb] rounded-xl overflow-hidden">
                <button
                  onClick={() => setMarketFiltersExpanded(!marketFiltersExpanded)}
                  className="w-full flex items-center justify-between px-6 py-4 hover:bg-[#f9fafb] transition-colors duration-200"
                >
                  <span className="text-sm font-semibold text-[#111827]">Market Filters</span>
                  <span className="text-[#9ca3af]">{marketFiltersExpanded ? '▼' : '▶'}</span>
                </button>
                {marketFiltersExpanded && (
                  <div className="px-6 pb-6 pt-2 space-y-5">
                    <div>
                      <label className="block text-xs font-medium text-[#6b7280] mb-2">
                        Min liquidity
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          defaultValue={2000}
                          className="flex-1 px-4 py-3 text-sm text-[#111827] bg-white border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent transition-all duration-200"
                        />
                        <span className="text-xs text-[#9ca3af] font-medium">USDC</span>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6b7280] mb-2">
                        Max ST volatility
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          step="0.0001"
                          defaultValue={0.0015}
                          className="flex-1 px-4 py-3 text-sm text-[#111827] bg-white border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent transition-all duration-200"
                        />
                        <span className="text-xs text-[#9ca3af] font-medium">/s</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Main Panel - Events */}
          <div className="flex-1 flex flex-col overflow-hidden bg-[#fafbfc]">
            {/* Events Header */}
            <div className="border-b border-[#e5e7eb] bg-white px-8 py-5">
              <div className="max-w-[1600px] mx-auto flex items-center justify-between">
                <div className="flex items-center gap-8">
                  <div className="text-sm text-[#6b7280]">
                    Eligible events: <span className="font-semibold text-[#111827]">{eligibleCount}</span>
                  </div>
                  <div className="text-sm text-[#6b7280]">
                    Active events: <span className="font-semibold text-[#10b981]">{activeCount}</span>
                  </div>
                  <div className="text-sm text-[#6b7280]">
                    Blocked: <span className="font-semibold text-[#ef4444]">{blockedCount}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={async () => {
                      if (!user) return;
                      const eligibleEvents = events.filter(e => e.status === 'ELIGIBLE');
                      const api = initApiClient(createTokenGetter(user, stackApp));
                      try {
                        for (const event of eligibleEvents) {
                          await api.post(`/strategies/${strategyId}/events/${event.id}`);
                        }
                        window.location.reload();
                      } catch (err) {
                        console.error('Error activating events:', err);
                        alert('Error al activar eventos');
                      }
                    }}
                    className="px-4 py-2 text-xs font-medium text-[#2563eb] bg-[#eff6ff] rounded-lg hover:bg-[#dbeafe] transition-all duration-200"
                  >
                    Activate all eligible
                  </button>
                  <button
                    onClick={async () => {
                      if (!user) return;
                      const api = initApiClient(createTokenGetter(user, stackApp));
                      try {
                        const strategyEvents = await api.get<{ events: any[] }>(`/strategies/${strategyId}/events`);
                        for (const se of strategyEvents.events) {
                          await api.delete(`/strategies/${strategyId}/events/${se.event_id}`);
                        }
                        window.location.reload();
                      } catch (err) {
                        console.error('Error deactivating events:', err);
                        alert('Error al desactivar eventos');
                      }
                    }}
                    className="px-4 py-2 text-xs font-medium text-[#6b7280] bg-[#f3f4f6] rounded-lg hover:bg-[#e5e7eb] transition-all duration-200"
                  >
                    Deactivate all
                  </button>
                </div>
              </div>
            </div>

            {/* Events Table */}
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-[1600px] mx-auto">
                <table className="w-full">
                  <thead className="bg-[#fafbfc] sticky top-0 border-b border-[#e5e7eb]">
                    <tr>
                      <th className="px-6 py-4 text-left text-xs font-semibold text-[#6b7280]">Event</th>
                      <th className="px-6 py-4 text-left text-xs font-semibold text-[#6b7280]">Liq</th>
                      <th className="px-6 py-4 text-left text-xs font-semibold text-[#6b7280]">Vol</th>
                      <th className="px-6 py-4 text-left text-xs font-semibold text-[#6b7280]">Time</th>
                      <th className="px-6 py-4 text-left text-xs font-semibold text-[#6b7280]">Status</th>
                      <th className="px-6 py-4 text-left text-xs font-semibold text-[#6b7280]">Action</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-[#e5e7eb]">
                    {events.map((event) => (
                      <tr key={event.id} className="hover:bg-[#fafbfc] transition-colors duration-150">
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-[#111827]">{event.name}</div>
                          {event.status === 'BLOCKED' && event.block_reason && (
                            <div className="text-xs text-[#ef4444] mt-1">{event.block_reason}</div>
                          )}
                        </td>
                        <td className="px-6 py-4 text-sm text-[#6b7280]">
                          {event.liquidity ? `${(event.liquidity / 1000).toFixed(1)}k` : '-'}
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium ${
                            (event.volatility || 0) < 0.001 ? 'bg-[#d1fae5] text-[#065f46]' :
                            (event.volatility || 0) < 0.0015 ? 'bg-[#fef3c7] text-[#92400e]' :
                            'bg-[#fee2e2] text-[#991b1b]'
                          }`}>
                            {(event.volatility || 0) < 0.001 ? 'Low' :
                             (event.volatility || 0) < 0.0015 ? 'Med' : 'High'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-[#6b7280]">{event.time_remaining || '-'}</td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium ${
                            event.status === 'ACTIVE' ? 'bg-[#d1fae5] text-[#065f46]' :
                            event.status === 'BLOCKED' ? 'bg-[#fee2e2] text-[#991b1b]' :
                            'bg-[#f3f4f6] text-[#374151]'
                          }`}>
                            {event.status}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={event.status === 'ACTIVE'}
                              onChange={async () => {
                                if (!user) return;
                                const api = initApiClient(createTokenGetter(user, stackApp));
                                try {
                                  if (event.status === 'ACTIVE') {
                                    await api.delete(`/strategies/${strategyId}/events/${event.id}`);
                                    setEvents(events.map(e => e.id === event.id ? { ...e, status: 'ELIGIBLE' as const } : e));
                                  } else {
                                    await api.post(`/strategies/${strategyId}/events/${event.id}`);
                                    setEvents(events.map(e => e.id === event.id ? { ...e, status: 'ACTIVE' as const } : e));
                                  }
                                } catch (err) {
                                  console.error('Error toggling event:', err);
                                  alert('Error al cambiar estado del evento');
                                }
                              }}
                              className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-[#e5e7eb] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#2563eb]"></div>
                          </label>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

