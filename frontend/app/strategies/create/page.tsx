'use client';

import { useState, useEffect } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { useRouter, useSearchParams } from 'next/navigation';
import { Layout } from '@/components/Layout';
import { StrategyTemplateSelector } from '@/components/StrategyTemplateSelector';
import { StrategyConfigForm, type TemplateField } from '@/components/StrategyConfigForm';
import { StrategyWorkflowView } from '@/components/StrategyWorkflowView';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { DecisionGraph, SupportGraph } from '@/types/strategy';
import { Skeleton } from '@/components/ui/skeleton';

interface Template {
  id: string;
  name: string;
  description: string;
  category?: string;
  /** Form field definitions from API; typed loosely to accept StrategyTemplateDetails from selector */
  fields?: unknown[];
}

export default function CreateStrategyPage() {
  const user = useUser();
  const stackApp = useStackApp();
  const router = useRouter();
  const searchParams = useSearchParams();
  const presetTemplateId = searchParams?.get('template') || null;

  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [templateConfig, setTemplateConfig] = useState<Record<string, any>>({});
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [compiledGraphs, setCompiledGraphs] = useState<{
    decision_graph: DecisionGraph;
    support_graphs: SupportGraph[];
    execution_graph?: Record<string, any>;
    risk_config: Record<string, any>;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingPreset, setLoadingPreset] = useState(!!presetTemplateId);
  const [error, setError] = useState<string | null>(null);

  // Mantener loadingPreset cuando hay preset en URL hasta que cargue o falle
  useEffect(() => {
    if (!presetTemplateId) setLoadingPreset(false);
  }, [presetTemplateId]);

  // Preselect template from URL (e.g. /strategies/create?template=telegram_tipster_ps3838)
  useEffect(() => {
    if (!presetTemplateId) return;
    if (!user || !stackApp) return;
    setError(null);
    setLoadingPreset(true);
    const api = initApiClient(createTokenGetter(user, stackApp));
    let cancelled = false;
    api
      .get<Template>(`/strategy-templates/${presetTemplateId}`)
      .then((templateDetails) => {
        if (!cancelled && templateDetails) {
          setSelectedTemplate(templateDetails);
          setName(templateDetails.name);
          setDescription(templateDetails.description || '');
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err?.message || 'No se pudo cargar la plantilla. Elige una abajo.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingPreset(false);
      });
    return () => {
      cancelled = true;
    };
  }, [user, stackApp, presetTemplateId]);

  const handleTemplateSelect = async (template: Template) => {
    if (template.id) {
      const api = initApiClient(createTokenGetter(user!, stackApp));
      try {
        const templateDetails = await api.get<Template>(`/strategy-templates/${template.id}`);
        if (templateDetails) {
          setSelectedTemplate(templateDetails);
          setName(templateDetails.name);
          setDescription(templateDetails.description || '');
        }
      } catch (err) {
        console.error('Error loading template details:', err);
        setError(`Error al cargar los detalles de la plantilla: ${err instanceof Error ? err.message : 'Error desconocido'}`);
      }
    } else {
      setSelectedTemplate(template);
      setName(template.name);
      setDescription(template.description || '');
    }
  };

  const handleConfigChange = async (config: Record<string, any>) => {
    setTemplateConfig(config);
    
    // Auto-compile when config changes
    if (selectedTemplate) {
      const api = initApiClient(createTokenGetter(user!, stackApp));
      try {
        const compiled = await api.post<{
          decision_graph: DecisionGraph;
          support_graphs: SupportGraph[];
          risk_config: Record<string, any>;
        }>(`/strategy-templates/${selectedTemplate.id}/compile`, config);
        setCompiledGraphs(compiled);
      } catch (err) {
        console.error('Error compiling template:', err);
        // Don't show error, just don't update compiled graphs
      }
    }
  };

  const handleCreate = async () => {
    if (!name.trim()) {
      setError('El nombre es requerido');
      return;
    }

    if (!compiledGraphs) {
      setError('Error: No se pudo compilar la estrategia. Por favor, revisa la configuración.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const api = initApiClient(createTokenGetter(user!, stackApp));
      const strategy = await api.post<{ id: string }>('/api/strategies', {
        name,
        description: description || undefined,
        decision_graph: compiledGraphs.decision_graph,
        support_graphs: compiledGraphs.support_graphs,
        execution_graph: compiledGraphs.execution_graph ?? undefined,
        risk_config: compiledGraphs.risk_config,
        tags: tags.length > 0 ? tags : undefined,
        wallet_id: undefined,
      });

      if (strategy?.id) router.push(`/strategies/${strategy.id}`);
    } catch (err) {
      console.error('Error creating strategy:', err);
      setError(err instanceof Error ? err.message : 'Error al crear estrategia');
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return null;
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Crear Estrategia</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Configura una estrategia de trading usando plantillas predefinidas
          </p>
        </div>

        {error && (
          <div className="p-4 bg-destructive/10 border border-destructive/30 rounded-lg">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Con ?template= en URL: cargar esa plantilla y mostrar config; no pedir elegir otra vez */}
        {loadingPreset && (
          <div className="p-8 bg-card border border-border rounded-lg text-center">
            <p className="text-muted-foreground">Cargando plantilla seleccionada…</p>
            <Skeleton className="mx-auto mt-4 h-10 w-48" />
          </div>
        )}

        {/* Selector de plantilla: solo si no hay preset en URL o si falló la carga del preset */}
        {!loadingPreset && (!presetTemplateId || !selectedTemplate) && (
          <div className="space-y-4 p-6 bg-card border border-border rounded-lg">
            <StrategyTemplateSelector onSelectTemplate={handleTemplateSelect} />
          </div>
        )}

        {/* Si llegamos con ?template= y ya cargó: mostrar solo la plantilla elegida y la config */}
        {presetTemplateId && selectedTemplate && !loadingPreset && (
          <div className="p-4 bg-muted/30 border border-border rounded-lg flex items-center justify-between flex-wrap gap-2">
            <p className="text-sm text-foreground">
              Plantilla: <span className="font-medium">{selectedTemplate.name}</span>
            </p>
            <button
              type="button"
              onClick={() => {
                router.replace('/strategies/create');
                setSelectedTemplate(null);
                setError(null);
              }}
              className="text-sm text-primary hover:underline"
            >
              Elegir otra plantilla
            </button>
          </div>
        )}

        {/* Config: Basic Info + Template Config (same page when template selected) */}
        {selectedTemplate && !loadingPreset && (
          <div className="space-y-6">
            {/* Basic Info */}
            <div className="p-6 bg-card border border-border rounded-lg space-y-4">
              <h2 className="text-lg font-semibold text-foreground">Información Básica</h2>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Nombre <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-input rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="Mi Estrategia de Liquidez"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Descripción
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-input rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  rows={3}
                  placeholder="Descripción de la estrategia..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Tags</label>
                <input
                  type="text"
                  value={tags.join(', ')}
                  onChange={(e) => setTags(e.target.value.split(',').map((t) => t.trim()).filter(Boolean))}
                  className="w-full px-3 py-2 text-sm border border-input rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="liquidez, near-end, bajo-riesgo"
                />
                <p className="text-xs text-muted-foreground mt-1">Separa los tags con comas</p>
              </div>
            </div>

            {/* Template Configuration */}
            {selectedTemplate.fields && selectedTemplate.fields.length > 0 ? (
              <div className="p-6 bg-card border border-border rounded-lg">
                <StrategyConfigForm
                  templateId={selectedTemplate.id}
                  templateName={selectedTemplate.name}
                  templateDescription={selectedTemplate.description}
                  fields={(selectedTemplate.fields ?? []) as TemplateField[]}
                  onChange={handleConfigChange}
                />
              </div>
            ) : (
              <div className="p-6 bg-muted/50 border border-border rounded-lg">
                <p className="text-sm text-muted-foreground">
                  Cargando configuración de la plantilla...
                </p>
              </div>
            )}

            {/* Workflow user-friendly */}
            {compiledGraphs && selectedTemplate && (
              <StrategyWorkflowView templateId={selectedTemplate.id} />
            )}

            <div className="flex gap-2">
              <button
                onClick={() => setSelectedTemplate(null)}
                type="button"
                className="px-4 py-2 text-sm font-medium text-foreground bg-muted rounded-lg hover:bg-muted/80 transition-colors"
              >
                Cambiar plantilla
              </button>
              <button
                onClick={handleCreate}
                disabled={!name.trim() || !compiledGraphs || loading}
                className="px-4 py-2 text-sm font-medium text-primary-foreground bg-primary rounded-lg hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Creando...' : 'Crear Estrategia'}
              </button>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
