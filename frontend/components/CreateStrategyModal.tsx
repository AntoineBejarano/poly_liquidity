'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { initApiClient, createTokenGetter } from '@/lib/api';

interface Template {
  id: string;
  name: string;
  description: string;
}

interface CreateStrategyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CreateStrategyModal({ isOpen, onClose }: CreateStrategyModalProps) {
  const user = useUser();
  const stackApp = useStackApp();
  const router = useRouter();
  
  const [name, setName] = useState('');
  const [templateId, setTemplateId] = useState<string>('');
  const [initialCapital, setInitialCapital] = useState(10000);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !user) return;

    const loadTemplates = async () => {
      const api = initApiClient(createTokenGetter(user, stackApp));
      try {
        const data = await api.get<Template[]>('/strategy-templates');
        setTemplates(data);
        if (data.length > 0) {
          setTemplateId(data[0].id);
        }
      } catch (err) {
        console.error('Error loading templates:', err);
      }
    };

    loadTemplates();
  }, [isOpen, user, stackApp]);

  const handleCreate = async () => {
    if (!name.trim() || !templateId) {
      setError('Nombre y tipo de estrategia son requeridos');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      
      // Get template details and compile with defaults
      const templateDetails = await api.get<any>(`/strategy-templates/${templateId}`);
      const defaultConfig: Record<string, any> = {};
      
      // Set defaults from template fields
      if (templateDetails.fields) {
        templateDetails.fields.forEach((field: any) => {
          if (field.default !== undefined) {
            defaultConfig[field.key] = field.default;
          }
        });
      }
      
      // Compile template
      const compiled = await api.post<{
        decision_graph: any;
        support_graphs: any[];
        risk_config: any;
      }>(`/strategy-templates/${templateId}/compile`, defaultConfig);
      
      // Create strategy
      const strategy = await api.post<{ id: string }>('/strategies', {
        name,
        description: templateDetails.description,
        decision_graph: compiled.decision_graph,
        support_graphs: compiled.support_graphs,
        risk_config: {
          ...compiled.risk_config,
          max_exposure: initialCapital,
        },
      });

      onClose();
      router.push(`/strategies/${strategy.id}/desk`);
    } catch (err) {
      console.error('Error creating strategy:', err);
      setError(err instanceof Error ? err.message : 'Error al crear estrategia');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Nueva Estrategia</h2>
          
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-800">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Nombre <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Mi Estrategia"
                autoFocus
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Tipo de Estrategia <span className="text-red-500">*</span>
              </label>
              <select
                value={templateId}
                onChange={(e) => setTemplateId(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Seleccionar...</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Capital Inicial (USDC)
              </label>
              <input
                type="number"
                value={initialCapital}
                onChange={(e) => setInitialCapital(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                min={1000}
                step={1000}
              />
            </div>
          </div>

          <div className="mt-6 flex gap-2 justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={handleCreate}
              disabled={loading || !name.trim() || !templateId}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Creando...' : 'Crear'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

