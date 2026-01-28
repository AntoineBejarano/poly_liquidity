"""
Strategy templates for common strategies.
These are pre-built graph configurations that users can start from.
"""
from typing import Dict, Any

# Template: Near-Resolution Liquidity Provider
LIQUIDITY_NEAR_END_TEMPLATE: Dict[str, Any] = {
    "name": "Near-Resolution Liquidity Provider",
    "description": "Provee liquidez cuando un evento ya terminó pero aún no ha sido resuelto por Polymarket. Captura el diferencial con riesgo casi nulo.",
    "decision_graph": {
        "entry_node": "collect_state",
        "nodes": {
            "collect_state": {
                "type": "collect_state",
                "config": {
                    "sources": ["market_state", "event_state", "external_data", "risk_state"]
                },
                "next": "compute_signals"
            },
            "compute_signals": {
                "type": "calculate_indicators",
                "config": {
                    "strategy_type": "liquidity"
                },
                "next": "check_event_finished"
            },
            "check_event_finished": {
                "type": "edge_and_risk_check",
                "config": {
                    "conditions": [
                        {
                            "field": "event_state.state",
                            "operator": "==",
                            "value": "FINISHED_CONFIRMED"
                        },
                        {
                            "field": "signals.toxic_flow",
                            "operator": "<",
                            "value": 0.25
                        },
                        {
                            "field": "signals.book_imbalance",
                            "operator": ">=",
                            "value": 0.4
                        },
                        {
                            "field": "signals.book_imbalance",
                            "operator": "<=",
                            "value": 0.6
                        },
                        {
                            "field": "signals.inventory_skew",
                            "operator": "<",
                            "value": 0.7
                        }
                    ],
                    "logic": "AND"
                },
                "on_true": "check_price_range",
                "on_false": "idle"
            },
            "check_price_range": {
                "type": "edge_and_risk_check",
                "config": {
                    "conditions": [
                        {
                            "field": "market_state.last_price",
                            "operator": ">=",
                            "value": 0.95
                        },
                        {
                            "field": "market_state.last_price",
                            "operator": "<=",
                            "value": 0.98
                        }
                    ],
                    "logic": "AND"
                },
                "on_true": "calculate_size",
                "on_false": "idle"
            },
            "calculate_size": {
                "type": "calculate_order_size",
                "config": {
                    "method": "fixed_range",
                    "min": 100,
                    "max": 5000
                },
                "next": "build_plan"
            },
            "build_plan": {
                "type": "build_plan",
                "config": {
                    "legs": [
                        {
                            "leg_id": "leg_1",
                            "side": "BUY",
                            "outcome": "YES",
                            "target_price": "{{calculate.price}}",
                            "size": "{{calculate.size}}",
                            "size_usdc": "{{calculate.size_usdc}}",
                            "reason": "Near-resolution liquidity provision"
                        }
                    ],
                    "ttl_ms": 30000,
                    "risk_config": {
                        "max_slippage": 0.02,
                        "max_fill_delay_ms": 5000,
                        "abort_on_price_move": True
                    }
                },
                "next": "emit_plan"
            },
            "emit_plan": {
                "type": "emit_plan_intent",
                "config": {
                    "plan_id": "{{plan.id}}"
                }
            },
            "idle": {
                "type": "noop"
            }
        }
    },
    "execution_graph": {
        "entry_node": "precheck",
        "nodes": {
            "precheck": {
                "type": "precheck",
                "config": {
                    "plan_id": "{{plan.id}}",
                    "max_book_staleness_ms": 2000,
                    "drift_bps_limit": 100,
                    "max_impact_bps": 200
                },
                "on_true": "coordinate",
                "on_false": "fail"
            },
            "coordinate": {
                "type": "execution_coordinator",
                "config": {
                    "plan_id": "{{plan.id}}",
                    "execution_mode": "sequential"
                }
            },
            "fail": {
                "type": "noop"
            }
        }
    },
    "support_graphs": [
        {
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
                        "source_id": "{{external_source_id}}",
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
        }
    ],
    "risk_config": {
        "max_exposure": 10000,
        "max_order_size": 5000,
        "max_position_size": 10000
    }
}

# Template: Surebet Polymarket-Pinnacle
SURBET_POLYMARKET_PINNACLE_TEMPLATE: Dict[str, Any] = {
    "name": "Surebet Polymarket-Pinnacle",
    "description": "Detecta y ejecuta surebets entre Polymarket y Pinnacle. Compra en el mercado más barato y vende en el más caro.",
    "decision_graph": {
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
                            "value": 0.48  # Si Polymarket es significativamente más barato que Pinnacle
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
                    "max": 2000
                },
                "next": "build_plan"
            },
            "build_plan": {
                "type": "build_plan",
                "config": {
                    "legs": [
                        {
                            "leg_id": "leg_1",
                            "side": "BUY",
                            "outcome": "YES",
                            "target_price": "{{calculate.price}}",
                            "size": "{{calculate.size}}",
                            "size_usdc": "{{calculate.size_usdc}}",
                            "reason": "Surebet: Polymarket cheaper than Pinnacle"
                        }
                    ],
                    "ttl_ms": 30000,
                    "risk_config": {
                        "max_slippage": 0.05,
                        "max_fill_delay_ms": 5000,
                        "abort_on_price_move": True
                    }
                },
                "next": "emit_plan"
            },
            "emit_plan": {
                "type": "emit_plan_intent",
                "config": {
                    "plan_id": "{{plan.id}}"
                }
            },
            "idle": {
                "type": "noop"
            }
        }
    },
    "execution_graph": {
        "entry_node": "precheck",
        "nodes": {
            "precheck": {
                "type": "precheck",
                "config": {
                    "plan_id": "{{plan.id}}",
                    "max_book_staleness_ms": 2000,
                    "drift_bps_limit": 100,
                    "max_impact_bps": 200
                },
                "on_true": "coordinate",
                "on_false": "fail"
            },
            "coordinate": {
                "type": "execution_coordinator",
                "config": {
                    "plan_id": "{{plan.id}}",
                    "execution_mode": "sequential"
                }
            },
            "fail": {
                "type": "noop"
            }
        }
    },
    "support_graphs": [
        {
            "name": "fetch_pinnacle_odds",
            "trigger": {
                "type": "timer",
                "interval_seconds": 10
            },
            "entry_node": "fetch_odds",
            "nodes": {
                "fetch_odds": {
                    "type": "fetch_external_source",
                    "config": {
                        "source_id": "{{pinnacle_source_id}}",
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
        }
    ],
    "risk_config": {
        "max_exposure": 5000,
        "max_order_size": 2000,
        "max_position_size": 5000
    }
}

# All available templates
STRATEGY_TEMPLATES = {
    "liquidity_near_end": LIQUIDITY_NEAR_END_TEMPLATE,
    "surebet_polymarket_pinnacle": SURBET_POLYMARKET_PINNACLE_TEMPLATE,
}

