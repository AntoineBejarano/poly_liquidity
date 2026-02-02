'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  Connection,
  addEdge,
  useNodesState,
  useEdgesState,
  Panel,
  ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';
import './builder.css';
import { StrategyNode } from '@/components/strategy/builder/StrategyNode';
import { InspectorPanel } from '@/components/strategy/builder/InspectorPanel';
import { NodePalette } from '@/components/strategy/builder/NodePalette';
import { jsonToReactFlow, reactFlowToJson, validateGraph, getNextNodePosition } from '@/components/strategy/builder/graphUtils';
import { NodeData, NODE_DEFINITIONS } from '@/components/strategy/builder/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Save, X, Plus, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Strategy } from '@/types/strategy';

const nodeTypes = {
  strategyNode: StrategyNode,
};

export default function StrategyBuilderPage() {
  const params = useParams();
  const router = useRouter();
  const strategyId = params.id as string;
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();

  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<NodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node<NodeData> | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validation, setValidation] = useState<{ valid: boolean; errors: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load strategy and graph
  useEffect(() => {
    if (!user || !strategyId) {
      setLoading(false);
      return;
    }

    const api = initApiClient(createTokenGetter(user, stackApp));

    const loadStrategy = async () => {
      try {
        setLoading(true);
        const strategyData = await api.get<Strategy>(`/api/strategies/${strategyId}`);
        setStrategy(strategyData);

        // Convert JSON graph to React Flow format
        if (strategyData.decision_graph) {
          const { nodes: flowNodes, edges: flowEdges } = jsonToReactFlow(strategyData.decision_graph);
          setNodes(flowNodes);
          setEdges(flowEdges);
        } else {
          // Initialize with empty graph
          setNodes([]);
          setEdges([]);
        }

        // Validate initial graph
        const { nodes: initialNodes, edges: initialEdges } = jsonToReactFlow(strategyData.decision_graph || { nodes: [], edges: [] });
        const validationResult = validateGraph(initialNodes, initialEdges);
        setValidation(validationResult);

        setError(null);
      } catch (err) {
        console.error('Error loading strategy:', err);
        setError(err instanceof Error ? err.message : 'Error al cargar la estrategia');
      } finally {
        setLoading(false);
      }
    };

    loadStrategy();
  }, [user, stackApp, strategyId, setNodes, setEdges]);

  // Handle node selection
  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node<NodeData>) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  // Handle connections
  const onConnect = useCallback(
    (params: Connection) => {
      // Validate connection
      const sourceNode = nodes.find(n => n.id === params.source);
      const targetNode = nodes.find(n => n.id === params.target);

      if (!sourceNode || !targetNode) return;

      // Check if target is a data source (cannot have inputs)
      if (targetNode.data.category === 'data_source') {
        return;
      }

      // Check if source is execution (cannot have outputs)
      if (sourceNode.data.category === 'execution') {
        return;
      }

      setEdges((eds) => addEdge(params, eds));
    },
    [nodes, setEdges]
  );

  // Handle node updates
  const handleUpdateNode = useCallback((nodeId: string, data: Partial<NodeData>) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...data } }
          : node
      )
    );
  }, [setNodes]);

  // Handle adding new node
  const handleAddNode = useCallback((nodeType: string) => {
    const nodeDef = NODE_DEFINITIONS[nodeType];
    if (!nodeDef) return;

    const position = getNextNodePosition(nodes);
    const newNode: Node<NodeData> = {
      id: `${nodeType}-${Date.now()}`,
      type: 'strategyNode',
      position,
      data: {
        type: nodeType,
        category: nodeDef.category,
        label: nodeDef.name,
        config: {},
        enabled: true,
      },
    };

    setNodes((nds) => [...nds, newNode]);
  }, [nodes, setNodes]);

  // Validate graph on changes
  useEffect(() => {
    const result = validateGraph(nodes, edges);
    setValidation(result);
  }, [nodes, edges]);

  // Save graph
  const handleSave = async () => {
    if (!strategy || !user) return;

    const validationResult = validateGraph(nodes, edges);
    if (!validationResult.valid) {
      setError('Graph validation failed. Please fix errors before saving.');
      return;
    }

    try {
      setSaving(true);
      const api = initApiClient(createTokenGetter(user, stackApp));

      // Convert React Flow format to JSON
      const jsonGraph = reactFlowToJson(nodes, edges);

      // Update strategy graph using the dedicated endpoint
      await api.put(`/api/strategies/${strategyId}/graph?graph_type=decision`, jsonGraph);

      setError(null);
      // Optionally redirect or show success message
    } catch (err) {
      console.error('Error saving strategy:', err);
      setError(err instanceof Error ? err.message : 'Error al guardar la estrategia');
    } finally {
      setSaving(false);
    }
  };

  if (!user) {
    return null;
  }

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner fullScreen text="Cargando strategy builder..." />
      </Layout>
    );
  }

  if (!strategy) {
    return (
      <Layout>
        <div className="p-6">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>Estrategia no encontrada</AlertDescription>
          </Alert>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <ReactFlowProvider>
        <div className="flex h-[calc(100vh-4rem)] w-full">
          {/* Node Palette */}
          <div className="w-64 border-r bg-background flex-shrink-0">
            <NodePalette onAddNode={handleAddNode} nodes={nodes} />
          </div>

          {/* Main Canvas */}
          <div className="flex-1 relative">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              nodeTypes={nodeTypes}
              fitView
              minZoom={0.2}
              maxZoom={1.5}
            >
              <Background color="#e5e7eb" gap={20} />
              <Controls />
              <MiniMap
                nodeColor={(node) => {
                  const nodeDef = NODE_DEFINITIONS[(node.data as NodeData).type];
                  return nodeDef?.color || '#6b7280';
                }}
                maskColor="rgba(0, 0, 0, 0.1)"
              />
              
              {/* Top Panel */}
              <Panel position="top-left" className="bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-4 m-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h1 className="text-xl font-bold">{strategy.name}</h1>
                    <p className="text-sm text-muted-foreground">Strategy Builder</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {validation && (
                      <div className="flex items-center gap-2">
                        {validation.valid ? (
                          <Badge variant="success" className="gap-1">
                            <CheckCircle2 className="h-3 w-3" />
                            Valid
                          </Badge>
                        ) : (
                          <Badge variant="error" className="gap-1">
                            <AlertCircle className="h-3 w-3" />
                            {validation.errors.length} error(s)
                          </Badge>
                        )}
                      </div>
                    )}
                    <Button onClick={handleSave} disabled={saving || !validation?.valid}>
                      <Save className="h-4 w-4 mr-2" />
                      {saving ? 'Saving...' : 'Save'}
                    </Button>
                    <Button variant="outline" onClick={() => router.back()}>
                      <X className="h-4 w-4 mr-2" />
                      Close
                    </Button>
                  </div>
                </div>
              </Panel>

              {/* Validation Errors */}
              {validation && !validation.valid && validation.errors.length > 0 && (
                <Panel position="top-right" className="bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-4 m-4 max-w-md">
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      <div className="font-semibold mb-2">Validation Errors:</div>
                      <ul className="list-disc list-inside space-y-1 text-sm">
                        {validation.errors.map((err, idx) => (
                          <li key={idx}>{err}</li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </Alert>
                </Panel>
              )}

              {/* Error Message */}
              {error && (
                <Panel position="bottom-center" className="bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-4 m-4">
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                </Panel>
              )}
            </ReactFlow>
          </div>

          {/* Inspector Panel */}
          <div className="w-80 border-l bg-background flex-shrink-0">
            <InspectorPanel
              selectedNode={selectedNode}
              onUpdateNode={handleUpdateNode}
            />
          </div>
        </div>
      </ReactFlowProvider>
    </Layout>
  );
}

