import { useState, useEffect, useRef, useCallback } from 'react';

export interface UseDataLoaderOptions<T> {
  /** Receives AbortSignal to cancel in-flight request when deps change or unmount. Optional so existing callers can ignore. */
  fetchFn: (signal?: AbortSignal) => Promise<T>;
  dependencies?: any[];
  refreshInterval?: number;
  enabled?: boolean;
  onError?: (error: Error) => void;
  onSuccess?: (data: T) => void;
}

export interface UseDataLoaderResult<T> {
  data: T | null;
  isInitialLoading: boolean;
  isRefreshing: boolean;
  error: Error | null;
  errorCount: number;
  refetch: () => Promise<void>;
}

/**
 * Hook robusto para cargar datos con manejo de estados de carga inicial vs actualización.
 * 
 * Características:
 * - `isInitialLoading`: Solo true en el primer fetch
 * - `isRefreshing`: True en actualizaciones automáticas de fondo
 * - `AbortController`: Limpieza de efectos para evitar Race Conditions
 * - `errorCount`: Solo muestra alertas después de 3 fallos consecutivos
 * - Mantiene datos anteriores si un refresh falla
 */
export function useDataLoader<T>({
  fetchFn,
  dependencies = [],
  refreshInterval,
  enabled = true,
  onError,
  onSuccess,
}: UseDataLoaderOptions<T>): UseDataLoaderResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [errorCount, setErrorCount] = useState(0);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  
  // AbortController para cancelar requests en curso
  const abortControllerRef = useRef<AbortController | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  const loadData = useCallback(async (isRefresh = false) => {
    // Cancelar request anterior si existe
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    // Crear nuevo AbortController
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;
    
    try {
      if (isRefresh) {
        setIsRefreshing(true);
      } else {
        setIsInitialLoading(true);
      }
      
      setError(null);
      
      const result = await fetchFn(signal);
      
      // Verificar si el componente sigue montado y la request no fue cancelada
      if (!isMountedRef.current || signal.aborted) {
        return;
      }
      
      setData(result);
      setErrorCount(0); // Resetear contador de errores en éxito
      setHasLoadedOnce(true);
      
      if (onSuccess) {
        onSuccess(result);
      }
    } catch (err) {
      // Ignorar errores de abort
      if (signal.aborted || !isMountedRef.current) {
        return;
      }
      
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      
      // Incrementar contador de errores
      setErrorCount(prev => {
        const newCount = prev + 1;
        // Solo llamar onError después de 3 errores consecutivos
        if (newCount >= 3 && onError) {
          onError(error);
        }
        return newCount;
      });
      
      // Si es un refresh que falla, mantener datos anteriores
      // Solo limpiar datos si es la carga inicial
      if (!isRefresh && hasLoadedOnce) {
        // Mantener datos anteriores
      } else if (!hasLoadedOnce) {
        // Primera carga falló, limpiar datos
        setData(null);
      }
    } finally {
      if (!signal.aborted && isMountedRef.current) {
        setIsInitialLoading(false);
        setIsRefreshing(false);
      }
    }
  }, [fetchFn, onError, onSuccess, hasLoadedOnce]);

  // Carga inicial
  useEffect(() => {
    if (!enabled) {
      setIsInitialLoading(false);
      return;
    }
    
    isMountedRef.current = true;
    loadData(false);
    
    return () => {
      // Cleanup: abortar request en curso
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [enabled, ...dependencies]);

  // Refresh periódico (solo si ya cargó una vez y está habilitado)
  useEffect(() => {
    if (!enabled || !hasLoadedOnce || !refreshInterval) {
      return;
    }
    
    intervalRef.current = setInterval(() => {
      loadData(true); // Refresh silencioso
    }, refreshInterval);
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [enabled, hasLoadedOnce, refreshInterval, loadData]);

  // Cleanup al desmontar
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const refetch = useCallback(async () => {
    await loadData(true);
  }, [loadData]);

  return {
    data,
    isInitialLoading,
    isRefreshing,
    error,
    errorCount,
    refetch,
  };
}

