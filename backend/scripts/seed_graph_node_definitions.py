"""
Script para seedear definiciones de nodos de grafo predefinidos.

Ejecutar: python -m scripts.seed_graph_node_definitions
"""
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.models.graph_node_definition import GraphNodeDefinition
from uuid import uuid4


def seed_graph_node_definitions():
    """Seed de nodos predefinidos."""
    db = SessionLocal()
    
    try:
        # Verificar si ya existen nodos
        existing = db.query(GraphNodeDefinition).count()
        if existing > 0:
            print(f"Ya existen {existing} nodos definidos. Saltando seed.")
            return
        
        nodes = [
            # Nodos para Decision Graph (hot path)
            {
                "node_type": "collect_state",
                "name": "Collect State",
                "description": "Recopila estado del State Cache (market_state, event_state, external_data, risk_state)",
                "category": "state",
                "path_type": "hot",
                "config_schema": {
                    "type": "object",
                    "properties": {
                        "sources": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["market_state", "event_state", "external_data", "risk_state"]},
                            "description": "Fuentes de estado a recopilar"
                        }
                    },
                    "required": ["sources"]
                },
                "is_builtin": True,
                "version": "1.0.0",
                "icon": "database"
            },
            {
                "node_type": "edge_and_risk_check",
                "name": "Edge and Risk Check",
                "description": "Evalúa condiciones (edge) y verifica riesgo. Retorna condición booleana.",
                "category": "condition",
                "path_type": "hot",
                "config_schema": {
                    "type": "object",
                    "properties": {
                        "conditions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "field": {"type": "string", "description": "Campo a evaluar (ej: 'event_state.state')"},
                                    "operator": {"type": "string", "enum": ["==", "!=", ">", ">=", "<", "<=", "in", "not_in"]},
                                    "value": {"description": "Valor esperado"}
                                },
                                "required": ["field", "operator", "value"]
                            }
                        },
                        "logic": {
                            "type": "string",
                            "enum": ["AND", "OR"],
                            "default": "AND",
                            "description": "Lógica para combinar condiciones"
                        }
                    },
                    "required": ["conditions"]
                },
                "is_builtin": True,
                "version": "1.0.0",
                "icon": "check-circle"
            },
            {
                "node_type": "calculate_order_size",
                "name": "Calculate Order Size",
                "description": "Calcula el tamaño de orden basado en configuración de riesgo",
                "category": "calculation",
                "path_type": "hot",
                "config_schema": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "enum": ["fixed_range", "percentage", "kelly"],
                            "description": "Método de cálculo"
                        },
                        "min": {"type": "number", "description": "Tamaño mínimo (USDC)"},
                        "max": {"type": "number", "description": "Tamaño máximo (USDC)"},
                        "percentage": {"type": "number", "description": "Porcentaje del bank (si method=percentage)"}
                    },
                    "required": ["method"]
                },
                "is_builtin": True,
                "version": "1.0.0",
                "icon": "calculator"
            },
            {
                "node_type": "emit_execution_intent",
                "name": "Emit Execution Intent",
                "description": "Emite un Execution Intent (output del Decision Graph)",
                "category": "action",
                "path_type": "hot",
                "config_schema": {
                    "type": "object",
                    "properties": {
                        "side": {
                            "type": "string",
                            "enum": ["BUY", "SELL"],
                            "default": "BUY"
                        },
                        "outcome": {
                            "type": "string",
                            "enum": ["YES", "NO", "UP", "DOWN"],
                            "default": "YES"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Razón de la entrada"
                        }
                    },
                    "required": ["side", "outcome"]
                },
                "is_builtin": True,
                "version": "1.0.0",
                "icon": "send"
            },
            {
                "node_type": "noop",
                "name": "No Operation",
                "description": "Nodo que no hace nada (fin del grafo o punto de espera)",
                "category": "action",
                "path_type": "hot",
                "config_schema": {
                    "type": "object",
                    "properties": {}
                },
                "is_builtin": True,
                "version": "1.0.0",
                "icon": "stop"
            },
            # Nodos para Support Graphs (cold path)
            {
                "node_type": "fetch_external_source",
                "name": "Fetch External Source",
                "description": "Obtiene datos de una fuente externa (API, etc.)",
                "category": "io",
                "path_type": "cold",
                "config_schema": {
                    "type": "object",
                    "properties": {
                        "source_id": {
                            "type": "string",
                            "format": "uuid",
                            "description": "ID de la fuente de datos externa"
                        },
                        "endpoint": {
                            "type": "string",
                            "description": "Endpoint a llamar"
                        },
                        "params": {
                            "type": "object",
                            "description": "Parámetros de la llamada"
                        }
                    },
                    "required": ["source_id", "endpoint"]
                },
                "is_builtin": True,
                "version": "1.0.0",
                "icon": "download"
            },
            {
                "node_type": "update_state_cache",
                "name": "Update State Cache",
                "description": "Actualiza el State Cache con nuevos valores",
                "category": "state",
                "path_type": "cold",
                "config_schema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Clave del cache (ej: 'event.{event_id}.external_confirmation')"
                        },
                        "value": {
                            "description": "Valor a almacenar"
                        },
                        "ttl_seconds": {
                            "type": "integer",
                            "description": "TTL en segundos (opcional)"
                        }
                    },
                    "required": ["key", "value"]
                },
                "is_builtin": True,
                "version": "1.0.0",
                "icon": "save"
            },
            {
                "node_type": "log",
                "name": "Log",
                "description": "Registra un mensaje en los logs",
                "category": "io",
                "path_type": "cold",
                "config_schema": {
                    "type": "object",
                    "properties": {
                        "level": {
                            "type": "string",
                            "enum": ["DEBUG", "INFO", "WARNING", "ERROR"],
                            "default": "INFO"
                        },
                        "message": {
                            "type": "string",
                            "description": "Mensaje a loggear"
                        }
                    },
                    "required": ["message"]
                },
                "is_builtin": True,
                "version": "1.0.0",
                "icon": "file-text"
            }
        ]
        
        for node_data in nodes:
            node = GraphNodeDefinition(
                id=uuid4(),
                **node_data
            )
            db.add(node)
        
        db.commit()
        print(f"Seedeados {len(nodes)} nodos de grafo predefinidos.")
        
    except Exception as e:
        db.rollback()
        print(f"Error al seedear nodos: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_graph_node_definitions()

