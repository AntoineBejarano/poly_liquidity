// Utilities for converting between JSON graph format and React Flow format

import { Node, Edge } from 'reactflow';
import { GraphNode, GraphEdge, StrategyGraph, NodeData, NODE_DEFINITIONS } from './types';

/**
 * Convert backend JSON graph format to React Flow format
 */
export function jsonToReactFlow(jsonGraph: any): { nodes: Node<NodeData>[]; edges: Edge[] } {
  if (!jsonGraph || !jsonGraph.nodes) {
    return { nodes: [], edges: [] };
  }

  const nodes: Node<NodeData>[] = jsonGraph.nodes.map((node: any) => {
    const nodeDef = NODE_DEFINITIONS[node.type];
    return {
      id: node.id,
      type: 'strategyNode',
      position: node.position || { x: 0, y: 0 },
      data: {
        type: node.type,
        category: nodeDef?.category || 'signal',
        label: node.label || nodeDef?.name || node.type,
        config: node.config || {},
        enabled: node.enabled !== false,
      },
    };
  });

  const edges: Edge[] = (jsonGraph.edges || []).map((edge: any) => ({
    id: edge.id || `${edge.source}-${edge.target}`,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.sourceHandle,
    targetHandle: edge.targetHandle,
    type: 'smoothstep',
    animated: true,
  }));

  return { nodes, edges };
}

/**
 * Convert React Flow format to backend JSON graph format
 */
export function reactFlowToJson(nodes: Node<NodeData>[], edges: Edge[]): any {
  return {
    nodes: nodes.map(node => ({
      id: node.id,
      type: node.data.type,
      label: node.data.label,
      position: node.position,
      config: node.data.config,
      enabled: node.data.enabled !== false,
    })),
    edges: edges.map(edge => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceHandle: edge.sourceHandle,
      targetHandle: edge.targetHandle,
    })),
  };
}

/**
 * Validate that the graph is a valid DAG ending in execution nodes
 */
export function validateGraph(nodes: Node<NodeData>[], edges: Edge[]): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // Check that graph has nodes
  if (nodes.length === 0) {
    errors.push('Graph must have at least one node');
    return { valid: false, errors };
  }

  // Check that there are execution nodes
  const executionNodes = nodes.filter(n => n.data.category === 'execution');
  if (executionNodes.length === 0) {
    errors.push('Graph must have at least one execution node');
  }

  // Check that all execution nodes are terminal (no outgoing edges)
  executionNodes.forEach(node => {
    const hasOutgoing = edges.some(e => e.source === node.id);
    if (hasOutgoing) {
      errors.push(`Execution node "${node.data.label}" cannot have outgoing connections`);
    }
  });

  // Check for cycles (simple DFS)
  const visited = new Set<string>();
  const recStack = new Set<string>();

  function hasCycle(nodeId: string): boolean {
    if (recStack.has(nodeId)) return true;
    if (visited.has(nodeId)) return false;

    visited.add(nodeId);
    recStack.add(nodeId);

    const outgoing = edges.filter(e => e.source === nodeId);
    for (const edge of outgoing) {
      if (hasCycle(edge.target)) return true;
    }

    recStack.delete(nodeId);
    return false;
  }

  for (const node of nodes) {
    if (!visited.has(node.id) && hasCycle(node.id)) {
      errors.push('Graph contains cycles (must be a DAG)');
      break;
    }
  }

  // Check that data sources have no inputs
  nodes.forEach(node => {
    if (node.data.category === 'data_source') {
      const hasInputs = edges.some(e => e.target === node.id);
      if (hasInputs) {
        errors.push(`Data source "${node.data.label}" cannot have inputs`);
      }
    }
  });

  // Check that execution nodes have inputs
  executionNodes.forEach(node => {
    const hasInputs = edges.some(e => e.target === node.id);
    if (!hasInputs) {
      errors.push(`Execution node "${node.data.label}" must have at least one input`);
    }
  });

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Get next available position for a new node
 */
export function getNextNodePosition(nodes: Node<NodeData>[]): { x: number; y: number } {
  if (nodes.length === 0) {
    return { x: 250, y: 250 };
  }

  const maxY = Math.max(...nodes.map(n => n.position.y));
  return { x: 250, y: maxY + 150 };
}












