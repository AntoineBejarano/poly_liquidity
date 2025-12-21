"""
Derive Plan Node - Crea un plan de seguimiento (follow-up) desde un plan base.

Este nodo crea un nuevo plan inmutable con el remanente de un plan parcialmente ejecutado.
El plan original permanece inmutable.
"""
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timedelta

from app.core.strategy_engine.nodes.base import GraphNode, PlanResult, FailureResult
from app.models.execution_plan import ExecutionPlan
from app.core.strategy_engine.models import PlanLeg

logger = logging.getLogger(__name__)


class DerivePlanNode(GraphNode):
    """
    Nodo que crea un plan de seguimiento (follow-up) desde un plan base.
    
    IMPORTANTE: El plan original permanece inmutable.
    Este nodo crea un NUEVO plan con el remanente.
    """
    
    async def execute(self) -> PlanResult:
        """
        Crea un plan de seguimiento desde un plan base.
        
        Config:
            base_plan_id: str | UUID - ID del plan base
            strategy: str - Estrategia para crear el follow-up:
                - "fill_remaining": Crea un plan con el remanente de legs parcialmente ejecutados
                - "retry_failed": Crea un plan con legs fallidos
                - "all_remaining": Crea un plan con todos los legs no completados
            ttl_ms: int - TTL del nuevo plan (default: mismo que el plan base)
            risk_config: dict - Risk config del nuevo plan (default: mismo que el plan base)
        
        Requiere:
            - db en context
            - strategy_id en context
            - event_id en context
        """
        base_plan_id = self.config.get("base_plan_id")
        strategy = self.config.get("strategy", "fill_remaining")
        ttl_ms = self.config.get("ttl_ms")
        risk_config = self.config.get("risk_config")
        
        if not base_plan_id:
            return FailureResult("base_plan_id is required")
        
        # Resolver template
        try:
            base_plan_id = self._resolve_template(base_plan_id)
        except ValueError as e:
            return FailureResult(f"Template resolution error: {str(e)}")
        
        # Convertir base_plan_id a UUID si es string
        if isinstance(base_plan_id, str):
            try:
                base_plan_id = UUID(base_plan_id)
            except ValueError:
                return FailureResult(f"Invalid base_plan_id format: {base_plan_id}")
        
        # Obtener plan base de DB
        try:
            base_plan = self.context.db.query(ExecutionPlan).filter(
                ExecutionPlan.id == base_plan_id
            ).first()
            
            if not base_plan:
                return FailureResult(f"Base ExecutionPlan with ID {base_plan_id} not found")
            
            # Validar que el plan base esté en un estado que permita derivar
            if base_plan.status not in {"EXECUTING", "PARTIAL_FILL", "FAILED"}:
                return FailureResult(
                    f"Cannot derive plan from base plan in status {base_plan.status}. "
                    f"Expected EXECUTING, PARTIAL_FILL, or FAILED"
                )
            
            # Obtener legs del plan base
            base_legs = base_plan.legs or []
            
            # Crear legs del nuevo plan según estrategia
            new_legs = []
            
            if strategy == "fill_remaining":
                # Crear legs con el remanente de legs parcialmente ejecutados
                for leg in base_legs:
                    if leg.get("status") == "PARTIAL":
                        remaining_size = Decimal(str(leg.get("size", 0))) - Decimal(str(leg.get("filled_size", 0)))
                        remaining_size_usdc = Decimal(str(leg.get("size_usdc", 0))) - Decimal(str(leg.get("filled_size_usdc", 0)))
                        
                        if remaining_size > 0:
                            new_leg = {
                                "leg_id": f"{leg.get('leg_id')}_followup",
                                "side": leg.get("side"),
                                "outcome": leg.get("outcome"),
                                "target_price": leg.get("target_price"),
                                "size": float(remaining_size),
                                "size_usdc": float(remaining_size_usdc),
                                "status": "PENDING",
                                "filled_size": 0,
                                "filled_size_usdc": 0,
                                "reason": f"Follow-up for {leg.get('leg_id')}",
                                "metadata": {
                                    "base_plan_id": str(base_plan_id),
                                    "base_leg_id": leg.get("leg_id")
                                }
                            }
                            new_legs.append(new_leg)
            
            elif strategy == "retry_failed":
                # Crear legs con legs fallidos
                for leg in base_legs:
                    if leg.get("status") == "FAILED":
                        new_leg = {
                            "leg_id": f"{leg.get('leg_id')}_retry",
                            "side": leg.get("side"),
                            "outcome": leg.get("outcome"),
                            "target_price": leg.get("target_price"),
                            "size": leg.get("size"),
                            "size_usdc": leg.get("size_usdc"),
                            "status": "PENDING",
                            "filled_size": 0,
                            "filled_size_usdc": 0,
                            "reason": f"Retry for {leg.get('leg_id')}",
                            "metadata": {
                                "base_plan_id": str(base_plan_id),
                                "base_leg_id": leg.get("leg_id")
                            }
                        }
                        new_legs.append(new_leg)
            
            elif strategy == "all_remaining":
                # Crear legs con todos los legs no completados
                for leg in base_legs:
                    if leg.get("status") not in {"FILLED", "CANCELLED"}:
                        remaining_size = Decimal(str(leg.get("size", 0))) - Decimal(str(leg.get("filled_size", 0)))
                        remaining_size_usdc = Decimal(str(leg.get("size_usdc", 0))) - Decimal(str(leg.get("filled_size_usdc", 0)))
                        
                        new_leg = {
                            "leg_id": f"{leg.get('leg_id')}_followup",
                            "side": leg.get("side"),
                            "outcome": leg.get("outcome"),
                            "target_price": leg.get("target_price"),
                            "size": float(remaining_size) if remaining_size > 0 else leg.get("size"),
                            "size_usdc": float(remaining_size_usdc) if remaining_size_usdc > 0 else leg.get("size_usdc"),
                            "status": "PENDING",
                            "filled_size": 0,
                            "filled_size_usdc": 0,
                            "reason": f"Follow-up for {leg.get('leg_id')}",
                            "metadata": {
                                "base_plan_id": str(base_plan_id),
                                "base_leg_id": leg.get("leg_id")
                            }
                        }
                        new_legs.append(new_leg)
            
            else:
                return FailureResult(f"Unknown strategy: {strategy}")
            
            if not new_legs:
                return FailureResult(f"No legs to create follow-up plan for strategy {strategy}")
            
            # Usar TTL y risk_config del plan base si no se especifican
            if ttl_ms is None:
                ttl_ms = base_plan.ttl_ms
            if risk_config is None:
                risk_config = base_plan.risk_config or {}
            
            # Crear nuevo ExecutionPlan
            new_plan = ExecutionPlan(
                strategy_id=self.context.strategy_id,
                event_id=self.context.event_id,
                legs=new_legs,
                ttl_ms=ttl_ms,
                status="PLAN_BUILT",
                risk_config=risk_config,
                trace_id=base_plan.trace_id,
                decision_graph_execution_id=base_plan.decision_graph_execution_id
            )
            
            self.context.db.add(new_plan)
            self.context.db.flush()
            
            # Guardar el plan_id en el contexto para nodos posteriores
            self.context.last_plan_id = new_plan.id
            
            logger.info(
                f"Created follow-up plan {new_plan.id} from base plan {base_plan_id} "
                f"with {len(new_legs)} legs using strategy {strategy}"
            )
            
            return PlanResult(plan_id=new_plan.id)
            
        except Exception as e:
            logger.error(f"Error deriving plan from {base_plan_id}: {e}", exc_info=True)
            self.context.db.rollback()
            return FailureResult(f"Error deriving plan: {str(e)}")
    
    def _resolve_template(self, value: Any) -> Any:
        """Resuelve templates usando valores del contexto."""
        if value is None:
            return None
        
        if isinstance(value, str) and "{{" in value and "}}" in value:
            if "{{plan.id}}" in value or "{{plan_id}}" in value or "{{base_plan_id}}" in value:
                plan_id = None
                if hasattr(self.context, 'plan_id'):
                    plan_id = self.context.plan_id
                elif hasattr(self.context, 'last_plan_id'):
                    plan_id = self.context.last_plan_id
                elif hasattr(self.context, 'base_plan_id'):
                    plan_id = self.context.base_plan_id
                
                if plan_id:
                    value = value.replace("{{plan.id}}", str(plan_id))
                    value = value.replace("{{plan_id}}", str(plan_id))
                    value = value.replace("{{base_plan_id}}", str(plan_id))
                    if value in ["{{plan.id}}", "{{plan_id}}", "{{base_plan_id}}"]:
                        return plan_id
                else:
                    raise ValueError(f"Template {value} could not be resolved: plan_id not in context")
            
            if "{{" in value and "}}" in value:
                raise ValueError(f"Unresolved template in value: {value}")
        
        return value

