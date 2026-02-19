'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

interface CustomNodeData {
  label: string;
  nodeId: string;
  nodeType: string;
  config: Record<string, any>;
  isEntryNode: boolean;
}

/* Muted institutional palette — no neon */
const nodeBarColors: Record<string, string> = {
  collect_state: 'bg-[hsl(var(--accent-secondary))]',
  edge_and_risk_check: 'bg-[hsl(var(--warning))]',
  calculate_order_size: 'bg-[hsl(var(--muted-foreground))]',
  emit_execution_intent: 'bg-[hsl(var(--primary))]',
  fetch_external_source: 'bg-[hsl(var(--accent-secondary))]',
  update_state_cache: 'bg-[hsl(var(--muted-foreground))]',
  log: 'bg-[hsl(var(--muted-foreground))]',
  noop: 'bg-[hsl(var(--muted-foreground))]',
  telegram_listener: 'bg-[hsl(var(--accent-secondary))]',
  fetch_ps3838_fixtures: 'bg-[hsl(var(--accent-secondary))]',
  fetch_ps3838_odds: 'bg-[hsl(var(--accent-secondary))]',
  match_resolution_ps3838: 'bg-[hsl(var(--primary))]',
  risk_check: 'bg-[hsl(var(--warning))]',
  precheck: 'bg-[hsl(var(--muted-foreground))]',
};

export const CustomNode = memo(({ data, selected }: NodeProps<CustomNodeData>) => {
  const barColor = nodeBarColors[data.nodeType] || 'bg-[hsl(var(--muted-foreground))]';

  return (
    <div
      className={`px-4 py-2 rounded-[var(--radius)] border min-w-[150px] bg-card shadow-premium-sm ${
        selected
          ? 'border-[hsl(var(--primary))]'
          : 'border-[hsl(var(--border))]/60'
      } ${data.isEntryNode ? 'ring-1 ring-[hsl(var(--primary))]/50' : ''}`}
    >
      {data.isEntryNode && (
        <div
          className="absolute -top-1.5 -left-1.5 w-3 h-3 rounded-full bg-[hsl(var(--primary))] border-2 border-card"
          aria-hidden
        />
      )}

      <div className={`w-full h-0.5 rounded-t ${barColor} mb-2`} />

      <div className="text-center">
        <div className="text-xs font-semibold text-foreground">{data.label}</div>
        <div className="text-xs text-muted-foreground mt-0.5">{data.nodeId}</div>
      </div>

      <Handle type="target" position={Position.Top} className="graph-handle w-2.5 h-2.5" />
      <Handle type="source" position={Position.Bottom} className="graph-handle w-2.5 h-2.5" />
    </div>
  );
});

CustomNode.displayName = 'CustomNode';

