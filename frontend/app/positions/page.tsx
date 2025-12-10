'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { getApiClient, initApiClient } from '@/lib/api';
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
}

// Placeholder data para generar FOMO
const PLACEHOLDER_POSITIONS: Position[] = [
  {
    market_id: 'demo-1',
    polymarket_id: '0x123...abc',
    question: 'Will Bitcoin reach $100K by end of 2024?',
    size: 45000.0,
    avg_price: 0.9850,
    current_price: 0.9875,
    unrealized_pnl: 1125.00,
    resolved: false,
    payout: null,
  },
  {
    market_id: 'demo-2',
    polymarket_id: '0x456...def',
    question: 'Will the Lakers win the NBA Championship?',
    size: 38000.0,
    avg_price: 0.9880,
    current_price: 0.9920,
    unrealized_pnl: 1520.00,
    resolved: false,
    payout: null,
  },
  {
    market_id: 'demo-3',
    polymarket_id: '0x789...ghi',
    question: 'Will AI achieve AGI before 2026?',
    size: 52000.0,
    avg_price: 0.9820,
    current_price: 0.9850,
    unrealized_pnl: 1560.00,
    resolved: false,
    payout: null,
  },
  {
    market_id: 'demo-4',
    polymarket_id: '0xabc...jkl',
    question: 'Will Ethereum 2.0 reduce gas fees by 90%?',
    size: 41000.0,
    avg_price: 0.9860,
    current_price: 0.9890,
    unrealized_pnl: 1230.00,
    resolved: false,
    payout: null,
  },
  {
    market_id: 'demo-5',
    polymarket_id: '0xdef...mno',
    question: 'Will Trump win 2024 US Election?',
    size: 48000.0,
    avg_price: 0.9885,
    current_price: 0.9915,
    unrealized_pnl: 1440.00,
    resolved: false,
    payout: null,
  },
  {
    market_id: 'demo-6',
    polymarket_id: '0xghi...pqr',
    question: 'Will Tesla stock reach $500 by Q2 2025?',
    size: 39000.0,
    avg_price: 0.9855,
    current_price: 0.9880,
    unrealized_pnl: 975.00,
    resolved: false,
    payout: null,
  },
];

export default function PositionsPage() {
  const user = useUser();
  const { isConnected } = useBackendConnection();
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;

    const api = initApiClient(() => user.accessToken || null);

    const fetchPositions = async () => {
      try {
        const data = await api.get<Position[]>('/positions');
        setPositions(data);
        setError(null);
      } catch (err) {
        // No mostrar error, usar datos placeholder
        setPositions(PLACEHOLDER_POSITIONS);
        setError(null);
      } finally {
        setLoading(false);
      }
    };

    setLoading(true);
    fetchPositions();
    const interval = setInterval(fetchPositions, 30000); // Refresh every 30 seconds
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
            <p className="text-slate-600 font-medium">Cargando posiciones...</p>
          </div>
        </div>
      </Layout>
    );
  }

  const totalUnrealizedPnL = positions.reduce(
    (sum, pos) => sum + pos.unrealized_pnl,
    0
  );

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gradient">Posiciones</h1>
          <div className="flex items-center gap-4">
            {!isConnected && (
              <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-50 border border-amber-200">
                <div className="w-2 h-2 rounded-full bg-amber-500"></div>
                <span className="text-sm text-amber-800 font-medium">Modo Demo</span>
              </div>
            )}
            <div className="text-right">
              <div className="text-sm text-slate-600">PnL No Realizado Total</div>
              <div
                className={`text-3xl font-bold ${
                  totalUnrealizedPnL >= 0 ? 'text-green-600' : 'text-red-600'
                }`}
              >
                ${totalUnrealizedPnL.toLocaleString('es-ES', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            </div>
          </div>
        </div>

        {!isConnected && (
          <div className="glass rounded-2xl p-4 shadow-premium border-2 border-indigo-200 bg-gradient-to-r from-indigo-50 to-purple-50">
            <p className="text-sm text-slate-700">
              <strong>💡 Modo Demo</strong> - Mostrando {positions.length} posiciones de demostración con PnL positivo. 
              Conecta el backend para ver posiciones en tiempo real.
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
                  Tamaño
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Precio Promedio
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Precio Actual
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  PnL No Realizado
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {positions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    No hay posiciones abiertas
                  </td>
                </tr>
              ) : (
                positions.map((position) => (
                  <tr key={position.market_id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {position.question}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {position.size.toFixed(4)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ${position.avg_price.toFixed(4)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ${position.current_price.toFixed(4)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`text-sm font-medium ${
                          position.unrealized_pnl >= 0
                            ? 'text-green-600'
                            : 'text-red-600'
                        }`}
                      >
                        ${position.unrealized_pnl.toLocaleString('es-ES', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
                          position.resolved
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-green-100 text-green-800'
                        }`}
                      >
                        {position.resolved ? 'Resuelto' : 'Abierto'}
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

