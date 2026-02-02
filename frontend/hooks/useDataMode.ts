'use client';

import { useDataModeContext } from '@/contexts/DataModeContext';

/**
 * Hook para el modo de datos: Demo (mock), Simulación (DRY_RUN/sim), Real (API).
 * Usar en páginas y loaders para decidir si mostrar datos mock o llamar API.
 */
export function useDataMode() {
  return useDataModeContext();
}
