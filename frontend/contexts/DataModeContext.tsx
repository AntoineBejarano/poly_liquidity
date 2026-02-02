'use client';

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';

export type DataMode = 'demo' | 'simulation' | 'real';

const STORAGE_KEY = 'poly_liquidity_data_mode';

interface DataModeContextValue {
  dataMode: DataMode;
  setDataMode: (mode: DataMode) => void;
  isDemo: boolean;
  isSimulation: boolean;
  isReal: boolean;
}

const DataModeContext = createContext<DataModeContextValue | null>(null);

function getStoredMode(): DataMode {
  if (typeof window === 'undefined') return 'real';
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'demo' || stored === 'simulation' || stored === 'real') return stored;
  } catch {
    // ignore
  }
  return 'real';
}

export function DataModeProvider({ children }: { children: ReactNode }) {
  const [dataMode, setDataModeState] = useState<DataMode>('real');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setDataModeState(getStoredMode());
    setMounted(true);
  }, []);

  const setDataMode = useCallback((mode: DataMode) => {
    setDataModeState(mode);
    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      // ignore
    }
  }, []);

  const value: DataModeContextValue = {
    dataMode: mounted ? dataMode : 'real',
    setDataMode,
    isDemo: dataMode === 'demo',
    isSimulation: dataMode === 'simulation',
    isReal: dataMode === 'real',
  };

  return (
    <DataModeContext.Provider value={value}>
      {children}
    </DataModeContext.Provider>
  );
}

export function useDataModeContext(): DataModeContextValue {
  const ctx = useContext(DataModeContext);
  if (!ctx) {
    throw new Error('useDataModeContext must be used within DataModeProvider');
  }
  return ctx;
}
