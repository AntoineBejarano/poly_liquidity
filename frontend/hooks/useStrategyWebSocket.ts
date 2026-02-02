'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { createTokenGetter } from '@/lib/api';

const WS_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL?.replace('http://', 'ws://').replace('https://', 'wss://') || 'ws://localhost:8000';

export interface StrategyWebSocketEvent {
  type: string;
  strategy_id: string;
  payload: any;
  timestamp?: string;
}

export function useStrategyWebSocket(strategyId: string | null) {
  const user = useUser();
  const stackApp = useStackApp();
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<StrategyWebSocketEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const intentionalCloseRef = useRef(false);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 1000;

  const connect = useCallback(() => {
    if (!strategyId || !user) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    intentionalCloseRef.current = false;

    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
    }

    const token = createTokenGetter(user, stackApp)();
    const wsUrl = `${WS_BASE_URL}/ws/strategies/${strategyId}${token ? `?token=${token}` : ''}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`[StrategyWebSocket] Connected to strategy ${strategyId}`);
        setIsConnected(true);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data: StrategyWebSocketEvent = JSON.parse(event.data);
          setLastEvent(data);
          if (data.type === 'pong') {
            // Connection is alive
          }
        } catch (error) {
          console.error('[StrategyWebSocket] Error parsing message:', error);
        }
      };

      ws.onerror = () => {
        // Browser often gives an empty event; avoid noisy "error: {}"
        if (ws.readyState !== WebSocket.CLOSING && ws.readyState !== WebSocket.CLOSED) {
          console.warn('[StrategyWebSocket] WebSocket connection error');
        }
      };

      ws.onclose = () => {
        console.log(`[StrategyWebSocket] Disconnected from strategy ${strategyId}`);
        setIsConnected(false);
        wsRef.current = null;

        if (intentionalCloseRef.current) return;

        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`[StrategyWebSocket] Reconnecting (attempt ${reconnectAttempts.current})...`);
            connect();
          }, reconnectDelay * reconnectAttempts.current);
        } else {
          console.warn('[StrategyWebSocket] Max reconnection attempts reached');
        }
      };
    } catch (error) {
      console.error('[StrategyWebSocket] Error creating WebSocket:', error);
    }
  }, [strategyId, user, stackApp]);

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'ping' }));
    }
  }, []);

  useEffect(() => {
    if (strategyId && user) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [strategyId, user, connect, disconnect]);

  // Send ping every 30 seconds to keep connection alive
  useEffect(() => {
    if (!isConnected) return;

    const pingInterval = setInterval(sendPing, 30000);
    return () => clearInterval(pingInterval);
  }, [isConnected, sendPing]);

  return {
    isConnected,
    lastEvent,
    reconnect: connect,
  };
}
