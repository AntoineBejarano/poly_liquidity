'use client';

import { useState, useEffect } from 'react';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { toast } from '@/components/ui/sonner';

interface StrategyTemplate {
  id: string;
  name: string;
  description: string;
}

interface StrategyTemplateDetails extends StrategyTemplate {
  category?: string;
  fields?: unknown[];
}

interface StrategyTemplateSelectorProps {
  onSelectTemplate: (template: StrategyTemplateDetails) => void;
}

export function StrategyTemplateSelector({ onSelectTemplate }: StrategyTemplateSelectorProps) {
  const user = useUser();
  const stackApp = useStackApp();
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [templateDetails, setTemplateDetails] = useState<StrategyTemplateDetails | null>(null);

  useEffect(() => {
    if (!user) return;

    const api = initApiClient(createTokenGetter(user, stackApp));

    const loadTemplates = async () => {
      try {
        setLoading(true);
        const data = await api.get<StrategyTemplate[]>('/strategy-templates');
        setTemplates(data ?? []);
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
      const details = await api.get<StrategyTemplateDetails>(`/strategy-templates/${templateId}`);
      console.log('Template details from API:', details);
      setTemplateDetails(details ?? null);
      setSelectedTemplateId(templateId);
      if (details != null) onSelectTemplate(details);
    } catch (err) {
      console.error('Error loading template details:', err);
      toast.error('Error al cargar la plantilla. Por favor, intenta de nuevo.');
    }
  };

  if (loading) {
    return (
      <div className="p-4 text-center text-sm text-muted-foreground">
        Cargando plantillas...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-2">
          Plantillas de Estrategias
        </h3>
        <p className="text-xs text-muted-foreground mb-4">
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
                ? 'border-primary bg-primary/10'
                : 'border-border bg-card hover:border-primary/50 hover:bg-muted/30'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-foreground mb-1">
                  {template.name}
                </h4>
                <p className="text-xs text-muted-foreground">{template.description}</p>
              </div>
              {selectedTemplateId === template.id && (
                <div className="ml-4 text-primary">✓</div>
              )}
            </div>
          </button>
        ))}
      </div>

      {selectedTemplateId != null && templateDetails != null ? (
        <div className="mt-4 p-4 bg-primary/10 border border-primary/30 rounded-lg">
          <p className="text-xs text-foreground">
            ✓ Plantilla &quot;{String(templateDetails.name)}&quot; seleccionada. Los grafos se han cargado automáticamente.
          </p>
        </div>
      ) : null}
    </div>
  );
}

