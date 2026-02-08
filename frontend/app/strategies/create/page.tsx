'use client';

import { useState, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { useUser, useStackApp } from '@stackframe/stack';
import { useRouter } from 'next/navigation';
import { Layout } from '@/components/Layout';
import { StrategyTemplateSelector } from '@/components/StrategyTemplateSelector';
import { StrategyConfigForm } from '@/components/StrategyConfigForm';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { DecisionGraph, SupportGraph } from '@/types/strategy';
import { Skeleton } from '@/components/ui/skeleton';

// Lazy load GraphBuilder (heavy component with ReactFlow)
const GraphBuilder = dynamic(
  () => import('@/components/GraphBuilder/GraphBuilder').then(mod => ({ default: mod.GraphBuilder })),
  {
    loading: () => (
      <div className="w-full h-[600px] border border-border rounded-lg p-4">
        <Skeleton className="w-full h-full" />
      </div>
    ),
    ssr: false,
  }
);

interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  fields: any[];
}

export default function CreateStrategyPage() {
  const user = useUser();
  const stackApp = useStackApp();
  const router = useRouter();

  const [step, setStep] = useState(0); // 0: template, 1: config, 2: events, 3: review
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [templateConfig, setTemplateConfig] = useState<Record<string, any>>({});
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [compiledGraphs, setCompiledGraphs] = useState<{
    decision_graph: DecisionGraph;
    support_graphs: SupportGraph[];
    risk_config: Record<string, any>;
  } | null>(null);
  const [showAdvancedGraph, setShowAdvancedGraph] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wallets, setWallets] = useState<Array<{ id: string; label: string; address: string; active: boolean }>>([]);
  const [walletId, setWalletId] = useState<string | null>(null);

  useEffect(() => {
    if (!user || !stackApp || step !== 1) return;
    const api = initApiClient(createTokenGetter(user, stackApp));
    api.get<Array<{ id: string; label: string; address: string; active: boolean }>>('/wallets').then((w) => setWallets(w ?? [])).catch(() => setWallets([]));
  }, [user, stackApp, step]);

  const handleTemplateSelect = async (template: any) => {
    console.log('Template selected:', template);
    
    // Always fetch full details to ensure we have fields
    if (template.id) {
      const api = initApiClient(createTokenGetter(user!, stackApp));
      try {
        const templateDetails = await api.get<Template>(`/strategy-templates/${template.id}`);
        if (templateDetails) {
          console.log('Template details loaded:', templateDetails);
          console.log('Fields:', templateDetails.fields);
          setSelectedTemplate(templateDetails);
          setName(templateDetails.name);
          setDescription(templateDetails.description);
        }
        setStep(1);
      } catch (err) {
        console.error('Error loading template details:', err);
        setError(`Error al cargar los detalles de la plantilla: ${err instanceof Error ? err.message : 'Error desconocido'}`);
      }
    } else {
      // Fallback if no id
      setSelectedTemplate(template);
      setName(template.name);
      setDescription(template.description);
      setStep(1);
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
        risk_config: compiledGraphs.risk_config,
        tags: tags.length > 0 ? tags : undefined,
        wallet_id: walletId || undefined,
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
          <h1 className="text-2xl font-bold text-slate-900">Crear Estrategia</h1>
          <p className="text-sm text-slate-600 mt-1">
            Configura una estrategia de trading usando plantillas predefinidas
          </p>
        </div>

        {/* Steps */}
        <div className="flex items-center gap-2">
          {[0, 1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium ${
                  step === s
                    ? 'bg-blue-600 text-white'
                    : step > s
                    ? 'bg-green-500 text-white'
                    : 'bg-slate-200 text-slate-600'
                }`}
              >
                {step > s ? '✓' : s === 0 ? '1' : s === 1 ? '2' : s === 2 ? '3' : '4'}
              </div>
              {s < 3 && (
                <div
                  className={`h-0.5 w-12 ${
                    step > s ? 'bg-green-500' : 'bg-slate-200'
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Step 0: Template Selection */}
        {step === 0 && (
          <div className="space-y-4 p-6 bg-white border border-slate-200 rounded-lg">
            <StrategyTemplateSelector onSelectTemplate={handleTemplateSelect} />
          </div>
        )}

        {/* Step 1: Configuration (Combined: Basic Info + Template Config) */}
        {step === 1 && selectedTemplate && (
          <div className="space-y-6">
            {/* Basic Info */}
            <div className="p-6 bg-white border border-slate-200 rounded-lg space-y-4">
              <h2 className="text-lg font-semibold text-slate-900">Información Básica</h2>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Nombre <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Mi Estrategia de Liquidez"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Descripción
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="Descripción de la estrategia..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Tags</label>
                <input
                  type="text"
                  value={tags.join(', ')}
                  onChange={(e) => setTags(e.target.value.split(',').map((t) => t.trim()).filter(Boolean))}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="liquidez, near-end, bajo-riesgo"
                />
                <p className="text-xs text-slate-500 mt-1">Separa los tags con comas</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Cuenta asociada</label>
                <select
                  value={walletId ?? 'active'}
                  onChange={(e) => setWalletId(e.target.value === 'active' ? null : e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                >
                  <option value="active">Usar cuenta activa del usuario</option>
                  {wallets.map((w) => (
                    <option key={w.id} value={w.id}>{w.label || w.address}</option>
                  ))}
                </select>
                <p className="text-xs text-slate-500 mt-1">Opcional. Si no eliges una, se usará la cuenta activa. Gestiona cuentas en Ajustes → Wallets.</p>
              </div>
            </div>

            {/* Template Configuration */}
            {selectedTemplate.fields && selectedTemplate.fields.length > 0 ? (
              <div className="p-6 bg-white border border-slate-200 rounded-lg">
                <StrategyConfigForm
                  templateId={selectedTemplate.id}
                  templateName={selectedTemplate.name}
                  templateDescription={selectedTemplate.description}
                  fields={selectedTemplate.fields || []}
                  onChange={handleConfigChange}
                />
              </div>
            ) : (
              <div className="p-6 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800">
                  Cargando configuración de la plantilla...
                </p>
              </div>
            )}

            {/* Advanced: View Generated Graph (Optional) */}
            {compiledGraphs && (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                <button
                  onClick={() => setShowAdvancedGraph(!showAdvancedGraph)}
                  className="text-sm font-medium text-slate-700 hover:text-slate-900 flex items-center gap-2"
                >
                  {showAdvancedGraph ? '▼' : '▶'} Ver lógica interna (avanzado)
                </button>
                {showAdvancedGraph && (
                  <div className="mt-4 space-y-4">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-900 mb-2">Decision Graph</h4>
                      <GraphBuilder
                        graph={compiledGraphs.decision_graph}
                        onGraphChange={() => {}} // Read-only
                        pathType="hot"
                        readOnly={true}
                      />
                    </div>
                    {compiledGraphs.support_graphs.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold text-slate-900 mb-2">Support Graphs</h4>
                        {compiledGraphs.support_graphs.map((sg, idx) => (
                          <div key={idx} className="mb-4">
                            <h5 className="text-xs font-medium text-slate-700 mb-2">{sg.name}</h5>
                            <GraphBuilder
                              graph={sg}
                              onGraphChange={() => {}} // Read-only
                              pathType="cold"
                              readOnly={true}
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => setStep(0)}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
              >
                Anterior
              </button>
              <button
                onClick={() => setStep(2)}
                disabled={!name.trim() || !compiledGraphs}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
              >
                Siguiente: Activar Eventos
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Activate Events (Placeholder - to be implemented) */}
        {step === 2 && (
          <div className="p-6 bg-white border border-slate-200 rounded-lg space-y-4">
            <h2 className="text-lg font-semibold text-slate-900">Activar Eventos</h2>
            <p className="text-sm text-slate-600">
              Selecciona los eventos en los que esta estrategia operará.
            </p>
            <p className="text-xs text-slate-500 italic">
              (Esta funcionalidad se implementará en la siguiente fase)
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setStep(1)}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
              >
                Anterior
              </button>
              <button
                onClick={() => setStep(3)}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
              >
                Continuar
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Review & Create */}
        {step === 3 && (
          <div className="p-6 bg-white border border-slate-200 rounded-lg space-y-4">
            <h2 className="text-lg font-semibold text-slate-900">Revisión Final</h2>
            <div className="space-y-2 text-sm">
              <div>
                <span className="font-medium text-slate-700">Nombre:</span> {name}
              </div>
              <div>
                <span className="font-medium text-slate-700">Plantilla:</span> {selectedTemplate?.name}
              </div>
              <div>
                <span className="font-medium text-slate-700">Configuración:</span>
                <pre className="mt-2 p-3 bg-slate-50 rounded text-xs overflow-auto max-h-40">
                  {JSON.stringify(templateConfig, null, 2)}
                </pre>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setStep(2)}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
              >
                Anterior
              </button>
              <button
                onClick={handleCreate}
                disabled={loading || !compiledGraphs}
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
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
