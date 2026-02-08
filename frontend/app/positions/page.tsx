'use client';

import { useEffect, useState, useMemo } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';

interface Position {
  market_id: string;
  polymarket_id: string;
  question: string;
  size: number;
  avg_price: number;
  current_price: number;
  unrealized_pnl: number;
  resolved: boolean;
  payout: number | null;
  resolved_at?: string | null;
  created_at?: string | null;
}

interface ResolvedMarket {
  market_id: string;
  polymarket_id: string;
  question: string;
  outcome: string;
  resolved: boolean;
  resolution_outcome: string | null;
  cost_total: number;
  payout_total: number;
  realized_pnl: number;
  resolved_at: string | null;
}

type TimeFilter = 'all' | 'today' | 'week' | 'month' | '3months';

export default function PositionsPage() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const [positions, setPositions] = useState<Position[]>([]);
  const [resolvedMarkets, setResolvedMarkets] = useState<ResolvedMarket[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'active' | 'closed'>('active');
  const [timeFilter, setTimeFilter] = useState<TimeFilter>('all');

  useEffect(() => {
    if (!user || !stackApp) return;

    const api = initApiClient(createTokenGetter(user, stackApp));

    const fetchData = async (isInitial = false) => {
      try {
        const [positionsData, marketsData] = await Promise.all([
          api.get<Position[]>('/positions').catch(() => []),
          api.get<ResolvedMarket[]>('/history/markets').catch(() => []),
        ]);
        
        setPositions(positionsData ?? []);
        setResolvedMarkets(marketsData ?? []);
      } catch (err) {
        setPositions([]);
        setResolvedMarkets([]);
      } finally {
        // Solo desactivar loading en la carga inicial
        if (isInitial) {
          setLoading(false);
        }
      }
    };

    // Carga inicial con loading
    setLoading(true);
    fetchData(true);
    
    // Actualizaciones periódicas sin mostrar loading
    const interval = setInterval(() => {
      fetchData(false);
    }, 2000); // Refresh every 2 seconds for real-time feel
    
    return () => clearInterval(interval);
  }, [user, stackApp]);

  // Filter positions by time
  const filteredResolvedMarkets = useMemo(() => {
    if (timeFilter === 'all') return resolvedMarkets;
    
    const now = new Date();
    const filterDate = new Date();
    
    switch (timeFilter) {
      case 'today':
        filterDate.setHours(0, 0, 0, 0);
        break;
      case 'week':
        filterDate.setDate(now.getDate() - 7);
        break;
      case 'month':
        filterDate.setMonth(now.getMonth() - 1);
        break;
      case '3months':
        filterDate.setMonth(now.getMonth() - 3);
        break;
    }
    
    return resolvedMarkets.filter(market => {
      if (!market.resolved_at) return false;
      const resolvedDate = new Date(market.resolved_at);
      return resolvedDate >= filterDate;
    });
  }, [resolvedMarkets, timeFilter]);

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner text="Cargando posiciones..." />
      </Layout>
    );
  }

  const activePositions = positions.filter(p => !p.resolved);
  const totalUnrealizedPnL = activePositions.reduce((sum, pos) => sum + pos.unrealized_pnl, 0);
  const totalRealizedPnL = filteredResolvedMarkets.reduce((sum, market) => sum + market.realized_pnl, 0);

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-lg font-medium text-slate-900">Posiciones</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Seguimiento de inversiones
            </p>
          </div>
          <div className="flex items-center gap-4">
            {!isConnected && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-slate-200 bg-slate-50">
                <div className="w-1.5 h-1.5 rounded-full bg-slate-300"></div>
                <span className="text-xs text-slate-500">Demo</span>
              </div>
            )}
            <div className="text-right">
              <div className="text-xs text-slate-500">Ganancias Pendientes</div>
              <div className="text-base font-medium text-slate-900">
                {totalUnrealizedPnL >= 0 ? '+' : ''}${totalUnrealizedPnL.toLocaleString('es-ES', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            </div>
            {activeTab === 'closed' && totalRealizedPnL !== 0 && (
              <div className="text-right">
                <div className="text-xs text-slate-500">PnL Realizado</div>
                <div className="text-base font-medium text-slate-900">
                  {totalRealizedPnL >= 0 ? '+' : ''}${totalRealizedPnL.toLocaleString('es-ES', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {!isConnected && (
          <div className="border border-slate-200 rounded-lg p-3 bg-white mb-4">
            <p className="text-xs text-slate-500">
              Modo demostración. Conecta el backend para ver posiciones reales.
            </p>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 border-b border-slate-200 mb-4">
          <button
            onClick={() => setActiveTab('active')}
            className={`px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === 'active'
                ? 'border-b-2 border-slate-900 text-slate-900'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Activas ({activePositions.length})
          </button>
          <button
            onClick={() => setActiveTab('closed')}
            className={`px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === 'closed'
                ? 'border-b-2 border-slate-900 text-slate-900'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Cerradas ({filteredResolvedMarkets.length})
          </button>
        </div>

        {/* Time Filter (only for closed positions) */}
        {activeTab === 'closed' && (
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xs text-slate-500">Filtrar por:</span>
            <select
              value={timeFilter}
              onChange={(e) => setTimeFilter(e.target.value as TimeFilter)}
              className="px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-slate-400"
            >
              <option value="all">Todas</option>
              <option value="today">Hoy</option>
              <option value="week">Última semana</option>
              <option value="month">Último mes</option>
              <option value="3months">Últimos 3 meses</option>
            </select>
          </div>
        )}

        {/* Active Positions Tab */}
        {activeTab === 'active' && (
          <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
            <div className="p-3 border-b border-slate-200">
              <h2 className="text-xs font-medium text-slate-900">
                Posiciones Activas
              </h2>
            </div>
            {activePositions.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-xs text-slate-500 mb-1">No hay posiciones abiertas</p>
                <p className="text-xs text-slate-400">
                  Cuando el bot entre en un mercado, aparecerá aquí
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Mercado
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Tamaño
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Precio Promedio
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Precio Actual
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        PnL
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Estado
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {activePositions.map((position, index) => (
                      <tr
                        key={position.market_id}
                        className={`hover:bg-slate-50 transition-colors ${
                          index === 0 ? 'bg-slate-50' : ''
                        }`}
                      >
                        <td className="px-4 py-3">
                          <div className="text-xs text-slate-900">
                            {position.question}
                          </div>
                          <div className="text-xs text-slate-400 mt-0.5">
                            {position.market_id.substring(0, 8)}...
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-600">
                          {position.size.toFixed(4)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-700">
                          ${position.avg_price.toFixed(4)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs font-medium text-slate-900">
                          ${position.current_price.toFixed(4)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className={`text-xs font-medium ${
                            position.unrealized_pnl >= 0
                              ? 'text-slate-900'
                              : 'text-slate-600'
                          }`}>
                            {position.unrealized_pnl >= 0 ? '+' : ''}${position.unrealized_pnl.toLocaleString('es-ES', {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            })}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-xs text-slate-500 px-1.5 py-0.5 rounded border border-slate-200 bg-slate-50">
                            Activo
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Closed Positions Tab */}
        {activeTab === 'closed' && (
          <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
            <div className="p-3 border-b border-slate-200">
              <h2 className="text-xs font-medium text-slate-900">
                Posiciones Cerradas
              </h2>
            </div>
            {filteredResolvedMarkets.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-xs text-slate-500 mb-1">No hay posiciones cerradas</p>
                <p className="text-xs text-slate-400">
                  {timeFilter !== 'all' ? 'Intenta cambiar el filtro de tiempo' : 'Las posiciones resueltas aparecerán aquí'}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Mercado
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Resultado
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Costo Total
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Payout Total
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        PnL Realizado
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">
                        Fecha Resolución
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredResolvedMarkets.map((market) => (
                      <tr
                        key={market.market_id}
                        className="hover:bg-slate-50 transition-colors"
                      >
                        <td className="px-4 py-3">
                          <div className="text-xs text-slate-900">
                            {market.question}
                          </div>
                          <div className="text-xs text-slate-400 mt-0.5">
                            {market.outcome}
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-xs text-slate-500 px-1.5 py-0.5 rounded border border-slate-200 bg-slate-50">
                            {market.resolution_outcome || 'Pendiente'}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-700">
                          ${market.cost_total.toLocaleString('es-ES', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-700">
                          ${market.payout_total.toLocaleString('es-ES', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className={`text-xs font-medium ${
                            market.realized_pnl >= 0
                              ? 'text-slate-900'
                              : 'text-slate-600'
                          }`}>
                            {market.realized_pnl >= 0 ? '+' : ''}${market.realized_pnl.toLocaleString('es-ES', {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            })}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-500">
                          {market.resolved_at
                            ? new Date(market.resolved_at).toLocaleString('es-ES', {
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
