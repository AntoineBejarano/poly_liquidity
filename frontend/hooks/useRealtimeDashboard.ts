'use client';

import { useEffect, useState } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { useWebSocket } from './useWebSocket';
import { createTokenGetter } from '@/lib/api';
import { WebSocketEvent } from '@/lib/websocket';
import { Strategy } from '@/types/strategy';

interface DashboardData {
  equity: number;
  realized_pnl: number;
  unrealized_pnl: number;
  global_exposure: number;
  active_markets: number;
  system_active: boolean;
}

export function useRealtimeDashboard() {
  const user = useUser();
  const stackApp = useStackApp();
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const token = user ? (createTokenGetter(user, stackApp)() || null) : null;

  const { isConnected, subscribe } = useWebSocket({
    token,
    enabled: !!user,
  });

  // Subscribe to strategy updates
  useEffect(() => {
    if (!isConnected) return;

    const unsubscribe = subscribe('system_status', (event: WebSocketEvent) => {
      if (event.payload.type === 'dashboard_update') {
        setDashboardData(event.payload.data);
        setLastUpdate(new Date());
      }
    });

    return unsubscribe;
  }, [isConnected, subscribe]);

  // Subscribe to strategy updates
  useEffect(() => {
    if (!isConnected) return;

    const unsubscribe = subscribe('system_status', (event: WebSocketEvent) => {
      if (event.payload.type === 'strategy_update') {
        setStrategies((prev) => {
          const updated = [...prev];
          const index = updated.findIndex((s) => s.id === event.payload.data.id);
          if (index >= 0) {
            updated[index] = { ...updated[index], ...event.payload.data };
          } else {
            updated.push(event.payload.data);
          }
          return updated;
        });
        setLastUpdate(new Date());
      }
    });

    return unsubscribe;
  }, [isConnected, subscribe]);

  return {
    dashboardData,
    strategies,
    isConnected,
    lastUpdate,
    setDashboardData,
    setStrategies,
  };
}

