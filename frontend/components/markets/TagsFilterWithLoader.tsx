'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { TagFilter } from './TagFilter';
import { CardSkeleton } from '@/components/ui/skeleton';

interface Tag {
  tag_id: string;
  name: string;
}

interface TagsFilterData {
  tags: Tag[];
}

interface TagsFilterWithLoaderProps {
  selectedTags: string[];
  onSelectionChange: (tags: string[]) => void;
}

export function TagsFilterWithLoader({ selectedTags, onSelectionChange }: TagsFilterWithLoaderProps) {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<TagsFilterData>({
    fetchFn: async () => {
      if (!user || !stackApp || !isConnected) {
        throw new Error('User not authenticated or backend not connected');
      }

      const api = initApiClient(createTokenGetter(user, stackApp));
      const tagsData = await api.get<Tag[]>('/tags').catch(() => []);

      return {
        tags: tagsData,
      };
    },
    dependencies: [user, stackApp, isConnected],
    refreshInterval: 30000, // Tags cambian menos frecuentemente
    enabled: !!user && !!stackApp && isConnected,
    showSkeleton: false, // No mostrar skeleton para filtros
    showRefreshingIndicator: false,
  });

  const tags = data?.tags || [];

  if (tags.length === 0 && !renderSkeleton) {
    return null;
  }

  return (
    <div className="relative">
      {renderRefreshingIndicator}
      {renderSkeleton ? (
        <CardSkeleton />
      ) : (
        <TagFilter tags={tags} selectedTags={selectedTags} onSelectionChange={onSelectionChange} />
      )}
    </div>
  );
}

