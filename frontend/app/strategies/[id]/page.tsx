'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { useUser, useStackApp } from '@stackframe/stack';
import { useParams, useRouter } from 'next/navigation';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import Link from 'next/link';
import { Strategy, GraphExecution, ExecutionIntent, StrategyMetric, GraphNodeDefinition, SupportGraph, DecisionGraph } from '@/types/strategy';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Save, ExternalLink, GitBranch, Calendar, MessageCircle } from 'lucide-react';
import { toast } from '@/components/ui/sonner';
import { StrategyConfigForm, type TemplateField } from '@/components/StrategyConfigForm';
import { StrategyDataFlowDiagram } from '@/components/strategy/StrategyDataFlowDiagram';

// Lazy load GraphBuilder (heavy component with ReactFlow)
const GraphBuilder = dynamic(
  () => import('@/components/GraphBuilder/GraphBuilder').then(mod => ({ default: mod.GraphBuilder })),
  {
    loading: () => (
      <div className="w-full h-[600px] border border-border rounded-lg p-4">
        <Skeleton className="w-full h-full" />
      </div>
    ),
    ssr: false,
  }
);

/** True si la estrategia es Telegram Tipster (usa listener Telegram). */
function isTelegramTipsterStrategy(s: Strategy | null): boolean {
  if (!s?.support_graphs?.length) return false;
  return (s.support_graphs as Array<{ name?: string }>).some(
    (g) => g?.name === 'telegram_listener'
  );
}

/** Editor de filtros por canal (include/exclude regex, max tips/día). */
function ChannelFiltersEditor({
  channels,
  chatFilters,
  perChannelLimits,
  onChange,
}: {
  channels: string[];
  chatFilters: Record<string, { include_regex?: string; exclude_regex?: string }>;
  perChannelLimits: Record<string, { max_tips_per_day?: number }>;
  onChange: (chatFilters: Record<string, { include_regex?: string; exclude_regex?: string }>, perChannelLimits: Record<string, { max_tips_per_day?: number }>) => void;
}) {
  const updateChatFilter = (chatId: string, key: 'include_regex' | 'exclude_regex', value: string) => {
    const next = { ...chatFilters };
    if (!next[chatId]) next[chatId] = {};
    next[chatId] = { ...next[chatId], [key]: value || undefined };
    if (!next[chatId].include_regex && !next[chatId].exclude_regex) delete next[chatId];
    onChange(next, perChannelLimits);
  };
  const updatePerChannelLimit = (chatId: string, maxTipsPerDay: number | '') => {
    const next = { ...perChannelLimits };
    const n = maxTipsPerDay === '' ? undefined : Number(maxTipsPerDay);
    if (n != null && n > 0) next[chatId] = { max_tips_per_day: n };
    else delete next[chatId];
    onChange(chatFilters, next);
  };
  return (
    <div className="space-y-3">
      <Label className="text-sm font-medium">Filtros por canal</Label>
      <p className="text-xs text-muted-foreground">
        Include: solo mensajes que coincidan con el regex. Exclude: excluir los que coincidan. Límite: máx tips/día por canal.
      </p>
      <Accordion type="multiple" className="space-y-1">
        {channels.map((chatId) => (
          <AccordionItem key={chatId} value={chatId} className="border rounded-lg px-3 py-2">
            <AccordionTrigger className="text-sm py-2 hover:no-underline">
              Canal {chatId}
            </AccordionTrigger>
            <AccordionContent className="space-y-2 pt-2">
              <div>
                <Label className="text-xs">Include regex (solo si coincide)</Label>
                <Input
                  placeholder="Ej: #pick|@tipster"
                  value={chatFilters[chatId]?.include_regex ?? ''}
                  onChange={(e) => updateChatFilter(chatId, 'include_regex', e.target.value)}
                  className="mt-1 text-sm"
                />
              </div>
              <div>
                <Label className="text-xs">Exclude regex</Label>
                <Input
                  placeholder="Ej: free|promo"
                  value={chatFilters[chatId]?.exclude_regex ?? ''}
                  onChange={(e) => updateChatFilter(chatId, 'exclude_regex', e.target.value)}
                  className="mt-1 text-sm"
                />
              </div>
              <div>
                <Label className="text-xs">Máx tips por día (por canal)</Label>
                <Input
                  type="number"
                  min={0}
                  placeholder="Ilimitado"
                  value={perChannelLimits[chatId]?.max_tips_per_day ?? ''}
                  onChange={(e) => updatePerChannelLimit(chatId, e.target.value === '' ? '' : Number(e.target.value))}
                  className="mt-1 text-sm max-w-[120px]"
                />
              </div>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}

/** Nombres legibles de los support graphs (para mostrar en UI). */
function getSupportGraphLabels(s: Strategy | null): string[] {
  if (!s?.support_graphs?.length) return [];
  return (s.support_graphs as Array<{ name?: string }>)
    .map((g) => g?.name || '')
    .filter(Boolean);
}

/** Extrae config del template Telegram Tipster desde support_graphs, execution_graph y risk_config. */
function extractTelegramTipsterConfig(s: Strategy | null): Record<string, unknown> {
  if (!s) return {};
  const rc = s.risk_config ?? {};
  const out: Record<string, unknown> = {
    max_stake_per_tip: rc.max_stake_per_tip ?? 50,
    max_daily_stake: rc.max_daily_stake ?? 300,
    execution_mode: rc.execution_mode ?? 'confirm_before',
    tipster_whitelist_regex: Array.isArray(rc.tipster_whitelist_regex) ? rc.tipster_whitelist_regex.join(', ') : '',
    tipster_blacklist_regex: Array.isArray(rc.tipster_blacklist_regex) ? rc.tipster_blacklist_regex.join(', ') : '',
    sport_filters: Array.isArray(rc.sport_filters) ? rc.sport_filters.join(', ') : '',
    chat_filters: rc.chat_filters ?? {},
    per_channel_limits: rc.per_channel_limits ?? {},
  };
  const getSourceId = (g: { nodes?: Record<string, { type?: string; config?: { source_id?: string } }> }) => {
    for (const node of Object.values(g.nodes ?? {})) {
      const sid = node?.config?.source_id;
      if (sid) return sid;
    }
    return null;
  };
  for (const g of (s.support_graphs as Array<{ name?: string; nodes?: Record<string, unknown> }>) ?? []) {
    const sid = getSourceId(g as { nodes?: Record<string, { config?: { source_id?: string } }> });
    if (!sid) continue;
    if (g.name === 'telegram_listener') out.telegram_source_id = sid;
    if (g.name === 'fetch_ps3838_fixtures') out.ps3838_source_id = sid;
  }
  const eg = (s as { execution_graph?: { nodes?: Record<string, { config?: { source_id?: string } }> } }).execution_graph;
  if (!out.ps3838_source_id && eg?.nodes) {
    for (const node of Object.values(eg.nodes)) {
      const sid = node?.config?.source_id;
      if (sid) { out.ps3838_source_id = sid; break; }
    }
  }
  return out;
}

export default function StrategyDetailPage() {
  return <StrategyDetailPageOld />;
}

function StrategyDetailPageOld() {
  const user = useUser();
  const stackApp = useStackApp();
  const params = useParams();
  const router = useRouter();
  const { isConnected } = useBackendConnection();

  const strategyId = params.id as string;
  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [executions, setExecutions] = useState<GraphExecution[]>([]);
  const [intents, setIntents] = useState<ExecutionIntent[]>([]);
  const [metrics, setMetrics] = useState<StrategyMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'config' | 'graph' | 'executions' | 'intents' | 'metrics'>('config');
  const [activating, setActivating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editMaxExposure, setEditMaxExposure] = useState('');
  const [editTags, setEditTags] = useState('');
  const [editCategories, setEditCategories] = useState('');
  const [editMarkets, setEditMarkets] = useState('');
  const [editAutoAttach, setEditAutoAttach] = useState(true);
  const [editDenyList, setEditDenyList] = useState('');
  const [editMaxBookStalenessMs, setEditMaxBookStalenessMs] = useState(2000);
  const [editMaxSpreadBps, setEditMaxSpreadBps] = useState(200);
  const [editMinDepthUsdc, setEditMinDepthUsdc] = useState(2000);
  const [editMaxImpactBps, setEditMaxImpactBps] = useState(50);
  const [editMinSecondsSinceFinished, setEditMinSecondsSinceFinished] = useState(60);
  const [editMaxSecondsSinceFinished, setEditMaxSecondsSinceFinished] = useState(1800);
  const [editOrderUsdc, setEditOrderUsdc] = useState(1000);
  const [editCapacitySizingEnabled, setEditCapacitySizingEnabled] = useState(true);
  const [editOrderMode, setEditOrderMode] = useState<'IOC' | 'POST_ONLY'>('IOC');
  const [editTtlMs, setEditTtlMs] = useState(5000);
  const [editDriftBpsLimit, setEditDriftBpsLimit] = useState(20);
  const [editTickSize, setEditTickSize] = useState(0.001);
  const [editImproveTicks, setEditImproveTicks] = useState(1);
  const [editWalletId, setEditWalletId] = useState<string | null>(null);
  const [editProxyId, setEditProxyId] = useState<string | null>(null);
  const [wallets, setWallets] = useState<Array<{ id: string; label: string; address: string; active: boolean }>>([]);
  const [proxies, setProxies] = useState<Array<{ id: string; name: string; proxy_type: string; proxy_host: string; proxy_port: number; validation_status?: string; validation_latency_ms?: number }>>([]);
  const [externalDataSources, setExternalDataSources] = useState<Array<{ id: string; name: string; connector_type: string; config?: { monitored_chats?: string[]; chat_filters?: Record<string, unknown> } }>>([]);
  const [telegramTipsterTemplate, setTelegramTipsterTemplate] = useState<{ id: string; name: string; fields?: TemplateField[] } | null>(null);
  const [templateConfig, setTemplateConfig] = useState<Record<string, unknown>>({});

  // Cargar definiciones de nodos
  const loadNodeDefinitions = async () => {
    if (!user) return [];
    const api = initApiClient(createTokenGetter(user, stackApp));
    try {
      const data = await api.get<GraphNodeDefinition[]>('/graph-nodes?path_type=hot');
      const coldData = await api.get<GraphNodeDefinition[]>('/graph-nodes?path_type=cold');
      return [...(data ?? []), ...(coldData ?? [])];
    } catch (err) {
      console.error('Error loading node definitions:', err);
      return [];
    }
  };

  useEffect(() => {
    if (!user || !isConnected || !strategyId) return;

    const api = initApiClient(createTokenGetter(user, stackApp));

    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [strategyData, executionsRes, intentsRes, metricsRes, walletsData, proxiesData, sourcesData] = await Promise.all([
          api.get<Strategy>(`/api/strategies/${strategyId}`),
          api.get<{ executions?: GraphExecution[] } | GraphExecution[]>(`/api/strategies/${strategyId}/executions?limit=50`).catch(() => ({ executions: [] })),
          api.get<{ intents?: ExecutionIntent[] } | ExecutionIntent[]>(`/api/strategies/${strategyId}/intents?limit=50`).catch(() => ({ intents: [] })),
          api.get<{ metrics?: StrategyMetric[] } | StrategyMetric[]>(`/api/strategies/${strategyId}/metrics`).catch(() => ({ metrics: [] })),
          api.get<Array<{ id: string; label: string; address: string; active: boolean }>>('/wallets').catch(() => []),
          api.get<Array<{ id: string; name: string; proxy_type: string; proxy_host: string; proxy_port: number; validation_status?: string; validation_latency_ms?: number }>>('/proxies').catch(() => []),
          api.get<Array<{ id: string; name: string; connector_type: string; config?: Record<string, unknown> }>>('/external-data-sources?is_active=true').catch(() => []),
        ]);

        const executionsList = Array.isArray(executionsRes) ? executionsRes : (executionsRes?.executions ?? []);
        const intentsList = Array.isArray(intentsRes) ? intentsRes : (intentsRes?.intents ?? []);
        const metricsList = Array.isArray(metricsRes) ? metricsRes : (metricsRes?.metrics ?? []);

        setStrategy(strategyData);
        setExecutions(executionsList);
        setIntents(intentsList);
        setMetrics(metricsList);
        setWallets(Array.isArray(walletsData) ? walletsData : []);
        setProxies(Array.isArray(proxiesData) ? proxiesData : []);
        setExternalDataSources(Array.isArray(sourcesData) ? sourcesData : []);

        if (strategyData && (strategyData.support_graphs as Array<{ name?: string }>)?.some((g) => g?.name === 'telegram_listener')) {
          api.get<{ id: string; name: string; fields?: TemplateField[] }>(`/strategy-templates/telegram_tipster_ps3838`).then(setTelegramTipsterTemplate).catch(() => {});
        }
      } catch (err) {
        console.error('Error fetching strategy:', err);
        setError(err instanceof Error ? err.message : 'Error al cargar estrategia');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user, stackApp, isConnected, strategyId]);

  const strategyExecutionGraph = (strategy as { execution_graph?: unknown })?.execution_graph;
  useEffect(() => {
    if (!strategy || !isTelegramTipsterStrategy(strategy)) return;
    setTemplateConfig(extractTelegramTipsterConfig(strategy));
  }, [strategy, strategyExecutionGraph]);

  useEffect(() => {
    if (!strategy) return;
    const rc = strategy.risk_config ?? {};
    const uc = (strategy as any).universe_config ?? {};
    const cc = (strategy as any).control_loop_config ?? {};
    setEditName(strategy.name ?? '');
    setEditDescription(strategy.description ?? '');
    setEditMaxExposure(String(rc.max_exposure ?? 5000));
    setEditTags((strategy.tags ?? []).join(', '));
    setEditCategories((uc.categories ?? []).join(', '));
    setEditMarkets((uc.markets ?? []).join(', '));
    setEditAutoAttach(uc.auto_attach ?? true);
    setEditDenyList((uc.deny_list ?? []).join(', '));
    setEditMaxBookStalenessMs(cc.max_book_staleness_ms ?? 2000);
    setEditMaxSpreadBps(cc.max_spread_bps ?? 200);
    setEditMinDepthUsdc(cc.min_depth_usdc_at_50bps ?? rc.min_liquidity ?? 2000);
    setEditMaxImpactBps(cc.max_impact_bps ?? 50);
    setEditMinSecondsSinceFinished(cc.min_seconds_since_finished ?? 60);
    setEditMaxSecondsSinceFinished(cc.max_seconds_since_finished ?? 1800);
    setEditOrderUsdc(cc.order_usdc ?? rc.order_usdc ?? 1000);
    setEditCapacitySizingEnabled(cc.capacity_sizing_enabled ?? true);
    setEditOrderMode((cc.order_mode ?? 'IOC') as 'IOC' | 'POST_ONLY');
    setEditTtlMs(cc.ttl_ms ?? 5000);
    setEditDriftBpsLimit(cc.drift_bps_limit ?? 20);
    setEditTickSize(cc.tick_size ?? 0.001);
    setEditImproveTicks(cc.improve_ticks ?? 1);
    setEditWalletId(strategy.wallet_id ?? null);
    setEditProxyId(strategy.proxy_id ?? null);
  }, [strategy]);

  const handleSave = async () => {
    if (!user || !stackApp || !strategy) return;
    setSaving(true);
    setSaveError(null);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      const tagsList = editTags.split(',').map((t) => t.trim()).filter(Boolean);
      const categoriesList = editCategories.split(',').map((c) => c.trim()).filter(Boolean);
      const marketsList = editMarkets.split(',').map((m) => m.trim()).filter(Boolean);
      const denyList = editDenyList.split(',').map((d) => d.trim()).filter(Boolean);

      let riskCfg = { ...strategy.risk_config, max_exposure: Number(editMaxExposure) || 5000, order_usdc: Number(editOrderUsdc) || 1000, min_liquidity: Number(editMinDepthUsdc) || 2000 };
      let supportGraphs = strategy.support_graphs;
      let decisionGraph = strategy.decision_graph;
      let executionGraph = (strategy as { execution_graph?: unknown }).execution_graph;

      if (isTelegramTipsterStrategy(strategy) && templateConfig.telegram_source_id && templateConfig.ps3838_source_id) {
        const compiled = await api.post<{ decision_graph: DecisionGraph; support_graphs: SupportGraph[]; execution_graph?: unknown; risk_config: Record<string, unknown> }>(
          '/strategy-templates/telegram_tipster_ps3838/compile',
          {
            ps3838_source_id: templateConfig.ps3838_source_id,
            telegram_source_id: templateConfig.telegram_source_id,
            max_stake_per_tip: Number(templateConfig.max_stake_per_tip) || 50,
            max_daily_stake: Number(templateConfig.max_daily_stake) || 300,
            execution_mode: templateConfig.execution_mode || 'confirm_before',
            tipster_whitelist_regex: typeof templateConfig.tipster_whitelist_regex === 'string' ? templateConfig.tipster_whitelist_regex : '',
            tipster_blacklist_regex: typeof templateConfig.tipster_blacklist_regex === 'string' ? templateConfig.tipster_blacklist_regex : '',
            sport_filters: typeof templateConfig.sport_filters === 'string' ? templateConfig.sport_filters : '',
            chat_filters: templateConfig.chat_filters ?? {},
            per_channel_limits: templateConfig.per_channel_limits ?? {},
          }
        );
        if (!compiled) throw new Error('La compilación del template falló');
        supportGraphs = compiled.support_graphs;
        decisionGraph = compiled.decision_graph;
        executionGraph = compiled.execution_graph;
        riskCfg = { ...riskCfg, ...compiled.risk_config };
      }

      const updated = await api.put<Strategy>(`/api/strategies/${strategyId}`, {
        name: editName || undefined,
        description: editDescription || undefined,
        wallet_id: editWalletId,
        proxy_id: editProxyId,
        decision_graph: decisionGraph,
        support_graphs: supportGraphs,
        execution_graph: executionGraph,
        risk_config: riskCfg,
        control_loop_config: {
          ...(strategy as any).control_loop_config,
          max_book_staleness_ms: Number(editMaxBookStalenessMs) || 2000,
          max_spread_bps: Number(editMaxSpreadBps) || 200,
          min_depth_usdc_at_50bps: Number(editMinDepthUsdc) || 2000,
          max_impact_bps: Number(editMaxImpactBps) || 50,
          min_seconds_since_finished: Number(editMinSecondsSinceFinished) || 60,
          max_seconds_since_finished: Number(editMaxSecondsSinceFinished) || 1800,
          order_usdc: Number(editOrderUsdc) || 1000,
          capacity_sizing_enabled: editCapacitySizingEnabled,
          order_mode: editOrderMode,
          ttl_ms: Number(editTtlMs) || 5000,
          drift_bps_limit: Number(editDriftBpsLimit) || 20,
          tick_size: Number(editTickSize) || 0.001,
          improve_ticks: Number(editImproveTicks) ?? 1,
        },
        universe_config: {
          categories: categoriesList,
          markets: marketsList,
          tags: [],
          auto_attach: editAutoAttach,
          deny_list: denyList,
        },
        tags: tagsList,
      });
      setStrategy(updated);
      toast.success('Cambios guardados');
    } catch (err) {
      console.error('Error saving strategy:', err);
      setSaveError(err instanceof Error ? err.message : 'Error al guardar');
      toast.error(err instanceof Error ? err.message : 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  const handleActivate = async () => {
    if (!strategy) return;

    setActivating(true);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.post(`/api/strategies/${strategyId}/activate`);
      setStrategy({ ...strategy, is_active: true });
    } catch (err) {
      console.error('Error activating strategy:', err);
      toast.error(err instanceof Error ? err.message : 'Error al activar estrategia');
    } finally {
      setActivating(false);
    }
  };

  const handleDeactivate = async () => {
    if (!strategy) return;

    setActivating(true);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.post(`/api/strategies/${strategyId}/deactivate`);
      setStrategy({ ...strategy, is_active: false });
    } catch (err) {
      console.error('Error deactivating strategy:', err);
      toast.error(err instanceof Error ? err.message : 'Error al desactivar estrategia');
    } finally {
      setActivating(false);
    }
  };

  // Mientras carga o faltan datos para pedir (user, conexión), mostrar spinner — no "no encontrada"
  if (!user || loading) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center min-h-[200px] gap-3">
          <LoadingSpinner />
          <p className="text-sm text-muted-foreground">Cargando estrategia…</p>
        </div>
      </Layout>
    );
  }

  // Solo después de terminar de cargar: error o estrategia inexistente
  if (error || !strategy) {
    return (
      <Layout>
        <div className="p-4 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-200">{error || 'Estrategia no encontrada'}</p>
          <Link href="/strategies" className="mt-2 inline-block text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400">
            Volver a Estrategias
          </Link>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Link href="/strategies" className="text-sm text-muted-foreground hover:text-foreground">
                ← My Strategies
              </Link>
            </div>
            <h1 className="text-2xl font-bold text-foreground mt-2">{strategy.name}</h1>
            {strategy.description && (
              <p className="text-sm text-muted-foreground mt-1">{strategy.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Link
              href={`/strategies/${strategyId}/tips`}
              className="px-4 py-2 text-sm font-medium border border-border rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              Tips
            </Link>
            <Link
              href={`/strategies/${strategyId}/live`}
              className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground border border-primary rounded-lg hover:bg-primary/90 hover:text-primary-foreground transition-colors"
            >
              Control en vivo
            </Link>
            {strategy.is_active ? (
              <button
                onClick={handleDeactivate}
                disabled={activating}
                className="px-4 py-2 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 disabled:opacity-50 transition-colors"
              >
                {activating ? 'Desactivando...' : 'Desactivar'}
              </button>
            ) : (
              <button
                onClick={handleActivate}
                disabled={activating}
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                {activating ? 'Activando...' : 'Activar'}
              </button>
            )}
          </div>
        </div>

        {/* Tabs: Config (universo/mercados primero), luego Live = observabilidad, Histórico = intentos/ejecuciones */}
        <div className="border-b border-border">
          <nav className="flex gap-4 flex-wrap">
            {(['config', 'graph', 'executions', 'intents', 'metrics'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                {tab === 'config' && (isTelegramTipsterStrategy(strategy) ? 'Configuración' : 'Configuración (universo y mercados)')}
                {tab === 'graph' && 'Grafos'}
                {tab === 'executions' && 'Histórico: Ejecuciones'}
                {tab === 'intents' && 'Histórico: Intents'}
                {tab === 'metrics' && 'Histórico: Métricas'}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Configuración */}
        {activeTab === 'config' && (
          <div className="space-y-6">
            <p className="text-sm text-muted-foreground">
              {isTelegramTipsterStrategy(strategy)
                ? 'Configura cuentas Telegram y PS3838, canales a monitorear, stake, riesgo y modo de ejecución.'
                : <>Lo más importante: definir el <strong>universo</strong> y qué <strong>mercados activar o excluir</strong>. Luego el resto de parámetros.</>}
            </p>
            <Accordion type="multiple" defaultValue={isTelegramTipsterStrategy(strategy) ? ['telegram-tipster', 'universe', 'account', 'proxies', 'identity', 'orderbook', 'timing', 'sizing', 'execution', 'risk'] : ['universe', 'account', 'proxies', 'identity', 'orderbook', 'timing', 'sizing', 'execution', 'risk']} className="space-y-2">
              {isTelegramTipsterStrategy(strategy) && telegramTipsterTemplate && (
              <AccordionItem value="telegram-tipster" className="border rounded-lg border-primary/30 bg-primary/5">
                <AccordionTrigger className="px-4 py-3 text-sm font-semibold flex items-center gap-2">
                  <MessageCircle className="h-4 w-4" />
                  Configuración Telegram Tipster (cuentas, canales, riesgo)
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 space-y-4">
                  {(templateConfig.max_stake_per_tip !== undefined || templateConfig.telegram_source_id) ? (
                    <StrategyConfigForm
                      templateId={telegramTipsterTemplate.id}
                      templateName={telegramTipsterTemplate.name}
                      templateDescription=""
                      fields={telegramTipsterTemplate.fields ?? []}
                      initialValues={templateConfig}
                      onChange={setTemplateConfig}
                      compact={false}
                    />
                  ) : (
                    <p className="text-sm text-muted-foreground py-2">Cargando configuración…</p>
                  )}
                  {!!templateConfig.telegram_source_id && (
                    <div className="border-t border-border pt-4 space-y-2">
                      <Label className="text-sm font-medium">Canales/grupos de Telegram monitoreados</Label>
                      <p className="text-xs text-muted-foreground">
                        Los canales se configuran en la conexión Telegram. Selecciona la cuenta arriba y gestiona canales en:
                      </p>
                      <Button variant="outline" size="sm" asChild>
                        <Link href="/settings/accounts">
                          <MessageCircle className="h-3.5 w-3.5 mr-1.5" />
                          Cuentas → Conexiones Telegram
                          <ExternalLink className="h-3.5 w-3.5 ml-1.5" />
                        </Link>
                      </Button>
                      {(() => {
                        const src = externalDataSources.find((s) => s.id === String(templateConfig.telegram_source_id));
                        const chats = (src?.config?.monitored_chats ?? []) as string[];
                        if (chats.length > 0) {
                          return (
                            <div className="mt-2 space-y-3">
                              <div className="p-3 rounded-lg bg-muted/50 text-sm">
                                <span className="font-medium">{chats.length} canal(es):</span>{' '}
                                {chats.slice(0, 5).join(', ')}
                                {chats.length > 5 && ` +${chats.length - 5} más`}
                              </div>
                              <ChannelFiltersEditor
                                channels={chats}
                                chatFilters={(templateConfig.chat_filters ?? {}) as Record<string, { include_regex?: string; exclude_regex?: string }>}
                                perChannelLimits={(templateConfig.per_channel_limits ?? {}) as Record<string, { max_tips_per_day?: number }>}
                                onChange={(chatFilters, perChannelLimits) => setTemplateConfig((prev) => ({ ...prev, chat_filters: chatFilters, per_channel_limits: perChannelLimits }))}
                              />
                            </div>
                          );
                        }
                        return (
                          <p className="text-sm text-amber-600 dark:text-amber-500">Sin canales configurados. Añade grupos en Cuentas.</p>
                        );
                      })()}
                    </div>
                  )}
                </AccordionContent>
              </AccordionItem>
              )}

              {!isTelegramTipsterStrategy(strategy) && (
              <AccordionItem value="universe" className="border rounded-lg border-primary/30 bg-primary/5">
                <AccordionTrigger className="px-4 py-3 text-sm font-semibold">
                  Universe y mercados (qué activar y qué no)
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 space-y-3">
                  <p className="text-sm text-muted-foreground mb-2">
                    Para explorar y asignar eventos desde el directorio (recomendado):
                  </p>
                  <Button variant="default" size="sm" asChild>
                    <Link href={`/strategies/${strategyId}/universe`}>
                      Configurar Universe
                      <ExternalLink className="h-3.5 w-3.5 ml-1.5" />
                    </Link>
                  </Button>
                  <div className="border-t border-border pt-3 mt-3 space-y-2">
                    <Label className="text-muted-foreground">O editar a mano (avanzado)</Label>
                    <div className="space-y-2">
                      <Label>Categorías (separadas por coma)</Label>
                      <Input value={editCategories} onChange={(e) => setEditCategories(e.target.value)} placeholder="Sports, Crypto, Politics" className="max-w-md" />
                    </div>
                    <div className="space-y-2">
                      <Label>Markets (IDs separados por coma)</Label>
                      <Input value={editMarkets} onChange={(e) => setEditMarkets(e.target.value)} placeholder="market-id-1, market-id-2" className="max-w-md" />
                    </div>
                    <div className="space-y-2">
                      <Label>Deny list (excluir)</Label>
                      <Input value={editDenyList} onChange={(e) => setEditDenyList(e.target.value)} placeholder="id1, id2" className="max-w-md" />
                    </div>
                    <label className="flex items-center gap-2">
                      <input type="checkbox" checked={editAutoAttach} onChange={(e) => setEditAutoAttach(e.target.checked)} className="w-4 h-4" />
                      <span className="text-sm">Auto-attach nuevos eventos</span>
                    </label>
                  </div>
                </AccordionContent>
              </AccordionItem>
              )}

              {!isTelegramTipsterStrategy(strategy) && (
              <AccordionItem value="account" className="border rounded-lg border-primary/30 bg-primary/5">
                <AccordionTrigger className="px-4 py-3 text-sm font-semibold">
                  Cuenta asociada (wallet)
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 space-y-3">
                  {strategy.is_active ? (
                    <div className="rounded-lg bg-muted/50 border border-border p-3 text-sm text-muted-foreground">
                      La estrategia está activa. Detén la estrategia para poder cambiar la cuenta asociada.
                      {editWalletId && wallets.find((w) => w.id === editWalletId) && (
                        <p className="mt-2 font-medium text-foreground">
                          Cuenta actual: <span className="font-mono">{wallets.find((w) => w.id === editWalletId)!.label}</span>
                        </p>
                      )}
                      {!editWalletId && (
                        <p className="mt-2 font-medium text-foreground">
                          Cuenta actual: cuenta activa del usuario
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Label>Cuenta para ejecutar esta estrategia</Label>
                      <Select
                        value={editWalletId ?? 'active'}
                        onValueChange={(v) => setEditWalletId(v === 'active' ? null : v)}
                      >
                        <SelectTrigger className="max-w-md">
                          <SelectValue placeholder="Seleccionar cuenta por alias" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="active">Usar cuenta activa del usuario</SelectItem>
                          {wallets.map((w) => (
                            <SelectItem key={w.id} value={w.id}>
                              {w.label || w.address}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground">
                        Si no asignas una cuenta, se usará la cuenta activa. Gestiona cuentas en{' '}
                        <Link href="/settings/wallets" className="text-primary hover:underline">Wallets</Link>.
                      </p>
                    </div>
                  )}
                </AccordionContent>
              </AccordionItem>
              )}

              <AccordionItem value="proxies" className="border rounded-lg border-primary/30 bg-primary/5">
                <AccordionTrigger className="px-4 py-3 text-sm font-semibold">
                  Proxies (routing)
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 space-y-3">
                  <div className="space-y-2">
                    <Label>Proxy (todas las conexiones)</Label>
                    <Select
                      value={editProxyId ?? 'none'}
                      onValueChange={(v) => setEditProxyId(v === 'none' ? null : v)}
                    >
                      <SelectTrigger className="max-w-md">
                        <SelectValue placeholder="Sin proxy (usar cloud)" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Sin proxy (usar cloud)</SelectItem>
                        {proxies.map((p) => (
                          <SelectItem key={p.id} value={p.id}>
                            {p.name} — {p.validation_status ?? 'unknown'} — {p.validation_latency_ms != null ? `${p.validation_latency_ms}ms` : '—'}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      Gestiona proxies en{' '}
                      <Link href="/settings/proxies" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                        Proxies
                      </Link>
                    </p>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {!isTelegramTipsterStrategy(strategy) && (
              <AccordionItem value="identity" className="border rounded-lg">
                <AccordionTrigger className="px-4 py-3 text-sm font-medium">
                  Datos básicos (nombre, descripción, tags)
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 space-y-3">
                  <div className="space-y-2">
                    <Label htmlFor="name">Nombre</Label>
                    <Input id="name" value={editName} onChange={(e) => setEditName(e.target.value)} placeholder="Nombre de la estrategia" className="max-w-md" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="description">Descripción</Label>
                    <Input id="description" value={editDescription} onChange={(e) => setEditDescription(e.target.value)} placeholder="Descripción opcional" className="max-w-md" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="tags">Tags (separados por coma)</Label>
                    <Input id="tags" value={editTags} onChange={(e) => setEditTags(e.target.value)} placeholder="liquidity, near-resolution" className="max-w-md" />
                  </div>
                </AccordionContent>
              </AccordionItem>
              )}

              {!isTelegramTipsterStrategy(strategy) && (
              <AccordionItem value="orderbook" className="border rounded-lg">
                <AccordionTrigger className="px-4 py-3 text-sm font-medium">
                  Orderbook (liquidez y spread)
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 grid gap-3 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Book freshness (ms)</Label>
                    <Input type="number" value={editMaxBookStalenessMs} onChange={(e) => setEditMaxBookStalenessMs(Number(e.target.value))} placeholder="2000" />
                  </div>
                  <div className="space-y-2">
                    <Label>Max spread (bps)</Label>
                    <Input type="number" value={editMaxSpreadBps} onChange={(e) => setEditMaxSpreadBps(Number(e.target.value))} placeholder="200" />
                  </div>
                  <div className="space-y-2">
                    <Label>Min liquidez (USDC)</Label>
                    <Input type="number" value={editMinDepthUsdc} onChange={(e) => setEditMinDepthUsdc(Number(e.target.value))} placeholder="2000" />
                  </div>
                  <div className="space-y-2">
                    <Label>Max price impact (bps)</Label>
                    <Input type="number" value={editMaxImpactBps} onChange={(e) => setEditMaxImpactBps(Number(e.target.value))} placeholder="50" />
                  </div>
                </AccordionContent>
              </AccordionItem>
              )}

              <AccordionItem value="timing" className="border rounded-lg">
                <AccordionTrigger className="px-4 py-3 text-sm font-medium">
                  Timing (ventana de entrada)
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 grid gap-3 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Esperar después de fin (seg)</Label>
                    <Input type="number" value={editMinSecondsSinceFinished} onChange={(e) => setEditMinSecondsSinceFinished(Number(e.target.value))} placeholder="60" />
                  </div>
                  <div className="space-y-2">
                    <Label>Máx tiempo después de fin (seg)</Label>
                    <Input type="number" value={editMaxSecondsSinceFinished} onChange={(e) => setEditMaxSecondsSinceFinished(Number(e.target.value))} placeholder="1800" />
                  </div>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="sizing" className="border rounded-lg">
                <AccordionTrigger className="px-4 py-3 text-sm font-medium">
                  Sizing {isTelegramTipsterStrategy(strategy) ? '(stake por tip)' : '(tamaño de orden)'}
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 space-y-3">
                  <div className="space-y-2">
                    <Label>{isTelegramTipsterStrategy(strategy) ? 'Stake por tip (USDC)' : 'Tamaño orden (USDC)'}</Label>
                    <Input type="number" value={editOrderUsdc} onChange={(e) => setEditOrderUsdc(Number(e.target.value))} placeholder="1000" className="max-w-xs" />
                  </div>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" checked={editCapacitySizingEnabled} onChange={(e) => setEditCapacitySizingEnabled(e.target.checked)} className="w-4 h-4" />
                    <span className="text-sm">Smart sizing (ajustar por liquidez)</span>
                  </label>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="execution" className="border rounded-lg">
                <AccordionTrigger className="px-4 py-3 text-sm font-medium">
                  Execution (tipo y límites)
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 grid gap-3 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Tipo de orden</Label>
                    <Select value={editOrderMode} onValueChange={(v) => setEditOrderMode(v as 'IOC' | 'POST_ONLY')}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="IOC">Market (IOC)</SelectItem>
                        <SelectItem value="POST_ONLY">Limit (POST_ONLY)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Timeout orden (ms)</Label>
                    <Input type="number" value={editTtlMs} onChange={(e) => setEditTtlMs(Number(e.target.value))} placeholder="5000" />
                  </div>
                  <div className="space-y-2">
                    <Label>Price drift limit (bps)</Label>
                    <Input type="number" value={editDriftBpsLimit} onChange={(e) => setEditDriftBpsLimit(Number(e.target.value))} placeholder="20" />
                  </div>
                  <div className="space-y-2">
                    <Label>Tick size</Label>
                    <Input type="number" step="0.0001" value={editTickSize} onChange={(e) => setEditTickSize(Number(e.target.value))} placeholder="0.001" />
                  </div>
                  <div className="space-y-2">
                    <Label>Improve price by (ticks)</Label>
                    <Input type="number" value={editImproveTicks} onChange={(e) => setEditImproveTicks(Number(e.target.value))} placeholder="1" />
                  </div>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="risk" className="border rounded-lg">
                <AccordionTrigger className="px-4 py-3 text-sm font-medium">
                  Riesgo (exposición máxima)
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 space-y-3">
                  <div className="space-y-2">
                    <Label>Exposición máxima (USDC)</Label>
                    <Input type="number" min={0} value={editMaxExposure} onChange={(e) => setEditMaxExposure(e.target.value)} placeholder="5000" className="max-w-xs" />
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>

            {saveError && <p className="text-sm text-destructive">{saveError}</p>}
            <Button onClick={handleSave} disabled={saving}>
              <Save className="h-4 w-4 mr-2" />
              {saving ? 'Guardando…' : 'Guardar cambios'}
            </Button>

            <div className="grid gap-4 pt-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <GitBranch className="h-4 w-4" />
                    Grafo de decisión
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    {isTelegramTipsterStrategy(strategy)
                      ? 'Flujo de decisión (parse, match, riesgo, ejecución).'
                      : 'Edita el flujo de decisión (nodos y conexiones).'}
                  </p>
                </CardHeader>
                <CardContent>
                  <Button variant="outline" asChild>
                    <Link href={`/strategies/${strategyId}/builder`}>
                      Editar grafo
                      <ExternalLink className="h-4 w-4 ml-2" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
              {!isTelegramTipsterStrategy(strategy) && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Eventos y mercados
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Asigna qué eventos/mercados opera esta estrategia (explorar directorio o Desk).
                  </p>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-2">
                  <Button variant="default" size="sm" asChild>
                    <Link href={`/strategies/${strategyId}/universe`}>
                      Configurar Universe
                      <ExternalLink className="h-3.5 w-3.5 ml-1.5" />
                    </Link>
                  </Button>
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/strategies/${strategyId}/desk`}>
                      Desk
                      <ExternalLink className="h-3.5 w-3.5 ml-1.5" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
              )}
            </div>

            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                  <span><strong>Estado:</strong> {strategy.is_active ? 'Activa' : 'Parada'}</span>
                  <span><strong>Versión:</strong> {strategy.version}</span>
                  {getSupportGraphLabels(strategy).length > 0 ? (
                    <span><strong>Módulos:</strong> {getSupportGraphLabels(strategy).join(', ')}</span>
                  ) : (
                    <span><strong>External Data Modules:</strong> {strategy.support_graphs?.length ?? 0}</span>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === 'graph' && (
          <div className="space-y-6">
            <StrategyDataFlowDiagram
              supportGraphs={strategy.support_graphs ?? []}
              defaultExpanded={true}
            />
            <div>
              <h2 className="text-h2 text-foreground mb-4">Decision Graph</h2>
              <GraphBuilder
                graph={strategy.decision_graph}
                onGraphChange={(newGraph) => {
                  // TODO: Implementar actualización del grafo
                  console.log('Graph changed:', newGraph);
                }}
                pathType="hot"
                readOnly={true}
                onNodeDefinitionsLoad={loadNodeDefinitions}
              />
            </div>
            {strategy.support_graphs && strategy.support_graphs.length > 0 && (
              <div>
                <h2 className="text-h2 text-foreground mb-4">External Data Modules</h2>
                <Accordion type="multiple" defaultValue={[]} className="space-y-2">
                  {strategy.support_graphs.map((sg, index) => (
                    <AccordionItem
                      key={index}
                      value={`sg-${index}`}
                      className="rounded-[var(--radius-lg)] bg-card shadow-premium-sm border border-[hsl(var(--border))]/50 overflow-hidden"
                    >
                      <AccordionTrigger className="px-4 py-3 hover:no-underline text-body font-medium">
                        {sg.name}
                      </AccordionTrigger>
                      <AccordionContent className="px-4 pb-4">
                        <GraphBuilder
                          graph={sg}
                          onGraphChange={() => {}}
                          pathType="cold"
                          readOnly={true}
                          onNodeDefinitionsLoad={loadNodeDefinitions}
                        />
                      </AccordionContent>
                    </AccordionItem>
                  ))}
                </Accordion>
              </div>
            )}
          </div>
        )}

        {activeTab === 'executions' && (
          <div className="space-y-4">
            {executions.length === 0 ? (
              <div className="p-8 text-center border border-slate-200 rounded-lg bg-white">
                <p className="text-sm text-slate-600">No hay ejecuciones registradas aún.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {executions.map((execution) => (
                  <div
                    key={execution.id}
                    className="p-4 border border-slate-200 rounded-lg bg-white"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-semibold text-slate-900">
                          {execution.graph_type === 'decision' ? 'Decision Graph' : execution.graph_name}
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          {new Date(execution.started_at).toLocaleString('es-ES')}
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <span
                          className={`px-2 py-1 text-xs font-medium rounded ${
                            execution.status === 'completed'
                              ? 'bg-green-100 text-green-700'
                              : execution.status === 'failed'
                              ? 'bg-red-100 text-red-700'
                              : 'bg-yellow-100 text-yellow-700'
                          }`}
                        >
                          {execution.status}
                        </span>
                        {execution.duration_ms && (
                          <span className="text-xs text-slate-600">
                            {execution.duration_ms.toFixed(2)}ms
                          </span>
                        )}
                      </div>
                    </div>
                    {execution.error_message && (
                      <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-800">
                        {execution.error_message}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'intents' && (
          <div className="space-y-4">
            {intents.length === 0 ? (
              <div className="p-8 text-center border border-slate-200 rounded-lg bg-white">
                <p className="text-sm text-slate-600">No hay intents generados aún.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {intents.map((intent) => (
                  <div
                    key={intent.id}
                    className="p-4 border border-slate-200 rounded-lg bg-white"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-semibold text-slate-900">
                          {intent.side} {intent.outcome} @ ${intent.target_price}
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          Tamaño: {intent.size} ({intent.size_usdc} USDC)
                        </div>
                        <div className="text-xs text-slate-500">{intent.reason}</div>
                      </div>
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          intent.status === 'APPROVED'
                            ? 'bg-green-100 text-green-700'
                            : intent.status === 'REJECTED'
                            ? 'bg-red-100 text-red-700'
                            : intent.status === 'EXECUTED'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {intent.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'metrics' && (
          <div className="space-y-4">
            {metrics.length === 0 ? (
              <div className="p-8 text-center border border-slate-200 rounded-lg bg-white">
                <p className="text-sm text-slate-600">No hay métricas disponibles aún.</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {metrics.map((metric) => (
                  <div key={metric.id} className="p-4 border border-slate-200 rounded-lg bg-white">
                    <div className="text-xs text-slate-600 mb-2">
                      {new Date(metric.period_start).toLocaleDateString('es-ES')} -{' '}
                      {new Date(metric.period_end).toLocaleDateString('es-ES')}
                    </div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">Intents:</span>
                        <span className="font-semibold text-slate-900">{metric.total_intents}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">Aprobados:</span>
                        <span className="font-semibold text-green-600">{metric.approved_intents}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">Ejecutados:</span>
                        <span className="font-semibold text-blue-600">{metric.executed_intents}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">Volumen:</span>
                        <span className="font-semibold text-slate-900">
                          ${metric.total_volume_usdc.toFixed(2)} USDC
                        </span>
                      </div>
                      {metric.total_pnl_usdc != null && (
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-600">PnL:</span>
                          <span
                            className={`font-semibold ${
                              (metric.total_pnl_usdc ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'
                            }`}
                          >
                            ${(metric.total_pnl_usdc ?? 0).toFixed(2)} USDC
                          </span>
                        </div>
                      )}
                      {metric.win_rate !== null && (
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-600">Win Rate:</span>
                          <span className="font-semibold text-slate-900">
                            {((metric.win_rate ?? 0) * 100).toFixed(2)}%
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}

