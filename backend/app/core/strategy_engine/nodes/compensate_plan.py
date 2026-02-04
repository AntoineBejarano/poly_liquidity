"""
Compensate Plan Node - Compensa (revierte) órdenes ejecutadas de un plan fallido.

Este nodo implementa la compensación según la estrategia especificada.
"""
import logging
from typing import Any, Dict, List, Optional
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
            
            # Ejecutar acciones de compensación usando trading_platform (preferido) o execution_engine (legacy)
            trading_platform = getattr(self.context, 'trading_platform', None)
            execution_engine = getattr(self.context, 'execution_engine', None)
            
            if not trading_platform and not execution_engine:
                logger.warning("No trading_platform or execution_engine available, simulating compensation")
                # Simular compensación exitosa
                for leg in legs_to_compensate:
                    if leg.get("status") == "FILLED":
                        leg["status"] = "CANCELLED"
                    elif leg.get("status") in {"PENDING", "EXECUTING"}:
                        leg["status"] = "CANCELLED"
            else:
                # Ejecutar compensación real usando trading_platform (preferido)
                if trading_platform:
                    await self._execute_compensation_via_platform(legs_to_compensate, plan, trading_platform, compensation_actions)
                else:
                    # Fallback a execution_engine (legacy) - simular por ahora
                    logger.warning("Using execution_engine (legacy) for compensation, simulating")
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
    
    async def _execute_compensation_via_platform(
        self,
        legs_to_compensate: List[Dict[str, Any]],
        plan: ExecutionPlan,
        trading_platform,
        compensation_actions: List[Dict[str, Any]]
    ):
        """
        Ejecuta acciones de compensación usando TradingPlatform.
        
        - Para órdenes FILLED: Crea órdenes inversas (reverse)
        - Para órdenes PENDING/EXECUTING: Cancela las órdenes
        """
        from app.core.strategy_engine.models import PlanLeg
        from decimal import Decimal
        
        event = plan.event
        if not event:
            logger.error(f"Cannot compensate plan {plan.id}: event not found")
            return
        
        for action in compensation_actions:
            leg_id = action.get("leg_id")
            leg = next((l for l in legs_to_compensate if l.get("leg_id") == leg_id), None)
            if not leg:
                continue
            
            try:
                if action.get("type") == "reverse_order":
                    # Crear orden inversa para revertir una orden ejecutada
                    reverse_leg = PlanLeg(
                        leg_id=f"{leg_id}_reverse",
                        side=action.get("side"),  # Ya invertido (SELL si era BUY, etc.)
                        outcome=leg.get("outcome"),
                        target_price=Decimal(str(action.get("price"))),
                        size=Decimal(str(action.get("size"))),
                        size_usdc=Decimal(str(action.get("size")) * Decimal(str(action.get("price")))),
                        status="PENDING",
                        filled_size=Decimal("0"),
                        filled_size_usdc=Decimal("0"),
                        reason=f"Compensation reverse for leg {leg_id}",
                        metadata={
                            "event_id": str(event.id),
                            "market_id": str(event.market_id) if event.market_id else None,
                            "original_leg_id": leg_id,
                            "compensation": True
                        }
                    )
                    
                    # Enviar orden inversa
                    order_result = await trading_platform.submit_order(
                        leg=reverse_leg,
                        risk_config=plan.risk_config or {},
                        trace_id=plan.trace_id
                    )
                    
                    logger.info(
                        f"Compensation reverse order submitted for leg {leg_id}: {order_result.platform_order_id}",
                        extra={
                            "component": "compensate_plan",
                            "event": "compensation_reverse_order",
                            "leg_id": leg_id,
                            "platform_order_id": order_result.platform_order_id,
                            "trace_id": str(plan.trace_id) if plan.trace_id else None
                        }
                    )
                    
                    leg["status"] = "CANCELLED"
                    leg["compensation_order_id"] = order_result.platform_order_id
                    
                elif action.get("type") == "cancel_order":
                    # Cancelar orden pendiente o ejecutándose
                    order_id = action.get("order_id") or leg.get("platform_order_id") or leg.get("order_id")
                    if order_id:
                        cancelled = await trading_platform.cancel_order(
                            order_id=str(order_id),
                            trace_id=plan.trace_id
                        )
                        
                        if cancelled:
                            logger.info(
                                f"Compensation cancelled order for leg {leg_id}: {order_id}",
                                extra={
                                    "component": "compensate_plan",
                                    "event": "compensation_order_cancelled",
                                    "leg_id": leg_id,
                                    "platform_order_id": order_id,
                                    "trace_id": str(plan.trace_id) if plan.trace_id else None
                                }
                            )
                            leg["status"] = "CANCELLED"
                        else:
                            logger.warning(
                                f"Failed to cancel order for leg {leg_id}: {order_id}",
                                extra={
                                    "component": "compensate_plan",
                                    "event": "compensation_cancel_failed",
                                    "leg_id": leg_id,
                                    "platform_order_id": order_id
                                }
                            )
                    else:
                        logger.warning(f"No order_id found for leg {leg_id}, cannot cancel")
                        leg["status"] = "CANCELLED"  # Marcar como cancelado de todas formas
                        
            except Exception as e:
                logger.error(
                    f"Error executing compensation action for leg {leg_id}: {e}",
                    exc_info=True,
                    extra={
                        "component": "compensate_plan",
                        "event": "compensation_error",
                        "leg_id": leg_id,
                        "action_type": action.get("type")
                    }
                )
                # Marcar como cancelado de todas formas para evitar reintentos
                leg["status"] = "CANCELLED"

