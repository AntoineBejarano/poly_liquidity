'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { getApiClient, initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';

interface Checker {
  id: string;
  implementation_key: string;
  category: string;
  name: string;
  description: string | null;
  enabled: boolean;
}

interface Secret {
  name: string;
  description: string | null;
  has_value: boolean;
}

// Placeholder data para generar FOMO
const PLACEHOLDER_CHECKERS: Checker[] = [
  {
    id: 'demo-1',
    implementation_key: 'sportradar_api',
    category: 'sports',
    name: 'Sportradar API Checker',
    description: 'Detecta finalización de eventos deportivos mediante Sportradar API',
    enabled: true,
  },
  {
    id: 'demo-2',
    implementation_key: 'espn_api',
    category: 'sports',
    name: 'ESPN API Checker',
    description: 'Verifica resultados de eventos deportivos usando ESPN API',
    enabled: true,
  },
  {
    id: 'demo-3',
    implementation_key: 'coinbase_api',
    category: 'crypto',
    name: 'Coinbase Price Checker',
    description: 'Monitorea precios de criptomonedas para eventos relacionados',
    enabled: true,
  },
  {
    id: 'demo-4',
    implementation_key: 'twitter_api',
    category: 'social',
    name: 'Twitter Sentiment Checker',
    description: 'Analiza sentimiento en Twitter para detectar eventos',
    enabled: false,
  },
  {
    id: 'demo-5',
    implementation_key: 'reuters_api',
    category: 'news',
    name: 'Reuters News Checker',
    description: 'Detecta eventos mediante análisis de noticias de Reuters',
    enabled: true,
  },
];

const PLACEHOLDER_SECRETS: Secret[] = [
  {
    name: 'sportradar_api_key',
    description: 'API Key para Sportradar',
    has_value: true,
  },
  {
    name: 'espn_api_key',
    description: 'API Key para ESPN',
    has_value: true,
  },
  {
    name: 'coinbase_api_key',
    description: 'API Key para Coinbase',
    has_value: true,
  },
  {
    name: 'twitter_bearer_token',
    description: 'Bearer Token para Twitter API v2',
    has_value: false,
  },
];

export default function CheckersPage() {
  const user = useUser();
  const { isConnected } = useBackendConnection();
  const { isDemo } = useDataMode();
  const [checkers, setCheckers] = useState<Checker[]>([]);
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showSecretForm, setShowSecretForm] = useState(false);
  const [secretForm, setSecretForm] = useState({
    name: '',
    value: '',
    description: '',
  });

  useEffect(() => {
    if (!user) return;

    if (isDemo) {
      setCheckers(PLACEHOLDER_CHECKERS);
      setSecrets(PLACEHOLDER_SECRETS);
      setError(null);
      setLoading(false);
      return;
    }

    const api = initApiClient(createTokenGetter(user as { accessToken?: string | null } | null));

    const fetchData = async () => {
      try {
        const [checkersData, secretsData] = await Promise.all([
          api.get<Checker[]>('/checkers'),
          api.get<Secret[]>('/checkers/secrets'),
        ]);
        setCheckers(checkersData ?? []);
        setSecrets(secretsData ?? []);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error al cargar checkers');
        setCheckers([]);
        setSecrets([]);
      } finally {
        setLoading(false);
      }
    };

    setLoading(true);
    fetchData();
  }, [user, isDemo]);

  const handleToggleChecker = async (checkerId: string, enabled: boolean) => {
    if (!user) return;

    const api = initApiClient(createTokenGetter(user as { accessToken?: string | null } | null));

    try {
      await api.put(`/checkers/${checkerId}`, { enabled: !enabled });
      // Reload
      const checkersData = await api.get<Checker[]>('/checkers');
      setCheckers(checkersData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error updating checker');
    }
  };

  const handleAddSecret = async () => {
    if (!user) return;

    const api = initApiClient(createTokenGetter(user as { accessToken?: string | null } | null));

    try {
      await api.post('/checkers/secrets', secretForm);
      setSecretForm({ name: '', value: '', description: '' });
      setShowSecretForm(false);
      // Reload
      const secretsData = await api.get<Secret[]>('/checkers/secrets');
      setSecrets(secretsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error adding secret');
    }
  };

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner text="Cargando checkers..." />
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gradient">Checkers y Credenciales</h1>
          <div className="flex items-center gap-3">
            {isDemo && (
              <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-50 border border-amber-200 dark:bg-amber-950/30 dark:border-amber-800">
                <div className="w-2 h-2 rounded-full bg-amber-500"></div>
                <span className="text-sm text-amber-800 dark:text-amber-200 font-medium">Modo Demo</span>
              </div>
            )}
            <button
              onClick={() => setShowSecretForm(!showSecretForm)}
              disabled={isDemo || !isConnected}
              className={`px-4 py-2 rounded-xl font-semibold text-white transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none ${
                !isDemo && isConnected
                  ? 'gradient-premium hover:opacity-90'
                  : 'bg-slate-400 cursor-not-allowed'
              }`}
            >
              {showSecretForm ? 'Cancelar' : '+ Agregar Credencial'}
            </button>
          </div>
        </div>

        {isDemo && (
          <div className="glass rounded-2xl p-4 shadow-premium border-2 border-indigo-200 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30 dark:border-indigo-800">
            <p className="text-sm text-slate-700 dark:text-slate-300">
              <strong>💡 Modo Demo</strong> - Mostrando {checkers.length} checkers y {secrets.length} credenciales de demostración.
              Cambia a modo Real en el header para gestionar checkers y credenciales.
            </p>
          </div>
        )}
        {error && !isDemo && (
          <div className="rounded-lg p-4 bg-destructive/10 border border-destructive/30 text-destructive text-sm">
            {error}
          </div>
        )}

        {showSecretForm && (
          <div className="glass rounded-2xl shadow-premium p-6">
            <h2 className="text-xl font-semibold mb-4">Agregar Nueva Credencial</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nombre
                </label>
                <input
                  type="text"
                  value={secretForm.name}
                  onChange={(e) => setSecretForm({ ...secretForm, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="api_key_sportradar"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Valor
                </label>
                <input
                  type="password"
                  value={secretForm.value}
                  onChange={(e) => setSecretForm({ ...secretForm, value: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="Valor de la credencial"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Descripción
                </label>
                <input
                  type="text"
                  value={secretForm.description}
                  onChange={(e) => setSecretForm({ ...secretForm, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="Descripción opcional"
                />
              </div>
              <button
                onClick={handleAddSecret}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
              >
                Agregar
              </button>
            </div>
          </div>
        )}

        <div className="glass rounded-2xl shadow-premium overflow-hidden">
          <h2 className="text-xl font-bold text-slate-900 p-6 border-b border-slate-200">Checkers</h2>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Nombre
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Categoría
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Implementación
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
              {checkers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                    No hay checkers configurados
                  </td>
                </tr>
              ) : (
                checkers.map((checker) => (
                  <tr key={checker.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{checker.name}</div>
                      {checker.description && (
                        <div className="text-sm text-gray-500">{checker.description}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {checker.category}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {checker.implementation_key}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {checker.enabled ? (
                        <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">
                          Habilitado
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800">
                          Deshabilitado
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {!isDemo && (
                        <button
                          onClick={() => handleToggleChecker(checker.id, checker.enabled)}
                          className={`${
                            checker.enabled ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'
                          } hover:underline`}
                        >
                          {checker.enabled ? 'Deshabilitar' : 'Habilitar'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="glass rounded-2xl shadow-premium overflow-hidden">
          <h2 className="text-xl font-bold text-slate-900 p-6 border-b border-slate-200">Credenciales</h2>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Nombre
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Descripción
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Estado
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {secrets.length === 0 ? (
                <tr>
                  <td colSpan={3} className="px-6 py-4 text-center text-gray-500">
                    No hay credenciales configuradas
                  </td>
                </tr>
              ) : (
                secrets.map((secret) => (
                  <tr key={secret.name} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {secret.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {secret.description || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {secret.has_value ? (
                        <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">
                          Configurado
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800">
                          Vacío
                        </span>
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

