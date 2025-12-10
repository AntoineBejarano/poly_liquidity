'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@stackframe/stack';
import { initApiClient } from '@/lib/api';

export function useBackendConnection() {
  const user = useUser();
  const [isConnected, setIsConnected] = useState(false);
  const [isChecking, setIsChecking] = useState(false);

  useEffect(() => {
    if (!user) {
      setIsConnected(false);
      return;
    }

    const checkConnection = async () => {
      setIsChecking(true);
      try {
        const api = initApiClient(() => user.accessToken || null);
        await api.get('/health');
        setIsConnected(true);
      } catch (err) {
        setIsConnected(false);
      } finally {
        setIsChecking(false);
      }
    };

    // Check immediately
    checkConnection();

    // Check every 10 seconds (less aggressive)
    const interval = setInterval(checkConnection, 10000);
    return () => clearInterval(interval);
  }, [user]);

  return { isConnected, isChecking };
}

