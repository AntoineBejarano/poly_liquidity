'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useDataMode } from '@/hooks/useDataMode';
import { toast } from '@/components/ui/sonner';
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

export default function StrategyDeskPage() {
  const params = useParams();
  const router = useRouter();
  const user = useUser();
  const stackApp = useStackApp();
  const strategyId = params.id as string;
  const isNew = strategyId === 'new';

  const { isDemo } = useDataMode();
  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [template, setTemplate] = useState<StrategyTemplate | null>(null);
  const [templateConfig, setTemplateConfig] = useState<Record<string, any>>({});
  const [events, setEvents] = useState<Event[]>([]);
  const [eventsLoadError, setEventsLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [strategyName, setStrategyName] = useState('');
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [initialCapital, setInitialCapital] = useState(10000);

  const [entryConditionsExpanded, setEntryConditionsExpanded] = useState(true);
  const [marketFiltersExpanded, setMarketFiltersExpanded] = useState(false);

  useEffect(() => {
    if (!user || !isNew) return;

    const loadTemplates = async () => {
      try {
        const api = initApiClient(createTokenGetter(user, stackApp));
        const data = await api.get<StrategyTemplate[]>('/strategy-templates');
        setTemplates(data ?? []);
        if (data && data.length > 0 && !selectedTemplateId) {
          setSelectedTemplateId(data[0].id);
        }
      } catch (err) {
        console.error('Error loading templates:', err);
      }
    };

    loadTemplates();
  }, [user, stackApp, isNew, selectedTemplateId]);

  useEffect(() => {
    if (!user || !isNew || !selectedTemplateId) return;

    const loadTemplateDetails = async () => {
      try {
        const api = initApiClient(createTokenGetter(user, stackApp));
        const templateDetails = await api.get<any>(`/strategy-templates/${selectedTemplateId}`);
        setTemplate(templateDetails);
        
        const defaultConfig: Record<string, any> = {};
        if (templateDetails.fields) {
          templateDetails.fields.forEach((field: any) => {
            if (field.default !== undefined) {
              defaultConfig[field.key] = field.default;
            }
          });
        }
        setTemplateConfig(defaultConfig);
      } catch (err) {
        console.error('Error loading template details:', err);
      }
    };

    loadTemplateDetails();
  }, [user, stackApp, isNew, selectedTemplateId]);

  useEffect(() => {
    if (!user || !strategyId || isNew) return;

    const loadStrategy = async () => {
      try {
        setLoading(true);
        const api = initApiClient(createTokenGetter(user, stackApp));
        const strategyData = await api.get<Strategy>(`/api/strategies/${strategyId}`);
        setStrategy(strategyData);
      } catch (err) {
        console.error('Error loading strategy:', err);
        setError('Error al cargar la estrategia');
      } finally {
        setLoading(false);
      }
    };

    loadStrategy();
  }, [user, stackApp, strategyId, isNew]);

  const MOCK_EVENTS: Event[] = [
    { id: '1', name: 'Bears vs Packers', market_id: 'm1', state: 'FINISHED', liquidity: 8200, volatility: 0.0005, time_remaining: 'Ended', status: 'ACTIVE' },
    { id: '2', name: 'Valencia vs Madrid', market_id: 'm2', state: 'FINISHED', liquidity: 6100, volatility: 0.001, time_remaining: 'Ended', status: 'ACTIVE' },
    { id: '3', name: 'Bitcoin 8:00–8:15', market_id: 'm3', state: 'ACTIVE', liquidity: 1100, volatility: 0.002, time_remaining: '+2m', status: 'BLOCKED', block_reason: 'Volatility too high' },
  ];

  useEffect(() => {
    if (!user || !strategy) return;

    if (isDemo) {
      setEvents(MOCK_EVENTS);
      setEventsLoadError(null);
      return;
    }

    const loadEvents = async () => {
      try {
        const api = initApiClient(createTokenGetter(user, stackApp));
        const strategyEventsResponse = await api.get<{ events: any[] }>(`/strategies/${strategyId}/events`);
        const eventsList = strategyEventsResponse?.events ?? [];
        const assignedEventIds = new Set(eventsList.map((e: any) => e.event_id));
        const allEvents = await api.get<any[]>('/markets/events/list?state=ACTIVE');
        const finishedEvents = await api.get<any[]>('/markets/events/list?state=FINISHED');
        const allAvailableEvents = [...(allEvents ?? []), ...(finishedEvents ?? [])];
        
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
        setEventsLoadError(null);
      } catch (err) {
        console.error('Error loading events:', err);
        setEvents([]);
        setEventsLoadError(err instanceof Error ? err.message : 'Error al cargar eventos');
      }
    };

    loadEvents();
  }, [user, stackApp, strategy, strategyId, isDemo]);

  if (!user) return null;

  const handleSave = async () => {
    if (!user || !strategyName.trim() || !selectedTemplateId) {
      setError('Nombre y tipo de estrategia son requeridos');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      const compiled = await api.post<{
        decision_graph: any;
        support_graphs: any[];
        risk_config: any;
      }>(`/strategy-templates/${selectedTemplateId}/compile`, templateConfig);
      
      if (!compiled) throw new Error('Compile failed');
      const newStrategy = await api.post<{ id: string }>('/api/strategies', {
        name: strategyName,
        description: template?.description,
        decision_graph: compiled.decision_graph,
        support_graphs: compiled.support_graphs,
        risk_config: {
          ...compiled.risk_config,
          max_exposure: initialCapital,
        },
      });

      if (newStrategy?.id) router.push(`/strategies/${newStrategy.id}/desk`);
    } catch (err) {
      console.error('Error creating strategy:', err);
      setError(err instanceof Error ? err.message : 'Error al crear estrategia');
    } finally {
      setLoading(false);
    }
  };

  if (loading && !isNew) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-full bg-background">
          <div className="text-sm text-muted-foreground">Cargando estrategia...</div>
        </div>
      </Layout>
    );
  }

  if (error && !isNew && !strategy) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-full bg-background">
          <div className="text-sm text-destructive">{error || 'Estrategia no encontrada'}</div>
        </div>
      </Layout>
    );
  }

  const eligibleCount = events.filter(e => e.status === 'ELIGIBLE' || e.status === 'ACTIVE').length;
  const activeCount = events.filter(e => e.status === 'ACTIVE').length;
  const blockedCount = events.filter(e => e.status === 'BLOCKED').length;

  return (
    <Layout>
      <div className="h-screen flex flex-col bg-background">
        {/* Header - compacto */}
        <div className="border-b border-border bg-card px-4 py-3 shrink-0">
          <div className="max-w-[1600px] mx-auto flex items-center justify-between">
            <div className="flex-1 min-w-0 flex items-center gap-2">
              {isDemo && !isNew && (
                <span className="shrink-0 inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-700">
                  Modo Demo
                </span>
              )}
              {isNew ? (
                <div className="space-y-0.5">
                  <input
                    type="text"
                    value={strategyName}
                    onChange={(e) => setStrategyName(e.target.value)}
                    placeholder="Nombre de la estrategia"
                    className="text-lg font-semibold text-foreground border-none outline-none bg-transparent placeholder-muted-foreground w-full"
                    autoFocus
                  />
                  <div className="text-xs text-muted-foreground">Nueva estrategia</div>
                </div>
              ) : strategy ? (
                <>
                  <h1 className="text-lg font-semibold text-foreground tracking-tight truncate">
                    {strategy.name}
                    {strategy.is_active && (
                      <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">
                        Active
                      </span>
                    )}
                  </h1>
                  <div className="mt-1 flex items-center gap-4 text-xs text-muted-foreground">
                    <Link
                      href={`/strategies/${strategyId}/universe`}
                      className="text-primary hover:underline"
                    >
                      Configurar Universe
                    </Link>
                    {isDemo ? (
                      <>
                        <span>Capital: <span className="font-medium text-foreground">42k / 50k</span></span>
                        <span>ROI 30d: <span className="font-medium text-emerald-600 dark:text-emerald-400">+3.2%</span></span>
                      </>
                    ) : (
                      <>
                        <span>Capital: <span className="font-medium text-foreground">—</span></span>
                        <span>ROI 30d: <span className="font-medium text-foreground">—</span></span>
                      </>
                    )}
                  </div>
                </>
              ) : null}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {isNew ? (
                <button
                  onClick={handleSave}
                  disabled={loading || !strategyName.trim() || !selectedTemplateId}
                  className="px-4 py-2 text-xs font-medium text-primary-foreground bg-primary rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? 'Guardando...' : 'Guardar Estrategia'}
                </button>
              ) : strategy ? (
                <button
                  onClick={async () => {
                    if (!user) return;
                    const api = initApiClient(createTokenGetter(user, stackApp));
                    try {
                      if (strategy.is_active) {
                        await api.post(`/api/strategies/${strategyId}/deactivate`);
                        setStrategy({ ...strategy, is_active: false });
                      } else {
                        await api.post(`/api/strategies/${strategyId}/activate`);
                        setStrategy({ ...strategy, is_active: true });
                      }
                    } catch (err) {
                      console.error('Error toggling strategy:', err);
                      toast.error(err instanceof Error ? err.message : 'Error al cambiar estado');
                    }
                  }}
                  className={`px-4 py-2 text-xs font-medium rounded-lg transition-colors ${
                    strategy.is_active
                      ? 'bg-destructive/15 text-destructive hover:bg-destructive/25'
                      : 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/25'
                  }`}
                >
                  {strategy.is_active ? 'Desactivar' : 'Activar'}
                </button>
              ) : null}
            </div>
          </div>
          {error && (
            <div className="mt-2 max-w-[1600px] mx-auto px-3 py-2 bg-destructive/10 border border-destructive/30 rounded-lg text-xs text-destructive">
              {error}
            </div>
          )}
        </div>

        {/* Main Content: izquierda sin scroll, derecha con scroll solo en tabla */}
        <div className="flex-1 flex min-h-0">
          {/* Left Panel - Configuración compacta, sin scroll */}
          <div className="w-80 border-r border-border bg-card shrink-0 overflow-hidden flex flex-col">
            <div className="p-3 space-y-2 overflow-hidden flex flex-col min-h-0">
              {/* Strategy Type */}
              <div className="bg-muted/30 border border-border rounded-lg p-3 shrink-0">
                <label className="block text-xs font-semibold text-muted-foreground mb-2 tracking-wide">
                  Strategy Type
                </label>
                {isNew ? (
                  <select
                    value={selectedTemplateId}
                    onChange={(e) => setSelectedTemplateId(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs text-foreground bg-background border border-border rounded focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  >
                    <option value="">Seleccionar tipo...</option>
                    {templates.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-medium text-foreground truncate">
                      {template?.name || 'Near-Resolution Liquidity'}
                    </span>
                    <button className="text-xs text-primary hover:underline shrink-0">Change type</button>
                  </div>
                )}
              </div>

              {/* Entry Conditions */}
              {template && template.fields && (
                <div className="bg-muted/30 border border-border rounded-lg overflow-hidden shrink-0">
                  <button
                    onClick={() => setEntryConditionsExpanded(!entryConditionsExpanded)}
                    className="w-full flex items-center justify-between px-3 py-2 hover:bg-muted/50 transition-colors text-left"
                  >
                    <span className="text-xs font-semibold text-foreground">Entry Conditions</span>
                    <span className="text-muted-foreground text-xs">{entryConditionsExpanded ? '▼' : '▶'}</span>
                  </button>
                  {entryConditionsExpanded && (
                    <div className="px-3 pb-3 pt-1 max-h-[40vh] overflow-y-auto">
                      <StrategyConfigForm
                        templateId={selectedTemplateId || template.id}
                        templateName={template.name}
                        templateDescription={template.description}
                        fields={((template?.fields ?? []) as any)}
                        initialValues={templateConfig}
                        onChange={setTemplateConfig}
                        compact
                      />
                    </div>
                  )}
                </div>
              )}

              {/* Risk Limits */}
              <div className="bg-muted/30 border border-border rounded-lg p-3 shrink-0">
                <label className="block text-xs font-semibold text-foreground mb-2">Risk Limits</label>
                <div className="space-y-2">
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Max per event</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={templateConfig.max_size_per_event || strategy?.risk_config?.max_order_size || 5000}
                        onChange={(e) => setTemplateConfig({ ...templateConfig, max_size_per_event: Number(e.target.value) })}
                        className="flex-1 px-2 py-1.5 text-xs text-foreground bg-background border border-border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                      <span className="text-xs text-muted-foreground">USDC</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Max total exposure</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={isNew ? initialCapital : (strategy?.risk_config?.max_exposure || 30000)}
                        onChange={(e) => isNew ? setInitialCapital(Number(e.target.value)) : setTemplateConfig({ ...templateConfig, max_exposure: Number(e.target.value) })}
                        className="flex-1 px-2 py-1.5 text-xs text-foreground bg-background border border-border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                      <span className="text-xs text-muted-foreground">USDC</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">If locked capital</label>
                    <div className="space-y-1">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input type="radio" name="locked_capital" defaultChecked className="w-3.5 h-3.5 text-primary border-border focus:ring-primary" />
                        <span className="text-xs text-foreground">Pause entries</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input type="radio" name="locked_capital" className="w-3.5 h-3.5 text-primary border-border focus:ring-primary" />
                        <span className="text-xs text-foreground">Continue</span>
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              {/* Market Filters */}
              <div className="bg-muted/30 border border-border rounded-lg overflow-hidden shrink-0">
                <button
                  onClick={() => setMarketFiltersExpanded(!marketFiltersExpanded)}
                  className="w-full flex items-center justify-between px-3 py-2 hover:bg-muted/50 transition-colors text-left"
                >
                  <span className="text-xs font-semibold text-foreground">Market Filters</span>
                  <span className="text-muted-foreground text-xs">{marketFiltersExpanded ? '▼' : '▶'}</span>
                </button>
                {marketFiltersExpanded && (
                  <div className="px-3 pb-3 pt-1 space-y-2">
                    <div>
                      <label className="block text-xs text-muted-foreground mb-1">Min liquidity</label>
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          defaultValue={2000}
                          className="flex-1 px-2 py-1.5 text-xs text-foreground bg-background border border-border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                        />
                        <span className="text-xs text-muted-foreground">USDC</span>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs text-muted-foreground mb-1">Max ST volatility</label>
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          step="0.0001"
                          defaultValue={0.0015}
                          className="flex-1 px-2 py-1.5 text-xs text-foreground bg-background border border-border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                        />
                        <span className="text-xs text-muted-foreground">/s</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Panel - Mercados: solo esta zona hace scroll */}
          <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-background">
            <div className="border-b border-border bg-card px-4 py-2 shrink-0">
              <div className="max-w-[1600px] mx-auto flex items-center justify-between">
                <div className="flex items-center gap-6">
                  <div className="text-xs text-muted-foreground">
                    Eligible: <span className="font-semibold text-foreground">{eligibleCount}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Active: <span className="font-semibold text-emerald-600 dark:text-emerald-400">{activeCount}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Blocked: <span className="font-semibold text-destructive">{blockedCount}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={async () => {
                      if (!user || isDemo) return;
                      const eligibleEvents = events.filter(e => e.status === 'ELIGIBLE');
                      const api = initApiClient(createTokenGetter(user, stackApp));
                      try {
                        for (const event of eligibleEvents) {
                          await api.post(`/api/strategies/${strategyId}/events/${event.id}`);
                        }
                        window.location.reload();
                      } catch (err) {
                        console.error('Error activating events:', err);
                        toast.error('Error al activar eventos');
                      }
                    }}
                    disabled={isDemo}
                    className="px-3 py-1.5 text-xs font-medium text-primary bg-primary/15 rounded hover:bg-primary/25 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Activate all eligible
                  </button>
                  <button
                    onClick={async () => {
                      if (!user || isDemo) return;
                      const api = initApiClient(createTokenGetter(user, stackApp));
                      try {
                        const strategyEvents = await api.get<{ events: any[] }>(`/strategies/${strategyId}/events`);
                        for (const se of (strategyEvents?.events ?? [])) {
                          await api.delete(`/api/strategies/${strategyId}/events/${se.event_id}`);
                        }
                        window.location.reload();
                      } catch (err) {
                        console.error('Error deactivating events:', err);
                        toast.error('Error al desactivar eventos');
                      }
                    }}
                    disabled={isDemo}
                    className="px-3 py-1.5 text-xs font-medium text-muted-foreground bg-muted rounded hover:bg-muted/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Deactivate all
                  </button>
                </div>
              </div>
            </div>

            {eventsLoadError && !isDemo && (
              <div className="px-4 py-2 bg-destructive/10 border-b border-destructive/30 text-destructive text-xs">
                {eventsLoadError}
              </div>
            )}

            <div className="flex-1 overflow-y-auto min-h-0">
              <div className="max-w-[1600px] mx-auto">
                <table className="w-full">
                  <thead className="bg-muted/50 sticky top-0 border-b border-border z-10">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Event</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Liq</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Vol</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Time</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Status</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Action</th>
                    </tr>
                  </thead>
                  <tbody className="bg-card divide-y divide-border">
                    {events.map((event) => (
                      <tr key={event.id} className="hover:bg-muted/30 transition-colors">
                        <td className="px-4 py-2">
                          <div className="text-xs font-medium text-foreground">{event.name}</div>
                          {event.status === 'BLOCKED' && event.block_reason && (
                            <div className="text-xs text-destructive mt-0.5">{event.block_reason}</div>
                          )}
                        </td>
                        <td className="px-4 py-2 text-xs text-muted-foreground">
                          {event.liquidity ? `${(event.liquidity / 1000).toFixed(1)}k` : '-'}
                        </td>
                        <td className="px-4 py-2">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            (event.volatility || 0) < 0.001 ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' :
                            (event.volatility || 0) < 0.0015 ? 'bg-amber-500/20 text-amber-600 dark:text-amber-400' :
                            'bg-destructive/20 text-destructive'
                          }`}>
                            {(event.volatility || 0) < 0.001 ? 'Low' :
                             (event.volatility || 0) < 0.0015 ? 'Med' : 'High'}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-xs text-muted-foreground">{event.time_remaining || '-'}</td>
                        <td className="px-4 py-2">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            event.status === 'ACTIVE' ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' :
                            event.status === 'BLOCKED' ? 'bg-destructive/20 text-destructive' :
                            'bg-muted text-muted-foreground'
                          }`}>
                            {event.status}
                          </span>
                        </td>
                        <td className="px-4 py-2">
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={event.status === 'ACTIVE'}
                              disabled={isDemo}
                              onChange={async () => {
                                if (!user || isDemo) return;
                                const api = initApiClient(createTokenGetter(user, stackApp));
                                try {
                                  if (event.status === 'ACTIVE') {
                                    await api.delete(`/api/strategies/${strategyId}/events/${event.id}`);
                                    setEvents(events.map(e => e.id === event.id ? { ...e, status: 'ELIGIBLE' as const } : e));
                                  } else {
                                    await api.post(`/api/strategies/${strategyId}/events/${event.id}`);
                                    setEvents(events.map(e => e.id === event.id ? { ...e, status: 'ACTIVE' as const } : e));
                                  }
                                } catch (err) {
                                  console.error('Error toggling event:', err);
                                  toast.error('Error al cambiar estado del evento');
                                }
                              }}
                              className="sr-only peer"
                            />
                            <div className="w-9 h-5 bg-muted-foreground/30 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-background after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
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
