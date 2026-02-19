'use client';

import { useState, useEffect } from 'react';
import { Node } from 'reactflow';
import { GraphNodeDefinition } from '@/types/strategy';
import { useConfirmDialog } from '@/contexts/NotificationContext';

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
  const { confirmDialog } = useConfirmDialog();
  const [config, setConfig] = useState<Record<string, any>>(node.data.config || {});

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sync local config from prop
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
    <div className="absolute top-4 right-4 w-96 bg-card border border-[hsl(var(--border))]/50 rounded-[var(--radius-lg)] shadow-premium-md p-6 z-10 max-h-[600px] overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-foreground">{nodeDefinition.name}</h3>
          <p className="text-xs text-muted-foreground mt-1">{nodeDefinition.description}</p>
        </div>
        <button
          onClick={async () => {
            const ok = await confirmDialog({
              title: 'Eliminar nodo',
              description: '¿Eliminar este nodo?',
              confirmLabel: 'Eliminar',
              variant: 'danger',
            });
            if (ok) onDelete();
          }}
          className="text-xs text-destructive hover:opacity-80"
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
              <label className="block text-sm font-medium text-foreground mb-2">
                {key}
                {isRequired && <span className="text-destructive ml-1">*</span>}
              </label>
              {prop.description && (
                <p className="text-xs text-muted-foreground mb-2">{prop.description}</p>
              )}
              {prop.type === 'string' && (
                <input
                  type="text"
                  value={value || ''}
                  onChange={(e) => handleConfigChange(key, e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-[hsl(var(--border))]/60 bg-background rounded-[var(--radius)] focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder={prop.description || key}
                />
              )}
              {(prop.type === 'number' || prop.type === 'integer') && (
                <input
                  type="number"
                  value={value || ''}
                  onChange={(e) => handleConfigChange(key, Number(e.target.value))}
                  className="w-full px-3 py-2 text-sm border border-[hsl(var(--border))]/60 bg-background rounded-[var(--radius)] focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder={prop.description || key}
                />
              )}
              {prop.type === 'boolean' && (
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={value || false}
                    onChange={(e) => handleConfigChange(key, e.target.checked)}
                    className="w-5 h-5 text-primary border-[hsl(var(--border))] rounded focus:ring-ring"
                  />
                  <span className="text-sm text-foreground">
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
                  className="w-full px-3 py-2 text-sm border border-[hsl(var(--border))]/60 bg-background rounded-[var(--radius)] focus:outline-none focus:ring-1 focus:ring-ring font-mono"
                  rows={6}
                  placeholder={prop.description || '{}'}
                />
              )}
              {prop.enum && (
                <select
                  value={value || ''}
                  onChange={(e) => handleConfigChange(key, e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-[hsl(var(--border))]/60 bg-background rounded-[var(--radius)] focus:outline-none focus:ring-1 focus:ring-ring"
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

      <div className="mt-4 pt-4 border-t border-[hsl(var(--border))]/50">
        {!isEntryNode && (
          <button
            onClick={onSetEntryNode}
            className="w-full px-3 py-1.5 text-xs font-medium text-primary bg-primary/10 rounded-[var(--radius)] hover:bg-primary/15 transition-colors"
          >
            Establecer como Nodo de Entrada
          </button>
        )}
        {isEntryNode && (
          <div className="text-xs text-primary font-medium text-center py-1.5">
            ✓ Nodo de Entrada
          </div>
        )}
      </div>
    </div>
  );
}

