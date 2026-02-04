'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { getApiClient, initApiClient } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';

interface RiskConfig {
  max_exposure_per_market: number;
  max_global_exposure: number;
  min_entry_price: number;
  target_margin: number;
  max_markets_active: number;
}

// Placeholder data para generar FOMO
const PLACEHOLDER_CONFIG: RiskConfig = {
  max_exposure_per_market: 50000,
  max_global_exposure: 500000,
  min_entry_price: 0.98,
  target_margin: 0.001,
  max_markets_active: 30,
};

export default function RiskPage() {
  const user = useUser();
  const { isConnected } = useBackendConnection();
  const { isDemo } = useDataMode();
  const [config, setConfig] = useState<RiskConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<Partial<RiskConfig>>({});

  useEffect(() => {
    if (!user) return;

    if (isDemo) {
      setConfig(PLACEHOLDER_CONFIG);
      setFormData(PLACEHOLDER_CONFIG);
      setError(null);
      setLoading(false);
      return;
    }

    const api = initApiClient(() => user.accessToken || null);

    const fetchConfig = async () => {
      try {
        const data = await api.get<RiskConfig>('/risk/config');
        setConfig(data);
        setFormData(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error al cargar configuración de riesgo');
        setConfig(null);
      } finally {
        setLoading(false);
      }
    };

    setLoading(true);
    fetchConfig();
  }, [user, isDemo]);

  const handleSave = async () => {
    if (!user) return;

    const api = initApiClient(() => user.accessToken || null);

    try {
      setSaving(true);
      await api.post('/risk/config', formData);
      setError(null);
      // Reload config
      const updated = await api.get<RiskConfig>('/risk/config');
      setConfig(updated);
      setFormData(updated);
      alert('Configuración guardada exitosamente');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error saving config');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner text="Cargando configuración..." />
      </Layout>
    );
  }

  if (!config && !error) {
    return null;
  }

  if (!config && error && !loading) {
    return (
      <Layout>
        <div className="space-y-6">
          <h1 className="text-3xl font-bold text-gradient">Configuración de Riesgo</h1>
          <div className="rounded-lg p-4 bg-destructive/10 border border-destructive/30 text-destructive text-sm">
            {error}
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gradient">Configuración de Riesgo</h1>
          {isDemo && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-50 border border-amber-200 dark:bg-amber-950/30 dark:border-amber-800">
              <div className="w-2 h-2 rounded-full bg-amber-500"></div>
              <span className="text-sm text-amber-800 dark:text-amber-200 font-medium">Modo Demo</span>
            </div>
          )}
        </div>

        {isDemo && (
          <div className="glass rounded-2xl p-4 shadow-premium border-2 border-indigo-200 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30 dark:border-indigo-800">
            <p className="text-sm text-slate-700 dark:text-slate-300">
              <strong>💡 Modo Demo</strong> - Mostrando configuración de demostración.
              Cambia a modo Real en el header para editar y guardar cambios.
            </p>
          </div>
        )}
        {error && !isDemo && (
          <div className="rounded-lg p-4 bg-destructive/10 border border-destructive/30 text-destructive text-sm">
            {error}
          </div>
        )}

        <div className="glass rounded-2xl shadow-premium p-6">
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Exposición Máxima por Mercado (USDC)
              </label>
              <input
                type="number"
                value={formData.max_exposure_per_market ?? config.max_exposure_per_market}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    max_exposure_per_market: parseFloat(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Exposición Global Máxima (USDC)
              </label>
              <input
                type="number"
                value={formData.max_global_exposure ?? config.max_global_exposure}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    max_global_exposure: parseFloat(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Precio Mínimo de Entrada
              </label>
              <input
                type="number"
                step="0.0001"
                value={formData.min_entry_price ?? config.min_entry_price}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    min_entry_price: parseFloat(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Margen Objetivo
              </label>
              <input
                type="number"
                step="0.0001"
                value={formData.target_margin ?? config.target_margin}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    target_margin: parseFloat(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Máximo de Mercados Activos
              </label>
              <input
                type="number"
                value={formData.max_markets_active ?? config.max_markets_active}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    max_markets_active: parseInt(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleSave}
                disabled={saving || isDemo || !isConnected}
                className={`px-6 py-3 rounded-xl font-semibold text-white transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none ${
                  !isDemo && isConnected
                    ? 'gradient-premium hover:opacity-90'
                    : 'bg-slate-400 cursor-not-allowed'
                }`}
              >
                {saving ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    Guardando...
                  </span>
                ) : (
                  '💾 Guardar Cambios'
                )}
              </button>
            </div>
            {(isDemo || !isConnected) && (
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 text-right">
                {isDemo ? 'Modo Demo: cambia a Real para editar.' : 'Conecta el backend para habilitar la edición.'}
              </p>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}

