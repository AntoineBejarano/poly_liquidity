'use client';

import { useEffect, useState, useRef } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import Link from 'next/link';

interface DashboardData {
  equity: number;
  realized_pnl: number;
  unrealized_pnl: number;
  global_exposure: number;
  active_markets: number;
  system_active: boolean;
}

interface BotStatus {
  execution_mode: 'DRY_RUN' | 'PAPER' | 'LIVE';
  system_state: 'PAUSADO' | 'ACTIVO' | 'BLOQUEADO';
  last_decision: {
    decision: string;
    component: string;
    reason: string | null;
    timestamp: string;
    trace_id: string;
  } | null;
  last_action: {
    type: string;
    message: string;
    timestamp?: string;
  } | null;
  execution_mode_description: {
    DRY_RUN: string;
    PAPER: string;
    LIVE: string;
  };
}

interface ActiveMarket {
  market_id: string;
  name: string;
  enabled: boolean;
  events_count: number;
  active_events_count: number;
  series_name: string | null;
}

interface ActiveEvent {
  event_id: string;
  polymarket_event_id: string;
  market_id: string;
  market_name: string;
  start_time: string;
  end_time: string;
  state: 'UPCOMING' | 'ACTIVE' | 'FINISHED';
  liquidity: number | null;
}

interface RiskAlert {
  type: string;
  severity: 'warning' | 'critical';
  message: string;
  details: Record<string, any>;
}

interface RecentDecision {
  timestamp: string;
  component: string;
  decision: string;
  reason: string | null;
  trace_id: string | null;
}

interface SystemHealth {
  latency_status: 'GREEN' | 'YELLOW' | 'RED';
  checkers_active: number;
  checkers_total: number;
  last_checker_failure: string | null;
  scanner_status: string;
  scanner_last_scan: string | null;
}

interface LiveStatus {
  bot_status: BotStatus;
  active_markets: ActiveMarket[];
  active_events: ActiveEvent[];
  risk_alerts: RiskAlert[];
  recent_decisions: RecentDecision[];
  system_health: SystemHealth;
}

interface Position {
  market_id: string;
  polymarket_id: string;
  question: string;
  size: number;
  avg_price: number;
  current_price: number;
  unrealized_pnl: number;
  resolved: boolean;
  payout: number | null;
}

interface RiskConfig {
  max_exposure_per_market: number;
  max_global_exposure: number;
  min_entry_price: number;
  target_margin: number;
  max_markets_active: number;
}

const PLACEHOLDER_DASHBOARD: DashboardData = {
  equity: 1250000.00,
  realized_pnl: 45000.00,
  unrealized_pnl: 12500.00,
  global_exposure: 350000.00,
  active_markets: 12,
  system_active: false,
};

const PLACEHOLDER_RISK: RiskConfig = {
  max_exposure_per_market: 50000,
  max_global_exposure: 500000,
  min_entry_price: 0.98,
  target_margin: 0.001,
  max_markets_active: 30,
};

const PLACEHOLDER_LIVE_STATUS: LiveStatus = {
  bot_status: {
    execution_mode: 'DRY_RUN' as const,
    system_state: 'PAUSADO' as const,
    last_decision: null,
    last_action: { type: 'no_connection', message: 'Backend no disponible - Modo demo' },
    execution_mode_description: {
      DRY_RUN: 'Simulación completa. No se envían órdenes, solo se simulan decisiones y ejecuciones.',
      PAPER: 'Trading en papel. Se envían órdenes pero no se ejecutan realmente. Útil para probar conectividad y lógica sin riesgo.',
      LIVE: 'Trading real. Se envían y ejecutan órdenes reales en Polymarket. ⚠️ Usa dinero real.'
    }
  },
  active_markets: [],
  active_events: [],
  risk_alerts: [],
  recent_decisions: [],
  system_health: {
    latency_status: 'UNKNOWN' as any,
    checkers_active: 0,
    checkers_total: 0,
    last_checker_failure: null,
    scanner_status: 'UNKNOWN',
    scanner_last_scan: null
  }
};

export default function LiveControlPage() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  
  // Dashboard data
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [liveStatus, setLiveStatus] = useState<LiveStatus | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [riskConfig, setRiskConfig] = useState<RiskConfig | null>(null);
  
  // UI state
  const [loading, setLoading] = useState(true);
  const [isToggling, setIsToggling] = useState(false);
  const [togglingMarket, setTogglingMarket] = useState<string | null>(null);
  const [changingMode, setChangingMode] = useState(false);
  const [showModeConfirm, setShowModeConfirm] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<Array<{time: string; event: string; component?: string}>>([]);

  // Fetch all data - SOLO cuando el backend está conectado
  useEffect(() => {
    if (!user || !isConnected) {
      // Si no hay usuario o backend no está conectado, usar datos placeholder
      setDashboardData(PLACEHOLDER_DASHBOARD);
      setLiveStatus(PLACEHOLDER_LIVE_STATUS);
      setPositions([]);
      setRiskConfig(PLACEHOLDER_RISK);
      setLoading(false);
      return;
    }

    const api = initApiClient(createTokenGetter(user, stackApp));

    const fetchAllData = async () => {
      try {
        const [dashboard, status, positionsData, risk] = await Promise.all([
          api.get<DashboardData>('/dashboard').catch(() => PLACEHOLDER_DASHBOARD),
          api.get<LiveStatus>('/live/status').catch(() => null),
          api.get<Position[]>('/positions').catch(() => []),
          api.get<RiskConfig>('/risk/config').catch(() => PLACEHOLDER_RISK),
        ]);
        
        setDashboardData(dashboard);
        setLiveStatus(status);
        setPositions(positionsData);
        setRiskConfig(risk);
        
        // Actualizar timeline con decisiones recientes
        if (status?.recent_decisions && status.recent_decisions.length > 0) {
          const timelineItems = status.recent_decisions.slice(0, 5).map(dec => ({
            time: new Date(dec.timestamp).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            event: `${dec.component}: ${dec.decision}${dec.reason ? ` - ${dec.reason}` : ''}`,
            component: dec.component,
          }));
          setTimeline(timelineItems);
        } else {
          setTimeline([]);
        }
      } catch (err) {
        console.error('Error fetching data:', err);
        // En caso de error, usar datos placeholder
        setDashboardData(PLACEHOLDER_DASHBOARD);
        setLiveStatus(PLACEHOLDER_LIVE_STATUS);
        setPositions([]);
        setRiskConfig(PLACEHOLDER_RISK);
      } finally {
        setLoading(false);
      }
    };

    setLoading(true);
    // Cargar datos iniciales SOLO si el backend está conectado
    fetchAllData();
    
    // NO hacer polling automático - solo actualizar bajo demanda o cuando el usuario interactúa
    // El usuario puede refrescar manualmente o usar un botón de actualización
    // Esto reduce significativamente la carga en el backend
    
    return () => {
      // Cleanup si es necesario
    };
  }, [user, stackApp, isConnected]); // Agregar isConnected como dependencia
  
  // Función para refrescar datos manualmente
  const refreshData = async () => {
    if (!user || !isConnected) return;
    
    const api = initApiClient(createTokenGetter(user, stackApp));
    try {
      const [dashboard, status, positionsData, risk] = await Promise.all([
        api.get<DashboardData>('/dashboard').catch(() => PLACEHOLDER_DASHBOARD),
        api.get<LiveStatus>('/live/status').catch(() => null),
        api.get<Position[]>('/positions').catch(() => []),
        api.get<RiskConfig>('/risk/config').catch(() => PLACEHOLDER_RISK),
      ]);
      
      setDashboardData(dashboard);
      setLiveStatus(status);
      setPositions(positionsData);
      setRiskConfig(risk);
      
      if (status?.recent_decisions && status.recent_decisions.length > 0) {
        const timelineItems = status.recent_decisions.slice(0, 5).map(dec => ({
          time: new Date(dec.timestamp).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          event: `${dec.component}: ${dec.decision}${dec.reason ? ` - ${dec.reason}` : ''}`,
          component: dec.component,
        }));
        setTimeline(timelineItems);
      } else {
        setTimeline([]);
      }
    } catch (err) {
      console.error('Error refreshing data:', err);
    }
  };

  const toggleSystem = async () => {
    if (!user || isToggling || !isConnected) return;
    
    setIsToggling(true);
    // Obtener el estado actual antes del try para usarlo en el catch
    const currentState = dashboardData?.system_active ?? false;
    
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      
      if (currentState) {
        await api.post('/control/pause');
      } else {
        await api.post('/control/resume');
      }
      
      const updated = await api.get<DashboardData>('/dashboard');
      setDashboardData(updated);
    } catch (err) {
      console.error('Error toggling system:', err);
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido';
      alert(`Error al ${currentState ? 'pausar' : 'iniciar'} el sistema: ${errorMessage}`);
      if (dashboardData) {
        setDashboardData({ ...dashboardData, system_active: !dashboardData.system_active });
      }
    } finally {
      setIsToggling(false);
    }
  };

  const handleToggleMarket = async (marketId: string, currentEnabled: boolean) => {
    if (!user || !isConnected || togglingMarket) return;
    
    setTogglingMarket(marketId);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.patch(`/markets/${marketId}/enable`, { enabled: !currentEnabled });
      
      // Refresh live status
      const status = await api.get<LiveStatus>('/live/status');
      setLiveStatus(status);
    } catch (err) {
      console.error('Error toggling market:', err);
    } finally {
      setTogglingMarket(null);
    }
  };

  const handleChangeExecutionMode = async (newMode: 'DRY_RUN' | 'PAPER' | 'LIVE') => {
    if (!user || !isConnected || changingMode) return;
    
    // Si el modo actual es el mismo, no hacer nada
    if (displayLiveStatus.bot_status.execution_mode === newMode) {
      return;
    }
    
    // Para LIVE, siempre pedir confirmación
    if (newMode === 'LIVE') {
      setShowModeConfirm('LIVE');
      return;
    }
    
    // Para DRY_RUN y PAPER, cambiar directamente pero con confirmación si viene de LIVE
    if (displayLiveStatus.bot_status.execution_mode === 'LIVE' && (newMode === 'DRY_RUN' || newMode === 'PAPER')) {
      if (!confirm(`¿Cambiar de LIVE a ${newMode}? Esto detendrá el trading real.`)) {
        return;
      }
    }
    
    setChangingMode(true);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.post(`/live/status/execution-mode?mode=${newMode}`);
      
      // Refresh status
      const status = await api.get<LiveStatus>('/live/status');
      setLiveStatus(status);
      setShowModeConfirm(null);
      
      // Mostrar mensaje de éxito
      console.log(`Modo de ejecución cambiado a ${newMode}`);
    } catch (err) {
      console.error('Error changing execution mode:', err);
      alert(`Error al cambiar el modo de ejecución: ${err instanceof Error ? err.message : 'Error desconocido'}`);
    } finally {
      setChangingMode(false);
    }
  };

  const handleCancelAllOrders = async () => {
    if (!user || !isConnected) return;
    
    if (!confirm('¿Cancelar todas las órdenes pendientes?')) return;
    
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.post('/live/status/cancel-all-orders');
      alert('Todas las órdenes han sido canceladas');
    } catch (err) {
      console.error('Error cancelling orders:', err);
      alert('Error al cancelar órdenes');
    }
  };

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner text="Cargando estado del bot..." />
      </Layout>
    );
  }

  // Usar placeholders si el backend no está disponible
  const displayDashboard = dashboardData || PLACEHOLDER_DASHBOARD;
  const displayLiveStatus = liveStatus || (!isConnected ? PLACEHOLDER_LIVE_STATUS : null);

  // Si estamos conectados pero aún no tenemos datos, mostrar loading
  if (isConnected && !liveStatus && loading) {
    return (
      <Layout>
        <LoadingSpinner text="Cargando estado del bot..." />
      </Layout>
    );
  }

  // Si estamos conectados pero no hay datos después de cargar, mostrar error
  if (isConnected && !liveStatus && !loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <p className="text-sm text-slate-500 mb-2">No se pudo conectar con el backend</p>
            <p className="text-xs text-slate-400">Verifica que el servidor esté ejecutándose</p>
          </div>
        </div>
      </Layout>
    );
  }

  // Asegurar que siempre tengamos displayLiveStatus
  if (!displayLiveStatus) {
    return (
      <Layout>
        <LoadingSpinner text="Cargando estado del bot..." />
      </Layout>
    );
  }

  const totalPnL = displayDashboard.realized_pnl + displayDashboard.unrealized_pnl;
  const isActive = displayDashboard.system_active;
  const totalUnrealizedPnL = positions.reduce((sum, pos) => sum + pos.unrealized_pnl, 0);
  const globalExposurePct = riskConfig ? (displayDashboard.global_exposure / riskConfig.max_global_exposure * 100) : 0;

  return (
    <Layout>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-medium text-slate-900">Live Control</h1>
          <div className="flex items-center gap-3">
            {isConnected && (
              <button
                onClick={refreshData}
                className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-md hover:bg-slate-50 hover:border-slate-300 hover:shadow-sm active:scale-[0.98] transition-all duration-150 cursor-pointer"
                title="Actualizar datos"
              >
                ↻ Actualizar
              </button>
            )}
            {!isConnected && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-slate-200 bg-slate-50">
                <div className="w-1.5 h-1.5 rounded-full bg-slate-300"></div>
                <span className="text-xs text-slate-500">Demo</span>
              </div>
            )}
          </div>
        </div>

        {/* 1️⃣ CRÍTICO: Estado Operativo del Bot */}
        <div className="border border-slate-200 rounded-lg p-6 bg-white">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-medium text-slate-900">Control del Bot</h2>
            <div className="flex items-center gap-2.5">
              <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-emerald-500' : 'bg-slate-400'}`}></div>
              <span className="text-sm font-medium text-slate-600">
                {isActive ? 'Activo' : 'Pausado'}
              </span>
            </div>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Control Principal - Botón Grande */}
            <div className="lg:col-span-1 flex items-center justify-center">
              <button
                onClick={toggleSystem}
                disabled={isToggling || !isConnected}
                className={`w-full max-w-xs py-3.5 px-6 rounded-md font-medium text-sm transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed ${
                  isActive
                    ? 'bg-slate-900 text-white hover:bg-slate-800 hover:shadow-md active:scale-[0.98] active:bg-slate-950'
                    : 'bg-slate-900 text-white hover:bg-slate-800 hover:shadow-md active:scale-[0.98] active:bg-slate-950'
                }`}
              >
                {isToggling ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    <span>{isActive ? 'Pausando' : 'Iniciando'}</span>
                  </span>
                ) : (
                  <span className="flex items-center justify-center">
                    {isActive ? 'Pausar' : 'Iniciar'}
                  </span>
                )}
              </button>
            </div>

            {/* Modo de Ejecución */}
            <div className="lg:col-span-1">
              <label className="block text-xs font-medium text-slate-500 mb-2.5 uppercase tracking-wide">
                Modo de Ejecución
              </label>
              {isConnected ? (
                <div className="relative">
                  <select
                    value={displayLiveStatus.bot_status.execution_mode}
                    onChange={(e) => handleChangeExecutionMode(e.target.value as 'DRY_RUN' | 'PAPER' | 'LIVE')}
                    disabled={changingMode}
                    className={`w-full py-2.5 px-3.5 rounded-md text-sm font-medium border transition-all duration-150 appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-1 ${
                      displayLiveStatus.bot_status.execution_mode === 'DRY_RUN' 
                        ? 'bg-white border-slate-300 text-slate-700' :
                      displayLiveStatus.bot_status.execution_mode === 'PAPER' 
                        ? 'bg-white border-slate-300 text-slate-700' :
                      'bg-white border-slate-300 text-slate-700'
                    } ${changingMode ? 'opacity-50 cursor-wait' : 'hover:border-slate-400 hover:shadow-sm active:scale-[0.98]'}`}
                  >
                    <option value="DRY_RUN">DRY_RUN</option>
                    <option value="PAPER">PAPER</option>
                    <option value="LIVE">LIVE</option>
                  </select>
                  {changingMode && (
                    <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                      <span className="w-3.5 h-3.5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin"></span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="w-full py-2.5 px-3.5 rounded-md text-sm font-medium border border-slate-200 bg-slate-50 text-slate-500">
                  {displayLiveStatus.bot_status.execution_mode}
                </div>
              )}
            </div>

            {/* Última Decisión y Acción */}
            <div className="lg:col-span-1 space-y-4">
              <div>
                <div className="text-xs font-medium text-slate-500 mb-2 uppercase tracking-wide">Última Decisión</div>
                {displayLiveStatus.bot_status.last_decision ? (
                  <div className="p-3 rounded-md bg-slate-50 border border-slate-200">
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <span className={`text-xs font-medium ${
                        displayLiveStatus.bot_status.last_decision.decision === 'APPROVED' ? 'text-emerald-700' :
                        displayLiveStatus.bot_status.last_decision.decision === 'REJECTED' ? 'text-slate-600' :
                        'text-slate-700'
                      }`}>
                        {displayLiveStatus.bot_status.last_decision.decision}
                      </span>
                      <span className="text-xs text-slate-500 font-normal">
                        {displayLiveStatus.bot_status.last_decision.component}
                      </span>
                    </div>
                    {displayLiveStatus.bot_status.last_decision.reason && (
                      <div className="text-xs text-slate-600 font-normal leading-relaxed">
                        {displayLiveStatus.bot_status.last_decision.reason}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-3 rounded-md bg-slate-50 border border-slate-200 text-xs text-slate-500 font-normal">
                    {!isConnected ? 'Modo demo' : 'Sin decisiones recientes'}
                  </div>
                )}
              </div>
              
              <div>
                <div className="text-xs font-medium text-slate-500 mb-2 uppercase tracking-wide">Última Acción</div>
                <div className="p-3 rounded-md bg-slate-50 border border-slate-200 text-xs text-slate-700 font-normal">
                  {displayLiveStatus.bot_status.last_action?.message || 'Sin acciones recientes'}
                </div>
              </div>
            </div>
          </div>

          {/* Descripción de Modos */}
          <div className="mt-4 p-3 bg-slate-50 rounded border border-slate-200">
            <div className="text-xs font-medium text-slate-900 mb-2">Modos de Ejecución:</div>
            <div className="space-y-1 text-xs text-slate-600">
              <div><strong>DRY_RUN:</strong> {displayLiveStatus.bot_status.execution_mode_description.DRY_RUN}</div>
              <div><strong>PAPER:</strong> {displayLiveStatus.bot_status.execution_mode_description.PAPER}</div>
              <div><strong>LIVE:</strong> {displayLiveStatus.bot_status.execution_mode_description.LIVE}</div>
            </div>
          </div>
        </div>

        {/* Confirmación de cambio a LIVE */}
        {showModeConfirm === 'LIVE' && (
          <div className="border-2 border-red-400 rounded-lg p-4 bg-red-50 shadow-lg">
            <div className="flex items-start gap-3">
              <div className="text-2xl">⚠️</div>
              <div className="flex-1">
                <div className="text-sm font-bold text-red-900 mb-2">Confirmar cambio a modo LIVE</div>
                <div className="text-xs text-red-800 mb-1">
                  <strong>ADVERTENCIA:</strong> El modo LIVE ejecuta órdenes reales con dinero real en Polymarket.
                </div>
                <div className="text-xs text-red-700 mb-4 space-y-1">
                  <div>• Las órdenes se enviarán y ejecutarán realmente</div>
                  <div>• Se utilizará dinero real de tu cuenta</div>
                  <div>• Los resultados son permanentes e irreversibles</div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={async () => {
                      setChangingMode(true);
                      try {
                        await handleChangeExecutionMode('LIVE');
                        setShowModeConfirm(null);
                      } catch (err) {
                        console.error('Error changing to LIVE mode:', err);
                        alert('Error al cambiar a modo LIVE. Por favor, intenta de nuevo.');
                      } finally {
                        setChangingMode(false);
                      }
                    }}
                    disabled={changingMode}
                    className="px-4 py-2 text-xs font-bold rounded-md bg-red-600 text-white hover:bg-red-700 hover:shadow-md active:scale-[0.98] transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                  >
                    {changingMode ? 'Cambiando...' : 'SÍ, cambiar a LIVE'}
                  </button>
                  <button
                    onClick={() => setShowModeConfirm(null)}
                    disabled={changingMode}
                    className="px-4 py-2 text-xs font-medium rounded-md bg-white border border-red-300 text-red-700 hover:bg-red-50 hover:border-red-400 hover:shadow-sm active:scale-[0.98] transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Grid Principal */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Columna Izquierda: Métricas y Markets */}
          <div className="lg:col-span-2 space-y-4">
            {/* Métricas Rápidas */}
            <div className="grid grid-cols-3 gap-3">
              <div className="border border-slate-200 rounded-lg p-3 bg-white hover:border-slate-300 hover:shadow-sm transition-all duration-150">
                <div className="text-xs text-slate-500 mb-0.5 font-medium">Balance</div>
                <div className="text-base font-semibold text-slate-900">
                  ${Number(displayDashboard.equity.toFixed(2)).toLocaleString('es-ES', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </div>
              </div>
              <div className="border border-slate-200 rounded-lg p-3 bg-white hover:border-slate-300 hover:shadow-sm transition-all duration-150">
                <div className="text-xs text-slate-500 mb-0.5 font-medium">PnL Total</div>
                <div className={`text-base font-semibold ${totalPnL >= 0 ? 'text-slate-900' : 'text-red-600'}`}>
                  {totalPnL >= 0 ? '+' : ''}${totalPnL.toLocaleString('es-ES', {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 0,
                  })}
                </div>
              </div>
              <div className="border border-slate-200 rounded-lg p-3 bg-white hover:border-slate-300 hover:shadow-sm transition-all duration-150">
                <div className="text-xs text-slate-500 mb-0.5 font-medium">Exposición</div>
                <div className="text-base font-semibold text-slate-900">
                  ${displayDashboard.global_exposure.toLocaleString('es-ES', {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 0,
                  })}
                </div>
              </div>
            </div>

            {/* 2️⃣ CRÍTICO: Markets Activos */}
            <div className="border border-slate-200 rounded-lg p-4 bg-white shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-medium text-slate-900">
                  Markets Activos ({displayLiveStatus.active_markets.length} / {riskConfig?.max_markets_active || 30})
                </h2>
              </div>
              
              {displayLiveStatus.active_markets.length === 0 ? (
                <div className="text-xs text-slate-500 text-center py-4">
                  {!isConnected ? 'Modo demo - Backend no disponible' : 'No hay markets activos'}
                </div>
              ) : (
                <div className="space-y-2">
                  {displayLiveStatus.active_markets.map((market) => (
                    <div
                      key={market.market_id}
                      className="flex items-center justify-between p-2 rounded-md border border-slate-200 hover:bg-slate-50 hover:border-slate-300 hover:shadow-sm transition-all duration-150"
                    >
                      <div className="flex-1">
                        <div className="text-xs font-medium text-slate-900">{market.name}</div>
                        {market.series_name && (
                          <div className="text-xs text-slate-500">{market.series_name}</div>
                        )}
                        <div className="text-xs text-slate-400 mt-0.5">
                          {market.active_events_count} events activos de {market.events_count} total
                        </div>
                      </div>
                      <button
                        onClick={() => handleToggleMarket(market.market_id, market.enabled)}
                        disabled={!isConnected || togglingMarket === market.market_id}
                        className={`px-2 py-1 text-xs font-medium rounded transition-all duration-150 ${
                          market.enabled
                            ? 'bg-slate-200 text-slate-700 hover:bg-slate-300 hover:shadow-sm active:scale-[0.95]'
                            : 'bg-slate-900 text-white hover:bg-slate-800 hover:shadow-md active:scale-[0.95]'
                        } disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer`}
                      >
                        {togglingMarket === market.market_id ? '...' : market.enabled ? 'ON' : 'OFF'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 3️⃣ CRÍTICO: Events Activos Ahora Mismo */}
            <div className="border border-slate-200 rounded-lg p-4 bg-white shadow-sm">
              <h2 className="text-sm font-medium text-slate-900 mb-3">Events Activos</h2>
              
              {displayLiveStatus.active_events.length === 0 ? (
                <div className="text-xs text-slate-500 text-center py-4">
                  {!isConnected ? 'Modo demo - Backend no disponible' : 'No hay events activos'}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-slate-600">Market</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-slate-600">Event</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-slate-600">Estado</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-slate-600">Fin</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-slate-600">Liquidez</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {displayLiveStatus.active_events.map((event) => (
                        <tr key={event.event_id} className="hover:bg-slate-50">
                          <td className="px-3 py-2 text-xs text-slate-900">{event.market_name}</td>
                          <td className="px-3 py-2 text-xs text-slate-600">
                            {new Date(event.start_time).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })} - {new Date(event.end_time).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                          </td>
                          <td className="px-3 py-2">
                            <span className={`text-xs px-1.5 py-0.5 rounded border ${
                              event.state === 'ACTIVE'
                                ? 'bg-green-100 text-green-700 border-green-200'
                                : event.state === 'UPCOMING'
                                ? 'bg-blue-100 text-blue-700 border-blue-200'
                                : 'bg-slate-100 text-slate-600 border-slate-200'
                            }`}>
                              {event.state}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-xs text-slate-600">
                            {new Date(event.end_time).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                          </td>
                          <td className="px-3 py-2 text-xs text-slate-600">
                            {event.liquidity ? `$${(event.liquidity / 1000).toFixed(0)}k` : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Columna Derecha: Riesgo, Decisiones, Health */}
          <div className="space-y-4">
            {/* 3️⃣ CRÍTICO: Riesgo Dinámico con Alertas */}
            <div className="border border-slate-200 rounded-lg p-4 bg-white shadow-sm">
              <h2 className="text-sm font-medium text-slate-900 mb-3">Riesgo</h2>
              
              {/* Exposición Global con Barra */}
              {riskConfig && (
                <div className="mb-3">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-500">Exposición Global</span>
                    <span className={`font-medium ${
                      globalExposurePct >= 90 ? 'text-red-600' :
                      globalExposurePct >= 75 ? 'text-yellow-600' :
                      'text-slate-900'
                    }`}>
                      {globalExposurePct.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        globalExposurePct >= 90 ? 'bg-red-500' :
                        globalExposurePct >= 75 ? 'bg-yellow-500' :
                        'bg-green-500'
                      }`}
                      style={{ width: `${Math.min(globalExposurePct, 100)}%` }}
                    ></div>
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    ${(dashboardData.global_exposure / 1000).toFixed(0)}k / ${(riskConfig.max_global_exposure / 1000).toFixed(0)}k
                  </div>
                </div>
              )}

              {/* Alertas de Riesgo */}
              {displayLiveStatus.risk_alerts.length > 0 && (
                <div className="space-y-2">
                  {displayLiveStatus.risk_alerts.map((alert, idx) => (
                    <div
                      key={idx}
                      className={`p-2 rounded border text-xs ${
                        alert.severity === 'critical'
                          ? 'bg-red-50 border-red-200 text-red-800'
                          : 'bg-yellow-50 border-yellow-200 text-yellow-800'
                      }`}
                    >
                      <div className="font-medium">⚠️ {alert.message}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Límites */}
              {riskConfig && (
                <div className="mt-3 space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Mercados activos:</span>
                    <span className="text-slate-900 font-medium">
                      {displayDashboard.active_markets} / {riskConfig.max_markets_active}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Exp. por mercado:</span>
                    <span className="text-slate-900 font-medium">
                      ${(riskConfig.max_exposure_per_market / 1000).toFixed(0)}k
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* 4️⃣ MUY IMPORTANTE: Últimas Decisiones */}
            <div className="border border-slate-200 rounded-lg p-4 bg-white shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-medium text-slate-900">Últimas Decisiones</h2>
                <Link
                  href="/decision-traces"
                  className="text-xs text-slate-600 hover:text-slate-900"
                >
                  Ver todas →
                </Link>
              </div>
              
              {displayLiveStatus.recent_decisions.length === 0 ? (
                <div className="text-xs text-slate-500 text-center py-4">
                  {!isConnected ? 'Modo demo - Backend no disponible' : 'Sin decisiones recientes'}
                </div>
              ) : (
                <div className="space-y-2">
                  {displayLiveStatus.recent_decisions.slice(0, 5).map((decision, idx) => (
                    <div
                      key={idx}
                      className="p-2 rounded border border-slate-200 hover:bg-slate-50 cursor-pointer"
                      onClick={() => {
                        if (decision.trace_id) {
                          window.open(`/decision-traces?trace_id=${decision.trace_id}`, '_blank');
                        }
                      }}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-slate-900">
                          {new Date(decision.timestamp).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          decision.decision === 'APPROVED' ? 'bg-green-100 text-green-700' :
                          decision.decision === 'REJECTED' ? 'bg-red-100 text-red-700' :
                          'bg-slate-100 text-slate-700'
                        }`}>
                          {decision.decision}
                        </span>
                      </div>
                      <div className="text-xs text-slate-600">
                        {decision.component}
                      </div>
                      {decision.reason && (
                        <div className="text-xs text-slate-500 mt-0.5">
                          {decision.reason}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 5️⃣ IMPORTANTE: System Health */}
            <div className="border border-slate-200 rounded-lg p-4 bg-white shadow-sm">
              <h2 className="text-sm font-medium text-slate-900 mb-3">System Health</h2>
              
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Latencia:</span>
                  <span className={`font-medium px-2 py-0.5 rounded ${
                    displayLiveStatus.system_health.latency_status === 'GREEN' ? 'bg-green-100 text-green-700' :
                    displayLiveStatus.system_health.latency_status === 'YELLOW' ? 'bg-yellow-100 text-yellow-700' :
                    displayLiveStatus.system_health.latency_status === 'UNKNOWN' ? 'bg-slate-100 text-slate-600' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {displayLiveStatus.system_health.latency_status}
                  </span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Checkers activos:</span>
                  <span className="text-slate-900 font-medium">
                    {displayLiveStatus.system_health.checkers_active} / {displayLiveStatus.system_health.checkers_total}
                  </span>
                </div>
                
                {displayLiveStatus.system_health.last_checker_failure && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Último fallo:</span>
                    <span className="text-xs text-slate-600">
                      {new Date(displayLiveStatus.system_health.last_checker_failure).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                )}
                
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Scanner:</span>
                  <span className={`font-medium ${
                    displayLiveStatus.system_health.scanner_status === 'OK' ? 'text-green-700' :
                    displayLiveStatus.system_health.scanner_status === 'DELAYED' ? 'text-yellow-700' :
                    displayLiveStatus.system_health.scanner_status === 'UNKNOWN' ? 'text-slate-600' :
                    'text-red-700'
                  }`}>
                    {displayLiveStatus.system_health.scanner_status}
                  </span>
                </div>
              </div>
            </div>

            {/* 6️⃣ IMPORTANTE: Acciones Rápidas */}
            <div className="border border-slate-200 rounded-lg p-4 bg-white shadow-sm">
              <h2 className="text-sm font-medium text-slate-900 mb-3">Acciones Rápidas</h2>
              
              <div className="space-y-2">
                <button
                  onClick={handleCancelAllOrders}
                  disabled={!isConnected}
                  className="w-full px-3 py-2 text-xs font-medium rounded-md border border-red-300 text-red-700 hover:bg-red-50 hover:border-red-400 hover:shadow-sm active:scale-[0.98] transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                >
                  Cancelar Todas las Órdenes
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* 7️⃣ NICE TO HAVE: Timeline / Actividad Reciente */}
        {timeline.length > 0 && (
          <div className="border border-slate-200 rounded-lg p-4 bg-white shadow-sm">
            <h2 className="text-sm font-medium text-slate-900 mb-3">Actividad Reciente</h2>
            <div className="space-y-1">
              {timeline.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2 text-xs text-slate-600">
                  <span className="text-slate-400 font-mono">{item.time}</span>
                  <span className="text-slate-500">•</span>
                  <span>{item.event}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Positions Table */}
        <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
          <div className="p-3 border-b border-slate-200">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-medium text-slate-900">
                Posiciones ({positions.filter(p => !p.resolved).length})
              </h2>
              <div className="text-xs text-slate-500">
                PnL pendiente: <span className={`font-medium ${totalUnrealizedPnL >= 0 ? 'text-slate-900' : 'text-slate-600'}`}>
                  {totalUnrealizedPnL >= 0 ? '+' : ''}${totalUnrealizedPnL.toLocaleString('es-ES', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </span>
              </div>
            </div>
          </div>
          {positions.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-xs text-slate-500">No hay posiciones abiertas</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Mercado</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Tamaño</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Precio Prom.</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Precio Actual</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">PnL</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {positions.map((position) => (
                    <tr key={position.market_id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="text-xs text-slate-900">{position.question}</div>
                        <div className="text-xs text-slate-400 mt-0.5">{position.market_id.substring(0, 8)}...</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-600">
                        {position.size.toFixed(4)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-700">
                        ${position.avg_price.toFixed(4)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs font-medium text-slate-900">
                        ${position.current_price.toFixed(4)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`text-xs font-medium ${
                          position.unrealized_pnl >= 0 ? 'text-slate-900' : 'text-slate-600'
                        }`}>
                          {position.unrealized_pnl >= 0 ? '+' : ''}${position.unrealized_pnl.toLocaleString('es-ES', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-xs text-slate-500 px-1.5 py-0.5 rounded border border-slate-200 bg-slate-50">
                          {position.resolved ? 'Resuelto' : 'Activo'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
