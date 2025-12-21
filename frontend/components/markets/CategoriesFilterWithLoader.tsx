'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useMemo } from 'react';

interface Market {
  market_id: string;
  category: string | null;
}

interface MarketsData {
  markets: Market[];
}

interface CategoriesFilterWithLoaderProps {
  categoryFilter: string;
  onCategoryChange: (category: string) => void;
}

export function CategoriesFilterWithLoader({ categoryFilter, onCategoryChange }: CategoriesFilterWithLoaderProps) {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();

  const { data } = useComponentDataLoader<MarketsData>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected) {
        throw new Error('User not authenticated or backend not connected');
      }

      const api = initApiClient(createTokenGetter(user, stackApp));
      const marketsData = await api.get<Market[]>('/markets').catch(() => []);

      return {
        markets: marketsData,
      };
    },
    dependencies: [user, stackApp, isConnected],
    refreshInterval: 30000, // Categories cambian menos frecuentemente
    enabled: !!user && !!stackApp && isConnected,
    showSkeleton: false,
    showRefreshingIndicator: false,
  });

  const categories = useMemo(() => {
    const markets = data?.markets || [];
    return Array.from(new Set(markets.map(m => m.category).filter(Boolean))) as string[];
  }, [data?.markets]);

  return (
    <select
      value={categoryFilter}
      onChange={(e) => onCategoryChange(e.target.value)}
      className="px-2 py-1.5 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-slate-400"
    >
      <option value="all">Todas las categorías</option>
      {categories.map(cat => (
        <option key={cat} value={cat}>{cat}</option>
      ))}
    </select>
  );
}

