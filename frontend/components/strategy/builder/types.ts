// Types for Strategy Builder

export type NodeType = 'data_source' | 'signal' | 'strategy' | 'risk' | 'execution';

export type NodeCategory = 'data_source' | 'signal' | 'strategy' | 'risk' | 'execution';

export interface NodeData {
  type: NodeType;
  category: NodeCategory;
  label: string;
  config: Record<string, any>;
  enabled: boolean;
}

export interface GraphNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: NodeData;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}

export interface StrategyGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// Node definitions
export interface NodeDefinition {
  type: string;
  name: string;
  description: string;
  category: NodeCategory;
  icon: string;
  color: string;
  inputs: number;
  outputs: number;
  configSchema: Record<string, any>;
}

// Predefined node definitions
export const NODE_DEFINITIONS: Record<string, NodeDefinition> = {
  // Data Sources (blue)
  'polymarket_markets': {
    type: 'polymarket_markets',
    name: 'Polymarket Markets',
    description: 'Polymarket markets and order book data',
    category: 'data_source',
    icon: '📊',
    color: '#3b82f6', // blue
    inputs: 0,
    outputs: 1,
    configSchema: {
      markets: { type: 'array', items: { type: 'string' } },
      update_frequency: { type: 'number', default: 5 },
    },
  },
  'pinnacle_odds': {
    type: 'pinnacle_odds',
    name: 'Pinnacle Odds',
    description: 'Pinnacle bookmaker odds',
    category: 'data_source',
    icon: '📈',
    color: '#3b82f6',
    inputs: 0,
    outputs: 1,
    configSchema: {
      sports: { type: 'array', items: { type: 'string' } },
      update_frequency: { type: 'number', default: 2 },
    },
  },
  'external_api': {
    type: 'external_api',
    name: 'External API',
    description: 'External data source (sports results, crypto price, etc.)',
    category: 'data_source',
    icon: '🔌',
    color: '#3b82f6',
    inputs: 0,
    outputs: 1,
    configSchema: {
      api_url: { type: 'string' },
      auth_type: { type: 'string', enum: ['none', 'api_key', 'oauth'] },
    },
  },
  
  // Signals / Functions (purple)
  'surebet_detector': {
    type: 'surebet_detector',
    name: 'Surebet Detector',
    description: 'Detects arbitrage opportunities between venues',
    category: 'signal',
    icon: '⚡',
    color: '#a855f7', // purple
    inputs: 2,
    outputs: 1,
    configSchema: {
      min_edge: { type: 'number', default: 0.02 },
      max_latency: { type: 'number', default: 5000 },
    },
  },
  'implied_probability': {
    type: 'implied_probability',
    name: 'Implied Probability',
    description: 'Calculates implied probability from odds',
    category: 'signal',
    icon: '📐',
    color: '#a855f7',
    inputs: 1,
    outputs: 1,
    configSchema: {
      odds_format: { type: 'string', enum: ['decimal', 'american', 'fractional'], default: 'decimal' },
    },
  },
  'price_deviation': {
    type: 'price_deviation',
    name: 'Price Deviation',
    description: 'Detects price deviations from expected value',
    category: 'signal',
    icon: '📉',
    color: '#a855f7',
    inputs: 2,
    outputs: 1,
    configSchema: {
      threshold: { type: 'number', default: 0.05 },
    },
  },
  'near_resolution_detector': {
    type: 'near_resolution_detector',
    name: 'Near Resolution Detector',
    description: 'Detects events near resolution',
    category: 'signal',
    icon: '⏰',
    color: '#a855f7',
    inputs: 1,
    outputs: 1,
    configSchema: {
      time_threshold: { type: 'number', default: 1800 }, // 30 minutes
    },
  },
  
  // Strategy Logic (green)
  'surebet_strategy': {
    type: 'surebet_strategy',
    name: 'Surebet Strategy',
    description: 'Surebet / arbitrage strategy logic',
    category: 'strategy',
    icon: '🎯',
    color: '#10b981', // green
    inputs: 1,
    outputs: 1,
    configSchema: {
      min_profit: { type: 'number', default: 0.02 },
      execution_order: { type: 'string', enum: ['polymarket_first', 'reference_first', 'atomic'] },
    },
  },
  'value_bet_strategy': {
    type: 'value_bet_strategy',
    name: 'Value Bet Strategy',
    description: 'Value betting strategy logic',
    category: 'strategy',
    icon: '💰',
    color: '#10b981',
    inputs: 1,
    outputs: 1,
    configSchema: {
      min_edge: { type: 'number', default: 0.05 },
      confidence_threshold: { type: 'number', default: 0.7 },
    },
  },
  'liquidity_provider': {
    type: 'liquidity_provider',
    name: 'Liquidity Provider',
    description: 'Liquidity provision strategy',
    category: 'strategy',
    icon: '💧',
    color: '#10b981',
    inputs: 1,
    outputs: 1,
    configSchema: {
      price_range: { type: 'object', properties: { min: { type: 'number' }, max: { type: 'number' } } },
      min_liquidity: { type: 'number', default: 1000 },
    },
  },
  
  // Risk & Constraints (red)
  'max_exposure': {
    type: 'max_exposure',
    name: 'Max Exposure',
    description: 'Maximum exposure constraint',
    category: 'risk',
    icon: '🛡️',
    color: '#ef4444', // red
    inputs: 1,
    outputs: 1,
    configSchema: {
      max_exposure: { type: 'number', default: 10000 },
      per_event: { type: 'number', default: 1000 },
    },
  },
  'cooldown': {
    type: 'cooldown',
    name: 'Cooldown',
    description: 'Cooldown period between trades',
    category: 'risk',
    icon: '⏸️',
    color: '#ef4444',
    inputs: 1,
    outputs: 1,
    configSchema: {
      cooldown_seconds: { type: 'number', default: 60 },
    },
  },
  'venue_availability': {
    type: 'venue_availability',
    name: 'Venue Availability',
    description: 'Checks venue availability and health',
    category: 'risk',
    icon: '🌐',
    color: '#ef4444',
    inputs: 1,
    outputs: 1,
    configSchema: {
      required_venues: { type: 'array', items: { type: 'string' } },
      max_latency: { type: 'number', default: 1000 },
    },
  },
  
  // Execution (gray)
  'polymarket_executor': {
    type: 'polymarket_executor',
    name: 'Polymarket Executor',
    description: 'Executes trades on Polymarket',
    category: 'execution',
    icon: '⚙️',
    color: '#6b7280', // gray
    inputs: 1,
    outputs: 0,
    configSchema: {
      wallet_id: { type: 'string' },
      slippage_tolerance: { type: 'number', default: 0.01 },
    },
  },
  'pinnacle_executor': {
    type: 'pinnacle_executor',
    name: 'Pinnacle Executor',
    description: 'Executes trades on Pinnacle',
    category: 'execution',
    icon: '⚙️',
    color: '#6b7280',
    inputs: 1,
    outputs: 0,
    configSchema: {
      account_id: { type: 'string' },
      max_stake: { type: 'number', default: 1000 },
    },
  },
  'multi_venue_executor': {
    type: 'multi_venue_executor',
    name: 'Multi-Venue Executor',
    description: 'Executes coordinated trades across multiple venues',
    category: 'execution',
    icon: '⚙️',
    color: '#6b7280',
    inputs: 1,
    outputs: 0,
    configSchema: {
      venues: { type: 'array', items: { type: 'string' } },
      atomic_execution: { type: 'boolean', default: false },
    },
  },
};





