'use client';

import { useEffect, useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, Signal, Activity } from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUser, useStackApp } from '@stackframe/stack';
import { createTokenGetter } from '@/lib/api';
import { WebSocketEvent } from '@/lib/websocket';
import { cn } from '@/lib/utils';

interface SignalValue {
  value: number | null;
  timestamp: string;
}

interface Signals {
  // Liquidity indicators
  book_imbalance?: SignalValue;
  toxic_flow?: SignalValue;
  inventory_skew?: SignalValue;
  price_drift?: SignalValue;
  spread_elasticity?: SignalValue;
  cancel_rate?: SignalValue;
  rel_liquidity?: SignalValue;
  tw_volatility?: SignalValue;
  res_gap?: SignalValue;
  slippage_impact?: SignalValue;
  // Rentabilidad indicators
  expected_roi_at_depth?: SignalValue;
  capital_absorption_capacity?: SignalValue;
  time_value_score?: SignalValue;
  slippage_impact_100k?: SignalValue;
  // Arbitrage indicators
  net_arb_gap?: SignalValue;
  latency_delta?: SignalValue;
  liquidity_match?: SignalValue;
  hedge_slippage?: SignalValue;
  sync_status?: SignalValue;
  price_correlation?: SignalValue;
  fill_probability?: SignalValue;
  rejection_risk?: SignalValue;
  gas_impact?: SignalValue;
  arb_persistence?: SignalValue;
  unreliable?: SignalValue;
}

interface SignalsMonitorProps {
  strategyId: string;
  strategyType: 'liquidity' | 'surebet_arbitrage';
}

// Visualizador: Barra de Progreso para book_imbalance
function BookImbalanceIndicator({ value }: { value: number | null }) {
  if (value === null) return <span className="text-muted-foreground text-sm">N/A</span>;
  
  // Normalizar a [0, 100] para la barra: [-1, 1] -> [0, 100]
  const normalized = ((value + 1) / 2) * 100;
  
  // Color reactivo: verde en centro (0.4-0.6), amarillo cerca, rojo en extremos
  const colorClass = 
    normalized < 40 || normalized > 60 ? 'bg-red-500' :
    normalized < 45 || normalized > 55 ? 'bg-yellow-500' :
    'bg-green-500';
  
  return (
    <div className="space-y-1">
      <Progress value={normalized} className={cn("h-2", colorClass)} />
      <span className="text-xs text-muted-foreground">{value.toFixed(3)}</span>
    </div>
  );
}

// Visualizador: Indicador de Latencia para latency_delta
function LatencyIndicator({ value }: { value: number | null }) {
  if (value === null) return <span className="text-muted-foreground text-sm">N/A</span>;
  
  // Estilo señal móvil: verde < 500ms, amarillo < 1000ms, naranja < 2000ms, rojo >= 2000ms
  const status = 
    value < 500 ? 'excellent' :
    value < 1000 ? 'good' :
    value < 2000 ? 'warning' :
    'critical';
  
  const colors = {
    excellent: 'bg-green-500',
    good: 'bg-yellow-500',
    warning: 'bg-orange-500',
    critical: 'bg-red-500 animate-pulse',
  };
  
  return (
    <div className="flex items-center gap-2">
      <div className={cn("w-3 h-3 rounded-full", colors[status])} />
      <span className="text-sm font-mono">{value.toFixed(0)}ms</span>
    </div>
  );
}

// Visualizador: Badge Dinámico para net_arb_gap
function NetArbGapBadge({ value }: { value: number | null }) {
  if (value === null) return <Badge variant="outline">N/A</Badge>;
  
  const percentage = (value * 100).toFixed(2);
  
  // Rojo < 0%, Verde > 1.5%, Dorado > 3%
  const variant = 
    value < 0 ? 'destructive' :
    value > 0.03 ? 'default' :
    value > 0.015 ? 'default' :
    'secondary';
  
  const colorClass = 
    value > 0.03 ? 'bg-yellow-500 text-yellow-900 dark:bg-yellow-600 dark:text-yellow-100' :
    value > 0.015 ? 'bg-green-500 text-green-900 dark:bg-green-600 dark:text-green-100' :
    value < 0 ? 'bg-red-500 text-red-900 dark:bg-red-600 dark:text-red-100' :
    'bg-gray-500 text-gray-900 dark:bg-gray-600 dark:text-gray-100';
  
  return (
    <Badge className={colorClass} variant={variant}>
      {value > 0 ? '+' : ''}{percentage}%
    </Badge>
  );
}

// Visualizador genérico para valores numéricos
function NumericIndicator({ 
  value, 
  label, 
  format = (v) => v.toFixed(3),
  colorClass
}: { 
  value: number | null; 
  label: string;
  format?: (v: number) => string;
  colorClass?: string;
}) {
  if (value === null) return <span className="text-muted-foreground text-sm">N/A</span>;
  
  return (
    <div className="space-y-1">
      <span className={cn("text-sm font-medium", colorClass)}>{format(value)}</span>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

// Visualizador: Barra de progreso para valores [0, 1]
function ProgressIndicator({ 
  value, 
  label,
  thresholds = { good: 0.7, warning: 0.5 }
}: { 
  value: number | null; 
  label: string;
  thresholds?: { good: number; warning: number };
}) {
  if (value === null) return <span className="text-muted-foreground text-sm">N/A</span>;
  
  const normalized = value * 100;
  const colorClass = 
    normalized >= thresholds.good * 100 ? 'bg-green-500' :
    normalized >= thresholds.warning * 100 ? 'bg-yellow-500' :
    'bg-red-500';
  
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span>{value.toFixed(3)}</span>
      </div>
      <Progress value={normalized} className={cn("h-2", colorClass)} />
    </div>
  );
}

export function SignalsMonitor({ strategyId, strategyType }: SignalsMonitorProps) {
  const [signals, setSignals] = useState<Signals>({});
  const [alertMode, setAlertMode] = useState(false);
  const user = useUser();
  const stackApp = useStackApp();
  
  const token = user ? (createTokenGetter(user, stackApp)() || null) : null;
  const { isConnected, subscribe } = useWebSocket({
    token,
    enabled: !!user && !!strategyId,
  });
  
  // Suscribirse a actualizaciones de DecisionTrace
  useEffect(() => {
    if (!isConnected || !strategyId) return;
    
    const unsubscribe = subscribe('decision_trace', (event: WebSocketEvent) => {
      if (event.payload.strategy_id === strategyId && event.payload.signals) {
        // Convertir signals a formato con timestamp
        const signalsWithTimestamp: Signals = {};
        Object.entries(event.payload.signals).forEach(([key, value]) => {
          signalsWithTimestamp[key as keyof Signals] = {
            value: value as number | null,
            timestamp: event.payload.timestamp || new Date().toISOString(),
          };
        });
        setSignals(signalsWithTimestamp);
        
        // Verificar modo alerta
        checkAlertMode(signalsWithTimestamp);
      }
    });
    
    return unsubscribe;
  }, [isConnected, strategyId, subscribe]);
  
  const checkAlertMode = (currentSignals: Signals) => {
    // Indicadores críticos en zona roja
    const criticalRed = 
      (currentSignals.toxic_flow?.value != null && currentSignals.toxic_flow.value > 0.7) ||
      (currentSignals.rejection_risk?.value != null && currentSignals.rejection_risk.value > 0.5) ||
      (currentSignals.latency_delta?.value != null && currentSignals.latency_delta.value > 2000) ||
      (currentSignals.unreliable?.value != null && currentSignals.unreliable.value === 1.0);
    
    setAlertMode(criticalRed);
  };
  
  // Determinar indicadores prioritarios según strategy_type
  const indicatorLayout = useMemo(() => {
    if (strategyType === 'liquidity') {
      return {
        primary: ['book_imbalance', 'toxic_flow', 'inventory_skew', 'expected_roi_at_depth'],
        secondary: ['price_drift', 'spread_elasticity', 'capital_absorption_capacity', 'time_value_score'],
        tertiary: ['cancel_rate', 'rel_liquidity', 'tw_volatility', 'res_gap', 'slippage_impact', 'slippage_impact_100k'],
      };
    } else {
      return {
        primary: ['net_arb_gap', 'latency_delta', 'liquidity_match', 'fill_probability'],
        secondary: ['sync_status', 'price_correlation', 'hedge_slippage'],
        tertiary: ['rejection_risk', 'gas_impact', 'arb_persistence'],
      };
    }
  }, [strategyType]);
  
  const renderIndicator = (key: string, signal: SignalValue | undefined) => {
    if (!signal) return null;
    
    const value = signal.value;
    
    switch (key) {
      case 'book_imbalance':
        return <BookImbalanceIndicator value={value} />;
      case 'latency_delta':
        return <LatencyIndicator value={value} />;
      case 'net_arb_gap':
        return <NetArbGapBadge value={value} />;
      case 'toxic_flow':
      case 'inventory_skew':
      case 'cancel_rate':
      case 'rejection_risk':
      case 'fill_probability':
      case 'sync_status':
        return (
          <ProgressIndicator 
            value={value} 
            label={key.replace(/_/g, ' ')}
            thresholds={{ good: 0.7, warning: 0.5 }}
          />
        );
      case 'expected_roi_at_depth':
      case 'capital_absorption_capacity':
      case 'time_value_score':
        return (
          <NumericIndicator 
            value={value} 
            label={key.replace(/_/g, ' ')}
            format={(v) => v > 0.01 ? `${(v * 100).toFixed(2)}%` : v.toFixed(4)}
            colorClass={value && value > 0.06 ? 'text-green-600 dark:text-green-400' : undefined}
          />
        );
      default:
        return (
          <NumericIndicator 
            value={value} 
            label={key.replace(/_/g, ' ')}
          />
        );
    }
  };
  
  return (
    <Card className={cn(
      "w-full transition-all duration-300",
      alertMode && "border-2 border-red-500 animate-pulse"
    )}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Signal className="h-4 w-4" />
          Signals Monitor
        </CardTitle>
        {alertMode && (
          <AlertCircle className="h-4 w-4 text-red-500 animate-pulse" />
        )}
        {!isConnected && (
          <Badge variant="outline" className="text-xs">
            <Activity className="h-3 w-3 mr-1" />
            Disconnected
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Indicadores Primarios */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground mb-2">Primary Indicators</h4>
          <div className="grid grid-cols-2 gap-3">
            {indicatorLayout.primary.map((key) => {
              const signal = signals[key as keyof Signals];
              if (!signal) return null;
              return (
                <div key={key} className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground capitalize">
                    {key.replace(/_/g, ' ')}
                  </p>
                  {renderIndicator(key, signal)}
                </div>
              );
            })}
          </div>
        </div>
        
        {/* Indicadores Secundarios */}
        {indicatorLayout.secondary.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-muted-foreground mb-2">Secondary Indicators</h4>
            <div className="grid grid-cols-2 gap-3">
              {indicatorLayout.secondary.map((key) => {
                const signal = signals[key as keyof Signals];
                if (!signal) return null;
                return (
                  <div key={key} className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground capitalize">
                      {key.replace(/_/g, ' ')}
                    </p>
                    {renderIndicator(key, signal)}
                  </div>
                );
              })}
            </div>
          </div>
        )}
        
        {/* Indicadores Terciarios (colapsables) */}
        {indicatorLayout.tertiary.length > 0 && (
          <details className="text-xs">
            <summary className="cursor-pointer font-semibold text-muted-foreground mb-2">
              Additional Indicators ({indicatorLayout.tertiary.length})
            </summary>
            <div className="grid grid-cols-2 gap-3 mt-2">
              {indicatorLayout.tertiary.map((key) => {
                const signal = signals[key as keyof Signals];
                if (!signal) return null;
                return (
                  <div key={key} className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground capitalize">
                      {key.replace(/_/g, ' ')}
                    </p>
                    {renderIndicator(key, signal)}
                  </div>
                );
              })}
            </div>
          </details>
        )}
        
        {/* Estado de confiabilidad para arbitraje */}
        {strategyType === 'surebet_arbitrage' && signals.unreliable?.value === 1.0 && (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/50 rounded-md">
            <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
              <AlertCircle className="h-4 w-4" />
              <span className="text-xs font-semibold">Data Unreliable</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              External data source is stale or latency exceeds threshold. Operations may be unsafe.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

