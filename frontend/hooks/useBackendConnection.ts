'use client';

import { useEffect, useState, useRef } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { initApiClient, createTokenGetter } from '@/lib/api';

export function useBackendConnection() {
  const user = useUser();
  const stackApp = useStackApp();
  const [isConnected, setIsConnected] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const isConnectedRef = useRef(false);

  useEffect(() => {
    if (!user || !stackApp) {
      setIsConnected(false);
      isConnectedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    const checkConnection = async () => {
      setIsChecking(true);
      try {
        const api = initApiClient(createTokenGetter(user, stackApp));
        // Usar modo silencioso para health check - no loguear errores esperados
        await api.get('/health', true);
        const wasConnected = isConnectedRef.current;
        setIsConnected(true);
        isConnectedRef.current = true;
        
        // Si cambió de desconectado a conectado, re-programar con intervalo más largo
        if (!wasConnected && intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
          scheduleCheck();
        }
      } catch (err) {
        const wasConnected = isConnectedRef.current;
        setIsConnected(false);
        isConnectedRef.current = false;
        
        // Si cambió de conectado a desconectado, re-programar con intervalo más corto
        if (wasConnected && intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
          scheduleCheck();
        }
      } finally {
        setIsChecking(false);
      }
    };

    const scheduleCheck = () => {
      // Limpiar intervalo anterior
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      
      // Usar el estado actual para determinar el intervalo
      // 3 segundos si no está conectado, 30 segundos si está conectado
      const intervalMs = isConnectedRef.current ? 30000 : 3000;
      
      intervalRef.current = setInterval(checkConnection, intervalMs);
    };

    // Check immediately
    checkConnection();
    
    // Programar siguiente check después de un pequeño delay
    const timeoutId = setTimeout(scheduleCheck, 1000);
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      clearTimeout(timeoutId);
    };
  }, [user, stackApp]);

  return { isConnected, isChecking };
}

