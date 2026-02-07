'use client';

import { useEffect, useState } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useDataMode } from '@/hooks/useDataMode';
import { toast } from '@/components/ui/sonner';

interface ConfigValue {
  value: any;
  value_type: string;
  description?: string;
  is_readonly: boolean;
  requires_confirmation: boolean;
  min_value?: string;
  max_value?: string;
  validation_rule?: any;
  updated_at?: string;
}

interface SystemConfig {
  [category: string]: {
    [key: string]: ConfigValue | any;
  };
}

interface BetSizeConfig {
  mode: 'percentage' | 'fixed_range';
  percentage?: number;
  min_amount?: number;
  max_amount?: number;
}

export default function SystemConfigPage() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const { isDemo } = useDataMode();
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [pendingUpdate, setPendingUpdate] = useState<{ key: string; value: string } | null>(null);
  const [betSizeConfig, setBetSizeConfig] = useState<BetSizeConfig | null>(null);
  const [savingBetSize, setSavingBetSize] = useState(false);

  useEffect(() => {
    if (!user || !stackApp) return;

    const api = initApiClient(createTokenGetter(user, stackApp));

    const fetchConfig = async () => {
      try {
        const data = await api.get<SystemConfig>('/system/config?include_metadata=true');
        setConfig(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading config');
      } finally {
        setLoading(false);
      }
    };

    setLoading(true);
    fetchConfig();
    
    // Fetch bet size config
    const fetchBetSizeConfig = async () => {
      try {
        const data = await api.get<BetSizeConfig>('/system/config/bet-size');
        setBetSizeConfig(data);
      } catch (err: any) {
        // Si la configuración no existe, usar valores por defecto
        if (err?.message?.includes('not found') || err?.message?.includes('Config not found')) {
          setBetSizeConfig({
            mode: 'fixed_range',
            min_amount: 10,
            max_amount: 50,
          });
        } else {
          console.error('Error loading bet size config:', err);
        }
      }
    };
    
    fetchBetSizeConfig();
  }, [user, stackApp]);
  
  const handleBetSizeSave = async (config: BetSizeConfig) => {
    if (!user || !stackApp || !isConnected) return;
    
    const api = initApiClient(createTokenGetter(user, stackApp));
    
    try {
      setSavingBetSize(true);
      setError(null);
      
      await api.put('/system/config/bet-size', config);
      
      // Reload config
      const updated = await api.get<BetSizeConfig>('/system/config/bet-size');
      setBetSizeConfig(updated);
      toast.success('Configuración de tamaño de apuesta guardada exitosamente');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error guardando configuración de tamaño de apuesta');
    } finally {
      setSavingBetSize(false);
    }
  };

  const handleEdit = (category: string, key: string, currentValue: ConfigValue) => {
    if (currentValue.is_readonly) {
      toast.error('Este parámetro es de solo lectura y no puede ser modificado.');
      return;
    }

    setEditingKey(`${category}.${key}`);
    setEditValue(String(currentValue.value));
  };

  const handleSave = async (category: string, key: string) => {
    if (!user || !isConnected) return;

    const fullKey = `${category}.${key}`;
    const configValue = config?.[category]?.[key] as ConfigValue;
    
    if (!configValue) return;

    // Check if requires confirmation
    if (configValue.requires_confirmation && !showConfirmation) {
      setPendingUpdate({ key: fullKey, value: editValue });
      setShowConfirmation(true);
      return;
    }

    if (!stackApp) return;

    const api = initApiClient(createTokenGetter(user, stackApp));

    try {
      setSaving(fullKey);
      setError(null);

      await api.put(`/system/config/${key}`, {
        value: editValue,
        requires_confirmation: configValue.requires_confirmation ? true : undefined,
      });

      // Reload config
      const updated = await api.get<SystemConfig>('/system/config?include_metadata=true');
      setConfig(updated);
      setEditingKey(null);
      setEditValue('');
      setShowConfirmation(false);
      setPendingUpdate(null);
      toast.success('Configuración guardada exitosamente');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error saving config');
    } finally {
      setSaving(null);
    }
  };

  const handleCancel = () => {
    setEditingKey(null);
    setEditValue('');
    setShowConfirmation(false);
    setPendingUpdate(null);
  };

  const categories = config ? Object.keys(config) : [];

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner text="Cargando configuración..." />
      </Layout>
    );
  }

  if (!config) {
    return (
      <Layout>
        <div className="text-center py-12">
          <p className="text-xs text-slate-500">Error cargando configuración</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-lg font-medium text-slate-900 dark:text-slate-100">Configuración</h1>
          {isDemo && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-amber-200 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-800">
              <div className="w-1.5 h-1.5 rounded-full bg-amber-500"></div>
              <span className="text-xs text-amber-800 dark:text-amber-200 font-medium">Modo Demo</span>
            </div>
          )}
        </div>

        {error && (
          <div className="border border-slate-200 rounded-lg p-3 bg-white">
            <p className="text-xs text-slate-600">{error}</p>
          </div>
        )}

        {showConfirmation && pendingUpdate && (
          <div className="border border-slate-200 rounded-lg p-4 bg-white">
            <h3 className="text-xs font-medium text-slate-900 mb-2">Confirmación Requerida</h3>
            <p className="text-xs text-slate-600 mb-3">
              Este parámetro requiere confirmación explícita para ser modificado.
            </p>
            <div className="flex gap-2">
              <button
                onClick={async () => {
                  const [category, key] = pendingUpdate.key.split('.');
                  await handleSave(category, key);
                }}
                className="px-3 py-1.5 text-xs font-medium rounded bg-slate-900 text-white hover:bg-slate-800 transition-colors"
              >
                Confirmar
              </button>
              <button
                onClick={handleCancel}
                className="px-3 py-1.5 text-xs font-medium rounded border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}

        {isDemo && (
          <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-3 bg-muted/50 dark:bg-muted/20 mb-4">
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Modo Demo: datos de ejemplo. Cambia a modo Real en el header para editar configuración.
            </p>
          </div>
        )}
        {!isDemo && !isConnected && (
          <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-3 bg-muted/50 dark:bg-muted/20 mb-4">
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Conecta el backend para editar configuración.
            </p>
          </div>
        )}

        {/* Bet Size Configuration Section */}
        <div className="border border-slate-200 rounded-lg p-5 bg-white mb-6">
          <div className="mb-4">
            <h2 className="text-sm font-medium text-slate-900 mb-1">Tamaño de Apuesta</h2>
            <p className="text-xs text-slate-500 mb-3">
              Define cuánto dinero invertir en cada operación. Elige una opción.
            </p>
          </div>
          
          <BetSizeConfigForm
            config={betSizeConfig}
            onSave={handleBetSizeSave}
            saving={savingBetSize}
            disabled={isDemo || !isConnected}
          />
        </div>

        {/* Category Tabs */}
        <div className="flex gap-1 overflow-x-auto pb-2 border-b border-slate-200 mb-4">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(selectedCategory === category ? null : category)}
              className={`px-3 py-2 text-xs font-medium transition-colors whitespace-nowrap ${
                selectedCategory === category
                  ? 'border-b-2 border-slate-900 text-slate-900'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {category.charAt(0).toUpperCase() + category.slice(1)}
            </button>
          ))}
        </div>

        {/* Config Tables */}
        {categories
          .filter((cat) => !selectedCategory || cat === selectedCategory)
          .map((category) => (
            <div key={category} className="border border-slate-200 rounded-lg p-4 bg-white">
              <h2 className="text-xs font-medium text-slate-900 mb-3">
                {category.charAt(0).toUpperCase() + category.slice(1)}
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="text-left py-2 px-3 text-xs font-medium text-slate-600">Parámetro</th>
                      <th className="text-left py-2 px-3 text-xs font-medium text-slate-600">Valor</th>
                      <th className="text-left py-2 px-3 text-xs font-medium text-slate-600">Descripción</th>
                      <th className="text-left py-2 px-3 text-xs font-medium text-slate-600">Estado</th>
                      <th className="text-left py-2 px-3 text-xs font-medium text-slate-600">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(config[category] || {}).map(([key, value]) => {
                      const configValue = value as ConfigValue;
                      const fullKey = `${category}.${key}`;
                      const isEditing = editingKey === fullKey;
                      const isSaving = saving === fullKey;

                      return (
                        <tr key={key} className="border-b border-slate-100 hover:bg-slate-50">
                          <td className="py-2.5 px-3 text-xs font-medium text-slate-900">{key}</td>
                          <td className="py-2.5 px-3">
                            {isEditing ? (
                              <input
                                type={configValue.value_type === 'float' || configValue.value_type === 'int' ? 'number' : 'text'}
                                step={configValue.value_type === 'float' ? '0.0001' : undefined}
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                min={configValue.min_value}
                                max={configValue.max_value}
                                className="w-full px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-slate-400"
                                disabled={isSaving}
                              />
                            ) : (
                              <span className="text-xs text-slate-700">
                                {typeof configValue.value === 'object' 
                                  ? JSON.stringify(configValue.value) 
                                  : String(configValue.value)}
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-xs text-slate-500">
                            {configValue.description || '-'}
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="flex gap-1.5">
                              {configValue.is_readonly && (
                                <span className="px-1.5 py-0.5 text-xs rounded border border-slate-200 bg-slate-50 text-slate-600">
                                  Solo lectura
                                </span>
                              )}
                              {configValue.requires_confirmation && (
                                <span className="px-1.5 py-0.5 text-xs rounded border border-slate-200 bg-slate-50 text-slate-600">
                                  Requiere confirmación
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="py-2.5 px-3">
                            {isEditing ? (
                              <div className="flex gap-1.5">
                                <button
                                  onClick={() => handleSave(category, key)}
                                  disabled={isSaving || !isConnected}
                                  className="px-2 py-1 text-xs rounded bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed"
                                >
                                  {isSaving ? '...' : 'Guardar'}
                                </button>
                                <button
                                  onClick={handleCancel}
                                  disabled={isSaving}
                                  className="px-2 py-1 text-xs rounded border border-slate-200 text-slate-700 hover:bg-slate-50 disabled:opacity-40"
                                >
                                  Cancelar
                                </button>
                              </div>
                            ) : (
                              <button
                                onClick={() => handleEdit(category, key, configValue)}
                                disabled={configValue.is_readonly || !isConnected}
                                className="px-2 py-1 text-xs rounded border border-slate-200 text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
                              >
                                Editar
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
      </div>
    </Layout>
  );
}

function BetSizeConfigForm({ 
  config, 
  onSave, 
  saving, 
  disabled 
}: { 
  config: BetSizeConfig | null; 
  onSave: (config: BetSizeConfig) => void;
  saving: boolean;
  disabled: boolean;
}) {
  const defaultConfig: BetSizeConfig = {
    mode: 'fixed_range',
    min_amount: 10,
    max_amount: 50,
  };
  
  const effectiveConfig = config || defaultConfig;
  
  const [mode, setMode] = useState<'percentage' | 'fixed_range'>(effectiveConfig.mode || 'fixed_range');
  const [percentage, setPercentage] = useState<number>(effectiveConfig.percentage || 5);
  const [minAmount, setMinAmount] = useState<number>(effectiveConfig.min_amount || 10);
  const [maxAmount, setMaxAmount] = useState<number>(effectiveConfig.max_amount || 50);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (mode === 'percentage') {
      if (percentage <= 0 || percentage > 100) {
        toast.error('El porcentaje debe estar entre 0 y 100');
        return;
      }
      onSave({ mode, percentage });
    } else {
      if (minAmount <= 0 || maxAmount <= 0) {
        toast.error('Los montos deben ser mayores a 0');
        return;
      }
      if (minAmount > maxAmount) {
        toast.error('El monto mínimo no puede ser mayor al máximo');
        return;
      }
      onSave({ mode, min_amount: minAmount, max_amount: maxAmount });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Mode Selection */}
      <div className="mb-4">
        <label className="block text-xs font-medium text-slate-700 mb-2">
          Modo
        </label>
        <div className="flex gap-4">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="radio"
              name="betSizeMode"
              value="percentage"
              checked={mode === 'percentage'}
              onChange={() => setMode('percentage')}
              disabled={disabled || saving}
              className="w-3 h-3 text-slate-900"
            />
            <span className="text-xs text-slate-700">Porcentaje del capital</span>
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="radio"
              name="betSizeMode"
              value="fixed_range"
              checked={mode === 'fixed_range'}
              onChange={() => setMode('fixed_range')}
              disabled={disabled || saving}
              className="w-3 h-3 text-slate-900"
            />
            <span className="text-xs text-slate-700">Rango fijo</span>
          </label>
        </div>
      </div>

      {/* Percentage Mode */}
      {mode === 'percentage' && (
        <div className="border border-slate-200 rounded-lg p-4 bg-white mb-4">
          <label className="block text-xs font-medium text-slate-700 mb-2">
            Porcentaje del capital (%)
          </label>
          <input
            type="number"
            min="0.1"
            max="100"
            step="0.1"
            value={percentage}
            onChange={(e) => setPercentage(parseFloat(e.target.value) || 0)}
            disabled={disabled || saving}
            className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-slate-400 focus:border-slate-400 disabled:opacity-40"
            placeholder="5.0"
          />
          <p className="text-xs text-slate-500 mt-2">
            Ejemplo: Con 5% y capital de $100,000, se apostará $5,000 por operación. 
            Se ajusta automáticamente según tu capital disponible.
          </p>
        </div>
      )}

      {/* Fixed Range Mode */}
      {mode === 'fixed_range' && (
        <div className="border border-slate-200 rounded-lg p-4 bg-white mb-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">
                Mínimo (USDC)
              </label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={minAmount}
                onChange={(e) => setMinAmount(parseFloat(e.target.value) || 0)}
                disabled={disabled || saving}
                className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-slate-400 focus:border-slate-400 disabled:opacity-40"
                placeholder="10.00"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">
                Máximo (USDC)
              </label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={maxAmount}
                onChange={(e) => setMaxAmount(parseFloat(e.target.value) || 0)}
                disabled={disabled || saving}
                className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-slate-400 focus:border-slate-400 disabled:opacity-40"
                placeholder="50.00"
              />
            </div>
          </div>
          <p className="text-xs text-slate-500">
            El bot elegirá un monto aleatorio entre el mínimo y máximo para cada operación. 
            Ejemplo: Con $10-$50, apostará entre $10 y $50 por mercado.
          </p>
        </div>
      )}

      {/* Submit Button */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={disabled || saving}
          className="px-4 py-2 rounded text-xs font-medium bg-slate-900 text-white hover:bg-slate-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {saving ? 'Guardando...' : 'Guardar'}
        </button>
      </div>
    </form>
  );
}

