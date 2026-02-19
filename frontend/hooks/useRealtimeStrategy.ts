'use client';

import { useEffect, useState } from 'react';
import { useStrategyWebSocket, StrategyWebSocketEvent } from './useStrategyWebSocket';
import { ExecutionIntent, StrategyMetric } from '@/types/strategy';

export function useRealtimeStrategy(strategyId: string) {
  const [intents, setIntents] = useState<ExecutionIntent[]>([]);
  const [metrics, setMetrics] = useState<StrategyMetric[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [recentPlans, setRecentPlans] = useState<any[]>([]);

  const { isConnected, lastEvent } = useStrategyWebSocket(strategyId);

  // Handle WebSocket events from strategy-specific endpoint
  useEffect(() => {
    if (!lastEvent) return;

    const event = lastEvent;

    switch (event.type) {
      case 'plan_created':
      case 'plan_executing':
      case 'plan_filled':
      case 'plan_failed':
        // Update recent plans (subscription to WebSocket - valid setState in effect)
        const newPlan = event.payload;
        // eslint-disable-next-line react-hooks/set-state-in-effect -- WebSocket subscription pattern
        setRecentPlans((prev) => {
          const exists = prev.some((p) => (p.plan_id || p.id) === (newPlan.plan_id || newPlan.id));
          if (exists) {
            return prev.map((p) => ((p.plan_id || p.id) === (newPlan.plan_id || newPlan.id) ? newPlan : p));
          }
          return [newPlan, ...prev].slice(0, 20);
        });
        
        // Also update intents if plan has legs (Execution Plan format)
        if (newPlan.legs && Array.isArray(newPlan.legs) && newPlan.legs.length > 0) {
          setIntents((prev) => {
            const planId = newPlan.plan_id || newPlan.id;
            const existingIndex = prev.findIndex((intent) => intent.id === planId);
            
            // Map plan leg to intent format
            const leg = newPlan.legs[0];
            const intent: ExecutionIntent = {
              id: planId,
              strategy_id: newPlan.strategy_id || strategyId,
              event_id: newPlan.event_id,
              side: leg.side || 'BUY',
              outcome: leg.outcome || 'YES',
              target_price: leg.target_price || 0,
              size: leg.size || 0,
              size_usdc: leg.size_usdc || 0,
              reason: (leg as { reason?: string }).reason ?? '',
              status: newPlan.status === 'PLAN_BUILT' ? 'APPROVED' : 
                      newPlan.status === 'EXECUTING' ? 'EXECUTING' :
                      newPlan.status === 'COMPLETED' ? 'EXECUTED' :
                      newPlan.status === 'FAILED' ? 'FAILED' : 'PENDING',
              created_at: newPlan.created_at,
              trace_id: newPlan.trace_id,
            };
            
            if (existingIndex >= 0) {
              // Update existing intent
              const updated = [...prev];
              updated[existingIndex] = intent;
              return updated;
            } else {
              // Add new intent at the beginning
              return [intent, ...prev].slice(0, 20);
            }
          });
        }
        
        setLastUpdate(new Date());
        break;

      case 'precheck_failed':
        // Could update intents or show alert
        setLastUpdate(new Date());
        break;

      case 'orderbook_update':
        // Orderbook update for this strategy
        setLastUpdate(new Date());
        break;

      case 'metrics_update':
        // Update metrics
        if (event.payload.metrics) {
          setMetrics(event.payload.metrics);
        }
        setLastUpdate(new Date());
        break;

      case 'connected':
        console.log(`[useRealtimeStrategy] Connected to strategy ${event.strategy_id}`);
        break;

      default:
        // Unknown event type, log for debugging
        console.log('[useRealtimeStrategy] Unknown event type:', event.type);
    }
  }, [lastEvent]);

  return {
    intents,
    metrics,
    recentPlans,
    isConnected,
    lastUpdate,
    setIntents,
    setMetrics,
  };
}

