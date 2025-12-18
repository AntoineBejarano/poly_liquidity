'use client';

import { useEffect, useState } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { useWebSocket } from './useWebSocket';
import { createTokenGetter } from '@/lib/api';
import { WebSocketEvent } from '@/lib/websocket';
import { ExecutionIntent, StrategyMetric } from '@/types/strategy';

export function useRealtimeStrategy(strategyId: string) {
  const user = useUser();
  const stackApp = useStackApp();
  const [intents, setIntents] = useState<ExecutionIntent[]>([]);
  const [metrics, setMetrics] = useState<StrategyMetric[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const token = user ? (createTokenGetter(user, stackApp)() || null) : null;

  const { isConnected, subscribe } = useWebSocket({
    token,
    enabled: !!user && !!strategyId,
  });

  // Subscribe to intent updates for this strategy
  useEffect(() => {
    if (!isConnected || !strategyId) return;

    const unsubscribe = subscribe('order_update', (event: WebSocketEvent) => {
      if (event.payload.strategy_id === strategyId) {
        // Add new intent to the beginning of the list
        setIntents((prev) => {
          const newIntent = event.payload as ExecutionIntent;
          // Check if intent already exists
          const exists = prev.some((i) => i.id === newIntent.id);
          if (exists) {
            // Update existing intent
            return prev.map((i) => (i.id === newIntent.id ? newIntent : i));
          }
          // Add new intent at the beginning
          return [newIntent, ...prev].slice(0, 20); // Keep only last 20
        });
        setLastUpdate(new Date());
      }
    });

    return unsubscribe;
  }, [isConnected, strategyId, subscribe]);

  // Subscribe to metric updates
  useEffect(() => {
    if (!isConnected || !strategyId) return;

    const unsubscribe = subscribe('system_status', (event: WebSocketEvent) => {
      if (event.payload.type === 'strategy_metrics' && event.payload.strategy_id === strategyId) {
        setMetrics(event.payload.metrics || []);
        setLastUpdate(new Date());
      }
    });

    return unsubscribe;
  }, [isConnected, strategyId, subscribe]);

  return {
    intents,
    metrics,
    isConnected,
    lastUpdate,
    setIntents,
    setMetrics,
  };
}

