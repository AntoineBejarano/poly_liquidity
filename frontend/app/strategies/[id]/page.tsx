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
  const params = useParams();
  const router = useRouter();
  
  // Redirect to live control page
  useEffect(() => {
    if (params.id) {
      router.replace(`/strategies/${params.id}/live`);
    }
  }, [params.id, router]);
  
  return null;
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
  const [activeTab, setActiveTab] = useState<'overview' | 'graph' | 'executions' | 'intents' | 'metrics'>('overview');
  const [activating, setActivating] = useState(false);

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
    if (!user || !isConnected || !strategyId) {
      setLoading(false);
      return;
    }

    const api = initApiClient(createTokenGetter(user, stackApp));

    const fetchData = async () => {
      try {
        setLoading(true);
        const [strategyData, executionsData, intentsData, metricsData] = await Promise.all([
          api.get<Strategy>(`/strategies/${strategyId}`),
          api.get<GraphExecution[]>(`/strategies/${strategyId}/executions?limit=50`).catch(() => []),
          api.get<ExecutionIntent[]>(`/strategies/${strategyId}/intents?limit=50`).catch(() => []),
          api.get<StrategyMetric[]>(`/strategies/${strategyId}/metrics`).catch(() => []),
        ]);

        setStrategy(strategyData);
        setExecutions(executionsData);
        setIntents(intentsData);
        setMetrics(metricsData);
        setError(null);
      } catch (err) {
        console.error('Error fetching strategy:', err);
        setError(err instanceof Error ? err.message : 'Error al cargar estrategia');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user, stackApp, isConnected, strategyId]);

  const handleActivate = async () => {
    if (!strategy) return;

    setActivating(true);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.post(`/strategies/${strategyId}/activate`);
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
      await api.post(`/strategies/${strategyId}/deactivate`);
      setStrategy({ ...strategy, is_active: false });
    } catch (err) {
      console.error('Error deactivating strategy:', err);
      alert(err instanceof Error ? err.message : 'Error al desactivar estrategia');
    } finally {
      setActivating(false);
    }
  };

  if (!user) {
    return null;
  }

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner />
      </Layout>
    );
  }

  if (error || !strategy) {
    return (
      <Layout>
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error || 'Estrategia no encontrada'}</p>
          <Link href="/strategies" className="mt-2 inline-block text-sm text-blue-600 hover:text-blue-700">
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
              <Link href="/strategies" className="text-sm text-slate-600 hover:text-slate-900">
                ← Estrategias
              </Link>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mt-2">{strategy.name}</h1>
            {strategy.description && (
              <p className="text-sm text-slate-600 mt-1">{strategy.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
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

        {/* Tabs */}
        <div className="border-b border-slate-200">
          <nav className="flex gap-4">
            {(['overview', 'graph', 'executions', 'intents', 'metrics'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                {tab === 'overview' && 'Resumen'}
                {tab === 'graph' && 'Grafos'}
                {tab === 'executions' && 'Ejecuciones'}
                {tab === 'intents' && 'Intents'}
                {tab === 'metrics' && 'Métricas'}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 bg-white border border-slate-200 rounded-lg">
                <div className="text-xs text-slate-600 mb-1">Estado</div>
                <div className="text-lg font-semibold text-slate-900">
                  {strategy.is_active ? 'Activa' : 'Inactiva'}
                </div>
              </div>
              <div className="p-4 bg-white border border-slate-200 rounded-lg">
                <div className="text-xs text-slate-600 mb-1">Versión</div>
                <div className="text-lg font-semibold text-slate-900">{strategy.version}</div>
              </div>
              <div className="p-4 bg-white border border-slate-200 rounded-lg">
                <div className="text-xs text-slate-600 mb-1">Support Graphs</div>
                <div className="text-lg font-semibold text-slate-900">
                  {strategy.support_graphs?.length || 0}
                </div>
              </div>
            </div>
            {strategy.tags && strategy.tags.length > 0 && (
              <div className="p-4 bg-white border border-slate-200 rounded-lg">
                <div className="text-xs text-slate-600 mb-2">Tags</div>
                <div className="flex flex-wrap gap-2">
                  {strategy.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-1 text-xs font-medium text-slate-700 bg-slate-100 border border-slate-200 rounded"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
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

