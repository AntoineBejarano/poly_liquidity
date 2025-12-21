"""
Emit Plan Intent Node - Marca un plan como listo para ejecución.

Este nodo marca un ExecutionPlan como ready_for_execution.
Es el punto final del Decision Graph.
"""
from typing import Dict, Any
from datetime import datetime

from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult, FailureResult
from app.models.execution_plan import ExecutionPlan


class EmitPlanIntentNode(GraphNode):
    """
    Nodo que marca un ExecutionPlan como listo para ejecución.
    
    Este nodo actualiza el plan con ready_for_execution=True y queued_at=now().
    Esto permite observabilidad y debugging.
    """
    
    async def execute(self) -> SuccessResult:
        """
        Marca un plan como listo para ejecución.
        
        Config:
            plan_id: UUID o str - ID del plan a marcar como listo
                Puede ser template: "{{plan.id}}" o "{{plan_id}}"
        
        Requiere:
            - context.db (SQLAlchemy Session)
            - plan_id en config o en context (si se usa template)
        
        Efectos:
            - Actualiza plan.ready_for_execution = True
            - Actualiza plan.queued_at = now()
        """
        # Validar que tenemos DB
        if not hasattr(self.context, 'db') or self.context.db is None:
            return FailureResult("Database session required")
        
        # Obtener plan_id
        plan_id = self.config.get("plan_id")
        if not plan_id:
            # Intentar obtener del contexto (si viene de build_plan)
            if hasattr(self.context, 'last_plan_id'):
                plan_id = self.context.last_plan_id
            else:
                return FailureResult("plan_id is required")
        
        # Resolver template si es necesario
        try:
            plan_id = self._resolve_template(plan_id)
        except ValueError as e:
            return FailureResult(f"plan_id could not be resolved: {str(e)}")
        
        if not plan_id:
            return FailureResult("plan_id could not be resolved")
        
        # Convertir a UUID si es string
        from uuid import UUID
        if isinstance(plan_id, str):
            try:
                plan_id = UUID(plan_id)
            except ValueError:
                return FailureResult(f"Invalid plan_id format: {plan_id}")
        
        # Buscar plan en DB
        plan = self.context.db.query(ExecutionPlan).filter(
            ExecutionPlan.id == plan_id
        ).first()
        
        if not plan:
            return FailureResult(f"ExecutionPlan {plan_id} not found")
        
        # Marcar como listo
        plan.ready_for_execution = True
        plan.queued_at = datetime.utcnow()
        
        # Guardar cambios
        try:
            self.context.db.flush()
            return SuccessResult()
        except Exception as e:
            return FailureResult(f"Error updating plan: {str(e)}")
    
    def _resolve_template(self, value: Any) -> Any:
        """
        Resuelve templates en el valor.
        
        Templates soportados:
            - {{plan.id}}
            - {{plan_id}}
        """
        if value is None:
            return None
        
        if isinstance(value, str) and "{{" in value and "}}" in value:
            # Template encontrado
            # Intentar obtener del contexto
            if "{{plan.id}}" in value or "{{plan_id}}" in value:
                # Buscar en el contexto
                plan_id = None
                if hasattr(self.context, 'last_plan_id'):
                    plan_id = self.context.last_plan_id
                elif hasattr(self.context, 'plan_id'):
                    plan_id = self.context.plan_id
                
                if plan_id:
                    value = value.replace("{{plan.id}}", str(plan_id))
                    value = value.replace("{{plan_id}}", str(plan_id))
                    # Si el valor completo era el template, retornar directamente
                    if value == "{{plan.id}}" or value == "{{plan_id}}":
                        return plan_id
                else:
                    raise ValueError(f"Template {value} could not be resolved: plan_id not in context")
            
            # Si quedan templates sin resolver, lanzar error
            if "{{" in value and "}}" in value:
                raise ValueError(f"Unresolved template in value: {value}")
        
        return value
