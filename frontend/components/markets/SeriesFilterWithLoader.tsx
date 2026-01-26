'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { SeriesFilter } from './SeriesFilter';
import { CardSkeleton } from '@/components/ui/skeleton';

interface Series {
  series_id: string;
  polymarket_series_id: string;
  name: string;
  slug: string | null;
  description: string | null;
  series_type: string | null;
  recurrence: string | null;
  markets_count: number;
  created_at: string;
  updated_at: string;
}

interface SeriesFilterData {
  series: Series[];
}

interface SeriesFilterWithLoaderProps {
  selectedSeries: string;
  onSelectionChange: (seriesId: string) => void;
}

export function SeriesFilterWithLoader({ selectedSeries, onSelectionChange }: SeriesFilterWithLoaderProps) {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<SeriesFilterData>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected) {
        throw new Error('User not authenticated or backend not connected');
      }

      const api = initApiClient(createTokenGetter(user, stackApp));
      const seriesData = await api.get<Series[]>('/series').catch(() => []);

      return {
        series: seriesData,
      };
    },
    dependencies: [user, stackApp, isConnected],
    refreshInterval: 30000, // Series cambian menos frecuentemente
    enabled: !!user && !!stackApp && isConnected,
    showSkeleton: false, // No mostrar skeleton para filtros
    showRefreshingIndicator: false,
  });

  const series = data?.series || [];

  if (series.length === 0 && !renderSkeleton) {
    return null;
  }

  return (
    <div className="relative">
      {renderRefreshingIndicator}
      {renderSkeleton ? (
        <CardSkeleton />
      ) : (
        <SeriesFilter series={series} selectedSeries={selectedSeries} onSelectionChange={onSelectionChange} />
      )}
    </div>
  );
}

