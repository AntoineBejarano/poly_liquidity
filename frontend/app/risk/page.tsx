'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { getApiClient, initApiClient } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';

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
  const [config, setConfig] = useState<RiskConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<Partial<RiskConfig>>({});

  useEffect(() => {
    if (!user) return;

    const api = initApiClient(() => user.accessToken || null);

    const fetchConfig = async () => {
      try {
        const data = await api.get<RiskConfig>('/risk/config');
        setConfig(data);
        setFormData(data);
        setError(null);
      } catch (err) {
        // No mostrar error, usar datos placeholder
        setConfig(PLACEHOLDER_CONFIG);
        setFormData(PLACEHOLDER_CONFIG);
        setError(null);
      } finally {
        setLoading(false);
      }
    };

    setLoading(true);
    fetchConfig();
  }, [user]);

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
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-premium mb-4 shadow-lg animate-pulse">
              <span className="text-3xl font-bold text-white">P</span>
            </div>
            <p className="text-slate-600 font-medium">Cargando configuración...</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (!config) {
    return null;
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gradient">Configuración de Riesgo</h1>
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
              <strong>💡 Modo Demo</strong> - Mostrando configuración de demostración. 
              Conecta el backend para editar y guardar cambios en tiempo real.
            </p>
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
                disabled={saving || !isConnected}
                className={`px-6 py-3 rounded-xl font-semibold text-white transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none ${
                  isConnected 
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
            {!isConnected && (
              <p className="text-xs text-slate-500 mt-2 text-right">
                Conecta el backend para habilitar la edición
              </p>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}

