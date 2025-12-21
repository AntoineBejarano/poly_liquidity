"""
Edge and Risk Check Node - Evalúa condiciones (edge) y riesgo.

Evalúa múltiples condiciones con lógica AND/OR.
"""
from typing import Dict, Any, List

from app.core.strategy_engine.nodes.base import GraphNode, ConditionalResult


class EdgeAndRiskCheckNode(GraphNode):
    """
    Nodo que evalúa condiciones (edge) y riesgo.
    
    Evalúa múltiples condiciones con lógica AND/OR.
    Retorna ConditionalResult con el resultado.
    """
    
    async def execute(self) -> ConditionalResult:
        """
        Evalúa condiciones y retorna resultado booleano.
        
        Config:
            conditions: List[Dict] - Lista de condiciones
                - field: str - Campo a evaluar (ej: "event_state.state")
                - operator: str - Operador (==, !=, >, >=, <, <=, in, not_in)
                - value: Any - Valor esperado
            logic: str - "AND" o "OR" (default: "AND")
        """
        conditions = self.config.get("conditions", [])
        logic = self.config.get("logic", "AND")  # "AND" o "OR"
        
        if not conditions:
            # Sin condiciones, retornar True
            return ConditionalResult(True, {"message": "No conditions to evaluate"})
        
        results: List[bool] = []
        
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")
            
            if not field or operator is None:
                # Condición inválida, considerar como False
                results.append(False)
                continue
            
            # Resolver valor del campo desde el estado recopilado
            field_value = self._resolve_field(field)
            
            # Evaluar condición
            try:
                condition_result = self._evaluate_condition(field_value, operator, value)
                results.append(condition_result)
            except Exception as e:
                # Error al evaluar, considerar como False
                results.append(False)
        
        # Aplicar lógica
        if logic == "AND":
            final_result = all(results)
        else:  # OR
            final_result = any(results)
        
        return ConditionalResult(
            final_result,
            {
                "conditions": results,
                "logic": logic,
                "total_conditions": len(conditions)
            }
        )
    
    def _resolve_field(self, field_path: str) -> Any:
        """
        Resuelve un campo desde el estado recopilado o signals.
        
        Ejemplos:
        - "event_state.state" -> context.collected_state["event_state"]["state"]
        - "signals.toxic_flow" -> context.signals["toxic_flow"]
        - "signals.book_imbalance" -> context.signals["book_imbalance"]
        """
        parts = field_path.split(".")
        
        # Si el campo empieza con "signals", buscar en context.signals
        if parts[0] == "signals":
            if not hasattr(self.context, 'signals') or not self.context.signals:
                return None
            
            # Si solo hay "signals", retornar todo el dict
            if len(parts) == 1:
                return self.context.signals
            
            # Resolver el campo específico (ej: "signals.toxic_flow")
            signal_name = ".".join(parts[1:])  # Unir el resto de las partes
            return self.context.signals.get(signal_name)
        
        # Para otros campos, buscar en collected_state
        if not hasattr(self.context, 'collected_state') or not self.context.collected_state:
            return None
        
        value = self.context.collected_state
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            
            if value is None:
                return None
        
        return value
    
    def _evaluate_condition(self, field_value: Any, operator: str, expected_value: Any) -> bool:
        """
        Evalúa una condición.
        
        Soporta: ==, !=, >, >=, <, <=, in, not_in
        
        ⚠️ Manejo de None: Si field_value es None (señal no calculable),
        la condición se evalúa como False para operadores de comparación,
        excepto para == y != donde None == None es True.
        """
        # Manejo especial para None (señales no calculables)
        if field_value is None:
            if operator == "==":
                return expected_value is None
            elif operator == "!=":
                return expected_value is not None
            else:
                # Para operadores de comparación (>, <, >=, <=), None es False
                # Esto evita crashear cuando una señal no se puede calcular
                return False
        
        # Evaluar condición normal
        if operator == "==":
            return field_value == expected_value
        elif operator == "!=":
            return field_value != expected_value
        elif operator == ">":
            return field_value > expected_value
        elif operator == ">=":
            return field_value >= expected_value
        elif operator == "<":
            return field_value < expected_value
        elif operator == "<=":
            return field_value <= expected_value
        elif operator == "in":
            if not isinstance(expected_value, (list, tuple, set)):
                return False
            return field_value in expected_value
        elif operator == "not_in":
            if not isinstance(expected_value, (list, tuple, set)):
                return True
            return field_value not in expected_value
        else:
            raise ValueError(f"Unknown operator: {operator}")

