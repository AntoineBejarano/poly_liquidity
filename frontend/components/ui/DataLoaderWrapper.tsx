import { ReactNode } from 'react';
import { useDataLoader, UseDataLoaderOptions } from '@/hooks/useDataLoader';
import { RefreshingIndicator } from './RefreshingIndicator';

export interface DataLoaderWrapperProps<T> {
  /**
   * Función para cargar datos
   */
  fetchFn: () => Promise<T>;
  
  /**
   * Intervalo de refresco en milisegundos
   */
  refreshInterval?: number;
  
  /**
   * Dependencias que trigger recarga
   */
  dependencies?: any[];
  
  /**
   * Si está habilitado
   */
  enabled?: boolean;
  
  /**
   * Componente skeleton para mostrar durante carga inicial
   */
  skeleton?: React.ComponentType;
  
  /**
   * Render function que recibe los datos
   */
  children: (data: T | null, isLoading: boolean, isRefreshing: boolean) => ReactNode;
  
  /**
   * Componente de error personalizado
   */
  errorComponent?: React.ComponentType<{ error: Error; retry: () => void }>;
  
  /**
   * Mostrar indicador de refresco
   */
  showRefreshingIndicator?: boolean;
  
  /**
   * Posición del indicador de refresco
   */
  refreshingIndicatorPosition?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  
  /**
   * Callback de error
   */
  onError?: (error: Error) => void;
  
  /**
   * Callback de éxito
   */
  onSuccess?: (data: T) => void;
}

/**
 * Wrapper genérico para componentes con carga de datos.
 * 
 * Maneja automáticamente:
 * - Skeletons durante carga inicial
 * - Indicadores de refresco
 * - Manejo de errores
 * 
 * @example
 * ```tsx
 * <DataLoaderWrapper
 *   fetchFn={() => api.get('/data')}
 *   refreshInterval={10000}
 *   skeleton={MyComponentSkeleton}
 *   errorComponent={MyErrorComponent}
 * >
 *   {(data, isLoading, isRefreshing) => (
 *     <div className="relative">
 *       {isRefreshing && <RefreshingIndicator />}
 *       <MyContent data={data} />
 *     </div>
 *   )}
 * </DataLoaderWrapper>
 * ```
 */
export function DataLoaderWrapper<T>({
  fetchFn,
  refreshInterval,
  dependencies,
  enabled = true,
  skeleton: Skeleton,
  children,
  errorComponent: ErrorComponent,
  showRefreshingIndicator = true,
  refreshingIndicatorPosition = 'top-right',
  onError,
  onSuccess,
}: DataLoaderWrapperProps<T>) {
  const { data, isInitialLoading, isRefreshing, error, refetch } = useDataLoader({
    fetchFn,
    refreshInterval,
    dependencies,
    enabled,
    onError,
    onSuccess,
  });

  // Mostrar error si existe y hay componente de error
  if (error && ErrorComponent) {
    return <ErrorComponent error={error} retry={refetch} />;
  }

  // Mostrar skeleton durante carga inicial
  if (isInitialLoading && Skeleton) {
    return <Skeleton />;
  }

  // Renderizar indicador de refresco si está habilitado
  const positionClasses = {
    'top-right': 'absolute top-2 right-2 z-10',
    'top-left': 'absolute top-2 left-2 z-10',
    'bottom-right': 'absolute bottom-2 right-2 z-10',
    'bottom-left': 'absolute bottom-2 left-2 z-10',
  };

  return (
    <div className="relative">
      {showRefreshingIndicator && isRefreshing && !isInitialLoading && (
        <div className={positionClasses[refreshingIndicatorPosition]}>
          <RefreshingIndicator isRefreshing={true} />
        </div>
      )}
      {children(data, isInitialLoading, isRefreshing)}
    </div>
  );
}

