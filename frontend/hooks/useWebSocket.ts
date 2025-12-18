'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketClient, WebSocketEvent, WebSocketEventType } from '@/lib/websocket';

interface UseWebSocketOptions {
  url?: string;
  token: string | null;
  enabled?: boolean;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

export function useWebSocket(options: UseWebSocketOptions) {
  const { url, token, enabled = true, onConnect, onDisconnect, onError } = options;
  const [isConnected, setIsConnected] = useState(false);
  const clientRef = useRef<WebSocketClient | null>(null);
  const handlersRef = useRef<Map<WebSocketEventType, Set<(event: WebSocketEvent) => void>>>(new Map());
  const isConnectedRef = useRef(false);

  // Get WebSocket URL from environment or default
  const wsUrl = url || (typeof window !== 'undefined' 
    ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host.replace(':3000', ':8000')}/ws/stream`
    : 'ws://localhost:8000/ws/stream');

  useEffect(() => {
    if (!enabled || !token) {
      return;
    }

    // Create WebSocket client
    const client = new WebSocketClient(wsUrl, token);
    clientRef.current = client;

    // Set up connection handlers using the client's internal event system
    const connectHandler = () => {
      isConnectedRef.current = true;
      setIsConnected(true);
      onConnect?.();
    };

    const disconnectHandler = () => {
      isConnectedRef.current = false;
      setIsConnected(false);
      onDisconnect?.();
    };

    // Subscribe to connection status by monitoring the client
    // We'll use a polling approach to check connection status
    const checkConnection = setInterval(() => {
      const connected = client.isConnected();
      if (connected !== isConnectedRef.current) {
        if (connected) {
          connectHandler();
        } else {
          disconnectHandler();
        }
      }
    }, 1000);

    // Connect
    client.connect();

    // Register all existing handlers
    handlersRef.current.forEach((handlers, eventType) => {
      handlers.forEach((handler) => {
        client.on(eventType, handler);
      });
    });

    return () => {
      clearInterval(checkConnection);
      client.disconnect();
      setIsConnected(false);
      isConnectedRef.current = false;
    };
  }, [enabled, token, wsUrl, onConnect, onDisconnect, onError]);

  const subscribe = useCallback((eventType: WebSocketEventType, handler: (event: WebSocketEvent) => void) => {
    if (!handlersRef.current.has(eventType)) {
      handlersRef.current.set(eventType, new Set());
    }
    handlersRef.current.get(eventType)!.add(handler);

    // If client is already connected, register handler immediately
    if (clientRef.current) {
      clientRef.current.on(eventType, handler);
    }

    // Return unsubscribe function
    return () => {
      handlersRef.current.get(eventType)?.delete(handler);
      clientRef.current?.off(eventType, handler);
    };
  }, []);

  const send = useCallback((data: string) => {
    clientRef.current?.send(data);
  }, []);

  return {
    isConnected,
    subscribe,
    send,
  };
}

