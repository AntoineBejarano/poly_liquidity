'use client';

import { useMemo } from 'react';
import { Node } from 'reactflow';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { NodeData, NODE_DEFINITIONS } from './types';
import { Info } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface InspectorPanelProps {
  selectedNode: Node<NodeData> | null;
  onUpdateNode: (nodeId: string, data: Partial<NodeData>) => void;
}

export function InspectorPanel({ selectedNode, onUpdateNode }: InspectorPanelProps) {
  const nodeDef = useMemo(() => {
    if (!selectedNode) return null;
    return NODE_DEFINITIONS[selectedNode.data.type];
  }, [selectedNode]);

  if (!selectedNode || !nodeDef) {
    return (
      <Card className="w-80 h-full">
        <CardHeader>
          <CardTitle>Inspector</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground text-sm">
            Select a node to configure
          </div>
        </CardContent>
      </Card>
    );
  }

  const handleConfigChange = (key: string, value: any) => {
    onUpdateNode(selectedNode.id, {
      config: {
        ...selectedNode.data.config,
        [key]: value,
      },
    });
  };

  const handleLabelChange = (label: string) => {
    onUpdateNode(selectedNode.id, { label });
  };

  const handleEnabledChange = (enabled: boolean) => {
    onUpdateNode(selectedNode.id, { enabled });
  };

  const renderConfigField = (key: string, schema: any) => {
    const value = selectedNode.data.config[key] ?? schema.default;

    switch (schema.type) {
      case 'string':
        if (schema.enum) {
          return (
            <Select value={value || ''} onValueChange={(v) => handleConfigChange(key, v)}>
              <SelectTrigger>
                <SelectValue placeholder={`Select ${key}`} />
              </SelectTrigger>
              <SelectContent>
                {schema.enum.map((option: string) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          );
        }
        return (
          <Input
            value={value || ''}
            onChange={(e) => handleConfigChange(key, e.target.value)}
            placeholder={schema.description || key}
          />
        );

      case 'number':
        return (
          <Input
            type="number"
            value={value ?? ''}
            onChange={(e) => handleConfigChange(key, parseFloat(e.target.value) || 0)}
            placeholder={schema.default?.toString() || '0'}
          />
        );

      case 'boolean':
        return (
          <Switch
            checked={value ?? false}
            onCheckedChange={(checked) => handleConfigChange(key, checked)}
          />
        );

      case 'array':
        return (
          <Textarea
            value={Array.isArray(value) ? value.join(', ') : ''}
            onChange={(e) => {
              const items = e.target.value.split(',').map(s => s.trim()).filter(Boolean);
              handleConfigChange(key, items);
            }}
            placeholder="Comma-separated values"
          />
        );

      case 'object':
        return (
          <Textarea
            value={JSON.stringify(value || {}, null, 2)}
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value);
                handleConfigChange(key, parsed);
              } catch {
                // Invalid JSON, ignore
              }
            }}
            placeholder="JSON object"
            className="font-mono text-xs"
            rows={4}
          />
        );

      default:
        return (
          <Input
            value={value?.toString() || ''}
            onChange={(e) => handleConfigChange(key, e.target.value)}
            placeholder={key}
          />
        );
    }
  };

  return (
    <Card className="w-80 h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="flex items-center gap-2">
          <span>{nodeDef.icon}</span>
          <span className="truncate">{selectedNode.data.label || nodeDef.name}</span>
        </CardTitle>
        <Badge variant="outline" className="mt-2" style={{ borderColor: nodeDef.color, color: nodeDef.color }}>
          {nodeDef.category}
        </Badge>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto space-y-4">
        {/* Node Label */}
        <div className="space-y-2">
          <Label>Node Label</Label>
          <Input
            value={selectedNode.data.label || nodeDef.name}
            onChange={(e) => handleLabelChange(e.target.value)}
            placeholder={nodeDef.name}
          />
        </div>

        {/* Enabled Toggle */}
        <div className="flex items-center justify-between">
          <Label>Enabled</Label>
          <Switch
            checked={selectedNode.data.enabled !== false}
            onCheckedChange={handleEnabledChange}
          />
        </div>

        {/* Description */}
        <div className="text-xs text-muted-foreground">
          {nodeDef.description}
        </div>

        <div className="border-t pt-4 space-y-4">
          <div className="flex items-center gap-2">
            <Label className="font-semibold">Configuration</Label>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="h-3 w-3 text-muted-foreground cursor-help" />
                </TooltipTrigger>
                <TooltipContent>
                  <p>Configure node parameters</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          {Object.entries(nodeDef.configSchema).map(([key, schema]: [string, any]) => (
            <div key={key} className="space-y-2">
              <Label className="text-xs">
                {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                {schema.default !== undefined && (
                  <span className="text-muted-foreground ml-1">
                    (default: {schema.default})
                  </span>
                )}
              </Label>
              {renderConfigField(key, schema)}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}













