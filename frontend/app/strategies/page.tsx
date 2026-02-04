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
import { Search, TrendingUp, PlusCircle, Pencil, Trash2, Play, Square } from 'lucide-react';
import { TableSkeleton } from '@/components/skeletons/TableSkeleton';
import Link from 'next/link';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

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
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const fetchStrategies = async () => {
    if (!user || !isConnected) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const api = initApiClient(createTokenGetter(user, stackApp));
      const data = await api.get<Strategy[]>('/api/strategies/summary');
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

  const handleActivate = async (strategyId: string) => {
    if (!user || !stackApp) return;
    setActionLoadingId(strategyId);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.post(`/api/strategies/${strategyId}/activate`);
      setStrategies((prev) =>
        prev.map((s) => (s.id === strategyId ? { ...s, is_active: true } : s))
      );
    } catch (err) {
      console.error('Error activating strategy:', err);
      alert(err instanceof Error ? err.message : 'Error al activar');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleDeactivate = async (strategyId: string) => {
    if (!user || !stackApp) return;
    setActionLoadingId(strategyId);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.post(`/api/strategies/${strategyId}/deactivate`);
      setStrategies((prev) =>
        prev.map((s) => (s.id === strategyId ? { ...s, is_active: false } : s))
      );
    } catch (err) {
      console.error('Error deactivating strategy:', err);
      alert(err instanceof Error ? err.message : 'Error al pausar');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleDelete = async (strategyId: string) => {
    if (!user || !stackApp) return;
    setActionLoadingId(strategyId);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.delete(`/api/strategies/${strategyId}`);
      setStrategies((prev) => prev.filter((s) => s.id !== strategyId));
      setDeleteConfirmId(null);
    } catch (err) {
      console.error('Error deleting strategy:', err);
      alert(err instanceof Error ? err.message : 'Error al eliminar');
    } finally {
      setActionLoadingId(null);
    }
  };

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
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-h2">Strategies</h1>
            <p className="text-body text-muted-foreground mt-1">
              Manage your graph-based trading strategies
            </p>
          </div>
          <Button onClick={() => router.push('/strategies/new')} size="lg" className="w-full sm:w-auto">
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
                <div className="flex flex-col sm:flex-row gap-3">
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
                  <SelectTrigger className="w-full sm:w-[180px]">
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
                    {filteredStrategies.map((strategy) => {
                      const isLoading = actionLoadingId === strategy.id;
                      return (
                        <Card
                          key={strategy.id}
                          className="transition-colors hover:border-primary/50 hover:shadow-md"
                        >
                          <CardHeader>
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1 flex-wrap">
                                  <Link
                                    href={`/strategies/${strategy.id}`}
                                    className="text-h3 truncate hover:underline"
                                  >
                                    {strategy.name}
                                  </Link>
                                  {strategy.is_active ? (
                                    <Badge variant="default" className="bg-green-500 dark:bg-green-600">
                                      Activa
                                    </Badge>
                                  ) : (
                                    <Badge variant="secondary">Parada</Badge>
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
                            <div className="flex flex-wrap items-center justify-between gap-4">
                              <div className="flex items-center gap-6 text-caption">
                                <span>Versión {strategy.version}</span>
                                {strategy.tags && strategy.tags.length > 0 && (
                                  <span className="text-muted-foreground">
                                    {strategy.tags.join(', ')}
                                  </span>
                                )}
                              </div>
                              <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  asChild
                                  disabled={isLoading}
                                  className="w-full sm:w-auto"
                                >
                                  <Link href={`/strategies/${strategy.id}`}>
                                    <Pencil className="h-4 w-4 mr-1" />
                                    Editar
                                  </Link>
                                </Button>
                                {strategy.is_active ? (
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => handleDeactivate(strategy.id)}
                                    disabled={isLoading}
                                    className="w-full sm:w-auto"
                                  >
                                    <Square className="h-4 w-4 mr-1" />
                                    Parar
                                  </Button>
                                ) : (
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => handleActivate(strategy.id)}
                                    disabled={isLoading}
                                    className="w-full sm:w-auto text-green-600 border-green-600 hover:bg-green-50 dark:hover:bg-green-950"
                                  >
                                    <Play className="h-4 w-4 mr-1" />
                                    Arrancar
                                  </Button>
                                )}
                                <AlertDialog
                                  open={deleteConfirmId === strategy.id}
                                  onOpenChange={(open) => setDeleteConfirmId(open ? strategy.id : null)}
                                >
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    className="w-full sm:w-auto text-destructive border-destructive/50 hover:bg-destructive/10"
                                    onClick={() => setDeleteConfirmId(strategy.id)}
                                    disabled={isLoading || strategy.is_active}
                                    title={strategy.is_active ? 'Detén la estrategia antes de eliminarla' : 'Eliminar estrategia'}
                                  >
                                    <Trash2 className="h-4 w-4 mr-1" />
                                    Borrar
                                  </Button>
                                  <AlertDialogContent>
                                    <AlertDialogHeader>
                                      <AlertDialogTitle>¿Eliminar estrategia?</AlertDialogTitle>
                                      <AlertDialogDescription>
                                        Se eliminará &quot;{strategy.name}&quot; y sus datos asociados. Esta acción no se puede deshacer.
                                      </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                      <AlertDialogCancel>Cancelar</AlertDialogCancel>
                                      <AlertDialogAction
                                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                        onClick={() => handleDelete(strategy.id)}
                                      >
                                        Eliminar
                                      </AlertDialogAction>
                                    </AlertDialogFooter>
                                  </AlertDialogContent>
                                </AlertDialog>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
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
