'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { getApiClient, initApiClient } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';

interface Wallet {
  id: string;
  label: string;
  address: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

// Placeholder data para generar FOMO
const PLACEHOLDER_WALLETS: Wallet[] = [
  {
    id: 'demo-1',
    label: 'Main Trading Wallet',
    address: '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0',
    active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 'demo-2',
    label: 'Backup Wallet',
    address: '0x8ba1f109551bD432803012645Hac136c22C929C',
    active: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 'demo-3',
    label: 'Testing Wallet',
    address: '0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE',
    active: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

export default function WalletsPage() {
  const user = useUser();
  const { isConnected } = useBackendConnection();
  const { isDemo } = useDataMode();
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [activeWallet, setActiveWallet] = useState<Wallet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    label: '',
    address: '',
    private_key: '',
  });

  useEffect(() => {
    if (!user) return;

    if (isDemo) {
      setWallets(PLACEHOLDER_WALLETS);
      setActiveWallet(PLACEHOLDER_WALLETS.find(w => w.active) || null);
      setError(null);
      setLoading(false);
      return;
    }

    const api = initApiClient(() => user.accessToken || null);

    const fetchData = async () => {
      try {
        const [walletsData, activeData] = await Promise.all([
          api.get<Wallet[]>('/wallets'),
          api.get<Wallet>('/wallets/active'),
        ]);
        setWallets(walletsData ?? []);
        setActiveWallet(activeData ?? null);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error al cargar wallets');
        setWallets([]);
        setActiveWallet(null);
      } finally {
        setLoading(false);
      }
    };

    setLoading(true);
    fetchData();
  }, [user, isDemo]);

  const handleAddWallet = async () => {
    if (!user) return;

    const api = initApiClient(() => user.accessToken || null);

    try {
      await api.post('/wallets', formData);
      setFormData({ label: '', address: '', private_key: '' });
      setShowAddForm(false);
      // Reload
      const walletsData = await api.get<Wallet[]>('/wallets');
      setWallets(walletsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error adding wallet');
    }
  };

  const handleActivate = async (walletId: string) => {
    if (!user) return;
    if (!confirm('¿Estás seguro de activar esta wallet? Esto cancelará todas las órdenes abiertas.')) {
      return;
    }

    const api = initApiClient(() => user.accessToken || null);

    try {
      await api.put(`/wallets/${walletId}/activate`, {
        confirm: true,
        cancel_open_orders: true,
      });
      // Reload
      const [walletsData, activeData] = await Promise.all([
        api.get<Wallet[]>('/wallets'),
        api.get<Wallet>('/wallets/active'),
      ]);
      setWallets(walletsData);
      setActiveWallet(activeData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error activating wallet');
    }
  };

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner text="Cargando wallets..." />
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gradient">Gestión de Wallets</h1>
          <div className="flex items-center gap-3">
            {isDemo && (
              <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-50 border border-amber-200 dark:bg-amber-950/30 dark:border-amber-800">
                <div className="w-2 h-2 rounded-full bg-amber-500"></div>
                <span className="text-sm text-amber-800 dark:text-amber-200 font-medium">Modo Demo</span>
              </div>
            )}
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              disabled={isDemo || !isConnected}
              className={`px-4 py-2 rounded-xl font-semibold text-white transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none ${
                !isDemo && isConnected
                  ? 'gradient-premium hover:opacity-90'
                  : 'bg-slate-400 cursor-not-allowed'
              }`}
            >
              {showAddForm ? 'Cancelar' : '+ Agregar Wallet'}
            </button>
          </div>
        </div>

        {isDemo && (
          <div className="glass rounded-2xl p-4 shadow-premium border-2 border-indigo-200 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30 dark:border-indigo-800">
            <p className="text-sm text-slate-700 dark:text-slate-300">
              <strong>💡 Modo Demo</strong> - Mostrando {wallets.length} wallets de demostración.
              Cambia a modo Real en el header para gestionar wallets con el backend.
            </p>
          </div>
        )}
        {error && !isDemo && (
          <div className="rounded-lg p-4 bg-destructive/10 border border-destructive/30 text-destructive text-sm">
            {error}
          </div>
        )}

        {showAddForm && (
          <div className="glass rounded-2xl shadow-premium p-6">
            <h2 className="text-xl font-semibold mb-4">Agregar Nueva Wallet</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Etiqueta
                </label>
                <input
                  type="text"
                  value={formData.label}
                  onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="main, backup, testing..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Dirección
                </label>
                <input
                  type="text"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="0x..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Clave Privada
                </label>
                <input
                  type="password"
                  value={formData.private_key}
                  onChange={(e) => setFormData({ ...formData, private_key: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="0x..."
                />
              </div>
              <button
                onClick={handleAddWallet}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
              >
                Agregar
              </button>
            </div>
          </div>
        )}

        <div className="glass rounded-2xl shadow-premium overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Etiqueta
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Dirección
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Estado
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {wallets.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-4 text-center text-gray-500">
                    No hay wallets configuradas
                  </td>
                </tr>
              ) : (
                wallets.map((wallet) => (
                  <tr key={wallet.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      {wallet.label}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {wallet.address}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {wallet.active ? (
                        <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">
                          Activa
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800">
                          Inactiva
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {!wallet.active && !isDemo && (
                        <button
                          onClick={() => handleActivate(wallet.id)}
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                        >
                          Activar
                        </button>
                      )}
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

