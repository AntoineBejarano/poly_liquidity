'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { getApiClient, initApiClient } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';

interface Market {
  market_id: string;
  polymarket_id: string;
  question: string;
  outcome: string;
  status: string;
  last_price: number;
  event_state: string;
  exposure: number;
  created_at: string;
  updated_at: string;
}

// Placeholder data para generar FOMO
const PLACEHOLDER_MARKETS: Market[] = [
  {
    market_id: 'demo-1',
    polymarket_id: '0x123...abc',
    question: 'Will Bitcoin reach $100K by end of 2024?',
    outcome: 'Yes',
    status: 'OPEN',
    last_price: 0.9875,
    event_state: 'LIVE',
    exposure: 45000.00,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    market_id: 'demo-2',
    polymarket_id: '0x456...def',
    question: 'Will the Lakers win the NBA Championship?',
    outcome: 'Yes',
    status: 'OPEN',
    last_price: 0.9920,
    event_state: 'LIVE',
    exposure: 38000.00,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    market_id: 'demo-3',
    polymarket_id: '0x789...ghi',
    question: 'Will AI achieve AGI before 2026?',
    outcome: 'Yes',
    status: 'OPEN',
    last_price: 0.9850,
    event_state: 'LIVE',
    exposure: 52000.00,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    market_id: 'demo-4',
    polymarket_id: '0xabc...jkl',
    question: 'Will Ethereum 2.0 reduce gas fees by 90%?',
    outcome: 'Yes',
    status: 'OPEN',
    last_price: 0.9890,
    event_state: 'LIVE',
    exposure: 41000.00,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    market_id: 'demo-5',
    polymarket_id: '0xdef...mno',
    question: 'Will Trump win 2024 US Election?',
    outcome: 'Yes',
    status: 'OPEN',
    last_price: 0.9915,
    event_state: 'LIVE',
    exposure: 48000.00,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    market_id: 'demo-6',
    polymarket_id: '0xghi...pqr',
    question: 'Will Tesla stock reach $500 by Q2 2025?',
    outcome: 'Yes',
    status: 'OPEN',
    last_price: 0.9880,
    event_state: 'LIVE',
    exposure: 39000.00,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    market_id: 'demo-7',
    polymarket_id: '0xjkl...stu',
    question: 'Will OpenAI release GPT-5 in 2024?',
    outcome: 'Yes',
    status: 'OPEN',
    last_price: 0.9865,
    event_state: 'LIVE',
    exposure: 44000.00,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    market_id: 'demo-8',
    polymarket_id: '0xmno...vwx',
    question: 'Will the Fed cut rates 3+ times in 2024?',
    outcome: 'Yes',
    status: 'OPEN',
    last_price: 0.9905,
    event_state: 'LIVE',
    exposure: 36000.00,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

export default function MarketsPage() {
  const user = useUser();
  const { isConnected } = useBackendConnection();
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;

    const api = initApiClient(() => user.accessToken || null);

    const fetchMarkets = async () => {
      try {
        const data = await api.get<Market[]>('/markets');
        setMarkets(data);
        setError(null);
      } catch (err) {
        // No mostrar error, usar datos placeholder
        setMarkets(PLACEHOLDER_MARKETS);
        setError(null);
      } finally {
        setLoading(false);
      }
    };

    setLoading(true);
    fetchMarkets();
    const interval = setInterval(fetchMarkets, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [user]);

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-premium mb-4 shadow-lg animate-pulse">
              <span className="text-3xl font-bold text-white">P</span>
            </div>
            <p className="text-slate-600 font-medium">Cargando mercados...</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gradient">Mercados</h1>
          {!isConnected && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-50 border border-amber-200">
              <div className="w-2 h-2 rounded-full bg-amber-500"></div>
              <span className="text-sm text-amber-800 font-medium">Modo Demo</span>
            </div>
          )}
        </div>

        {!isConnected && (
          <div className="glass rounded-2xl p-4 shadow-premium border-2 border-indigo-200 bg-gradient-to-r from-indigo-50 to-purple-50">
            <p className="text-sm text-slate-700">
              <strong>💡 Modo Demo</strong> - Mostrando {markets.length} mercados de demostración. 
              Conecta el backend para ver mercados en tiempo real.
            </p>
          </div>
        )}

        <div className="glass rounded-2xl shadow-premium overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Mercado
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Precio
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado Evento
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Exposición
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {markets.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                    No hay mercados disponibles
                  </td>
                </tr>
              ) : (
                markets.map((market) => (
                  <tr key={market.market_id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {market.question}
                        </div>
                        <div className="text-sm text-gray-500">{market.outcome}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        ${market.last_price.toFixed(4)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
                          market.event_state === 'FINISHED_CONFIRMED'
                            ? 'bg-green-100 text-green-800'
                            : market.event_state === 'FINISHED_UNCONFIRMED'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {market.event_state}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ${market.exposure.toLocaleString('es-ES', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
                          market.status === 'OPEN'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {market.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
}

