'use client';

import { useEffect, useState } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import Link from 'next/link';
import { Strategy } from '@/types/strategy';

export default function StrategiesPage() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user || !isConnected) {
      setLoading(false);
      return;
    }

    const api = initApiClient(createTokenGetter(user, stackApp));

    const fetchStrategies = async () => {
      try {
        setLoading(true);
        const data = await api.get<Strategy[]>('/strategies');
        setStrategies(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching strategies:', err);
        setError(err instanceof Error ? err.message : 'Error al cargar estrategias');
      } finally {
        setLoading(false);
      }
    };

    fetchStrategies();
  }, [user, stackApp, isConnected]);

  if (!user) {
    return null;
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Estrategias</h1>
            <p className="text-sm text-slate-600 mt-1">
              Gestiona tus estrategias de trading basadas en grafos
            </p>
          </div>
          <Link
            href="/strategies/create"
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Crear Estrategia
          </Link>
        </div>

        {loading && <LoadingSpinner />}

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {!loading && !error && (
          <>
            {strategies.length === 0 ? (
              <div className="p-8 text-center border border-slate-200 rounded-lg bg-white">
                <p className="text-sm text-slate-600">No hay estrategias creadas aún.</p>
                <Link
                  href="/strategies/create"
                  className="mt-4 inline-block px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700"
                >
                  Crear tu primera estrategia
                </Link>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {strategies.map((strategy) => (
                  <Link
                    key={strategy.id}
                    href={`/strategies/${strategy.id}`}
                    className="block p-4 border border-slate-200 rounded-lg bg-white hover:border-slate-300 hover:shadow-sm transition-all"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-semibold text-slate-900">
                            {strategy.name}
                          </h3>
                          {strategy.is_active ? (
                            <span className="px-2 py-0.5 text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded">
                              Activa
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 text-xs font-medium text-slate-600 bg-slate-50 border border-slate-200 rounded">
                              Inactiva
                            </span>
                          )}
                        </div>
                        {strategy.description && (
                          <p className="text-xs text-slate-600 mt-1">{strategy.description}</p>
                        )}
                        <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                          <span>Versión {strategy.version}</span>
                          <span>
                            {strategy.support_graphs?.length || 0} Support Graph
                            {(strategy.support_graphs?.length || 0) !== 1 ? 's' : ''}
                          </span>
                        </div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  );
}

