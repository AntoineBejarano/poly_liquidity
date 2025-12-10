'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { initApiClient } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';

interface Trade {
  trade_id: string;
  market_id: string;
  polymarket_id: string;
  fill_price: number;
  fill_size: number;
  direction: 'BUY' | 'SELL';
  timestamp: string;
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

// Placeholder data para generar FOMO
const PLACEHOLDER_TRADES: Trade[] = [
  {
    trade_id: 'demo-trade-1',
    market_id: 'demo-1',
    polymarket_id: '0x123...abc',
    fill_price: 0.9850,
    fill_size: 45000.0,
    direction: 'BUY',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 horas atrás
  },
  {
    trade_id: 'demo-trade-2',
    market_id: 'demo-2',
    polymarket_id: '0x456...def',
    fill_price: 0.9880,
    fill_size: 38000.0,
    direction: 'BUY',
    timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(), // 5 horas atrás
  },
  {
    trade_id: 'demo-trade-3',
    market_id: 'demo-3',
    polymarket_id: '0x789...ghi',
    fill_price: 0.9820,
    fill_size: 52000.0,
    direction: 'BUY',
    timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(), // 8 horas atrás
  },
  {
    trade_id: 'demo-trade-4',
    market_id: 'demo-4',
    polymarket_id: '0xabc...jkl',
    fill_price: 0.9860,
    fill_size: 41000.0,
    direction: 'BUY',
    timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(), // 12 horas atrás
  },
  {
    trade_id: 'demo-trade-5',
    market_id: 'demo-5',
    polymarket_id: '0xdef...mno',
    fill_price: 0.9885,
    fill_size: 48000.0,
    direction: 'BUY',
    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // 1 día atrás
  },
];

const PLACEHOLDER_RESOLVED_MARKETS: ResolvedMarket[] = [
  {
    market_id: 'demo-resolved-1',
    polymarket_id: '0xres1...abc',
    question: 'Will the Super Bowl winner be an NFC team?',
    outcome: 'Yes',
    resolved: true,
    resolution_outcome: 'Yes',
    cost_total: 45000.0,
    payout_total: 45682.23,
    realized_pnl: 682.23,
    resolved_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 días atrás
  },
  {
    market_id: 'demo-resolved-2',
    polymarket_id: '0xres2...def',
    question: 'Will Apple stock close above $200 in Q1 2024?',
    outcome: 'Yes',
    resolved: true,
    resolution_outcome: 'Yes',
    cost_total: 38000.0,
    payout_total: 38456.00,
    realized_pnl: 456.00,
    resolved_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 días atrás
  },
  {
    market_id: 'demo-resolved-3',
    polymarket_id: '0xres3...ghi',
    question: 'Will OpenAI release GPT-4.5 before June 2024?',
    outcome: 'Yes',
    resolved: true,
    resolution_outcome: 'Yes',
    cost_total: 52000.0,
    payout_total: 52600.00,
    realized_pnl: 600.00,
    resolved_at: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(), // 14 días atrás
  },
  {
    market_id: 'demo-resolved-4',
    polymarket_id: '0xres4...jkl',
    question: 'Will Ethereum merge complete successfully?',
    outcome: 'Yes',
    resolved: true,
    resolution_outcome: 'Yes',
    cost_total: 41000.0,
    payout_total: 41500.00,
    realized_pnl: 500.00,
    resolved_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 días atrás
  },
];

export default function HistoryPage() {
  const user = useUser();
  const { isConnected } = useBackendConnection();
  const [trades, setTrades] = useState<Trade[]>([]);
  const [resolvedMarkets, setResolvedMarkets] = useState<ResolvedMarket[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'trades' | 'markets'>('trades');

  useEffect(() => {
    if (!user) return;

    const api = initApiClient(() => user.accessToken || null);

    const fetchData = async () => {
      try {
        const [tradesData, marketsData] = await Promise.all([
          api.get<{ items: Trade[] }>('/history/trades').catch(() => ({ items: [] })),
          api.get<ResolvedMarket[]>('/history/markets').catch(() => []),
        ]);
        setTrades(tradesData.items || []);
        setResolvedMarkets(marketsData || []);
      } catch (err) {
        // No mostrar error, usar datos placeholder
        setTrades(PLACEHOLDER_TRADES);
        setResolvedMarkets(PLACEHOLDER_RESOLVED_MARKETS);
      } finally {
        setLoading(false);
      }
    };

    setLoading(true);
    fetchData();
  }, [user]);

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-premium mb-4 shadow-lg animate-pulse">
              <span className="text-3xl font-bold text-white">P</span>
            </div>
            <p className="text-slate-600 font-medium">Cargando historial...</p>
          </div>
        </div>
      </Layout>
    );
  }

  const totalRealizedPnL = resolvedMarkets.reduce(
    (sum, market) => sum + market.realized_pnl,
    0
  );

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gradient">Historial</h1>
          <div className="flex items-center gap-3">
            {!isConnected && (
              <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-50 border border-amber-200">
                <div className="w-2 h-2 rounded-full bg-amber-500"></div>
                <span className="text-sm text-amber-800 font-medium">Modo Demo</span>
              </div>
            )}
            {resolvedMarkets.length > 0 && (
              <div className="text-right">
                <div className="text-sm text-slate-600">PnL Realizado Total</div>
                <div className="text-2xl font-bold text-green-600">
                  ${totalRealizedPnL.toLocaleString('es-ES', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {!isConnected && (
          <div className="glass rounded-2xl p-4 shadow-premium border-2 border-indigo-200 bg-gradient-to-r from-indigo-50 to-purple-50">
            <p className="text-sm text-slate-700">
              <strong>💡 Modo Demo</strong> - Mostrando {trades.length} trades y {resolvedMarkets.length} mercados resueltos de demostración. 
              Conecta el backend para ver historial completo en tiempo real.
            </p>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 border-b border-slate-200">
          <button
            onClick={() => setActiveTab('trades')}
            className={`px-6 py-3 font-semibold transition-all duration-200 border-b-2 ${
              activeTab === 'trades'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            📊 Trades ({trades.length})
          </button>
          <button
            onClick={() => setActiveTab('markets')}
            className={`px-6 py-3 font-semibold transition-all duration-200 border-b-2 ${
              activeTab === 'markets'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            ✅ Mercados Resueltos ({resolvedMarkets.length})
          </button>
        </div>

        {/* Trades Tab */}
        {activeTab === 'trades' && (
          <div className="glass rounded-2xl shadow-premium overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Mercado
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Dirección
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Precio
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Tamaño
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Valor
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Fecha
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {trades.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-4 text-center text-slate-500">
                      No hay trades en el historial
                    </td>
                  </tr>
                ) : (
                  trades.map((trade) => (
                    <tr key={trade.trade_id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-slate-900">
                          {trade.polymarket_id.slice(0, 12)}...
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-3 py-1 text-xs font-semibold rounded-full ${
                            trade.direction === 'BUY'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {trade.direction}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                        ${trade.fill_price.toFixed(4)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                        {trade.fill_size.toLocaleString('es-ES', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-slate-900">
                        ${(trade.fill_price * trade.fill_size).toLocaleString('es-ES', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                        {new Date(trade.timestamp).toLocaleString('es-ES', {
                          day: '2-digit',
                          month: '2-digit',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Resolved Markets Tab */}
        {activeTab === 'markets' && (
          <div className="glass rounded-2xl shadow-premium overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Mercado
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Resultado
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Costo Total
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Payout Total
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    PnL Realizado
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Fecha Resolución
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {resolvedMarkets.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-4 text-center text-slate-500">
                      No hay mercados resueltos en el historial
                    </td>
                  </tr>
                ) : (
                  resolvedMarkets.map((market) => (
                    <tr key={market.market_id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-slate-900">{market.question}</div>
                        <div className="text-sm text-slate-500">{market.outcome}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-3 py-1 text-xs font-semibold rounded-full ${
                            market.resolution_outcome === market.outcome
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {market.resolution_outcome || 'Pendiente'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                        ${market.cost_total.toLocaleString('es-ES', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                        ${market.payout_total.toLocaleString('es-ES', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`text-sm font-bold ${
                            market.realized_pnl >= 0
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          ${market.realized_pnl >= 0 ? '+' : ''}
                          {market.realized_pnl.toLocaleString('es-ES', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
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
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  );
}

