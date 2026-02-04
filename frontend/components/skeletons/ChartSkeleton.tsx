'use client';

import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader } from '@/components/ui/card';

interface ChartSkeletonProps {
  height?: number;
  showTitle?: boolean;
}

export function ChartSkeleton({ height = 280, showTitle = true }: ChartSkeletonProps) {
  return (
    <Card>
      {showTitle && (
        <CardHeader>
          <Skeleton className="h-6 w-56" />
        </CardHeader>
      )}
      <CardContent>
        <div style={{ height: `${height}px` }}><Skeleton className="w-full h-full" /></div>
      </CardContent>
    </Card>
  );
}
