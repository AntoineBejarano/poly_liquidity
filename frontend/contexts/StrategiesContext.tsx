'use client';

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { initApiClient, createTokenGetter } from '@/lib/api';
import type { Strategy } from '@/types/strategy';

interface StrategiesContextValue {
  strategies: Strategy[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  clearError: () => void;
}

const StrategiesContext = createContext<StrategiesContextValue | null>(null);

export function StrategiesProvider({ children }: { children: ReactNode }) {
  const user = useUser();
  const stackApp = useStackApp();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStrategies = useCallback(async () => {
    if (!user || !stackApp) return;

    setLoading(true);
    setError(null);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      const data = await api.get<Strategy[]>('/api/strategies/summary', true);
      setStrategies(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar estrategias');
      setStrategies([]);
    } finally {
      setLoading(false);
    }
  }, [user, stackApp]);

  useEffect(() => {
    if (!user || !stackApp) return;
    fetchStrategies();
  }, [fetchStrategies, user, stackApp]);

  const value: StrategiesContextValue = {
    strategies,
    loading,
    error,
    refetch: fetchStrategies,
    clearError: () => setError(null),
  };

  return (
    <StrategiesContext.Provider value={value}>
      {children}
    </StrategiesContext.Provider>
  );
}

export function useStrategies() {
  const ctx = useContext(StrategiesContext);
  if (!ctx) {
    throw new Error('useStrategies must be used within StrategiesProvider');
  }
  return ctx;
}

/** Hook opcional: devuelve null si no hay provider (para componentes que pueden estar fuera) */
export function useStrategiesOptional() {
  return useContext(StrategiesContext);
}
