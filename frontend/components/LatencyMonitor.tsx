"use client";

import { useEffect, useState } from "react";
import { initApiClient } from "@/lib/api";

interface LatencyMetrics {
  timestamp: string;
  backend_latency_ms: number;
  polymarket_data_latency_ms: number | null;
  polymarket_trading_latency_ms: number | null;
  execution_latency_ms: number | null;
  status: "GREEN" | "YELLOW" | "RED";
}

interface LatencyMonitorProps {
  getToken: () => string | null;
}

export default function LatencyMonitor({ getToken }: LatencyMonitorProps) {
  const [metrics, setMetrics] = useState<LatencyMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const api = initApiClient(getToken);

    const fetchMetrics = async (isInitial = false) => {
      try {
        const data = await api.get<LatencyMetrics>("/metrics/latency");
        setMetrics(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error loading latency metrics");
      } finally {
        // Solo desactivar loading en la carga inicial
        if (isInitial) {
          setLoading(false);
        }
      }
    };

    // Carga inicial con loading
    fetchMetrics(true);

    // Actualizaciones periódicas sin mostrar loading
    const interval = setInterval(() => {
      fetchMetrics(false);
    }, 3000);

    return () => clearInterval(interval);
  }, [getToken]);

  if (loading && !metrics) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-sm text-gray-500">Cargando métricas de latencia...</div>
      </div>
    );
  }

  if (error && !metrics) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-sm text-red-800">Error: {error}</div>
      </div>
    );
  }

  if (!metrics) {
    return null;
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "GREEN":
        return "bg-green-100 border-green-300 text-green-800";
      case "YELLOW":
        return "bg-yellow-100 border-yellow-300 text-yellow-800";
      case "RED":
        return "bg-red-100 border-red-300 text-red-800";
      default:
        return "bg-gray-100 border-gray-300 text-gray-800";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "GREEN":
        return "🟢";
      case "YELLOW":
        return "🟡";
      case "RED":
        return "🔴";
      default:
        return "⚪";
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "GREEN":
        return "Operación Normal - Agresión Completa";
      case "YELLOW":
        return "Latencia Elevada - Reducir Agresión";
      case "RED":
        return "Latencia Crítica - Detener Nuevas Entradas";
      default:
        return "Estado Desconocido";
    }
  };

  return (
    <div className={`rounded-lg shadow p-4 border-2 ${getStatusColor(metrics.status)}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold">Monitor de Latencia</h3>
        <div className="flex items-center gap-2">
          <span className="text-2xl">{getStatusIcon(metrics.status)}</span>
          <span className="font-bold">{metrics.status}</span>
        </div>
      </div>

      <div className="text-sm mb-4">
        <p className="font-medium">{getStatusText(metrics.status)}</p>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="bg-white/50 rounded p-2">
          <div className="text-gray-600">Backend Latency</div>
          <div className="text-lg font-mono font-bold">
            {metrics.backend_latency_ms.toFixed(1)} ms
          </div>
        </div>

        <div className="bg-white/50 rounded p-2">
          <div className="text-gray-600">Polymarket Data API</div>
          <div className="text-lg font-mono font-bold">
            {metrics.polymarket_data_latency_ms !== null
              ? `${metrics.polymarket_data_latency_ms.toFixed(1)} ms`
              : "N/A"}
          </div>
        </div>

        <div className="bg-white/50 rounded p-2">
          <div className="text-gray-600">Polymarket Trading API</div>
          <div className="text-lg font-mono font-bold">
            {metrics.polymarket_trading_latency_ms !== null
              ? `${metrics.polymarket_trading_latency_ms.toFixed(1)} ms`
              : "N/A"}
          </div>
        </div>

        <div className="bg-white/50 rounded p-2">
          <div className="text-gray-600">Execution Latency (E2E)</div>
          <div className="text-lg font-mono font-bold">
            {metrics.execution_latency_ms !== null
              ? `${metrics.execution_latency_ms.toFixed(1)} ms`
              : "N/A"}
          </div>
        </div>
      </div>

      <div className="mt-3 text-xs text-gray-600">
        Última actualización: {new Date(metrics.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
}


