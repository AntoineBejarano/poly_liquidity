'use client';

import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { NODE_DEFINITIONS, NodeDefinition } from './types';
import { getNextNodePosition } from './graphUtils';
import { Node } from 'reactflow';
import { NodeData } from './types';

interface NodePaletteProps {
  onAddNode: (nodeType: string) => void;
  nodes: Node<NodeData>[];
}

export function NodePalette({ onAddNode, nodes }: NodePaletteProps) {
  const [searchTerm, setSearchTerm] = useState('');
  
  const filteredNodes = useMemo(() => {
    const all = Object.values(NODE_DEFINITIONS);
    if (!searchTerm) return all;
    const term = searchTerm.toLowerCase();
    return all.filter(def => 
      def.name.toLowerCase().includes(term) ||
      def.description.toLowerCase().includes(term) ||
      def.category.toLowerCase().includes(term)
    );
  }, [searchTerm]);

  const groupedNodes = useMemo(() => {
    const groups: Record<string, NodeDefinition[]> = {
      'Data Sources': [],
      'Signals / Functions': [],
      'Strategy Logic': [],
      'Risk & Constraints': [],
      'Execution': [],
    };

    filteredNodes.forEach(def => {
      switch (def.category) {
        case 'data_source':
          groups['Data Sources'].push(def);
          break;
        case 'signal':
          groups['Signals / Functions'].push(def);
          break;
        case 'strategy':
          groups['Strategy Logic'].push(def);
          break;
        case 'risk':
          groups['Risk & Constraints'].push(def);
          break;
        case 'execution':
          groups['Execution'].push(def);
          break;
      }
    });

    return groups;
  }, [filteredNodes]);

  const handleAddNode = (nodeType: string) => {
    onAddNode(nodeType);
  };

  return (
    <Card className="w-64 h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="text-sm">Node Palette</CardTitle>
        <Input
          placeholder="Search nodes..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="mt-2 h-8"
        />
      </CardHeader>
      <CardContent className="flex-1 min-h-0 p-0">
        <ScrollArea className="h-full">
          <div className="p-4 space-y-6">
            {Object.entries(groupedNodes).map(([category, nodeDefs]) => {
              if (nodeDefs.length === 0) return null;
              
              return (
                <div key={category}>
                  <div className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">
                    {category}
                  </div>
                  <div className="space-y-1">
                    {nodeDefs.map((def) => (
                      <button
                        key={def.type}
                        onClick={() => handleAddNode(def.type)}
                        className="w-full text-left p-2 rounded-lg border hover:bg-accent hover:border-primary transition-colors group"
                        style={{ borderColor: def.color + '40' }}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{def.icon}</span>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-sm truncate">{def.name}</div>
                            <div className="text-xs text-muted-foreground line-clamp-1">
                              {def.description}
                            </div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

