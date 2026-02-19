'use client';

import { useEffect, useState } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { useParams, useRouter } from 'next/navigation';
import { Layout } from '@/components/Layout';
import { initApiClient, createTokenGetter, ApiResponseError, WALLET_NOT_CONFIGURED_STATUS } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
import { useRealtimeStrategy } from '@/hooks/useRealtimeStrategy';
import { Strategy } from '@/types/strategy';
import { Badge } from '@/components/ui/badge';
import { StrategyHeaderWithLoader } from '@/components/strategy/StrategyHeaderWithLoader';
import { LiveKPIStrip } from '@/components/strategy/LiveKPIStrip';
import { StrategyInfo } from '@/components/strategy/StrategyInfo';
import { PositionsTable } from '@/components/strategy/PositionsTable';
import { StrategySystemHealth } from '@/components/strategy/StrategySystemHealth';
import { IntentsTableWithLoader } from '@/components/strategy/IntentsTableWithLoader';
import { ExternalConfirmationStatus } from '@/components/strategy/ExternalConfirmationStatus';
import { EventPipeline } from '@/components/strategy/EventPipeline';
import { RiskMonitor } from '@/components/strategy/RiskMonitor';
import { ActivityLog } from '@/components/strategy/ActivityLog';
import { SignalsMonitor } from '@/components/strategy/SignalsMonitor';
import { TipsPipelineCompact } from '@/components/strategy/tipster/TipsPipelineCompact';
import { SurebetHeader } from '@/components/strategy/surebet/SurebetHeader';
import { DualVenueHealth } from '@/components/strategy/surebet/DualVenueHealth';
import { LiveArbitrageSnapshot } from '@/components/strategy/surebet/LiveArbitrageSnapshot';
import { ExecutionPipeline } from '@/components/strategy/surebet/ExecutionPipeline';
import { OpenExposure } from '@/components/strategy/surebet/OpenExposure';
import { CapitalLimitsMonitor } from '@/components/strategy/surebet/CapitalLimitsMonitor';
import { ProfitEfficiencyMetrics } from '@/components/strategy/surebet/ProfitEfficiencyMetrics';
import { EventLevelControls } from '@/components/strategy/surebet/EventLevelControls';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertBannerStack, type AlertBannerItem } from '@/components/strategy/AlertBannerStack';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle } from 'lucide-react';
import Link from 'next/link';

type LiveStatusPayload = { status: any; metrics: any; recent_plans: any[]; orderbook_health: any };

export default function StrategyLivePage() {
  const user = useUser();
  const stackApp = useStackApp();
  const params = useParams();
  const router = useRouter();
  const { isConnected } = useBackendConnection();

  const strategyId = params.id as string;
  const { isDemo, isSimulation } = useDataMode();
  const [isActivating, setIsActivating] = useState(false);
  const [controlError, setControlError] = useState<string | null>(null);
  const [activateSuccessMessage, setActivateSuccessMessage] = useState<string | null>(null);

  const getControlErrorMessage = (err: unknown): string => {
    if (err instanceof ApiResponseError) {
      const statusLabel =
        err.statusCode === 403
          ? 'No autorizado (403)'
          : err.statusCode === 404
            ? 'Estrategia no encontrada (404)'
            : err.statusCode === 400
              ? 'Solicitud incorrecta (400)'
              : `Error ${err.statusCode}`;
      return err.message ? `${statusLabel}: ${err.message}` : statusLabel;
    }
    return err instanceof Error ? err.message : 'Error de conexión';
  };

  // Use realtime hook for intents and metrics
  const { 
    intents: realtimeIntents, 
    metrics: realtimeMetrics, 
    isConnected: wsConnected,
    lastUpdate,
  } = useRealtimeStrategy(strategyId);
  
  // Strategy state (se carga en StrategyHeaderWithLoader)
  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [isSurebetStrategy, setIsSurebetStrategy] = useState(false);
  const [isTipsterStrategy, setIsTipsterStrategy] = useState(false);
  const [executionMode, setExecutionMode] = useState<string>('DRY_RUN');
  const [strategyEventsCount, setStrategyEventsCount] = useState<number>(0);
  
  // Use realtime data if available
  const currentIntents = realtimeIntents.length > 0 ? realtimeIntents : [];

  const handlePause = async () => {
    if (!strategy || isActivating) return;
    if (isDemo) {
      setStrategy((prev) =>
        prev ? { ...prev, is_active: false, enabled_at: null } : null
      );
      return;
    }
    setIsActivating(true);
    setControlError(null);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      const updatedStrategy = await api.post<Strategy>(`/api/strategies/${strategyId}/deactivate`);
      setStrategy(updatedStrategy);
    } catch (err) {
      console.error('Error pausing strategy:', err);
      setControlError(getControlErrorMessage(err));
    } finally {
      setIsActivating(false);
    }
  };

  const handleStop = async () => {
    if (!strategy || isActivating) return;
    if (isDemo) {
      setStrategy((prev) =>
        prev
          ? { ...prev, is_active: false, enabled_at: null, disabled_at: new Date().toISOString() }
          : null
      );
      return;
    }
    setIsActivating(true);
    setControlError(null);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      const updatedStrategy = await api.post<Strategy>(`/api/strategies/${strategyId}/deactivate`);
      if (updatedStrategy) setStrategy({ ...updatedStrategy, disabled_at: new Date().toISOString() });
    } catch (err) {
      console.error('Error stopping strategy:', err);
      setControlError(getControlErrorMessage(err));
    } finally {
      setIsActivating(false);
    }
  };

  const handleActivate = async () => {
    if (!strategy || isActivating) return;
    if (isDemo) {
      setStrategy((prev) =>
        prev
          ? {
              ...prev,
              is_active: true,
              enabled_at: new Date().toISOString(),
              disabled_at: undefined,
            }
          : null
      );
      return;
    }
    if (isSimulation && executionMode === 'LIVE') {
      setControlError(
        'El backend está en modo LIVE. Para simulación, elige "Simulación" en el selector del header y vuelve a intentar.'
      );
      return;
    }
    setIsActivating(true);
    setControlError(null);
    setActivateSuccessMessage(null);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      const updatedStrategy = await api.post<Strategy>(`/api/strategies/${strategyId}/activate`);
      setStrategy(updatedStrategy);
      if (executionMode === 'DRY_RUN') {
        setActivateSuccessMessage('Estrategia activada en modo simulación (DRY_RUN). No se envían órdenes reales.');
        setTimeout(() => setActivateSuccessMessage(null), 5000);
      }
    } catch (err) {
      console.error('Error activating strategy:', err);
      setControlError(getControlErrorMessage(err));
    } finally {
      setIsActivating(false);
    }
  };

  // Fetch positions from backend using strategy-specific endpoint
  const [positions, setPositions] = useState<any[]>([]);
  
  useEffect(() => {
    if (!user || !strategyId) return;
    if (isDemo) {
      setPositions([]);
      return;
    }
    if (!isConnected) return;

    const api = initApiClient(createTokenGetter(user, stackApp));
    
    const fetchPositions = async () => {
      try {
        const response = await api.get<{ positions: any[] }>(`/api/strategies/${strategyId}/positions`).catch(() => ({ positions: [] }));
        const mappedPositions = ((response?.positions) ?? []).map((pos: any) => ({
          id: pos.position_id || pos.market_id,
          eventName: pos.name || 'Unknown Event',
          marketName: pos.polymarket_id || pos.market_id,
          size: pos.size || 0,
          avgPrice: pos.avg_price || 0,
          pnl: pos.unrealized_pnl || 0,
          currentPrice: pos.current_price || 0,
          status: pos.resolved ? 'pending_close' : 'open' as const,
        }));
        setPositions(mappedPositions);
      } catch (err) {
        console.error('Error fetching positions:', err);
        setPositions([]);
      }
    };
    
    fetchPositions();
    const interval = setInterval(fetchPositions, 5000);
    return () => clearInterval(interval);
  }, [user, stackApp, isConnected, strategyId, isDemo]);

  // Live status data from backend
  const [liveStatus, setLiveStatus] = useState<{
    status: any;
    metrics: any;
    recent_plans: any[];
    orderbook_health: any;
  } | null>(null);
  
  // Executions (Execution Plans) from backend
  const [executions, setExecutions] = useState<any[]>([]);
  
  // Modo de ejecución y eventos asignados
  useEffect(() => {
    if (!user || !strategyId) return;
    if (isDemo) {
      setExecutionMode('DRY_RUN');
      setStrategyEventsCount(0);
      return;
    }
    if (!isConnected) return;
    const api = initApiClient(createTokenGetter(user, stackApp));
    (async () => {
      try {
        const modeRes = await api.get<{ execution_mode?: string }>('/system/config/execution-mode').catch((): { execution_mode?: string } => ({}));
        setExecutionMode(modeRes?.execution_mode ?? 'DRY_RUN');
        const eventsRes = await api.get<{ events?: unknown[] }>(`/api/strategies/${strategyId}/events`).catch(() => ({ events: [] }));
        setStrategyEventsCount(eventsRes?.events?.length ?? 0);
      } catch {
        // ignore
      }
    })();
  }, [user, stackApp, isConnected, strategyId, isDemo]);

  // Scroll a sección cuando la URL tiene hash (#metrics, #logs) para cohesión con botones Métricas/Logs
  useEffect(() => {
    const scrollToHash = () => {
      const hash = typeof window !== 'undefined' ? window.location.hash.slice(1) : '';
      if (hash !== 'metrics' && hash !== 'logs') return;
      const el = document.getElementById(hash);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    const t = setTimeout(scrollToHash, 100);
    return () => clearTimeout(t);
  }, []);
  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash.slice(1);
      if (hash !== 'metrics' && hash !== 'logs') return;
      const el = document.getElementById(hash);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  // Fetch live status and executions from backend
  useEffect(() => {
    if (!user || !strategyId) return;
    if (isDemo) {
      setLiveStatus(null);
      setExecutions([]);
      return;
    }
    if (!isConnected) return;
    
    const api = initApiClient(createTokenGetter(user, stackApp));
    
    const fetchLiveStatus = async () => {
      try {
        const statusData = await api.get<LiveStatusPayload>(`/api/strategies/${strategyId}/live-status`).catch(() => null);
        if (statusData) {
          setLiveStatus(statusData);
          setRiskData(prev => ({
            ...prev,
            currentExposure: statusData.metrics?.total_exposure_usdc || 0,
            maxExposure: strategy?.risk_config?.max_exposure || 5000,
            capitalUsed: statusData.metrics?.total_exposure_usdc || 0,
            capitalAssigned: strategy?.risk_config?.max_exposure || 5000,
            activeEvents: statusData.metrics?.active_orders || 0,
          }));
        }
      } catch (err) {
        console.error('Error fetching live status:', err);
      }
    };
    
    const fetchExecutions = async () => {
      try {
        const response = await api.get<{ executions: any[]; total: number }>(`/api/strategies/${strategyId}/executions?limit=20`).catch(() => ({ executions: [], total: 0 }));
        setExecutions(response?.executions ?? []);
      } catch (err) {
        console.error('Error fetching executions:', err);
        setExecutions([]);
      }
    };
    
    const fetchBalance = async () => {
      try {
        const data = await api.get<{ balance_usdc: number; currency: string }>('/api/polymarket/balance');
        if (data?.balance_usdc != null) {
          setPolymarketBalanceUsdc(data.balance_usdc);
          setWalletNotConfigured(false);
        } else {
          setPolymarketBalanceUsdc(null);
        }
      } catch (e) {
        setPolymarketBalanceUsdc(null);
        setWalletNotConfigured(e instanceof ApiResponseError && e.statusCode === WALLET_NOT_CONFIGURED_STATUS);
      }
    };

    fetchLiveStatus();
    fetchExecutions();
    fetchBalance();
    const liveStatusInterval = setInterval(fetchLiveStatus, 2000);
    const executionsInterval = setInterval(fetchExecutions, 5000);
    const balanceInterval = setInterval(fetchBalance, 60000); // 60s, alineado con caché del backend
    return () => {
      clearInterval(liveStatusInterval);
      clearInterval(executionsInterval);
      clearInterval(balanceInterval);
    };
  }, [user, stackApp, isConnected, strategyId, strategy, isDemo]);
  
  // Fetch checkers status
  const [checkers, setCheckers] = useState<any[]>([]);
  
  // Fetch event pipeline
  const [eventPipeline, setEventPipeline] = useState<any[]>([]);
  
  // Balance USDC de la wallet Polymarket (desde GET /api/polymarket/balance, caché 60s)
  const [polymarketBalanceUsdc, setPolymarketBalanceUsdc] = useState<number | null>(null);
  // Política v2: 409 = usuario sin wallet configurada; mostrar mensaje y enlace a Settings
  const [walletNotConfigured, setWalletNotConfigured] = useState(false);

  // Fetch risk data
  const [riskData, setRiskData] = useState({
    currentExposure: liveStatus?.metrics?.total_exposure_usdc || 0,
    maxExposure: strategy?.risk_config?.max_exposure || 5000,
    capitalUsed: liveStatus?.metrics?.total_exposure_usdc || 0,
    capitalAssigned: strategy?.risk_config?.max_exposure || 5000,
    activeEvents: liveStatus?.metrics?.active_orders || 0,
    alerts: [] as Array<{ id: string; type: 'warning' | 'critical'; message: string }>,
  });
  
  // Fetch activity logs
  const [activityLogs, setActivityLogs] = useState<any[]>([]);
  
  // Fetch connections and events from backend
  const [connections, setConnections] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);

  // Surebet-specific data
  const [globalStatus, setGlobalStatus] = useState<'in_sync' | 'latency_risk' | 'execution_halted'>('in_sync');
  const [venueAHealth, setVenueAHealth] = useState<any>(null);
  const [venueBHealth, setVenueBHealth] = useState<any>(null);
  const [arbitrageOpportunities, setArbitrageOpportunities] = useState<any[]>([]);
  const [executionPipeline, setExecutionPipeline] = useState<any[]>([]);
  const [openExposures, setOpenExposures] = useState<any[]>([]);
  const [capitalLimitsAlerts, setCapitalLimitsAlerts] = useState<any[]>([]);
  const [profitMetrics, setProfitMetrics] = useState<any>(null);
  const [eventControls, setEventControls] = useState<any[]>([]);
  const [riskAlerts, setRiskAlerts] = useState<any[]>([]);
  
  // Reset demo state in a separate effect to avoid dependency loops (riskData was causing re-runs)
  useEffect(() => {
    if (!isDemo || !strategy) return;
    setConnections([]);
    setEvents([]);
    setCheckers([]);
    setEventPipeline([]);
    setActivityLogs([]);
    setPolymarketBalanceUsdc(null);
    setRiskData({
      currentExposure: 0,
      maxExposure: strategy?.risk_config?.max_exposure || 5000,
      capitalUsed: 0,
      capitalAssigned: strategy?.risk_config?.max_exposure || 5000,
      activeEvents: 0,
      alerts: [],
    });
    setWalletNotConfigured(false);
  }, [isDemo, strategy?.id]);

  useEffect(() => {
    if (!user || !strategyId || !strategy) return;
    if (isDemo) return;
    const api = initApiClient(createTokenGetter(user, stackApp));
    
    const fetchSystemHealth = async () => {
      try {
        // Get system health data
        const healthData = await api.get<any>('/metrics/system/health').catch(() => null);
        
        // Map connections (this is a placeholder - actual implementation depends on backend)
        const mappedConnections = [
          {
            name: 'Polymarket (Ejecución)',
            status: healthData?.checkers?.status === 'ok' ? 'ok' as const : 'degraded' as const,
            latency: healthData?.execution_latency_ms?.p95 || 45,
            lastUpdate: '2m ago',
            type: 'execution' as const,
          },
          {
            name: 'Support Graph API',
            status: 'ok' as const,
            latency: 120,
            lastUpdate: '10s ago',
            type: 'data' as const,
          },
        ];
        
        setConnections(mappedConnections);
        
        // Map events from intents and executions
        const intentsToUse = realtimeIntents.length > 0 ? realtimeIntents : [];
        const mappedEvents = intentsToUse.slice(0, 5).map((intent, index) => ({
          time: intent.created_at 
            ? `${Math.floor((Date.now() - new Date(intent.created_at).getTime()) / 60000)}m ago`
            : `${index * 3}m ago`,
          message: intent.status === 'EXECUTED' 
            ? `Orden ejecutada $${intent.size_usdc?.toLocaleString() || '0'} @ ${intent.target_price?.toFixed(2) || '0.00'}`
            : intent.status === 'APPROVED'
            ? 'Intent generado - Aprobado por Risk Engine'
            : 'Intent generado',
          type: intent.status === 'EXECUTED' ? 'execution' as const : 'decision_graph' as const,
          traceId: intent.trace_id,
        }));
        
        setEvents(mappedEvents);

        // Fetch checkers status
        let mappedCheckers: Array<{
          id: string;
          name: string;
          source: string;
          lastUpdate: string;
          latency: number;
          status: 'confirmed' | 'pending' | 'delayed' | 'error';
          delay: number;
        }> = [];
        try {
          const checkersData = await api.get<any>('/checkers/status').catch(() => null);
          // El endpoint devuelve { checkers: {...}, timestamp: ... }
          const checkersObj = checkersData?.checkers || {};
          mappedCheckers = Object.entries(checkersObj).map(([checkerId, checkerData]: [string, any]) => ({
            id: checkerId,
            name: checkerId,
            source: checkerData.source || 'Unknown',
            lastUpdate: checkerData.last_update || 'N/A',
            latency: checkerData.latency_p95 || 0,
            status: checkerData.error_count > 0 ? 'error' : 'confirmed',
            delay: checkerData.delay_seconds || 0,
          }));
          setCheckers(mappedCheckers);
        } catch (e) {
          console.warn('Error loading checkers status:', e);
          setCheckers([]);
        }

        // Fetch event pipeline
        const pipelineData = await api.get<any>('/api/strategies/' + strategyId + '/events/pipeline').catch(() => null);
        const pipelineArray = Array.isArray(pipelineData) ? pipelineData : (pipelineData?.events || pipelineData?.data || []);
        const mappedPipeline = pipelineArray.map((event: any) => ({
          id: event.id,
          eventName: event.name || 'Unknown Event',
          marketName: event.market_id || 'Unknown Market',
          currentPrice: event.current_price || 0,
          status: (event.status || 'waiting_for_result') as 'waiting_for_result' | string,
          exposure: event.exposure || 0,
          estimatedPnL: event.estimated_pnl || 0,
          timeToResolution: event.time_to_resolution_minutes,
        }));
        setEventPipeline(mappedPipeline);

        // Calculate risk data
        const totalExposure = positions.reduce((sum, pos) => sum + pos.size, 0);
        const activeEventsCount = mappedPipeline.length;
        const alerts: Array<{ id: string; type: 'warning' | 'critical'; message: string }> = [];
        
        const exposurePercent = (totalExposure / (strategy.risk_config?.max_exposure || 5000)) * 100;
        if (exposurePercent >= 90) {
          alerts.push({
            id: 'high-exposure',
            type: 'critical',
            message: `Exposición aproximándose al límite máximo (${exposurePercent.toFixed(1)}%)`,
          });
        } else if (exposurePercent >= 75) {
          alerts.push({
            id: 'high-exposure-warning',
            type: 'warning',
            message: `Exposición alta (${exposurePercent.toFixed(1)}%)`,
          });
        }

        // Check for checker delays
        mappedCheckers.forEach((checker: any) => {
          if (checker.status === 'delayed' && checker.delay && checker.delay > 5) {
            alerts.push({
              id: `checker-delay-${checker.id}`,
              type: 'warning',
              message: `Delay detectado en ${checker.name}: ${checker.delay}s`,
            });
          }
        });

        setRiskData({
          currentExposure: totalExposure,
          maxExposure: strategy.risk_config?.max_exposure || 5000,
          capitalUsed: totalExposure,
          capitalAssigned: strategy.risk_config?.max_exposure || 5000,
          activeEvents: activeEventsCount,
          alerts,
        });

        // Fetch activity logs (backend GET /api/strategies/:id/logs devuelve array de { id, timestamp, level, message })
        const logsRaw = await api.get<unknown>('/api/strategies/' + strategyId + '/logs?limit=20').catch(() => []);
        const logsList = Array.isArray(logsRaw) ? logsRaw : [];
        const mappedLogs = logsList.map((log: any) => {
          const ts = log.timestamp ? new Date(log.timestamp).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : new Date().toLocaleTimeString('es-ES');
          return {
            id: log.id ?? String(Math.random()),
            timestamp: ts,
            type: log.level === 'error' ? 'ERROR' as const :
                   log.level === 'warning' ? 'WARNING' as const : 'INFO' as const,
            message: log.message || 'Sin mensaje',
          };
        });
        setActivityLogs(mappedLogs);

        // Fetch surebet-specific data if this is a surebet strategy
        if (isSurebetStrategy && strategy) {
          // Fetch dual venue health
          const venueHealthData = await api.get<any>('/api/strategies/' + strategyId + '/venue-health').catch(() => null);
          if (venueHealthData) {
            setVenueAHealth({
              venue: 'polymarket' as const,
              name: 'Polymarket',
              status: venueHealthData.polymarket?.status || 'connected' as const,
              latency: venueHealthData.polymarket?.latency_ms,
              lastPriceUpdate: venueHealthData.polymarket?.last_update,
              orderAcceptanceStatus: venueHealthData.polymarket?.order_status || 'ok' as const,
            });
            setVenueBHealth({
              venue: 'pinnacle' as const,
              name: 'Pinnacle',
              status: venueHealthData.pinnacle?.status || 'connected' as const,
              latency: venueHealthData.pinnacle?.latency_ms,
              oddsAge: venueHealthData.pinnacle?.odds_age_seconds,
              apiRateLimitStatus: venueHealthData.pinnacle?.rate_limit_status || 'ok' as const,
            });

            // Calculate global status
            const pmStatus = venueHealthData.polymarket?.status;
            const pnStatus = venueHealthData.pinnacle?.status;
            if (pmStatus === 'error' || pnStatus === 'error') {
              setGlobalStatus('execution_halted');
            } else if (pmStatus === 'degraded' || pnStatus === 'stale' || 
                      venueHealthData.pinnacle?.odds_age_seconds > 10) {
              setGlobalStatus('latency_risk');
            } else {
              setGlobalStatus('in_sync');
            }
          }

          // Fetch arbitrage opportunities
          const opportunitiesData = await api.get<any[]>('/api/strategies/' + strategyId + '/arbitrage-opportunities').catch(() => []);
          setArbitrageOpportunities((opportunitiesData ?? []).map((opp: any) => ({
            id: opp.id,
            eventName: opp.event_name || 'Unknown',
            marketName: opp.market_name || 'Unknown',
            polymarketPrice: opp.polymarket_price || 0,
            pinnacleOdds: opp.pinnacle_odds || 0,
            grossEdge: opp.gross_edge_percent || 0,
            netEdge: opp.net_edge_percent || 0,
            status: opp.status || 'below_threshold' as const,
            timestamp: opp.timestamp || new Date().toISOString(),
          })));

          // Fetch execution pipeline
          const execPipelineData = await api.get<any[]>('/api/strategies/' + strategyId + '/execution-pipeline').catch(() => []);
          setExecutionPipeline((execPipelineData ?? []).map((exec: any) => ({
            id: exec.id,
            timestamp: exec.timestamp || new Date().toLocaleTimeString('es-ES'),
            eventName: exec.event_name || 'Unknown',
            action: exec.action || 'pm_buy' as const,
            status: exec.status || 'pending' as const,
            executionTime: exec.execution_time_ms,
            flags: exec.flags || [],
          })));

          // Fetch open exposures
          const exposuresData = await api.get<any[]>('/api/strategies/' + strategyId + '/exposures').catch(() => []);
          setOpenExposures((exposuresData ?? []).map((exp: any) => ({
            id: exp.id,
            eventName: exp.event_name || 'Unknown',
            netExposure: exp.net_exposure || 0,
            polymarketExposure: exp.polymarket_exposure || 0,
            pinnacleExposure: exp.pinnacle_exposure || 0,
            directionalRisk: exp.directional_risk || 'balanced' as const,
            timeSinceImbalance: exp.time_since_imbalance_seconds,
          })));

          // Fetch profit metrics
          const profitData = await api.get<any>('/api/strategies/' + strategyId + '/profit-metrics').catch(() => null);
          if (profitData) {
            setProfitMetrics({
              totalPnLGross: profitData.total_pnl_gross || 0,
              totalPnLNet: profitData.total_pnl_net || 0,
              profitPerTrade: profitData.profit_per_trade || 0,
              avgExecutionTime: profitData.avg_execution_time_ms || 0,
              avgSlippage: profitData.avg_slippage_percent || 0,
              successRate: profitData.success_rate_percent || 0,
            });
          }

          // Fetch event controls
          const eventsData = await api.get<any[]>('/api/strategies/' + strategyId + '/events/controls').catch(() => []);
          setEventControls((eventsData ?? []).map((evt: any) => ({
            id: evt.id,
            eventName: evt.event_name || 'Unknown',
            status: evt.status || 'active' as const,
            currentEdge: evt.current_edge_percent || 0,
            tradesExecuted: evt.trades_executed || 0,
            lastExecution: evt.last_execution,
          })));

          // Generate risk alerts
          const alerts: any[] = [];
          if (venueHealthData?.pinnacle?.odds_age_seconds > 10) {
            alerts.push({
              id: 'stale-odds',
              severity: 'warning',
              message: `Pinnacle odds stale (${venueHealthData.pinnacle.odds_age_seconds.toFixed(1)}s)`,
              action: 'Verificar conexión API',
              timestamp: new Date().toLocaleTimeString('es-ES'),
            });
          }
          const partialFills = (execPipelineData ?? []).filter((e: any) => e.status === 'partial');
          if (partialFills.length > 0) {
            alerts.push({
              id: 'partial-fills',
              severity: 'warning',
              message: `${partialFills.length} partial fill(s) detectado(s)`,
              action: 'Revisar exposición',
              timestamp: new Date().toLocaleTimeString('es-ES'),
            });
          }
          const unhedgedExposures = (exposuresData ?? []).filter((e: any) => e.directional_risk === 'unhedged');
          if (unhedgedExposures.length > 0) {
            alerts.push({
              id: 'unhedged-exposure',
              severity: 'critical',
              message: `${unhedgedExposures.length} exposición(es) sin hedge`,
              action: 'Force hedge o close position',
              timestamp: new Date().toLocaleTimeString('es-ES'),
            });
          }
          setRiskAlerts(alerts);

          // Capital limits alerts
          const capitalAlerts: any[] = [];
          const capitalPercent = (riskData.capitalUsed / riskData.capitalAssigned) * 100;
          if (capitalPercent >= 90) {
            capitalAlerts.push({
              id: 'max-exposure',
              type: 'critical',
              message: `Approaching max exposure (${capitalPercent.toFixed(1)}%)`,
            });
          }
          // TODO: Calculate dailyPnL and dailyLossLimit from strategy config
          setCapitalLimitsAlerts(capitalAlerts);
        }
      } catch (err) {
        console.error('Error fetching system health:', err);
        // Fallback to default values
        setConnections([
          {
            name: 'Polymarket (Ejecución)',
            status: 'ok' as const,
            latency: 45,
            lastUpdate: '2m ago',
            type: 'execution' as const,
          },
        ]);
        setEvents([]);
        setCheckers([]);
        setEventPipeline([]);
        setActivityLogs([]);
      }
    };
    
    fetchSystemHealth();
    const interval = setInterval(fetchSystemHealth, 10000);
    return () => clearInterval(interval);
  }, [user, stackApp, strategyId, realtimeIntents, strategy, positions, isSurebetStrategy, isDemo]);

  if (!user) return null;

  // Render Surebet-specific Live Control
  if (isSurebetStrategy && strategy) {
    const surebetAlerts: AlertBannerItem[] = [
      ...(isDemo || isSimulation
        ? [{
            id: 'demo-sim',
            severity: 'info' as const,
            message: (
              <>
                {isDemo ? <strong>Modo Demo</strong> : <strong>Modo Simulación</strong>}
                {' — '}
                {isDemo
                  ? 'Datos de ejemplo. Cambia a Real en el header para ver datos del backend.'
                  : 'Backend en DRY_RUN. Datos de ejecución simulada.'}
              </>
            ),
          }]
        : []),
      ...(controlError
        ? [{
            id: 'control-error',
            severity: 'error' as const,
            message: controlError,
            onDismiss: () => setControlError(null),
            dismissLabel: 'Cerrar',
          }]
        : []),
      ...(activateSuccessMessage
        ? [{
            id: 'activate-ok',
            severity: 'info' as const,
            message: activateSuccessMessage,
            onDismiss: () => setActivateSuccessMessage(null),
            dismissLabel: 'Cerrar',
          }]
        : []),
      ...(walletNotConfigured
        ? [{
            id: 'wallet',
            severity: 'error' as const,
            message: (
              <>
                No hay wallet Polymarket configurada. <Link href="/settings/wallets" className="underline font-medium">Ajustes → Wallets</Link>
              </>
            ),
          }]
        : []),
    ];

    return (
      <Layout>
        <div className="space-y-6 w-full">
          {surebetAlerts.length > 0 && (
            <AlertBannerStack alerts={surebetAlerts} maxVisible={2} />
          )}
          <div className="flex items-center justify-end gap-2 flex-wrap">
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground border border-border/50 rounded px-1.5 py-0.5">
              Surebet
            </span>
            {lastUpdate && (
              <span className="text-xs text-muted-foreground whitespace-nowrap">
                Actualizado: {lastUpdate.toLocaleTimeString('es-ES')}
              </span>
            )}
          </div>

          {/* 1. Strategy Header */}
          <div className="w-full">
            <StrategyHeaderWithLoader
              strategyOverride={strategy}
              onPause={handlePause}
              onStop={handleStop}
              onActivate={handleActivate}
              onConfig={() => router.push(`/strategies/${strategyId}`)}
              isLoading={isActivating}
              onStrategyLoaded={(loadedStrategy) => {
                setStrategy(loadedStrategy);
                setIsSurebetStrategy(
                  loadedStrategy.tags?.includes('surebet') ||
                  loadedStrategy.tags?.includes('arbitrage') ||
                  loadedStrategy.name?.toLowerCase().includes('surebet') ||
                  loadedStrategy.name?.toLowerCase().includes('arbitrage')
                );
              }}
            />
          </div>

          {/* Modo y eventos asignados - claridad para el usuario */}
          <Alert variant={executionMode === 'LIVE' ? 'default' : 'default'} className="w-full">
            <AlertDescription className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
              <span>
                <strong>Modo:</strong>{' '}
                {executionMode === 'LIVE'
                  ? 'Real (órdenes con dinero real)'
                  : executionMode === 'PAPER'
                    ? 'Papel (simulación con datos reales)'
                    : 'Simulación (no se envían órdenes)'}
              </span>
              {isSimulation && (
                <span>
                  <strong>Execution mode (backend):</strong> {executionMode}
                </span>
              )}
              <span>
                <strong>Eventos asignados:</strong>{' '}
                {strategyEventsCount === 0
                  ? 'Ninguno. Asigna al menos uno en '
                  : strategyEventsCount}
                {strategyEventsCount === 0 && (
                  <>
                    <Link href={`/strategies/${strategyId}/desk`} className="font-medium underline underline-offset-2 hover:no-underline">
                      Desk
                    </Link>
                    {' o '}
                    <Link href={`/strategies/${strategyId}/universe`} className="font-medium underline underline-offset-2 hover:no-underline">
                      Configurar Universe
                    </Link>
                  </>
                )}
                {strategyEventsCount === 0 && ' para que la estrategia opere.'}
              </span>
              {strategyEventsCount === 0 && strategy?.is_active && (
                <span className="text-amber-600 dark:text-amber-400">
                  La estrategia está activa pero no tiene mercados asignados.
                </span>
              )}
              <span className="text-muted-foreground text-xs block mt-2 w-full">
                Datos en vivo desde el backend (refresco cada 2–5 s). Límite de exposición y métricas desde la configuración de la estrategia y el estado en vivo. Sin eventos asignados no hay operativa.
              </span>
            </AlertDescription>
          </Alert>

          {/* 3. KPI Strip */}
          <div className="w-full">
            <LiveKPIStrip
              totalPnL={liveStatus?.metrics?.total_pnl_usdc ?? 0}
              totalExposure={liveStatus?.metrics?.total_exposure_usdc ?? 0}
              maxExposure={strategy?.risk_config?.max_exposure ?? 5000}
              totalIntents={liveStatus?.metrics?.total_intents ?? 0}
              approvedIntents={liveStatus?.metrics?.approved_intents ?? 0}
              executedIntents={liveStatus?.metrics?.executed_intents ?? 0}
              winRate={(liveStatus?.metrics?.win_rate ?? 0) * 100}
              lastCalculatedAt={liveStatus?.metrics?.calculated_at ?? null}
              isLoading={!liveStatus && !isDemo}
            />
          </div>

          {/* 4. Signals Monitor (Core) */}
          <div className="w-full">
            <SignalsMonitor 
              strategyId={strategyId} 
              strategyType={isSurebetStrategy ? "surebet_arbitrage" : "liquidity"} 
            />
          </div>

          {/* 3. Dual Venue Health */}
          {venueAHealth && venueBHealth && (
            <div className="w-full">
              <DualVenueHealth venueA={venueAHealth} venueB={venueBHealth} />
            </div>
          )}

          {/* 4. Live Arbitrage Snapshot */}
          <div className="w-full">
            <LiveArbitrageSnapshot opportunities={arbitrageOpportunities} />
          </div>

          {/* 5. Execution Pipeline */}
          <div className="w-full">
            <ExecutionPipeline executions={executionPipeline} />
          </div>

          {/* 6. Open Exposure */}
          <div className="w-full">
            <OpenExposure 
              exposures={openExposures}
              onForceHedge={(id) => {
                // TODO: Implement force hedge
                console.log('Force hedge:', id);
              }}
              onClosePosition={(id) => {
                // TODO: Implement close position
                console.log('Close position:', id);
              }}
              onFreezeEvent={(id) => {
                // TODO: Implement freeze event
                console.log('Freeze event:', id);
              }}
            />
          </div>

          {/* 7. Capital & Limits Monitor */}
          <div id="metrics" className="w-full scroll-mt-4">
            <CapitalLimitsMonitor
              capitalAssigned={riskData.capitalAssigned}
              capitalUsed={riskData.capitalUsed}
              walletBalanceUsdc={polymarketBalanceUsdc}
              activeTrades={riskData.activeEvents}
              dailyPnL={0} // TODO: Calculate from metrics
              drawdown={0} // TODO: Calculate from metrics
              alerts={capitalLimitsAlerts}
            />
          </div>

          {/* 8. Profit & Efficiency Metrics */}
          {profitMetrics && (
            <div className="w-full">
              <ProfitEfficiencyMetrics {...profitMetrics} />
            </div>
          )}

          {/* 9. Risk Alerts & Safeguards */}
          {riskAlerts.length > 0 && (
            <div className="w-full">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg font-semibold">Active Alerts</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {riskAlerts.map((alert) => (
                      <Alert 
                        key={alert.id} 
                        variant={alert.severity === 'critical' ? 'destructive' : 'default'}
                      >
                        <AlertTriangle className="h-4 w-4" />
                        <AlertDescription>
                          <div className="flex items-center justify-between">
                            <span>{alert.message}</span>
                            <span className="text-xs text-muted-foreground">{alert.timestamp}</span>
                          </div>
                          {alert.action && (
                            <div className="text-xs text-muted-foreground mt-1">
                              Acción: {alert.action}
                            </div>
                          )}
                        </AlertDescription>
                      </Alert>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* 10. Event-Level Controls */}
          <div className="w-full">
            <EventLevelControls
              events={eventControls}
              onDisableEvent={(id) => {
                // TODO: Implement disable event
                console.log('Disable event:', id);
              }}
              onForceSync={(id) => {
                // TODO: Implement force sync
                console.log('Force sync:', id);
              }}
              onManualOverride={(id) => {
                // TODO: Implement manual override
                console.log('Manual override:', id);
              }}
            />
          </div>

          {/* 11. Activity Log */}
          <div id="logs" className="w-full scroll-mt-4">
            <ActivityLog logs={activityLogs} />
          </div>
        </div>
      </Layout>
    );
  }

  // Tipster Live Control — layout específico (tips pipeline, ejecuciones desde tips)
  if (isTipsterStrategy && strategy) {
    const tipsterAlerts: AlertBannerItem[] = [
      ...(isDemo || isSimulation
        ? [{
            id: 'demo-sim',
            severity: 'info' as const,
            message: (
              <>
                {isDemo ? <strong>Modo Demo</strong> : <strong>Modo Simulación</strong>}
                {' — '}
                {isDemo
                  ? 'Datos de ejemplo. Cambia a Real en el header para ver datos del backend.'
                  : 'Backend en DRY_RUN. Datos de ejecución simulada.'}
              </>
            ),
          }]
        : []),
      ...(controlError
        ? [{
            id: 'control-error',
            severity: 'error' as const,
            message: controlError,
            onDismiss: () => setControlError(null),
            dismissLabel: 'Cerrar',
          }]
        : []),
      ...(activateSuccessMessage
        ? [{
            id: 'activate-ok',
            severity: 'info' as const,
            message: activateSuccessMessage,
            onDismiss: () => setActivateSuccessMessage(null),
            dismissLabel: 'Cerrar',
          }]
        : []),
    ];

    return (
      <Layout>
        <div className="space-y-4 w-full max-w-5xl">
          {tipsterAlerts.length > 0 && (
            <AlertBannerStack alerts={tipsterAlerts} maxVisible={2} />
          )}
          <div className="flex items-center justify-end gap-2 flex-wrap">
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground border border-border/50 rounded px-1.5 py-0.5">Tipster</span>
            {lastUpdate && <span className="text-xs text-muted-foreground whitespace-nowrap">Actualizado: {lastUpdate.toLocaleTimeString('es-ES')}</span>}
          </div>
          <div className="w-full border-b border-border/40 pb-4">
            <StrategyHeaderWithLoader
              strategyOverride={strategy}
              onPause={handlePause}
              onStop={handleStop}
              onActivate={handleActivate}
              onConfig={() => router.push(`/strategies/${strategyId}`)}
              isLoading={isActivating}
              onStrategyLoaded={(loadedStrategy) => {
                setStrategy(loadedStrategy);
                const isSurebet = loadedStrategy.tags?.includes('surebet') || loadedStrategy.tags?.includes('arbitrage') || loadedStrategy.name?.toLowerCase().includes('surebet') || loadedStrategy.name?.toLowerCase().includes('arbitrage');
                setIsSurebetStrategy(isSurebet);
                const sgs = loadedStrategy.support_graphs as Array<{ name?: string }> | undefined;
                setIsTipsterStrategy(!!sgs?.some((g) => g?.name === 'telegram_listener'));
              }}
            />
          </div>
          <Alert variant="default" className="w-full py-2">
            <AlertDescription className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
              <span><strong>Modo:</strong> {executionMode === 'LIVE' ? 'Real (órdenes con dinero real)' : executionMode === 'PAPER' ? 'Papel' : 'Simulación'}</span>
              <span><strong>Eventos asignados:</strong> {strategyEventsCount === 0 ? 'Ninguno. Asigna en ' : strategyEventsCount}
                {strategyEventsCount === 0 && <><Link href={`/strategies/${strategyId}/desk`} className="font-medium underline">Desk</Link> o <Link href={`/strategies/${strategyId}/universe`} className="font-medium underline">Universe</Link></>}
                {strategyEventsCount === 0 && ' para operar.'}
              </span>
              {strategyEventsCount === 0 && strategy?.is_active && <span className="text-amber-600 dark:text-amber-400">Estrategia activa sin mercados asignados.</span>}
            </AlertDescription>
          </Alert>
          <div className="w-full">
            <LiveKPIStrip
              totalPnL={liveStatus?.metrics?.total_pnl_usdc ?? 0}
              totalExposure={liveStatus?.metrics?.total_exposure_usdc ?? 0}
              maxExposure={strategy?.risk_config?.max_exposure ?? 5000}
              totalIntents={liveStatus?.metrics?.total_intents ?? 0}
              approvedIntents={liveStatus?.metrics?.approved_intents ?? 0}
              executedIntents={liveStatus?.metrics?.executed_intents ?? 0}
              winRate={(liveStatus?.metrics?.win_rate ?? 0) * 100}
              lastCalculatedAt={liveStatus?.metrics?.calculated_at ?? null}
              isLoading={!liveStatus && !isDemo}
            />
          </div>
          <div className="w-full">
            <TipsPipelineCompact />
          </div>
          {checkers.length > 0 && (
            <div className="w-full">
              <ExternalConfirmationStatus checkers={checkers} />
            </div>
          )}
          <div className="w-full">
            <IntentsTableWithLoader variant="compact" />
          </div>
          <div className="w-full">
            <RiskMonitor {...riskData} walletBalanceUsdc={polymarketBalanceUsdc} />
          </div>
          <div id="logs" className="w-full scroll-mt-4">
            <ActivityLog logs={activityLogs} />
          </div>
        </div>
      </Layout>
    );
  }

  // Liquidity Live Control — layout específico (orderbook signals, execution feed, event pipeline)
  const liquidityAlerts: AlertBannerItem[] = [
    ...(isDemo || isSimulation
      ? [{
          id: 'demo-sim',
          severity: 'info' as const,
          message: (
            <>
              {isDemo ? <strong>Modo Demo</strong> : <strong>Modo Simulación</strong>}
              {' — '}
              {isDemo
                ? 'Datos de ejemplo. Cambia a Real en el header para ver datos del backend.'
                : 'Backend en DRY_RUN. Datos de ejecución simulada.'}
            </>
          ),
        }]
      : []),
    ...(controlError
      ? [{
          id: 'control-error',
          severity: 'error' as const,
          message: controlError,
          onDismiss: () => setControlError(null),
          dismissLabel: 'Cerrar',
        }]
      : []),
    ...(activateSuccessMessage
      ? [{
          id: 'activate-ok',
          severity: 'info' as const,
          message: activateSuccessMessage,
          onDismiss: () => setActivateSuccessMessage(null),
          dismissLabel: 'Cerrar',
        }]
      : []),
    ...(walletNotConfigured
      ? [{
          id: 'wallet',
          severity: 'error' as const,
          message: (
            <>
              No hay wallet Polymarket configurada para tu usuario. El balance y las operaciones con CLOB requieren una wallet activa en{' '}
              <Link href="/settings/wallets" className="underline font-medium">Ajustes → Wallets</Link>.
            </>
          ),
        }]
      : []),
  ];

  return (
    <Layout>
      <div className="space-y-4 w-full max-w-5xl">
        {liquidityAlerts.length > 0 && (
          <AlertBannerStack alerts={liquidityAlerts} maxVisible={2} />
        )}
        {/* Last Update & Strategy Type */}
        <div className="flex items-center justify-end gap-2 flex-wrap">
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground border border-border/50 rounded px-1.5 py-0.5">
            Liquidity
          </span>
          {lastUpdate && (
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              Actualizado: {lastUpdate.toLocaleTimeString('es-ES')}
            </span>
          )}
        </div>

        {/* 1. Strategy Header */}
        <div className="w-full border-b border-border/40 pb-4">
          <StrategyHeaderWithLoader
            strategyOverride={strategy}
            onPause={handlePause}
            onStop={handleStop}
            onActivate={handleActivate}
            onConfig={() => router.push(`/strategies/${strategyId}`)}
            isLoading={isActivating}
            onStrategyLoaded={(loadedStrategy) => {
              setStrategy(loadedStrategy);
              const isSurebet =
                loadedStrategy.tags?.includes('surebet') ||
                loadedStrategy.tags?.includes('arbitrage') ||
                loadedStrategy.name?.toLowerCase().includes('surebet') ||
                loadedStrategy.name?.toLowerCase().includes('arbitrage');
              setIsSurebetStrategy(isSurebet);
              const sgs = loadedStrategy.support_graphs as Array<{ name?: string }> | undefined;
              setIsTipsterStrategy(!!sgs?.some((g) => g?.name === 'telegram_listener'));
            }}
          />
        </div>

        {/* 2. Mode & Events (compact) */}
        <Alert variant="default" className="w-full py-2">
          <AlertDescription className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
            <span>
              <strong>Modo:</strong>{' '}
              {executionMode === 'LIVE'
                ? 'Real (órdenes con dinero real)'
                : executionMode === 'PAPER'
                  ? 'Papel (simulación con datos reales)'
                  : 'Simulación (no se envían órdenes)'}
            </span>
            {isSimulation && (
              <span>
                <strong>Execution mode (backend):</strong> {executionMode}
              </span>
            )}
            <span>
              <strong>Eventos asignados:</strong>{' '}
              {strategyEventsCount === 0
                ? 'Ninguno. Asigna al menos uno en '
                : strategyEventsCount}
              {strategyEventsCount === 0 && (
                <>
                  <Link href={`/strategies/${strategyId}/desk`} className="font-medium underline underline-offset-2 hover:no-underline">
                    Desk
                  </Link>
                  {' o '}
                  <Link href={`/strategies/${strategyId}/universe`} className="font-medium underline underline-offset-2 hover:no-underline">
                    Configurar Universe
                  </Link>
                </>
              )}
              {strategyEventsCount === 0 && ' para que la estrategia opere.'}
            </span>
            {strategyEventsCount === 0 && strategy?.is_active && (
              <span className="text-amber-600 dark:text-amber-400">
                La estrategia está activa pero no tiene mercados asignados.
              </span>
            )}
            <span className="text-muted-foreground text-xs block mt-2 w-full">
              Datos en vivo desde el backend (refresco cada 2–5 s). Límite de exposición y métricas desde la configuración de la estrategia y el estado en vivo. Sin eventos asignados no hay operativa.
            </span>
          </AlertDescription>
        </Alert>

        {/* 3. KPI Strip */}
        <div className="w-full">
          <LiveKPIStrip
            totalPnL={liveStatus?.metrics?.total_pnl_usdc ?? 0}
            totalExposure={liveStatus?.metrics?.total_exposure_usdc ?? 0}
            maxExposure={strategy?.risk_config?.max_exposure ?? 5000}
            totalIntents={liveStatus?.metrics?.total_intents ?? 0}
            approvedIntents={liveStatus?.metrics?.approved_intents ?? 0}
            executedIntents={liveStatus?.metrics?.executed_intents ?? 0}
            winRate={(liveStatus?.metrics?.win_rate ?? 0) * 100}
            lastCalculatedAt={liveStatus?.metrics?.calculated_at ?? null}
            isLoading={!liveStatus && !isDemo}
          />
        </div>

        {/* 4. Core Panel: Monitor de Señales */}
        <div className="w-full">
          <SignalsMonitor strategyId={strategyId} strategyType="liquidity" variant="compact" />
        </div>

        {/* 4.5 Confirmación Externa (cuando hay checkers) */}
        {checkers.length > 0 && (
          <div className="w-full">
            <ExternalConfirmationStatus checkers={checkers} />
          </div>
        )}

        {/* 5. Feed de Ejecución */}
        <div className="w-full">
          <IntentsTableWithLoader variant="compact" />
        </div>

        {/* 6. Pipeline de Eventos */}
        <div className="w-full">
          <EventPipeline events={eventPipeline} variant="compact" />
        </div>

        {/* Posiciones Abiertas */}
        <div className="w-full">
          <PositionsTable positions={positions} />
        </div>

        {/* Monitor de Riesgo */}
        <div className="w-full">
          <RiskMonitor {...riskData} walletBalanceUsdc={polymarketBalanceUsdc} />
        </div>

        {/* Orderbook Health */}
        {liveStatus?.orderbook_health && Object.keys(liveStatus.orderbook_health).length > 0 && (
          <div className="w-full">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg font-semibold">Orderbook Health</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(liveStatus.orderbook_health).map(([assetId, health]: [string, any]) => (
                    <div key={assetId} className="border rounded p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium">{assetId}</span>
                        <Badge variant={health.has_data ? 'default' : 'secondary'}>
                          {health.has_data ? 'Active' : 'No Data'}
                        </Badge>
                      </div>
                      {health.has_data && (
                        <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                          <div>
                            <span className="font-medium">Staleness:</span> {health.staleness_ms}ms
                          </div>
                          <div>
                            <span className="font-medium">Spread:</span> {health.spread_bps?.toFixed(2) || 'N/A'} bps
                          </div>
                          {health.best_bid_price && (
                            <div>
                              <span className="font-medium">Bid:</span> {health.best_bid_price.toFixed(4)}
                            </div>
                          )}
                          {health.best_ask_price && (
                            <div>
                              <span className="font-medium">Ask:</span> {health.best_ask_price.toFixed(4)}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Logs de Actividad */}
        <div id="logs" className="w-full scroll-mt-4">
          <ActivityLog logs={activityLogs} />
        </div>
      </div>
    </Layout>
  );
}
