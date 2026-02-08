'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { getApiClient, initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
import { useConfirmDialog } from '@/contexts/NotificationContext';

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
  const { confirmDialog } = useConfirmDialog();
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [activeWallet, setActiveWallet] = useState<Wallet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [isAdding, setIsAdding] = useState(false);
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

    const api = initApiClient(createTokenGetter(user));

    const fetchData = async () => {
      try {
        const walletsData = await api.get<Wallet[]>('/wallets');
        setWallets(walletsData ?? []);
        setError(null);
        try {
          const activeData = await api.get<Wallet>('/wallets/active');
          setActiveWallet(activeData ?? null);
        } catch {
          setActiveWallet(null);
        }
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
    const alias = formData.label.trim();
    if (!alias) {
      setFormError('El alias es obligatorio. Será el nombre con el que identificarás esta cuenta en estrategias.');
      return;
    }
    setFormError(null);
    setIsAdding(true);

    const api = initApiClient(createTokenGetter(user));

    try {
      await api.post('/wallets', { ...formData, label: alias });
      setFormData({ label: '', address: '', private_key: '' });
      setShowAddForm(false);
      setError(null);
      const walletsData = await api.get<Wallet[]>('/wallets');
      setWallets(walletsData ?? []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al agregar wallet';
      setFormError(message);
      setError(message);
    } finally {
      setIsAdding(false);
    }
  };

  const handleDeleteWallet = async (walletId: string) => {
    if (!user) return;
    const ok = await confirmDialog({
      title: 'Eliminar cuenta',
      description: '¿Eliminar esta cuenta? No podrás recuperarla.',
      confirmLabel: 'Eliminar',
      cancelLabel: 'Cancelar',
      variant: 'danger',
    });
    if (!ok) return;

    const api = initApiClient(createTokenGetter(user));
    try {
      await api.delete(`/wallets/${walletId}`);
      const walletsData = await api.get<Wallet[]>('/wallets');
      setWallets(walletsData ?? []);
      const activeData = await api.get<Wallet | null>('/wallets/active').catch(() => null);
      setActiveWallet(activeData ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al eliminar wallet');
    }
  };

  const handleActivate = async (walletId: string) => {
    if (!user) return;
    const ok = await confirmDialog({
      title: 'Activar cuenta',
      description: '¿Activar esta cuenta? Se usará para nuevas operaciones y estrategias.',
    });
    if (!ok) return;

    const api = initApiClient(createTokenGetter(user));

    try {
      await api.put(`/wallets/${walletId}/activate`, {
        confirm: true,
        cancel_open_orders: false,
      });
      setError(null);
      const [walletsData, activeData] = await Promise.all([
        api.get<Wallet[]>('/wallets'),
        api.get<Wallet>('/wallets/active'),
      ]);
      setWallets(walletsData ?? []);
      setActiveWallet(activeData ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al activar la cuenta');
    }
  };

  const handleDeactivate = async (walletId: string) => {
    if (!user) return;
    const ok = await confirmDialog({
      title: 'Desactivar cuenta',
      description: '¿Desactivar esta cuenta? Dejará de usarse para nuevas operaciones.',
    });
    if (!ok) return;

    const api = initApiClient(createTokenGetter(user));
    try {
      await api.put(`/wallets/${walletId}/deactivate`, { cancel_open_orders: false });
      setError(null);
      const walletsData = await api.get<Wallet[]>('/wallets');
      setWallets(walletsData ?? []);
      const activeData = await api.get<Wallet | null>('/wallets/active').catch(() => null);
      setActiveWallet(activeData ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al desactivar la cuenta');
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
              type="button"
              onClick={() => setShowAddForm(!showAddForm)}
              disabled={isDemo || !isConnected}
              title={isDemo ? 'Desactiva el modo Demo para agregar cuentas reales' : !isConnected ? 'Conecta el backend para poder agregar cuentas' : undefined}
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
            <h2 className="text-xl font-semibold mb-4">Agregar nueva cuenta</h2>
            <p className="text-sm text-muted-foreground mb-4">
              El <strong>alias</strong> es obligatorio: con él identificarás esta cuenta en la lista y al asignarla a una estrategia.
            </p>
            {formError && (
              <div className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm">
                {formError}
              </div>
            )}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Alias <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  value={formData.label}
                  onChange={(e) => { setFormData({ ...formData, label: e.target.value }); setFormError(null); }}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background"
                  placeholder="Ej: Principal, Backup, Testing..."
                  aria-required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Dirección</label>
                <input
                  type="text"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background"
                  placeholder="0x..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Clave privada</label>
                <input
                  type="password"
                  value={formData.private_key}
                  onChange={(e) => setFormData({ ...formData, private_key: e.target.value })}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background"
                  placeholder="0x..."
                />
              </div>
              <button
                type="button"
                onClick={handleAddWallet}
                disabled={isAdding}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 font-medium disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isAdding ? 'Agregando…' : 'Agregar cuenta'}
              </button>
            </div>
          </div>
        )}

        <div className="glass rounded-2xl shadow-premium overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Alias
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Dirección
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {wallets.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-muted-foreground">
                    No hay cuentas. Agrega una para usarla en estrategias.
                  </td>
                </tr>
              ) : (
                wallets.map((wallet) => (
                  <tr key={wallet.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                      {wallet.label || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground font-mono truncate max-w-[200px]">
                      {wallet.address}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {wallet.active ? (
                        <span className="px-2 py-1 text-xs rounded-full bg-green-500/15 text-green-700 dark:text-green-400">
                          Activa
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs rounded-full bg-muted text-muted-foreground">
                          Inactiva
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-3">
                        {!isDemo && wallet.active && (
                          <button
                            type="button"
                            onClick={() => handleDeactivate(wallet.id)}
                            className="text-amber-600 dark:text-amber-400 hover:underline font-medium"
                          >
                            Desactivar
                          </button>
                        )}
                        {!wallet.active && !isDemo && (
                          <>
                            <button
                              type="button"
                              onClick={() => handleActivate(wallet.id)}
                              className="text-primary hover:underline font-medium"
                            >
                              Activar
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteWallet(wallet.id)}
                              className="text-destructive hover:underline font-medium"
                            >
                              Eliminar
                            </button>
                          </>
                        )}
                      </div>
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

