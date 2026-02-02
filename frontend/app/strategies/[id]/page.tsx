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
import { Strategy, GraphExecution, ExecutionIntent, StrategyMetric, GraphNodeDefinition } from '@/types/strategy';
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
import { Save, ExternalLink, GitBranch, Calendar } from 'lucide-react';

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

  // Cargar definiciones de nodos
  const loadNodeDefinitions = async () => {
    if (!user) return [];
    const api = initApiClient(createTokenGetter(user, stackApp));
    try {
      const data = await api.get<GraphNodeDefinition[]>('/graph-nodes?path_type=hot');
      const coldData = await api.get<GraphNodeDefinition[]>('/graph-nodes?path_type=cold');
      return [...data, ...coldData];
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
        const [strategyData, executionsRes, intentsRes, metricsRes] = await Promise.all([
          api.get<Strategy>(`/api/strategies/${strategyId}`),
          api.get<{ executions?: GraphExecution[] } | GraphExecution[]>(`/api/strategies/${strategyId}/executions?limit=50`).catch(() => ({ executions: [] })),
          api.get<{ intents?: ExecutionIntent[] } | ExecutionIntent[]>(`/api/strategies/${strategyId}/intents?limit=50`).catch(() => ({ intents: [] })),
          api.get<{ metrics?: StrategyMetric[] } | StrategyMetric[]>(`/api/strategies/${strategyId}/metrics`).catch(() => ({ metrics: [] })),
        ]);

        const executionsList = Array.isArray(executionsRes) ? executionsRes : (executionsRes?.executions ?? []);
        const intentsList = Array.isArray(intentsRes) ? intentsRes : (intentsRes?.intents ?? []);
        const metricsList = Array.isArray(metricsRes) ? metricsRes : (metricsRes?.metrics ?? []);

        setStrategy(strategyData);
        setExecutions(executionsList);
        setIntents(intentsList);
        setMetrics(metricsList);
      } catch (err) {
        console.error('Error fetching strategy:', err);
        setError(err instanceof Error ? err.message : 'Error al cargar estrategia');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user, stackApp, isConnected, strategyId]);

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
      const updated = await api.put<Strategy>(`/api/strategies/${strategyId}`, {
        name: editName || undefined,
        description: editDescription || undefined,
        risk_config: {
          ...strategy.risk_config,
          max_exposure: Number(editMaxExposure) || 5000,
          order_usdc: Number(editOrderUsdc) || 1000,
          min_liquidity: Number(editMinDepthUsdc) || 2000,
        },
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
    } catch (err) {
      console.error('Error saving strategy:', err);
      setSaveError(err instanceof Error ? err.message : 'Error al guardar');
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
      alert(err instanceof Error ? err.message : 'Error al activar estrategia');
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
      alert(err instanceof Error ? err.message : 'Error al desactivar estrategia');
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
                {tab === 'config' && 'Configuración (universo y mercados)'}
                {tab === 'graph' && 'Grafos'}
                {tab === 'executions' && 'Histórico: Ejecuciones'}
                {tab === 'intents' && 'Histórico: Intents'}
                {tab === 'metrics' && 'Histórico: Métricas'}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Configuración: lo más importante = universo y mercados (qué activar y qué no) */}
        {activeTab === 'config' && (
          <div className="space-y-6">
            <p className="text-sm text-muted-foreground">
              Lo más importante: definir el <strong>universo</strong> y qué <strong>mercados activar o excluir</strong>. Luego el resto de parámetros.
            </p>
            <Accordion type="multiple" defaultValue={['universe', 'identity', 'orderbook', 'timing', 'sizing', 'execution', 'risk']} className="space-y-2">
              <AccordionItem value="universe" className="border rounded-lg border-primary/30 bg-primary/5">
                <AccordionTrigger className="px-4 py-3 text-sm font-semibold">
                  Universe y mercados (qué activar y qué no)
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 space-y-3">
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
                </AccordionContent>
              </AccordionItem>

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
                  Sizing (tamaño de orden)
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 space-y-3">
                  <div className="space-y-2">
                    <Label>Tamaño orden (USDC)</Label>
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

            <div className="grid gap-4 md:grid-cols-2 pt-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <GitBranch className="h-4 w-4" />
                    Grafo de decisión
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Edita el flujo de decisión (nodos y conexiones).
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
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Eventos y mercados
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Asigna qué eventos/mercados opera esta estrategia.
                  </p>
                </CardHeader>
                <CardContent>
                  <Button variant="outline" asChild>
                    <Link href={`/strategies/${strategyId}/desk`}>
                      Asignar eventos
                      <ExternalLink className="h-4 w-4 ml-2" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                  <span><strong>Estado:</strong> {strategy.is_active ? 'Activa' : 'Parada'}</span>
                  <span><strong>Versión:</strong> {strategy.version}</span>
                  <span><strong>Support graphs:</strong> {strategy.support_graphs?.length ?? 0}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === 'graph' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Decision Graph</h2>
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
                <h2 className="text-lg font-semibold text-slate-900 mb-4">Support Graphs</h2>
                <div className="space-y-4">
                  {strategy.support_graphs.map((sg, index) => (
                    <div key={index} className="p-4 border border-slate-200 rounded-lg bg-white">
                      <h3 className="text-sm font-semibold text-slate-900 mb-2">{sg.name}</h3>
                      <GraphBuilder
                        graph={sg}
                        onGraphChange={() => {}}
                        pathType="cold"
                        readOnly={true}
                        onNodeDefinitionsLoad={loadNodeDefinitions}
                      />
                    </div>
                  ))}
                </div>
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
                      {metric.total_pnl_usdc !== null && (
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-600">PnL:</span>
                          <span
                            className={`font-semibold ${
                              metric.total_pnl_usdc >= 0 ? 'text-green-600' : 'text-red-600'
                            }`}
                          >
                            ${metric.total_pnl_usdc.toFixed(2)} USDC
                          </span>
                        </div>
                      )}
                      {metric.win_rate !== null && (
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-600">Win Rate:</span>
                          <span className="font-semibold text-slate-900">
                            {(metric.win_rate * 100).toFixed(2)}%
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

