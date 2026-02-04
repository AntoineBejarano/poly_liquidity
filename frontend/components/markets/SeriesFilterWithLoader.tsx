'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
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
  const { isDemo } = useDataMode();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<SeriesFilterData>({
    fetchFn: async () => {
      if (!user || !stackApp) {
        throw new Error('User not authenticated');
      }
      if (isDemo) {
        return { series: [] };
      }
      if (!isConnected) {
        return { series: [] };
      }
      const api = initApiClient(createTokenGetter(user, stackApp));
      const seriesData = await api.get<Series[]>('/series');

      return {
        series: seriesData ?? [],
      };
    },
    dependencies: [user, stackApp, isConnected, isDemo],
    refreshInterval: isDemo ? 0 : 30000,
    enabled: !!user && !!stackApp && (isConnected || isDemo),
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

