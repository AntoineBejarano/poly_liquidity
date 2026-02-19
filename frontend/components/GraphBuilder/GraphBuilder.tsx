'use client';

import { useCallback, useEffect, useState, useMemo, useRef } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  Connection,
  addEdge,
  useNodesState,
  useEdgesState,
  NodeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { DecisionGraph, SupportGraph, GraphNodeDefinition } from '@/types/strategy';
import { CustomNode } from './CustomNode';
import { NodeConfigPanel } from './NodeConfigPanel';
import { NodePalette } from './NodePalette';

interface GraphBuilderProps {
  graph: DecisionGraph | SupportGraph;
  onGraphChange: (graph: DecisionGraph | SupportGraph) => void;
  pathType: 'hot' | 'cold';
  readOnly?: boolean;
  nodeDefinitions?: GraphNodeDefinition[];
  onNodeDefinitionsLoad?: () => Promise<GraphNodeDefinition[]>;
}

const nodeTypes: NodeTypes = {
  custom: CustomNode,
};

const initialNodePosition = { x: 100, y: 100 };

/**
 * Convierte un grafo JSON a nodos y edges de React Flow.
 */
function graphToReactFlow(
  graph: DecisionGraph | SupportGraph
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const nodePositions = new Map<string, { x: number; y: number }>();

  // Calcular posiciones automáticamente (layout simple)
  const nodeIds = Object.keys(graph.nodes);
  nodeIds.forEach((nodeId, index) => {
    const row = Math.floor(index / 3);
    const col = index % 3;
    nodePositions.set(nodeId, {
      x: col * 250 + 100,
      y: row * 150 + 100,
    });
  });

  // Crear nodos
  Object.entries(graph.nodes).forEach(([nodeId, nodeConfig]) => {
    const position = nodePositions.get(nodeId) || initialNodePosition;
    const isEntryNode = nodeId === graph.entry_node;

    nodes.push({
      id: nodeId,
      type: 'custom',
      position,
      data: {
        label: nodeConfig.type,
        nodeId,
        nodeType: nodeConfig.type,
        config: nodeConfig.config || {},
        isEntryNode,
      },
    });

    // Crear edges
    if (nodeConfig.next) {
      edges.push({
        id: `e-${nodeId}-${nodeConfig.next}`,
        source: nodeId,
        target: nodeConfig.next,
        type: 'smoothstep',
      });
    }
    if (nodeConfig.on_true) {
      edges.push({
        id: `e-${nodeId}-${nodeConfig.on_true}-true`,
        source: nodeId,
        target: nodeConfig.on_true,
        type: 'smoothstep',
        label: 'true',
        labelStyle: { fontWeight: 600, fill: 'hsl(var(--primary))' },
      });
    }
    if (nodeConfig.on_false) {
      edges.push({
        id: `e-${nodeId}-${nodeConfig.on_false}-false`,
        source: nodeId,
        target: nodeConfig.on_false,
        type: 'smoothstep',
        label: 'false',
        labelStyle: { fontWeight: 600, fill: 'hsl(var(--destructive))' },
      });
    }
  });

  return { nodes, edges };
}

/**
 * Convierte nodos y edges de React Flow a grafo JSON.
 */
function reactFlowToGraph(
  nodes: Node[],
  edges: Edge[],
  currentEntryNode?: string
): DecisionGraph | SupportGraph {
  const graphNodes: Record<string, any> = {};
  const entryNode = currentEntryNode || nodes[0]?.id || '';

  // Crear nodos
  nodes.forEach((node) => {
    const nodeData = node.data;
    graphNodes[node.id] = {
      type: nodeData.nodeType || nodeData.label,
      config: nodeData.config || {},
    };
  });

  // Agregar conexiones
  edges.forEach((edge) => {
    const sourceNode = graphNodes[edge.source];
    if (!sourceNode) return;

    if (edge.label === 'true') {
      sourceNode.on_true = edge.target;
    } else if (edge.label === 'false') {
      sourceNode.on_false = edge.target;
    } else {
      sourceNode.next = edge.target;
    }
  });

  return {
    entry_node: entryNode,
    nodes: graphNodes,
  } as DecisionGraph;
}

export function GraphBuilder({
  graph,
  onGraphChange,
  pathType,
  readOnly = false,
  nodeDefinitions = [],
  onNodeDefinitionsLoad,
}: GraphBuilderProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => graphToReactFlow(graph),
    [graph]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [availableNodeDefinitions, setAvailableNodeDefinitions] = useState<GraphNodeDefinition[]>(nodeDefinitions);
  
  // Ref para evitar loops infinitos
  const isInternalUpdateRef = useRef(false);
  const lastGraphRef = useRef<string>(JSON.stringify(graph));

  // Cargar definiciones de nodos si no se proporcionaron
  useEffect(() => {
    if (availableNodeDefinitions.length === 0 && onNodeDefinitionsLoad) {
      onNodeDefinitionsLoad().then(setAvailableNodeDefinitions).catch(console.error);
    }
  }, [availableNodeDefinitions.length, onNodeDefinitionsLoad]);

  // Actualizar nodos cuando cambia el grafo (solo si viene de fuera)
  useEffect(() => {
    const currentGraphStr = JSON.stringify(graph);
    
    // Solo actualizar si el grafo cambió desde fuera (no desde nuestra actualización interna)
    if (currentGraphStr !== lastGraphRef.current && !isInternalUpdateRef.current) {
      const { nodes: newNodes, edges: newEdges } = graphToReactFlow(graph);
      setNodes(newNodes);
      setEdges(newEdges);
      lastGraphRef.current = currentGraphStr;
    }
    
    // Resetear flag después de procesar
    isInternalUpdateRef.current = false;
  }, [graph, setNodes, setEdges]);

  // Manejar conexiones
  const onConnect = useCallback(
    (params: Connection) => {
      if (readOnly) return;
      setEdges((eds) => addEdge(params, eds));
    },
    [readOnly, setEdges]
  );

  // Actualizar grafo cuando cambian nodos o edges (solo en modo edición)
  useEffect(() => {
    if (readOnly) return;

    // Marcar como actualización interna para evitar loop
    isInternalUpdateRef.current = true;
    
    const newGraph = reactFlowToGraph(nodes, edges, graph.entry_node);
    const newGraphStr = JSON.stringify(newGraph);
    
    // Solo llamar onGraphChange si realmente cambió
    if (newGraphStr !== lastGraphRef.current) {
      lastGraphRef.current = newGraphStr;
      onGraphChange(newGraph);
    }
  }, [nodes, edges, graph.entry_node, readOnly, onGraphChange]);

  // Manejar selección de nodo
  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    if (readOnly) return;
    setSelectedNode(node);
  }, [readOnly]);

  // Actualizar configuración de nodo
  const handleNodeConfigChange = useCallback(
    (nodeId: string, config: Record<string, any>) => {
      if (readOnly) return;
      setNodes((nds) =>
        nds.map((node) =>
          node.id === nodeId
            ? { ...node, data: { ...node.data, config } }
            : node
        )
      );
    },
    [readOnly, setNodes]
  );

  // Agregar nuevo nodo
  const handleAddNode = useCallback(
    (nodeType: string) => {
      if (readOnly) return;

      const nodeDef = availableNodeDefinitions.find((d) => d.node_type === nodeType);
      if (!nodeDef) return;

      const newNodeId = `${nodeType}_${Date.now()}`;
      const newNode: Node = {
        id: newNodeId,
        type: 'custom',
        position: {
          x: Math.random() * 400 + 100,
          y: Math.random() * 300 + 100,
        },
        data: {
          label: nodeDef.name,
          nodeId: newNodeId,
          nodeType: nodeType,
          config: {},
          isEntryNode: nodes.length === 0,
        },
      };

      setNodes((nds) => [...nds, newNode]);

      // Si es el primer nodo, hacerlo entry node
      if (nodes.length === 0) {
        const newGraph = reactFlowToGraph([newNode], [], newNodeId);
        onGraphChange(newGraph);
      }
    },
    [readOnly, availableNodeDefinitions, nodes.length, setNodes, onGraphChange]
  );

  // Eliminar nodo
  const handleDeleteNode = useCallback(
    (nodeId: string) => {
      if (readOnly) return;
      setNodes((nds) => nds.filter((node) => node.id !== nodeId));
      setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
    },
    [readOnly, setNodes, setEdges]
  );

  // Establecer nodo de entrada
  const handleSetEntryNode = useCallback(
    (nodeId: string) => {
      if (readOnly) return;
      const newGraph = reactFlowToGraph(nodes, edges, nodeId);
      onGraphChange(newGraph);
    },
    [readOnly, nodes, edges, onGraphChange]
  );

  const nodeDefinition = selectedNode
    ? availableNodeDefinitions.find((d) => d.node_type === selectedNode.data.nodeType)
    : null;

  return (
    <div className="w-full h-[700px] rounded-[var(--radius-lg)] bg-card border border-[hsl(var(--border))]/50 relative overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        className="!bg-muted/30"
      >
        <Controls />
        <MiniMap />
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
      </ReactFlow>

      {!readOnly && (
        <>
          {selectedNode && nodeDefinition && (
            <NodeConfigPanel
              node={selectedNode}
              nodeDefinition={nodeDefinition}
              onConfigChange={(config) => handleNodeConfigChange(selectedNode.id, config)}
              onDelete={() => handleDeleteNode(selectedNode.id)}
              onSetEntryNode={() => handleSetEntryNode(selectedNode.id)}
              isEntryNode={selectedNode.id === graph.entry_node}
            />
          )}

          <NodePalette
            nodeDefinitions={availableNodeDefinitions.filter((d) => d.path_type === pathType)}
            onAddNode={handleAddNode}
          />
        </>
      )}
    </div>
  );
}

