'use client';

import { GraphNodeDefinition } from '@/types/strategy';

interface NodePaletteProps {
  nodeDefinitions: GraphNodeDefinition[];
  onAddNode: (nodeType: string) => void;
}

const categoryStyles: Record<string, string> = {
  state: 'bg-muted/60 text-foreground border-[hsl(var(--border))]/50',
  condition: 'bg-muted/60 text-foreground border-[hsl(var(--border))]/50',
  calculation: 'bg-muted/60 text-foreground border-[hsl(var(--border))]/50',
  action: 'bg-muted/60 text-foreground border-[hsl(var(--border))]/50',
  io: 'bg-muted/60 text-foreground border-[hsl(var(--border))]/50',
};

export function NodePalette({ nodeDefinitions, onAddNode }: NodePaletteProps) {
  const groupedByCategory = nodeDefinitions.reduce((acc, def) => {
    const category = def.category || 'other';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(def);
    return acc;
  }, {} as Record<string, GraphNodeDefinition[]>);

  return (
    <div className="absolute bottom-4 left-4 w-72 bg-card border border-[hsl(var(--border))]/50 rounded-[var(--radius-lg)] shadow-premium-md p-4 z-10 max-h-[450px] overflow-y-auto">
      <h3 className="text-xs font-semibold text-foreground mb-3">Nodos Disponibles</h3>

      <div className="space-y-3">
        {Object.entries(groupedByCategory).map(([category, defs]) => (
          <div key={category}>
            <div className="text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wide">
              {category}
            </div>
            <div className="space-y-1">
              {defs.map((def) => (
                <button
                  key={def.node_type}
                  onClick={() => onAddNode(def.node_type)}
                  className={`w-full text-left px-2 py-1.5 text-xs rounded-[var(--radius)] border transition-colors hover:bg-muted/50 ${
                    categoryStyles[category] || 'bg-muted/60 text-foreground border-[hsl(var(--border))]/50'
                  }`}
                >
                  <div className="font-medium">{def.name}</div>
                  {def.description && (
                    <div className="text-xs opacity-75 mt-0.5 line-clamp-1">
                      {def.description}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

