/**
 * Tipos TypeScript para el sistema de estrategias basado en grafos.
 */

export interface DecisionGraph {
  entry_node: string;
  nodes: Record<string, GraphNode>;
}

export interface SupportGraph {
  name: string;
  trigger: GraphTrigger;
  entry_node: string;
  nodes: Record<string, GraphNode>;
}

export interface GraphNode {
  type: string;
  config?: Record<string, any>;
  next?: string;
  on_true?: string;
  on_false?: string;
}

export interface GraphTrigger {
  type: 'always' | 'timer' | 'event_state_change' | 'external';
  interval_seconds?: number;
  condition?: {
    field: string;
    operator: string;
    value: any;
  };
}

export interface StrategyTemplate {
  id: string;
  name: string;
  description: string;
  /** API may return key/label or name; StrategyConfigForm expects key, label, type */
  fields?: Array<Record<string, any>>;
  [key: string]: any;
}

export interface Strategy {
  id: string;
  name: string;
  description?: string;
  is_active: boolean;
  enabled_at?: string | null;
  disabled_at?: string | null;
  decision_graph: DecisionGraph;
  support_graphs: SupportGraph[];
  control_loop_config: Record<string, any>;
  risk_config: Record<string, any>;
  tags?: string[];
  /** ID de la wallet asignada a esta estrategia; null = usar cuenta activa del usuario */
  wallet_id?: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface GraphNodeDefinition {
  id: string;
  node_type: string;
  name: string;
  description?: string;
  category: string;
  path_type: 'hot' | 'cold';
  config_schema: Record<string, any>;
  is_builtin: boolean;
  version?: string;
  icon?: string;
}

export interface GraphExecution {
  id: string;
  strategy_id: string;
  graph_type: 'decision' | 'support';
  graph_name?: string;
  event_id?: string;
  status: 'completed' | 'failed' | 'running';
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  result?: Record<string, any>;
  error_message?: string;
  trace_id: string;
  node_executions?: Array<{
    node_id: string;
    node_type: string;
    status: string;
    duration_ms: number;
    result?: any;
    error?: string;
  }>;
}

export interface ExecutionIntent {
  id: string;
  strategy_id: string;
  event_id: string;
  side: 'BUY' | 'SELL';
  outcome: string;
  target_price: number;
  size: number;
  size_usdc: number;
  reason: string;
  context?: Record<string, any>;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXECUTED' | 'EXECUTING' | 'FAILED';
  approved_at?: string;
  rejected_at?: string;
  rejection_reason?: string;
  trace_id: string;
  graph_execution_id?: string;
  order_id?: string;
  created_at: string;
}

export interface StrategyMetric {
  id: string;
  strategy_id: string;
  period_start: string;
  period_end: string;
  total_intents: number;
  approved_intents: number;
  executed_intents: number;
  rejected_intents: number;
  total_volume_usdc: number;
  total_pnl_usdc?: number;
  total_exposure_usdc: number;
  win_rate?: number;
  avg_entry_price?: number;
  avg_exit_price?: number;
  calculated_at: string;
}

