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

interface DecisionTraceTimelineProps {
  stages: DecisionTrace[];
}

const STAGE_ORDER = ['SCAN', 'EVENT_CONFIRMATION', 'STRATEGY', 'RISK', 'EXECUTION'];
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

export function DecisionTraceTimeline({ stages }: DecisionTraceTimelineProps) {
  // Ordenar stages por orden esperado
  const orderedStages = [...stages].sort((a, b) => {
    const aIndex = STAGE_ORDER.indexOf(a.decision_stage);
    const bIndex = STAGE_ORDER.indexOf(b.decision_stage);
    if (aIndex === -1 && bIndex === -1) return 0;
    if (aIndex === -1) return 1;
    if (bIndex === -1) return -1;
    return aIndex - bIndex;
  });

  // Calcular tiempos relativos
  const firstTimestamp = new Date(orderedStages[0]?.timestamp || Date.now()).getTime();
  const lastTimestamp = new Date(orderedStages[orderedStages.length - 1]?.timestamp || Date.now()).getTime();
  const totalDuration = Math.max(lastTimestamp - firstTimestamp, 1);

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  };

  const getRelativePosition = (timestamp: string) => {
    const time = new Date(timestamp).getTime();
    return ((time - firstTimestamp) / totalDuration) * 100;
  };

  return (
    <div className="relative">
      {/* Timeline Line */}
      <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-slate-300"></div>

      {/* Stages */}
      <div className="space-y-6">
        {orderedStages.map((stage, index) => {
          const position = getRelativePosition(stage.timestamp);
          const stageColor = STAGE_COLORS[stage.decision_stage] || '#6b7280';
          const decisionColor = DECISION_COLORS[stage.decision] || '#6b7280';

          return (
            <div key={stage.id} className="relative flex items-start gap-4">
              {/* Timeline Dot */}
              <div className="relative z-10">
                <div
                  className="w-4 h-4 rounded-full border-2 border-white shadow-lg"
                  style={{ backgroundColor: stageColor }}
                ></div>
                {index < orderedStages.length - 1 && (
                  <div
                    className="absolute left-1/2 top-4 w-0.5 -translate-x-1/2"
                    style={{
                      height: '24px',
                      backgroundColor: stageColor,
                      opacity: 0.3,
                    }}
                  ></div>
                )}
              </div>

              {/* Content Card */}
              <div className="flex-1 glass rounded-xl p-4 shadow-md">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span
                      className="px-3 py-1 text-xs font-semibold rounded-full text-white"
                      style={{ backgroundColor: stageColor }}
                    >
                      {stage.decision_stage}
                    </span>
                    <span
                      className="px-2 py-1 text-xs rounded"
                      style={{
                        backgroundColor: decisionColor + '20',
                        color: decisionColor,
                      }}
                    >
                      {stage.decision}
                    </span>
                  </div>
                  <span className="text-xs text-slate-500">{formatTime(stage.timestamp)}</span>
                </div>

                {stage.reason && (
                  <p className="text-sm text-slate-700 mb-2">
                    <strong>Razón:</strong> {stage.reason}
                  </p>
                )}

                <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
                  {stage.latency_ms !== null && (
                    <div>
                      <strong>Latencia:</strong> {stage.latency_ms.toFixed(2)}ms
                    </div>
                  )}
                  {stage.confidence_score !== null && (
                    <div>
                      <strong>Confianza:</strong> {(stage.confidence_score * 100).toFixed(1)}%
                    </div>
                  )}
                </div>

                {/* Input/Output Summary */}
                {stage.input_data && (
                  <details className="mt-2">
                    <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-700">
                      Ver detalles
                    </summary>
                    <div className="mt-2 p-2 bg-slate-50 rounded text-xs">
                      <div className="mb-2">
                        <strong>Input:</strong>
                        <pre className="mt-1 text-xs overflow-x-auto">
                          {JSON.stringify(stage.input_data, null, 2)}
                        </pre>
                      </div>
                      {stage.output_data && (
                        <div>
                          <strong>Output:</strong>
                          <pre className="mt-1 text-xs overflow-x-auto">
                            {JSON.stringify(stage.output_data, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </details>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

