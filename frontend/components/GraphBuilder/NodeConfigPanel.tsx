'use client';

import { useState, useEffect } from 'react';
import { Node } from 'reactflow';
import { GraphNodeDefinition } from '@/types/strategy';

interface NodeConfigPanelProps {
  node: Node;
  nodeDefinition: GraphNodeDefinition;
  onConfigChange: (config: Record<string, any>) => void;
  onDelete: () => void;
  onSetEntryNode: () => void;
  isEntryNode: boolean;
}

export function NodeConfigPanel({
  node,
  nodeDefinition,
  onConfigChange,
  onDelete,
  onSetEntryNode,
  isEntryNode,
}: NodeConfigPanelProps) {
  const [config, setConfig] = useState<Record<string, any>>(node.data.config || {});

  useEffect(() => {
    setConfig(node.data.config || {});
  }, [node.data.config]);

  const handleConfigChange = (key: string, value: any) => {
    const newConfig = { ...config, [key]: value };
    setConfig(newConfig);
    onConfigChange(newConfig);
  };

  const schema = nodeDefinition.config_schema || {};
  const properties = schema.properties || {};

  return (
    <div className="absolute top-4 right-4 w-96 bg-white border-2 border-slate-300 rounded-lg shadow-xl p-6 z-10 max-h-[600px] overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{nodeDefinition.name}</h3>
          <p className="text-xs text-slate-500 mt-1">{nodeDefinition.description}</p>
        </div>
        <button
          onClick={() => {
            if (confirm('¿Eliminar este nodo?')) {
              onDelete();
            }
          }}
          className="text-xs text-red-600 hover:text-red-700"
        >
          Eliminar
        </button>
      </div>

      <div className="space-y-3">
        {Object.entries(properties).map(([key, prop]: [string, any]) => {
          const value = config[key];
          const isRequired = schema.required?.includes(key);

          return (
            <div key={key}>
              <label className="block text-sm font-medium text-slate-900 mb-2">
                {key}
                {isRequired && <span className="text-red-500 ml-1">*</span>}
              </label>
              {prop.description && (
                <p className="text-xs text-slate-600 mb-2">{prop.description}</p>
              )}
              {prop.type === 'string' && (
                <input
                  type="text"
                  value={value || ''}
                  onChange={(e) => handleConfigChange(key, e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder={prop.description || key}
                />
              )}
              {(prop.type === 'number' || prop.type === 'integer') && (
                <input
                  type="number"
                  value={value || ''}
                  onChange={(e) => handleConfigChange(key, Number(e.target.value))}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder={prop.description || key}
                />
              )}
              {prop.type === 'boolean' && (
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={value || false}
                    onChange={(e) => handleConfigChange(key, e.target.checked)}
                    className="w-5 h-5 text-blue-600 border-slate-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm text-slate-700">
                    {value ? 'Activado' : 'Desactivado'}
                  </span>
                </div>
              )}
              {prop.type === 'object' && (
                <textarea
                  value={JSON.stringify(value || {}, null, 2)}
                  onChange={(e) => {
                    try {
                      handleConfigChange(key, JSON.parse(e.target.value));
                    } catch {
                      // Invalid JSON, ignore
                    }
                  }}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono"
                  rows={6}
                  placeholder={prop.description || '{}'}
                />
              )}
              {prop.enum && (
                <select
                  value={value || ''}
                  onChange={(e) => handleConfigChange(key, e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Seleccionar...</option>
                  {prop.enum.map((option: string) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-4 pt-4 border-t border-slate-200">
        {!isEntryNode && (
          <button
            onClick={onSetEntryNode}
            className="w-full px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
          >
            Establecer como Nodo de Entrada
          </button>
        )}
        {isEntryNode && (
          <div className="text-xs text-blue-600 font-medium text-center py-1.5">
            ✓ Nodo de Entrada
          </div>
        )}
      </div>
    </div>
  );
}

