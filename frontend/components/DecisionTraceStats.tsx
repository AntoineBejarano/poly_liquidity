'use client';

interface DecisionTrace {
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

interface DecisionTraceStatsProps {
  traces: DecisionTrace[];
}

export function DecisionTraceStats({ traces }: DecisionTraceStatsProps) {
  // Estadísticas por etapa
  const statsByStage = traces.reduce((acc, trace) => {
    const stage = trace.decision_stage;
    if (!acc[stage]) {
      acc[stage] = { total: 0, approved: 0, rejected: 0, adjusted: 0, cancelled: 0, simulated: 0 };
    }
    acc[stage].total++;
    if (trace.decision === 'APPROVED') acc[stage].approved++;
    else if (trace.decision === 'REJECTED') acc[stage].rejected++;
    else if (trace.decision === 'ADJUSTED') acc[stage].adjusted++;
    else if (trace.decision === 'CANCELLED') acc[stage].cancelled++;
    else if (trace.decision === 'SIMULATED') acc[stage].simulated++;
    return acc;
  }, {} as Record<string, any>);

  // Estadísticas de latencia
  const latencies = traces.filter((t) => t.latency_ms !== null).map((t) => t.latency_ms!);
  const avgLatency = latencies.length > 0 ? latencies.reduce((a, b) => a + b, 0) / latencies.length : 0;
  const maxLatency = latencies.length > 0 ? Math.max(...latencies) : 0;
  const minLatency = latencies.length > 0 ? Math.min(...latencies) : 0;

  // Estadísticas de confianza
  const confidences = traces.filter((t) => t.confidence_score !== null).map((t) => t.confidence_score!);
  const avgConfidence = confidences.length > 0 ? confidences.reduce((a, b) => a + b, 0) / confidences.length : 0;

  // Distribución de decisiones
  const decisionCounts = traces.reduce((acc, trace) => {
    acc[trace.decision] = (acc[trace.decision] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const STAGE_COLORS: { [key: string]: string } = {
    SCAN: '#3b82f6',
    EVENT_CONFIRMATION: '#8b5cf6',
    STRATEGY: '#10b981',
    RISK: '#f59e0b',
    EXECUTION: '#ef4444',
  };

  const DECISION_COLORS: { [key: string]: string } = {
    APPROVED: '#10b981',
    REJECTED: '#ef4444',
    ADJUSTED: '#f59e0b',
    CANCELLED: '#6b7280',
    SIMULATED: '#3b82f6',
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {/* Estadísticas por Etapa */}
      <div className="glass rounded-xl p-4 shadow-md">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Decisiones por Etapa</h3>
        <div className="space-y-2">
          {Object.entries(statsByStage).map(([stage, stats]: [string, any]) => {
            const color = STAGE_COLORS[stage] || '#6b7280';
            const total = stats.total;
            const approvedPct = total > 0 ? (stats.approved / total) * 100 : 0;
            const rejectedPct = total > 0 ? (stats.rejected / total) * 100 : 0;

            return (
              <div key={stage} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium" style={{ color }}>
                    {stage}
                  </span>
                  <span className="text-slate-600">{total}</span>
                </div>
                <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div className="h-full flex">
                    <div
                      className="bg-green-500"
                      style={{ width: `${approvedPct}%` }}
                      title={`Approved: ${stats.approved}`}
                    ></div>
                    <div
                      className="bg-red-500"
                      style={{ width: `${rejectedPct}%` }}
                      title={`Rejected: ${stats.rejected}`}
                    ></div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Distribución de Decisiones */}
      <div className="glass rounded-xl p-4 shadow-md">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Distribución de Decisiones</h3>
        <div className="space-y-2">
          {Object.entries(decisionCounts).map(([decision, count]) => {
            const total = traces.length;
            const percentage = total > 0 ? (count / total) * 100 : 0;
            const color = DECISION_COLORS[decision] || '#6b7280';

            return (
              <div key={decision} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium" style={{ color }}>
                    {decision}
                  </span>
                  <span className="text-slate-600">
                    {count} ({percentage.toFixed(1)}%)
                  </span>
                </div>
                <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full"
                    style={{
                      width: `${percentage}%`,
                      backgroundColor: color,
                    }}
                  ></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Métricas de Rendimiento */}
      <div className="glass rounded-xl p-4 shadow-md">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Métricas de Rendimiento</h3>
        <div className="space-y-3">
          {latencies.length > 0 && (
            <div>
              <div className="text-xs text-slate-600 mb-1">Latencia (ms)</div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <div className="text-slate-500">Promedio</div>
                  <div className="font-semibold text-indigo-600">{avgLatency.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-slate-500">Mín</div>
                  <div className="font-semibold text-green-600">{minLatency.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-slate-500">Máx</div>
                  <div className="font-semibold text-red-600">{maxLatency.toFixed(2)}</div>
                </div>
              </div>
            </div>
          )}
          {confidences.length > 0 && (
            <div>
              <div className="text-xs text-slate-600 mb-1">Confianza Promedio</div>
              <div className="text-lg font-semibold text-purple-600">
                {(avgConfidence * 100).toFixed(1)}%
              </div>
            </div>
          )}
          <div>
            <div className="text-xs text-slate-600 mb-1">Total de Traces</div>
            <div className="text-lg font-semibold text-slate-700">{traces.length}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

