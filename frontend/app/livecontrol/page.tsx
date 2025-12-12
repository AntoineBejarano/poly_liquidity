'use client';

import { useEffect, useState, useRef } from 'react';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { initApiClient } from '@/lib/api';

interface Watcher {
  event_id: string;
  event_name: string;
  market_id: string;
  status: 'pending' | 'checking' | 'finished' | 'error';
  last_polymarket_response: any;
  last_sports_response: any;
  estimated_remaining_seconds: number | null;
  last_update: string | null;
  time_since_update: number | null;
  error_message: string | null;
  created_at: string;
}

interface StartWatcherForm {
  event_id: string;
  event_name: string;
  market_id: string;
}

export default function LiveControlPage() {
  const user = useUser();
  const [watchers, setWatchers] = useState<Watcher[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [formData, setFormData] = useState<StartWatcherForm>({
    event_id: '',
    event_name: '',
    market_id: '',
  });
  const [isStarting, setIsStarting] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Initialize SSE connection
  useEffect(() => {
    if (!user) return;

    const token = user.accessToken;
    if (!token) return;

    // Connect to SSE stream
    const apiBaseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const eventSource = new EventSource(
      `${apiBaseUrl}/live/watchers/stream?token=${encodeURIComponent(token)}`
    );

    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      setLoading(false);
      setError(null);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.watchers) {
          setWatchers(data.watchers);
        }
      } catch (err) {
        console.error('Error parsing SSE message:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE error:', err);
      setIsConnected(false);
      setError('Error de conexión con el servidor');
      
      // Try to reconnect after 3 seconds
      setTimeout(() => {
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
        }
        // Will reconnect via useEffect
      }, 3000);
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [user]);

  // Fallback: Polling if SSE fails or not connected
  useEffect(() => {
    if (!user) return;
    
    // Only use polling if SSE is not connected
    if (isConnected) return;

    const fetchWatchers = async () => {
      try {
        const api = initApiClient(() => user.accessToken || null);
        const response = await api.get<{ watchers: Watcher[] }>('/live/watchers');
        setWatchers(response.watchers);
        setError(null);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching watchers:', err);
        setError('No se pudo conectar al backend');
        setLoading(false);
      }
    };

    // Initial fetch
    fetchWatchers();
    
    // Poll every 2 seconds as fallback
    const interval = setInterval(fetchWatchers, 2000);
    return () => clearInterval(interval);
  }, [user, isConnected]);

  const handleStartWatcher = async () => {
    if (!user || !formData.event_id || !formData.event_name || !formData.market_id) {
      setError('Por favor completa todos los campos');
      return;
    }

    setIsStarting(true);
    setError(null);

    try {
      const api = initApiClient(() => user.accessToken || null);
      await api.post('/live/watchers/start', formData);
      
      // Clear form
      setFormData({
        event_id: '',
        event_name: '',
        market_id: '',
      });
      
      // Refresh watchers after a short delay
      setTimeout(async () => {
        try {
          const response = await api.get<{ watchers: Watcher[] }>('/live/watchers');
          setWatchers(response.watchers);
        } catch (err) {
          console.error('Error refreshing watchers:', err);
        }
      }, 500);
    } catch (err: any) {
      setError(err.message || 'Error al iniciar watcher');
    } finally {
      setIsStarting(false);
    }
  };

  const handleStopWatcher = async (eventId: string) => {
    if (!user) return;

    try {
      const api = initApiClient(() => user.accessToken || null);
      await api.post(`/live/watchers/${eventId}/stop`);
      
      // Refresh watchers
      const response = await api.get<{ watchers: Watcher[] }>('/live/watchers');
      setWatchers(response.watchers);
    } catch (err: any) {
      setError(err.message || 'Error al detener watcher');
    }
  };

  const formatTime = (seconds: number | null): string => {
    if (seconds === null || seconds === undefined) return 'N/A';
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (minutes < 60) return `${minutes}m ${secs}s`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'pending':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'checking':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'finished':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusLabel = (status: string): string => {
    switch (status) {
      case 'pending':
        return 'Pendiente';
      case 'checking':
        return 'Verificando';
      case 'finished':
        return 'Finalizado';
      case 'error':
        return 'Error';
      default:
        return status;
    }
  };

  const isWatcherAtRisk = (watcher: Watcher): boolean => {
    // Watcher is at risk if:
    // - Less than 5 minutes remaining
    // - Status is checking for more than 30 seconds
    // - Has error status
    if (watcher.status === 'error') return true;
    if (watcher.estimated_remaining_seconds !== null && watcher.estimated_remaining_seconds < 300) {
      return true;
    }
    if (watcher.time_since_update !== null && watcher.time_since_update > 30) {
      return true;
    }
    return false;
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-premium mb-4 shadow-lg animate-pulse">
              <span className="text-3xl font-bold text-white">⏳</span>
            </div>
            <p className="text-slate-600 font-medium">Cargando watchers...</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gradient">LiveControl</h1>
          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
              isConnected 
                ? 'bg-green-50 border border-green-200' 
                : 'bg-red-50 border border-red-200'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                isConnected 
                  ? 'bg-green-500 animate-pulse' 
                  : 'bg-red-500'
              }`}></div>
              <span className={`text-sm font-medium ${
                isConnected 
                  ? 'text-green-800' 
                  : 'text-red-800'
              }`}>
                {isConnected ? 'Conectado (SSE)' : 'Desconectado (Polling)'}
              </span>
            </div>
          </div>
        </div>

        {error && (
          <div className="glass rounded-2xl p-4 bg-red-50 border border-red-200">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        {/* Start Watcher Form */}
        <div className="glass rounded-2xl p-6 shadow-premium">
          <h2 className="text-xl font-bold text-slate-900 mb-4">Iniciar Nuevo Watcher</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Event ID (Deportivo)
              </label>
              <input
                type="text"
                value={formData.event_id}
                onChange={(e) => setFormData({ ...formData, event_id: e.target.value })}
                className="w-full px-4 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="event-123"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Nombre del Evento
              </label>
              <input
                type="text"
                value={formData.event_name}
                onChange={(e) => setFormData({ ...formData, event_name: e.target.value })}
                className="w-full px-4 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="Lakers vs Warriors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Market ID (Polymarket)
              </label>
              <input
                type="text"
                value={formData.market_id}
                onChange={(e) => setFormData({ ...formData, market_id: e.target.value })}
                className="w-full px-4 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="0x123..."
              />
            </div>
          </div>
          <button
            onClick={handleStartWatcher}
            disabled={isStarting || !formData.event_id || !formData.event_name || !formData.market_id}
            className="mt-4 px-6 py-3 rounded-xl gradient-premium text-white font-semibold shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          >
            {isStarting ? 'Iniciando...' : '▶️ Iniciar Watcher'}
          </button>
        </div>

        {/* Watchers Table */}
        <div className="glass rounded-2xl p-6 shadow-premium">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-slate-900">
              Watchers Activos ({watchers.length})
            </h2>
          </div>

          {watchers.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-slate-600">No hay watchers activos</p>
              <p className="text-sm text-slate-500 mt-2">
                Inicia un watcher usando el formulario de arriba
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">Evento</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">Estado</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">Tiempo Restante</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">PolyMarket</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">API Deportiva</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">Última Actualización</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {watchers.map((watcher) => {
                    const atRisk = isWatcherAtRisk(watcher);
                    return (
                      <tr
                        key={watcher.event_id}
                        className={`border-b border-slate-100 hover:bg-slate-50 ${
                          atRisk ? 'bg-red-50/50' : ''
                        }`}
                      >
                        <td className="py-3 px-4">
                          <div>
                            <p className="font-medium text-slate-900">{watcher.event_name}</p>
                            <p className="text-xs text-slate-500 mt-1">
                              {watcher.event_id}
                            </p>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(watcher.status)}`}>
                            {getStatusLabel(watcher.status)}
                          </span>
                          {atRisk && (
                            <span className="ml-2 text-red-600 text-xs">⚠️</span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <span className="text-sm text-slate-700">
                            {formatTime(watcher.estimated_remaining_seconds)}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <div className="text-xs text-slate-600">
                            {watcher.last_polymarket_response ? (
                              <span className="text-green-600">✓ OK</span>
                            ) : (
                              <span className="text-red-600">✗ Error</span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="text-xs text-slate-600">
                            {watcher.last_sports_response ? (
                              <span className="text-green-600">✓ OK</span>
                            ) : (
                              <span className="text-red-600">✗ Error</span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="text-xs text-slate-600">
                            {watcher.time_since_update !== null
                              ? `${watcher.time_since_update}s ago`
                              : 'N/A'}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <button
                            onClick={() => handleStopWatcher(watcher.event_id)}
                            className="px-3 py-1.5 rounded-lg bg-red-100 text-red-700 hover:bg-red-200 text-xs font-medium transition-colors"
                          >
                            Detener
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

