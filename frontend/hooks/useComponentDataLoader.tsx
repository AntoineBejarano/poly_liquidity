'use client';

import { ReactNode } from 'react';
import { useDataLoader, UseDataLoaderOptions, UseDataLoaderResult } from './useDataLoader';
import { RefreshingIndicator } from '@/components/ui/RefreshingIndicator';

export interface UseComponentDataLoaderOptions<T> extends Omit<UseDataLoaderOptions<T>, 'onError' | 'onSuccess'> {
  /**
   * Mostrar skeleton durante carga inicial
   */
  showSkeleton?: boolean;
  
  /**
   * Componente skeleton personalizado
   */
  skeletonComponent?: React.ComponentType;
  
  /**
   * Mostrar indicador de refresco
   */
  showRefreshingIndicator?: boolean;
  
  /**
   * Posición del indicador de refresco ('top-right' | 'top-left' | 'bottom-right' | 'bottom-left')
   */
  refreshingIndicatorPosition?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  
  /**
   * Callback de error personalizado
   */
  onError?: (error: Error) => void;
  
  /**
   * Callback de éxito personalizado
   */
  onSuccess?: (data: T) => void;
}

export interface UseComponentDataLoaderResult<T> extends UseDataLoaderResult<T> {
  /**
   * Componente skeleton para renderizar durante carga inicial
   */
  renderSkeleton: ReactNode | null;
  
  /**
   * Componente indicador de refresco para renderizar
   */
  renderRefreshingIndicator: ReactNode | null;
}

/**
 * Hook especializado para componentes que necesitan carga separada.
 * 
 * Extiende useDataLoader con helpers para renderizado de skeletons e indicadores.
 * 
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader({
 *     fetchFn: () => api.get('/data'),
 *     refreshInterval: 10000,
 *     showSkeleton: true,
 *     skeletonComponent: MyComponentSkeleton,
 *     showRefreshingIndicator: true,
 *   });
 * 
 *   if (renderSkeleton) return renderSkeleton;
 * 
 *   return (
 *     <div className="relative">
 *       {renderRefreshingIndicator}
 *       <MyContent data={data} />
 *     </div>
 *   );
 * }
 * ```
 */
export function useComponentDataLoader<T>({
  showSkeleton = true,
  skeletonComponent: SkeletonComponent,
  showRefreshingIndicator = true,
  refreshingIndicatorPosition = 'top-right',
  onError,
  onSuccess,
  ...dataLoaderOptions
}: UseComponentDataLoaderOptions<T>): UseComponentDataLoaderResult<T> {
  const { data, isInitialLoading, isRefreshing, error, errorCount, refetch } = useDataLoader({
    ...dataLoaderOptions,
    onError,
    onSuccess,
  });

  // Render skeleton durante carga inicial
  const renderSkeleton = showSkeleton && isInitialLoading && SkeletonComponent
    ? <SkeletonComponent />
    : null;

  // Render refreshing indicator
  let renderRefreshingIndicator: ReactNode | null = null;
  if (showRefreshingIndicator && isRefreshing && !isInitialLoading) {
    const positionClasses = {
      'top-right': 'absolute top-2 right-2 z-10',
      'top-left': 'absolute top-2 left-2 z-10',
      'bottom-right': 'absolute bottom-2 right-2 z-10',
      'bottom-left': 'absolute bottom-2 left-2 z-10',
    };

    renderRefreshingIndicator = (
      <div className={positionClasses[refreshingIndicatorPosition]}>
        <RefreshingIndicator isRefreshing={true} />
      </div>
    );
  }

  return {
    data,
    isInitialLoading,
    isRefreshing,
    error,
    errorCount,
    refetch,
    renderSkeleton,
    renderRefreshingIndicator,
  };
}

