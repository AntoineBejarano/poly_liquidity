'use client';

import { GraphNodeDefinition } from '@/types/strategy';

interface NodePaletteProps {
  nodeDefinitions: GraphNodeDefinition[];
  onAddNode: (nodeType: string) => void;
}

const categoryColors: Record<string, string> = {
  state: 'bg-blue-100 text-blue-700 border-blue-200',
  condition: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  calculation: 'bg-purple-100 text-purple-700 border-purple-200',
  action: 'bg-green-100 text-green-700 border-green-200',
  io: 'bg-orange-100 text-orange-700 border-orange-200',
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
    <div className="absolute bottom-4 left-4 w-72 bg-white border-2 border-slate-300 rounded-lg shadow-xl p-4 z-10 max-h-[450px] overflow-y-auto">
      <h3 className="text-xs font-semibold text-slate-900 mb-3">Nodos Disponibles</h3>
      
      <div className="space-y-3">
        {Object.entries(groupedByCategory).map(([category, defs]) => (
          <div key={category}>
            <div className="text-xs font-medium text-slate-600 mb-1.5 uppercase tracking-wide">
              {category}
            </div>
            <div className="space-y-1">
              {defs.map((def) => (
                <button
                  key={def.node_type}
                  onClick={() => onAddNode(def.node_type)}
                  className={`w-full text-left px-2 py-1.5 text-xs rounded border transition-colors hover:opacity-80 ${
                    categoryColors[category] || 'bg-slate-100 text-slate-700 border-slate-200'
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

