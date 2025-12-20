'use client';

import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { EmptyState } from '@/components/EmptyState';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { Strategy } from '@/types/strategy';
import { Search, TrendingUp, PlusCircle } from 'lucide-react';
import { TableSkeleton } from '@/components/skeletons/TableSkeleton';
import Link from 'next/link';

export default function StrategiesPage() {
  const router = useRouter();
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');

  const fetchStrategies = async () => {
    if (!user || !isConnected) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const api = initApiClient(createTokenGetter(user, stackApp));
      const data = await api.get<Strategy[]>('/strategies');
      setStrategies(data);
    } catch (err) {
      console.error('Error fetching strategies:', err);
      setError(err instanceof Error ? err.message : 'Failed to load strategies');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStrategies();
  }, [user, stackApp, isConnected]);

  // Filtered strategies
  const filteredStrategies = useMemo(() => {
    return strategies.filter((strategy) => {
      // Search filter
      const matchesSearch = strategy.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           strategy.description?.toLowerCase().includes(searchQuery.toLowerCase());

      // Status filter
      const matchesStatus = statusFilter === 'all' ||
                           (statusFilter === 'active' && strategy.is_active) ||
                           (statusFilter === 'inactive' && !strategy.is_active);

      return matchesSearch && matchesStatus;
    });
  }, [strategies, searchQuery, statusFilter]);

  if (!user) {
    return null;
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-h2">Strategies</h1>
            <p className="text-body text-muted-foreground mt-1">
              Manage your graph-based trading strategies
            </p>
          </div>
          <Button onClick={() => router.push('/strategies/new')} size="lg">
            <PlusCircle className="mr-2 h-4 w-4" />
            New Strategy
          </Button>
        </div>

        {/* Error Banner */}
        {error && (
          <ErrorBanner
            error={error}
            onRetry={fetchStrategies}
            onDismiss={() => setError(null)}
          />
        )}

        {/* Loading State */}
        {loading && <TableSkeleton rows={5} columns={3} />}

        {/* Content */}
        {!loading && !error && (
          <>
            {strategies.length === 0 ? (
              <EmptyState
                icon={TrendingUp}
                title="No strategies yet"
                description="Create your first algorithmic trading strategy to get started with automated trading."
                action={{
                  label: "Create Strategy",
                  onClick: () => router.push('/strategies/new')
                }}
              />
            ) : (
              <>
                {/* Search & Filters */}
                <div className="flex gap-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search strategies..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9"
                    />
                  </div>

                  <Select value={statusFilter} onValueChange={(value: any) => setStatusFilter(value)}>
                    <SelectTrigger className="w-[180px]">
                      <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Strategies</SelectItem>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="inactive">Inactive</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Results count */}
                <div className="text-caption">
                  {filteredStrategies.length === strategies.length ? (
                    <span>{strategies.length} {strategies.length === 1 ? 'strategy' : 'strategies'}</span>
                  ) : (
                    <span>
                      {filteredStrategies.length} of {strategies.length} strategies
                    </span>
                  )}
                </div>

                {/* Strategies List */}
                {filteredStrategies.length === 0 ? (
                  <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center p-12 text-center">
                      <Search className="h-8 w-8 text-muted-foreground mb-3" />
                      <p className="text-body text-muted-foreground">
                        No strategies match your filters
                      </p>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setSearchQuery('');
                          setStatusFilter('all');
                        }}
                        className="mt-3"
                      >
                        Clear filters
                      </Button>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="grid gap-4">
                    {filteredStrategies.map((strategy) => (
                      <Link key={strategy.id} href={`/strategies/${strategy.id}`}>
                        <Card className="transition-colors hover:border-primary/50 hover:shadow-md">
                          <CardHeader>
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <h3 className="text-h3 truncate">
                                    {strategy.name}
                                  </h3>
                                  {strategy.is_active ? (
                                    <Badge variant="default" className="bg-green-500 dark:bg-green-600">
                                      Active
                                    </Badge>
                                  ) : (
                                    <Badge variant="secondary">Inactive</Badge>
                                  )}
                                </div>
                                {strategy.description && (
                                  <p className="text-body text-muted-foreground line-clamp-2">
                                    {strategy.description}
                                  </p>
                                )}
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent className="pt-0">
                            <div className="flex items-center gap-6 text-caption">
                              <span>Version {strategy.version}</span>
                              <span>
                                {strategy.support_graphs?.length || 0} Support Graph
                                {(strategy.support_graphs?.length || 0) !== 1 ? 's' : ''}
                              </span>
                            </div>
                          </CardContent>
                        </Card>
                      </Link>
                    ))}
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </Layout>
  );
}
