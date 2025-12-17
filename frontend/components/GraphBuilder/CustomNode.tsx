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

const nodeColors: Record<string, string> = {
  collect_state: 'bg-blue-500',
  edge_and_risk_check: 'bg-yellow-500',
  calculate_order_size: 'bg-purple-500',
  emit_execution_intent: 'bg-green-500',
  fetch_external_source: 'bg-orange-500',
  update_state_cache: 'bg-indigo-500',
  log: 'bg-gray-500',
  noop: 'bg-slate-400',
};

export const CustomNode = memo(({ data, selected }: NodeProps<CustomNodeData>) => {
  const color = nodeColors[data.nodeType] || 'bg-slate-500';

  return (
    <div
      className={`px-4 py-2 shadow-lg rounded-lg border-2 min-w-[150px] ${
        selected ? 'border-slate-900' : 'border-slate-300'
      } ${data.isEntryNode ? 'ring-2 ring-blue-400' : ''}`}
    >
      {data.isEntryNode && (
        <div className="absolute -top-2 -left-2 w-4 h-4 bg-blue-500 rounded-full border-2 border-white"></div>
      )}
      
      <div className={`w-full h-1 rounded-t-lg ${color} mb-2`}></div>
      
      <div className="text-center">
        <div className="text-xs font-semibold text-slate-900">{data.label}</div>
        <div className="text-xs text-slate-500 mt-1">{data.nodeId}</div>
      </div>

      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
    </div>
  );
});

CustomNode.displayName = 'CustomNode';

