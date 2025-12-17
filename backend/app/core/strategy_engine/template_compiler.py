"""
Template Compiler: Converts form-based strategy configuration to Decision Graphs.
This is the bridge between user-friendly forms and the graph execution engine.
"""
from typing import Dict, Any
from app.models.strategy_template_config import get_template_config


def compile_liquidity_near_end(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compila la configuración de Near-Resolution Liquidity a un Decision Graph.
    """
    price_min = config.get("price_min", 0.95)
    price_max = config.get("price_max", 0.98)
    max_size = config.get("max_size_per_event", 5000)
    min_liquidity = config.get("min_liquidity", 2000)
    min_spread = config.get("min_spread", 1.5)
    event_finished = config.get("event_finished", True)
    external_confirmation = config.get("external_confirmation_required", True)
    allow_ambiguity = config.get("allow_ambiguity", False)
    
    # Build conditions for event_finished check
    conditions = []
    
    if event_finished:
        conditions.append({
            "field": "event_state.state",
            "operator": "==",
            "value": "FINISHED_CONFIRMED"
        })
    
    if external_confirmation:
        conditions.append({
            "field": "external_data.event_confirmation.confirmed",
            "operator": "==",
            "value": True
        })
    
    if not allow_ambiguity:
        conditions.append({
            "field": "external_data.event_confirmation.ambiguous",
            "operator": "==",
            "value": False
        })
    
    conditions.append({
        "field": "risk_state.exposure",
        "operator": "<",
        "value": "max_exposure"
    })
    
    # Price range check
    price_conditions = [
        {
            "field": "market_state.last_price",
            "operator": ">=",
            "value": price_min
        },
        {
            "field": "market_state.last_price",
            "operator": "<=",
            "value": price_max
        }
    ]
    
    # Liquidity check (if configured)
    liquidity_conditions = []
    if min_liquidity > 0:
        liquidity_conditions.append({
            "field": "market_state.total_liquidity",
            "operator": ">=",
            "value": min_liquidity
        })
    
    # Build Decision Graph
    decision_graph = {
        "entry_node": "collect_state",
        "nodes": {
            "collect_state": {
                "type": "collect_state",
                "config": {
                    "sources": ["market_state", "event_state", "external_data", "risk_state"]
                },
                "next": "check_event_finished"
            },
            "check_event_finished": {
                "type": "edge_and_risk_check",
                "config": {
                    "conditions": conditions,
                    "logic": "AND"
                },
                "on_true": "check_price_range",
                "on_false": "idle"
            },
            "check_price_range": {
                "type": "edge_and_risk_check",
                "config": {
                    "conditions": price_conditions,
                    "logic": "AND"
                },
                "on_true": "check_liquidity" if liquidity_conditions else "calculate_size",
                "on_false": "idle"
            }
        }
    }
    
    # Add liquidity check if needed
    if liquidity_conditions:
        decision_graph["nodes"]["check_liquidity"] = {
            "type": "edge_and_risk_check",
            "config": {
                "conditions": liquidity_conditions,
                "logic": "AND"
            },
            "on_true": "calculate_size",
            "on_false": "idle"
        }
    
    # Calculate size and emit intent
    decision_graph["nodes"]["calculate_size"] = {
        "type": "calculate_order_size",
        "config": {
            "method": "fixed_range",
            "min": 100,
            "max": max_size
        },
        "next": "emit_intent"
    }
    
    decision_graph["nodes"]["emit_intent"] = {
        "type": "emit_execution_intent",
        "config": {
            "side": "BUY",
            "outcome": "YES",
            "reason": "Near-resolution liquidity provision"
        },
        "next": "idle"
    }
    
    decision_graph["nodes"]["idle"] = {
        "type": "noop"
    }
    
    # Build Support Graph for external confirmation
    support_graphs = []
    if external_confirmation:
        external_source_id = config.get("external_source_id")
        if external_source_id:
            support_graphs.append({
                "name": "confirm_event_result",
                "trigger": {
                    "type": "event_state_change",
                    "condition": {
                        "field": "event.state",
                        "operator": "==",
                        "value": "FINISHED"
                    }
                },
                "entry_node": "fetch_external_confirmation",
                "nodes": {
                    "fetch_external_confirmation": {
                        "type": "fetch_external_source",
                        "config": {
                            "source_id": external_source_id,
                            "endpoint": "/api/event/result",
                            "params": {
                                "event_id": "{{event.id}}"
                            },
                            "output_key": "event_confirmation"
                        },
                        "next": "update_cache"
                    },
                    "update_cache": {
                        "type": "update_state_cache",
                        "config": {
                            "key": "event.{{event.id}}.external_confirmation",
                            "value_source": "context",
                            "value_path": "event_confirmation",
                            "ttl_seconds": 3600
                        },
                        "next": "end"
                    },
                    "end": {
                        "type": "noop"
                    }
                }
            })
    
    return {
        "decision_graph": decision_graph,
        "support_graphs": support_graphs,
        "risk_config": {
            "max_exposure": config.get("max_exposure", 10000),
            "max_order_size": max_size,
            "max_position_size": config.get("max_position_size", 10000)
        }
    }


def compile_surebet_polymarket_pinnacle(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compila la configuración de Surebet Polymarket-Pinnacle a un Decision Graph.
    """
    min_profit = config.get("min_profit_percentage", 2.0) / 100  # Convert to decimal
    max_size = config.get("max_size_per_event", 2000)
    polling_interval = config.get("polling_interval_seconds", 10)
    pinnacle_source_id = config.get("pinnacle_source_id")
    
    decision_graph = {
        "entry_node": "collect_state",
        "nodes": {
            "collect_state": {
                "type": "collect_state",
                "config": {
                    "sources": ["market_state", "external_data", "risk_state"]
                },
                "next": "check_surebet_opportunity"
            },
            "check_surebet_opportunity": {
                "type": "edge_and_risk_check",
                "config": {
                    "conditions": [
                        {
                            "field": "external_data.pinnacle_odds",
                            "operator": "!=",
                            "value": None
                        },
                        {
                            "field": "market_state.last_price",
                            "operator": "!=",
                            "value": None
                        },
                        {
                            "field": "risk_state.exposure",
                            "operator": "<",
                            "value": "max_exposure"
                        }
                    ],
                    "logic": "AND"
                },
                "on_true": "check_price_difference",
                "on_false": "idle"
            },
            "check_price_difference": {
                "type": "edge_and_risk_check",
                "config": {
                    "conditions": [
                        {
                            "field": "market_state.last_price",
                            "operator": "<=",
                            "value": 0.48  # Simplified: if Polymarket is significantly cheaper
                        }
                    ],
                    "logic": "AND"
                },
                "on_true": "buy_polymarket",
                "on_false": "idle"
            },
            "buy_polymarket": {
                "type": "calculate_order_size",
                "config": {
                    "method": "fixed_range",
                    "min": 100,
                    "max": max_size
                },
                "next": "emit_buy_intent"
            },
            "emit_buy_intent": {
                "type": "emit_execution_intent",
                "config": {
                    "side": "BUY",
                    "outcome": "YES",
                    "reason": "Surebet: Polymarket cheaper than Pinnacle"
                },
                "next": "idle"
            },
            "idle": {
                "type": "noop"
            }
        }
    }
    
    # Build Support Graph for Pinnacle odds
    support_graphs = []
    if pinnacle_source_id:
        support_graphs.append({
            "name": "fetch_pinnacle_odds",
            "trigger": {
                "type": "timer",
                "interval_seconds": polling_interval
            },
            "entry_node": "fetch_odds",
            "nodes": {
                "fetch_odds": {
                    "type": "fetch_external_source",
                    "config": {
                        "source_id": pinnacle_source_id,
                        "endpoint": "/api/odds",
                        "params": {
                            "event_id": "{{event.id}}"
                        },
                        "output_key": "pinnacle_odds"
                    },
                    "next": "update_cache"
                },
                "update_cache": {
                    "type": "update_state_cache",
                    "config": {
                        "key": "event.{{event.id}}.pinnacle_odds",
                        "value_source": "context",
                        "value_path": "pinnacle_odds",
                        "ttl_seconds": 30
                    },
                    "next": "end"
                },
                "end": {
                    "type": "noop"
                }
            }
        })
    
    return {
        "decision_graph": decision_graph,
        "support_graphs": support_graphs,
        "risk_config": {
            "max_exposure": config.get("max_exposure", 5000),
            "max_order_size": max_size,
            "max_position_size": config.get("max_position_size", 5000)
        }
    }


# Compiler registry
COMPILERS = {
    "compile_liquidity_near_end": compile_liquidity_near_end,
    "compile_surebet_polymarket_pinnacle": compile_surebet_polymarket_pinnacle,
}


def compile_strategy(template_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compila una configuración de estrategia a Decision Graph y Support Graphs.
    """
    template_config = get_template_config(template_id)
    if not template_config:
        raise ValueError(f"Template '{template_id}' not found")
    
    compiler_func = COMPILERS.get(template_config.compiler)
    if not compiler_func:
        raise ValueError(f"Compiler '{template_config.compiler}' not found")
    
    return compiler_func(config)

