"""
Build Plan Node - Construye un ExecutionPlan.

Este nodo crea un ExecutionPlan inmutable con los legs especificados.
Es el punto donde el Decision Graph decide qué ejecutar.
"""
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4

from app.core.strategy_engine.nodes.base import GraphNode, PlanResult, FailureResult
from app.core.strategy_engine.models import PlanLeg
from app.models.execution_plan import ExecutionPlan


class BuildPlanNode(GraphNode):
    """
    Nodo que construye un ExecutionPlan.
    
    Este nodo crea un ExecutionPlan inmutable con los legs especificados.
    El plan se guarda en la base de datos con status PLAN_BUILT.
    """
    
    async def execute(self) -> PlanResult:
        """
        Construye un ExecutionPlan.
        
        Config:
            legs: List[Dict] - Lista de legs del plan
                Cada leg debe tener:
                    - leg_id: str
                    - side: str ("BUY" | "SELL")
                    - outcome: str ("YES" | "NO" | "UP" | "DOWN")
                    - target_price: Decimal o str (se puede usar template "{{calculated_price}}")
                    - size: Decimal o str (se puede usar template "{{calculated_size}}")
                    - size_usdc: Decimal o str (se puede usar template "{{calculated_size_usdc}}")
                    - reason: str
                    - metadata: Dict (opcional)
            ttl_ms: int - Tiempo de vida del plan en milisegundos (default: 60000)
            risk_config: Dict (opcional) - Configuración de riesgo a nivel plan
        
        Requiere:
            - context.db (SQLAlchemy Session)
            - context.strategy_id
            - context.event_id
            - context.trace_id (opcional)
            - context.graph_execution_id (opcional)
        
        Puede usar datos del contexto:
            - calculated_price
            - calculated_size
            - calculated_size_usdc
        """
        # Validar que tenemos DB
        if not hasattr(self.context, 'db') or self.context.db is None:
            return FailureResult("Database session required")
        
        # Obtener configuración
        legs_data = self.config.get("legs", [])
        if not legs_data:
            return FailureResult("At least one leg is required")
        
        ttl_ms = self.config.get("ttl_ms", 60000)
        risk_config = self.config.get("risk_config", {})
        
        # Procesar legs (resolver templates y validar)
        processed_legs = []
        for leg_data in legs_data:
            try:
                leg = self._process_leg(leg_data)
                processed_legs.append(leg.model_dump() if hasattr(leg, 'model_dump') else leg.dict())
            except Exception as e:
                return FailureResult(f"Error processing leg {leg_data.get('leg_id', 'unknown')}: {str(e)}")
        
        # Registrar versiones de nodos usadas (si está disponible)
        node_versions = None
        if hasattr(self.context, 'strategy') and self.context.strategy:
            try:
                from app.core.strategy_engine.versioning import record_node_versions
                # Obtener el grafo actual (decision_graph) desde el contexto o strategy
                if hasattr(self.context, 'current_graph'):
                    graph = self.context.current_graph
                elif hasattr(self.context, 'strategy') and self.context.strategy:
                    graph = self.context.strategy.decision_graph
                else:
                    graph = {}
                
                node_versions = record_node_versions(graph, self.context.strategy, self.context.db)
            except Exception as e:
                logger.warning(f"Error recording node versions: {e}")
        
        # Crear ExecutionPlan
        try:
            plan = ExecutionPlan(
                strategy_id=self.context.strategy_id,
                event_id=self.context.event_id,
                legs=processed_legs,
                ttl_ms=ttl_ms,
                status="PLAN_BUILT",
                risk_config=risk_config,
                trace_id=getattr(self.context, 'trace_id', None),
                decision_graph_execution_id=getattr(self.context, 'graph_execution_id', None),
                ready_for_execution=False,
                queued_at=None,
                node_versions=node_versions
            )
            
            # Guardar en DB
            self.context.db.add(plan)
            self.context.db.flush()  # Para obtener el ID
            
            return PlanResult(plan.id)
            
        except Exception as e:
            return FailureResult(f"Error creating ExecutionPlan: {str(e)}")
    
    def _process_leg(self, leg_data: Dict[str, Any]) -> PlanLeg:
        """
        Procesa un leg, resolviendo templates y validando.
        
        Templates soportados:
            - {{calculated_price}}
            - {{calculated_size}}
            - {{calculated_size_usdc}}
        """
        # Resolver templates en target_price
        target_price = self._resolve_template(
            leg_data.get("target_price"),
            {
                "calculated_price": getattr(self.context, 'calculated_price', None)
            }
        )
        if target_price is None:
            raise ValueError("target_price is required")
        target_price = Decimal(str(target_price))
        
        # Resolver templates en size
        size = self._resolve_template(
            leg_data.get("size"),
            {
                "calculated_size": getattr(self.context, 'calculated_size', None)
            }
        )
        if size is None:
            raise ValueError("size is required")
        size = Decimal(str(size))
        
        # Resolver templates en size_usdc
        size_usdc = self._resolve_template(
            leg_data.get("size_usdc"),
            {
                "calculated_size_usdc": getattr(self.context, 'calculated_size_usdc', None),
                "calculated_price": getattr(self.context, 'calculated_price', None),
                "calculated_size": getattr(self.context, 'calculated_size', None)
            }
        )
        if size_usdc is None:
            # Calcular automáticamente si no se proporciona
            size_usdc = size * target_price
        else:
            size_usdc = Decimal(str(size_usdc))
        
        # Crear PlanLeg
        leg = PlanLeg(
            leg_id=leg_data.get("leg_id"),
            side=leg_data.get("side"),
            outcome=leg_data.get("outcome"),
            target_price=target_price,
            size=size,
            size_usdc=size_usdc,
            status=leg_data.get("status", "PENDING"),
            filled_size=Decimal(str(leg_data.get("filled_size", "0"))),
            filled_size_usdc=Decimal(str(leg_data.get("filled_size_usdc", "0"))),
            reason=leg_data.get("reason", ""),
            metadata=leg_data.get("metadata", {})
        )
        
        return leg
    
    def _resolve_template(self, value: Any, context: Dict[str, Any]) -> Any:
        """
        Resuelve templates en el valor.
        
        Si value es string y contiene {{variable}}, lo reemplaza con context[variable].
        Si no, retorna value tal cual.
        """
        if value is None:
            return None
        
        if isinstance(value, str) and "{{" in value and "}}" in value:
            # Template encontrado
            original_value = value
            for key, val in context.items():
                if val is not None:
                    template = f"{{{{{key}}}}}"
                    if template in value:
                        # Si el valor completo era el template, retornar el valor directamente
                        if value.strip() == template:
                            return val
                        # Reemplazar template
                        value = value.replace(template, str(val))
            # Si quedan templates sin resolver, lanzar error
            if "{{" in value and "}}" in value:
                raise ValueError(f"Unresolved template in value: {value}")
        
        return value
