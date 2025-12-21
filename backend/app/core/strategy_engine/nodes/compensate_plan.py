"""
Compensate Plan Node - Compensa (revierte) órdenes ejecutadas de un plan fallido.

Este nodo implementa la compensación según la estrategia especificada.
"""
import logging
from typing import Dict, Any, Optional
from uuid import UUID

from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult, FailureResult
from app.models.execution_plan import ExecutionPlan
from app.core.strategy_engine.invariants import validate_compensation_only_reduces_exposure

logger = logging.getLogger(__name__)


class CompensatePlanNode(GraphNode):
    """
    Nodo que compensa (revierte) órdenes ejecutadas de un plan fallido.
    
    La compensación solo puede reducir exposición, nunca aumentarla.
    """
    
    async def execute(self) -> SuccessResult:
        """
        Compensa un plan fallido.
        
        Config:
            plan_id: str | UUID - ID del plan a compensar
            compensation_strategy: str - Estrategia de compensación:
                - "reverse_all": Revierte todas las órdenes ejecutadas
                - "cancel_all": Cancela todas las órdenes pendientes
                - "partial": Solo compensa legs específicos (requiere leg_ids)
            leg_ids: list[str] - IDs de legs a compensar (solo para "partial")
        
        Requiere:
            - db en context
        """
        plan_id = self.config.get("plan_id")
        compensation_strategy = self.config.get("compensation_strategy", "reverse_all")
        leg_ids = self.config.get("leg_ids", [])
        
        if not plan_id:
            return FailureResult("plan_id is required")
        
        # Resolver template
        try:
            plan_id = self._resolve_template(plan_id)
        except ValueError as e:
            return FailureResult(f"Template resolution error: {str(e)}")
        
        # Convertir plan_id a UUID si es string
        if isinstance(plan_id, str):
            try:
                plan_id = UUID(plan_id)
            except ValueError:
                return FailureResult(f"Invalid plan_id format: {plan_id}")
        
        # Obtener plan de DB
        try:
            plan = self.context.db.query(ExecutionPlan).filter(
                ExecutionPlan.id == plan_id
            ).first()
            
            if not plan:
                return FailureResult(f"ExecutionPlan with ID {plan_id} not found")
            
            # Validar que el plan esté en un estado que permita compensación
            if plan.status not in {"EXECUTING", "FAILED", "PARTIAL_FILL"}:
                return FailureResult(
                    f"Cannot compensate plan in status {plan.status}. "
                    f"Expected EXECUTING, FAILED, or PARTIAL_FILL"
                )
            
            # Obtener legs del plan
            legs = plan.legs or []
            
            # Filtrar legs según estrategia
            legs_to_compensate = []
            if compensation_strategy == "reverse_all":
                # Compensar todos los legs ejecutados
                legs_to_compensate = [leg for leg in legs if leg.get("status") in {"FILLED", "PARTIAL", "EXECUTING"}]
            elif compensation_strategy == "cancel_all":
                # Cancelar todos los legs pendientes o ejecutándose
                legs_to_compensate = [leg for leg in legs if leg.get("status") in {"PENDING", "EXECUTING"}]
            elif compensation_strategy == "partial":
                # Solo compensar legs específicos
                if not leg_ids:
                    return FailureResult("leg_ids required for partial compensation strategy")
                legs_to_compensate = [leg for leg in legs if leg.get("leg_id") in leg_ids]
            else:
                return FailureResult(f"Unknown compensation_strategy: {compensation_strategy}")
            
            if not legs_to_compensate:
                logger.info(f"No legs to compensate for plan {plan_id}")
                return SuccessResult()
            
            # Validar que la compensación solo reduzca exposición
            compensation_actions = []
            for leg in legs_to_compensate:
                if leg.get("status") == "FILLED":
                    # Crear orden inversa para revertir
                    compensation_actions.append({
                        "type": "reverse_order",
                        "leg_id": leg.get("leg_id"),
                        "side": "SELL" if leg.get("side") == "BUY" else "BUY",
                        "outcome": leg.get("outcome"),
                        "size": leg.get("filled_size", leg.get("size")),
                        "price": leg.get("target_price")
                    })
                elif leg.get("status") in {"PENDING", "EXECUTING"}:
                    # Cancelar orden pendiente
                    compensation_actions.append({
                        "type": "cancel_order",
                        "leg_id": leg.get("leg_id"),
                        "order_id": leg.get("order_id")
                    })
            
            # Validar invariante: compensación solo reduce exposición
            try:
                validate_compensation_only_reduces_exposure(compensation_actions)
            except ValueError as e:
                return FailureResult(f"Compensation validation failed: {str(e)}")
            
            # Ejecutar acciones de compensación
            execution_engine = getattr(self.context, 'execution_engine', None)
            
            if not execution_engine:
                logger.warning("No execution_engine available, simulating compensation")
                # Simular compensación exitosa
                for leg in legs_to_compensate:
                    if leg.get("status") == "FILLED":
                        leg["status"] = "CANCELLED"  # Marcar como cancelado después de revertir
                    elif leg.get("status") in {"PENDING", "EXECUTING"}:
                        leg["status"] = "CANCELLED"
            else:
                # TODO: Implementar compensación real usando execution_engine
                # Por ahora, simular
                for leg in legs_to_compensate:
                    if leg.get("status") == "FILLED":
                        leg["status"] = "CANCELLED"
                    elif leg.get("status") in {"PENDING", "EXECUTING"}:
                        leg["status"] = "CANCELLED"
            
            # Actualizar estado del plan
            plan.status = "ABORTED"
            self.context.db.flush()
            
            logger.info(
                f"Compensated {len(legs_to_compensate)} legs for plan {plan_id} "
                f"using strategy {compensation_strategy}"
            )
            
            return SuccessResult()
            
        except ValueError as e:
            return FailureResult(f"Validation error: {str(e)}")
        except Exception as e:
            logger.error(f"Error compensating plan {plan_id}: {e}", exc_info=True)
            return FailureResult(f"Error compensating plan: {str(e)}")
    
    def _resolve_template(self, value: Any) -> Any:
        """Resuelve templates usando valores del contexto."""
        if value is None:
            return None
        
        if isinstance(value, str) and "{{" in value and "}}" in value:
            if "{{plan.id}}" in value or "{{plan_id}}" in value:
                plan_id = None
                if hasattr(self.context, 'plan_id'):
                    plan_id = self.context.plan_id
                elif hasattr(self.context, 'last_plan_id'):
                    plan_id = self.context.last_plan_id
                
                if plan_id:
                    value = value.replace("{{plan.id}}", str(plan_id))
                    value = value.replace("{{plan_id}}", str(plan_id))
                    if value == "{{plan.id}}" or value == "{{plan_id}}":
                        return plan_id
                else:
                    raise ValueError(f"Template {value} could not be resolved: plan_id not in context")
            
            if "{{" in value and "}}" in value:
                raise ValueError(f"Unresolved template in value: {value}")
        
        return value

