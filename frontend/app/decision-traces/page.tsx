'use client';

import { useEffect, useState, useRef } from 'react';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
import { DecisionTraceTimeline } from '@/components/DecisionTraceTimeline';
import { DecisionTraceStats } from '@/components/DecisionTraceStats';
import Link from 'next/link';

export interface DecisionTrace {
  id: string;
  trace_id: string;
  session_id: string | null;
  timestamp: string;
  component: string;
  decision_stage: string;
  market_id: string | null;
  event_id: string | null;
  decision_type: string;
  decision: string;
  reason: string | null;
  input_data: any;
  output_data: any;
  config_used: any;
  latency_ms: number | null;
  confidence_score: number | null;
  extra_metadata: any;
}

interface DecisionTracesResponse {
  total: number;
  offset: number;
  limit: number;
  traces: DecisionTrace[];
}

interface TracePipeline {
  trace_id: string;
  stages: DecisionTrace[];
}

const DECISION_STAGES = ['SCAN', 'EVENT_CONFIRMATION', 'STRATEGY', 'RISK', 'EXECUTION'];
const DECISION_COLORS: { [key: string]: string } = {
  APPROVED: 'bg-slate-100 text-slate-700 border-slate-200',
  REJECTED: 'bg-slate-100 text-slate-600 border-slate-200',
  ADJUSTED: 'bg-slate-100 text-slate-700 border-slate-200',
  CANCELLED: 'bg-slate-100 text-slate-800 border-slate-200',
  SIMULATED: 'bg-slate-100 text-slate-700 border-slate-200',
};

export default function DecisionTracesPage() {
  const user = useUser();
  const { isConnected } = useBackendConnection();
  const { isDemo } = useDataMode();
  const [traces, setTraces] = useState<DecisionTrace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [limit] = useState(50);
  
  // Filters
  const [filterComponent, setFilterComponent] = useState<string>('');
  const [filterStage, setFilterStage] = useState<string>('');
  const [filterDecision, setFilterDecision] = useState<string>('');
  const [filterTraceId, setFilterTraceId] = useState<string>('');
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [tracePipeline, setTracePipeline] = useState<TracePipeline | null>(null);
  const isInitialLoadRef = useRef(true);

  useEffect(() => {
    if (!user) return;

    if (isDemo) {
      setTraces([]);
      setTotal(0);
      setError(null);
      setLoading(false);
      return;
    }

    const api = initApiClient(createTokenGetter(user));

    const fetchTraces = async (isInitial = false) => {
      try {
        const params = new URLSearchParams();
        if (filterComponent) params.append('component', filterComponent);
        if (filterStage) params.append('decision_stage', filterStage);
        if (filterDecision) params.append('decision', filterDecision);
        if (filterTraceId) params.append('trace_id', filterTraceId);
        params.append('limit', String(limit));
        params.append('offset', String(offset));

        const data = await api.get<DecisionTracesResponse>(`/system/decision-traces?${params.toString()}`);
        setTraces(data.traces);
        setTotal(data.total);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading traces');
      } finally {
        if (isInitial) {
          setLoading(false);
        }
      }
    };

    if (isInitialLoadRef.current) {
      setLoading(true);
      fetchTraces(true);
      isInitialLoadRef.current = false;
    } else {
      fetchTraces(false);
    }
  }, [user, isDemo, filterComponent, filterStage, filterDecision, filterTraceId, offset, limit]);

  const handleViewPipeline = async (traceId: string) => {
    if (!user) return;

    const api = initApiClient(createTokenGetter(user));

    try {
      const data = await api.get<TracePipeline>(`/system/decision-traces/${traceId}`);
      setTracePipeline(data);
      setSelectedTraceId(traceId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error loading trace pipeline');
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('es-ES', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  };

  if (loading && traces.length === 0) {
    return (
      <Layout>
        <LoadingSpinner text="Cargando decision traces..." />
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-medium text-slate-900 dark:text-slate-100">Decision Traces</h1>
          {isDemo && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-50 border border-amber-200 dark:bg-amber-950/30 dark:border-amber-800">
              <div className="w-2 h-2 rounded-full bg-amber-500"></div>
              <span className="text-sm text-amber-800 dark:text-amber-200 font-medium">Modo Demo</span>
            </div>
          )}
        </div>

        {isDemo && (
          <div className="rounded-lg p-3 bg-muted/50 dark:bg-muted/20 border border-border">
            <p className="text-sm text-muted-foreground">
              Modo Demo: no hay datos de traces. Cambia a modo Real para ver decision traces del backend.
            </p>
          </div>
        )}

        {error && !isDemo && (
          <div className="border border-destructive/30 rounded-lg p-3 bg-destructive/10">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Filters */}
        <div className="glass rounded-2xl shadow-premium p-6">
          <h2 className="text-lg font-semibold mb-4">Filtros</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Componente</label>
              <select
                value={filterComponent}
                onChange={(e) => {
                  setFilterComponent(e.target.value);
                  setOffset(0);
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Todos</option>
                <option value="scanner">Scanner</option>
                <option value="event_engine">Event Engine</option>
                <option value="strategy">Strategy</option>
                <option value="risk">Risk</option>
                <option value="execution">Execution</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Etapa</label>
              <select
                value={filterStage}
                onChange={(e) => {
                  setFilterStage(e.target.value);
                  setOffset(0);
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Todas</option>
                {DECISION_STAGES.map((stage) => (
                  <option key={stage} value={stage}>
                    {stage}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Decisión</label>
              <select
                value={filterDecision}
                onChange={(e) => {
                  setFilterDecision(e.target.value);
                  setOffset(0);
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Todas</option>
                <option value="APPROVED">APPROVED</option>
                <option value="REJECTED">REJECTED</option>
                <option value="ADJUSTED">ADJUSTED</option>
                <option value="CANCELLED">CANCELLED</option>
                <option value="SIMULATED">SIMULATED</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Trace ID</label>
              <input
                type="text"
                value={filterTraceId}
                onChange={(e) => {
                  setFilterTraceId(e.target.value);
                  setOffset(0);
                }}
                placeholder="UUID del trace"
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
        </div>

        {/* Statistics */}
        {traces.length > 0 && (
          <div className="glass rounded-2xl shadow-premium p-6">
            <h2 className="text-lg font-semibold mb-4">Estadísticas</h2>
            <DecisionTraceStats traces={traces} />
          </div>
        )}

        {/* Trace Pipeline View */}
        {tracePipeline && selectedTraceId && (
          <div className="glass rounded-2xl shadow-premium p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-sm font-medium text-slate-900">Pipeline Completo</h2>
              <button
                onClick={() => {
                  setTracePipeline(null);
                  setSelectedTraceId(null);
                }}
                className="px-4 py-2 text-sm rounded-lg bg-slate-200 text-slate-700 hover:bg-slate-300 transition-colors"
              >
                Cerrar
              </button>
            </div>
            <div className="mb-4 p-3 bg-slate-50 rounded-lg">
              <p className="text-xs text-slate-600">
                <strong>Trace ID:</strong> {selectedTraceId}
              </p>
            </div>
            <DecisionTraceTimeline stages={tracePipeline.stages} />
          </div>
        )}

        {/* Traces Table */}
        <div className="glass rounded-2xl shadow-premium p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">
              Traces ({total} total)
            </h2>
            <div className="flex gap-2">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="px-3 py-1 text-sm rounded bg-slate-200 text-slate-700 hover:bg-slate-300 disabled:opacity-50"
              >
                Anterior
              </button>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={offset + limit >= total}
                className="px-3 py-1 text-sm rounded bg-slate-200 text-slate-700 hover:bg-slate-300 disabled:opacity-50"
              >
                Siguiente
              </button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 px-4 font-semibold text-slate-700">Timestamp</th>
                  <th className="text-left py-3 px-4 font-semibold text-slate-700">Etapa</th>
                  <th className="text-left py-3 px-4 font-semibold text-slate-700">Componente</th>
                  <th className="text-left py-3 px-4 font-semibold text-slate-700">Decisión</th>
                  <th className="text-left py-3 px-4 font-semibold text-slate-700">Razón</th>
                  <th className="text-left py-3 px-4 font-semibold text-slate-700">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {traces.map((trace) => (
                  <tr key={trace.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-3 px-4 text-sm text-slate-600">
                      {formatTimestamp(trace.timestamp)}
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-1 text-xs rounded border border-slate-200 bg-slate-50 text-slate-700">
                        {trace.decision_stage}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700">{trace.component}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 text-xs rounded ${DECISION_COLORS[trace.decision] || 'bg-slate-200'}`}>
                        {trace.decision}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-600">
                      {trace.reason || '-'}
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => handleViewPipeline(trace.trace_id)}
                        className="px-3 py-1 text-sm rounded border border-slate-200 bg-slate-900 text-white hover:bg-slate-800"
                      >
                        Ver Pipeline
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Layout>
  );
}

