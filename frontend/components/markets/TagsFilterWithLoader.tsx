'use client';

import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
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
  const { isDemo } = useDataMode();

  const { data, renderSkeleton, renderRefreshingIndicator } = useComponentDataLoader<TagsFilterData>({
    fetchFn: async () => {
      if (!user || !stackApp) {
        throw new Error('User not authenticated');
      }
      if (isDemo) {
        return { tags: [] };
      }
      if (!isConnected) {
        return { tags: [] };
      }
      const api = initApiClient(createTokenGetter(user, stackApp));
      const tagsData = await api.get<Tag[]>('/tags');

      return {
        tags: tagsData ?? [],
      };
    },
    dependencies: [user, stackApp, isConnected, isDemo],
    refreshInterval: isDemo ? 0 : 30000,
    enabled: !!user && !!stackApp && (isConnected || isDemo),
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

