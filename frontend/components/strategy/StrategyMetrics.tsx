'use client';

import { useState, useEffect } from 'react';
import { KPICard } from '@/components/dashboard/KPICard';
import { StrategyMetric } from '@/types/strategy';

interface StrategyMetricsProps {
  metrics?: StrategyMetric[];
  strategyId: string;
}

export function StrategyMetrics({ metrics, strategyId }: StrategyMetricsProps) {
  const [now, setNow] = useState(0);
  useEffect(() => {
    const update = () => setNow(Date.now());
    update();
    const id = setInterval(update, 60000); // actualizar cada minuto
    return () => clearInterval(id);
  }, []);

  // Calcular métricas agregadas desde el array de métricas
  const latestMetric = metrics && metrics.length > 0 ? metrics[0] : null;
  
  const totalPnL = latestMetric?.total_pnl_usdc || 0;
  const totalExposure = latestMetric?.total_exposure_usdc || 0;
  const totalIntents = latestMetric?.total_intents || 0;
  const approvedIntents = latestMetric?.approved_intents || 0;
  const executedIntents = latestMetric?.executed_intents || 0;
  const winRate = latestMetric?.win_rate ? latestMetric.win_rate * 100 : 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 w-full">
      <KPICard
        title="PnL"
        value={`${totalPnL >= 0 ? '+' : ''}$${totalPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
        trend={totalPnL !== 0 ? {
          value: `${totalPnL >= 0 ? '+' : ''}${(totalPnL / 1000).toFixed(1)}%`,
          isPositive: totalPnL >= 0,
        } : undefined}
        breakdown={
          <>
            Realizado: ${totalPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}<br />
            No Realizado: $0.00
          </>
        }
      />
      
      <KPICard
        title="Exposición"
        value={`$${totalExposure.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
        breakdown="Límite: $5,000"
      />
      
      <KPICard
        title="Intents"
        value={`${totalIntents} ejecutados`}
        breakdown={
          <>
            Aprobados: {approvedIntents}<br />
            Rechazados: {totalIntents - approvedIntents}<br />
            Tasa: {totalIntents > 0 ? ((approvedIntents / totalIntents) * 100).toFixed(0) : 0}%
          </>
        }
      />
      
      <KPICard
        title="Win Rate"
        value={`${winRate.toFixed(1)}%`}
        breakdown={
          <>
            Ejecutados: {executedIntents}<br />
            Avg Profit: ${totalPnL > 0 && executedIntents > 0 ? (totalPnL / executedIntents).toFixed(2) : '0.00'}
          </>
        }
      />
      
      <KPICard
        title="Última Acción"
        value={latestMetric?.calculated_at 
          ? new Date(latestMetric.calculated_at).toLocaleDateString('es-ES', {
              month: 'short',
              day: 'numeric',
            })
          : 'N/A'}
        breakdown={
          latestMetric?.calculated_at
            ? now > 0
              ? `Hace ${Math.floor((now - new Date(latestMetric.calculated_at).getTime()) / 60000)} min`
              : '...'
            : 'Sin actividad'
        }
      />
    </div>
  );
}

