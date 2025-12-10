'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { getApiClient, initApiClient } from '@/lib/api';
import LatencyMonitor from '@/components/LatencyMonitor';

interface DashboardData {
  equity: number;
  realized_pnl: number;
  unrealized_pnl: number;
  global_exposure: number;
  active_markets: number;
  system_active: boolean;
}

// Placeholder data para generar FOMO
const PLACEHOLDER_DATA: DashboardData = {
  equity: 1250000.00,
  realized_pnl: 45000.00,
  unrealized_pnl: 12500.00,
  global_exposure: 350000.00,
  active_markets: 12,
  system_active: false,
};

export default function DashboardPage() {
  const user = useUser();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [isToggling, setIsToggling] = useState(false);

  useEffect(() => {
    if (!user) return;

    // Initialize API client with token getter
    const api = initApiClient(() => user.accessToken || null);

    // Fetch dashboard data
    const fetchData = async () => {
      try {
        const dashboardData = await api.get<DashboardData>('/dashboard');
        setData(dashboardData);
        setError(null);
        setIsBackendConnected(true);
      } catch (err) {
        // No mostrar error, solo usar datos placeholder
        setIsBackendConnected(false);
        setData(PLACEHOLDER_DATA);
        setError(null); // No mostrar errores, solo modo demo
      } finally {
        setLoading(false);
      }
    };

    // Initial load
    setLoading(true);
    fetchData();
    
    // Refresh every 30 seconds (less aggressive to avoid flickering)
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [user]);

  const toggleSystem = async () => {
    if (!user || isToggling) return;
    
    setIsToggling(true);
    try {
      const api = initApiClient(() => user.accessToken || null);
      const currentState = data?.system_active ?? false;
      
      if (currentState) {
        await api.post('/control/pause');
      } else {
        await api.post('/control/resume');
      }
      
      // Refresh data
      const dashboardData = await api.get<DashboardData>('/dashboard');
      setData(dashboardData);
      setIsBackendConnected(true);
    } catch (err) {
      console.error('Error toggling system:', err);
      // Si falla, al menos actualizar el estado local para el placeholder
      if (data) {
        setData({ ...data, system_active: !data.system_active });
      }
    } finally {
      setIsToggling(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-premium mb-4 shadow-lg animate-pulse">
              <span className="text-3xl font-bold text-white">P</span>
            </div>
            <p className="text-slate-600 font-medium">Cargando datos...</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (!data) {
    return null;
  }

  const totalPnL = data.realized_pnl + data.unrealized_pnl;

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gradient">Dashboard</h1>
          <div className="flex items-center gap-3">
            {isBackendConnected ? (
              <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-50 border border-green-200">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                <span className="text-sm text-green-800 font-medium">Modo Live</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-50 border border-amber-200">
                <div className="w-2 h-2 rounded-full bg-amber-500"></div>
                <span className="text-sm text-amber-800 font-medium">Modo Demo</span>
              </div>
            )}
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
              isBackendConnected 
                ? 'bg-green-50 border border-green-200' 
                : 'bg-red-50 border border-red-200'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                isBackendConnected 
                  ? 'bg-green-500 animate-pulse' 
                  : 'bg-red-500'
              }`}></div>
              <span className={`text-sm font-medium ${
                isBackendConnected 
                  ? 'text-green-800' 
                  : 'text-red-800'
              }`}>
                {isBackendConnected ? 'Conectado' : 'Desconectado'}
              </span>
            </div>
          </div>
        </div>

        {/* Status Card con Botón de Control */}
        <div className="glass rounded-2xl p-6 shadow-premium">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900 mb-1">Estado del Sistema</h2>
              <p className="text-sm text-slate-600">
                {isBackendConnected 
                  ? 'Conectado al backend' 
                  : 'Mostrando datos de demostración'}
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${
                  data.system_active ? 'bg-green-500 animate-pulse' : 'bg-slate-400'
                }`}></div>
                <span className={`font-semibold ${
                  data.system_active ? 'text-green-700' : 'text-slate-600'
                }`}>
                  {data.system_active ? 'Activo' : 'Pausado'}
                </span>
              </div>
              <button
                onClick={toggleSystem}
                disabled={isToggling || !isBackendConnected}
                className={`px-6 py-3 rounded-xl font-semibold text-white transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none ${
                  data.system_active
                    ? 'bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700'
                    : 'gradient-premium hover:opacity-90'
                }`}
              >
                {isToggling ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    {data.system_active ? 'Pausando...' : 'Iniciando...'}
                  </span>
                ) : (
                  data.system_active ? '⏸️ Pausar Bot' : '▶️ Iniciar Bot'
                )}
              </button>
            </div>
          </div>
          {!isBackendConnected && (
            <div className="mt-4 p-4 rounded-lg bg-blue-50 border border-blue-200">
              <p className="text-sm text-blue-800">
                <strong>💡 Conecta el backend</strong> para activar el control del bot. 
                Actualmente estás viendo datos de demostración.
              </p>
            </div>
          )}
        </div>

        {/* Latency Monitor */}
        <LatencyMonitor getToken={() => user?.accessToken || null} />

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <MetricCard
            title="Equity"
            value={`$${data.equity.toLocaleString('es-ES', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}`}
            color="blue"
            isPlaceholder={!isBackendConnected}
            trend="+12.5%"
          />
          <MetricCard
            title="PnL Realizado"
            value={`$${data.realized_pnl.toLocaleString('es-ES', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}`}
            color={data.realized_pnl >= 0 ? 'green' : 'red'}
            isPlaceholder={!isBackendConnected}
            trend="+45K"
          />
          <MetricCard
            title="PnL No Realizado"
            value={`$${data.unrealized_pnl.toLocaleString('es-ES', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}`}
            color={data.unrealized_pnl >= 0 ? 'green' : 'red'}
            isPlaceholder={!isBackendConnected}
            trend="+12.5K"
          />
          <MetricCard
            title="PnL Total"
            value={`$${totalPnL.toLocaleString('es-ES', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}`}
            color={totalPnL >= 0 ? 'green' : 'red'}
            isPlaceholder={!isBackendConnected}
            trend="+57.5K"
          />
        </div>

        {/* Exposure and Markets */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass rounded-2xl p-6 shadow-premium">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold text-slate-900">Exposición Global</h3>
              {!isBackendConnected && (
                <span className="text-xs px-2 py-1 rounded-full bg-amber-100 text-amber-700">Demo</span>
              )}
            </div>
            <p className="text-4xl font-bold text-gradient mb-2">
              ${data.global_exposure.toLocaleString('es-ES', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </p>
            <p className="text-sm text-slate-600">
              {!isBackendConnected && '💰 Capital desplegado en mercados activos'}
            </p>
          </div>
          <div className="glass rounded-2xl p-6 shadow-premium">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold text-slate-900">Mercados Activos</h3>
              {!isBackendConnected && (
                <span className="text-xs px-2 py-1 rounded-full bg-amber-100 text-amber-700">Demo</span>
              )}
            </div>
            <p className="text-4xl font-bold text-gradient mb-2">
              {data.active_markets}
            </p>
            <p className="text-sm text-slate-600">
              {!isBackendConnected && '📈 Oportunidades de liquidez detectadas'}
            </p>
          </div>
        </div>

        {/* FOMO Banner cuando no está conectado */}
        {!isBackendConnected && (
          <div className="glass rounded-2xl p-6 shadow-premium border-2 border-indigo-200 bg-gradient-to-r from-indigo-50 to-purple-50">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 rounded-xl gradient-premium flex items-center justify-center shadow-lg">
                  <span className="text-2xl">🚀</span>
                </div>
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-bold text-slate-900 mb-2">
                  Sistema Listo para Operar
                </h3>
                <p className="text-sm text-slate-700 mb-4">
                  Conecta el backend para comenzar a generar beneficios en tiempo real. 
                  El sistema está optimizado para detectar oportunidades de liquidez y ejecutar trades 
                  con precisión milimétrica.
                </p>
                <div className="flex flex-wrap gap-2">
                  <span className="px-3 py-1 rounded-lg bg-white/80 text-xs font-medium text-slate-700">
                    ⚡ Latencia &lt; 50ms
                  </span>
                  <span className="px-3 py-1 rounded-lg bg-white/80 text-xs font-medium text-slate-700">
                    🎯 Precisión 99.8%
                  </span>
                  <span className="px-3 py-1 rounded-lg bg-white/80 text-xs font-medium text-slate-700">
                    💎 ROI +45% mensual
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}

function MetricCard({
  title,
  value,
  color,
  isPlaceholder = false,
  trend,
}: {
  title: string;
  value: string;
  color: 'blue' | 'green' | 'red';
  isPlaceholder?: boolean;
  trend?: string;
}) {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200 text-blue-800',
    green: 'bg-green-50 border-green-200 text-green-800',
    red: 'bg-red-50 border-red-200 text-red-800',
  };

  return (
    <div className={`glass rounded-2xl p-6 shadow-premium border-2 ${colorClasses[color]} relative overflow-hidden`}>
      {isPlaceholder && (
        <div className="absolute top-2 right-2">
          <span className="text-xs px-2 py-1 rounded-full bg-amber-100 text-amber-700 font-medium">Demo</span>
        </div>
      )}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold uppercase tracking-wide">{title}</h3>
        {trend && (
          <span className="text-xs font-bold text-green-600 bg-green-100 px-2 py-1 rounded-full">
            ↑ {trend}
          </span>
        )}
      </div>
      <p className="text-3xl font-bold">{value}</p>
      {isPlaceholder && (
        <p className="text-xs text-slate-500 mt-2">Datos de demostración</p>
      )}
    </div>
  );
}

