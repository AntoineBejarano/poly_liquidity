'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { NodeData, NODE_DEFINITIONS } from './types';
import { cn } from '@/lib/utils';

export const StrategyNode = memo(({ data, selected }: NodeProps<NodeData>) => {
  const nodeDef = NODE_DEFINITIONS[data.type];
  if (!nodeDef) return null;

  const isEnabled = data.enabled !== false;
  const color = nodeDef.color;

  return (
    <Card 
      className={cn(
        "min-w-[200px] border-2 transition-all",
        selected ? "ring-2 ring-primary shadow-lg" : "shadow-md",
        !isEnabled && "opacity-50"
      )}
      style={{ borderColor: selected ? color : undefined }}
    >
      <CardContent className="p-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <span className="text-lg flex-shrink-0">{nodeDef.icon}</span>
            <div className="min-w-0 flex-1">
              <div className="font-semibold text-sm truncate">{data.label || nodeDef.name}</div>
              <Badge 
                variant="outline" 
                className="text-xs mt-0.5"
                style={{ borderColor: color, color: color }}
              >
                {nodeDef.category}
              </Badge>
            </div>
          </div>
        </div>

        {/* Description */}
        <div className="text-xs text-muted-foreground mb-2 line-clamp-2">
          {nodeDef.description}
        </div>

        {/* Handles */}
        <div className="space-y-1">
          {/* Input handles */}
          {nodeDef.inputs > 0 && (
            <div className="flex items-center gap-1">
              <Handle
                type="target"
                position={Position.Top}
                className="!w-3 !h-3 !bg-blue-500 !border-2 !border-white"
                style={{ left: '50%', transform: 'translateX(-50%)' }}
              />
              <span className="text-xs text-muted-foreground">
                {nodeDef.inputs} input{nodeDef.inputs > 1 ? 's' : ''}
              </span>
            </div>
          )}

          {/* Output handles */}
          {nodeDef.outputs > 0 && (
            <div className="flex items-center gap-1">
              <Handle
                type="source"
                position={Position.Bottom}
                className="!w-3 !h-3 !bg-green-500 !border-2 !border-white"
                style={{ left: '50%', transform: 'translateX(-50%)' }}
              />
              <span className="text-xs text-muted-foreground">
                {nodeDef.outputs} output{nodeDef.outputs > 1 ? 's' : ''}
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
});

StrategyNode.displayName = 'StrategyNode';

