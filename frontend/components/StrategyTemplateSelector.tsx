'use client';

import { useState, useEffect } from 'react';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';

interface StrategyTemplate {
  id: string;
  name: string;
  description: string;
}

interface StrategyTemplateSelectorProps {
  onSelectTemplate: (template: any) => void;
}

export function StrategyTemplateSelector({ onSelectTemplate }: StrategyTemplateSelectorProps) {
  const user = useUser();
  const stackApp = useStackApp();
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [templateDetails, setTemplateDetails] = useState<any>(null);

  useEffect(() => {
    if (!user) return;

    const api = initApiClient(createTokenGetter(user, stackApp));

    const loadTemplates = async () => {
      try {
        setLoading(true);
        const data = await api.get<StrategyTemplate[]>('/strategy-templates');
        setTemplates(data);
      } catch (err) {
        console.error('Error loading templates:', err);
      } finally {
        setLoading(false);
      }
    };

    loadTemplates();
  }, [user, stackApp]);

  const handleSelectTemplate = async (templateId: string) => {
    if (!user) return;

    const api = initApiClient(createTokenGetter(user, stackApp));

    try {
      const details = await api.get<any>(`/strategy-templates/${templateId}`);
      console.log('Template details from API:', details);
      setTemplateDetails(details);
      setSelectedTemplateId(templateId);
      onSelectTemplate(details);
    } catch (err) {
      console.error('Error loading template details:', err);
      // Show error to user
      alert('Error al cargar la plantilla. Por favor, intenta de nuevo.');
    }
  };

  if (loading) {
    return (
      <div className="p-4 text-center text-sm text-slate-600">
        Cargando plantillas...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-slate-900 mb-2">
          Plantillas de Estrategias
        </h3>
        <p className="text-xs text-slate-600 mb-4">
          Selecciona una plantilla para empezar con una estrategia preconfigurada
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {templates.map((template) => (
          <button
            key={template.id}
            onClick={() => handleSelectTemplate(template.id)}
            className={`p-4 text-left border-2 rounded-lg transition-all ${
              selectedTemplateId === template.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-slate-200 hover:border-slate-300 bg-white'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-slate-900 mb-1">
                  {template.name}
                </h4>
                <p className="text-xs text-slate-600">{template.description}</p>
              </div>
              {selectedTemplateId === template.id && (
                <div className="ml-4 text-blue-600">✓</div>
              )}
            </div>
          </button>
        ))}
      </div>

      {selectedTemplateId && templateDetails && (
        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-xs text-green-800">
            ✓ Plantilla "{templateDetails.name}" seleccionada. Los grafos se han cargado automáticamente.
          </p>
        </div>
      )}
    </div>
  );
}

